"""
process_monitor.py — Process and Active Window Monitoring.

Provides functions to enumerate running processes and retrieve active foreground
window information for rule enforcement.
"""
import sys

import psutil


def get_running_processes() -> list[dict]:
    """
    Enumerates running processes on the system using psutil.

    Returns:
        list[dict]: A list of dictionaries containing 'pid', 'name', and 'exe'.
                    Example: [{"pid": 1234, "name": "chrome.exe", "exe": "C:\\Program Files\\..."}]
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            info = proc.info
            pid = info.get('pid')
            name = info.get('name') or ""
            exe = info.get('exe') or ""
            processes.append({
                "pid": pid,
                "name": name,
                "exe": exe
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    return processes


def get_active_window_info() -> dict:
    """
    Retrieves information about the currently active foreground window.
    On Windows, uses win32gui and win32process.

    Returns:
        dict: {"pid": int | None, "process_name": str, "window_title": str}
              Returns fallback dict if non-Windows or if win32gui fails.
    """
    fallback = {"pid": None, "process_name": "", "window_title": ""}

    if sys.platform != "win32":
        return fallback

    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return fallback

        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        process_name = ""
        if pid:
            try:
                proc = psutil.Process(pid)
                process_name = proc.name() or ""
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                process_name = ""
            except Exception:
                process_name = ""

        return {
            "pid": pid,
            "process_name": process_name,
            "window_title": title
        }
    except Exception:
        return fallback


# Supported browser process names (lowercase) — synced with WebEnforcer.DEFAULT_BROWSER_PROCESSES
_BROWSER_PROC_NAMES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    "opera.exe", "iexplore.exe", "safari.exe", "vivaldi.exe",
    "tor.exe", "arc.exe",
}


def get_all_browser_windows() -> list[dict]:
    """
    Enumerates ALL visible browser windows (not just the foreground window).

    Uses win32gui.EnumWindows to iterate over all top-level windows and
    returns those whose owning process is a known web browser.

    Returns:
        list[dict]: List of dicts with 'pid', 'process_name', 'window_title'
                    for every visible browser window.
                    Returns empty list on non-Windows or if win32gui is unavailable.
    """
    results = []

    if sys.platform != "win32":
        return results

    try:
        import win32gui
        import win32process

        def _enum_callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return True
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if not pid:
                    return True
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name() or ""
                except Exception:
                    return True
                if proc_name.lower() in _BROWSER_PROC_NAMES:
                    results.append({
                        "pid": pid,
                        "process_name": proc_name,
                        "window_title": title,
                    })
            except Exception:
                pass
            return True  # continue enumeration

        win32gui.EnumWindows(_enum_callback, None)
    except Exception:
        pass

    return results
