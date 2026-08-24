"""
Agent Check Good - Comprehensive Diagnostic and Health Verification Tool
Parental Control System for Windows Target Device
"""

import ctypes
import os
import platform
import socket
import sys
import time
import traceback
from datetime import datetime

# Optional third-party imports with graceful fallback
try:
    import psutil
except ImportError:
    psutil = None

try:
    import requests
except ImportError:
    requests = None

try:
    import winreg
except ImportError:
    winreg = None

try:
    import win32crypt
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None
    win32crypt = None

try:
    import mss
    from PIL import Image
except ImportError:
    mss = None
    Image = None

try:
    import tkinter as tk
except ImportError:
    tk = None


LOG_FILE = "agent_health_debug.log"
TARGET_DIR = r"C:\ProgramData\ParentalControl"

class DiagnosticReporter:
    def __init__(self):
        self.results = []
        self.log_entries = []
        self.start_time = time.time()
        self.log_file_path = os.path.abspath(LOG_FILE)

    def log(self, level, category, message, details=None, exc_info=None):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        entry = {
            "timestamp": ts,
            "level": level,
            "category": category,
            "message": message,
            "details": details or {},
            "traceback": traceback.format_exc() if exc_info else None
        }
        self.log_entries.append(entry)

        # Write incrementally to disk
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{level:<5}] [{category:<18}] {message}\n")
                if details:
                    f.writelines(f"    |-- {k}: {v}\n" for k, v in details.items())
                if exc_info:
                    f.write("    |-- TRACEBACK:\n")
                    f.writelines(f"        {line}\n" for line in traceback.format_exc().strip().split("\n"))
        except Exception:
            pass

    def record_check(self, index, name, passed, warning=False, message="", technical_info="", fix_suggestion=""):
        status = "WARN" if warning else ("PASS" if passed else "FAIL")
        self.results.append({
            "index": index,
            "name": name,
            "status": status,
            "message": message,
            "technical_info": technical_info,
            "fix_suggestion": fix_suggestion
        })

        lvl = "WARN" if warning else ("INFO" if passed else "ERROR")
        self.log(lvl, f"CHECK_{index:02d}", f"{name} -> {status}: {message}", {
            "Technical Info": technical_info,
            "Suggestion": fix_suggestion if not passed else "None"
        })

    def write_header(self):
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("  PARENTAL CONTROL AGENT - COMPREHENSIVE HEALTH & DIAGNOSTIC LOG\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generated At      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Computer Name     : {platform.node()}\n")
                f.write(f"OS Version        : {platform.system()} {platform.release()} (Build {platform.version()})\n")
                f.write(f"Architecture      : {platform.machine()} / {platform.architecture()[0]}\n")
                f.write(f"Python / Runtime  : {sys.version.split()[0]} ({sys.executable})\n")
                f.write(f"Working Directory : {os.getcwd()}\n")
                f.write(f"Target Directory  : {TARGET_DIR}\n")
                f.write("=" * 80 + "\n\n")
        except Exception as e:
            print(f"[!] Warning: Could not initialize log file: {e}")


reporter = DiagnosticReporter()


# ============================================================================
# CHECK 1: Administrator Privileges
# ============================================================================
def check_admin_privileges():
    t0 = time.time()
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        dur_ms = int((time.time() - t0) * 1000)
        if is_admin:
            reporter.record_check(
                1, "Quyền Quản Trị (Admin Privileges)", True,
                message="Đang chạy với quyền Administrator (UAC Elevated).",
                technical_info=f"IsUserAnAdmin=True ({dur_ms}ms)"
            )
        else:
            reporter.record_check(
                1, "Quyền Quản Trị (Admin Privileges)", False,
                message="Chưa chạy dưới quyền Administrator.",
                technical_info=f"IsUserAnAdmin=False ({dur_ms}ms)",
                fix_suggestion="Chuột phải vào Agent_check_good.bat -> chọn 'Run as administrator'."
            )
    except Exception as e:
        reporter.log("ERROR", "CHECK_01", f"Admin check failed: {e}", exc_info=True)
        reporter.record_check(
            1, "Quyền Quản Trị (Admin Privileges)", False,
            message=f"Lỗi kiểm tra quyền: {e}",
            technical_info=str(e),
            fix_suggestion="Kiểm tra hệ thống Windows UAC."
        )


