"""
main.py — Main Entry Point for Desktop Agent Phase 2 MVP Architecture

Key Responsibilities:
1. Load configuration and credentials (DPAPI token / pairing check).
2. Initialize Local-First SQLite Database & HMAC integrity check.
3. Start 3-Stream Communication Engine (WebSocket, Alert Queue, Log Uploader).
4. Register command handlers & self-protection (Blocker UI, Shutdown handler).
5. Execute main enforcement loop (App, Web, Time rules scanning).
"""

import logging
import os
import sys
import threading
import time
from pathlib import Path

import requests

# Ensure stdout/stderr safe in PyInstaller windowed mode
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

# Configure root logger to output to both stream and agent_debug.log
log_handlers = []
try:
    log_file_path = Path(r"C:\ProgramData\ParentalControl\agent_debug.log")
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    log_handlers.append(logging.FileHandler(str(log_file_path), encoding='utf-8'))
except Exception:
    pass

try:
    log_handlers.append(logging.StreamHandler(sys.stdout))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger("ParentalAgent")

import config
import credential_store
from communication.alert_sender import AlertSender
from communication.log_uploader import LogUploader
from communication.ws_client import WebSocketClient
from enforcement.app_enforcer import enforce_app_rules
from enforcement.browser_tracker import BrowserTracker
from enforcement.process_monitor import (
    get_active_window_info,
    get_all_browser_windows,
    get_running_processes,
)
from enforcement.time_enforcer import check_time_rules
from enforcement.web_enforcer import enforce_web_rules
from local_store.integrity import sign_rules, verify_rules
from local_store.local_db import LocalDB
from pairing_ui import run_pairing_ui
from protection.blocker import BlockerUI
from protection.chat_window import ChatWindow
from protection.shutdown_handler import register_shutdown_handlers
from protection.updater import AutoUpdater
from screenshot_engine import ScreenshotEngine


