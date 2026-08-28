"""Supabase Storage (S3-compatible) helper for screenshot persistence + quota cleanup.

Screenshots are uploaded to the Supabase Storage `screenshots` bucket (public). The
free bucket limit is 50MB, so we auto-delete the OLDEST objects when usage nears the
limit (default 47MB) down to a target (default 40MB).
"""
import os
import logging
from datetime import datetime, timezone

import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)

S3_ENDPOINT = os.getenv(
    "SUPABASE_S3_ENDPOINT",
    "https://xqscnzdghjvgdozwfdbj.supabase.co/storage/v1/s3",
)
S3_REGION = os.getenv("SUPABASE_S3_REGION", "ap-southeast-1")
S3_ACCESS_KEY = os.getenv("SUPABASE_S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("SUPABASE_S3_SECRET_KEY", "")
BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "screenshots")
PUBLIC_BASE = os.getenv(
    "SUPABASE_STORAGE_PUBLIC_BASE",
    "https://xqscnzdghjvgdozwfdbj.supabase.co/storage/v1/object/public/screenshots",
)
# Quota: if bucket total >= LIMIT_MB, delete oldest until <= TARGET_MB.
QUOTA_LIMIT_MB = float(os.getenv("SCREENSHOT_QUOTA_LIMIT_MB", "47"))
QUOTA_TARGET_MB = float(os.getenv("SCREENSHOT_QUOTA_TARGET_MB", "40"))


_client = None


def _s3():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            region_name=S3_REGION,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
    return _client


def upload_file(content: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    """Upload a screenshot to Supabase Storage; return its public URL."""
    _s3().put_object(Bucket=BUCKET, Key=filename, Body=content, ContentType=content_type)
    return f"{PUBLIC_BASE}/{filename}"


def delete_file(filename: str) -> None:
    try:
        _s3().delete_object(Bucket=BUCKET, Key=filename)
    except Exception as e:
        logger.warning(f"S3 delete failed {filename}: {e}")


def list_files():
    """Return list of (key, size, last_modified)."""
    s3 = _s3()
    out = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET):
        for obj in page.get("Contents", []):
            out.append((obj["Key"], obj["Size"], obj.get("LastModified")))
    return out


def _filename_from_url(url: str) -> str:
    """Extract the object key (filename) from a public image_url."""
    return url.rstrip("/").rsplit("/", 1)[-1]


def enforce_screenshot_quota():
    """If bucket total >= LIMIT_MB, delete OLDEST objects until total <= TARGET_MB.

    Returns the list of deleted filenames so the caller can also remove DB rows.
    """
    try:
        files = list_files()
    except Exception as e:
        logger.warning(f"S3 list failed: {e}")
        return []
    total = sum(s for _, s, _ in files)
    limit_bytes = QUOTA_LIMIT_MB * 1024 * 1024
    if total <= limit_bytes:
        return []
    # Sort oldest first by last_modified (fallback to name for missing mtime).
    files.sort(key=lambda x: (x[2] or datetime(1970, 1, 1, tzinfo=timezone.utc), x[0]))
    target_bytes = QUOTA_TARGET_MB * 1024 * 1024
    deleted = []
    while files and total > target_bytes:
        key, size, _ = files.pop(0)
        delete_file(key)
        total -= size
        deleted.append(key)
    if deleted:
        logger.info(f"Screenshot quota: deleted {len(deleted)} oldest (total now {total/1024/1024:.1f}MB)")
    return deleted
