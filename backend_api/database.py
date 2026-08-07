import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{BASE_DIR / 'data' / 'app.db'}")
API_KEY = os.getenv('API_KEY', '')
STORAGE_PATH = os.getenv('STORAGE_PATH', str(BASE_DIR / 'storage'))

DATA_DIR = BASE_DIR / 'data'
STORAGE_DIR = Path(STORAGE_PATH)

DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

engine_kwargs = {}
if DATABASE_URL.startswith('sqlite'):
    engine_kwargs['connect_args'] = {'check_same_thread': False}

engine = create_engine(DATABASE_URL, future=True, echo=False, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

from models import Base


def init_db():
    Base.metadata.create_all(bind=engine)
