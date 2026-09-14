import threading
import time
import requests
import logging
from utils.logger import log_debug

logger = logging.getLogger(__name__)

class FallbackClient:
    """Background poller for the Vercel backup API (failover mode).

    While FALLBACK_MODE is active (main WebSocket down), polls
    {BACKUP_SERVER_URL}/api/device/{device_id}/commands every 30s and dispatches
    queued commands through the same handler used by the WebSocket path.
    """

    POLL_INTERVAL = 5  # seconds — primary command channel (no home WS; ~5s command latency)

    def __init__(self, dispatch_callback, device_id: str, secret_token: str = "", backup_url: str = "",
                 on_offline_exceeded=None, offline_lock_seconds: int = 180,
                 on_network_restored=None):
        self.dispatch_callback = dispatch_callback
        self.device_id = str(device_id or "").strip()
        self.secret_token = str(secret_token or "").strip()
        self.backup_url = (backup_url or "").strip()
        # Anti-network-unplug: called once when offline duration crosses the threshold.
        self.on_offline_exceeded = on_offline_exceeded
        self.offline_lock_seconds = offline_lock_seconds
        # Called when connectivity is restored AFTER an anti-unplug lock fired, so
        # the agent can unlock the screen (hide the blocker).
        self.on_network_restored = on_network_restored
        self._running = False
        self._thread = None
        self._last_success_ts = None  # monotonic timestamp of last successful poll
        self._offline_locked = False   # fire callback only once until back online

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="FallbackClient-Poll")
        self._thread.start()
        log_debug("[FALLBACK] FallbackClient started.")

    def stop(self):
        self._running = False
        log_debug("[FALLBACK] FallbackClient stopped.")

    def _loop(self):
        from utils.config import BACKUP_SERVER_URL, API_KEY

        backup_url = (self.backup_url or BACKUP_SERVER_URL or "").strip()
        if not backup_url:
            log_debug("[FALLBACK] BACKUP_SERVER_URL not configured — fallback polling disabled.")
            return
        if not self.device_id:
            log_debug("[FALLBACK] device_id missing — fallback polling disabled.")
            return

        token = self.secret_token or API_KEY or ""
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Poll ALWAYS (not only in FALLBACK_MODE): the shared Supabase queue is
        # drained by this poll, so commands queued while the main link was down
        # (or during a brief outage) are still delivered after WS reconnects.
        # Use a single reusable session for connection pooling + DNS caching so a
        # flaky domain doesn't break every poll, and tolerate cold starts.
        session = requests.Session()
        while self._running:
            # Honor the configured poll interval before each fetch.
            for _ in range(self.POLL_INTERVAL):
                if not self._running:
                    return
                time.sleep(1)

            import time as _t
            now = _t.monotonic()
            if self._last_success_ts is None:
                self._last_success_ts = now

            try:
                url = f"{backup_url.rstrip('/')}/api/device/{self.device_id}/commands"
                resp = session.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    # Online again — refresh last success + reset the lock trigger.
                    self._last_success_ts = _t.monotonic()
                    if self._offline_locked:
                        self._offline_locked = False
                        log_debug("[FALLBACK] Back online — unlocking screen (anti-unplug lock).")
                        if callable(self.on_network_restored):
                            try:
                                self.on_network_restored()
                            except Exception as _e:
                                log_debug(f"[FALLBACK] on_network_restored error: {_e}")
                    data = resp.json()
                    for cmd in data.get("commands", []):
                        try:
                            self.dispatch_callback(cmd.get("command"), cmd.get("payload"))
                        except Exception as e:
                            log_debug(f"[FALLBACK] dispatch error: {e}")
                elif resp.status_code == 401:
                    log_debug("[FALLBACK] Unauthorized polling backup API — check secret_token/API_KEY.")
                elif resp.status_code == 404:
                    log_debug("[FALLBACK] Device not found polling backup API — check device_id.")
            except Exception as e:
                log_debug(f"[FALLBACK] Error polling commands: {e}")
                # Brief backoff on transient network/DNS errors so we don't hammer.
                for _ in range(3):
                    if not self._running:
                        return
                    time.sleep(1)

            offline_for = _t.monotonic() - self._last_success_ts

            # Anti-network-unplug: if offline longer than threshold and we haven't
            # already fired the lock callback, fire it exactly once.
            if (offline_for >= self.offline_lock_seconds and not self._offline_locked
                    and callable(self.on_offline_exceeded)):
                self._offline_locked = True
                log_debug(f"[FALLBACK] Offline {int(offline_for)}s >= {self.offline_lock_seconds}s — locking screen (anti network-unplug).")
                try:
                    self.on_offline_exceeded()
                except Exception as _e:
                    log_debug(f"[FALLBACK] on_offline_exceeded error: {_e}")
