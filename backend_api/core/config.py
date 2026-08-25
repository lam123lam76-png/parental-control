import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / ".env")


def _writable_storage_dir() -> Path:
    """Pick a writable storage root.

    Locally this is PROJECT_ROOT/storage. On serverless runtimes (Vercel) the
    deploy dir /var/task is read-only, so fall back to the OS temp dir (writable,
    ephemeral). Probes with a real write to make sure mkdir alone is not enough.
    """
    candidates = []
    # Local default first: keep the normal backend_api/storage layout.
    candidates.append(PROJECT_ROOT / "storage")
    env_path = os.getenv("STORAGE_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path(tempfile.gettempdir()) / "pc_storage")
    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            probe = cand / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return cand
        except Exception:
            continue
    return PROJECT_ROOT / "storage"


STORAGE_DIR = _writable_storage_dir()
SCREENSHOTS_DIR = STORAGE_DIR / "screenshots"
UPDATES_DIR = STORAGE_DIR / "updates"
TRASH_DIR = STORAGE_DIR / "trash"
TRASH_SHOTS_DIR = TRASH_DIR / "screenshots"
TRASH_RECORDS_DIR = TRASH_DIR / "records"

# Ensure directories exist (best effort; serverless may be read-only)
for _d in (SCREENSHOTS_DIR, UPDATES_DIR, TRASH_SHOTS_DIR, TRASH_RECORDS_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

# Admin
SYSTEM_ADMIN_EMAIL = os.getenv("SYSTEM_ADMIN_EMAIL", "admin@nguyentruclam.io.vn")
SYSTEM_ADMIN_PASSWORD = os.getenv("SYSTEM_ADMIN_PASSWORD", "Truc@1905s")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "PMQL_JWT_SECRET_KEY_CHANGE_ME_IN_PROD")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
