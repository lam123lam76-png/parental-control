import time
import win32gui
import win32process
import psutil

def get_active_window_info():
    """Lấy thông tin cửa sổ đang được focus"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        # Lấy tiêu đề cửa sổ
        title = win32gui.GetWindowText(hwnd)
        
        # Lấy PID của process
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        process_name = "Unknown"
        try:
            process = psutil.Process(pid)
            process_name = process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return {
            "title": title,
            "process_name": process_name,
            "pid": pid
        }
    except Exception as e:
        print(f"Lỗi lấy active window: {e}")
        return None