class AgentApp:
    def __init__(self):
        self.device_id = None
        self.secret_token = None
        self.local_db = None
        self.ws_client = None
        self.alert_sender = None
        self.log_uploader = None
        self.screenshot_engine = None
        self.blocker_ui = None
        self.is_running = False
        self.rules_cache = []

    def initialize(self) -> bool:
        """Initialize configurations, credentials, and local database."""
        logger.info("Initializing Parental Control Agent Phase 2...")
        
        # 1. Check Credentials
        if not credential_store.has_credentials():
            logger.info("No credentials found. Launching Pairing UI...")
            success = run_pairing_ui(config.BACKEND_URL)
            if not success:
                logger.critical("Pairing cancelled or failed. Activating Fail-Closed lock!")
                self.trigger_fail_closed()
                return False
        
        self.device_id, self.secret_token = credential_store.load_credentials()
        if not self.device_id or not self.secret_token:
            logger.error("Failed to load credentials after pairing check.")
            return False

        logger.info(f"Loaded credentials for device_id: {self.device_id}")

        # 2. Local DB
        self.local_db = LocalDB()
        self.rules_cache = self.local_db.get_cached_rules()

        # 3. HMAC Integrity Check
        saved_hmac = self.local_db.get_meta("hmac_sig")
        if self.rules_cache and saved_hmac:
            if not verify_rules(self.rules_cache, saved_hmac, self.secret_token):
                logger.critical("RULES INTEGRITY TAMPERED! Triggering Fail-Closed state...")
                self.trigger_fail_closed()
                return False
        elif not self.rules_cache:
            # DB rỗng (thiết bị mới hoặc chưa đồng bộ rules) -> Tiếp tục khởi động để WebSocket kết nối và đồng bộ ngầm
            logger.info("Local rules cache is empty. Proceeding with startup; rules will sync via WebSocket.")

        # 4. Init Communication Engine, Screenshot Engine & Time Sync
        from utils.time_sync import SecureTime
        SecureTime.start_sync_thread()
        
        self.alert_sender = AlertSender(backend_url=config.BACKEND_URL, device_id=self.device_id)
        self.log_uploader = LogUploader(backend_url=config.BACKEND_URL, device_id=self.device_id, local_db=self.local_db)
        self.screenshot_engine = ScreenshotEngine(device_id=self.device_id, backend_url=config.BACKEND_URL, secret_token=self.secret_token)
        self.browser_tracker = BrowserTracker(device_id=self.device_id, backend_url=config.BACKEND_URL)
        self.ws_client = WebSocketClient(device_id=self.device_id, secret_token=self.secret_token, ws_url=config.WS_URL)
        self.ws_client.register_command_callback(self.handle_server_command)

        # 5. Init Blocker UI, Chat Window & AutoUpdater
        self.blocker_ui = BlockerUI(verify_password_fn=self.verify_parent_password)
        self.chat_window = ChatWindow(send_callback=self.send_chat_reply)
        self.auto_updater = AutoUpdater(backend_url=config.BACKEND_URL)

        # 6. Register Shutdown Handlers
        register_shutdown_handlers(self.on_shutdown)

        return True

    def trigger_fail_closed(self):
        """Show permanent blocker if offline rules were tampered."""
        blocker = BlockerUI()
        blocker.show("Dữ liệu quy tắc bị vi phạm tính toàn vẹn (HMAC). Thiết bị đã bị khóa an toàn!")
        import time
        while True:
            time.sleep(1)

    def handle_server_command(self, command: str, payload: dict):
        """Callback for WebSocket commands pushed from parent backend."""
        logger.info(f"Received command '{command}' with payload: {payload}")
        
        if command == "kill_process":
            proc_name = payload.get("process_name")
            pid = payload.get("pid")
            if proc_name or pid:
                logger.info(f"Executing remote command kill_process: {proc_name} / {pid}")
                for proc in get_running_processes():
                    if (pid and proc["pid"] == pid) or (proc_name and proc["name"].lower() == proc_name.lower()):
                        try:
                            import psutil
                            psutil.Process(proc["pid"]).kill()
                            logger.info(f"Killed process {proc['name']} (PID {proc['pid']})")
                        except Exception as e:
                            logger.error(f"Failed to kill process {proc['name']}: {e}")

        elif command == "lock_screen":
            reason = payload.get("reason", "Thiết bị bị khóa bởi Phụ huynh")
            logger.info("Executing remote command lock_screen")
            self.blocker_ui.show(reason)

        elif command == "unlock_screen":
            logger.info("Executing remote command unlock_screen")
            self.blocker_ui.hide()

        elif command == "chat_message":
            msg_text = payload.get("message", "")
            logger.info(f"Received chat_message from Admin: {msg_text}")
            if hasattr(self, "chat_window") and self.chat_window:
                self.chat_window.add_message("admin", msg_text)

        elif command == "force_update":
            download_url = payload.get("download_url")
            version = payload.get("version", "2.1.0")
            logger.info(f"Received force_update command: version {version} ({download_url})")
            if hasattr(self, "auto_updater") and self.auto_updater and download_url:
                threading.Thread(
                    target=self.auto_updater.trigger_silent_update,
                    args=(download_url, version),
                    daemon=True
                ).start()

        elif command == "refresh_rules":
            logger.info("Refreshing rules from payload or backend...")
            new_rules = payload.get("rules")
            if new_rules is not None:
                self.update_rules(new_rules)

        elif command == "take_screenshot":
            logger.info("Executing remote command take_screenshot")
            if hasattr(self, "screenshot_engine") and self.screenshot_engine:
                threading.Thread(target=self.screenshot_engine.capture_and_upload, daemon=True).start()

        elif command == "shutdown_pc":
            delay = int(payload.get("delay", 10))
            reason = payload.get("reason", "Thiết bị được tắt theo lệnh từ Phụ huynh")
            logger.info(f"Executing remote shutdown_pc in {delay}s: {reason}")
            try:
                if self.alert_sender:
                    self.alert_sender.send_alert(
                        device_id=self.device_id,
                        alert_type="agent_shutdown",
                        message=f"Thiết bị đang tắt nguồn theo lệnh Phụ huynh ({reason})"
                    )
            except Exception as e:
                logger.warning(f"Failed to send shutdown alert: {e}")

            # Guard against executing real OS shutdown during test / dev mode
            if not os.getenv("PC_AGENT_TEST_MODE"):
                safe_reason = reason.replace('"', '')
                cmd = f'shutdown /s /f /t {delay} /c "{safe_reason}"'
                logger.info(f"Triggering OS shutdown command: {cmd}")
                os.system(cmd)

        elif command == "check_version":
            logger.info("Executing remote command check_version")
            msg_id = payload.get("msg_id")
            version_str = "v1.0.0"
            try:
                import json
                import os
                with open(os.environ.get("APPDATA", "C:\\") + "\\ParentalControl\\updates\\version.json", "r") as f:
                    vd = json.load(f)
                    version_str = vd.get("version", version_str)
            except Exception:
                pass
            if hasattr(self, "ws_client") and self.ws_client and self.ws_client._ws:
                import json
                self.ws_client._ws.send(json.dumps({
                    "type": "version_info",
                    "msg_id": msg_id,
                    "version": version_str
                }))

    def send_chat_reply(self, text: str):
        """Callback to transmit child chat reply over WebSocket."""
        if hasattr(self, "ws_client") and self.ws_client and self.ws_client.is_connected():
            try:
                payload = {"type": "chat_message", "sender": "child", "message": text}
                self.ws_client._ws.send(json.dumps(payload))
                logger.info(f"Sent child chat reply via WebSocket: {text}")
            except Exception as e:
                logger.error(f"Failed to send WS chat reply: {e}")

    def update_rules(self, new_rules: list):
        """Update active rules cache and sign with HMAC."""
        self.rules_cache = new_rules
        sig = sign_rules(new_rules, self.secret_token)
        self.local_db.save_cached_rules(new_rules)
        self.local_db.save_meta("hmac_sig", sig)
        logger.info(f"Updated {len(new_rules)} rules and saved HMAC signature.")

    def verify_parent_password(self, password: str) -> bool:
        """Verify parent password against backend / API."""
        try:
            # We can verify via a test login call or endpoint
            res = requests.post(
                f"{config.BACKEND_URL}/api/pair",
                json={
                    "hardware_uuid": "verify",
                    "device_name": "verify",
                    "parent_email": self.local_db.get_meta("parent_email") or "",
                    "parent_password": password
                },
                timeout=5
            )
            data = res.json()
            if res.status_code == 200 or data.get("status_code") == 200:
                return True
        except Exception as e:
            logger.warning(f"Parent password verification check failed: {e}")
        return False

    def _periodic_screenshot_worker(self, interval_seconds: int = 1200):
        """Background thread to capture and upload screenshots periodically (default: 20 mins)."""
        logger.info(f"Periodic screenshot worker started (interval: {interval_seconds}s)")
        while self.is_running:
            for _ in range(int(interval_seconds)):
                if not self.is_running:
                    break
                time.sleep(1)
            
            if self.is_running and self.screenshot_engine:
                try:
                    logger.info("Triggering periodic screenshot upload...")
                    self.screenshot_engine.capture_and_upload()
                except Exception as e:
                    logger.error(f"Error in periodic screenshot worker: {e}")

    def on_shutdown(self, reason: str = "Agent process terminating gracefully."):
        """Graceful shutdown callback."""
        logger.info("Agent shutting down gracefully...")
        self.is_running = False

        if self.alert_sender:
            self.alert_sender.send_alert_direct(self.device_id, "agent_shutdown", f"🔴 [AGENT SHUTDOWN] {reason}")
            self.alert_sender.stop()
        if self.ws_client:
            self.ws_client.stop()
        if self.log_uploader:
            self.log_uploader.stop()

    def _watchdog_guardian_worker(self):
        """Background thread ensuring ParentalControlWatchdog.exe is always active (Dual Cross-Monitoring)."""
        logger.info("Dual Cross-Monitoring Watchdog Guardian thread active.")
        is_frozen = getattr(sys, 'frozen', False)
        base_dir = Path(sys.executable).parent if is_frozen else Path(__file__).resolve().parent

        watchdog_exe = base_dir / "ParentalControlWatchdog.exe"
        prog_data_exe = Path(r"C:\ProgramData\ParentalControl\ParentalControlWatchdog.exe")

        while self.is_running:
            time.sleep(1.5)
            if not self.is_running:
                break

            watchdog_active = False
            try:
                import psutil
                for proc_obj in psutil.process_iter(['name', 'cmdline']):
                    try:
                        pname = (proc_obj.info.get('name') or "").lower()
                        cmd_args = proc_obj.info.get('cmdline') or []
                        cmd_str = " ".join(cmd_args).lower()
                        if "parentalcontrolwatchdog" in pname or "watchdog.py" in cmd_str:
                            watchdog_active = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception as _e:
                logger.debug(f"Process check error: {_e}")

            if not watchdog_active:
                logger.warning("Watchdog process missing! Relaunching ParentalControlWatchdog...")
                target = None
                if watchdog_exe.exists():
                    target = [str(watchdog_exe)]
                elif prog_data_exe.exists():
                    target = [str(prog_data_exe)]
                else:
                    watchdog_py = base_dir / "protection" / "watchdog.py"
                    if watchdog_py.exists():
                        target = [sys.executable, str(watchdog_py)]

                if target:
                    try:
                        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        subprocess.Popen(target, creationflags=creationflags)
                        logger.info("Successfully re-spawned Watchdog process.")
                    except Exception as e:
                        logger.error(f"Failed to re-spawn Watchdog: {e}")

    def run(self):
        """Main enforcement loop."""
        if not self.initialize():
            return

        self.is_running = True

        # Start communication workers
        self.alert_sender.start()
        self.log_uploader.start()
        self.ws_client.start()

        # Send Online Notification to Backend
        if self.alert_sender:
            self.alert_sender.send_alert(self.device_id, "agent_online", "🟢 [ONLINE] Agent vừa khởi động và đã kết nối!")

        # Start Dual Cross-Monitoring Watchdog Guardian thread
        watchdog_guardian = threading.Thread(
            target=self._watchdog_guardian_worker,
            daemon=True
        )
        watchdog_guardian.start()

        # Start periodic screenshot thread (every 20 minutes)
        periodic_screenshot_thread = threading.Thread(
            target=self._periodic_screenshot_worker,
            args=(1200,),
            daemon=True
        )
        periodic_screenshot_thread.start()

        # Start automatic startup diagnostic & Telegram integrity report
        try:
            from diagnostic import run_diagnostic_in_background
            run_diagnostic_in_background(
                device_id=self.device_id,
                secret_token=self.secret_token,
                backend_url=config.BACKEND_URL,
                device_name=config.DEVICE_NAME
            )
        except Exception as de:
            logger.warning(f"Could not launch diagnostic: {de}")

        logger.info("Starting main enforcement loop (scan interval: %ds)...", config.PROCESS_SCAN_INTERVAL)


        _loop_counter = 0

        try:
            while self.is_running:
                loop_start = time.time()
                _loop_counter += 1
                try:
                    # ── Periodic autostart self-repair (every ~20 loops ≈ 5 min) ──
                    if _loop_counter % 20 == 0:
                        try:
                            from protection.autostart import install_autostart
                            install_autostart()
                        except Exception as _asr:
                            logger.debug(f"Autostart self-repair error: {_asr}")
                    # 1. Enumerate processes & active foreground window
                    running_procs = get_running_processes()
                    active_win = get_active_window_info()

                    # 2. Log active window & track browser history
                    if active_win.get("process_name"):
                        self.local_db.add_pending_log(
                            process_name=active_win.get("process_name"),
                            window_title=active_win.get("window_title")
                        )
                        self.browser_tracker.process_active_window(active_win)

                    # 3. Time rules check
                    allowed, time_reason = check_time_rules(self.rules_cache)
                    if not allowed:
                        if not self.blocker_ui.is_showing:
                            logger.info(f"Time rule active: {time_reason}. Displaying Blocker UI.")
                        self.blocker_ui.show(time_reason)
                    else:
                        # If blocker was shown due to time rule, hide it
                        if self.blocker_ui.is_showing and self.blocker_ui.current_reason and "lịch" in self.blocker_ui.current_reason.lower():
                            logger.info("Schedule allowed window active. Hiding Blocker UI.")
                            self.blocker_ui.hide()

                    # 4. App rules enforcement
                    enforce_app_rules(running_procs, self.rules_cache, self.alert_sender, self.device_id)

                    # 5. Web rules enforcement (Checks ALL open browser windows across monitors & background tabs)
                    browser_windows = get_all_browser_windows()
                    if not browser_windows and active_win.get("process_name"):
                        browser_windows = [active_win]
                    if browser_windows:
                        enforce_web_rules(browser_windows, self.rules_cache, self.alert_sender, self.device_id)
                except Exception as _step_err:
                    logger.error(f"Error during enforcement loop iteration: {_step_err}")

                # Sleep remaining time
                elapsed = time.time() - loop_start
                sleep_dur = max(0.5, config.PROCESS_SCAN_INTERVAL - elapsed)
                time.sleep(sleep_dur)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received.")
        finally:
            self.on_shutdown()


