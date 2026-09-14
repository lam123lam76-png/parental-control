"""Cloudflare R2 release storage for the remote Agent updater (S3 SigV4, no boto3).

WHY THIS MODULE
---------------
The "Đóng gói & Cập nhật Agent từ xa" flow used to write the release package
(`agent-update.zip`) and `version.json` to the BACKEND's local disk and serve
them from `/static/updates/*`. On Vercel that disk is ephemeral (/tmp) and
read-only everywhere else, so:

  * `POST /api/v1/agent/pack-zip`  -> 500 "Agent directory not found" (the repo's
    `agent/` folder is not part of a backend-only deployment);
  * `GET /api/v1/agent/version`    -> returned the v0001 fallback while the real
    published build was v0031 (observed live);
  * `/static/updates/agent-update.zip` -> 404 on every cold instance.

R2 is now the single source of truth. The web uploads the zip that
`build_and_pack_agent.bat` produced STRAIGHT to the bucket with a presigned PUT
URL (the 43 MB never passes through a 4.5 MB-limited Vercel function), and the
backend only writes the tiny `version.json` (carrying the SHA-256 the browser
computed) once the upload finished.

No boto3 on purpose: SigV4 presigning is a few dozen lines of hmac/hashlib and
keeps the serverless cold start small — same reasoning as
`core/supabase_storage.py`, which talks plain HTTP for the same reason.
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

# Bucket coordinates. Account id / bucket / public domain are not secrets and are
# already the ones used by build_and_pack_agent.bat + upload_r2.py, so they are
# defaulted here and only the API token needs to be provided (Vercel env).
ZIP_KEY = "agent-update.zip"
VERSION_KEY = "version.json"

DEFAULT_ACCOUNT_ID = "af2303db4db239ca215302615d46a101"
DEFAULT_BUCKET = "parental-control-updates"
DEFAULT_PUBLIC_BASE = "https://pub-68ac9fad65e94c8f886542276f2e490c.r2.dev"


def _account_id() -> str:
    return os.getenv("R2_ACCOUNT_ID", DEFAULT_ACCOUNT_ID).strip() or DEFAULT_ACCOUNT_ID


def _bucket() -> str:
    return os.getenv("R2_BUCKET", DEFAULT_BUCKET).strip() or DEFAULT_BUCKET


def _region() -> str:
    # R2 accepts "auto" in the SigV4 credential scope (upload_r2.py uses
    # region_name="auto" with boto3 for the same bucket).
    return os.getenv("R2_REGION", "auto").strip() or "auto"


def _access_key() -> str:
    return os.getenv("R2_ACCESS_KEY", "").strip()


def _secret_key() -> str:
    return os.getenv("R2_SECRET_KEY", "").strip()


def public_base() -> str:
    return os.getenv("R2_PUBLIC_BASE", DEFAULT_PUBLIC_BASE).strip().rstrip("/") or DEFAULT_PUBLIC_BASE


def _s3_host() -> str:
    return f"{_account_id()}.r2.cloudflarestorage.com"


def is_configured() -> bool:
    """True when the R2 API token is present (the only thing that is secret)."""
    return bool(_access_key() and _secret_key())


def bucket_name() -> str:
    return _bucket()


def account_id() -> str:
    return _account_id()


def public_url(key: str) -> str:
    return f"{public_base()}/{key}"


# --------------------------------------------------------------------------- #
# SigV4 primitives
# --------------------------------------------------------------------------- #
def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret_key: str, datestamp: str, region: str) -> bytes:
    k = _hmac(("AWS4" + secret_key).encode("utf-8"), datestamp)
    k = _hmac(k, region)
    k = _hmac(k, "s3")
    return _hmac(k, "aws4_request")


def _quote(value: str) -> str:
    return quote(str(value), safe="-_.~")


def _canonical_uri(path: str) -> str:
    """URI-encode a path but keep the '/' separators (S3 canonical form)."""
    return quote(path, safe="/-_.~")


def _canonical_query(params: dict) -> str:
    return "&".join(f"{_quote(k)}={_quote(v)}" for k, v in sorted(params.items()))


def sign_presigned_url(
    method: str,
    host: str,
    path: str,
    *,
    access_key: str,
    secret_key: str,
    region: str,
    amz_date: str,
    datestamp: str,
    expires: int,
    payload_hash: str = "UNSIGNED-PAYLOAD",
) -> str:
    """Build a presigned S3/R2 URL. Pure function so it can be tested against the
    AWS documentation vector (see backend_api/tests/test_r2_sigv4.py)."""
    scope = f"{datestamp}/{region}/s3/aws4_request"
    params = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{access_key}/{scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(int(expires)),
        "X-Amz-SignedHeaders": "host",
    }
    canonical_request = "\n".join([
        method.upper(),
        _canonical_uri(path),
        _canonical_query(params),
        f"host:{host}\n",
        "host",
        payload_hash,
    ])
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        scope,
        _sha256_hex(canonical_request.encode("utf-8")),
    ])
    signature = hmac.new(
        _signing_key(secret_key, datestamp, region),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        f"https://{host}{_canonical_uri(path)}"
        f"?{_canonical_query(params)}&X-Amz-Signature={signature}"
    )


def presign_put(key: str, expires: int = 900) -> str:
    """Presigned PUT URL for the browser (no CORS-free alternative exists: the
    file is ~43 MB, far above Vercel's 4.5 MB function body limit, so it cannot
    be proxied through the backend)."""
    if not is_configured():
        raise RuntimeError(
            "R2 chưa được cấu hình trên server (thiếu R2_ACCESS_KEY / R2_SECRET_KEY)."
        )
    now = datetime.now(timezone.utc)
    return sign_presigned_url(
        "PUT",
        _s3_host(),
        f"/{_bucket()}/{key}",
        access_key=_access_key(),
        secret_key=_secret_key(),
        region=_region(),
        amz_date=now.strftime("%Y%m%dT%H%M%SZ"),
        datestamp=now.strftime("%Y%m%d"),
        expires=expires,
    )


def _signed_request(method: str, path: str, *, body: bytes = b"", content_type=None, query=None):
    """Signed (not presigned) request, used for the small server-side writes."""
    if not is_configured():
        raise RuntimeError(
            "R2 chưa được cấu hình trên server (thiếu R2_ACCESS_KEY / R2_SECRET_KEY)."
        )
    host = _s3_host()
    region = _region()
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    scope = f"{datestamp}/{region}/s3/aws4_request"
    payload_hash = _sha256_hex(body)

    headers = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    if content_type:
        headers["content-type"] = content_type

    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(f"{k}:{headers[k].strip()}\n" for k in sorted(headers))
    canonical_query = _canonical_query(query or {})
    canonical_request = "\n".join([
        method.upper(),
        _canonical_uri(path),
        canonical_query,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        scope,
        _sha256_hex(canonical_request.encode("utf-8")),
    ])
    signature = hmac.new(
        _signing_key(_secret_key(), datestamp, region),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    url = f"https://{host}{_canonical_uri(path)}"
    if canonical_query:
        url = f"{url}?{canonical_query}"
    send_headers = {k: v for k, v in headers.items() if k != "host"}
    send_headers["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={_access_key()}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return requests.request(method, url, data=body or None, headers=send_headers, timeout=60)


# --------------------------------------------------------------------------- #
# Release metadata
# --------------------------------------------------------------------------- #
def upload_version_json(data: dict) -> dict:
    """Publish `version.json` — the release pointer every agent reads."""
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    resp = _signed_request(
        "PUT",
        f"/{_bucket()}/{VERSION_KEY}",
        body=body,
        content_type="application/json",
    )
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"R2 từ chối ghi version.json (HTTP {resp.status_code}): {resp.text[:300]}")
    return data


def fetch_version_json(timeout: int = 15) -> dict | None:
    """Read the published release pointer straight from the public bucket URL."""
    try:
        resp = requests.get(public_url(VERSION_KEY), timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"[r2] version.json HTTP {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        logger.warning(f"[r2] could not read version.json: {e}")
        return None


def object_size(key: str, timeout: int = 15) -> int | None:
    """Content-Length of a published object (None when it does not exist)."""
    try:
        resp = requests.head(public_url(key), timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        return int(resp.headers.get("Content-Length") or 0)
    except Exception as e:
        logger.warning(f"[r2] HEAD {key} failed: {e}")
        return None


# --------------------------------------------------------------------------- #
# One-time bucket setup
# --------------------------------------------------------------------------- #
def get_bucket_cors() -> str | None:
    """Current CORS policy XML of the bucket (None when no policy is set)."""
    resp = _signed_request("GET", f"/{_bucket()}", query={"cors": ""})
    if resp.status_code == 200:
        return resp.text
    if resp.status_code == 404:
        return None
    raise RuntimeError(f"R2 không đọc được CORS (HTTP {resp.status_code}): {resp.text[:300]}")


def set_bucket_cors(origins: list[str], max_age: int = 3600) -> None:
    """Allow the web app to PUT the release zip straight into the bucket.

    A browser upload to R2 needs a CORS policy on the bucket; without it the
    upload fails (the browser refuses to hand the response back). Applying it
    from here means the whole setup is one click instead of a dashboard trip.
    """
    rules = "".join(
        f"<AllowedOrigin>{origin}</AllowedOrigin>"
        for origin in origins
        if origin and origin.strip()
    )
    body = (
        "<CORSConfiguration><CORSRule>"
        f"{rules}"
        "<AllowedMethod>PUT</AllowedMethod>"
        "<AllowedMethod>GET</AllowedMethod>"
        "<AllowedMethod>HEAD</AllowedMethod>"
        "<AllowedHeader>*</AllowedHeader>"
        "<ExposeHeader>ETag</ExposeHeader>"
        f"<MaxAgeSeconds>{int(max_age)}</MaxAgeSeconds>"
        "</CORSRule></CORSConfiguration>"
    ).encode("utf-8")
    resp = _signed_request(
        "PUT",
        f"/{_bucket()}",
        body=body,
        content_type="application/xml",
        query={"cors": ""},
    )
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"R2 từ chối CORS (HTTP {resp.status_code}): {resp.text[:300]}")
