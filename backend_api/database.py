import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

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
