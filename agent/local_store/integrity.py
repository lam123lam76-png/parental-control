"""HMAC-SHA256 signature generation and verification for rule integrity."""

import hashlib
import hmac
import json
from typing import Any


def sign_rules(rules: list[dict[str, Any]], secret_token: str) -> str:
    """Deterministically serialize rules and return HMAC-SHA256 hex signature."""
    if not isinstance(secret_token, str):
        raise TypeError("secret_token must be a string")

    # Sanitize rules to only include fields stored in local_db to ensure HMAC matches after DB roundtrip
    allowed_keys = {"id", "rule_type", "target", "is_banned", "daily_limit_minutes", "day_of_week", "allowed_start", "allowed_end"}
    sanitized_rules = []
    for r in rules:
        sanitized_r = {k: r.get(k) for k in allowed_keys}
        # Ensure is_banned is bool for deterministic JSON serialization
        if "is_banned" in sanitized_r:
            sanitized_r["is_banned"] = bool(sanitized_r["is_banned"])
        sanitized_rules.append(sanitized_r)

    serialized = json.dumps(sanitized_rules, sort_keys=True).encode('utf-8')
    key = secret_token.encode('utf-8')
    return hmac.new(key, serialized, hashlib.sha256).hexdigest()


def verify_rules(rules: list[dict[str, Any]], hmac_hex: str, secret_token: str) -> bool:
    """Recompute rule signature and compare with provided hmac_hex using constant-time comparison."""
    if not hmac_hex or not secret_token or not isinstance(hmac_hex, str):
        return False

    try:
        expected_hmac = sign_rules(rules, secret_token)
        return hmac.compare_digest(expected_hmac.lower(), hmac_hex.lower())
    except Exception:
        return False
