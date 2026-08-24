import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
PROJECT_ROOT = Path(__file__).parent.parent
STORAGE_DIR = PROJECT_ROOT / "storage"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / ".env")

SCREENSHOTS_DIR = STORAGE_DIR / "screenshots"
UPDATES_DIR = STORAGE_DIR / "updates"
TRASH_DIR = STORAGE_DIR / "trash"
TRASH_SHOTS_DIR = TRASH_DIR / "screenshots"
TRASH_RECORDS_DIR = TRASH_DIR / "records"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
UPDATES_DIR.mkdir(parents=True, exist_ok=True)
TRASH_SHOTS_DIR.mkdir(parents=True, exist_ok=True)
TRASH_RECORDS_DIR.mkdir(parents=True, exist_ok=True)

# Admin
SYSTEM_ADMIN_EMAIL = os.getenv("SYSTEM_ADMIN_EMAIL", "admin@nguyentruclam.io.vn")
SYSTEM_ADMIN_PASSWORD = os.getenv("SYSTEM_ADMIN_PASSWORD", "Truc@1905s")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "PMQL_JWT_SECRET_KEY_CHANGE_ME_IN_PROD")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
