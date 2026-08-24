import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

AGENT_DIR = Path(__file__).resolve().parent.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from protection import watchdog


class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.fake_flag = Path(self.temp_dir) / 'shutdown.flag'

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_shutdown_flag_validation_valid_secret(self):
        self.fake_flag.write_text(watchdog.SHUTDOWN_FLAG_SECRET, encoding='utf-8')
        is_valid = watchdog._validate_flag_file(self.fake_flag)
        self.assertTrue(is_valid)
        self.assertTrue(self.fake_flag.exists())

    def test_shutdown_flag_validation_fake_empty_file(self):
        self.fake_flag.write_text('', encoding='utf-8')
        is_valid = watchdog._validate_flag_file(self.fake_flag)
        self.assertFalse(is_valid)
        self.assertFalse(self.fake_flag.exists())

    def test_shutdown_flag_validation_fake_random_text(self):
        self.fake_flag.write_text('random_attacker_string_123', encoding='utf-8')
        is_valid = watchdog._validate_flag_file(self.fake_flag)
        self.assertFalse(is_valid)
        self.assertFalse(self.fake_flag.exists())

    def test_create_shutdown_flag(self):
        with patch.object(watchdog, 'SHUTDOWN_FLAG', self.fake_flag):
            watchdog.create_shutdown_flag()
            self.assertTrue(self.fake_flag.exists())
            self.assertEqual(self.fake_flag.read_text(encoding='utf-8'), watchdog.SHUTDOWN_FLAG_SECRET)
            self.assertTrue(watchdog._validate_flag_file(self.fake_flag))

    def test_autostart_task_frequency_is_2_minutes(self):
        with open(AGENT_DIR / 'protection' / 'autostart.py', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('/sc minute /mo 2', content)

if __name__ == '__main__':
    unittest.main()
