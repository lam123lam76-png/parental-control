"""
command_listener.py v3 — Local-First Instant Commands.

Xử lý các lệnh tức thì từ Web App.
Instant Screenshot: Gọi queue_screenshot(supabase, db, force=True) chuẩn Local-First architecture.
Cập nhật status = 'completed' khi thành công và status = 'failed' khi lỗi.
"""
from utils.config import DEVICE_NAME
from utils.logger import log_debug
from storage.local_db import LocalDB
from monitor.screenshot import queue_screenshot
from monitor.time_checker import is_within_allowed_time
from monitor.blocker import start_blocker

# CHỐNG SPAM THỰC THI LẠI LỆNH KHI MẠNG LỖI UPDATE STATUS
_processed_command_ids = set()


def process_pending_commands(supabase):
    """
    Lắng nghe và thực thi các lệnh tức thì từ Web App.
    Các lệnh hỗ trợ: take_screenshot, force_update, pause_control, resume_control, reload_rules.
    """
    try:
        res = supabase.table("system_commands")\
            .select("*")\
            .eq("device_name", DEVICE_NAME)\
            .eq("status", "pending")\
            .execute()

        commands = res.data or []
        if not commands:
            return

        db = LocalDB()

        global _processed_command_ids

        for cmd in commands:
            cmd_id = cmd["id"]
            if cmd_id in _processed_command_ids:
                # Đã thực thi lệnh này rồi, bỏ qua để tránh spam nếu update status DB gặp sự cố mạng
                continue
            _processed_command_ids.add(cmd_id)
            if len(_processed_command_ids) > 1000:
                _processed_command_ids.clear()

            cmd_type = cmd["command"]
            print(f"[CMD] Nhận lệnh từ Web: {cmd_type}")

            cmd_success = True

            if cmd_type == "take_screenshot":
                try:
                    # Gọi hàm queue_screenshot thống nhất (chụp -> Storage upload -> pending_logs)
                    queue_screenshot(supabase, db, force=True)
                    print(f"[CMD] Đã thực thi chụp ảnh tức thì chuẩn Local-First thành công.")
                except Exception as e:
                    cmd_success = False
                    log_debug(f"[ERR] Instant screenshot command failed: {e}")
                    print(f"[ERR] Instant screenshot command failed: {e}")

            elif cmd_type in ("reload_rules", "time_config_changed", "app_rules_changed"):
                print("[CMD] Nhận lệnh reload_rules -> Kéo quy tắc mới...")
                try:
                    from storage.sync_worker import SyncWorker
                    sync = SyncWorker(supabase)
                    sync.pull_rules()

                    allowed, reason = is_within_allowed_time(supabase)
                    if not allowed:
                        print(f"[CMD] [BLOCK] Ngoài giờ cho phép ngay sau khi reload: {reason}")
                        start_blocker(supabase)
                except Exception as e:
                    cmd_success = False
                    log_debug(f"[ERR] reload_rules failed: {e}")

            elif cmd_type == "force_update":
                print("[CMD] Nhận lệnh force_update -> Kéo rules & Đề Watchdog cập nhật.")
                try:
                    from storage.sync_worker import SyncWorker
                    sync = SyncWorker(supabase)
                    sync.pull_rules()
                    supabase.table("system_events").insert({
                        "device_name": DEVICE_NAME,
                        "event_type": "force_update_received",
                        "message": "Core agent received force_update. Watchdog will handle."
                    }).execute()
                except Exception as e:
                    cmd_success = False
                    log_debug(f"[ERR] force_update command failed: {e}")

            elif cmd_type in ("pause_control", "resume_control"):
                print(f"[CMD] Nhận lệnh {cmd_type}")
                try:
                    from storage.sync_worker import SyncWorker
                    sync = SyncWorker(supabase)
                    sync.pull_rules()
                except Exception as e:
                    cmd_success = False
                    log_debug(f"[ERR] {cmd_type} failed: {e}")

            else:
                print(f"[CMD] Lệnh không xác định: {cmd_type}")

            # Đánh dấu status lệnh: 'completed' nếu thành công, 'failed' nếu lỗi
            new_status = "completed" if cmd_success else "failed"
            try:
                supabase.table("system_commands")\
                    .update({"status": new_status})\
                    .eq("id", cmd_id)\
                    .execute()
                print(f"[CMD] Đã cập nhật status lệnh #{cmd_id}: {new_status}")
            except Exception as e:
                log_debug(f"[ERR] Không thể cập nhật status command #{cmd_id}: {e}")

    except Exception as e:
        log_debug(f"[ERR] Lỗi xử lý system_commands: {e}")
