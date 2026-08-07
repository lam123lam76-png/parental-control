import os
import sys
from datetime import datetime
from supabase import create_client

# Add agent path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
from utils.config import SUPABASE_URL, SUPABASE_KEY, DEVICE_NAME

def push_update():
    zip_path = os.path.join(os.path.dirname(__file__), "update_ver", "agent_update.zip")
    if not os.path.exists(zip_path):
        print(f"[!] File {zip_path} khong ton tai. Hay nen file truoc.")
        return False

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"update_{timestamp}.zip"
    
    print(f"[+] Dang tai {zip_path} len Supabase Storage 'agent-updates'...")
    with open(zip_path, "rb") as f:
        file_bytes = f.read()
        
    try:
        # Upload file
        supabase.storage.from_("agent-updates").upload(path=file_name, file=file_bytes, file_options={"content-type": "application/zip", "x-upsert": "true"})
        print(f"[OK] Da tai file len Storage: {file_name}")
    except Exception as e:
        print(f"[!] Thong bao upload: {e}")

    try:
        # Cap nhat cac ban cu is_latest = False
        supabase.table("agent_versions").update({"is_latest": False}).eq("is_latest", True).execute()
        
        # Them ban moi
        supabase.table("agent_versions").insert({
            "version": f"v{timestamp}",
            "file_path": file_name,
            "is_latest": True
        }).execute()
        print("[OK] Da cap nhat bang agent_versions (is_latest = True)")

        # Them lenh force_update
        supabase.table("system_commands").insert({
            "device_name": DEVICE_NAME,
            "command": "force_update",
            "status": "pending"
        }).execute()
        print(f"[SUCCESS] DA GUI LENH FORCE_UPDATE CHO THIET BI '{DEVICE_NAME}'!")
        print("Agent tren may em ban se nhan lenh, tu tai ban moi, gia nen va khoi dong lai!")
        return True
    except Exception as e:
        print(f"[!] Loi cap nhat co so du lieu: {e}")
        return False

if __name__ == "__main__":
    push_update()