import subprocess
from pathlib import Path

# Reuse the validated shutdown flag from watchdog module (single source of truth)
try:
    from protection.watchdog import (
        SHUTDOWN_FLAG,
        create_shutdown_flag,
        is_shutdown_flag_set,
    )
except ImportError:
    # Fallback if import fails — use hardened inline version
    SHUTDOWN_FLAG = Path(r"C:\ProgramData\ParentalControl\shutdown.flag")
    _SHUTDOWN_SECRET = "PC_WATCHDOG_SAFE_EXIT_a8f3e1b9c2d7"
    def is_shutdown_flag_set() -> bool:
        try:
            if SHUTDOWN_FLAG.exists():
                content = SHUTDOWN_FLAG.read_text(encoding="utf-8").strip()
                if content == _SHUTDOWN_SECRET:
                    return True
                else:
                    SHUTDOWN_FLAG.unlink(missing_ok=True)
        except Exception:
            pass
        return False

_single_instance_mutex = None

def ensure_single_instance(mutex_name: str):
    """Ensure only one instance of the process runs on Windows using Named Mutex."""
    if os.name == 'nt':
        try:
            import win32api
            import win32event
            import winerror
            global _single_instance_mutex
            _single_instance_mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                logger.warning(f"Another instance with mutex '{mutex_name}' is already running. Exiting silently.")
                sys.exit(0)
        except Exception as e:
            logger.debug(f"Single instance check fallback: {e}")

def main():
    try:
        ensure_single_instance("Global\\ParentalControlAgent_SingleInstance_Mutex")
        try:
            import diagnostic
            diagnostic.run_diagnostic_in_background(
                device_id=config.DEVICE_ID,
                secret_token=config.SECRET_TOKEN,
                backend_url=config.BACKEND_URL,
                device_name=config.DEVICE_NAME
            )
        except Exception as d_e:
            logger.error(f"Failed to run diagnostic test: {d_e}")

        app = AgentApp()
        app.run()
    except Exception as e:
        logger.critical(f"Unhandled error in main execution: {e}")


if __name__ == "__main__":
    main()
