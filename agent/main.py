"""
main.py — Entry Point (Local-First Architecture v2.0)

Vai trò: Điểm khởi động chính của hệ thống.
- Mặc định Production: Khởi động Watchdog Supervisor để quản lý Core Agent & xử lý Force Update tự động.
- Chế độ Debug (--core-only / --core): Chạy trực tiếp Core Agent dành cho Lập trình viên debug.
"""
import sys
import os

# Safe stdout/stderr for PyInstaller windowed mode
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    except Exception:
        pass


def main():
    """Entry point chính."""
    # Nếu có flag --core-only hoặc --core: Chạy trực tiếp Core Agent (chế độ Debug)
    if "--core-only" in sys.argv or "--core" in sys.argv:
        print("[MAIN] Chạy trực tiếp core_agent (Chế độ Debug / Core-only)...")
        from core_agent import main as core_main
        core_main()
    else:
        # Mặc định Production: Chạy Watchdog Supervisor quản lý Core Agent & Auto Update
        print("[MAIN] Khởi động chế độ Watchdog Supervisor (Mặc định Production)...")
        try:
            from watchdog_updater import WatchdogUpdater
            watchdog = WatchdogUpdater()
            watchdog.run()
        except Exception as e:
            print(f"[ERR] Không thể chạy Watchdog ({e}). Fallback trực tiếp sang core_agent...")
            from core_agent import main as core_main
            core_main()


if __name__ == "__main__":
    main()
