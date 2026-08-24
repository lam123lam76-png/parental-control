"""
Phase 1 Mock Test Script
=========================
Tests all 3 streams of the Parental Control Backend:
- Stream 1: WebSocket Heartbeat (Agent simulation)
- Stream 2: Fast-track Alerts (POST /api/alerts)
- Stream 3: Batch Log Upload (POST /api/logs/batch)
Plus: Parent registration, device pairing, and command endpoint.

Usage:
    1. Start the backend: uvicorn main:app --reload
    2. Run this script: python test_phase1.py

Prerequisites:
    pip install httpx websockets
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

import httpx

BASE_URL = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

# Test data
TEST_PARENT_EMAIL = f"test_parent_{int(datetime.now().timestamp())}@example.com"
TEST_PARENT_PASSWORD = "SecurePass123!"
TEST_DEVICE_NAME = "TestPC-Phase1"


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record(self, name: str, success: bool, detail: str = ""):
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append((name, status, detail))
        if success:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  {status} | {name}" + (f" — {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  RESULTS: {self.passed}/{total} passed, {self.failed}/{total} failed")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResults()


async def test_1_register_parent(client: httpx.AsyncClient) -> bool:
    """Test parent registration with bcrypt password hashing."""
    print("\n[1] Testing Parent Registration...")
    
    resp = await client.post(f"{BASE_URL}/api/register", json={
        "email": TEST_PARENT_EMAIL,
        "password": TEST_PARENT_PASSWORD
    })
    data = resp.json()
    
    success = resp.status_code == 200 and data.get("data", {}).get("parent_id") is not None
    results.record(
        "POST /api/register",
        success,
        f"parent_id={data.get('data', {}).get('parent_id', 'N/A')}"
    )
    
    # Test duplicate registration
    resp2 = await client.post(f"{BASE_URL}/api/register", json={
        "email": TEST_PARENT_EMAIL,
        "password": TEST_PARENT_PASSWORD
    })
    data2 = resp2.json()
    results.record(
        "Duplicate email rejection",
        data2.get("error") is not None,
        f"error={data2.get('error', 'N/A')}"
    )
    
    return success


async def test_2_pair_device(client: httpx.AsyncClient) -> dict:
    """Test device pairing with bcrypt password verification."""
    print("\n[2] Testing Device Pairing...")
    
    resp = await client.post(f"{BASE_URL}/api/pair", json={
        "hardware_uuid": "TEST-HW-UUID-12345",
        "device_name": TEST_DEVICE_NAME,
        "parent_email": TEST_PARENT_EMAIL,
        "parent_password": TEST_PARENT_PASSWORD
    })
    data = resp.json()
    
    device_id = data.get("data", {}).get("device_id")
    secret_token = data.get("data", {}).get("secret_token")
    
    success = device_id is not None and secret_token is not None
    results.record(
        "POST /api/pair",
        success,
        f"device_id={device_id}, token={'***' + secret_token[-6:] if secret_token else 'N/A'}"
    )
    
    # Test invalid credentials
    resp_bad = await client.post(f"{BASE_URL}/api/pair", json={
        "hardware_uuid": "TEST-HW-UUID-12345",
        "device_name": TEST_DEVICE_NAME,
        "parent_email": TEST_PARENT_EMAIL,
        "parent_password": "wrong_password"
    })
    data_bad = resp_bad.json()
    results.record(
        "Invalid password rejection",
        data_bad.get("error") is not None,
        f"error={data_bad.get('error', 'N/A')}"
    )
    
    return {"device_id": device_id, "secret_token": secret_token}


async def test_3_websocket_heartbeat(device_info: dict) -> None:
    """Test WebSocket connection and heartbeat (Stream 1)."""
    print("\n[3] Testing WebSocket Heartbeat (Stream 1)...")
    
    try:
        import websockets
    except ImportError:
        results.record("WebSocket Heartbeat", False, "websockets package not installed. Run: pip install websockets")
        return
    
    device_id = device_info["device_id"]
    token = device_info["secret_token"]
    ws_url = f"{WS_BASE}/ws/device/{device_id}?token={token}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            # Send heartbeat
            heartbeat_msg = json.dumps({"type": "heartbeat"})
            await ws.send(heartbeat_msg)
            
            # Wait for ack
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            ack = json.loads(response)
            
            success = ack.get("type") == "heartbeat_ack" and ack.get("status") == "ok"
            results.record(
                "WebSocket Heartbeat → ACK",
                success,
                f"response={ack}"
            )
            
            # Send second heartbeat to confirm loop works
            await ws.send(heartbeat_msg)
            response2 = await asyncio.wait_for(ws.recv(), timeout=5.0)
            ack2 = json.loads(response2)
            results.record(
                "WebSocket Heartbeat Loop",
                ack2.get("type") == "heartbeat_ack",
                "Second heartbeat acknowledged"
            )
            
    except asyncio.TimeoutError:
        results.record("WebSocket Heartbeat", False, "Timeout waiting for heartbeat_ack")
    except ConnectionRefusedError:
        results.record("WebSocket Heartbeat", False, "Connection refused. Is the server running?")
    except Exception as e:
        results.record("WebSocket Heartbeat", False, f"Error: {e}")

    # Test invalid token
    try:
        bad_url = f"{WS_BASE}/ws/device/{device_id}?token=invalid_token"
        async with websockets.connect(bad_url) as ws:
            # Should be closed immediately
            try:
                await asyncio.wait_for(ws.recv(), timeout=3.0)
                results.record("WebSocket Invalid Token Rejection", False, "Connection was not closed")
            except websockets.exceptions.ConnectionClosed:
                results.record("WebSocket Invalid Token Rejection", True, "Connection properly rejected")
    except Exception:
        results.record("WebSocket Invalid Token Rejection", True, "Connection refused (expected)")


async def test_4_alerts(client: httpx.AsyncClient, device_info: dict) -> None:
    """Test Alert creation (Stream 2)."""
    print("\n[4] Testing Alerts - Fast-track (Stream 2)...")
    
    device_id = device_info["device_id"]
    
    # Send a banned app alert
    resp = await client.post(f"{BASE_URL}/api/alerts", json={
        "device_id": device_id,
        "alert_type": "banned_app_opened",
        "message": "LienMinh.exe was opened on the device"
    })
    data = resp.json()
    
    results.record(
        "POST /api/alerts (banned_app)",
        resp.status_code == 200 and data.get("data", {}).get("msg") == "Alert received",
        f"response={data}"
    )
    
    # Send a tamper alert
    resp2 = await client.post(f"{BASE_URL}/api/alerts", json={
        "device_id": device_id,
        "alert_type": "tampered",
        "message": "Agent process was killed by user"
    })
    data2 = resp2.json()
    
    results.record(
        "POST /api/alerts (tampered)",
        resp2.status_code == 200,
        f"status_code={resp2.status_code}"
    )


async def test_5_batch_logs(client: httpx.AsyncClient, device_info: dict) -> None:
    """Test Batch Log Upload (Stream 3)."""
    print("\n[5] Testing Batch Log Upload (Stream 3)...")
    
    device_id = device_info["device_id"]
    now = datetime.now(timezone.utc).isoformat()
    
    # Create a batch of 50 logs
    logs = [
        {
            "process_name": f"process_{i}.exe",
            "window_title": f"Window Title {i}" if i % 2 == 0 else None,
            "timestamp": now
        }
        for i in range(50)
    ]
    
    resp = await client.post(f"{BASE_URL}/api/logs/batch", json={
        "device_id": device_id,
        "logs": logs
    })
    data = resp.json()
    
    success = resp.status_code == 200 and "50" in data.get("data", {}).get("msg", "")
    results.record(
        "POST /api/logs/batch (50 logs)",
        success,
        f"response={data}"
    )
    
    # Test with large batch (500 logs)
    large_logs = [
        {
            "process_name": f"bulk_process_{i}.exe",
            "window_title": f"Bulk Window {i}",
            "timestamp": now
        }
        for i in range(500)
    ]
    
    resp2 = await client.post(f"{BASE_URL}/api/logs/batch", json={
        "device_id": device_id,
        "logs": large_logs
    })
    data2 = resp2.json()
    
    results.record(
        "POST /api/logs/batch (500 logs - stress)",
        resp2.status_code == 200 and "500" in data2.get("data", {}).get("msg", ""),
        f"response={data2}"
    )


async def test_6_device_status(client: httpx.AsyncClient, device_info: dict) -> None:
    """Test device online/offline status endpoint."""
    print("\n[6] Testing Device Status...")
    
    device_id = device_info["device_id"]
    
    resp = await client.get(f"{BASE_URL}/api/device/{device_id}/status")
    data = resp.json()
    
    results.record(
        "GET /api/device/{id}/status",
        resp.status_code == 200 and data.get("data", {}).get("device_id") == device_id,
        f"is_online={data.get('data', {}).get('is_online')}, last_seen={data.get('data', {}).get('last_seen_at')}"
    )


async def test_7_command_endpoint(client: httpx.AsyncClient, device_info: dict) -> None:
    """Test command push endpoint (when device is offline)."""
    print("\n[7] Testing Command Endpoint...")
    
    device_id = device_info["device_id"]
    
    # Device is likely offline at this point, so we expect a 503
    resp = await client.post(f"{BASE_URL}/api/device/{device_id}/command", json={
        "command": "kill_process",
        "payload": {"process_name": "LienMinh.exe"}
    })
    data = resp.json()
    
    # Either 200 (device online) or error with "offline" message
    results.record(
        "POST /api/device/{id}/command",
        resp.status_code == 200,
        f"response={data}"
    )


async def main():
    print("=" * 60)
    print("  PHASE 1 MOCK TEST — Parental Control Backend")
    print("=" * 60)
    print(f"  Target: {BASE_URL}")
    print(f"  Test Parent: {TEST_PARENT_EMAIL}")
    print()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check if server is running
        try:
            await client.get(f"{BASE_URL}/docs")
        except httpx.ConnectError:
            print("❌ ERROR: Server is not running!")
            print(f"   Please start: cd backend_api && uvicorn main:app --reload")
            sys.exit(1)
        
        # Run tests sequentially
        await test_1_register_parent(client)
        device_info = await test_2_pair_device(client)
        
        if device_info.get("device_id"):
            await test_3_websocket_heartbeat(device_info)
            await test_4_alerts(client, device_info)
            await test_5_batch_logs(client, device_info)
            await test_6_device_status(client, device_info)
            await test_7_command_endpoint(client, device_info)
        else:
            print("\n❌ Skipping remaining tests — device pairing failed")
    
    # Print summary
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
