"""
autostart.py — Windows Registry / Task Scheduler Auto-Start Manager
"""

import logging
import os
import sys
import winreg
from pathlib import Path

logger = logging.getLogger("AutoStart")

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ParentalControlAgent"


def get_agent_launch_cmd() -> str:
    """Returns the silent execution command for Agent."""
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        # Running as compiled PyInstaller executable (e.g. ParentalControlAgent.exe)
        prog_data_exe = Path(r"C:\ProgramData\ParentalControl\ParentalControlAgent.exe")
        if prog_data_exe.exists():
            return f'"{prog_data_exe}"'
        return f'"{sys.executable}"'

    python_exe = sys.executable
    pythonw_exe = Path(python_exe).parent / "pythonw.exe"
    exec_path = str(pythonw_exe) if pythonw_exe.exists() else python_exe
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{exec_path}" "{main_py}"'


import subprocess


def install_scheduled_task() -> bool:
    """Creates a Windows Scheduled Task to launch Watchdog every 5 minutes to ensure ultimate persistence."""
    try:
        is_frozen = getattr(sys, 'frozen', False)
        base_dir = Path(sys.executable).parent if is_frozen else Path(__file__).resolve().parent.parent
        
        watchdog_exe = base_dir / "ParentalControlWatchdog.exe"
        prog_data_exe = Path(r"C:\ProgramData\ParentalControl\ParentalControlWatchdog.exe")
        
        if watchdog_exe.exists():
            target_path = str(watchdog_exe)
        elif prog_data_exe.exists():
            target_path = str(prog_data_exe)
        else:
            watchdog_py = base_dir / "protection" / "watchdog.py"
            if watchdog_py.exists():
                target_path = f'"{sys.executable}" "{watchdog_py}"'
            else:
                return False

        # Run Watchdog every 5 minutes. If it's already running, Named Mutex will prevent duplicate execution.
        if "python.exe" in target_path or "pythonw.exe" in target_path:
            cmd = f'schtasks /create /tn "ParentalControlWatchdogTask" /tr "{target_path}" /sc minute /mo 2 /f'
        else:
            cmd = f'schtasks /create /tn "ParentalControlWatchdogTask" /tr "\\"{target_path}\\"" /sc minute /mo 2 /f'
            
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=creationflags)
        if res.returncode == 0:
            logger.info("Successfully installed Scheduled Task for Watchdog.")
            return True
        else:
            logger.error(f"Failed to install Scheduled Task: {res.stderr}")
            return False
    except Exception as e:
        logger.error(f"Scheduled task installation error: {e}")
        return False


def remove_scheduled_task() -> bool:
    """Removes the persistence Windows Scheduled Task."""
    try:
        cmd = 'schtasks /delete /tn "ParentalControlWatchdogTask" /f'
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=creationflags)
        return res.returncode == 0
    except Exception as e:
        logger.warning(f"Failed to remove Scheduled Task: {e}")
        return False


def install_autostart() -> bool:
    """Add agent silent launch command to Windows Registry Startup and setup persistence Task Scheduler."""
    success = False
    cmd = get_agent_launch_cmd()
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        logger.info(f"Successfully installed HKCU Registry autostart: {cmd}")
        success = True
    except Exception as e:
        logger.error(f"Failed to install HKCU autostart registry key: {e}")

    # Also try HKLM for system-wide persistence
    try:
        key_lm = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key_lm, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key_lm)
        logger.info(f"Successfully installed HKLM Registry autostart: {cmd}")
        success = True
    except Exception:
        pass

    # Also install scheduled task
    task_success = install_scheduled_task()
    return success or task_success


def remove_autostart() -> bool:
    """Remove agent from Windows Registry Startup and Scheduled Tasks."""
    success = False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        logger.info("Successfully removed Registry autostart.")
        success = True
    except Exception as e:
        logger.warning(f"Failed or key not found when removing autostart: {e}")

    task_removed = remove_scheduled_task()
    return success or task_removed


def is_autostart_enabled() -> bool:
    """Check if autostart registry entry exists."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "--remove" in sys.argv:
        remove_autostart()
    else:
        install_autostart()
