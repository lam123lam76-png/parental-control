import time
import subprocess
import os
import sys
import psutil
from pathlib import Path

AGENT_SCRIPT = Path(__file__).parent / "main.py"
CHECK_INTERVAL = 20  # giây

def is_agent_running():
    """Kiểm tra xem main.py có đang chạy không"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any("main.py" in str(arg) for arg in cmdline):
                # Loại trừ chính watchdog
                if "watchdog.py" not in " ".join(cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def start_agent():
    """Khởi động agent ẩn"""
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable  # fallback

    subprocess.Popen(
        [pythonw, str(AGENT_SCRIPT)],
        cwd=str(AGENT_SCRIPT.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    print(f"[{time.strftime('%H:%M:%S')}] Đã khởi động lại Agent")

def main():
    print("👁 Watchdog đang chạy... (canh Agent)")
    while True:
        if not is_agent_running():
            print(f"[{time.strftime('%H:%M:%S')}] Agent bị tắt → khởi động lại")
            start_agent()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()