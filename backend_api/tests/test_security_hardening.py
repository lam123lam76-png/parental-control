"""Regression tests for the leaked-credential cleanup (2026-09-14).

Every literal below was published in this public repository and was live on
production. They must never come back: the default JWT secret let anyone forge a
system-admin token, the default admin password was both a web login and the
screen-unlock "master password", the hardcoded bot token handed over the Telegram
bot, and the static API key was mapped to system admin (so its holder could
publish a malicious agent update = RCE on every child PC).
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("JWT_SECRET_KEY", "unit-test-secret-value-0123456789")

from core import security  # noqa: E402

LEAKED_JWT_DEFAULT = "PMQL_JWT_SECRET_KEY_CHANGE_ME_IN_PROD"
LEAKED_API_KEY_DEFAULT = "PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"
LEAKED_ADMIN_PASSWORD = "Truc@1905s"
LEAKED_BOT_TOKEN = "8838573041:AAFhpXyKVZib1_Y0wv29At1JlkiC1F-V-w4"
LEGACY_STATIC_API_KEY = "732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7"

# Mọi token bot từng bị hardcode ở đâu đó trong repo/bundle web.
LEAKED_BOT_TOKENS = [
    "8838573041:AAFhpXyKVZib1_Y0wv29At1JlkiC1F-V-w4",
    "8791493245:AAGzaUQiS5XiLlsUt9xjBQZqh-OM2zb1rv4",
    "8754890738:AAEGB2dZCXJzlQ-Bzk1zwN3n2HLxAyj8imA",
]

SOURCE_GLOBS = [
    (REPO_ROOT / "agent", "**/*.py"),
    (BACKEND_DIR / "core", "*.py"),
    (BACKEND_DIR / "routers", "*.py"),
    (BACKEND_DIR / "api", "*.py"),
    (REPO_ROOT / "manager-web" / "src", "**/*.js"),
    (REPO_ROOT / "manager-web" / "src", "**/*.jsx"),
    (REPO_ROOT / "docs", "*.md"),
    (REPO_ROOT, "*.py"),
    (REPO_ROOT, "*.md"),
    (REPO_ROOT, "*.bat"),
]


SOURCE_DIRS = [
    BACKEND_DIR / "core",
    BACKEND_DIR / "routers",
    BACKEND_DIR / "api",
    REPO_ROOT / "agent",  # rglob → phủ cả communication/, enforcement/, protection/, utils/, local_store/
    REPO_ROOT / "manager-web" / "src",
    REPO_ROOT / "docs",
    REPO_ROOT,  # script/tài liệu ở gốc repo
]
SOURCE_SUFFIXES = (".py", ".js", ".jsx", ".md")


def _source_files():
    seen = set()
    for base, pattern in SOURCE_GLOBS:
        if base.exists():
            for path in base.glob(pattern):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    yield path


@pytest.mark.parametrize(
    "literal",
    [LEAKED_JWT_DEFAULT, LEAKED_API_KEY_DEFAULT, LEAKED_ADMIN_PASSWORD] + LEAKED_BOT_TOKENS,
)
def test_leaked_literal_is_gone_from_source(literal):
    offenders = [str(p) for p in _source_files() if literal in p.read_text(encoding="utf-8", errors="ignore")]
    assert offenders == [], f"{literal!r} vẫn còn trong: {offenders}"


def test_static_api_key_only_lives_in_security_module():
    """The agent key must not be shipped in the agent or inlined into the web.

    It is still accepted by the backend as a legacy credential until agent v0032
    (which authenticates with its own device secret_token) is deployed, so it is
    allowed in exactly one file, clearly documented, and nowhere else.
    """
    allowed = {BACKEND_DIR / "core" / "security.py"}
    offenders = [
        str(p)
        for p in _source_files()
        if LEGACY_STATIC_API_KEY in p.read_text(encoding="utf-8", errors="ignore") and p not in allowed
    ]
    assert offenders == [], f"API key tĩnh bị phát tán tới: {offenders}"


def test_all_static_keys_map_to_a_non_admin_identity():
    assert security.VALID_API_KEYS, "phải có ít nhất 1 key tĩnh để agent v0031 còn chạy"
    for key in security.VALID_API_KEYS:
        user = asyncio.run(security.get_current_user(api_key_header=f"Bearer {key}", db=None))
        assert user["is_system_admin"] is False
        assert user["role"] not in ("admin", "system")
        assert user["permissions"]["can_manage_users"] is False
        assert user["permissions"]["can_remote_control"] is False


def test_static_key_cannot_publish_an_agent_update():
    """require_system_admin is what guards force-update-all / r2-presign / pack-zip."""
    for key in security.VALID_API_KEYS:
        user = asyncio.run(security.get_current_user(api_key_header=key, db=None))
        with pytest.raises(HTTPException) as exc:
            asyncio.run(security.require_system_admin(user=user))
        assert exc.value.status_code == 403


def test_config_never_uses_a_shipped_jwt_secret():
    from core import config

    assert config.JWT_SECRET_KEY != LEAKED_JWT_DEFAULT
    assert len(config.JWT_SECRET_KEY) >= 32


def test_default_admin_password_is_not_shipped():
    from core import config

    assert config.SYSTEM_ADMIN_PASSWORD != LEAKED_ADMIN_PASSWORD


# --------------------------------------------------------------------------- #
# Mật khẩu rỗng — lỗ hổng có thật: DB giữ hash của chuỗi rỗng nên login với
# password="" trả về token system-admin hợp lệ.
# --------------------------------------------------------------------------- #
def test_login_rejects_empty_password_before_touching_the_db():
    """Chốt chặn nằm TRƯỚC truy vấn DB nên test này không cần database."""
    from fastapi.testclient import TestClient

    import main

    client = TestClient(main.app)
    for password in ("", "   "):
        resp = client.post(
            "/api/auth/login",
            json={"email": "admin@nguyentruclam.io.vn", "password": password},
        )
        assert resp.status_code == 401, f"{password!r} phải bị từ chối, nhận {resp.status_code}"
        assert "access_token" not in resp.text


def test_auth_module_guards_against_empty_passwords():
    """Cả /api/auth/login và /api/pair đều phải có chốt chặn mật khẩu rỗng."""
    auth_src = (BACKEND_DIR / "routers" / "auth.py").read_text(encoding="utf-8")
    assert "not login_data.password" in auth_src
    assert "not request.parent_password" in auth_src


def test_seed_never_rewrites_the_admin_password_with_an_empty_value():
    """Startup seeding không được ghi lại hash("") (đó là cách lỗ hổng tái sinh)."""
    src = (BACKEND_DIR / "main.py").read_text(encoding="utf-8")
    assert 'verify("", user.password_hash)' in src, "phải kiểm tra hash chuỗi rỗng"
    assert "if WEB_ADMIN_PASSWORD:" in src, "chỉ ghi khi có mật khẩu web thật"
    assert "user.password_hash = _ctx2.hash(SYSTEM_ADMIN_PASSWORD)" not in src, (
        "seeder không được lấy mật khẩu MỞ MÁY CON làm mật khẩu web"
    )


# --------------------------------------------------------------------------- #
# Hai loại mật khẩu tách biệt (yêu cầu nghiệp vụ)
#   - mật khẩu WEB        -> đăng nhập quản trị, KHÔNG mở khoá máy con
#   - mật khẩu MỞ MÁY CON -> CHỈ mở khoá màn hình máy con, KHÔNG vào web
# --------------------------------------------------------------------------- #
def test_web_login_never_accepts_the_unlock_password():
    """login_user không được dùng mật khẩu mở máy con (nếu không lại thành 1 mật khẩu).

    Chỉ soi phần CODE, bỏ docstring — docstring có nhắc tên biến để giải thích.
    """
    import ast

    src = (BACKEND_DIR / "routers" / "auth.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "login_user"
    )
    # Bỏ docstring (biểu thức chuỗi đầu tiên) rồi mới kiểm tra tên biến được dùng.
    body = [n for n in fn.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
    code = "\n".join(ast.unparse(node) for node in body)
    for forbidden in ("MASTER_UNLOCK_PASSWORD", "SYSTEM_ADMIN_PASSWORD", "WEB_ADMIN_PASSWORD"):
        assert forbidden not in code, f"login_user không được dùng {forbidden}"
    assert "pwd_context.verify" in code, "login phải kiểm tra hash trong DB"


def test_unlock_endpoint_accepts_both_password_kinds():
    """verify-password nhận mật khẩu mở máy (env) và mật khẩu tài khoản (hash trong DB)."""
    src = (BACKEND_DIR / "routers" / "auth.py").read_text(encoding="utf-8")
    unlock_body = src.split("def verify_parent_password", 1)[1]
    assert "MASTER_UNLOCK_PASSWORD" in unlock_body, "phải nhận mật khẩu mở máy con"
    assert "pwd_context.verify(request.password" in unlock_body, "phải nhận mật khẩu tài khoản"
    assert "compare_digest" in unlock_body, "so sánh theo thời gian hằng định"


def test_unlock_password_comes_from_either_env_name(monkeypatch):
    """Hai tên biến đều được nhận; tên cũ vẫn tương thích."""
    import importlib

    from core import config

    monkeypatch.setenv("MASTER_UNLOCK_PASSWORD", "unlock-A")
    monkeypatch.setenv("SYSTEM_ADMIN_PASSWORD", "legacy-B")
    reloaded = importlib.reload(config)
    assert reloaded.MASTER_UNLOCK_PASSWORD == "unlock-A"
    assert reloaded.SYSTEM_ADMIN_PASSWORD == "unlock-A"

    monkeypatch.delenv("MASTER_UNLOCK_PASSWORD", raising=False)
    reloaded = importlib.reload(config)
    assert reloaded.MASTER_UNLOCK_PASSWORD == "legacy-B"

    monkeypatch.delenv("SYSTEM_ADMIN_PASSWORD", raising=False)
    reloaded = importlib.reload(config)
    assert reloaded.MASTER_UNLOCK_PASSWORD == ""
