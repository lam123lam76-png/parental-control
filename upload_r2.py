"""
upload_r2.py — Upload agent-update.zip + version.json to Cloudflare R2 via S3 API.

Cách dùng:
  python upload_r2.py --access-key <AK> --secret-key <SK> [--account-id af2303db4db239ca215302615d46a101] [--bucket parental-control-updates]

Cần tạo R2 API token: Cloudflare Dashboard -> R2 -> Manage R2 API Tokens
  -> Create API Token -> chọn quyền Read/Write cho bucket này.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BUCKET = "parental-control-updates"
DEFAULT_ACCOUNT = "af2303db4db239ca215302615d46a101"
UPDATES_DIR = Path(__file__).resolve().parent / "backend_api" / "storage" / "updates"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--access-key", required=True)
    parser.add_argument("--secret-key", required=True)
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT)
    parser.add_argument("--bucket", default=BUCKET)
    args = parser.parse_args()

    zip_path = UPDATES_DIR / "agent-update.zip"
    version_path = UPDATES_DIR / "version.json"
    if not zip_path.exists():
        print(f"❌ Không tìm thấy {zip_path}")
        sys.exit(1)

    version = "unknown"
    try:
        version = json.loads(version_path.read_text(encoding="utf-8")).get("version", "unknown")
    except Exception:
        pass

    # Compute SHA-256 of the zip so agents can verify the package before running it
    # (Task 10). Stored in version.json and delivered with the force_update payload.
    import hashlib
    print(f"Computing SHA-256 of {zip_path.name} ...")
    h = hashlib.sha256()
    with open(zip_path, "rb") as zf:
        for chunk in iter(lambda: zf.read(1 << 20), b""):
            h.update(chunk)
    sha256 = h.hexdigest()
    try:
        vd = json.loads(version_path.read_text(encoding="utf-8"))
    except Exception:
        vd = {}
    vd["sha256"] = sha256
    version_path.write_text(json.dumps(vd, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"SHA-256: {sha256}")

    print(f"Uploading agent-update.zip ({zip_path.stat().st_size/1e6:.1f} MB) version {version} ...")

    import boto3
    from botocore.config import Config

    endpoint = f"https://{args.account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=args.access_key,
        aws_secret_access_key=args.secret_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )

    for key, path, ctype in [
        ("agent-update.zip", zip_path, "application/zip"),
        ("version.json", version_path, "application/json"),
    ]:
        s3.upload_file(str(path), args.bucket, key, ExtraArgs={"ContentType": ctype})
        print(f"  ✅ {key} -> s3://{args.bucket}/{key}")

    print("\n✅ Upload R2 hoàn tất!")
    print(f"   Public URL: https://pub-68ac9fad65e94c8f886542276f2e490c.r2.dev/version.json")


if __name__ == "__main__":
    main()
