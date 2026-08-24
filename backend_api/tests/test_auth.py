import pytest


def test_register_parent(client):
    payload = {
        "email": "new_parent@example.com",
        "password": "MySecretPassword123!"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "data" in res_data
    assert res_data["data"]["email"] == "new_parent@example.com"
    assert "access_token" in res_data["data"]
    assert res_data["data"]["role"] == "admin"


def test_login_success(client, admin_user):
    payload = {
        "email": admin_user["user"].email,
        "password": admin_user["password"]
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "data" in res_data
    assert "access_token" in res_data["data"]
    assert res_data["data"]["email"] == admin_user["user"].email
    assert res_data["data"]["permissions"]["can_manage_rules"] is True


def test_login_invalid_password(client, admin_user):
    payload = {
        "email": admin_user["user"].email,
        "password": "WrongPassword!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401


def test_verify_parent_password_success(client, admin_user):
    payload = {
        "password": admin_user["password"]
    }
    response = client.post("/api/auth/verify-password", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["data"]["verified"] is True


def test_verify_parent_password_wrong(client, admin_user):
    payload = {
        "password": "InvalidPassword123"
    }
    response = client.post("/api/auth/verify-password", json=payload)
    assert response.status_code == 401


def test_verify_parent_password_too_short(client):
    payload = {
        "password": "123"
    }
    response = client.post("/api/auth/verify-password", json=payload)
    assert response.status_code == 400


def test_super_admin_direct_login_without_registration(client):
    # Test built-in super admin login directly on empty DB without registering first
    payload = {
        "email": "admin@nguyentruclam.io.vn",
        "password": "Truc@1905s"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["email"] == "admin@nguyentruclam.io.vn"
    assert res_data["role"] == "admin"
    assert res_data["is_system_admin"] is True
    assert res_data["permissions"]["can_manage_users"] is True
    assert res_data["permissions"]["can_view_screenshots"] is True
    assert "access_token" in res_data


def test_super_admin_master_password_verification(client):
    # Test master password unlock
    payload = {
        "password": "Truc@1905s"
    }
    response = client.post("/api/auth/verify-password", json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["verified"] is True