# ============================================================================
# CHECK 2: Directory & Files Integrity
# ============================================================================
def check_files_integrity():
    t0 = time.time()
    required_files = [
        "ParentalControlAgent.exe",
        "ParentalControlWatchdog.exe",
        "Updater.exe",
        "Install_Parental_Control.bat"
    ]
    missing = []
    file_details = {}

    if not os.path.exists(TARGET_DIR):
        reporter.record_check(
            2, "Thư Mục & Tính Toàn Vẹn Tệp Tin", False,
            message=f"Thư mục cài đặt chưa tồn tại: {TARGET_DIR}",
            technical_info="DirExists=False",
            fix_suggestion=f"Chạy Install_Parental_Control.bat để tiến hành cài đặt vào {TARGET_DIR}."
        )
        return

    for fname in required_files:
        fpath = os.path.join(TARGET_DIR, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            file_details[fname] = f"Exists ({size:,} bytes)"
            if size == 0:
                missing.append(f"{fname} (File 0 bytes)")
        else:
            missing.append(fname)
            file_details[fname] = "MISSING"

    dur_ms = int((time.time() - t0) * 1000)
    if not missing:
        reporter.record_check(
            2, "Thư Mục & Tính Toàn Vẹn Tệp Tin", True,
            message=f"Đầy đủ {len(required_files)} tệp tin thực thi chuẩn trong {TARGET_DIR}.",
            technical_info=f"All files OK ({dur_ms}ms) -> {file_details}"
        )
    else:
        reporter.record_check(
            2, "Thư Mục & Tính Toàn Vẹn Tệp Tin", False,
            message=f"Thiếu {len(missing)} tệp tin: {', '.join(missing)}",
            technical_info=f"Missing={missing} ({dur_ms}ms)",
            fix_suggestion="Chạy lại file Install_Parental_Control.bat để sao chép đầy đủ các file .exe vào thư mục đích."
        )


# ============================================================================
# CHECK 3: Running Processes (Agent & Watchdog)
# ============================================================================
def check_running_processes():
    t0 = time.time()
    if not psutil:
        reporter.record_check(
            3, "Trạng Thái Tiến Trình Hoạt Động", False,
            message="Thư viện psutil chưa sẵn sàng.",
            technical_info="psutil=None",
            fix_suggestion="Cài đặt psutil hoặc chạy từ bản build .exe đã đóng gói sẵn."
        )
        return

    agent_proc = []
    watchdog_proc = []

    try:
        for p in psutil.process_iter(['pid', 'name', 'memory_info', 'create_time', 'cpu_percent']):
            try:
                pname = p.info['name'] or ""
                if pname.lower() == "parentalcontrolagent.exe":
                    agent_proc.append(p)
                elif pname.lower() == "parentalcontrolwatchdog.exe":
                    watchdog_proc.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        reporter.log("ERROR", "CHECK_03", f"Error scanning processes: {e}", exc_info=True)

    dur_ms = int((time.time() - t0) * 1000)
    agent_ok = len(agent_proc) > 0
    watchdog_ok = len(watchdog_proc) > 0

    tech_info = {}
    if agent_ok:
        p = agent_proc[0]
        mem_mb = round(p.info['memory_info'].rss / (1024 * 1024), 1)
        tech_info["Agent"] = f"PID={p.info['pid']}, RAM={mem_mb}MB"
    else:
        tech_info["Agent"] = "NOT RUNNING"

    if watchdog_ok:
        p = watchdog_proc[0]
        mem_mb = round(p.info['memory_info'].rss / (1024 * 1024), 1)
        tech_info["Watchdog"] = f"PID={p.info['pid']}, RAM={mem_mb}MB"
    else:
        tech_info["Watchdog"] = "NOT RUNNING"

    if agent_ok and watchdog_ok:
        reporter.record_check(
            3, "Trạng Thái Tiến Trình Hoạt Động", True,
            message="Cả ParentalControlAgent và Watchdog đang hoạt động bình thường.",
            technical_info=f"{tech_info} ({dur_ms}ms)"
        )
    elif agent_ok and not watchdog_ok:
        reporter.record_check(
            3, "Trạng Thái Tiến Trình Hoạt Động", False, warning=True,
            message="Agent đang chạy nhưng Watchdog chưa bật (thiếu lớp tự bảo vệ).",
            technical_info=f"{tech_info} ({dur_ms}ms)",
            fix_suggestion=f"Khởi động {TARGET_DIR}\\ParentalControlWatchdog.exe."
        )
    else:
        reporter.record_check(
            3, "Trạng Thái Tiến Trình Hoạt Động", False,
            message="Tiến trình Agent chính chưa được khởi chạy.",
            technical_info=f"{tech_info} ({dur_ms}ms)",
            fix_suggestion=f"Chạy Install_Parental_Control.bat hoặc khởi động thủ công {TARGET_DIR}\\ParentalControlAgent.exe."
        )


# ============================================================================
# CHECK 4: Auto-Start Registry & Task Scheduler
# ============================================================================
def check_autostart_persistence():
    t0 = time.time()
    registry_found = False
    reg_val = ""

    if winreg:
        paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
        ]
        for root_key, sub_key in paths:
            try:
                key = winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(key, "ParentalControlAgent")
                winreg.CloseKey(key)
                if val:
                    registry_found = True
                    reg_val = str(val)
                    break
            except Exception:
                pass

    dur_ms = int((time.time() - t0) * 1000)
    if registry_found:
        reporter.record_check(
            4, "Đăng Ký Tự Khởi Động (Auto-Start)", True,
            message="Đã đăng ký tự khởi động cùng Windows trong Run Registry.",
            technical_info=f"RegistryKey='{reg_val}' ({dur_ms}ms)"
        )
    else:
        reporter.record_check(
            4, "Đăng Ký Tự Khởi Động (Auto-Start)", False, warning=True,
            message="Chưa tìm thấy mục đăng ký trong Registry Run.",
            technical_info=f"RegistryRun=NotFound ({dur_ms}ms)",
            fix_suggestion="Chạy Install_Parental_Control.bat để tự động thêm khóa khởi động Run."
        )


