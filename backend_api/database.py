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
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,       # Seconds to wait for a connection from the pool
        pool_recycle=1800,     # Recycle connections after 30 minutes
        pool_pre_ping=True,    # Check connection health before using
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
