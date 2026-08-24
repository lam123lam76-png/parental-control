import psutil
from utils.config import AGENT_PASSWORD


def get_remote_password():
    """Lấy mật khẩu từ Backend (chưa triển khai). Dùng tạm mật khẩu tĩnh từ config."""
    return AGENT_PASSWORD


def kill_agent_and_watchdog():
    killed = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info.get('cmdline') or [])
            if "main.py" in cmdline or "watchdog.py" in cmdline:
                proc.terminate()
                killed.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed

def main():
    print("=" * 50)
    print("  DỪNG PARENTAL CONTROL AGENT (YÊU CẦU MẬT KHẨU)")
    print("=" * 50)
    password = input("Nhập mật khẩu quản lý: ").strip()

    valid_password = get_remote_password()

    if password != valid_password:
        print("❌ SAI MẬT KHẨU! Không có quyền dừng phần mềm.")
        input("Nhấn Enter để thoát...")
        return

    killed = kill_agent_and_watchdog()
    if killed:
        print(f"✅ Đã dừng thành công Agent (PID: {killed})")
    else:
        print("ℹ Không tìm thấy tiến trình Agent nào đang chạy.")

    input("Nhấn Enter để thoát...")

if __name__ == "__main__":
    main()