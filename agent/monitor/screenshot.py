"""
screenshot.py v4 — Chụp màn hình tối ưu chuẩn WebP & Thread-Safe (Local-First Architecture).
Chuyển đổi sang định dạng WebP (quality=80) giúp giảm 40-50% dung lượng storage & bandwidth.
"""
import io
import threading
from datetime import datetime, timezone
from typing import Optional

from mss import mss
from PIL import Image, ImageDraw, ImageChops
from utils.config import DEVICE_NAME
from utils.logger import log_debug

# BẢO VỆ THREAD-SAFE CHO _previous_thumbnail
_previous_thumbnail: Optional[Image.Image] = None
_lock = threading.Lock()

# NGƯỠNG THAY ĐỔI: 5% pixel khác biệt mới upload
DIFF_THRESHOLD: float = 0.05
COMPARE_SIZE: tuple[int, int] = (320, 180)
PIXEL_TOLERANCE: int = 30


def _get_font(size: int = 36):
    """Thử nhiều font phổ biến trên Windows + Linux để nạp font chuẩn cross-platform."""
    font_paths = [
        "arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for fp in font_paths:
        try:
            from PIL import ImageFont
            return ImageFont.truetype(fp, size)
        except Exception:
            pass
    try:
        from PIL import ImageFont
        return ImageFont.load_default()
    except Exception:
        return None


def _compute_change_ratio(current: Image.Image, previous: Image.Image) -> float:
    """So sánh 2 ảnh bằng pixel diff. Trả về tỉ lệ pixel thay đổi (0.0 ~ 1.0)."""
    try:
        cur_small = current.resize(COMPARE_SIZE)
        prev_small = previous.resize(COMPARE_SIZE)

        diff = ImageChops.difference(cur_small, prev_small)
        diff_pixels = diff.getdata()

        changed = 0
        total = len(diff_pixels)
        for pixel in diff_pixels:
            if max(pixel) > PIXEL_TOLERANCE:
                changed += 1

        return changed / total if total > 0 else 0.0
    except Exception as e:
        log_debug(f"[ERR] Image diff calculation failed: {e}")
        return 1.0


def has_significant_change(current_img: Image.Image) -> bool:
    """
    Thao tác thread-safe kiểm tra ảnh hiện tại có thay đổi đáng kể so với ảnh trước đó không.
    """
    global _previous_thumbnail

    with _lock:
        if _previous_thumbnail is None:
            _previous_thumbnail = current_img.copy()
            return True

        ratio = _compute_change_ratio(current_img, _previous_thumbnail)

        if ratio > DIFF_THRESHOLD:
            _previous_thumbnail = current_img.copy()
            return True

        return False


def take_screenshot(force_upload: bool = False) -> tuple[bytes, bool]:
    """
    Chụp toàn bộ tất cả màn hình (hỗ trợ đa màn hình mss), nén chuẩn WEBP (quality=80).
    
    Returns:
        tuple[bytes, bool]: (image_bytes, should_upload)
    """
    try:
        with mss() as sct:
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)

            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.thumbnail((1920, 1080))

            # Vẽ Timestamp màu xanh neon lên ảnh
            draw = ImageDraw.Draw(img)
            time_str = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
            font = _get_font(36)

            x, y = 25, 25
            if font:
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), time_str, fill="black", font=font)
                draw.text((x, y), time_str, fill="#00ff00", font=font)

            # Kiểm tra thay đổi bằng Image Diff (Thread-Safe)
            should_upload = force_upload or has_significant_change(img)

            # Đóng gói thành byte WEBP quality=80 (Tiết kiệm 50% dung lượng so với JPEG)
            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=80)
            buffer.seek(0)

            return buffer.getvalue(), should_upload
    except Exception as e:
        log_debug(f"[ERR] mss take_screenshot exception: {e}")
        raise e


def make_screenshot_filename() -> str:
    """Tạo tên file screenshot theo UTC timestamp với đuôi .webp."""
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{DEVICE_NAME}/{now}.webp"


def queue_screenshot(supabase, db, force: bool = False) -> None:
    """
    HÀM CHUNG CHO CẢ AUTO MODE & INSTANT MODE (LOCAL-FIRST):
    1. Chụp ảnh WEBP -> 2. Check Image Diff -> 3. Upload Storage -> 4. Ghi pending_logs cho SyncWorker.
    """
    try:
        image_bytes, should_upload = take_screenshot(force_upload=force)
        if not should_upload:
            print("[SCREENSHOT] Không có thay đổi đáng kể (> 5%), bỏ qua upload.")
            return

        filename = make_screenshot_filename()

        # 1. Upload binary file WEBP lên Supabase Storage & Cập nhật Heartbeat tức thì
        if supabase:
            try:
                supabase.storage.from_("screenshots").upload(
                    path=filename,
                    file=image_bytes,
                    file_options={"content-type": "image/webp", "upsert": "true"}
                )
                print(f"[SCREENSHOT] Đã upload Storage WebP: {filename}")

                # Cập nhật ngay last_seen để Web App giữ màu xanh
                now_iso = datetime.now(timezone.utc).isoformat()
                supabase.table("devices").upsert({
                    "device_name": DEVICE_NAME,
                    "last_seen": now_iso,
                    "is_online": True
                }, on_conflict="device_name").execute()
            except Exception as se:
                log_debug(f"[ERR] Supabase storage WebP upload failed: {se}")

        # 2. Luôn ghi record vào pending_logs (Local-First SQLite) để SyncWorker đẩy vào screenshot_logs
        db.add_pending_log("screenshot", {
            "device_name": DEVICE_NAME,
            "file_path": filename
        })
        print(f"[SCREENSHOT] Đã ghi pending_logs WebP screenshot: {filename}")

    except Exception as e:
        log_debug(f"[ERR] queue_screenshot failed: {e}")
        raise e
