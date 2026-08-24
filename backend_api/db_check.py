import sqlite3
import json

db_path = 'app.db'
conn = sqlite3.connect(db_path)
tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("Tables:", tables)

if 'devices' in tables:
    devices = conn.execute("SELECT id, device_name, is_online, last_seen, agent_version FROM devices").fetchall()
    print("Devices:", json.dumps(devices, indent=2))
else:
    print("No devices table found.")
