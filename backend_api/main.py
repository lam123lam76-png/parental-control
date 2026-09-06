import logging
import threading
import time
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio

from database import SessionLocal, engine, ensure_schema
import models
from core.sync_service import periodic_sync_task

# Routers
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.devices import router as devices_router
from routers.rules import router as rules_router
from routers.logs import router as logs_router
from routers.websockets import router as websockets_router
from routers.system import router as system_router
from routers.registration import router as registration_router

# Core
from core.config import SCREENSHOTS_DIR, UPDATES_DIR, SYSTEM_ADMIN_EMAIL, SYSTEM_ADMIN_PASSWORD, PROJECT_ROOT
from core.state import device_online_state, device_graceful_shutdown
from core.notifications import send_telegram_notification
from core.telegram_approval import get_updates_poller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _init_schema_background():
    """Create/migrate schema in a background thread so a slow or unreachable DB
    never blocks uvicorn startup (tables already exist from migration; requests
    use pool_pre_ping and recover when Supabase is reachable).

    NOTE: we deliberately DO NOT run raw ALTER TABLE ADD COLUMN here — those
    columns already exist (migration + models), and a redundant ALTER takes an
    AccessExclusiveLock on the table, blocking all queries (seen in Supabase logs:
    'column is_system_admin already exists' + 90s lock waits -> web hangs loading).
    ensure_schema() below conditionally adds only genuinely-missing columns.
    """
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning(f"create_all failed (background): {e}")
    try:
        ensure_schema(engine)
    except Exception as e:
        logger.warning(f"ensure_schema failed (background): {e}")


threading.Thread(target=_init_schema_background, daemon=True).start()

def seed_system_admin():
    """Ensure the built-in super admin account exists on every startup."""
    from passlib.context import CryptContext
    _ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == SYSTEM_ADMIN_EMAIL).first()
        if not user:
            hashed = _ctx.hash(SYSTEM_ADMIN_PASSWORD)
            user = models.User(
                email=SYSTEM_ADMIN_EMAIL,
                password_hash=hashed,
                role="admin",
                is_system_admin=True
            )
            db.add(user)
            db.flush()
            perm = models.UserPermission(
                user_id=user.id,
                can_view_screenshots=True,
                can_manage_rules=True,
                can_view_logs=True,
                can_remote_control=True,
                can_manage_users=True
            )
            db.add(perm)
            parent = db.query(models.Parent).filter(models.Parent.email == SYSTEM_ADMIN_EMAIL).first()
            if not parent:
                parent = models.Parent(email=SYSTEM_ADMIN_EMAIL, password_hash=hashed)
                db.add(parent)
            db.commit()
            logger.info(f"[Seed] System admin account created: {SYSTEM_ADMIN_EMAIL}")
        else:
            _ctx2 = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
            if not user.is_system_admin:
                user.is_system_admin = True
            if user.role != "admin":
                user.role = "admin"
            if not _ctx2.verify(SYSTEM_ADMIN_PASSWORD, user.password_hash):
                user.password_hash = _ctx2.hash(SYSTEM_ADMIN_PASSWORD)
            perm = db.query(models.UserPermission).filter(models.UserPermission.user_id == user.id).first()
            if not perm:
                perm = models.UserPermission(
                    user_id=user.id,
                    can_view_screenshots=True,
                    can_manage_rules=True,
                    can_view_logs=True,
                    can_remote_control=True,
                    can_manage_users=True
                )
                db.add(perm)
            db.commit()
    except Exception as _e:
        db.rollback()
        logger.error(f"[Seed] Failed to seed system admin: {_e}")
    finally:
        db.close()

from datetime import timezone, timedelta
VIETNAM_TZ = timezone(timedelta(hours=7))

OFFLINE_THRESHOLD_SECONDS = 30  # báo offline nếu quá 30s không nghe thấy agent


