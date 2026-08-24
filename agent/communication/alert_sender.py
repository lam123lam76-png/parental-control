"""
alert_sender.py - HTTP Alert Sender for Luồng 2 (Tuyến Báo Động).

Target URL: POST {BACKEND_URL}/api/alerts
Payload schema: {"device_id": device_id, "alert_type": alert_type, "message": message}

Uses LocalDB for offline buffering and thread-safe alert queuing.
Worker thread processes DB queue: sends HTTP POST requests. 
If request fails, sleeps (ALERT_RETRY_INTERVAL) and retries.
"""

import os
import threading

import requests
from local_store.local_db import LocalDB
from utils.config import API_KEY
from utils.logger import log_debug


class AlertSender:
    """
    Luồng 2 (Tuyến Báo Động) HTTP Alert Sender.
    Queues alerts in SQLite and reliably delivers them to the backend server with retry logic.
    """

    ALERT_RETRY_INTERVAL = 3.0  # seconds

    def __init__(
        self,
        backend_url: str | None = None,
        device_id: str | None = None,
        retry_interval: float = ALERT_RETRY_INTERVAL,
        local_db: LocalDB | None = None,
    ):
        from utils.config import BACKEND_URL
        base_url = backend_url or BACKEND_URL
        self.backend_url = base_url.rstrip("/")
        self.device_id = device_id or os.getenv("DEVICE_ID") or os.getenv("DEVICE_NAME", "May_Em_Trai")
        self.retry_interval = retry_interval
        self.db = local_db or LocalDB()

        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._trigger_event = threading.Event()

    @property
    def alert_url(self) -> str:
        return f"{self.backend_url}/api/alerts"

    def send_alert(self, device_id: str, alert_type: str, message: str) -> None:
        """
        Enqueue an alert to be sent to the backend.
        Saves to SQLite for offline buffering.
        """
        target_device_id = device_id or self.device_id
        self.db.add_pending_alert(alert_type, message)
        self._trigger_event.set()

    def send_alert_direct(self, device_id: str, alert_type: str, message: str) -> bool:
        """
        Sends an alert immediately via synchronous HTTP POST (used for shutdown/critical alerts).
        """
        target_device_id = device_id or self.device_id
        alert_item = {
            "device_id": target_device_id,
            "alert_type": alert_type,
            "message": message,
        }
        try:
            log_debug(f"[ALERT_SENDER] Sending direct alert POST to {self.alert_url}: {alert_item}")
            res = requests.post(
                self.alert_url,
                json=alert_item,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
                timeout=5,
            )
            return 200 <= res.status_code < 300
        except Exception as e:
            log_debug(f"[ALERT_SENDER] Direct alert send failed: {e}")
            return False

    def start(self) -> None:
        """Start the background worker thread."""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="AlertSender-Worker"
        )
        self._worker_thread.start()
        log_debug("[ALERT_SENDER] Worker thread started.")

    def stop(self) -> None:
        """Stop the background worker thread gracefully and flush pending queue."""
        log_debug("[ALERT_SENDER] Stopping worker thread and flushing queue...")
        self._running = False
        self._trigger_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)
        log_debug("[ALERT_SENDER] Worker thread stopped.")

    def _worker_loop(self) -> None:
        while self._running:
            try:
                self._flush_queue()
            except Exception as e:
                log_debug(f"[ALERT_SENDER] Error in flush loop: {e}")
            
            # Wait for next interval or trigger event
            triggered = self._trigger_event.wait(timeout=self.retry_interval)
            if triggered:
                self._trigger_event.clear()

    def _flush_queue(self) -> None:
        pending_alerts = self.db.get_pending_alerts(limit=50)
        if not pending_alerts:
            return
            
        success_ids = []
        for item in pending_alerts:
            if not self._running:
                break
                
            alert_id = item.get("id")
            alert_item = {
                "device_id": self.device_id,
                "alert_type": item.get("alert_type"),
                "message": item.get("message"),
                "timestamp": item.get("timestamp")
            }
            
            try:
                log_debug(f"[ALERT_SENDER] Sending offline alert POST: {alert_item}")
                response = requests.post(
                    self.alert_url,
                    json=alert_item,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
                    timeout=10,
                )

                if 200 <= response.status_code < 300:
                    log_debug(f"[ALERT_SENDER] Alert {alert_id} sent successfully.")
                    success_ids.append(alert_id)
                else:
                    log_debug(f"[ALERT_SENDER] HTTP error {response.status_code} for alert {alert_id}: {response.text}")
                    break # Stop flushing and wait for next retry interval if network drops
            except Exception as e:
                log_debug(f"[ALERT_SENDER] Request failed for alert {alert_id}: {e}")
                break # Stop flushing if network drops
                
        if success_ids:
            self.db.delete_pending_alerts(success_ids)
