from utils.logger import log_debug
"""
core_agent.py — Clean Orchestrator (Local-First Architecture v2.0)

Vai tro: Dieu phoi toan bo cac module giam sat.
Thay the main.py cu (God Object 322 dong) bang kien truc sach:
- Ghi du lieu vao SQLite local (khong query Supabase moi vong lap)
- SyncWorker chay rieng thread de dong bo batch
- Watchdog process quan ly update va health check

Tien trinh nay duoc spawn boi watchdog_updater.py hoac main.py.
"""
import sys
import os
import time
import traceback
import threading
from datetime import datetime, timezone
from pathlib import Path
import uuid

# Safe stdout/stderr for PyInstaller windowed mode
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass

from supabase import create_client, Client

from utils.config import (
    SUPABASE_URL, SUPABASE_KEY, DEVICE_NAME, SEND_INTERVAL, get_vn_now
)
from utils.telegram_notify import send_telegram


# Monitor modules
from monitor.process_monitor import get_running_processes
from monitor.screenshot import take_screenshot, make_screenshot_filename
from monitor.active_window import get_active_window_info
from monitor.time_checker import is_within_allowed_time
from monitor.blocker import start_blocker
from monitor.network_checker import is_internet_available, check_network
from monitor.command_listener import process_pending_commands
from monitor.schedule_checker import check_current_schedule
from monitor.chat_client import check_unread_messages
from monitor.browser_history import get_browser_history
from monitor.app_rules import enforce_app_rules
from monitor.web_rules import enforce_web_rules

# Storage modules
from storage.local_db import LocalDB
from storage.sync_worker import SyncWorker


# === CONSTANTS ===
INSTALL_DIR = Path(r"C:\ProgramData\ParentalControl")
SHUTDOWN_FLAG = INSTALL_DIR / "shutdown.flag"
LOG_FILE = INSTALL_DIR / "agent_debug.log"


# log_debug imported from utils.logger


