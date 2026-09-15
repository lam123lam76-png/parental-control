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

# ==== HAI LOẠI MẬT KHẨU, TÁCH BIỆT HOÀN TOÀN ====
# 1. MẬT KHẨU WEB (đăng nhập quản trị): lưu dạng hash trong bảng users/parents và chỉ
#    đổi khi có người chủ động đổi — KHÔNG bao giờ bị ghi từ biến môi trường.
#    WEB_ADMIN_PASSWORD chỉ dùng để tạo tài khoản admin trên một DB hoàn toàn mới.
WEB_ADMIN_PASSWORD = os.getenv("WEB_ADMIN_PASSWORD", "").strip()

# 2. MẬT KHẨU MỞ MÁY CON: dùng ở màn hình khoá của Agent
#    (POST /api/auth/verify-password) để mở khoá máy con khẩn cấp, KHÔNG đăng nhập web.
#    Nhận cả hai tên biến: MASTER_UNLOCK_PASSWORD (tên đúng nghĩa) và
#    SYSTEM_ADMIN_PASSWORD (tên cũ, giữ để không phá cấu hình đang chạy).
#    KHÔNG có giá trị mặc định: mật khẩu mặc định cũ từng nằm công khai trong repo,
#    nghĩa là đứa trẻ tự mở khoá được máy mình.
MASTER_UNLOCK_PASSWORD = (
    os.getenv("MASTER_UNLOCK_PASSWORD", "").strip()
    or os.getenv("SYSTEM_ADMIN_PASSWORD", "").strip()
)
# Tên cũ, giữ cho code/agent đang tham chiếu.
SYSTEM_ADMIN_PASSWORD = MASTER_UNLOCK_PASSWORD

# JWT Configuration
# KHÔNG có secret mặc định. Trước đây để mặc định một chuỗi có sẵn trong repo (dạng
# PMQL_JWT_SECRET_KEY_..._IN_PROD) và production không đặt biến này, nên bất kỳ ai
# đọc repo (đang public) đều tự ký được token system-admin — đã kiểm chứng thực tế
# (HTTP 200 trên endpoint admin). Nay nếu thiếu biến môi trường thì sinh secret ngẫu
# nhiên theo tiến trình: token giả không dùng được nữa, đổi lại phiên đăng nhập hết
# hiệu lực mỗi lần instance khởi động lại — đúng hướng an toàn, kèm log báo lỗi để
# nhắc đặt biến.
_jwt_secret_env = os.getenv("JWT_SECRET_KEY", "").strip()
if _jwt_secret_env:
    JWT_SECRET_KEY = _jwt_secret_env
else:
    import logging as _logging
    import secrets as _secrets

    JWT_SECRET_KEY = _secrets.token_urlsafe(48)
    _logging.getLogger(__name__).error(
        "JWT_SECRET_KEY chưa được đặt — đang dùng secret ngẫu nhiên tạm thời cho tiến "
        "trình này (mọi phiên đăng nhập sẽ mất hiệu lực khi khởi động lại). "
        "Hãy đặt JWT_SECRET_KEY trong biến môi trường của server."
    )
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
