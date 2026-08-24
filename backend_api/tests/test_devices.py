import io
import uuid
import models


def test_devices_unauthorized_without_token(client):
    response = client.get("/api/devices")
    assert response.status_code == 401


def test_devices_authorized_with_jwt(client, admin_user):
    headers = {"Authorization": f"Bearer {admin_user['token']}"}
    response = client.get("/api/devices", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "devices" in data["data"]


def test_screenshot_upload_webp_and_png(client, admin_user, db_session):
    # 1. Create a dummy device
    device = models.Device(
        parent_id=admin_user["user"].id,
        device_name="Test-Device-Screenshot",
        secret_token=str(uuid.uuid4())
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    headers = {"Authorization": f"Bearer {admin_user['token']}"}

    # 2. Upload WebP screenshot
    webp_content = b"RIFF....WEBPVP8 ...fake-webp-binary-data..."
    files = {
        "file": ("screen_test.webp", io.BytesIO(webp_content), "image/webp")
    }
    data = {
        "device_id": str(device.id)
    }

    agent_headers = {"Authorization": f"Bearer {device.secret_token}"}
    response = client.post("/api/screenshots/upload", headers=agent_headers, data=data, files=files)
    assert response.status_code == 200
    res_data = response.json()
    assert "data" in res_data
    assert res_data["data"]["image_url"].endswith(".webp")

    # 3. Upload PNG screenshot with Device Secret Token (Agent Authentication)
    agent_headers = {"Authorization": f"Bearer {device.secret_token}"}
    png_content = b"\x89PNG\r\n\x1a\n...fake-png-binary-data..."
    files_png = {
        "file": ("screen_test.png", io.BytesIO(png_content), "image/png")
    }
    response_png = client.post("/api/screenshots/upload", headers=agent_headers, data=data, files=files_png)
    assert response_png.status_code == 200
    assert response_png.json()["data"]["image_url"].endswith(".png")

    # 4. Test Single Screenshot Deletion
    shot_id = response.json()["data"]["screenshot_id"]
    del_res = client.delete(f"/api/screenshots/{shot_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["data"]["msg"] == "Screenshot deleted successfully"
    # Ensure it's no longer in DB
    assert db_session.query(models.Screenshot).filter(models.Screenshot.id == uuid.UUID(shot_id)).first() is None

    # 5. Test Delete All Device Screenshots
    del_all_res = client.delete(f"/api/device/{device.id}/screenshots", headers=headers)
    assert del_all_res.status_code == 200
    assert del_all_res.json()["data"]["deleted_count"] >= 1
    assert db_session.query(models.Screenshot).filter(models.Screenshot.device_id == device.id).count() == 0

