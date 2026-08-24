"""Thread-safe SQLite database wrapper for local agent storage."""

import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure parent agent directory is in Python path for importing config
_agent_dir = Path(__file__).resolve().parent.parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

from config import DB_PATH


class LocalDB:
    """Thread-safe SQLite database manager for offline caching and queueing."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            self.db_path = Path(DB_PATH)
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a new SQLite connection with Row factory."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite database tables if they do not exist."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cached_rules (
                        id TEXT PRIMARY KEY,
                        rule_type TEXT,
                        target TEXT,
                        is_banned INTEGER,
                        daily_limit_minutes INTEGER,
                        day_of_week INTEGER,
                        allowed_start TEXT,
                        allowed_end TEXT
                    )
                """)
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pending_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        process_name TEXT,
                        window_title TEXT,
                        timestamp TEXT
                    )
                """)
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pending_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_type TEXT,
                        message TEXT,
                        timestamp TEXT
                    )
                """)
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS device_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
            conn.commit()

    # --- Cached Rules Methods ---

    def save_cached_rules(self, rules: list[dict[str, Any]]) -> None:
        """Replace all cached rules with the provided list of rules."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cached_rules")
            for r in rules:
                cursor.execute("""
                        INSERT INTO cached_rules (
                            id, rule_type, target, is_banned,
                            daily_limit_minutes, day_of_week, allowed_start, allowed_end
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                    str(r.get("id", "")),
                    r.get("rule_type"),
                    r.get("target"),
                    1 if r.get("is_banned") else 0,
                    r.get("daily_limit_minutes"),
                    r.get("day_of_week"),
                    r.get("allowed_start"),
                    r.get("allowed_end")
                ))
            conn.commit()

    def get_cached_rules(self) -> list[dict[str, Any]]:
        """Retrieve all cached rules as a list of dictionaries."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                    SELECT id, rule_type, target, is_banned,
                           daily_limit_minutes, day_of_week, allowed_start, allowed_end
                    FROM cached_rules
                """)
            rows = cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                # Convert integer 0/1 back to bool if needed or keep standard
                item["is_banned"] = bool(item["is_banned"])
                result.append(item)
            return result

    # --- Pending Logs Methods ---

    def add_pending_log(self, process_name: str, window_title: str | None = None, timestamp: str | None = None) -> None:
        """Add a pending process log to local queue."""
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                        INSERT INTO pending_logs (process_name, window_title, timestamp)
                        VALUES (?, ?, ?)
                    """, (process_name, window_title, timestamp))
                # SQLite FIFO Limit: Keep only the latest 10,000 records
                cursor.execute("""
                        DELETE FROM pending_logs 
                        WHERE id NOT IN (
                            SELECT id FROM pending_logs ORDER BY id DESC LIMIT 10000
                        )
                    """)
                conn.commit()
        except Exception:
            pass

    def get_pending_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch pending process logs up to the specified limit."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                    SELECT id, process_name, window_title, timestamp
                    FROM pending_logs
                    ORDER BY id ASC
                    LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_pending_logs(self, ids: list[int]) -> None:
        """Delete pending logs by ID list."""
        if not ids:
            return
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in ids)
                cursor.execute(f"DELETE FROM pending_logs WHERE id IN ({placeholders})", ids)
                conn.commit()

    # --- Pending Alerts Methods ---

    def add_pending_alert(self, alert_type: str, message: str, timestamp: str | None = None) -> None:
        """Add a pending alert to local queue."""
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                    INSERT INTO pending_alerts (alert_type, message, timestamp)
                    VALUES (?, ?, ?)
                """, (alert_type, message, timestamp))
            # SQLite FIFO Limit: Keep only the latest 10,000 records
            cursor.execute("""
                    DELETE FROM pending_alerts 
                    WHERE id NOT IN (
                        SELECT id FROM pending_alerts ORDER BY id DESC LIMIT 10000
                    )
                """)
            conn.commit()

    def get_pending_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch pending alerts up to the specified limit."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                    SELECT id, alert_type, message, timestamp
                    FROM pending_alerts
                    ORDER BY id ASC
                    LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_pending_alerts(self, ids: list[int]) -> None:
        """Delete pending alerts by ID list."""
        if not ids:
            return
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in ids)
                cursor.execute(f"DELETE FROM pending_alerts WHERE id IN ({placeholders})", ids)
                conn.commit()

    # --- Device Meta Methods ---

    def save_meta(self, key: str, value: str) -> None:
        """Save or update metadata key-value pair."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                    INSERT OR REPLACE INTO device_meta (key, value)
                    VALUES (?, ?)
                """, (key, value))
            conn.commit()

    def get_meta(self, key: str) -> str | None:
        """Retrieve value for a given metadata key."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM device_meta WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None