def init_supabase() -> Client:
    """Khoi tao Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERR] Thieu SUPABASE_URL hoac SUPABASE_KEY")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def is_shutdown_requested() -> bool:
    """Kiem tra co file shutdown flag tu watchdog khong."""
    return SHUTDOWN_FLAG.exists()


def get_screenshot_interval(db: LocalDB) -> int:
    """Lay cau hinh chu ky chup anh tu cached_rules."""
    try:
        config = db.get_cached_rules("app_config")
        if config and isinstance(config, dict):
            val = config.get("screenshot_interval_minutes")
            if val:
                return max(1, int(val))
    except Exception:
        pass
    return 3  # Mac dinh 3 phut


def is_control_paused(db: LocalDB) -> bool:
    """Kiem tra che do tam dung tu cached_rules."""
    try:
        config = db.get_cached_rules("app_config")
        if config and isinstance(config, dict):
            return config.get("is_paused", False) is True
    except Exception:
        pass
    return False


def check_device_permission(db: LocalDB) -> bool:
    """Kiem tra may co duoc phep hoat dong khong tu cached_rules."""
    try:
        config = db.get_cached_rules("app_config")
        if config and isinstance(config, dict):
            if config.get("is_allowed") is False:
                return False
    except Exception:
        pass
    return True  # Mac dinh cho phep


def queue_screenshot(supabase: Client, db: LocalDB, force: bool = False) -> None:
    """Chup va upload screenshot (voi image diff)."""
    try:
        image_bytes, should_upload = take_screenshot(force_upload=force)
        
        if not should_upload:
            print("[SCREENSHOT] Khong co thay doi dang ke, bo qua upload.")
            return
        
        filename = make_screenshot_filename()
        
        supabase.storage.from_("screenshots").upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        
        # Ghi vao pending_logs thay vi insert truc tiep
        db.add_pending_log("screenshot", {
            "device_name": DEVICE_NAME,
            "file_path": filename
        })
        
        print(f"[SCREENSHOT] Da chup & upload: {filename}")
    except Exception as e:
        print(f"[ERR] Screenshot: {e}")


def run_command_listener_forever(supabase: Client) -> None:
    """Chay lang nghe lenh khan cap tu Web App moi 2 giay (instant execution)."""
    print("[CMD] CommandListener thread started (polling 2s)")
    while True:
        try:
            process_pending_commands(supabase)
        except Exception as e:
            print(f"[CMD] Error in command listener thread: {e}")
        time.sleep(2)


_global_supabase = None
import signal
import atexit

def cleanup_on_exit(sig=None, frame=None):
    # Xu ly dong Agent & Gui thong bao Telegram khi Tat May / Dung Process
    try:
        print("\n[CORE] Signal / Exit detected. Updating status to OFFLINE...")
        log_debug("[CORE] OS Shutdown / Exit signal captured. Setting is_online=False...")
        try:
            from supabase import create_client
            client = _global_supabase or create_client(SUPABASE_URL, SUPABASE_KEY)
            now_iso = datetime.now(timezone.utc).isoformat()
            client.table("devices").upsert({
                "device_name": DEVICE_NAME,
                "last_seen": now_iso,
                "is_online": False
            }, on_conflict="device_name").execute()
            print("[CORE] [OK] Da cap nhat status OFFLINE len Supabase khi exit.")
        except Exception as e:
            log_debug(f"[ERR] Heartbeat set offline failed: {e}")

        try:
            send_telegram(f"🔴 [OFFLINE] Máy em trai ({DEVICE_NAME}) đã TẮT MÁY / Dừng Agent!")
        except Exception as e:
            log_debug(f"[ERR] Send Telegram shutdown failed: {e}")
    except Exception as e:
        log_debug(f"[ERR] cleanup_on_exit exception: {e}")

atexit.register(cleanup_on_exit)
try:
    signal.signal(signal.SIGINT, cleanup_on_exit)
    signal.signal(signal.SIGTERM, cleanup_on_exit)
except Exception:
    pass

class PresenceDaemon:
    """
    Dedicated Worker chuyên trách duy trì kết nối thời gian thực (Presence / Online State).
    Đảm bảo cập nhật trạng thái 'Đã kết nối' trên Web Dashboard dưới 3 giây ngay khi khởi động/có mạng.
    """
    def __init__(self, supabase_client, interval_sec: float = 3.0):
        self.supabase = supabase_client
        self.interval_sec = interval_sec
        self._running = False
        self._thread = None

    def send_fast_handshake(self) -> bool:
        if not self.supabase:
            return False
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            ping_id = f"ping_{uuid.uuid4().hex[:8]}"
            self.supabase.table("devices").upsert({
                "device_name": DEVICE_NAME,
                "last_seen": now_iso,
                "last_ping_time": now_iso,
                "ping_id": ping_id,
                "is_online": True,
                "updated_at": now_iso
            }, on_conflict="device_name").execute()
            return True
        except Exception as e:
            log_debug(f"[PRESENCE] Fast Handshake failed: {e}")
            return False

    def _loop(self):
        while self._running:
            self.send_fast_handshake()
            time.sleep(self.interval_sec)

    def start(self):
        self._running = True
        self.send_fast_handshake()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="PresenceDaemonWorker"
        )
        self._thread.start()
        log_debug("[PRESENCE] PresenceDaemon Thread started (3s interval)")

    def stop(self):
        self._running = False


def send_heartbeat(supabase) -> None:
    """Cập nhật Heartbeat thời gian thực (is_online=True) lên Supabase."""
    if not supabase:
        return
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        supabase.table("devices").upsert({
            "device_name": DEVICE_NAME,
            "last_seen": now_iso,
            "is_online": True
        }, on_conflict="device_name").execute()
    except Exception as hbe:
        log_debug(f"[ERR] Main loop heartbeat failed: {hbe}")


def run_fast_command_listener(supabase):
    """Thread rieng biet chay ngam lien tuc 1.5s/lan xu ly cac lenh tuc thi (take_screenshot, pause_control, reload_rules)."""
    while True:
        try:
            process_pending_commands(supabase)
        except Exception as e:
            log_debug(f"[ERR] Fast command listener thread error: {e}")
        time.sleep(1.5)

def main():
    """Main loop — Clean Orchestrator."""
    log_debug(f"[CORE] Agent started: {DEVICE_NAME}")
    print(f"[CORE] Agent dang khoi dong (v2.0 Local-First): {DEVICE_NAME}")
    print(f"[CORE] Chu ky: {SEND_INTERVAL} giay")

    # --- KHOI TAO ---
    try:
        global _global_supabase
        supabase = init_supabase()
        _global_supabase = supabase
        log_debug("[CORE] Supabase client OK")
    except Exception as e:
        log_debug(f"[ERR] Supabase init: {e}")
        return

    # --- PRESENCE DAEMON (Online Status <3s) ---
    presence = PresenceDaemon(supabase_client=supabase, interval_sec=3.0)
    presence.start()

    db = LocalDB()

    # --- SYNC WORKER (chay background thread) ---
    sync = SyncWorker(supabase=supabase)
    sync_thread = threading.Thread(target=sync.run_forever, daemon=True, name="SyncWorker")
    sync_thread.start()
    log_debug("[CORE] SyncWorker thread started")

    # --- COMMAND LISTENER WORKER (chay background thread 2s/lan) ---
    cmd_thread = threading.Thread(
        target=run_command_listener_forever,
        args=(supabase,),
        daemon=True,
        name="CommandListenerWorker"
    )
    cmd_thread.start()
    log_debug("[CORE] CommandListenerWorker thread started")

    # --- SYNC NGAY LAN DAU (lay rules tu cloud) ---
    try:
        sync.pull_rules()
        log_debug("[CORE] Initial pull_rules OK")
    except Exception:
        log_debug("[CORE] Initial pull_rules failed, using cached data")

    # --- THONG BAO KHOI DONG ---
    try:
        send_telegram(
            f"[AGENT] Agent da khoi dong\n"
            f"Thiet bi: {DEVICE_NAME}\n"
            f"Chu ky: {SEND_INTERVAL}s\n"
            f"Version: v2.0 Local-First\n"
            f"Thoi gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )
    except Exception as e:
        log_debug(f"[ERR] Telegram: {e}")

    # --- LOG EVENT KHOI DONG ---
    db.add_pending_log("system_event", {
        "device_name": DEVICE_NAME,
        "event_type": "agent_start",
        "message": "Agent started (v2.0 Local-First)"
    })

    # --- KIEM TRA QUYEN MO MAY ---
    if not check_device_permission(db):
        print("[BLOCK] May bi cam hoat dong boi Admin!")
        try:
            send_telegram(
                f"[BLOCK] May bi cam hoat dong\n"
                f"Thiet bi: {DEVICE_NAME}"
            )
        except Exception:
            pass
        db.add_pending_log("system_event", {
            "device_name": DEVICE_NAME,
            "event_type": "permission_denied",
            "message": "May bi cam boi Admin khi khoi dong"
        })
        unlocked = start_blocker(supabase)
        if not unlocked:
            return

    # --- MAIN LOOP ---
    last_screenshot_ts = 0
    last_violation_notify = None

    try:
        while True:
            # Kiem tra shutdown flag tu watchdog
            if is_shutdown_requested():
                print("[CORE] Shutdown flag detected, exiting gracefully...")
                log_debug("[CORE] Shutdown by watchdog flag")
                break

            # 0. CAP NHAT HEARTBEAT MOI CHU KY (LUÔN CHẠY KỂ CẢ KHI MÁY BỊ BLOCK HOẶC MẤT NET)
            send_heartbeat(supabase)

            try:
                # 0.1 KIEM TRA TIN NHAN CHAT TU ADMIN
                check_unread_messages(supabase)

                # 0.2 KIEM TRA CHE DO TAM DUNG
                paused = is_control_paused(db)
                if paused:
                    print("[PAUSE] Tam dung kiem soat")
                else:
                    # KIEM TRA QUYEN MO MAY MOI CHU KY
                    if not check_device_permission(db):
                        print("[BLOCK] May bi cam hoat dong!")
                        unlocked = start_blocker(supabase)
                        if unlocked:
                            try:
                                send_telegram(f"[UNLOCK] Da mo khoa: {DEVICE_NAME}")
                            except Exception:
                                pass
                        time.sleep(SEND_INTERVAL)
                        continue

                    # 1. KIEM TRA MANG MUC 2 BẰNG HTTP LATENCY (DNS + TCP + TLS + HTTP)
                    net_info = check_network(timeout=3.0)
                    quality = net_info.get("quality", "down")
                    latency = net_info.get("latency_ms", -1)
                    supabase_ok = net_info.get("supabase_ok", False)

                    print(f"[NET] HTTP latency={latency}ms quality={quality}")

                    if quality == "down":
                        print(f"[NET] [DOWN] Mất kết nối hoặc HTTP latency quá cao (>3500ms): latency={latency}ms supabase_ok={supabase_ok}")
                        unlocked = start_blocker(supabase)
                        if unlocked:
                            print("[NET] Đã mở khóa bằng mật khẩu")
                        time.sleep(SEND_INTERVAL)
                        continue

                    if quality == "slow":
                        print(f"[NET] [WARN] Mang kem: HTTP latency={latency}ms. Uu tien Local-First.")
                        log_debug(f"[NET] Warning slow HTTP network: {net_info}")

                    # 2. KIEM TRA LICH HOC TAP
                    is_study, study_title = check_current_schedule(supabase)
                    if is_study:
                        print(f"[STUDY] Dang trong gio hoc tap: {study_title}")

                    # 3. KIEM TRA KHUNG GIO CHO PHEP
                    allowed, reason = is_within_allowed_time(supabase)

                    if not allowed:
                        print(f"[TIME] Ngoai gio cho phep: {reason}")
                        now = datetime.now()
                        if last_violation_notify is None or (now - last_violation_notify).seconds > 600:
                            try:
                                send_telegram(
                                    f"[TIME] CANH BAO NGOAI GIO + DA KHOA MAN HINH\n"
                                    f"Thiet bi: {DEVICE_NAME}\n"
                                    f"Ly do: {reason}"
                                )
                            except Exception:
                                pass
                            db.add_pending_log("system_event", {
                                "device_name": DEVICE_NAME,
                                "event_type": "time_violation_locked",
                                "message": reason
                            })
                            last_violation_notify = now

                        unlocked = start_blocker(supabase)
                        if unlocked:
                            try:
                                send_telegram(f"[UNLOCK] Da mo khoa: {DEVICE_NAME}")
                            except Exception:
                                pass
                            db.add_pending_log("system_event", {
                                "device_name": DEVICE_NAME,
                                "event_type": "manual_unlock",
                                "message": "Unlocked with password"
                            })

                # ==== GIAM SAT LIEN TUC (chay ca khi paused) ====
                today_str = get_vn_now().strftime("%Y-%m-%d")

                # 4. TANG BOO DEM THOI GIAN SU DUNG (local theo giay thuc te)
                elapsed_seconds = float(SEND_INTERVAL)
                db.increment_usage_minutes(today_str, seconds=elapsed_seconds)

                # 5. GHI PROCESS (vao pending_logs)
                processes = get_running_processes(limit=30)
                for p in processes[:5]:  # Chi ghi top 5 tien trinh de giam spam SQLite
                    db.add_pending_log("process", {
                        "device_name": DEVICE_NAME,
                        "process_name": p["name"],
                        "pid": p["pid"],
                        "cpu_percent": p["cpu_percent"],
                        "memory_mb": p["memory_mb"]
                    })

                # 6. ENFORCE APP RULES (chi khi khong paused)
                if not paused:
                    alerts = enforce_app_rules(supabase, processes)
                    for a in alerts:
                        print(f"[APP] {a}")

                # 7. GHI ACTIVE WINDOW (vao pending_logs) VA TANG DEM APP USAGE THUC TE
                active_info = get_active_window_info()
                if active_info:
                    p_name = active_info["process_name"]
                    db.increment_app_usage(today_str, p_name, seconds=elapsed_seconds)
                    db.add_pending_log("active_window", {
                        "device_name": DEVICE_NAME,
                        "process_name": p_name,
                        "window_title": active_info["title"]
                    })
                    print(f"[WIN] {p_name} | {active_info['title'][:80]}")


                # 8. ENFORCE WEB RULES (chi khi khong paused)
                if active_info and not paused:
                    web_alerts = enforce_web_rules(supabase, active_info, processes)
                    for wa in web_alerts:
                        print(f"[WEB] {wa}")

                # 9. CHUP ANH THEO CHU KY (THOI GIAN THUC & LOCAL-FIRST QUEUE)
                interval_sec = get_screenshot_interval(db) * 60
                if time.time() - last_screenshot_ts >= interval_sec:
                    try:
                        queue_screenshot(supabase, db, force=False)
                        last_screenshot_ts = time.time()
                    except Exception as se:
                        print(f"[ERR] Auto screenshot failed: {se}")

                # 10. THU THAP LICH SU DUYET WEB
                get_browser_history(supabase)



            except Exception as e:
                # Bat moi loi trong chu ky de Agent KHONG BAO GIO chet
                error_msg = f"Loi trong chu ky: {e}"
                print(f"[ERR] {error_msg}")
                log_debug(f"{error_msg}\n{traceback.format_exc()}")

            print("-" * 50)
            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n[CORE] Agent dang tat...")

    # --- CLEANUP ---
    log_debug("[CORE] Agent shutting down")
    db.add_pending_log("system_event", {
        "device_name": DEVICE_NAME,
        "event_type": "agent_stop",
        "message": "Agent stopped"
    })
    # Sync cuoi cung truoc khi thoat
    try:
        sync.sync_once()
    except Exception:
        pass
    try:
        send_telegram(f"[AGENT] Agent da tat: {DEVICE_NAME}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
