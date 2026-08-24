import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models
import uuid
from datetime import datetime, timezone, timedelta

client = TestClient(app)

def test_daily_screen_time():
    db = SessionLocal()
    parent_id = uuid.uuid4()
    dev_id = uuid.uuid4()
    
    try:
        # 1. Prepare data
        parent = models.User(id=parent_id, email='test_screen_time_dummy@example.com', password_hash='foo')
        db.add(parent)
        db.commit()

        device = models.Device(id=dev_id, parent_id=parent_id, device_name='DummyTestDevice_XYZ123', secret_token='foo')
        db.add(device)
        db.commit()
        
        now = datetime.now(timezone.utc)
        logs = [
            models.ProcessLog(device_id=dev_id, process_name='chrome.exe', window_title='YouTube - Google Chrome', timestamp=now),
            models.ProcessLog(device_id=dev_id, process_name='chrome.exe', window_title='YouTube - Google Chrome', timestamp=now + timedelta(seconds=15)),
            models.ProcessLog(device_id=dev_id, process_name='chrome.exe', window_title='YouTube - Google Chrome', timestamp=now + timedelta(seconds=30)),
            models.ProcessLog(device_id=dev_id, process_name='chrome.exe', window_title='YouTube - Google Chrome', timestamp=now + timedelta(seconds=45))
        ]
        db.add_all(logs)
        db.commit()
        
        # 2. Execute test
        response = client.get(f'/api/device/{dev_id}/screen-time/today', headers={"Authorization": "Bearer 732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7"})
        assert response.status_code == 200
        data = response.json()['data']
        
        assert data['total_screen_seconds'] == 60, f"Expected 60s, got {data['total_screen_seconds']}s"
    finally:
        # 3. Guaranteed Cleanup regardless of pass/fail
        db.query(models.ProcessLog).filter(models.ProcessLog.device_id == dev_id).delete()
        db.query(models.Device).filter(models.Device.id == dev_id).delete()
        db.query(models.User).filter(models.User.id == parent_id).delete()
        db.commit()
        db.close()
    
    # Top app should be chrome.exe with 60 seconds
    top_app = data['top_apps_today'][0]
    assert top_app['name'] == 'chrome.exe'
    assert top_app['seconds'] == 60, f"Expected chrome to have 60s, got {top_app['seconds']}s"
    
    # Top site should be youtube.com with 60 seconds (inferred from window title)
    top_site = data['top_sites_today'][0]
    assert 'youtube' in top_site['domain'], f"Got {top_site['domain']}"
    assert top_site['seconds'] == 60, f"Expected youtube to have 60s, got {top_site['seconds']}s"
