"""
watchdog.py — Dual Process Supervisor for Parental Control Agent

Monitors main agent process.
If target process exits unexpectedly or is killed via Task Manager, re-launches it within 3 seconds.
Ignores restarts if shutdown signal flag is set.
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Enable silent autostart installation
try:
    from protection.autostart import get_agent_launch_cmd, install_autostart
except ImportError:
    try:
        from autostart import get_agent_launch_cmd, install_autostart
    except ImportError:
        install_autostart = None
        get_agent_launch_cmd = None

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [WATCHDOG] %(message)s")
logger = logging.getLogger("Watchdog")

# Default shutdown flag path
SHUTDOWN_FLAG = Path(r"C:\ProgramData\ParentalControl\shutdown.flag")
# Secret token that must be present inside the flag file for it to be considered valid.
# A fake empty file or file with wrong content will be deleted and ignored.
SHUTDOWN_FLAG_SECRET = "PC_WATCHDOG_SAFE_EXIT_a8f3e1b9c2d7"


def _validate_flag_file(flag_path: Path) -> bool:
    """Validate that a shutdown flag file contains the correct secret token."""
    try:
        if flag_path.exists():
            content = flag_path.read_text(encoding="utf-8").strip()
            if content == SHUTDOWN_FLAG_SECRET:
                return True
            else:
                # Fake flag detected! Delete it immediately.
                logger.warning(f"FAKE shutdown flag detected at {flag_path}! Deleting.")
                try:
                    flag_path.unlink(missing_ok=True)
                except Exception:
                    pass
                return False
    except Exception:
        pass
    return False


def is_shutdown_flag_set() -> bool:
    """Check if a valid shutdown signal flag exists (must contain correct secret)."""
    if _validate_flag_file(SHUTDOWN_FLAG):
        return True
    try:
        appdata = os.getenv("APPDATA") or os.path.expanduser("~")
        fallback_flag = Path(appdata) / "ParentalControl" / "shutdown.flag"
        if _validate_flag_file(fallback_flag):
            return True
    except Exception:
        pass
    return False


def create_shutdown_flag() -> None:
    """Create a valid shutdown flag file with the correct secret token."""
    try:
        SHUTDOWN_FLAG.parent.mkdir(parents=True, exist_ok=True)
        SHUTDOWN_FLAG.write_text(SHUTDOWN_FLAG_SECRET, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to create shutdown flag: {e}")


_single_instance_mutex = None

def ensure_single_instance(mutex_name: str):
    """Ensure only one instance of Watchdog runs on Windows using Named Mutex.

    Uses ctypes (always available, works in the frozen exe) instead of win32event,
    which can be missing from the PyInstaller bundle and silently disable the check.
    """
    if os.name == 'nt':
        try:
            import ctypes
            global _single_instance_mutex
            _single_instance_mutex = ctypes.WinDLL('kernel32', use_last_error=True).CreateMutexW(None, False, mutex_name)
            if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
                logger.warning(f"Another Watchdog instance with mutex '{mutex_name}' is active. Exiting silently.")
                sys.exit(0)
        except Exception as e:
            logger.debug(f"Watchdog single instance check fallback: {e}")

def run_watchdog(target_cmd: list[str] | None = None) -> None:
    """
    Supervise target agent process with fast 3-second self-healing restart.
    """
    ensure_single_instance("Global\\ParentalControlWatchdog_SingleInstance_Mutex")

    # Ensure Windows Registry autostart is active (never crash the supervisor
    # if HKLM writes are denied on a non-elevated token)
    if install_autostart:
        try:
            install_autostart()
        except Exception as _e:
            logger.debug(f"Autostart repair error at startup: {_e}")

    if not target_cmd:
        is_frozen = getattr(sys, 'frozen', False)
        base_dir = Path(sys.executable).parent if is_frozen else Path(__file__).resolve().parent.parent

        target_exe = base_dir / "ParentalControlAgent.exe"
        prog_data_exe = Path(r"C:\ProgramData\ParentalControl\ParentalControlAgent.exe")

        if target_exe.exists():
            target_cmd = [str(target_exe)]
        elif prog_data_exe.exists():
            target_cmd = [str(prog_data_exe)]
        else:
            main_py = base_dir / "main.py"
            python_exe = sys.executable
            pythonw_exe = Path(python_exe).parent / "pythonw.exe"
            exec_path = str(pythonw_exe) if pythonw_exe.exists() else python_exe
            target_cmd = [exec_path, str(main_py)]

    logger.info(f"Starting Dual Watchdog supervisor for: {' '.join(target_cmd)}")

    while True:
        if is_shutdown_flag_set():
            logger.info("Shutdown flag detected before launch. Exiting Watchdog.")
            break

        # Re-ensure Windows Registry autostart and Scheduled Task are active
        if install_autostart:
            try:
                install_autostart()
            except Exception as _e:
                logger.debug(f"Autostart repair error: {_e}")

        logger.info(f"Launching supervised agent process: {' '.join(target_cmd)}")
        try:
            # Create process silently without console window on Windows
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            proc = subprocess.Popen(target_cmd, creationflags=creationflags)
            
            # Monitor process loop
            exit_code = proc.wait()
            logger.info(f"Target agent process exited with code: {exit_code}")

            # Check shutdown flag
            if is_shutdown_flag_set():
                logger.info("Shutdown flag set. Stopping Watchdog supervisor gracefully.")
                break

            logger.warning(f"Target process exited with code {exit_code}. Instant self-healing: restarting agent process in 1s...")
            time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Watchdog interrupted by KeyboardInterrupt. Exiting.")
            break
        except Exception as e:
            logger.error(f"Watchdog error supervising process: {e}")
            if is_shutdown_flag_set():
                break
            logger.info("Retrying agent process in 1s...")
            time.sleep(1)


if __name__ == "__main__":
    run_watchdog()
