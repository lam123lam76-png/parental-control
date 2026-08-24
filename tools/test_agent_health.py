#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agent_health.py — Kiểm tra sức khỏe Agent trên máy Windows
=================================================================
Cách dùng (chạy trên máy đã cài Agent):
    python test_agent_health.py

Yêu cầu: pip install psutil requests python-dotenv
"""

import os
import sys
import socket
import time
import subprocess
from pathlib import Path

# ── Màu sắc ──
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

PASS_COUNT = FAIL_COUNT = WARN_COUNT = 0


def check(name: str, status: str, detail: str = ""):
    """status: 'PASS' | 'FAIL' | 'WARN'"""
    global PASS_COUNT, FAIL_COUNT, WARN_COUNT
    icons = {"PASS": f"{GREEN}✅ PASS{RESET}",
             "FAIL": f"{RED}❌ FAIL{RESET}",
             "WARN": f"{YELLOW}⚠️  WARN{RESET}"}
    print(f"  {icons.get(status, status)}: {name}")
    if detail:
        print(f"       → {detail}")
    if status == "PASS": PASS_COUNT += 1
    elif status == "FAIL": FAIL_COUNT += 1
    else: WARN_COUNT += 1


def section(title: str):
    print(f"\n{CYAN}{BOLD}[{title}]{RESET}")


def find_agent_dir() -> Path:
    """Tìm thư mục cài đặt Agent từ vị trí phổ biến."""
    script_dir = Path(__file__).resolve().parent
    # Nếu chạy từ thư mục tools/, agent/ là anh em
    candidates = [
        script_dir.parent / "agent",
        script_dir / "agent",
        Path("C:/ParentalControl/agent"),
        Path("C:/Users") / os.getenv("USERNAME", "") / "ParentalControl/agent",
    ]
    for p in candidates:
        if (p / "main.py").exists() or (p / ".env").exists():
            return p
    return script_dir.parent  # Fallback


# ─────────────────────────────────────────────
def test_environment():
    section("1 — Môi Trường Hệ Thống")

    check("Hệ điều hành là Windows",
          "PASS" if os.name == "nt" else "FAIL",
          "Agent chỉ hỗ trợ Windows!" if os.name != "nt" else "")

    check("Python 3.9+",
          "PASS" if sys.version_info >= (3, 9) else "FAIL",
          f"Python hiện tại: {sys.version.split()[0]}")

    for lib in ["psutil", "requests", "dotenv"]:
        try:
            __import__(lib)
            check(f"Thư viện '{lib}' đã cài", "PASS")
        except ImportError:
            check(f"Thư viện '{lib}' đã cài", "FAIL",
                  f"Chạy: pip install {lib}")


def test_processes():
    section("2 — Tiến Trình Agent")
    try:
        import psutil
        names_lower = {
            (p.info.get("name") or "").lower()
            for p in psutil.process_iter(["name"])
        }

        agent_running = "parentalcontrolagent.exe" in names_lower
        watchdog_running = "parentalcontrolwatchdog.exe" in names_lower

        check("ParentalControlAgent.exe đang chạy",
              "PASS" if agent_running else "FAIL",
              "Agent không chạy — hãy khởi động lại!" if not agent_running else "")

        check("ParentalControlWatchdog.exe đang chạy",
              "PASS" if watchdog_running else "WARN",
              "Watchdog không chạy — Agent ít được bảo vệ hơn" if not watchdog_running else "")
    except ImportError:
        check("Kiểm tra tiến trình", "FAIL", "Cần cài: pip install psutil")
    except Exception as e:
        check("Kiểm tra tiến trình", "FAIL", str(e))


def test_env_file():
    section("3 — File Cấu Hình (.env)")
    agent_dir = find_agent_dir()
    env_path = agent_dir / ".env"

    if not env_path.exists():
        # Thử thư mục hiện tại
        env_path = Path(".env")

    if not env_path.exists():
        check("File .env tồn tại", "FAIL",
              f"Không tìm thấy .env tại {agent_dir}\n"
              "       Sao chép .env.example thành .env và điền giá trị!")
        return

    check("File .env tồn tại", "PASS", str(env_path))

    content = env_path.read_text(encoding="utf-8", errors="ignore")
    lines = {
        line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip()
        for line in content.splitlines()
        if "=" in line and not line.startswith("#")
    }

    required = {
        "API_KEY": "Khóa xác thực Backend",
        "DEVICE_NAME": "Tên thiết bị",
    }
    optional = {
        "AGENT_PASSWORD": "Mật khẩu mở màn hình khóa",
        "BACKEND_URL": "Địa chỉ Backend",
    }

    for key, desc in required.items():
        val = lines.get(key, "")
        is_ok = bool(val) and not val.startswith("<") and val != ""
        check(f"[Bắt buộc] {key} ({desc})",
              "PASS" if is_ok else "FAIL",
              f"Hãy thêm {key}=<giá trị> vào .env" if not is_ok else "")

    for key, desc in optional.items():
        val = lines.get(key, "")
        is_ok = bool(val) and not val.startswith("<")
        check(f"[Tùy chọn] {key} ({desc})",
              "PASS" if is_ok else "WARN",
              f"Nên đặt {key} để có đầy đủ tính năng" if not is_ok else "")


def test_connectivity():
    section("4 — Kết Nối Mạng")

    # Internet
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        check("Kết nối Internet (8.8.8.8:53)", "PASS")
    except OSError:
        check("Kết nối Internet", "FAIL",
              "Không có Internet — Agent sẽ không đồng bộ được!")

    # Backend
    try:
        import requests as req
        agent_dir = find_agent_dir()
        env_path = agent_dir / ".env"
        backend_url = "http://localhost:8000"

        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("BACKEND_URL="):
                    backend_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

        r = req.get(f"{backend_url}/api/health", timeout=5)
        check(f"Kết nối Backend ({backend_url})",
              "PASS" if r.status_code == 200 else "WARN",
              f"Nhận status {r.status_code}" if r.status_code != 200 else "")
    except Exception as e:
        check("Kết nối Backend", "WARN",
              f"Không kết nối được — {e}\n"
              "       (Bình thường nếu Backend chạy trên máy chủ khác)")


def test_registry():
    section("5 — Khởi Động Cùng Windows (Registry)")
    if os.name != "nt":
        print(f"  {YELLOW}⏭️  Bỏ qua — không phải Windows{RESET}")
        return
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, "ParentalControlAgent")
            check("Agent tự khởi động cùng Windows", "PASS",
                  f"Path: {value[:60]}...")
        except FileNotFoundError:
            check("Agent tự khởi động cùng Windows", "WARN",
                  "Chưa đăng ký Startup — Agent sẽ không tự chạy khi bật máy!")
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        check("Kiểm tra Registry", "WARN", str(e))


def test_disk_space():
    section("6 — Dung Lượng Đĩa")
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        percent_free = (free / total) * 100

        status = "PASS" if free_gb > 2 else ("WARN" if free_gb > 0.5 else "FAIL")
        check(f"Đĩa C: còn {free_gb:.1f} GB tự do ({percent_free:.0f}%)",
              status,
              "Dưới 2GB — ảnh chụp màn hình có thể không lưu được!" if free_gb <= 2 else "")
    except Exception as e:
        check("Dung lượng đĩa", "WARN", str(e))


def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  PARENTAL CONTROL — KIỂM TRA AGENT{RESET}")
    print(f"  Máy: {os.environ.get('COMPUTERNAME', 'N/A')} | User: {os.environ.get('USERNAME', 'N/A')}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"{BOLD}{'='*55}{RESET}")

    start = time.time()

    test_environment()
    test_processes()
    test_env_file()
    test_connectivity()
    test_registry()
    test_disk_space()

    elapsed = time.time() - start

    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  KẾT QUẢ: {GREEN}{PASS_COUNT} PASS{RESET} | {RED}{FAIL_COUNT} FAIL{RESET} | {YELLOW}{WARN_COUNT} WARN{RESET}")
    print(f"  Thời gian kiểm tra: {elapsed:.1f}s")

    if FAIL_COUNT == 0 and WARN_COUNT == 0:
        print(f"  {GREEN}🎉 Agent hoạt động hoàn hảo!{RESET}")
    elif FAIL_COUNT == 0:
        print(f"  {YELLOW}✅ Cơ bản ổn — xem các cảnh báo (⚠️) ở trên.{RESET}")
    elif FAIL_COUNT <= 2:
        print(f"  {YELLOW}⚠️  Có {FAIL_COUNT} vấn đề — xem hướng dẫn sửa ở trên.{RESET}")
    else:
        print(f"  {RED}❌ Agent gặp sự cố nghiêm trọng! Liên hệ Admin.{RESET}")

    print(f"{BOLD}{'='*55}{RESET}\n")

    if os.name == "nt":
        input("Nhấn Enter để đóng...")

    sys.exit(0 if FAIL_COUNT == 0 else 1)


if __name__ == "__main__":
    main()
