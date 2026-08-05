"""
main.py — Entry Point (Local-First Architecture v2.0)

Vai tro: Diem khoi dong cua he thong.
Chi quyet dinh chay core_agent truc tiep hoac thong qua watchdog.

Cac che do khoi dong:
1. Mac dinh: Chay core_agent.main() truc tiep (don gian, de debug)
2. --watchdog: Chay watchdog_updater.py lam supervisor
   (watchdog se spawn va giam sat core_agent.py)
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
    """Entry point chinh."""
    if "--watchdog" in sys.argv:
        # Che do Watchdog: Chay supervisor process
        print("[MAIN] Khoi dong che do Watchdog...")
        try:
            from watchdog_updater import WatchdogUpdater
            watchdog = WatchdogUpdater()
            watchdog.run()
        except ImportError as e:
            print(f"[ERR] Khong tim thay watchdog_updater: {e}")
            print("[MAIN] Fallback sang core_agent...")
            from core_agent import main as core_main
            core_main()
    else:
        # Che do mac dinh: Chay core agent truc tiep
        print("[MAIN] Khoi dong core_agent truc tiep...")
        from core_agent import main as core_main
        core_main()


if __name__ == "__main__":
    main()