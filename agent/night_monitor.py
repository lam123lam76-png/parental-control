"""
night_monitor.py — Night-time monitoring (anti-late-gaming) alerts.

Runs as a background thread on the agent. Tracks Vietnamese time and sends
Telegram alerts when a child is gaming too late:
  - device booted after 23:00  -> one-time "bật sau 11 giờ tối" alert
  - still on at 00:00          -> "chơi quá muộn" alert with Allow/Deny buttons
  - still on at 01:00..04:00   -> continuous "hoạt động liên tục" alerts

These are delivered to the backend as alerts (alert_type "night_*"), which the
backend formats into Telegram messages (and inline buttons for the 00:00 case).
This runs on the agent because Vercel serverless does not hold a persistent
background thread.
"""
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger("NightMonitor")

# Alert types sent to backend -> Telegram
ALERT_BOOT_AFTER_23 = "night_boot_after_23"
ALERT_MIDNIGHT = "night_midnight"      # 00:00 -> with Allow/Deny buttons
ALERT_CONTINUOUS = "night_continuous"  # 01..04 -> text only


class NightMonitor:
    def __init__(self, alert_sender, device_id: str, device_name: str, check_interval: float = 20.0):
        self.alert_sender = alert_sender
        self.device_id = device_id
        self.device_name = device_name
        self.check_interval = check_interval
        self._running = False
        self._thread = None
        self._sent_boot_after_23 = False
        self._sent_hours = set()   # hours (0..4) for which continuous alert was sent
        self._midnight_sent = False
        self._current_day = None
        self._active_start_hour = None  # hour (VN) the continuous late-night session began

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="NightMonitor")
        self._thread.start()
        logger.info("NightMonitor started.")

    def stop(self):
        self._running = False
        logger.info("NightMonitor stopped.")

    def _vn_now(self) -> datetime:
        from utils.config import get_vn_now
        return get_vn_now()

    def _loop(self):
        while self._running:
            try:
                self._check()
            except Exception as e:
                logger.debug(f"NightMonitor check error: {e}")
            for _ in range(int(self.check_interval)):
                if not self._running:
                    return
                time.sleep(1)

    def _check(self):
        now = self._vn_now()
        day = now.strftime("%Y-%m-%d")

        # New day -> reset per-day state
        if self._current_day != day:
            self._current_day = day
            self._sent_boot_after_23 = False
            self._sent_hours = set()
            self._midnight_sent = False
            self._active_start_hour = None
            logger.info(f"NightMonitor: new day {day}, state reset.")

        hour = now.hour
        is_late_night = (hour >= 23 or hour < 6)

        # Track when the continuous late-night session began. If we're in the
        # late-night window but haven't recorded a start yet, use the current hour
        # (>=23) else 23 (device likely already running before midnight).
        if is_late_night and self._active_start_hour is None:
            self._active_start_hour = hour if hour >= 23 else 23

        start = self._active_start_hour if self._active_start_hour is not None else 23

        # 1. Booted after 23:00 (23, 0..5 are "late night" hours). We detect this
        #    once per day when the current time is in the late-night window and the
        #    agent just started (first check of the day).
        if is_late_night and not self._sent_boot_after_23:
            self._sent_boot_after_23 = True
            self._send(ALERT_BOOT_AFTER_23, f"Hệ thống giám sát phát hiện máy bật sau 11 giờ tối.")

        # 2. At 00:00 -> midnight warning with buttons (only once)
        if hour == 0 and not self._midnight_sent:
            self._midnight_sent = True
            self._send(
                ALERT_MIDNIGHT,
                f"Hệ thống giám sát phát hiện máy {self.device_name} đang hoạt động liên tục từ {start} giờ đến 0 giờ.",
            )

        # 3. Continuous warnings at 01..04 (once per hour)
        if 1 <= hour <= 4 and hour not in self._sent_hours:
            self._sent_hours.add(hour)
            self._send(
                ALERT_CONTINUOUS,
                f"Hệ thống giám sát phát hiện máy {self.device_name} đang hoạt động liên tục từ {start} giờ đến {hour} giờ sáng.",
            )

    def _send(self, alert_type: str, message: str):
        logger.info(f"[NightMonitor] Sending {alert_type}: {message}")
        if not self.alert_sender:
            return
        try:
            self.alert_sender.send_alert(self.device_id, alert_type, message)
        except Exception as e:
            logger.error(f"[NightMonitor] send_alert failed: {e}")
