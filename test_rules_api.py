import requests

# 1. Login
login_data = {
    "email": "admin@nguyentruclam.io.vn",
    "password": "Truc@1905s"
}
res = requests.post("http://localhost:8000/api/auth/login", json=login_data)
token = res.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Get device
dev_res = requests.get("http://localhost:8000/api/devices", headers=headers)
device_id = dev_res.json()["data"]["devices"][0]["device_id"]
print(f"Device ID: {device_id}")

# 3. Get rules
rules_res = requests.get(f"http://localhost:8000/api/device/{device_id}/rules", headers=headers)
print("\nCURRENT RULES:")
for r in rules_res.json()["data"]["rules"]:
    print(f" - [{r.get('id')}] {r.get('rule_type')} : {r.get('target')}")

# 4. Add app rule
print("\nADDING APP RULE...")
new_rule = {
    "rule_type": "app",
    "target": "test_app.exe",
    "is_banned": True
}
add_res = requests.post(f"http://localhost:8000/api/device/{device_id}/rules", json=new_rule, headers=headers)
print("ADD RESPONSE:", add_res.json())

# 5. Get rules again
rules_res2 = requests.get(f"http://localhost:8000/api/device/{device_id}/rules", headers=headers)
print("\nNEW RULES LIST:")
for r in rules_res2.json()["data"]["rules"]:
    print(f" - [{r.get('id')}] {r.get('rule_type')} : {r.get('target')}")