def check_devices_offline(db) -> None:
    """Detect device online/offline transitions and notify Telegram.

    Persists per-device online state in system_settings so the check works on
    Vercel serverless (each request is a fresh process — an in-memory dict would
    be lost between invocations). Called from a middleware on every request and
    from the background thread (non-serverless).
    """
    try:
        now_utc = datetime.now(timezone.utc)
        # Refresh the session so we always read the latest persisted state (avoids
        # stale snapshot when this runs repeatedly in one session).
        try:
            db.expire_all()
        except Exception:
            pass
        # Load persisted online states (device_id -> "1"/"0")
        rows = db.query(models.SystemSetting).filter(
            models.SystemSetting.key.like("online_state:%")
        ).all()
        persisted = {r.key: r.value for r in rows}

        for d in db.query(models.Device).all():
            key = f"online_state:{d.id}"
            if not d.last_seen_at:
                continue
            last_seen = d.last_seen_at
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)

            is_offline = (now_utc - last_seen).total_seconds() > OFFLINE_THRESHOLD_SECONDS
            prev_online = persisted.get(key) == "1"

            if is_offline and prev_online:
                # online -> offline
                _set_state(db, key, "0")
                if device_graceful_shutdown.get(str(d.id), False):
                    device_graceful_shutdown[str(d.id)] = False
                else:
                    send_telegram_notification(db, f"🔴 Hệ thống giám sát thiết bị <b>{d.device_name}</b> đã tắt.")
            elif not is_offline and not prev_online:
                # offline -> online
                _set_state(db, key, "1")
                device_graceful_shutdown[str(d.id)] = False
        db.commit()
    except Exception as e:
        logger.error(f"[Monitor] check_devices_offline failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass


def _set_state(db, key: str, value: str) -> None:
    try:
        setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(models.SystemSetting(key=key, value=value))
    except Exception as e:
        logger.debug(f"set_state error {key}: {e}")


async def background_monitor_heartbeats():
    """Async background task (for non-serverless runtimes that keep threads alive)."""
    while True:
        try:
            db = SessionLocal()
            try:
                check_devices_offline(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[Monitor] Heartbeat check failed: {e}")
        await asyncio.sleep(15)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Parental Control Backend MVP...")
    # Run seed in a background thread so a slow/unreachable Supabase never
    # blocks uvicorn from starting and serving.
    threading.Thread(target=seed_system_admin, daemon=True).start()

    # DB-bound loops run in their OWN threads/event-loops so their synchronous
    # SQLAlchemy calls never block the main uvicorn event loop. Without this, a
    # hung Supabase connection freezes even static/SPA serving -> web won't open.
    def _run_monitor():
        asyncio.run(background_monitor_heartbeats())
    threading.Thread(target=_run_monitor, daemon=True).start()

    def _run_sync():
        asyncio.run(periodic_sync_task(SessionLocal))
    threading.Thread(target=_run_sync, daemon=True).start()

    # Telegram approval poller: run ONLY on the home backend (not Vercel serverless),
    # otherwise home + Vercel both poll getUpdates with the same bot token and steal
    # each other's updates. Override with TELEGRAM_POLLER_ENABLED=1 if needed.
    _on_vercel = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))
    _poller_override = os.getenv("TELEGRAM_POLLER_ENABLED", "").strip().lower() in ("1", "true", "yes")
    if _poller_override or not _on_vercel:
        threading.Thread(target=get_updates_poller, daemon=True).start()

    # Run purge in a separate thread so it doesn't block async loop if IO bound
    from routers.system import purge_old_trash
    asyncio.create_task(asyncio.to_thread(purge_old_trash))

    yield
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(title="Parental Control Backend MVP", lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

import schemas

@app.get("/api/health", response_model=schemas.StandardResponse)
def health_check():
    return schemas.StandardResponse(
        data={"status": "ok", "service": "Parental Control Backend MVP"},
        status_code=200
    )


app.mount("/static/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")
app.mount("/static/updates", StaticFiles(directory=str(UPDATES_DIR)), name="updates")

# Secured CORS Configuration (Production should list specific origins)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,https://nguyentruclam.io.vn")
allowed_origins_list = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_server_source_header(request, call_next):
    """Expose the serving source so the web manager can show where it's running.
    Home backend (not on Vercel) reports 'home'; the Vercel backup reports 'vercel'.
    The domain (nguyentruclam.io.vn) is identical for both, so the frontend can't
    infer the source from the hostname alone — it needs this header.

    Also runs a lazy offline-detection sweep on every request. On Vercel serverless
    the lifespan background thread does not persist between invocations, so this
    per-request check is what actually catches a device going offline (the web
    manager polls /api/devices regularly, giving us frequent triggers).

    FIX (HTTP 508): check_devices_offline chạy đồng bộ trên event loop làm block
    uvicorn khi Supabase chậm → request auth timeout → nginx retry → 508 loop.
    Giải pháp:
      1. Bỏ qua offline-check hoàn toàn cho mọi route auth/register/pair.
      2. Chạy trong asyncio.to_thread() để không block event loop cho các route khác.
    """
    path = request.url.path

    # Bỏ qua offline-check cho auth routes — login không được bị chặn bởi DB chậm
    _SKIP_CHECK_PREFIXES = ("/static", "/api/auth/", "/api/register", "/api/pair")
    should_check = not any(path.startswith(p) for p in _SKIP_CHECK_PREFIXES)

    if should_check:
        def _run_check():
            db = SessionLocal()
            try:
                check_devices_offline(db)
            finally:
                db.close()

        try:
            # Chạy trong thread pool — không block event loop của uvicorn
            await asyncio.wait_for(
                asyncio.to_thread(_run_check),
                timeout=5.0  # Nếu DB chậm > 5s → bỏ qua, không làm nghẽn request
            )
        except asyncio.TimeoutError:
            logger.warning("[offline-middleware] check timed out (>5s), skipping")
        except Exception as _e:
            logger.error(f"[offline-middleware] check failed: {_e}")

    response = await call_next(request)
    source = "vercel" if (os.getenv("VERCEL") or os.getenv("VERCEL_ENV")) else "home"
    response.headers["X-PC-Source"] = source
    return response

# Include Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(devices_router)
app.include_router(rules_router)
app.include_router(logs_router)
app.include_router(websockets_router)
app.include_router(system_router)
app.include_router(registration_router)

# Fallback WEB SPA
WEB_DIST_DIR = PROJECT_ROOT.parent / "manager-web" / "dist"
if not WEB_DIST_DIR.exists():
    WEB_DIST_DIR = PROJECT_ROOT / "manager-web" / "dist"

if WEB_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST_DIR / "assets")), name="web_assets")

    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}")
    async def serve_web_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws") or full_path.startswith("static"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        
        target_path = WEB_DIST_DIR / full_path
        if target_path.is_file():
            return FileResponse(target_path)
        return FileResponse(
            WEB_DIST_DIR / "index.html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

# Trigger reload
