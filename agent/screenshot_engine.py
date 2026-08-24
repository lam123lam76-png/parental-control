"""
screenshot_engine.py — Screenshot Capture & Upload Engine for Agent Phase 3
"""

import datetime
import io
import logging
import os

import requests
from PIL import Image, ImageDraw, ImageFont

try:
    from utils.config import API_KEY
except Exception:
    API_KEY = os.getenv("API_KEY", "732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7")

try:
    import mss
except ImportError:
    mss = None

logger = logging.getLogger("ScreenshotEngine")


class ScreenshotEngine:
    """Handles full-screen capture, timestamp overlay, and backend upload."""

    def __init__(self, device_id: str, backend_url: str, secret_token: str = None):
        self.device_id = device_id
        self.backend_url = backend_url.rstrip("/")
        self.secret_token = secret_token

    def _ctypes_gdi_capture(self) -> Image.Image | None:
        """Capture full screen using pure Windows GDI BitBlt via ctypes."""
        if os.name != 'nt':
            return None
        try:
            import ctypes
            import ctypes.wintypes
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            x = user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN
            y = user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN
            w = user32.GetSystemMetrics(78) # SM_CXVIRTUALSCREEN
            h = user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN
            if w <= 0 or h <= 0:
                return None
            hdc = user32.GetDC(0)
            if not hdc:
                return None
            memdc = gdi32.CreateCompatibleDC(hdc)
            hbmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
            oldbmp = gdi32.SelectObject(memdc, hbmp)
            
            success = gdi32.BitBlt(memdc, 0, 0, w, h, hdc, x, y, 0x00CC0020)
            if not success:
                gdi32.SelectObject(memdc, oldbmp)
                gdi32.DeleteObject(hbmp)
                gdi32.DeleteDC(memdc)
                user32.ReleaseDC(0, hdc)
                return None
            
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', ctypes.wintypes.DWORD),
                    ('biWidth', ctypes.wintypes.LONG),
                    ('biHeight', ctypes.wintypes.LONG),
                    ('biPlanes', ctypes.wintypes.WORD),
                    ('biBitCount', ctypes.wintypes.WORD),
                    ('biCompression', ctypes.wintypes.DWORD),
                    ('biSizeImage', ctypes.wintypes.DWORD),
                    ('biXPelsPerMeter', ctypes.wintypes.LONG),
                    ('biYPelsPerMeter', ctypes.wintypes.LONG),
                    ('biClrUsed', ctypes.wintypes.DWORD),
                    ('biClrImportant', ctypes.wintypes.DWORD)
                ]
            bmi = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=w, biHeight=-h, biPlanes=1, biBitCount=32, biCompression=0)
            buffer = ctypes.create_string_buffer(w * h * 4)
            
            gdi32.SelectObject(memdc, oldbmp)
            gdi32.GetDIBits(hdc, hbmp, 0, h, buffer, ctypes.byref(bmi), 0)
            img = Image.frombytes("RGB", (w, h), buffer.raw, "raw", "BGRX")
            
            gdi32.DeleteObject(hbmp)
            gdi32.DeleteDC(memdc)
            user32.ReleaseDC(0, hdc)
            return img
        except Exception as e:
            logger.warning(f"ctypes GDI capture failed: {e}")
            return None

    def capture_screenshot(self) -> io.BytesIO | None:
        """
        Capture full screen using ctypes GDI, mss, or ImageGrab,
        overlay timestamp YYYY-MM-DD HH:MM:SS in top-right corner,
        and return JPEG BytesIO stream.
        """
        img = self._ctypes_gdi_capture()

        # 1. Try mss capture fallback
        if img is None and mss is not None:
            try:
                with mss.mss() as sct:
                    # sct.monitors[0] is a dict of all monitors together
                    monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as e:
                logger.warning(f"mss screenshot failed: {e}. Trying ImageGrab fallback...")

        # 2. Fallback to PIL.ImageGrab
        if img is None:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab(all_screens=True)
            except Exception as e:
                logger.warning(f"PIL ImageGrab screenshot failed: {e}. Generating fallback canvas...")

        # 3. Fallback to synthetic image if no desktop environment available
        if img is None:
            img = Image.new("RGB", (1280, 720), color=(30, 30, 40))
            draw_fb = ImageDraw.Draw(img)
            draw_fb.text((50, 50), "Parental Control Agent - Background Service Screen Capture", fill=(255, 255, 255))

        try:
            # Prepare timestamp text (Force UTC+7 Vietnam Time)
            draw = ImageDraw.Draw(img)
            vn_tz = datetime.timezone(datetime.timedelta(hours=7))
            timestamp_str = datetime.datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

            # Load font with fallback to default
            font = None
            font_sizes = [28, 24, 20]
            for font_name in ["arial.ttf", "arialbd.ttf", "dejavusans.ttf", "tahoma.ttf"]:
                for size in font_sizes:
                    try:
                        font = ImageFont.truetype(font_name, size)
                        break
                    except Exception:
                        continue
                if font:
                    break

            if font is None:
                font = ImageFont.load_default()

            # Compute text width/height for top-right corner placement
            padding = 15
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), timestamp_str, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            else:
                text_w, text_h = draw.textsize(timestamp_str, font=font)

            x = max(padding, img.width - text_w - padding)
            y = padding

            # Draw subtle dark outline for visibility on bright backgrounds
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1), (0, -1), (0, 1), (-1, 0), (1, 0)]:
                draw.text((x + dx, y + dy), timestamp_str, fill=(0, 0, 0), font=font)

            # Draw bright red timestamp text
            draw.text((x, y), timestamp_str, fill=(255, 0, 0), font=font)

            # Save image to io.BytesIO stream in JPEG format
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            return buffer

        except Exception as e:
            logger.error(f"Error drawing timestamp on screenshot: {e}", exc_info=True)
            return None

    def capture_and_upload(self) -> bool:
        """
        Captures screenshot and posts it to backend API /api/screenshots/upload.
        Returns True if response status_code == 200.
        """
        try:
            img_buffer = self.capture_screenshot()
            if not img_buffer:
                logger.error("Screenshot capture returned empty buffer.")
                return False

            url = f"{self.backend_url}/api/screenshots/upload"
            data = {"device_id": self.device_id}
            files = {
                "file": ("screenshot.jpg", img_buffer, "image/jpeg")
            }
            auth_token = self.secret_token or API_KEY
            headers = {
                "Authorization": f"Bearer {auth_token}"
            }

            logger.info(f"Uploading screenshot for device {self.device_id} to {url}...")
            response = requests.post(url, data=data, files=files, headers=headers, timeout=20)

            if response.status_code == 200:
                logger.info("Screenshot uploaded successfully.")
                return True
            else:
                logger.error(f"Failed to upload screenshot. Server HTTP {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exception during screenshot upload process: {e}", exc_info=True)
            return False
