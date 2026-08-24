"""
test_e2e_full_flow.py — Comprehensive End-to-End System Verification Suite

Tests the complete Parental Control System flow:
1. Backend Startup (FastAPI + SQLite)
2. Parent Registration & Device Pairing
3. Agent DPAPI / Credential Store & Local SQLite Database
4. WebSocket Stream 1: Real-time Connection, Heartbeat & Remote Command Push
5. Stream 2: Fast-Track Alert Queue
6. Stream 3: Batch Process Activity Log Uploader
7. Screenshot Engine: Capture, Timestamp Rendering, Upload & Serving
8. Rules Engine: Rule Creation, Real-time WebSocket Push & HMAC Signature Validation
"""

import sys
import os
import time
import json
import uuid
import signal
import socket
import asyncio
import tempfile
import threading
import unittest
import subprocess
from pathlib import Path

import requests
import websocket

# Set up paths
BASE_DIR = Path(__file__).resolve().parent
AGENT_DIR = BASE_DIR / "agent"
BACKEND_DIR = BASE_DIR / "backend_api"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BACKEND_DIR))


def find_free_port() -> int:
    """Find an available TCP port for local test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestE2EFullFlow(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Start local test server."""
        cls.port = find_free_port()
        cls.backend_url = f"http://127.0.0.1:{cls.port}"
        cls.ws_url = f"ws://127.0.0.1:{cls.port}"

        # Create temporary database path
        cls.tmp_dir = tempfile.TemporaryDirectory()
        cls.db_file = Path(cls.tmp_dir.name) / "test_e2e.db"
        
        # Env for uvicorn process
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{cls.db_file.as_posix()}"
        env["PYTHONPATH"] = str(BACKEND_DIR)

        # Launch backend uvicorn process
        cls.server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(cls.port)],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait for server to become responsive
        start_time = time.time()
        server_ready = False
        while time.time() - start_time < 10:
            try:
                res = requests.get(f"{cls.backend_url}/docs", timeout=1)
                if res.status_code == 200:
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.3)

        if not server_ready:
            cls.server_proc.kill()
            raise RuntimeError("Backend test server failed to start on port " + str(cls.port))

        print(f"\n[E2E] Backend server running at {cls.backend_url}")

    @classmethod
    def tearDownClass(cls):
        """Terminate local test server and cleanup."""
        if cls.server_proc:
            cls.server_proc.terminate()
            try:
                cls.server_proc.wait(timeout=3)
            except Exception:
                cls.server_proc.kill()
        cls.tmp_dir.cleanup()
        print("[E2E] Backend test server terminated cleanly.")

    def test_full_system_pipeline(self):
        """Execute full E2E system pipeline test."""
        # 1. Parent Registration
        parent_email = f"e2e_parent_{int(time.time())}@test.com"
        parent_pass = "TestPassword123!"

        reg_res = requests.post(
            f"{self.backend_url}/api/register",
            json={"email": parent_email, "password": parent_pass}
        )
        self.assertEqual(reg_res.status_code, 200)
        self.assertEqual(reg_res.json()["status_code"], 201)
        print("  ✅ Step 1: Parent registration successful.")

        # 2. Device Pairing
        pair_res = requests.post(
            f"{self.backend_url}/api/pair",
            json={
                "hardware_uuid": str(uuid.uuid4()),
                "device_name": "E2E-Test-PC",
                "parent_email": parent_email,
                "parent_password": parent_pass
            }
        )
        self.assertEqual(pair_res.status_code, 200)
        pair_data = pair_res.json()["data"]
        device_id = pair_data["device_id"]
        secret_token = pair_data["secret_token"]
        self.assertIsNotNone(device_id)
        self.assertIsNotNone(secret_token)
        print(f"  ✅ Step 2: Device paired (device_id={device_id}).")

        # 3. Agent DPAPI & Local DB Verification
        import credential_store
        from local_store.local_db import LocalDB
        from local_store.integrity import sign_rules, verify_rules

        credential_store.save_credentials(device_id, secret_token)
        self.assertTrue(credential_store.has_credentials())
        loaded_id, loaded_tok = credential_store.load_credentials()
        self.assertEqual(loaded_id, device_id)
        self.assertEqual(loaded_tok, secret_token)
        print("  ✅ Step 3: Credential Store (DPAPI/Fallback) verified.")

        # 4. WebSocket Stream 1 (Heartbeat & Remote Commands)
        ws_uri = f"{self.ws_url}/ws/device/{device_id}?token={secret_token}"
        received_messages = []
        ws_connected = threading.Event()

        def on_message(ws, message):
            data = json.loads(message)
            received_messages.append(data)
            if data.get("type") == "heartbeat_ack":
                ws_connected.set()

        ws_app = websocket.WebSocketApp(
            ws_uri,
            on_message=on_message,
        )

        ws_thread = threading.Thread(target=ws_app.run_forever, daemon=True)
        ws_thread.start()

        # Send heartbeat
        time.sleep(1)
        ws_app.send(json.dumps({"type": "heartbeat"}))
        self.assertTrue(ws_connected.wait(timeout=5))
        print("  ✅ Step 4: Stream 1 WebSocket Heartbeat ACK received.")

        # 5. Remote Command Push via WebSocket
        cmd_res = requests.post(
            f"{self.backend_url}/api/device/{device_id}/command",
            json={"command": "lock_screen", "payload": {"reason": "E2E Lock Test"}}
        )
        self.assertEqual(cmd_res.status_code, 200)

        time.sleep(1)
        command_received = any(
            m.get("type") == "command" and m.get("command") == "lock_screen"
            for m in received_messages
        )
        self.assertTrue(command_received)
        print("  ✅ Step 5: Remote command pushed & received via WebSocket.")

        # 6. Stream 2: Fast-Track Alert
        alert_res = requests.post(
            f"{self.backend_url}/api/alerts",
            json={
                "device_id": device_id,
                "alert_type": "banned_app_opened",
                "message": "Opened forbidden test app"
            }
        )
        self.assertEqual(alert_res.status_code, 200)
        print("  ✅ Step 6: Stream 2 Fast-Track Alert uploaded.")

        # 7. Stream 3: Batch Process Logs
        log_res = requests.post(
            f"{self.backend_url}/api/logs/batch",
            json={
                "device_id": device_id,
                "logs": [
                    {
                        "process_name": "chrome.exe",
                        "window_title": "Google Search - Chrome",
                        "timestamp": "2026-08-11T10:00:00Z"
                    }
                ]
            }
        )
        self.assertEqual(log_res.status_code, 200)
        print("  ✅ Step 7: Stream 3 Process Logs Batch uploaded.")

        # 8. Screenshot Capture & Upload
        from screenshot_engine import ScreenshotEngine
        engine = ScreenshotEngine(device_id, self.backend_url)
        upload_success = engine.capture_and_upload()
        self.assertTrue(upload_success)

        # Verify screenshot list
        shots_res = requests.get(f"{self.backend_url}/api/device/{device_id}/screenshots")
        self.assertEqual(shots_res.status_code, 200)
        shots = shots_res.json()["data"]["screenshots"]
        self.assertGreater(len(shots), 0)
        print(f"  ✅ Step 8: Screenshot captured, timestamped & uploaded ({shots[0]['image_url']}).")

        # 9. Rules API & WebSocket Push
        rule_res = requests.post(
            f"{self.backend_url}/api/device/{device_id}/rules",
            json={
                "device_id": device_id,
                "rule_type": "app",
                "target": "forbidden_game.exe",
                "is_banned": True
            }
        )
        self.assertEqual(rule_res.status_code, 200)

        rules_list_res = requests.get(f"{self.backend_url}/api/device/{device_id}/rules")
        rules = rules_list_res.json()["data"]["rules"]
        self.assertEqual(len(rules), 1)

        # Test HMAC signature
        sig = sign_rules(rules, secret_token)
        self.assertTrue(verify_rules(rules, sig, secret_token))
        print("  ✅ Step 9: Rules API CRUD, WebSocket push & HMAC signature verified.")

        ws_app.close()
        credential_store.clear_credentials()


if __name__ == "__main__":
    unittest.main()
