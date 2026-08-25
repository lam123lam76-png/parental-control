import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

SUPABASE_DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL")

supabase_engine = None
SupabaseSessionLocal = None

if SUPABASE_DATABASE_URL:
    try:
        supabase_engine = create_engine(
            SUPABASE_DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        SupabaseSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=supabase_engine)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase engine: {e}")

def get_supabase_db():
    if not SupabaseSessionLocal:
        return None
    db = SupabaseSessionLocal()
    try:
        yield db
    finally:
        db.close()

def push_to_supabase(local_db):
    if not SupabaseSessionLocal:
        return
    supabase_db = SupabaseSessionLocal()
    try:
        logger.info("Starting sync push to Supabase...")
        pass
    except Exception as e:
        logger.error(f"Error pushing to Supabase: {e}")
    finally:
        supabase_db.close()

def pull_from_supabase(local_db):
    if not SupabaseSessionLocal:
        return
    supabase_db = SupabaseSessionLocal()
    try:
        logger.info("Starting sync pull from Supabase...")
        pass
    except Exception as e:
        logger.error(f"Error pulling from Supabase: {e}")
    finally:
        supabase_db.close()

async def periodic_sync_task(local_db_session_factory):
    if not SupabaseSessionLocal:
        logger.info("No SUPABASE_DATABASE_URL configured. Sync disabled.")
        return
    import asyncio
    while True:
        try:
            local_db = local_db_session_factory()
            try:
                pull_from_supabase(local_db)
                push_to_supabase(local_db)
            finally:
                local_db.close()
        except Exception as e:
            logger.error(f"Periodic sync error: {e}")
        await asyncio.sleep(600)
