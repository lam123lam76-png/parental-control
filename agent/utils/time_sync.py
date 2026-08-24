import datetime
import threading
import time

import requests


class SecureTime:
    """
    Provides secure, tamper-resistant time by fetching from internet (NTP/WorldTimeAPI)
    and tracking monotonic offset. Defeats local clock manipulation.
    """
    
    _offset_seconds: float = 0.0
    _last_sync_monotonic: float = 0.0
    _is_synced: bool = False
    _lock = threading.Lock()
    _sync_thread: threading.Thread | None = None
    
    # Hanoi Timezone (UTC+7)
    TZ_OFFSET = datetime.timezone(datetime.timedelta(hours=7))

    @classmethod
    def start_sync_thread(cls):
        with cls._lock:
            if cls._sync_thread is None or not cls._sync_thread.is_alive():
                cls._sync_thread = threading.Thread(target=cls._sync_loop, daemon=True)
                cls._sync_thread.start()

    @classmethod
    def _sync_loop(cls):
        while True:
            cls.sync_now()
            time.sleep(3600)  # Re-sync every hour

    @classmethod
    def sync_now(cls) -> bool:
        """Attempt to fetch time from WorldTimeAPI. Fallback to local clock on failure."""
        try:
            # 1. Try WorldTimeAPI
            res = requests.get("http://worldtimeapi.org/api/timezone/Asia/Ho_Chi_Minh", timeout=5)
            if res.status_code == 200:
                data = res.json()
                unix_time = float(data["unixtime"])
                cls._set_time(unix_time)
                return True
        except Exception:
            pass
            
        try:
            # 2. Try simple fallback to a Google headers date
            res = requests.head("http://google.com", timeout=5)
            date_str = res.headers.get("Date")
            if date_str:
                # e.g., "Wed, 21 Oct 2015 07:28:00 GMT"
                dt = datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT")
                unix_time = dt.replace(tzinfo=datetime.timezone.utc).timestamp()
                cls._set_time(unix_time)
                return True
        except Exception:
            pass

        return False

    @classmethod
    def _set_time(cls, utc_unix_time: float):
        with cls._lock:
            cls._last_sync_monotonic = time.monotonic()
            cls._offset_seconds = utc_unix_time - cls._last_sync_monotonic
            cls._is_synced = True

    @classmethod
    def now(cls) -> datetime.datetime:
        """
        Returns a datetime representing the current time in Hanoi timezone (UTC+7).
        If synced, it uses the secure monotonic tracking.
        If never synced, it falls back to the system local time.
        """
        with cls._lock:
            if cls._is_synced:
                current_unix = time.monotonic() + cls._offset_seconds
                dt_utc = datetime.datetime.fromtimestamp(current_unix, tz=datetime.timezone.utc)
                return dt_utc.astimezone(cls.TZ_OFFSET)
            else:
                # Fallback if we have absolutely no internet since boot
                # Assume local system time is the best we have, but force it into UTC+7
                return datetime.datetime.now(cls.TZ_OFFSET)
