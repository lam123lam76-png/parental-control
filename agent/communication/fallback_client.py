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

    def __init__(self, dispatch_callback, device_id: str, secret_token: str = "", backup_url: str = ""):
        self.dispatch_callback = dispatch_callback
        self.device_id = str(device_id or "").strip()
        self.secret_token = str(secret_token or "").strip()
        self.backup_url = (backup_url or "").strip()
        self._running = False
        self._thread = None

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
        while self._running:
            try:
                url = f"{backup_url.rstrip('/')}/api/device/{self.device_id}/commands"
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    for cmd in data.get("commands", []):
                        try:
                            self.dispatch_callback(cmd.get("command"), cmd.get("payload"))
                        except Exception as e:
                            log_debug(f"[FALLBACK] dispatch error: {e}")
                elif resp.status_code == 401:
                    log_debug("[FALLBACK] Unauthorized polling backup API — check secret_token/API_KEY.")
            except Exception as e:
                log_debug(f"[FALLBACK] Error polling commands: {e}")

            # Sleep interruptible
            for _ in range(self.POLL_INTERVAL):
                if not self._running:
                    return
                time.sleep(1)
