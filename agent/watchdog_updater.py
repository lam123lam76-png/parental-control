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
                cmd = [sys.executable, "--core"]
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
        """Lay thong tin version moi nhat"""
        try:
            # Gia su table ten la agent_versions
            response = self.supabase.table('agent_versions') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()
                
            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as e:
            print(f"[UPDATE] Error fetching version info: {e}")
        return {}

    def perform_update(self) -> bool:
        """Thuc hien qua trinh update"""
        try:
            print("[UPDATE] Starting update process...")
            self._notify("Starting agent update...")
            
            # 1. Update command status to in_progress
            if self.supabase:
                try:
                    self.supabase.table('system_commands') \
                        .update({'status': 'in_progress', 'updated_at': datetime.utcnow().isoformat()}) \
                        .eq('device_name', DEVICE_NAME) \
                        .eq('command', 'force_update') \
                        .eq('status', 'pending') \
                        .execute()
                except Exception as e:
                    print(f"[UPDATE] Warning: Failed to update command status: {e}")
            
            # 2. Get latest version info
            version_info = self.get_latest_version_info()
            if not version_info or 'file_path' not in version_info:
                raise Exception("Could not find latest version info or file_path")
                
            file_path = version_info['file_path']
            
            # 3. Download zip tu storage
            print(f"[UPDATE] Downloading {file_path}...")
            zip_bytes = self.supabase.storage.from_('agent-updates').download(file_path)
            
            # 4. Backup hien tai
            print("[UPDATE] Creating backup...")
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
                    
            # 5. Stop core
            self.stop_core_agent()
            
            # 6. Extract zip vao temp va copy de len INSTALL_DIR
            print("[UPDATE] Extracting and installing new files...")
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / 'update.zip'
                with open(zip_path, 'wb') as f:
                    f.write(zip_bytes)
                    
                extract_dir = Path(temp_dir) / 'extracted'
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    
                # Check if zip contains a single root directory
                source_dir = extract_dir
                items = list(extract_dir.iterdir())
                if len(items) == 1 and items[0].is_dir():
                    source_dir = items[0]

                # Copy files
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
                            print(f"[UPDATE] Error copying {file}: {e}")
                        
            # 7. Restart core
            print("[UPDATE] Restarting core agent...")
            self.start_core_agent()
            
            # 8. Verify
            print("[UPDATE] Waiting 15s to verify health...")
            time.sleep(15)
            if self.is_core_healthy():
                print("[UPDATE] Update successful, core is healthy.")
                self._notify("Update completed successfully.")
                if self.supabase:
                    try:
                        self.supabase.table('system_commands') \
                            .update({'status': 'completed', 'updated_at': datetime.utcnow().isoformat()}) \
                            .eq('device_name', DEVICE_NAME) \
                            .eq('command', 'force_update') \
                            .eq('status', 'in_progress') \
                            .execute()
                    except Exception:
                        pass
                return True
            else:
                print("[UPDATE] Core crashed after update. Rolling back...")
                self.rollback()
                return False
                
        except Exception as e:
            msg = f"Update failed: {e}"
            print(f"[UPDATE] {msg}")
            self._notify(msg)
            self.rollback()
            return False

    def rollback(self) -> bool:
        """Khoi phuc tu backup"""
        try:
            print("[ROLLBACK] Starting rollback...")
            self._notify("Starting rollback to previous version...")
            
            self.stop_core_agent()
            
            if not BACKUP_DIR.exists() or not any(BACKUP_DIR.iterdir()):
                print("[ROLLBACK] No backup found!")
                return False
                
            # Xoa file hien tai va copy lai tu backup
            for item in INSTALL_DIR.iterdir():
                if item.name == 'backup' or item.name == '__pycache__' or item.suffix == '.db':
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                    
            for item in BACKUP_DIR.iterdir():
                if item.is_dir():
                    shutil.copytree(item, INSTALL_DIR / item.name)
                else:
                    shutil.copy2(item, INSTALL_DIR)
                    
            print("[ROLLBACK] Restarting core agent after rollback...")
            self.start_core_agent()
            self._notify("Rollback completed.")
            return True
        except Exception as e:
            print(f"[ROLLBACK] Error during rollback: {e}")
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
