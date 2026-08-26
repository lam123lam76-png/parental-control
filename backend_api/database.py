import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env BEFORE reading DATABASE_URL — database.py may be imported before
# core.config, so relying on that module's load_dotenv is not safe. Without this,
# the local backend silently falls back to SQLite while Vercel uses Supabase
# (split-brain: queued commands never reach the polling endpoint).
_BE_DIR = Path(__file__).resolve().parent
load_dotenv(_BE_DIR / ".env")
load_dotenv(_BE_DIR.parent / ".env")

# Fallback to local SQLite database if env var is not set
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./parental_control.db"
)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 15.0}
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=3,           # small: home server + ~2 agents needs very few
        max_overflow=5,        # cap total ~8 conns/process so Supabase pooler never exhausts
        pool_timeout=8,        # fail fast instead of waiting 30s for a pool slot
        pool_recycle=300,      # Recycle connections after 5 minutes
        pool_pre_ping=True,    # Check connection health before using
        # Fail fast: cap connect + add a statement timeout so a hung Supabase query
        # is cancelled and its connection released instead of exhausting the pool
        # and freezing the whole backend (web keeps loading forever).
        connect_args={"connect_timeout": 8, "options": "-c statement_timeout=10000"},
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_db():
    """
    FastAPI dependency to provide a database session per request.
    Closes the session after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Async engine/session — for async endpoints.
# Sync SQLAlchemy in an `async def` endpoint blocks the uvicorn event loop, so a
# slow/hung Supabase query freezes the whole backend (web keeps loading forever).
# Async endpoints use this async engine (asyncpg) instead; their DB calls are
# awaited and never block the loop.
# ---------------------------------------------------------------------------
import ssl as _ssl
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession  # noqa: E402


def _async_pg_url(url: str) -> str:
    base = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "?" in base:                      # strip ?sslmode=... (asyncpg uses ssl= connect arg)
        base = base.split("?")[0]
    return base


_ssl_ctx = _ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = _ssl.CERT_NONE

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    async_engine = None
    AsyncSessionLocal = None
else:
    async_engine = create_async_engine(
        _async_pg_url(SQLALCHEMY_DATABASE_URL),
        pool_size=3,
        max_overflow=5,
        pool_timeout=8,
        pool_recycle=300,
        pool_pre_ping=True,
        # statement_cache_size=0: avoids pgbouncer (Supabase pooler) prepared-statement errors
        connect_args={"ssl": _ssl_ctx, "statement_cache_size": 0, "timeout": 10},
    )
    AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_db_async():
    """FastAPI dependency yielding an async DB session (for async endpoints)."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Async DB not configured (SQLite has no async engine)")
    async with AsyncSessionLocal() as session:
        yield session


def ensure_schema(engine):
    """Idempotently add columns that create_all() cannot alter on existing tables.

    Works on both SQLite and PostgreSQL (Supabase). Safe to call at every startup.
    """
    try:
        insp = inspect(engine)
        if not insp.has_table("pending_commands"):
            return
        cols = {c["name"] for c in insp.get_columns("pending_commands")}
        if "delivered_at" in cols:
            return
        ddl = (
            "ALTER TABLE pending_commands ADD COLUMN delivered_at TIMESTAMPTZ"
            if engine.dialect.name == "postgresql"
            else "ALTER TABLE pending_commands ADD COLUMN delivered_at DATETIME"
        )
        with engine.begin() as conn:
            conn.execute(text(ddl))
    except Exception:
        pass
