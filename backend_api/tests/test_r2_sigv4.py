"""SigV4 presign tests for core/r2_storage.py.

The vector is the one published in the AWS S3 documentation for presigned URLs
("Example: GET Object"): examplebucket / test.txt / 20130524T000000Z / 86400s.
If our canonical request, credential scope or signing-key chain were wrong, the
signature would not match, so this pins the algorithm without needing R2 access.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.r2_storage import sign_presigned_url  # noqa: E402

AWS_EXAMPLE = dict(
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    region="us-east-1",
    amz_date="20130524T000000Z",
    datestamp="20130524",
    expires=86400,
)
AWS_EXPECTED_SIGNATURE = (
    "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"
)


def test_matches_aws_documented_vector():
    url = sign_presigned_url(
        "GET", "examplebucket.s3.amazonaws.com", "/test.txt", **AWS_EXAMPLE
    )
    assert url.endswith(f"&X-Amz-Signature={AWS_EXPECTED_SIGNATURE}")
    assert "X-Amz-Credential=AKIAIOSFODNN7EXAMPLE%2F20130524%2Fus-east-1%2Fs3%2Faws4_request" in url
    assert "X-Amz-SignedHeaders=host" in url
    assert "X-Amz-Expires=86400" in url


def test_different_key_changes_signature():
    base = sign_presigned_url(
        "PUT", "acct.r2.cloudflarestorage.com", "/bucket/agent-update.zip", **AWS_EXAMPLE
    )
    other = sign_presigned_url(
        "PUT", "acct.r2.cloudflarestorage.com", "/bucket/other.zip", **AWS_EXAMPLE
    )
    assert base.split("X-Amz-Signature=")[1] != other.split("X-Amz-Signature=")[1]


def test_presign_put_requires_credentials(monkeypatch):
    from core import r2_storage

    monkeypatch.delenv("R2_ACCESS_KEY", raising=False)
    monkeypatch.delenv("R2_SECRET_KEY", raising=False)
    assert r2_storage.is_configured() is False
    try:
        r2_storage.presign_put(r2_storage.ZIP_KEY)
    except RuntimeError as e:
        assert "R2" in str(e)
    else:  # pragma: no cover
        raise AssertionError("presign_put must refuse to build a URL without credentials")


def test_presign_put_uses_configured_bucket(monkeypatch):
    from core import r2_storage

    monkeypatch.setenv("R2_ACCESS_KEY", "AK")
    monkeypatch.setenv("R2_SECRET_KEY", "SK")
    url = r2_storage.presign_put(r2_storage.ZIP_KEY)
    assert url.startswith(f"https://{r2_storage._s3_host()}/{r2_storage._bucket()}/agent-update.zip?")
    assert "X-Amz-Signature=" in url
