"""
test_phase3.py — Phase 3 Screenshot & Rules Integration Test Suite
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screenshot_engine import ScreenshotEngine


class TestPhase3(unittest.TestCase):
    
    def test_01_screenshot_engine_capture(self):
        """Test screenshot capture and image generation in memory."""
        engine = ScreenshotEngine(device_id="test-device-uuid", backend_url="http://127.0.0.1:8000")
        
        # Test raw screenshot capture
        img_buffer = engine.capture_screenshot()
        self.assertIsNotNone(img_buffer)
        img_bytes = img_buffer.getvalue()
        self.assertGreater(len(img_bytes), 100)
        
        # Verify header is JPEG
        self.assertTrue(img_bytes.startswith(b'\xff\xd8'))

    def test_02_screenshot_is_not_black(self):
        """Verify the captured screenshot is not completely black."""
        engine = ScreenshotEngine(device_id="test-device", backend_url="http://127.0.0.1")
        img_buffer = engine.capture_screenshot()
        self.assertIsNotNone(img_buffer)
        
        from PIL import Image, ImageStat
        img = Image.open(img_buffer)
        stat = ImageStat.Stat(img)
        
        # If mean is too low (e.g. < 0.5), it means the image is almost entirely black
        # A normal desktop screenshot should have a mean > 1
        mean_brightness = sum(stat.mean) / len(stat.mean)
        self.assertGreater(mean_brightness, 1.0, "Screenshot is completely black")

    def test_03_backend_api_imports(self):
        """Verify backend_api models, schemas, and endpoints import correctly."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend_api"))
        import models
        import schemas
        
        # Check model attributes
        self.assertTrue(hasattr(models, "Screenshot"))
        self.assertTrue(hasattr(schemas, "ScreenshotResponse"))


if __name__ == "__main__":
    unittest.main()
