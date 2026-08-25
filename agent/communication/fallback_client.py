import threading
import time
import requests
import logging
from utils.logger import log_debug

logger = logging.getLogger(__name__)

class FallbackClient:
    def __init__(self, dispatch_callback):
        self.dispatch_callback = dispatch_callback
        self._running = False
        self._thread = None
        
    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        self._running = False
        
    def _loop(self):
        from utils.config import BACKUP_SERVER_URL, API_KEY
        import utils.state as state
        import os
        
        device_id = os.getenv("DEVICE_ID") or os.getenv("DEVICE_NAME", "May_Em_Trai")
        headers = {}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
            
        while self._running:
            if state.FALLBACK_MODE and BACKUP_SERVER_URL:
                try:
                    url = f"{BACKUP_SERVER_URL.rstrip('/')}/api/device/{device_id}/commands"
                    resp = requests.get(url, headers=headers, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        for cmd in data.get("commands", []):
                            self.dispatch_callback(cmd.get("command"), cmd.get("payload"), cmd)
                except Exception as e:
                    log_debug(f"[FALLBACK] Error polling commands: {e}")
            
            time.sleep(30)
