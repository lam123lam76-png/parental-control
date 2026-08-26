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
from sqlalchemy import text
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

# Core
from core.config import SCREENSHOTS_DIR, UPDATES_DIR, SYSTEM_ADMIN_EMAIL, SYSTEM_ADMIN_PASSWORD, PROJECT_ROOT
from core.state import device_online_state, device_graceful_shutdown
from core.notifications import send_telegram_notification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _init_schema_background():
    """Create/migrate schema in a background thread so a slow or unreachable DB
    never blocks uvicorn startup (tables already exist from migration; requests
    use pool_pre_ping and recover when Supabase is reachable)."""
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning(f"create_all failed (background): {e}")
    try:
        ensure_schema(engine)
    except Exception as e:
        logger.warning(f"ensure_schema failed (background): {e}")
    # Auto-migrate SQLite schema columns if missing
    for _col_sql in [
        "ALTER TABLE devices ADD COLUMN is_locked BOOLEAN DEFAULT 0;",
        "ALTER TABLE users ADD COLUMN is_system_admin BOOLEAN DEFAULT 0;",
    ]:
        try:
            with engine.connect() as conn:
                conn.execute(text(_col_sql))
                conn.commit()
        except Exception:
            pass


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

async def background_monitor_heartbeats():
    """Async background task replacing the threading block."""
    while True:
        try:
            db = SessionLocal()
            try:
                devices = db.query(models.Device).all()
                now_utc = datetime.now(timezone.utc)
                for d in devices:
                    if not d.last_seen_at:
                        continue
                    last_seen = d.last_seen_at
                    if last_seen.tzinfo is None:
                        # Stored as UTC (naive after SQLite round-trip).
                        last_seen = last_seen.replace(tzinfo=timezone.utc)

                    is_offline = (now_utc - last_seen).total_seconds() > 45
                    prev_state = device_online_state.get(str(d.id), False)

                    if is_offline and prev_state:
                        device_online_state[str(d.id)] = False
                        if device_graceful_shutdown.get(str(d.id), False):
                            device_graceful_shutdown[str(d.id)] = False
                        else:
                            send_telegram_notification(db, f"⚠️ <b>[MẤT KẾT NỐI]</b> Thiết bị {d.device_name} đã mất kết nối đột ngột với Server!")
                    elif not is_offline and not prev_state:
                        device_online_state[str(d.id)] = True
                        device_graceful_shutdown[str(d.id)] = False
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

# Include Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(devices_router)
app.include_router(rules_router)
app.include_router(logs_router)
app.include_router(websockets_router)
app.include_router(system_router)


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
