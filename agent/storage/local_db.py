import os
import sqlite3
import json
import threading
from contextlib import contextmanager
from typing import Optional, Union, List, Dict, Any
from datetime import datetime

DB_PRIMARY_PATH = r'C:\ProgramData\ParentalControl\parental_control.db'
DB_FALLBACK_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FALLBACK_PATH = os.path.join(DB_FALLBACK_DIR, 'parental_control.db')

class LocalDB:
    """Singleton quản lý kết nối SQLite local database."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LocalDB, cls).__new__(cls)
                cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        """Khởi tạo cấu hình và tạo file db."""
        self._db_path = DB_PRIMARY_PATH
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            conn = sqlite3.connect(self._db_path)
            conn.close()
            print(f"[OK] Su dung DB chinh: {self._db_path}")
        except Exception as e:
            print(f"[ERR] Khong the dung DB chinh: {e}")
            self._db_path = DB_FALLBACK_PATH
            try:
                os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
                print(f"[OK] Su dung DB du phong: {self._db_path}")
            except Exception as fe:
                print(f"[ERR] Khong the dung DB du phong: {fe}")
        
        self._create_tables()

    @contextmanager
    def _get_connection(self):
        """Lấy kết nối SQLite với WAL mode, tự động commit/rollback và ĐÓNG kết nối khi dùng xong."""
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA journal_mode=WAL')
        except Exception as e:
            print(f"[ERR] Khong the bat WAL mode: {e}")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _create_tables(self) -> None:
        """Tạo các bảng nếu chưa có."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usage_minutes (
                        date TEXT PRIMARY KEY, 
                        total_minutes INTEGER DEFAULT 0
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS app_usage (
                        date TEXT, 
                        process_name TEXT, 
                        used_minutes INTEGER DEFAULT 0, 
                        PRIMARY KEY(date, process_name)
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS web_usage (
                        date TEXT, 
                        domain TEXT, 
                        used_minutes INTEGER DEFAULT 0, 
                        PRIMARY KEY(date, domain)
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cached_rules (
                        rule_type TEXT PRIMARY KEY, 
                        data TEXT, 
                        updated_at TEXT
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pending_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        log_type TEXT, 
                        data TEXT, 
                        created_at TEXT
                    )
                ''')
                conn.commit()
            print("[OK] Da tao cac bang DB cuc bo")
        except Exception as e:
            print(f"[ERR] Loi khi tao bang: {e}")

    def increment_usage_minutes(self, date_str: str, minutes: int = 1) -> int:
        """Tăng số phút sử dụng tổng cho một ngày."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO usage_minutes (date, total_minutes) 
                    VALUES (?, ?) 
                    ON CONFLICT(date) 
                    DO UPDATE SET total_minutes = total_minutes + ?
                ''', (date_str, minutes, minutes))
                conn.commit()
            return self.get_usage_minutes(date_str)
        except Exception as e:
            print(f"[ERR] Loi increment_usage_minutes: {e}")
            return 0

    def get_usage_minutes(self, date_str: str) -> int:
        """Lấy tổng số phút sử dụng của một ngày."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT total_minutes FROM usage_minutes WHERE date = ?', (date_str,))
                row = cursor.fetchone()
                return row['total_minutes'] if row else 0
        except Exception as e:
            print(f"[ERR] Loi get_usage_minutes: {e}")
            return 0

    def increment_app_usage(self, date_str: str, process_name: str, minutes: int = 1) -> int:
        """Tăng thời gian sử dụng ứng dụng."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO app_usage (date, process_name, used_minutes) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(date, process_name) 
                    DO UPDATE SET used_minutes = used_minutes + ?
                ''', (date_str, process_name, minutes, minutes))
                conn.commit()
            return self.get_app_usage(date_str, process_name)
        except Exception as e:
            print(f"[ERR] Loi increment_app_usage: {e}")
            return 0

    def get_app_usage(self, date_str: str, process_name: str) -> int:
        """Lấy thời gian sử dụng ứng dụng."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT used_minutes FROM app_usage WHERE date = ? AND process_name = ?', 
                               (date_str, process_name))
                row = cursor.fetchone()
                return row['used_minutes'] if row else 0
        except Exception as e:
            print(f"[ERR] Loi get_app_usage: {e}")
            return 0

    def increment_web_usage(self, date_str: str, domain: str, minutes: int = 1) -> int:
        """Tăng thời gian sử dụng web."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO web_usage (date, domain, used_minutes) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(date, domain) 
                    DO UPDATE SET used_minutes = used_minutes + ?
                ''', (date_str, domain, minutes, minutes))
                conn.commit()
            return self.get_web_usage(date_str, domain)
        except Exception as e:
            print(f"[ERR] Loi increment_web_usage: {e}")
            return 0

    def get_web_usage(self, date_str: str, domain: str) -> int:
        """Lấy thời gian sử dụng web."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT used_minutes FROM web_usage WHERE date = ? AND domain = ?', 
                               (date_str, domain))
                row = cursor.fetchone()
                return row['used_minutes'] if row else 0
        except Exception as e:
            print(f"[ERR] Loi get_web_usage: {e}")
            return 0

    def save_cached_rules(self, rule_type: str, data: Union[Dict, List]) -> None:
        """Lưu rules vào cache dưới dạng JSON."""
        try:
            json_data = json.dumps(data)
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO cached_rules (rule_type, data, updated_at) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(rule_type) 
                    DO UPDATE SET data = ?, updated_at = ?
                ''', (rule_type, json_data, now, json_data, now))
                conn.commit()
        except Exception as e:
            print(f"[ERR] Loi save_cached_rules: {e}")

    def get_cached_rules(self, rule_type: str) -> Optional[Union[Dict, List]]:
        """Lấy rules từ cache."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT data FROM cached_rules WHERE rule_type = ?', (rule_type,))
                row = cursor.fetchone()
                if row and row['data']:
                    return json.loads(row['data'])
                return None
        except Exception as e:
            print(f"[ERR] Loi get_cached_rules: {e}")
            return None

    def add_pending_log(self, log_type: str, data: Dict) -> None:
        """Thêm một log vào hàng đợi (tối đa 5000 logs để tránh tràn đĩa)."""
        try:
            json_data = json.dumps(data)
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM pending_logs WHERE id IN (
                        SELECT id FROM pending_logs ORDER BY id ASC LIMIT max(0, (SELECT count(*) FROM pending_logs) - 4999)
                    )
                ''')
                cursor.execute('''
                    INSERT INTO pending_logs (log_type, data, created_at) 
                    VALUES (?, ?, ?)
                ''', (log_type, json_data, now))
                conn.commit()
        except Exception as e:
            print(f"[ERR] Loi add_pending_log: {e}")

    def get_pending_logs(self, limit: int = 500) -> List[Dict]:
        """Lấy danh sách các log cũ nhất."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, log_type, data, created_at 
                    FROM pending_logs 
                    ORDER BY id ASC LIMIT ?
                ''', (limit,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "id": row["id"],
                        "log_type": row["log_type"],
                        "data": json.loads(row["data"]),
                        "created_at": row["created_at"]
                    })
                return results
        except Exception as e:
            print(f"[ERR] Loi get_pending_logs: {e}")
            return []

    def delete_pending_logs(self, ids: List[int]) -> None:
        """Xóa các log đã được đồng bộ."""
        if not ids:
            return
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' for _ in ids)
                cursor.execute(f'DELETE FROM pending_logs WHERE id IN ({placeholders})', ids)
                conn.commit()
        except Exception as e:
            print(f"[ERR] Loi delete_pending_logs: {e}")

    def get_all_app_usage_for_date(self, date_str: str) -> List[Dict]:
        """Lấy toàn bộ dòng app_usage cho một ngày."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT process_name, used_minutes FROM app_usage WHERE date = ?', (date_str,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "process_name": row["process_name"],
                        "used_minutes": row["used_minutes"]
                    })
                return results
        except Exception as e:
            print(f"[ERR] Loi get_all_app_usage_for_date: {e}")
            return []

    def get_all_web_usage_for_date(self, date_str: str) -> List[Dict]:
        """Lấy toàn bộ dòng web_usage cho một ngày."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT domain, used_minutes FROM web_usage WHERE date = ?', (date_str,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "domain": row["domain"],
                        "used_minutes": row["used_minutes"]
                    })
                return results
        except Exception as e:
            print(f"[ERR] Loi get_all_web_usage_for_date: {e}")
            return []
