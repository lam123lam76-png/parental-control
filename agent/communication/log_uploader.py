"""
log_uploader.py - Batch Log Uploader for Luồng 3 (Tuyến Xe Tải).

Target URL: POST {BACKEND_URL}/api/logs/batch
Payload schema: {"device_id": device_id, "logs": [{"process_name": ..., "window_title": ..., "timestamp": ...}]}

Worker thread runs every LOG_BATCH_INTERVAL (300s / 5 minutes).
Reads pending logs from local_db (up to 100 entries).
Sends HTTP POST. On HTTP 200 success, deletes uploaded log IDs from local_db.
"""

import os
import threading
import time

import requests
from local_store.local_db import LocalDB
from utils.config import API_KEY
from utils.logger import log_debug


class LogUploader:
    """
    Luồng 3 (Tuyến Xe Tải) Batch Log Uploader.
    Periodically reads pending logs from local SQLite DB, batches them up to 100 entries,
    and uploads them to the server.
    """

    LOG_BATCH_INTERVAL = 300.0  # 5 minutes (300 seconds)
    BATCH_LIMIT = 100

    def __init__(
        self,
        backend_url: str | None = None,
        device_id: str | None = None,
        batch_interval: float = LOG_BATCH_INTERVAL,
        local_db: LocalDB | None = None,
    ):
        from utils.config import BACKEND_URL, BACKUP_SERVER_URL
        self.base_url = base_url or BACKEND_URL
        self.backup_url = BACKUP_SERVER_URL
        self.device_id = device_id or os.getenv("DEVICE_ID") or os.getenv("DEVICE_NAME", "May_Em_Trai")
        self.batch_interval = batch_interval
        self.db = local_db or LocalDB()

        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._trigger_event = threading.Event()

    @property
    def upload_url(self) -> str:
        import utils.state as state
        if state.FALLBACK_MODE and self.backup_url:
            return f"{self.backup_url.rstrip('/')}/api/logs/batch"
        return f"{self.base_url.rstrip('/')}/api/logs/batch"

    def start(self) -> None:
        """Start the batch uploader worker thread."""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="LogUploader-Worker"
        )
        self._worker_thread.start()
        log_debug("[LOG_UPLOADER] Batch uploader thread started.")

    def stop(self) -> None:
        """Stop the batch uploader worker thread."""
        log_debug("[LOG_UPLOADER] Stopping batch uploader thread...")
        self._running = False
        self._trigger_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        log_debug("[LOG_UPLOADER] Batch uploader thread stopped.")

    def trigger_now(self) -> None:
        """Triggers an immediate log upload attempt without waiting for the timer."""
        log_debug("[LOG_UPLOADER] Triggering immediate log batch upload.")
        self._trigger_event.set()

    def _worker_loop(self) -> None:
        while self._running:
            try:
                # Flush continuously with 2-second sleep until queue is empty
                while self._running:
                    processed_count = self._upload_batch()
                    if not processed_count or processed_count < self.BATCH_LIMIT:
                        break  # Queue is empty or near empty, wait for next interval
                    time.sleep(2.0)  # Rate-limiting between large batches to prevent DDoS
            except Exception as e:
                log_debug(f"[LOG_UPLOADER] Unexpected error during batch upload: {e}")

            # Wait for next interval or trigger event
            triggered = self._trigger_event.wait(timeout=self.batch_interval)
            if triggered:
                self._trigger_event.clear()

    def _upload_batch(self) -> int:
        pending_records = self.db.get_pending_logs(limit=self.BATCH_LIMIT)
        if not pending_records:
            return 0

        log_debug(f"[LOG_UPLOADER] Found {len(pending_records)} pending log entries to upload.")

        log_ids = []
        logs_payload = []

        for item in pending_records:
            log_id = item.get("id")

            process_name = item.get("process_name") or item.get("process") or "unknown"
            window_title = item.get("window_title") or item.get("title") or ""
            timestamp = item.get("timestamp") or item.get("created_at") or ""

            logs_payload.append({
                "process_name": process_name,
                "window_title": window_title,
                "timestamp": timestamp,
            })
            if log_id is not None:
                log_ids.append(log_id)

        if not logs_payload:
            return 0

        payload = {
            "device_id": self.device_id,
            "logs": logs_payload
        }

        try:
            log_debug(f"[LOG_UPLOADER] Sending {len(logs_payload)} logs to {self.upload_url}...")
            response = requests.post(
                self.upload_url,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
                timeout=10,
            )

            if 200 <= response.status_code < 300:
                log_debug(f"[LOG_UPLOADER] Upload successful (HTTP {response.status_code}). Deleting uploaded log IDs: {log_ids}")
                self.db.delete_pending_logs(log_ids)
                return len(log_ids)
            else:
                log_debug(f"[LOG_UPLOADER] Upload failed with HTTP {response.status_code}: {response.text}")
                return 0
        except Exception as e:
            log_debug(f"[LOG_UPLOADER] HTTP request failed: {e}")
            return 0
