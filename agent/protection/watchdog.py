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

def _create_mutex_with_dacl(mutex_name: str):
    """Create a named mutex with an explicit DACL granting Everyone access.

    A plain 'Global\\' mutex created by an ELEVATED process gets a default DACL
    that denies lower-integrity processes, so they see ERROR_ACCESS_DENIED instead
    of ERROR_ALREADY_EXISTS and fail to detect the existing instance → duplicates.
    An explicit DACL (grant Everyone GENERIC_ALL) makes the mutex visible across
    integrity levels and sessions so single-instance enforcement actually holds.
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL),
        ]

    # SDDL: D:(A;;GA;;;WD)  -> Allow Everyone GENERIC_ALL on the DACL.
    sddl = "D:(A;;GA;;;WD)"
    sd_ptr = ctypes.c_void_p()
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        ctypes.c_wchar_p, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(sd_ptr), None):
        raise ctypes.WinError()

    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
    sa.lpSecurityDescriptor = sd_ptr
    sa.bInheritHandle = False

    kernel32.CreateMutexW.argtypes = [
        ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.BOOL, ctypes.c_wchar_p,
    ]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(ctypes.byref(sa), False, mutex_name)
    last_err = ctypes.get_last_error()

    # Free the security descriptor (no longer needed after CreateMutexW).
    try:
        advapi32.LocalFree(sd_ptr)
    except Exception:
        pass

    return handle, last_err


def ensure_single_instance(mutex_name: str):
    """Ensure only one instance of Watchdog runs on Windows using Named Mutex.

    Uses a mutex with an explicit Everyone DACL so the check works across
    elevated/non-elevated launches (otherwise duplicate supervisors survive).
    If the DACL helper fails (e.g. advapi32 unavailable in the frozen exe), fall
    back to a plain named mutex — but STILL exit if another instance exists. The
    previous fallback silently continued without any mutex, which disabled
    single-instance entirely and let duplicate watchdogs run side by side.
    """
    if os.name != 'nt':
        return
    import ctypes
    global _single_instance_mutex

    handle = None
    last_err = None
    try:
        handle, last_err = _create_mutex_with_dacl(mutex_name)
    except Exception as e:
        logger.warning(f"DACL mutex creation failed ({e}); falling back to plain mutex.")
    if handle is None or last_err is None:
        # Plain-mutex fallback — always keep single-instance enforcement.
        try:
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            handle = kernel32.CreateMutexW(None, False, mutex_name)
            last_err = ctypes.get_last_error()
        except Exception as e:
            logger.warning(f"Plain mutex fallback also failed: {e}")
            return
    _single_instance_mutex = handle
    if last_err == 183:  # ERROR_ALREADY_EXISTS
        logger.warning(f"Another Watchdog instance with mutex '{mutex_name}' is active. Exiting silently.")
        sys.exit(0)

_LOCK_FILE = Path(r"C:\ProgramData\ParentalControl\watchdog.lock")
_lock_fd = None


def acquire_file_lock() -> bool:
    """Acquire a single-instance lock via a byte-range file lock.

    We open (or create) the lock file and take an exclusive lock on one byte with
    msvcrt.locking (LK_NBLCK). The holder keeps the fd open for its lifetime. A
    second instance fails to take the byte lock -> another holder exists -> exit.
    This does NOT rely on PID liveness, so a reused PID can never falsely look
    alive and block a legitimate new instance (the bug that caused infinite
    agent restart loops).
    """
    global _lock_fd
    try:
        import msvcrt
        _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT
        if os.name == 'nt':
            flags |= getattr(os, "O_BINARY", 0)
        fd = os.open(str(_LOCK_FILE), flags)
        try:
            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            # Another process holds the byte lock -> another watchdog is running.
            try:
                os.close(fd)
            except Exception:
                pass
            logger.warning(f"Another Watchdog instance holds lock {_LOCK_FILE}. Exiting silently.")
            return False
        # We own the lock. Keep fd open; also record PID for diagnostics.
        _lock_fd = fd
        try:
            os.lseek(fd, 0, 0)
            os.ftruncate(fd, 0)
            os.write(fd, str(os.getpid()).encode())
        except Exception:
            pass
        logger.info(f"Acquired single-instance file lock {_LOCK_FILE} (pid={os.getpid()}).")
        return True
    except Exception as e:
        logger.warning(f"File lock error ({e}); falling through to mutex check.")
        return True  # be permissive; mutex below still guards


def _pid_alive(pid: int) -> bool:
    try:
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL('kernel32', use_last_error=True)
            k32.OpenProcess.restype = ctypes.c_void_p
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k32.CloseHandle.argtypes = [ctypes.c_void_p]
            h = k32.OpenProcess(0x1000, False, int(pid))
            if not h:
                return False
            k32.CloseHandle(h)
            return True
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def run_watchdog(target_cmd: list[str] | None = None) -> None:
    """
    Supervise target agent process with fast 3-second self-healing restart.
    """
    if not acquire_file_lock():
        sys.exit(0)
    ensure_single_instance("ParentalControlWatchdog_SingleInstance_Mutex")

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
