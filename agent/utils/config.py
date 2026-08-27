import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

progdata_env = Path(r"C:\ProgramData\ParentalControl\.env")
if progdata_env.exists():
    load_dotenv(dotenv_path=progdata_env, override=True)

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)


def _require(key: str, description: str) -> str:
    """Lấy biến môi trường bắt buộc. Dừng chương trình nếu thiếu."""
    value = os.getenv(key, "").strip()
    if not value:
        print(f"\n❌ LỖI CẤU HÌNH: Biến '{key}' ({description}) chưa được đặt trong file .env")
        print(f"   → Hãy mở file {ENV_PATH} và thêm: {key}=<giá trị của bạn>")
        print("   → Xem file .env.example để biết mẫu\n")
        sys.exit(1)
    return value


def _optional(key: str, default: str = "") -> str:
    """Lấy biến môi trường tùy chọn."""
    return os.getenv(key, default).strip() or default


# === Cấu hình kết nối (bắt buộc cấu hình qua .env) ===
BACKEND_URL       = _require("BACKEND_URL", "URL của Backend API (vd: https://nguyentruclam.io.vn)")
WS_URL            = _require("WS_URL", "URL của WebSocket (vd: wss://nguyentruclam.io.vn)")
BACKUP_SERVER_URL = _optional("BACKUP_SERVER_URL", "https://nguyentruclam.io.vn")

# === Cấu hình xác thực & định danh ===
API_KEY     = _optional("API_KEY",     "732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7")
DEVICE_NAME = _optional("DEVICE_NAME", "May_Con")

# === Cấu hình tùy chọn ===
AGENT_PASSWORD     = _optional("AGENT_PASSWORD", "")
TELEGRAM_BOT_TOKEN = _optional("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = _optional("TELEGRAM_CHAT_ID", "")

# === Cảnh báo nếu thiếu mật khẩu agent ===
if not AGENT_PASSWORD:
    logger.warning(
        "AGENT_PASSWORD chưa được đặt — màn hình khóa chỉ có thể mở bằng xác thực từ Backend."
    )

# === Thời gian đồng bộ (giây) ===
try:
    SEND_INTERVAL = int(os.getenv("SEND_INTERVAL", "5"))
except (ValueError, TypeError):
    SEND_INTERVAL = 5

# === Múi giờ Việt Nam (UTC+7) ===
from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))


def get_vn_now() -> datetime:
    """Trả về thời gian hiện tại theo múi giờ Việt Nam (UTC+7)."""
    return datetime.now(timezone.utc).astimezone(VN_TZ)


# === Phiên bản Agent (single source of truth) ===
# The build writes version.json (AGENT_VERSION) to backend storage; the installer
# copies it to the install dir (C:\ProgramData\ParentalControl\version.json).
# Reading that file at runtime keeps reports/updater consistent with the build.
import json as _json

# Fallback only used if the installer-written version.json is missing.
DEFAULT_AGENT_VERSION = "v0011"


def get_agent_version() -> str:
    """Return the installed agent version (reads the installer-written version.json)."""
    candidates = [
        Path(r"C:\ProgramData\ParentalControl\version.json"),
        Path(os.environ.get("APPDATA", "C:\\")) / "ParentalControl" / "version.json",
        Path(r"C:\ProgramData\ParentalControl\updates\version.json"),
        Path(os.environ.get("APPDATA", "C:\\")) / "ParentalControl" / "updates" / "version.json",
    ]
    for p in candidates:
        try:
            if p.exists():
                v = _json.loads(p.read_text(encoding="utf-8")).get("version")
                if v:
                    return str(v)
        except Exception:
            continue
    return DEFAULT_AGENT_VERSION