# ============================================================================
# CHECK 5: Internet Network Connectivity
# ============================================================================
def check_internet():
    t0 = time.time()
    dns_servers = [("8.8.8.8", 53), ("1.1.1.1", 53)]
    connected = False
    tested_ip = ""

    for ip, port in dns_servers:
        try:
            s = socket.create_connection((ip, port), timeout=3)
            s.close()
            connected = True
            tested_ip = f"{ip}:{port}"
            break
        except Exception:
            continue

    dur_ms = int((time.time() - t0) * 1000)
    if connected:
        reporter.record_check(
            5, "Kết Nối Mạng Internet", True,
            message=f"Kết nối Internet sẵn sàng (đáp ứng qua {tested_ip}).",
            technical_info=f"DNS Check={tested_ip} ({dur_ms}ms)"
        )
    else:
        reporter.record_check(
            5, "Kết Nối Mạng Internet", False,
            message="Không thể kết nối Internet hoặc DNS bị chặn.",
            technical_info=f"DNS Check Failed ({dur_ms}ms)",
            fix_suggestion="Kiểm tra lại kết nối mạng WiFi/LAN trên máy đích."
        )


# ============================================================================
# CHECK 6: Backend API Server Health
# ============================================================================
def check_backend_api():
    t0 = time.time()
    backend_url = os.environ.get("BACKEND_URL", "")

    # Try reading from TARGET_DIR .env or local .env
    if not backend_url:
        for env_path in [os.path.join(TARGET_DIR, ".env"), ".env", "../.env"]:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("BACKEND_URL="):
                                backend_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass
            if backend_url:
                break

    if not backend_url:
        backend_url = "http://127.0.0.1:8000"

    success = False
    status_code = None
    tested_url = ""
    error_msg = ""

    for endpoint in ["/api/health", "/api/devices", "/docs", "/api/auth/login"]:
        test_url = f"{backend_url.rstrip('/')}{endpoint}"
        try:
            if requests:
                resp = requests.get(test_url, timeout=5)
                status_code = resp.status_code
                tested_url = test_url
                if status_code in (200, 401, 403, 405):
                    success = True
                    break
        except Exception as ex:
            error_msg = str(ex)

    dur_ms = int((time.time() - t0) * 1000)
    if success:
        reporter.record_check(
            6, "Kết Nối Backend API Server", True,
            message=f"Kết nối Backend API thành công ({dur_ms}ms). Server phản hồi HTTP {status_code}.",
            technical_info=f"URL={tested_url}, Status={status_code}"
        )
    elif requests and status_code is not None:
        reporter.record_check(
            6, "Kết Nối Backend API Server", False,
            message=f"Backend API trả về mã lỗi HTTP {status_code}.",
            technical_info=f"URL={tested_url}, Code={status_code}",
            fix_suggestion="Kiểm tra trạng thái dịch vụ FastAPI backend trên máy chủ VPS."
        )
    else:
        # Fallback socket check
        try:
            parsed = backend_url.replace("http://", "").replace("https://", "").split("/")[0].split(":")
            host = parsed[0]
            port = int(parsed[1]) if len(parsed) > 1 else (443 if backend_url.startswith("https") else 80)
            s = socket.create_connection((host, port), timeout=5)
            s.close()
            reporter.record_check(
                6, "Kết Nối Backend API Server", True,
                message=f"Cổng kết nối Backend mở thành công ({host}:{port}).",
                technical_info=f"Socket connected in {dur_ms}ms"
            )
        except Exception as e:
            reporter.log("ERROR", "CHECK_06", f"Backend connection error: {e}", exc_info=True)
            reporter.record_check(
                6, "Kết Nối Backend API Server", False,
                message=f"Không thể kết nối tới Backend API ({backend_url}).",
                technical_info=f"Error: {e} ({dur_ms}ms)",
                fix_suggestion="Kiểm tra Domain/IP VPS trong .env và đảm bảo tường lửa VPS mở port 80/443."
            )


