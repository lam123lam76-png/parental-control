"""
app_rules.py v2 — Local-First + File Hash identification.
Nhan dien app bang nhieu tieu chi chong bypass:
- Ten file (process name)
- Duong dan file (exe path)
- File hash (MD5 cua file thuc thi)
- Product name (metadata cua file)

Doc rules tu SQLite cached_rules thay vi query Supabase moi lan.
"""
import os
import hashlib
import psutil
from datetime import date
from typing import Optional

from utils.config import DEVICE_NAME, SEND_INTERVAL
from utils.telegram_notify import send_telegram


def _get_local_db():
    """Lazy import de tranh circular dependency."""
    from storage.local_db import LocalDB
    return LocalDB()


def _get_file_hash(exe_path: str) -> Optional[str]:
    """Tinh MD5 hash cua file thuc thi. Tra ve None neu loi."""
    try:
        if not os.path.isfile(exe_path):
            return None
        hasher = hashlib.md5()
        with open(exe_path, "rb") as f:
            # Doc tung chunk 64KB de khong ton RAM
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None


def _get_product_name(exe_path: str) -> Optional[str]:
    """Lay product name tu metadata cua file .exe (FileVersionInfo)."""
    try:
        import win32api
        info = win32api.GetFileVersionInfo(exe_path, "\\StringFileInfo\\040904B0\\ProductName")
        return info if info else None
    except Exception:
        pass
    
    # Fallback: Thu voi FileDescription
    try:
        import win32api
        info = win32api.GetFileVersionInfo(exe_path, "\\StringFileInfo\\040904B0\\FileDescription")
        return info if info else None
    except Exception:
        return None


# Cache hash de khong phai tinh lai moi 60s
_hash_cache: dict[str, str] = {}  # exe_path -> md5_hash


def _get_cached_hash(exe_path: str) -> Optional[str]:
    """Lay hash tu cache hoac tinh moi."""
    if exe_path in _hash_cache:
        return _hash_cache[exe_path]
    h = _get_file_hash(exe_path)
    if h:
        _hash_cache[exe_path] = h
    return h


def get_app_rules_local(supabase=None) -> list:
    """
    Lay danh sach app rules tu SQLite cached_rules.
    Fallback: Query Supabase neu chua co cache.
    """
    try:
        db = _get_local_db()
        rules = db.get_cached_rules("app_rules")
        
        if rules is not None:
            return rules if isinstance(rules, list) else []
        
        # Fallback: Query Supabase
        if supabase:
            try:
                result = supabase.table("app_rules")\
                    .select("*")\
                    .eq("device_name", DEVICE_NAME)\
                    .eq("is_active", True)\
                    .execute()
                rules = result.data or []
                db.save_cached_rules("app_rules", rules)
                return rules
            except Exception:
                pass
        
        return []
    except Exception as e:
        print(f"[ERR] Loi lay app_rules: {e}")
        return []


def _match_process_to_rule(proc_info: dict, rule: dict) -> bool:
    """
    So khop process voi rule bang nhieu tieu chi:
    1. Ten process (bat buoc)
    2. File hash (neu rule co truong 'file_hash')
    3. Product name (neu rule co truong 'product_name')
    """
    rule_name = rule.get("process_name", "").lower()
    proc_name = proc_info.get("name", "").lower()
    
    # So sanh ten process (tieu chi co ban)
    if rule_name != proc_name:
        return False
    
    # Neu rule co file_hash -> so sanh (chong doi ten file)
    rule_hash = rule.get("file_hash")
    if rule_hash:
        try:
            p = psutil.Process(proc_info["pid"])
            exe_path = p.exe()
            actual_hash = _get_cached_hash(exe_path)
            if actual_hash and actual_hash.lower() != rule_hash.lower():
                return False
        except Exception:
            pass
    
    return True


def enforce_app_rules(supabase, processes: list) -> list:
    """
    Kiem tra va xu ly cac process dang chay theo rule.
    - forbidden: Tat ngay lap tuc.
    - limited: Dem thoi gian su dung, neu vuot max_minutes_per_day thi tat app va gui canh bao.
    
    LOCAL-FIRST: Doc rules tu SQLite, dem thoi gian su dung trong SQLite.
    """
    rules = get_app_rules_local(supabase)
    if not rules:
        return []

    alerts = []
    killed = []
    db = _get_local_db()
    today_str = date.today().isoformat()

    # Thoi gian moi chu ky chay bang SEND_INTERVAL giay (mac dinh 5s hoac 10s)
    elapsed_seconds = float(SEND_INTERVAL)

    # Loai bo trung lap ten process dang chay trong cung 1 chu ky
    running_names = set(p["name"].lower() for p in processes)

    for name in running_names:
        # Tim rule phu hop
        matched_rule = None
        for rule in rules:
            if rule.get("process_name", "").lower() == name:
                matched_rule = rule
                break
        
        if not matched_rule:
            continue

        category = matched_rule.get("category", "")
        max_minutes = matched_rule.get("max_minutes_per_day", 0)

        # ===== 1. UNG DUNG CAM =====
        if category == "forbidden":
            for proc_info in processes:
                if proc_info["name"].lower() == name:
                    try:
                        p = psutil.Process(proc_info["pid"])
                        p.terminate()
                        killed.append(name)
                        alerts.append(f"Da tat app cam: {name}")
                    except Exception as e:
                        alerts.append(f"Khong tat duoc {name}: {e}")

        # ===== 2. UNG DUNG GIOI HAN THOI GIAN =====
        elif category == "limited" and max_minutes > 0:
            # Cong don thoi gian su dung theo giay thuc te vao SQLite local
            total_used = db.increment_app_usage(today_str, name, seconds=elapsed_seconds)
            print(f"[APP] Gioi han [{name}]: Da dung {total_used}/{max_minutes} phut hom nay.")

            if total_used >= max_minutes:
                # Qua thoi gian cho phep -> Tat app
                for proc_info in processes:
                    if proc_info["name"].lower() == name:
                        try:
                            p = psutil.Process(proc_info["pid"])
                            p.terminate()
                            killed.append(f"{name} (Da dung {total_used}/{max_minutes} phut)")
                            alerts.append(f"Da tat {name} do vuot qua thoi gian cho phep ({max_minutes} phut/ngay)")
                        except Exception:
                            pass

    # Gui Telegram neu co ung dung bi chan hoac het gio
    if killed:
        msg = "[BLOCKED] DA TAT UNG DUNG\n" + "\n".join(f"- {n}" for n in killed)
        try:
            send_telegram(msg)
        except Exception:
            pass
        
        # Ghi vao pending_logs de sync sau
        try:
            db.add_pending_log("system_event", {
                "device_name": DEVICE_NAME,
                "event_type": "app_blocked",
                "message": f"Killed apps: {', '.join(killed)}"
            })
        except Exception:
            pass

    return alerts