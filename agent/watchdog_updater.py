import os
import sys
import time
import json
import shutil
import zipfile
import tempfile
import subprocess
import signal
from datetime import datetime
from pathlib import Path
from supabase import create_client, Client

from utils.config import SUPABASE_URL, SUPABASE_KEY, DEVICE_NAME
from utils.telegram_notify import send_telegram

INSTALL_DIR = Path(r'C:\ProgramData\ParentalControl')
BACKUP_DIR = INSTALL_DIR / 'backup'
FLAG_FILE = INSTALL_DIR / 'shutdown.flag'
CORE_SCRIPT = 'core_agent.py'
HEALTH_CHECK_INTERVAL = 30  # seconds
UPDATE_CHECK_INTERVAL = 60  # seconds
MAX_CRASH_COUNT = 3
CRASH_WINDOW = 300  # 5 minutes

class WatchdogUpdater:
    def __init__(self):
        """Khoi tao watchdog va ket noi Supabase"""
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"[WATCHDOG] Supabase init failed: {e}")
            self.supabase = None
            
        self.core_process: subprocess.Popen | None = None
        self.crash_times: list[float] = []
        self.running = True
        self.last_update_check = 0.0
        
        # Tao thu muc neu chua co
        os.makedirs(INSTALL_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)

    def _notify(self, msg: str):
        print(f"[WATCHDOG] {msg}")
        try:
            send_telegram(f"[WATCHDOG] {DEVICE_NAME}: {msg}")
        except Exception:
            pass

    def start_core_agent(self) -> bool:
        """Khoi dong core_agent"""
        try:
            if FLAG_FILE.exists():
                try:
                    FLAG_FILE.unlink()
                except Exception as e:
                    print(f"[WATCHDOG] Failed to remove flag file: {e}")
            
            script_path = INSTALL_DIR / CORE_SCRIPT
            if not script_path.exists():
                # Fallback to local path for development/testing
                script_path = Path(CORE_SCRIPT).absolute()
                
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--core-only"]
                cwd_dir = os.path.dirname(sys.executable)
            else:
                cmd = [sys.executable, str(script_path)]
                cwd_dir = str(script_path.parent)

            print(f"[WATCHDOG] Starting core agent with cmd: {cmd}")
            
            # Khong hien thi cua so tren Windows
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NO_WINDOW
                
            self.core_process = subprocess.Popen(
                cmd,
                cwd=cwd_dir,
                creationflags=creationflags
            )
            
            print(f"[WATCHDOG] Core agent started with PID: {self.core_process.pid}")
            return True
        except Exception as e:
            msg = f"Failed to start core agent: {e}"
            self._notify(msg)
            return False

    def stop_core_agent(self, timeout: int = 10) -> bool:
        """Dung core_agent an toan"""
        if self.core_process is None or self.core_process.poll() is not None:
            return True
            
        try:
            print(f"[WATCHDOG] Stopping core agent, creating shutdown flag...")
            FLAG_FILE.touch()
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.core_process.poll() is not None:
                    print("[WATCHDOG] Core agent stopped gracefully.")
                    break
                time.sleep(0.5)
                
            if self.core_process.poll() is None:
                print("[WATCHDOG] Core agent timeout, forcing kill.")
                self.core_process.kill()
                self.core_process.wait()
                
            return True
        except Exception as e:
            print(f"[WATCHDOG] Error stopping core agent: {e}")
            return False
        finally:
            if FLAG_FILE.exists():
                try:
                    FLAG_FILE.unlink()
                except Exception:
                    pass
            self.core_process = None

    def is_core_healthy(self) -> bool:
        """Kiem tra xem process core_agent con chay khong"""
        try:
            if self.core_process is None:
                return False
            if self.core_process.poll() is not None:
                return False
            return True
        except Exception as e:
            print(f"[HEALTH] Error checking health: {e}")
            return False

    def check_for_update(self) -> bool:
        """Kiem tra xem co lenh cap nhat tu Supabase khong"""
        if self.supabase is None:
            return False
            
        try:
            response = self.supabase.table('system_commands') \
                .select('*') \
                .eq('device_name', DEVICE_NAME) \
                .eq('command', 'force_update') \
                .eq('status', 'pending') \
                .execute()
                
            if response.data and len(response.data) > 0:
                print("[UPDATE] Found pending update command.")
                return True
        except Exception as e:
            print(f"[UPDATE] Error checking for updates: {e}")
            
        return False

    def get_latest_version_info(self) -> dict:
        """Lấy thông tin phiên bản mới nhất từ agent_versions (ưu tiên is_latest=True)."""
        if not self.supabase:
            return {}

        # 1. Ưu tiên lấy bản ghi có is_latest = True
        try:
            res_latest = self.supabase.table('agent_versions') \
                .select('*') \
                .eq('is_latest', True) \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()
            if res_latest.data and len(res_latest.data) > 0:
                item = res_latest.data[0]
                if item.get('file_path'):
                    return item
        except Exception as e:
            print(f"[UPDATE] Error querying is_latest version: {e}")

        # 2. Fallback: Lấy bản ghi created_at mới nhất
        try:
            res_fallback = self.supabase.table('agent_versions') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()
            if res_fallback.data and len(res_fallback.data) > 0:
                item = res_fallback.data[0]
                if item.get('file_path'):
                    return item
        except Exception as e:
            print(f"[UPDATE] Error querying latest version fallback: {e}")

        return {}

    def _update_command_status(self, status: str):
        """Cập nhật trạng thái lệnh force_update trên system_commands."""
        if self.supabase:
            try:
                self.supabase.table('system_commands') \
                    .update({'status': status, 'updated_at': datetime.utcnow().isoformat()}) \
                    .eq('device_name', DEVICE_NAME) \
                    .eq('command', 'force_update') \
                    .in_('status', ['pending', 'in_progress']) \
                    .execute()
            except Exception as e:
                print(f"[UPDATE] Failed to update command status to {status}: {e}")

    def _log_system_event(self, event_type: str, message: str):
        """Ghi nhật ký sự kiện hệ thống vào Supabase system_events."""
        if self.supabase:
            try:
                self.supabase.table('system_events').insert({
                    'device_name': DEVICE_NAME,
                    'event_type': event_type,
                    'message': message,
                    'created_at': datetime.utcnow().isoformat()
                }).execute()
            except Exception as e:
                print(f"[UPDATE] Failed to log system event ({event_type}): {e}")

    def _is_backup_valid(self) -> bool:
        """Kiểm tra thư mục backup có hợp lệ và chứa file cốt lõi không."""
        if not BACKUP_DIR.exists() or not any(BACKUP_DIR.iterdir()):
            return False
        has_core = (BACKUP_DIR / 'core_agent.py').exists() or \
                   (BACKUP_DIR / 'main.py').exists() or \
                   (BACKUP_DIR / 'ParentalControlAgent.exe').exists()
        return has_core
    def perform_update(self) -> bool:
        """Thực hiện quá trình cập nhật phiên bản an toàn."""
        print("[UPDATE] Bắt đầu quá trình cập nhật...")
        self._notify("Bắt đầu tải bản cập nhật mới...")
        self._update_command_status('in_progress')

        # GIAI ĐOẠN A: LẤY THÔNG TIN VERSION VÀ DOWNLOAD ZIP
        # (Nếu lỗi ở giai đoạn này: KHÔNG stop core agent, KHÔNG đụng đến file local)
        try:
            version_info = self.get_latest_version_info()
            if not version_info or 'file_path' not in version_info:
                raise Exception("Không tìm thấy thông tin version hoặc file_path hợp lệ")

            file_path = version_info['file_path']
            print(f"[UPDATE] Đang tải bản zip {file_path}...")
            zip_bytes = self.supabase.storage.from_('agent-updates').download(file_path)
            if not zip_bytes:
                raise Exception("Tải file zip từ Storage trả về rỗng")
        except Exception as e:
            msg = f"Tải bản cập nhật thất bại: {e}"
            print(f"[UPDATE] [ERR] {msg}")
            self._notify(msg)
            self._log_system_event("update_download_failed", msg)
            self._update_command_status('failed')
            return False  # CORE AGENT VẪN ĐANG CHẠY BÌNH THƯỜNG!

        # GIAI ĐOẠN B: TẠO BACKUP TRƯỚC KHI CAN THIỆP CORE AGENT
        try:
            print("[UPDATE] Đang tạo bản sao lưu (backup)...")
            if BACKUP_DIR.exists():
                shutil.rmtree(BACKUP_DIR, ignore_errors=True)
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)

            for item in INSTALL_DIR.iterdir():
                if item.name == 'backup' or item.name == '__pycache__' or item.suffix == '.db':
                    continue
                if item.is_dir():
                    shutil.copytree(item, BACKUP_DIR / item.name)
                else:
                    shutil.copy2(item, BACKUP_DIR)

            if not self._is_backup_valid():
                raise Exception("Sao lưu thất bại: Thư mục backup không hợp lệ hoặc thiếu file cốt lõi")
        except Exception as e:
            msg = f"Tạo backup thất bại: {e}. Hủy cập nhật để bảo vệ hệ thống."
            print(f"[UPDATE] [ERR] {msg}")
            self._notify(msg)
            self._log_system_event("update_backup_failed", msg)
            self._update_command_status('failed')
            return False  # CORE AGENT VẪN ĐANG CHẠY BÌNH THƯỜNG!

        # GIAI ĐOẠN C: DỪNG CORE AGENT -> GIẢI NÉN ĐỀ FILE -> KHỞI ĐỘNG LẠI CORE
        try:
            self.stop_core_agent()

            print("[UPDATE] Đang giải nén và ghi đè phiên bản mới...")
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / 'update.zip'
                with open(zip_path, 'wb') as f:
                    f.write(zip_bytes)

                extract_dir = Path(temp_dir) / 'extracted'
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                source_dir = extract_dir
                items = list(extract_dir.iterdir())
                if len(items) == 1 and items[0].is_dir():
                    source_dir = items[0]

                for root, _, files in os.walk(source_dir):
                    rel_path = os.path.relpath(root, source_dir)
                    dest_dir = INSTALL_DIR if rel_path == '.' else INSTALL_DIR / rel_path
                    dest_dir.mkdir(parents=True, exist_ok=True)

                    for file in files:
                        src_file = Path(root) / file
                        dst_file = dest_dir / file
                        try:
                            shutil.copy2(src_file, dst_file)
                        except Exception as e:
                            print(f"[UPDATE] Lỗi copy {file}: {e}")

            print("[UPDATE] Khởi động lại Core Agent...")
            self.start_core_agent()

            # GIAI ĐOẠN D: VERIFY HEALTH (HEALTH CHECK SẢN PHẨM MỚI)
            print("[UPDATE] Đang đợi 15s để kiểm tra sức khỏe Core Agent mới...")
            time.sleep(15)
            if self.is_core_healthy():
                print("[UPDATE] Cập nhật thành công! Core Agent mới đang chạy ổn định.")
                self._notify("Cập nhật Agent thành công!")
                self._log_system_event("update_success", "Agent updated successfully.")
                self._update_command_status('completed')
                return True
            else:
                raise Exception("Core Agent mới bị crash sau 15s kiểm tra sức khỏe")

        except Exception as e:
            msg = f"Cài đặt phiên bản mới thất bại: {e}. Tiến hành Rollback an toàn..."
            print(f"[UPDATE] [ERR] {msg}")
            self._notify(msg)
            self._log_system_event("update_failed", msg)
            self.rollback()
            return False

    def rollback(self) -> bool:
        """Khôi phục hệ thống về bản backup an toàn trước đó."""
        try:
            print("[ROLLBACK] Bắt đầu quá trình khôi phục (Rollback)...")
            self._notify("Tiến hành khôi phục lại phiên bản an toàn trước đó...")

            # 1. KIỂM TRA VALIDATE BACKUP TRƯỚC KHI XÓA BẢN HIỆN TẠI
            if not self._is_backup_valid():
                msg = "[CRITICAL] Không thể Rollback: Thư mục backup không hợp lệ hoặc thiếu file cốt lõi!"
                print(f"[ROLLBACK] [ERR] {msg}")
                self._notify(msg)
                self._log_system_event("rollback_impossible", msg)
                self._update_command_status('failed')
                # Thử khởi động lại bản hiện tại nếu chưa chạy
                self.start_core_agent()
                return False

            # 2. DỪNG CORE AGENT
            self.stop_core_agent()

            # 3. XÓA FILE TRONG INSTALL_DIR (BẢO VỆ .db, backup, __pycache__)
            for item in INSTALL_DIR.iterdir():
                if item.name == 'backup' or item.name == '__pycache__' or item.suffix == '.db':
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)

            # 4. RESTORE TỪ BACKUP SANG INSTALL_DIR
            for item in BACKUP_DIR.iterdir():
                if item.is_dir():
                    shutil.copytree(item, INSTALL_DIR / item.name)
                else:
                    shutil.copy2(item, INSTALL_DIR)

            # 5. KHỞI ĐỘNG LẠI CORE AGENT VÀ HEALTH-CHECK
            print("[ROLLBACK] Đang khởi động lại Core Agent từ bản sao lưu...")
            self.start_core_agent()

            print("[ROLLBACK] Đang đợi 15s kiểm tra sức khỏe Core Agent sau khi khôi phục...")
            time.sleep(15)

            if self.is_core_healthy():
                msg = "Khôi phục (Rollback) phiên bản cũ thành công. Hệ thống đã hoạt động ổn định trở lại."
                print(f"[ROLLBACK] {msg}")
                self._notify(msg)
                self._log_system_event("rollback_success", msg)
                self._update_command_status('failed')
                return True
            else:
                msg = "[CRITICAL] Rollback thất bại: Core Agent phiên bản cũ cũng bị crash sau khi restore!"
                print(f"[ROLLBACK] [ERR] {msg}")
                self._notify(msg)
                self._log_system_event("rollback_failed", msg)
                self._update_command_status('failed')
                return False

        except Exception as e:
            msg = f"[CRITICAL] Lỗi ngoại lệ trong quá trình Rollback: {e}"
            print(f"[ROLLBACK] [ERR] {msg}")
            self._notify(msg)
            self._log_system_event("rollback_failed", msg)
            self._update_command_status('failed')
            return False
    def record_crash(self):
        """Ghi nhan su co va rollback neu can"""
        try:
            now = time.time()
            self.crash_times.append(now)
            
            # Loai bo cac lan crash cu hon CRASH_WINDOW
            self.crash_times = [t for t in self.crash_times if now - t <= CRASH_WINDOW]
            
            print(f"[HEALTH] Crash recorded. Recent crashes: {len(self.crash_times)}")
            
            if len(self.crash_times) >= MAX_CRASH_COUNT:
                print("[HEALTH] Max crash count reached. Attempting rollback...")
                self._notify(f"Core agent crashed {MAX_CRASH_COUNT} times in {CRASH_WINDOW}s. Initiating rollback.")
                self.rollback()
                self.crash_times.clear()  # Reset sau khi rollback
        except Exception as e:
            print(f"[HEALTH] Error recording crash: {e}")

    def run(self):
        """Vong lap chinh cua watchdog"""
        print("[WATCHDOG] Starting watchdog updater...")
        self.start_core_agent()
        
        while self.running:
            try:
                # 1. Health check
                if not self.is_core_healthy():
                    print("[HEALTH] Core agent is not running!")
                    self.record_crash()
                    self.start_core_agent()
                    
                # 2. Update check
                current_time = time.time()
                if current_time - self.last_update_check >= UPDATE_CHECK_INTERVAL:
                    self.last_update_check = current_time
                    if self.check_for_update():
                        self.perform_update()
                        
            except Exception as e:
                print(f"[WATCHDOG] Error in main loop: {e}")
                
            time.sleep(HEALTH_CHECK_INTERVAL)

if __name__ == '__main__':
    watchdog = WatchdogUpdater()
    try:
        watchdog.run()
    except KeyboardInterrupt:
        print("\n[WATCHDOG] Shutting down...")
        watchdog.running = False
        watchdog.stop_core_agent()
        sys.exit(0)
