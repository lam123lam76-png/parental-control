"""
sync_worker.py v2 — Batch sync local SQLite <-> Supabase Cloud.

Chay tren background thread, moi 5 phut:
1. PULL: Tai rules moi nhat tu Supabase -> ghi vao SQLite cached_rules
2. PUSH: Doc pending_logs tu SQLite -> batch insert vao Supabase -> xoa khoi SQLite
3. PUSH USAGE: Dong bo app_usage va web_usage tong hop
4. HEARTBEAT: Cap nhat devices.last_seen
"""
import time
import json
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client, Client
from storage.local_db import LocalDB
from utils.config import SUPABASE_URL, SUPABASE_KEY, DEVICE_NAME


class SyncWorker:
    """Dong bo du lieu giua SQLite local va Supabase cloud."""

    def __init__(self, supabase: Optional[Client] = None):
        try:
            self.supabase = supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"[SYNC] [ERR] Init Supabase failed: {e}")
            self.supabase = None

        self.db = LocalDB()
        self.SYNC_INTERVAL = 30  # 30 giay (Heartbeat cap nhat lien tuc)

    def pull_rules(self) -> None:
        """Keo rules moi nhat tu Supabase va luu vao SQLite cached_rules."""
        if not self.supabase:
            print("[PULL] Supabase not available, skip pull.")
            return

        print("[PULL] Bat dau lay rules tu Supabase...")

        # 1. time_restrictions
        try:
            res = self.supabase.table("time_restrictions")\
                .select("*")\
                .eq("device_name", DEVICE_NAME)\
                .eq("is_active", True)\
                .execute()
            self.db.save_cached_rules("time_restrictions", res.data or [])
            print(f"[PULL] [OK] time_restrictions: {len(res.data or [])} rules")
        except Exception as e:
            print(f"[PULL] [ERR] time_restrictions: {e}")

        # 2. app_rules
        try:
            res = self.supabase.table("app_rules")\
                .select("*")\
                .eq("device_name", DEVICE_NAME)\
                .eq("is_active", True)\
                .execute()
            self.db.save_cached_rules("app_rules", res.data or [])
            print(f"[PULL] [OK] app_rules: {len(res.data or [])} rules")
        except Exception as e:
            print(f"[PULL] [ERR] app_rules: {e}")

        # 3. web_rules
        try:
            res = self.supabase.table("web_rules")\
                .select("*")\
                .eq("device_name", DEVICE_NAME)\
                .eq("is_active", True)\
                .execute()
            self.db.save_cached_rules("web_rules", res.data or [])
            print(f"[PULL] [OK] web_rules: {len(res.data or [])} rules")
        except Exception as e:
            print(f"[PULL] [ERR] web_rules: {e}")

        # 4. app_config
        try:
            res = self.supabase.table("app_config")\
                .select("*")\
                .eq("device_name", DEVICE_NAME)\
                .execute()
            config_data = res.data[0] if res.data else {}
            self.db.save_cached_rules("app_config", config_data)
            print(f"[PULL] [OK] app_config: {bool(config_data)}")
        except Exception as e:
            print(f"[PULL] [ERR] app_config: {e}")

    def push_logs(self) -> None:
        """Day pending_logs tu SQLite len Supabase theo batch."""
        if not self.supabase:
            return

        try:
            logs = self.db.get_pending_logs(limit=500)
            if not logs:
                return

            print(f"[PUSH] Dang day {len(logs)} logs len Supabase...")

            # Nhom theo log_type
            grouped: dict[str, list] = {}
            for log in logs:
                lt = log.get("log_type", "unknown")
                if lt not in grouped:
                    grouped[lt] = []
                grouped[lt].append(log)

            # Map log_type -> Supabase table name
            type_to_table = {
                "active_window": "active_window_logs",
                "process": "process_logs",
                "browser_history": "browser_history_logs",
                "system_event": "system_events",
                "screenshot": "screenshot_logs",
            }

            synced_ids: list[int] = []

            for log_type, entries in grouped.items():
                table_name = type_to_table.get(log_type)
                if not table_name:
                    # Loai log khong xac dinh -> van xoa di
                    synced_ids.extend(e["id"] for e in entries)
                    continue

                try:
                    # data cua moi entry da la dict (LocalDB.get_pending_logs da json.loads)
                    payloads = [e["data"] for e in entries]
                    
                    # Batch insert (Supabase cho phep insert list)
                    if payloads:
                        self.supabase.table(table_name).insert(payloads).execute()
                    
                    synced_ids.extend(e["id"] for e in entries)
                    print(f"[PUSH] [OK] {table_name}: {len(payloads)} rows")
                except Exception as batch_err:
                    print(f"[PUSH] [WARN] Batch insert {table_name} error: {batch_err}. Fallback row-by-row...")
                    # CHỐNG LẶP VÔ HẠN: Thử insert từng dòng một để loại bỏ bản ghi bị lỗi cứng
                    for e in entries:
                        try:
                            self.supabase.table(table_name).insert(e["data"]).execute()
                            synced_ids.append(e["id"])
                        except Exception as row_err:
                            print(f"[PUSH] [SKIP CORRUPT LOG #{e['id']}]: {row_err}")
                            # Bỏ qua log hỏng bằng cách xóa nó đi để tránh nghẽn hàng đợi
                            synced_ids.append(e["id"])

            # Xoa cac logs da sync thanh cong
            if synced_ids:
                self.db.delete_pending_logs(synced_ids)
                print(f"[PUSH] Da xoa {len(synced_ids)} logs da sync.")

        except Exception as e:
            print(f"[PUSH] [ERR] push_logs: {e}")

    def push_usage_data(self) -> None:
        """Day du lieu su dung app va web tong hop len Supabase (upsert)."""
        if not self.supabase:
            return

        try:
            today_str = datetime.now().strftime("%Y-%m-%d")

            # 1. App usage
            app_usages = self.db.get_all_app_usage_for_date(today_str)
            if app_usages:
                try:
                    payloads = [{
                        "device_name": DEVICE_NAME,
                        "process_name": u["process_name"],
                        "usage_date": today_str,
                        "used_minutes": u["used_minutes"]
                    } for u in app_usages]

                    self.supabase.table("app_usage_logs").upsert(
                        payloads,
                        on_conflict="device_name,process_name,usage_date"
                    ).execute()
                    print(f"[PUSH] [OK] app_usage: {len(payloads)} apps")
                except Exception as e:
                    print(f"[PUSH] [ERR] app_usage upsert: {e}")

            # 2. Web usage
            web_usages = self.db.get_all_web_usage_for_date(today_str)
            if web_usages:
                try:
                    payloads = [{
                        "device_name": DEVICE_NAME,
                        "domain": u["domain"],
                        "usage_date": today_str,
                        "used_minutes": u["used_minutes"]
                    } for u in web_usages]

                    self.supabase.table("web_usage_logs").upsert(
                        payloads,
                        on_conflict="device_name,domain,usage_date"
                    ).execute()
                    print(f"[PUSH] [OK] web_usage: {len(payloads)} domains")
                except Exception as e:
                    print(f"[PUSH] [ERR] web_usage upsert: {e}")

        except Exception as e:
            print(f"[PUSH] [ERR] push_usage_data: {e}")

    def sync_once(self) -> None:
        """Thuc hien mot chu ky dong bo day du (chỉ xử lý Rules, Logs & Usage Data)."""
        print("[SYNC] --- Bat dau chu ky dong bo ---")
        self.pull_rules()
        self.push_logs()
        self.push_usage_data()
        # Ghi chú: Heartbeat đã được quản lý tập trung 1 nguồn duy nhất ở core_agent.py (Main Loop)
        print("[SYNC] --- Ket thuc chu ky dong bo ---")

    def run_forever(self) -> None:
        """Chay dong bo trong vong lap vo han (daemon thread)."""
        print(f"[SYNC] Bat dau dong bo tu dong moi {self.SYNC_INTERVAL} giay.")
        while True:
            try:
                self.sync_once()
            except Exception as e:
                print(f"[SYNC] [ERR] Unexpected: {e}")
            time.sleep(self.SYNC_INTERVAL)

    def test_connection(self) -> bool:
        """Kiem tra ket noi Supabase."""
        if not self.supabase:
            return False
        try:
            self.supabase.table("devices").select("device_name").limit(1).execute()
            print("[SYNC] [OK] Supabase connection OK.")
            return True
        except Exception as e:
            print(f"[SYNC] [ERR] Connection failed: {e}")
            return False