# ============================================================================
# CHECK 7: WebSocket Server Connectivity
# ============================================================================
def check_websocket_channel():
    t0 = time.time()
    ws_url = os.environ.get("WS_URL", "")

    if not ws_url:
        for env_path in [os.path.join(TARGET_DIR, ".env"), ".env", "../.env"]:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("WS_URL="):
                                ws_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass
            if ws_url:
                break

    if not ws_url:
        ws_url = "ws://127.0.0.1:8000"

    try:
        clean_host = ws_url.replace("ws://", "").replace("wss://", "").split("/")[0].split(":")
        host = clean_host[0]
        port = int(clean_host[1]) if len(clean_host) > 1 else (443 if "wss://" in ws_url else 80)
        
        s = socket.create_connection((host, port), timeout=4)
        s.close()
        dur_ms = int((time.time() - t0) * 1000)
        reporter.record_check(
            7, "Kênh Điều Khiển WebSocket Real-time", True,
            message=f"Cổng WebSocket ({host}:{port}) sẵn sàng cho kết nối 2 chiều.",
            technical_info=f"WS Target={ws_url}, Socket OK in {dur_ms}ms"
        )
    except Exception as e:
        dur_ms = int((time.time() - t0) * 1000)
        reporter.log("ERROR", "CHECK_07", f"WebSocket port unreachable: {e}", exc_info=True)
        reporter.record_check(
            7, "Kênh Điều Khiển WebSocket Real-time", False,
            message=f"Không thể kết nối đến cổng WebSocket ({ws_url}).",
            technical_info=f"Error: {e} ({dur_ms}ms)",
            fix_suggestion="Kiểm tra cấu hình Nginx Reverse Proxy hỗ trợ WebSocket (Upgrade/Connection headers)."
        )


