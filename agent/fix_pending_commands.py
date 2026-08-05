"""
Script dọn dẹp: Xóa tất cả lệnh 'pending' đang kẹt trong Supabase
Chạy script này 1 lần để reset trạng thái, sau đó build lại EXE
"""
from supabase import create_client

SUPABASE_URL = "https://whymvwuzjaffltkjkfoj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndoeW12d3V6amFmZmx0a2prZm9qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUzOTU4ODgsImV4cCI6MjEwMDk3MTg4OH0.Cfqfgi-1uGQlj3S2_2yI8uaNYNGTDOYawD8do7qnohI"
DEVICE_NAME = "May_Em_Trai"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Lấy tất cả lệnh pending
res = sb.table("system_commands").select("*").eq("device_name", DEVICE_NAME).eq("status", "pending").execute()
cmds = res.data or []
print(f"Tìm thấy {len(cmds)} lệnh đang pending:")
for c in cmds:
    print(f"  - ID={c['id']}, command={c['command']}")

# 2. Đánh dấu tất cả là completed
if cmds:
    sb.table("system_commands").update({"status": "completed"}).eq("device_name", DEVICE_NAME).eq("status", "pending").execute()
    print(f"✅ Đã đánh dấu {len(cmds)} lệnh là 'completed'")
else:
    print("✅ Không có lệnh nào đang pending")

# 3. Reset is_paused về False để agent hoạt động bình thường
try:
    sb.table("app_config").update({"is_paused": False}).eq("device_name", DEVICE_NAME).execute()
    print("✅ Đã reset is_paused = False")
except Exception as e:
    print(f"Lỗi reset is_paused: {e}")

print("\n🎉 XONG! Bây giờ Agent sẽ chạy bình thường sau khi cài lại.")
