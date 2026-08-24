"""
test_system_integrity.py — Automated QA & System Integrity Test Suite.

Chay test tu dong cho cac module local (dung standard unittest library):
1. app_rules.py: Test file hash calculation & process matching
2. screenshot.py: Test image diff calculation & change detection
3. storage/local_db.py: Test SQLite concurrent multi-thread read/write safety
"""
import os
import sys
import tempfile
import threading
import time
import unittest

from PIL import Image

# Add agent root directory to sys.path
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from local_store.local_db import LocalDB
from monitor.app_rules import _get_file_hash, _match_process_to_rule
from monitor.screenshot import _compute_change_ratio, has_significant_change


class TestSystemIntegrity(unittest.TestCase):

    def test_01_app_rules_file_hash(self):
        """1. Kiem tra tinh dung dan cua ham tinh MD5 hash file thực thi."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as tmp:
            tmp.write(b"PARENTAL_CONTROL_TEST_HASH_CONTENT_12345")
            tmp_path = tmp.name

        try:
            file_hash = _get_file_hash(tmp_path)
            self.assertIsNotNone(file_hash)
            self.assertEqual(len(file_hash), 32)  # MD5 hex digest length

            proc_info = {"name": "test_app.exe", "pid": os.getpid()}
            rule = {"process_name": "test_app.exe", "category": "forbidden"}
            self.assertTrue(_match_process_to_rule(proc_info, rule))

            wrong_rule = {"process_name": "other_app.exe", "category": "forbidden"}
            self.assertFalse(_match_process_to_rule(proc_info, wrong_rule))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_02_screenshot_image_diff(self):
        """2. Kiem tra thuat toan so sanh anh pixel-diff."""
        img1 = Image.new("RGB", (640, 480), color="blue")
        img2 = Image.new("RGB", (640, 480), color="blue")

        ratio_same = _compute_change_ratio(img1, img2)
        self.assertEqual(ratio_same, 0.0)

        img_red = Image.new("RGB", (640, 480), color="red")
        ratio_diff = _compute_change_ratio(img1, img_red)
        self.assertGreater(ratio_diff, 0.9)

        self.assertTrue(has_significant_change(img1))
        self.assertFalse(has_significant_change(img2))
        self.assertTrue(has_significant_change(img_red))

    def test_03_local_db_multithread_concurrency(self):
        """3. Mo phong 10 threads ghi dong thoi vao SQLite (WAL mode safety)."""
        db = LocalDB()
        today_str = "2026-08-04"
        num_threads = 10
        increments_per_thread = 15
        errors = []

        def worker_thread(thread_id: int):
            try:
                for i in range(increments_per_thread):
                    db.increment_usage_minutes(today_str, 1)
                    db.increment_app_usage(today_str, f"app_{thread_id}.exe", 1)
                    db.add_pending_log("test_event", {"thread": thread_id, "step": i})
                    time.sleep(0.005)
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")

        threads = []
        for t_id in range(num_threads):
            t = threading.Thread(target=worker_thread, args=(t_id,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        pending_logs = db.get_pending_logs(limit=500)
        self.assertGreater(len(pending_logs), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