# ============================================================================
# CHECK 8: Windows DPAPI Encryption & Token Storage
# ============================================================================
def check_dpapi_module():
    t0 = time.time()
    try:
        if not win32crypt:
            reporter.record_check(
                8, "Module Bảo Mật & Mã Hóa DPAPI", False,
                message="Thư viện win32crypt chưa được nạp.",
                technical_info="win32crypt=None",
                fix_suggestion="Đảm bảo môi trường thực thi hỗ trợ pywin32."
            )
            return

        test_secret = b"ParentalControlSecretVerificationPayload"
        encrypted = win32crypt.CryptProtectData(test_secret, "test", None, None, None, 0)
        decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1]

        dur_ms = int((time.time() - t0) * 1000)
        if decrypted == test_secret:
            reporter.record_check(
                8, "Module Bảo Mật & Mã Hóa DPAPI", True,
                message="Mã hóa và giải mã Windows DPAPI hoạt động hoàn hảo.",
                technical_info=f"DPAPI Verified ({dur_ms}ms)"
            )
        else:
            reporter.record_check(
                8, "Module Bảo Mật & Mã Hóa DPAPI", False,
                message="Giải mã DPAPI không khớp với dữ liệu gốc.",
                technical_info=f"Mismatch ({dur_ms}ms)"
            )
    except Exception as e:
        reporter.log("ERROR", "CHECK_08", f"DPAPI error: {e}", exc_info=True)
        reporter.record_check(
            8, "Module Bảo Mật & Mã Hóa DPAPI", False,
            message=f"Lỗi module mã hóa DPAPI: {e}",
            technical_info=str(e),
            fix_suggestion="Kiểm tra quyền bảo mật tài khoản Windows."
        )


# ============================================================================
# CHECK 9: Screen Capture Engine (MSS / PIL)
# ============================================================================
def check_screen_capture():
    t0 = time.time()
    try:
        if not mss or not Image:
            reporter.record_check(
                9, "Engine Chụp Màn Hình (MSS / PIL)", False,
                message="Thư viện mss hoặc Pillow chưa sẵn sàng.",
                technical_info="mss or PIL is None"
            )
            return

        # Use MSS class or mss()
        mss_cls = getattr(mss, "MSS", None) or getattr(mss, "mss", None)
        with mss_cls() as sct:
            monitors = sct.monitors
            if not monitors or len(monitors) < 2:
                primary = monitors[0] if monitors else None
            else:
                primary = monitors[1]

            if not primary:
                raise RuntimeError("Không tìm thấy màn hình hiển thị.")

            shot = sct.grab(primary)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            width, height = img.size

        dur_ms = int((time.time() - t0) * 1000)
        if width > 0 and height > 0:
            reporter.record_check(
                9, "Engine Chụp Màn Hình (MSS / PIL)", True,
                message=f"Chụp màn hình thử nghiệm thành công ({width}x{height} px, {dur_ms}ms).",
                technical_info=f"Monitors={len(monitors)-1}, Res={width}x{height}, Time={dur_ms}ms"
            )
        else:
            reporter.record_check(
                9, "Engine Chụp Màn Hình (MSS / PIL)", False,
                message="Khung hình chụp có kích thước 0x0.",
                technical_info=f"Invalid shot size ({dur_ms}ms)"
            )
    except Exception as e:
        dur_ms = int((time.time() - t0) * 1000)
        reporter.log("WARN", "CHECK_09", f"Screen capture notification: {e}", exc_info=True)
        reporter.record_check(
            9, "Engine Chụp Màn Hình (MSS / PIL)", False, warning=True,
            message=f"Lỗi chụp màn hình: {e}",
            technical_info=str(e),
            fix_suggestion="Tính năng chụp ảnh cần chạy trực tiếp trên màn hình đăng nhập của người dùng thực tế (Session 1)."
        )


# ============================================================================
# CHECK 10: Window & Process Tracking Engine
# ============================================================================
def check_window_tracking():
    t0 = time.time()
    try:
        if not win32gui or not win32process:
            reporter.record_check(
                10, "Engine Giám Sát Cửa Sổ & Ứng Dụng", False,
                message="Thư viện win32gui / win32process chưa sẵn sàng.",
                technical_info="win32gui/win32process is None"
            )
            return

        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd) if hwnd else ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd) if hwnd else (0, 0)
        pname = ""
        if pid and psutil:
            try:
                pname = psutil.Process(pid).name()
            except Exception:
                pname = "Unknown"

        dur_ms = int((time.time() - t0) * 1000)
        reporter.record_check(
            10, "Engine Giám Sát Cửa Sổ & Ứng Dụng", True,
            message=f"Bắt tiêu đề cửa sổ và tiến trình hoạt động tốt ({dur_ms}ms).",
            technical_info=f"HWND={hwnd}, PID={pid}, Process='{pname}', Title='{window_title[:40]}'"
        )
    except Exception as e:
        reporter.log("ERROR", "CHECK_10", f"Window tracking error: {e}", exc_info=True)
        reporter.record_check(
            10, "Engine Giám Sát Cửa Sổ & Ứng Dụng", False,
            message=f"Lỗi bắt thông tin cửa sổ: {e}",
            technical_info=str(e)
        )


