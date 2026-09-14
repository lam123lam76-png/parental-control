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
    (BACKEND_DIR / "core", "*.py"),
    (BACKEND_DIR / "routers", "*.py"),
    (REPO_ROOT / "agent", "*.py"),
    (REPO_ROOT / "manager-web" / "src", "*.js"),
    (REPO_ROOT / "manager-web" / "src", "*.jsx"),
    (REPO_ROOT / "docs", "*.md"),
    (REPO_ROOT, "*.py"),
    (REPO_ROOT, "*.md"),
]


def _source_files():
    for base, pattern in SOURCE_GLOBS:
        if base.exists():
            yield from base.glob(pattern)


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
