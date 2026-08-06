import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from utils.config import DEVICE_NAME
from utils.logger import log_debug
from storage.local_db import LocalDB
from monitor.screenshot import take_screenshot, make_screenshot_filename, queue_screenshot
from monitor.time_checker import is_within_allowed_time
from monitor.blocker import start_blocker

# CHỐNG SPAM THỰC THI LẠI LỆNH KHI MẠNG LỖI UPDATE STATUS
_processed_command_ids = set()

# Dedicated High-Priority Executor cho tác vụ chụp ảnh tức thì
high_priority_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="HighPriorityCmd")


def execute_instant_screenshot_async(supabase, cmd_id: int):
    """
    Worker xử lý chụp ảnh tức thì bất đồng bộ.
    Đảm bảo Chụp + Upload + Direct DB Insert hoàn tất <3s.
    """
    try:
        start_time = time.time()
        image_bytes, should_upload = take_screenshot(force_upload=True)
        if not image_bytes:
            raise Exception("Failed to capture screen image bytes")

        filename = make_screenshot_filename()

        # Upload trực tiếp lên Supabase Storage
        supabase.storage.from_("screenshots").upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )

        # Direct DB Insert vào screenshot_logs (bỏ qua hàng đợi SQLite chờ batch sync)
        supabase.table("screenshot_logs").insert({
            "device_name": DEVICE_NAME,
            "file_path": filename,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Đánh dấu completed
        supabase.table("system_commands").update({
            "status": "completed",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", cmd_id).execute()

        elapsed = time.time() - start_time
        log_debug(f"[INSTANT_CMD] Screenshot finished & logged in {elapsed:.2f}s")

    except Exception as e:
        log_debug(f"[ERR] Instant screenshot execution failed: {e}")
        try:
            supabase.table("system_commands").update({
                "status": "failed",
                "error_message": str(e)
            }).eq("id", cmd_id).execute()
        except Exception:
            pass


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
            cmd_type = cmd.get("command")

            # 1. TỰ ĐỘNG XỬ LÝ force_update TỨC THỜI CHUẨN XÁC
            if cmd_type == "force_update":
                print("[CMD] Core nhận lệnh force_update -> Kích hoạt WatchdogUpdater thực thi ngay...")
                def _do_update_async():
                    try:
                        from watchdog_updater import WatchdogUpdater
                        updater = WatchdogUpdater()
                        updater.perform_update()
                    except Exception as ex:
                        log_debug(f"[ERR] Fallback force_update failed: {ex}")
                        try:
                            supabase.table("system_commands").update({
                                "status": "failed",
                                "error_message": str(ex)
                            }).eq("id", cmd_id).execute()
                        except Exception:
                            pass

                high_priority_executor.submit(_do_update_async)
                continue

            if cmd_id in _processed_command_ids:
                continue
            _processed_command_ids.add(cmd_id)
            if len(_processed_command_ids) > 1000:
                _processed_command_ids.clear()

            print(f"[CMD] Nhận lệnh từ Web: {cmd_type}")

            if cmd_type == "take_screenshot":
                # A. Cập nhật status 'processing' ngay lập tức (<200ms)
                try:
                    supabase.table("system_commands").update({"status": "processing"}).eq("id", cmd_id).execute()
                except Exception as e:
                    log_debug(f"[ERR] Mark command processing failed: {e}")

                # B. Đưa vào High-Priority Executor xử lý bất đồng bộ
                high_priority_executor.submit(execute_instant_screenshot_async, supabase, cmd_id)
                continue

            cmd_success = True

            if cmd_type in ("reload_rules", "time_config_changed", "app_rules_changed"):
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

