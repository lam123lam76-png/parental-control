import uuid
from datetime import datetime, timezone, timedelta
import models

def test_focus_mode_toggle(client, admin_user, db_session):
    # 1. Create a dummy device
    device = models.Device(
        parent_id=admin_user["user"].id,
        device_name="Kid-PC",
        secret_token=str(uuid.uuid4())
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    headers = {"Authorization": f"Bearer {admin_user['token']}"}

    # 2. Enable Focus Mode (60 mins)
    res_enable = client.post(
        f"/api/device/{device.id}/focus-mode",
        headers=headers,
        json={"duration_minutes": 60, "enabled": True}
    )
    assert res_enable.status_code == 200
    data_enable = res_enable.json()["data"]
    assert data_enable["focus_mode"] is True
    assert data_enable["duration_minutes"] == 60
    assert data_enable["rules_added"] > 0

    # 3. Check that rules exist in database
    rules = db_session.query(models.Rule).filter(models.Rule.device_id == device.id).all()
    assert len(rules) >= 10
    target_names = [r.target.lower() for r in rules]
    assert "robloxplayerbeta.exe" in target_names
    assert "tiktok.com" in target_names

    # 4. Disable Focus Mode
    res_disable = client.post(
        f"/api/device/{device.id}/focus-mode",
        headers=headers,
        json={"duration_minutes": 60, "enabled": False}
    )
    assert res_disable.status_code == 200
    data_disable = res_disable.json()["data"]
    assert data_disable["focus_mode"] is False
    assert data_disable["rules_removed"] > 0


def test_device_analytics(client, admin_user, db_session):
    # 1. Create dummy device
    device = models.Device(
        parent_id=admin_user["user"].id,
        device_name="Analytics-PC",
        secret_token=str(uuid.uuid4())
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    # 2. Add some process logs and browser history
    now = datetime.now(timezone.utc)
    for app_name in ["chrome.exe", "RobloxPlayerBeta.exe", "chrome.exe", "code.exe", "chrome.exe"]:
        log = models.ProcessLog(
            device_id=device.id,
            process_name=app_name,
            window_title="Active Window",
            timestamp=now - timedelta(days=1)
        )
        db_session.add(log)

    for url in ["https://youtube.com/watch?v=1", "https://facebook.com/feed", "https://youtube.com/watch?v=2"]:
        hist = models.BrowserHistory(
            device_id=device.id,
            browser_name="Chrome",
            url=url,
            page_title="Sample Page",
            timestamp=now - timedelta(days=2)
        )
        db_session.add(hist)
    db_session.commit()

    headers = {"Authorization": f"Bearer {admin_user['token']}"}

    # 3. Request analytics
    response = client.get(f"/api/device/{device.id}/analytics", headers=headers)
    assert response.status_code == 200
    res_data = response.json()["data"]
    assert "total_logs_week" in res_data
    assert res_data["total_logs_week"] == 5
    assert len(res_data["top_apps"]) > 0
    assert res_data["top_apps"][0]["name"] == "chrome.exe"
    assert res_data["top_apps"][0]["count"] == 3
    assert len(res_data["top_sites"]) > 0
    assert len(res_data["daily_trend"]) == 7


def test_alert_creation_with_telegram_dispatch(client, admin_user, db_session):
    device = models.Device(
        parent_id=admin_user["user"].id,
        device_name="Alert-PC",
        secret_token=str(uuid.uuid4())
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    headers = {"Authorization": f"Bearer {admin_user['token']}"}
    alert_payload = {
        "device_id": str(device.id),
        "alert_type": "app_banned_violation",
        "message": "Trẻ đã cố mở ứng dụng bị cấm: RobloxPlayerBeta.exe"
    }

    res = client.post("/api/alerts", headers=headers, json=alert_payload)
    assert res.status_code == 200
    assert res.json()["data"]["msg"] == "Alert received"


def test_storage_cleanup_by_period(client, admin_user, db_session):
    headers = {"Authorization": f"Bearer {admin_user['token']}"}
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Call cleanup storage by period
    req_body = {
        "category": "all",
        "periods": [today_str],
        "period_type": "day"
    }
    res = client.post("/api/v1/storage/cleanup-by-period", headers=headers, json=req_body)
    assert res.status_code == 200
    res_data = res.json()["data"]
    assert "freed_mb" in res_data
    assert "deleted_counts" in res_data
    assert "total_deleted" in res_data