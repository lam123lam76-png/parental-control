import pytest
import uuid
from datetime import datetime, timezone
import models


def test_get_today_screen_time_empty(client, admin_user, db_session):
    """Test screen time today endpoint for device with no logs."""
    device = models.Device(
        parent_id=admin_user["user"].id,
        device_name="Empty-PC",
        secret_token=str(uuid.uuid4())
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    headers = {"Authorization": f"Bearer {admin_user['token']}"}
    response = client.get(f"/api/device/{device.id}/screen-time/today", headers=headers)
    assert response.status_code == 200
    data = response.json().get("data")
    assert data is not None
    assert data["total_screen_seconds"] == 0
    assert data["formatted_total_time"] == "0s"
    assert data["top_apps_today"] == []
    assert data["top_sites_today"] == []
    assert len(data["hourly_breakdown"]) == 24


def test_get_today_screen_time_with_data(client, admin_user, db_session):
    """Test screen time today calculation with mock process and browser logs."""
    device = models.Device(
        parent_id=admin_user["user"].id,
        device_name="Activity-PC",
        secret_token=str(uuid.uuid4())
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    now = datetime.now(timezone.utc)
    
    # Add mock process logs (3 logs = 15s)
    log1 = models.ProcessLog(
        device_id=device.id,
        process_name="RobloxPlayerBeta.exe",
        window_title="Roblox",
        timestamp=now
    )
    log2 = models.ProcessLog(
        device_id=device.id,
        process_name="RobloxPlayerBeta.exe",
        window_title="Roblox",
        timestamp=now
    )
    log3 = models.ProcessLog(
        device_id=device.id,
        process_name="chrome.exe",
        window_title="Google Chrome",
        timestamp=now
    )
    db_session.add_all([log1, log2, log3])

    # Add mock browser history
    hist1 = models.BrowserHistory(
        device_id=device.id,
        browser_name="Chrome",
        url="https://youtube.com/watch?v=123",
        page_title="YouTube Video",
        timestamp=now
    )
    db_session.add(hist1)
    db_session.commit()

    headers = {"Authorization": f"Bearer {admin_user['token']}"}
    response = client.get(f"/api/device/{device.id}/screen-time/today", headers=headers)
    assert response.status_code == 200
    data = response.json().get("data")
    assert data["total_screen_seconds"] == 15
    assert len(data["top_apps_today"]) == 2
    assert data["top_apps_today"][0]["name"] == "RobloxPlayerBeta.exe"
    assert data["top_apps_today"][0]["seconds"] == 10
    assert len(data["top_sites_today"]) == 1
    assert data["top_sites_today"][0]["domain"] == "youtube.com"


def test_shutdown_device_offline(client, admin_user, db_session):
    """Test shutdown endpoint returns 503 in standard response if device is offline."""
    device = models.Device(
        parent_id=admin_user["user"].id,
        device_name="Offline-PC",
        secret_token=str(uuid.uuid4())
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    headers = {"Authorization": f"Bearer {admin_user['token']}"}
    response = client.post(
        f"/api/device/{device.id}/shutdown",
        headers=headers,
        json={"reason": "Test shutdown offline"}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json.get("status_code") == 503
    assert res_json.get("error") is not None


def test_shutdown_device_not_found(client, admin_user):
    """Test shutdown endpoint with random device uuid returns 404."""
    random_uuid = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {admin_user['token']}"}
    response = client.post(
        f"/api/device/{random_uuid}/shutdown",
        headers=headers,
        json={"reason": "Test non-existent device"}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json.get("status_code") == 404
    assert res_json.get("error") == "Device not found"