# ============================================================================
# CHECK 11: Blocker & UI Layer (Tkinter)
# ============================================================================
def check_blocker_ui():
    t0 = time.time()
    try:
        if not tk:
            reporter.record_check(
                11, "Module Màn Hình Khóa (Tkinter UI)", False,
                message="Thư viện Tkinter không khả dụng.",
                technical_info="tkinter=None"
            )
            return

        root = tk.Tk()
        root.withdraw()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.destroy()

        dur_ms = int((time.time() - t0) * 1000)
        reporter.record_check(
            11, "Module Màn Hình Khóa (Tkinter UI)", True,
            message=f"Giao diện đồ họa Tkinter khởi tạo tốt ({sw}x{sh} px, {dur_ms}ms).",
            technical_info=f"Tkinter Root OK, Screen={sw}x{sh}"
        )
    except Exception as e:
        reporter.log("ERROR", "CHECK_11", f"Tkinter initialization error: {e}", exc_info=True)
        reporter.record_check(
            11, "Module Màn Hình Khóa (Tkinter UI)", False,
            message=f"Lỗi khởi tạo giao diện màn hình khóa: {e}",
            technical_info=str(e),
            fix_suggestion="Kiểm tra môi trường desktop graphical session."
        )


# ============================================================================
# MAIN RUNNER & CONSOLE CHECKLIST FORMATTER
# ============================================================================
def main():
    reporter.write_header()

    print("==============================================================================")
    print("      PARENTAL CONTROL AGENT - KIEM TRA TOAN DIEN HE THONG (DIAGNOSTIC)")
    print("==============================================================================")
    print(f"[*] Thoi gian bat dau : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] May dich          : {platform.node()} ({platform.system()} {platform.release()})")
    print(f"[*] Thu muc cai dat   : {TARGET_DIR}")
    print(f"[*] File log chi tiet : {reporter.log_file_path}")
    print("------------------------------------------------------------------------------\n")

    # Run all 11 diagnostic checks
    check_admin_privileges()
    check_files_integrity()
    check_running_processes()
    check_autostart_persistence()
    check_internet()
    check_backend_api()
    check_websocket_channel()
    check_dpapi_module()
    check_screen_capture()
    check_window_tracking()
    check_blocker_ui()

    # Print Pretty Console Checklist
    passed_count = sum(1 for r in reporter.results if r["status"] == "PASS")
    warn_count = sum(1 for r in reporter.results if r["status"] == "WARN")
    fail_count = sum(1 for r in reporter.results if r["status"] == "FAIL")
    total_count = len(reporter.results)

    for r in reporter.results:
        idx = r["index"]
        name = r["name"]
        status = r["status"]
        msg = r["message"]

        if status == "PASS":
            tag = "[ PASS ]"
        elif status == "WARN":
            tag = "[ WARN ]"
        else:
            tag = "[ FAIL ]"

        print(f"{tag} {idx:02d}. {name}")
        print(f"         + Ket qua: {msg}")
        if r.get("fix_suggestion") and status != "PASS":
            print(f"         + Huong dan sua: {r['fix_suggestion']}")
        print()

    print("==============================================================================")
    print(f"KET QUA TONG THE: {passed_count}/{total_count} PASSED | {warn_count} WARNINGS | {fail_count} FAILED")
    print("==============================================================================")
    
    if fail_count == 0 and warn_count == 0:
        print("[SUCCESS] AGENT HOAT DONG HOAN HAO VA SAN SANG 100%!")
    elif fail_count == 0:
        print("[NOTICE] Agent co the hoat dong nhung can luu y cac canh bao tren.")
    else:
        print(f"[ERROR] Phat hien {fail_count} loi can xu ly! Vui long xem file log de debug:")
        print(f"        -> {reporter.log_file_path}")
    print("==============================================================================\n")


if __name__ == "__main__":
    main()