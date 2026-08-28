"""Supabase Storage (REST API) helper for screenshot persistence + quota cleanup.

Screenshots are uploaded to the Supabase Storage `screenshots` bucket (public).
The free bucket limit is 50MB, so we auto-delete the OLDEST objects when usage
nears the limit (default 47MB) down to a target (default 40MB).

Uses the REST API (Authorization: Bearer service_role) — simpler/more reliable
from Vercel serverless than boto3 S3 signing.
"""
import os
import logging

import requests

logger = logging.getLogger(__name__)

PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL") or os.getenv("SUPABASE_URL") or "https://xqscnzdghjvgdozwfdbj.supabase.co"
SERVICE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SECRET_KEY")
    or ""
)
BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "screenshots")
PUBLIC_BASE = f"{PROJECT_URL}/storage/v1/object/public/{BUCKET}"
# Quota: if bucket total >= LIMIT_MB, delete oldest until <= TARGET_MB.
QUOTA_LIMIT_MB = float(os.getenv("SCREENSHOT_QUOTA_LIMIT_MB", "47"))
QUOTA_TARGET_MB = float(os.getenv("SCREENSHOT_QUOTA_TARGET_MB", "40"))


def _json_headers():
    return {"Authorization": f"Bearer {SERVICE_KEY}", "Content-Type": "application/json"}


def upload_file(content: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """Upload a screenshot to Supabase Storage; return its public URL."""
    # Supabase Storage rejects 'image/jpg' — normalize to standard MIME.
    if content_type in ("image/jpg", "image/jpe"):
        content_type = "image/jpeg"
    url = f"{PROJECT_URL}/storage/v1/object/{BUCKET}/{filename}"
    headers = {"Authorization": f"Bearer {SERVICE_KEY}", "Content-Type": content_type}
    resp = requests.post(url, data=content, headers=headers, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Storage upload failed HTTP {resp.status_code}: {resp.text[:200]}")
    return f"{PUBLIC_BASE}/{filename}"


def delete_file(filename: str) -> None:
    url = f"{PROJECT_URL}/storage/v1/object/{BUCKET}/{filename}"
    try:
        requests.delete(url, headers=_json_headers(), timeout=20)
    except Exception as e:
        logger.warning(f"Storage delete failed {filename}: {e}")


def list_files():
    """Return list of (key, size) for all objects, oldest first."""
    url = f"{PROJECT_URL}/storage/v1/object/list/{BUCKET}"
    body = {"prefix": "", "limit": 1000, "offset": 0, "sortBy": {"column": "created_at", "order": "asc"}}
    resp = requests.post(url, json=body, headers=_json_headers(), timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Storage list failed HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    out = []
    for obj in data:
        size = obj.get("metadata", {}).get("size")
        try:
            size = int(size) if size is not None else 0
        except (TypeError, ValueError):
            size = 0
        out.append((obj.get("name", ""), size))
    return out  # already sorted by created_at asc (oldest first)


def _filename_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def enforce_screenshot_quota():
    """If bucket total >= LIMIT_MB, delete OLDEST objects until total <= TARGET_MB.

    Returns the list of deleted filenames so the caller can also remove DB rows.
    """
    try:
        files = list_files()
    except Exception as e:
        logger.warning(f"Storage list failed for quota: {e}")
        return []
    total = sum(s for _, s in files)
    limit_bytes = QUOTA_LIMIT_MB * 1024 * 1024
    if total <= limit_bytes:
        return []
    target_bytes = QUOTA_TARGET_MB * 1024 * 1024
    deleted = []
    for name, size in files:
        if total <= target_bytes:
            break
        delete_file(name)
        total -= size
        deleted.append(name)
    if deleted:
        logger.info(f"Screenshot quota: deleted {len(deleted)} oldest (total now {total/1024/1024:.1f}MB)")
    return deleted
