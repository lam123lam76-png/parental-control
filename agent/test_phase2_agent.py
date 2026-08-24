"""
test_phase2_agent.py — Phase 2 Architecture Verification Suite
"""

import os
import sys
import tempfile
import time
import unittest

# Ensure agent directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import credential_store
from communication.alert_sender import AlertSender
from enforcement.process_monitor import get_active_window_info, get_running_processes
from enforcement.time_enforcer import check_time_rules
from local_store.integrity import sign_rules, verify_rules
from local_store.local_db import LocalDB


class TestPhase2Agent(unittest.TestCase):
    
    def test_01_credential_store(self):
        """Test DPAPI credential save, load, and clear."""
        test_device_id = "test-device-uuid-1234"
        test_secret_token = "test-secret-token-5678"
        
        # Save
        credential_store.save_credentials(test_device_id, test_secret_token)
        self.assertTrue(credential_store.has_credentials())
        
        # Load
        dev_id, token = credential_store.load_credentials()
        self.assertEqual(dev_id, test_device_id)
        self.assertEqual(token, test_secret_token)
        
        # Clear
        credential_store.clear_credentials()
        self.assertFalse(credential_store.has_credentials())

    def test_02_local_db_and_hmac(self):
        """Test SQLite local DB CRUD operations and HMAC integrity verification."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name

        try:
            db = LocalDB(db_path=tmp_db_path)
            
            # Save and get cached rules
            test_rules = [
                {"id": "r1", "rule_type": "app", "target": "game.exe", "is_banned": 1},
                {"id": "r2", "rule_type": "web", "target": "facebook.com", "is_banned": 1}
            ]
            db.save_cached_rules(test_rules)
            cached = db.get_cached_rules()
            self.assertEqual(len(cached), 2)
            
            # Test HMAC signing & verification
            secret_token = "my-secret-key"
            sig = sign_rules(test_rules, secret_token)
            self.assertTrue(verify_rules(test_rules, sig, secret_token))
            
            # Tamper rules -> verification should fail
            tampered_rules = [
                {"id": "r1", "rule_type": "app", "target": "game.exe", "is_banned": 0}
            ]
            self.assertFalse(verify_rules(tampered_rules, sig, secret_token))

            # Test Pending logs
            db.add_pending_log("chrome.exe", "Google - Chrome")
            logs = db.get_pending_logs(limit=10)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["process_name"], "chrome.exe")
            
            # Delete pending log
            db.delete_pending_logs([logs[0]["id"]])
            self.assertEqual(len(db.get_pending_logs()), 0)

            # Delete pending alert
            db.add_pending_alert("banned_app", "Opened game.exe")
            alerts = db.get_pending_alerts()
            self.assertEqual(len(alerts), 1)
            db.delete_pending_alerts([alerts[0]["id"]])
            self.assertEqual(len(db.get_pending_alerts()), 0)

        finally:
            try:
                if os.path.exists(tmp_db_path):
                    os.remove(tmp_db_path)
            except Exception:
                pass

    def test_03_enforcement_engine(self):
        """Test process scan, active window info, app/web/time rule checking."""
        # Process monitor
        procs = get_running_processes()
        self.assertIsInstance(procs, list)
        self.assertGreater(len(procs), 0)
        
        # Active window
        win_info = get_active_window_info()
        self.assertIsInstance(win_info, dict)
        
        # Time rules check
        allow_rules = [
            {
                "id": "t1",
                "rule_type": "time",
                "day_of_week": time.localtime().tm_wday,
                "allowed_start": "00:00:00",
                "allowed_end": "23:59:59"
            }
        ]
        is_allowed, reason = check_time_rules(allow_rules)
        self.assertTrue(is_allowed)

    def test_04_alert_sender_queue(self):
        """Test AlertSender initialization and queue handling."""
        sender = AlertSender("test-device", "http://127.0.0.1:9999")
        sender.start()
        sender.send_alert("test-device", "test_alert", "Hello Test")
        time.sleep(0.5)
        sender.stop()


if __name__ == "__main__":
    unittest.main()
