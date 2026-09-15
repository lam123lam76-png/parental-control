"""Test: mọi thời gian gửi cho phụ huynh phải là GIỜ VIỆT NAM, không phải UTC.

Lỗi thật đã xảy ra: caption ảnh chụp gửi Telegram in thẳng giá trị UTC trong DB nên
ảnh chụp lúc 17:57 giờ VN lại hiện "10:57" — phụ huynh đọc sai giờ (lệch 7 tiếng).
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("JWT_SECRET_KEY", "unit-test-secret-value-0123456789")

from core.telegram_bot import VIETNAM_TZ, _to_vn  # noqa: E402

VN = timezone(timedelta(hours=7))


def test_vietnam_tz_is_utc_plus_7():
    assert VIETNAM_TZ.utcoffset(None) == timedelta(hours=7)


def test_to_vn_converts_utc_to_local():
    """10:57 UTC phải hiển thị 17:57 giờ VN (đúng ca lỗi đã gặp)."""
    utc_dt = datetime(2026, 9, 15, 10, 57, 22, tzinfo=timezone.utc)
    vn_dt = _to_vn(utc_dt)
    assert vn_dt.strftime("%d/%m %H:%M:%S") == "15/09 17:57:22"
    assert vn_dt.utcoffset() == timedelta(hours=7)


def test_to_vn_treats_naive_datetime_as_utc():
    """Dữ liệu cũ không có tzinfo vẫn phải được coi là UTC rồi đổi sang giờ VN."""
    naive = datetime(2026, 9, 15, 10, 57, 22)
    assert _to_vn(naive).strftime("%H:%M") == "17:57"


def test_to_vn_handles_none():
    """None -> giờ hiện tại theo VN (không crash)."""
    result = _to_vn(None)
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(hours=7)


def test_screenshot_caption_uses_vietnam_time():
    """Nguồn: caption trong cmd_shot phải đi qua _to_vn."""
    src = (BACKEND_DIR / "core" / "telegram_bot.py").read_text(encoding="utf-8")
    shot_body = src.split("def cmd_shot", 1)[1].split("def _fmt_duration", 1)[0]
    assert "_to_vn(shot.timestamp)" in shot_body, "caption ảnh phải đổi sang giờ VN"
    assert "shot.timestamp.strftime" not in shot_body, "không được in thẳng UTC"


def test_registration_expiry_uses_vietnam_time():
    """Thông báo duyệt thiết bị cũng phải theo giờ VN, không ghi 'UTC'."""
    src = (BACKEND_DIR / "core" / "telegram_approval.py").read_text(encoding="utf-8")
    assert "VIETNAM_TZ" in src
    assert "astimezone(VIETNAM_TZ)" in src
    assert "} UTC" not in src, "không hiển thị UTC cho phụ huynh"
