import pytest
import os
import sys
from fastapi.testclient import TestClient

# Ensure backend_api is in pythonpath
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from database import get_db, Base, engine
import models
from core.security import create_access_token

client = TestClient(app)

def test_system_and_rbac_flow():
    print("\n--- [START] Testing Settings & RBAC Permissions ---")

    # 1. Test Period Settings
    print("[1] Testing GET & PUT /api/settings/periods...")
    res = client.get("/api/settings/periods", headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    assert res.status_code == 200, f"GET /api/settings/periods failed: {res.text}"
    data = res.json()["data"]
    print(f" -> Current Period Settings: {data}")

    put_res = client.put("/api/settings/periods", json={
        "screenshot_interval_seconds": 45,
        "heartbeat_interval_seconds": 10,
        "log_batch_interval_seconds": 180
    }, headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    assert put_res.status_code == 200, f"PUT /api/settings/periods failed: {put_res.text}"
    print(" -> Successfully updated Period Settings to 45s/10s/180s")

    # 2. Test Time Control: Allowed Hours (with empty and valid device_id)
    print("\n[2] Testing GET & PUT /api/settings/time-control/allowed-hours...")
    res = client.get("/api/settings/time-control/allowed-hours?device_id=", headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    assert res.status_code == 200, f"GET allowed-hours with empty device_id failed: {res.text}"
    print(f" -> GET allowed-hours response with fallback: {res.json()['data']}")

    # Get first device or pair mock
    dev_res = client.get("/api/devices", headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    devices = dev_res.json()["data"]["devices"]
    device_id = devices[0]["device_id"] if devices else None
    print(f" -> Using Device ID: {device_id}")

    res_put_time = client.put("/api/settings/time-control/allowed-hours", json={
        "device_id": device_id,
        "schedules": [
            {"days": [0, 1, 2, 3, 4], "start": "07:30", "end": "21:00"},
            {"days": [5, 6], "start": "08:00", "end": "22:30"}
        ]
    }, headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    assert res_put_time.status_code == 200, f"PUT allowed-hours failed: {res_put_time.text}"
    print(f" -> Successfully saved allowed hours: {res_put_time.json()['data']}")

    # 3. Test Restrictions (App & Web)
    print("\n[3] Testing GET & PUT /api/settings/time-control/restrictions...")
    res_put_restr = client.put("/api/settings/time-control/restrictions", json={
        "device_id": device_id,
        "rules": [
            {"type": "app", "target": "notepad.exe", "mode": "ban"},
            {"type": "web", "target": "tiktok.com", "mode": "ban"},
            {"type": "app", "target": "chrome.exe", "mode": "limit", "daily_limit_minutes": 120}
        ]
    }, headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    assert res_put_restr.status_code == 200, f"PUT restrictions failed: {res_put_restr.text}"
    print(f" -> Successfully saved restrictions: {res_put_restr.json()['data']}")

    res_get_restr = client.get(f"/api/settings/time-control/restrictions?device_id={device_id}", headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    assert res_get_restr.status_code == 200
    print(f" -> Fetched active restrictions: {res_get_restr.json()['data']['rules']}")

    # 4. Test RBAC Permissions Enforcement
    print("\n[4] Testing RBAC Permissions Enforcement...")
    # Create Sub-Account with ONLY can_view_logs=True
    sub_account_email = "sub_tester_restricted@example.com"
    sub_account_pwd = "Password123!"

    # Ensure clean state for test user
    from database import SessionLocal
    db = SessionLocal()
    existing_user = db.query(models.User).filter(models.User.email == sub_account_email).first()
    if existing_user:
        db.query(models.UserPermission).filter(models.UserPermission.user_id == existing_user.id).delete()
        db.delete(existing_user)
        db.commit()
    db.close()

    create_user_res = client.post("/api/v1/users", json={
        "email": sub_account_email,
        "password": sub_account_pwd,
        "role": "sub_account",
        "permissions": {
            "can_view_screenshots": False,
            "can_manage_rules": False,
            "can_view_logs": True,
            "can_remote_control": False,
            "can_manage_users": False
        }
    }, headers={"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"})
    assert create_user_res.status_code in [200, 201], f"Create sub-account failed: {create_user_res.text}"
    print(f" -> Created restricted sub-account: {sub_account_email}")

    # Login as Sub-Account to get JWT token
    login_res = client.post("/api/auth/login", json={
        "email": sub_account_email,
        "password": sub_account_pwd
    })
    assert login_res.status_code == 200, f"Sub-account login failed: {login_res.text}"
    sub_token = login_res.json()["data"]["access_token"]
    sub_headers = {"Authorization": f"Bearer {sub_token}"}
    print(" -> Sub-account logged in, token acquired")

    # A. Sub-account tries to view screenshots (can_view_screenshots = False) -> Expected 403
    shot_res = client.get(f"/api/device/{device_id}/screenshots", headers=sub_headers)
    print(f" -> Sub-account GET /screenshots response: HTTP {shot_res.status_code}")
    assert shot_res.status_code == 403, f"Expected 403 Forbidden for screenshots, got {shot_res.status_code}"

    # B. Sub-account tries to create rule (can_manage_rules = False) -> Expected 403
    rule_res = client.post(f"/api/device/{device_id}/rules", json={"rule_type": "app", "target": "game.exe", "is_banned": True}, headers=sub_headers)
    print(f" -> Sub-account POST /rules response: HTTP {rule_res.status_code}")
    assert rule_res.status_code == 403, f"Expected 403 Forbidden for rules, got {rule_res.status_code}"

    # C. Sub-account tries to send remote command (can_remote_control = False) -> Expected 403
    cmd_res = client.post(f"/api/device/{device_id}/command", json={"command": "lock_screen"}, headers=sub_headers)
    print(f" -> Sub-account POST /command response: HTTP {cmd_res.status_code}")
    assert cmd_res.status_code == 403, f"Expected 403 Forbidden for remote command, got {cmd_res.status_code}"

    # D. Sub-account tries to view logs (can_view_logs = True) -> Expected 200
    log_res = client.get(f"/api/device/{device_id}/logs", headers=sub_headers)
    print(f" -> Sub-account GET /logs response: HTTP {log_res.status_code}")
    assert log_res.status_code == 200, f"Expected 200 OK for logs, got {log_res.status_code}"

    # E. Admin does the same screenshot request -> Expected 200
    admin_headers = {"Authorization": "Bearer PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD"}
    admin_shot_res = client.get(f"/api/device/{device_id}/screenshots", headers=admin_headers)
    print(f" -> Admin GET /screenshots response: HTTP {admin_shot_res.status_code}")
    assert admin_shot_res.status_code == 200, f"Expected 200 OK for admin, got {admin_shot_res.status_code}"

    print("\n✅ ALL SETTINGS & RBAC PERMISSION TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_system_and_rbac_flow()
