"""
updater.py — Silent Auto-Updater Engine for Agent Machine.

Handles downloading release zip packages, extracting to staged folder,
and spawning detached update worker script to replace executable files.
"""
import logging
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Current version read from the installer-written version.json so the
# auto-update comparison matches the actual build (not a stale hardcode).
try:
    from utils.config import get_agent_version
    CURRENT_AGENT_VERSION = get_agent_version()
except Exception:
    CURRENT_AGENT_VERSION = "v0009"

class AutoUpdater:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.appdata_dir = Path(os.environ.get("APPDATA", "C:\\")) / "ParentalControl"
        self.updates_dir = self.appdata_dir / "updates"
        self.updates_dir.mkdir(parents=True, exist_ok=True)

    def trigger_silent_update(self, download_url: str, new_version: str, force: bool = True) -> bool:
        """
        Downloads update package from backend, stages update files,
        spawns detached script, and exits main process cleanly.
        """
        if not force and new_version == CURRENT_AGENT_VERSION:
            logger.info(f"[AutoUpdater] Already running latest version {new_version}. Skip update.")
            return False

        logger.info(f"[AutoUpdater] Executing update to version '{new_version}' (current: {CURRENT_AGENT_VERSION})...")

        full_url = download_url if download_url.startswith("http") else f"{self.backend_url}{download_url}"
        zip_path = self.updates_dir / "agent-update.zip"
        staged_dir = self.updates_dir / "staged"

        try:
            # 1. Download Zip package
            logger.info(f"[AutoUpdater] Downloading package from {full_url}...")
            resp = requests.get(full_url, timeout=45)
            if resp.status_code != 200:
                logger.error(f"[AutoUpdater] Download failed HTTP {resp.status_code}")
                return False

            with open(zip_path, "wb") as f:
                f.write(resp.content)

            # 2. Extract to staged directory
            logger.info(f"[AutoUpdater] Extracting to {staged_dir}...")
            if staged_dir.exists():
                shutil_rmtree_safe(staged_dir)
            staged_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(staged_dir)

            # 3. Create version.json so that check_version.ps1 and other components can read the current version
            import json
            from datetime import datetime
            version_data = {
                "version": new_version,
                "download_url": full_url,
                "updated_at": datetime.now().isoformat()
            }
            with open(self.updates_dir / "version.json", "w", encoding="utf-8") as f:
                json.dump(version_data, f, indent=4)

            # 4. Launch Updater.exe based on execution environment
            current_agent_dir = Path(__file__).parent.parent.resolve()
            
            is_frozen = getattr(sys, 'frozen', False)
            
            if is_frozen:
                # We are running as an executable created by PyInstaller
                current_exe = sys.executable
                exe_name = os.path.basename(current_exe)
                dest_dir = Path(current_exe).parent
                
                # Check staged_dir first, then fallback to current installation folder
                updater_exe = staged_dir / "Updater.exe"
                if not updater_exe.exists():
                    updater_exe = dest_dir / "Updater.exe"
                
                if updater_exe.exists():
                    logger.info(f"[AutoUpdater] Spawning {updater_exe} process and exiting...")
                    pid = str(os.getpid())
                    
                    # Set temporary shutdown flag so Watchdog doesn't race against Updater
                    try:
                        from protection.watchdog import create_shutdown_flag
                        create_shutdown_flag()
                    except Exception:
                        try:
                            from protection.watchdog import (
                                SHUTDOWN_FLAG,
                                SHUTDOWN_FLAG_SECRET,
                            )
                            SHUTDOWN_FLAG.parent.mkdir(parents=True, exist_ok=True)
                            SHUTDOWN_FLAG.write_text(SHUTDOWN_FLAG_SECRET, encoding="utf-8")
                        except Exception:
                            pass

                    subprocess.Popen([
                        str(updater_exe),
                        pid,
                        str(staged_dir),
                        str(dest_dir),
                        exe_name
                    ], cwd=str(self.updates_dir), creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    logger.error("[AutoUpdater] Updater.exe not found! Cannot apply update.")
                    return False
            else:
                # We are running as raw python scripts
                script_path = self.updates_dir / "apply_update.py"
    
                script_content = f"""import time, os, shutil, subprocess, sys
from pathlib import Path

time.sleep(2)  # Wait for main process to terminate
src_dir = r"{staged_dir}"
dest_dir = r"{current_agent_dir}"

try:
    print("[ApplyUpdate] Copying updated files...")
    for root, dirs, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, src_dir)
        target_path = os.path.join(dest_dir, rel_path)
        os.makedirs(target_path, exist_ok=True)
        for f in files:
            s_file = os.path.join(root, f)
            d_file = os.path.join(target_path, f)
            try:
                shutil.copy2(s_file, d_file)
            except Exception as ce:
                print(f"[ApplyUpdate] Skip file copy error {{f}}: {{ce}}")

    print("[ApplyUpdate] Relaunching main.py...")
    main_py = os.path.join(dest_dir, "main.py")
    subprocess.Popen([sys.executable, main_py], cwd=dest_dir)
    print("[ApplyUpdate] Update completed successfully!")
except Exception as e:
    print(f"[ApplyUpdate] Critical error applying update: {{e}}")
"""
                with open(script_path, "w", encoding="utf-8") as sf:
                    sf.write(script_content)
    
                logger.info("[AutoUpdater] Spawning detached apply_update process and exiting...")
                # Spawn detached process
                subprocess.Popen([sys.executable, str(script_path)], cwd=str(self.updates_dir))

            # Exit current agent main process
            time.sleep(0.5)
            os._exit(0)
            return True
        except Exception as e:
            logger.error(f"[AutoUpdater] Update exception: {e}")
            return False


def shutil_rmtree_safe(path: Path):
    try:
        import shutil
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass
