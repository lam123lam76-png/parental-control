"""
updater.py — Deprecated.
Logic update da duoc chuyen sang watchdog_updater.py.
File nay giu lai de dam bao backward compatibility neu co script cu import.
"""
def download_and_apply_update(supabase) -> bool:
    print("[UPDATER] download_and_apply_update is deprecated. Use WatchdogUpdater instead.")
    try:
        from watchdog_updater import WatchdogUpdater
        watchdog = WatchdogUpdater()
        return watchdog.perform_update()
    except Exception as e:
        print(f"[UPDATER] Error delegating to WatchdogUpdater: {e}")
        return False
