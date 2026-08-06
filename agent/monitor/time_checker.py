"""
time_checker.py v2 — Local-First Architecture.
Doc du lieu tu SQLite local thay vi query Supabase moi lan.
Agent van hoat dong binh thuong khi mat mang.
"""
import json
from datetime import datetime, time
from typing import Optional

from utils.config import DEVICE_NAME, get_vn_now


def _get_local_db():
    """Lazy import de tranh circular dependency."""
    from storage.local_db import LocalDB
    return LocalDB()


def get_time_limit_mode_local() -> str:
    """
    Lay phuong thuc gioi han gio tu cached_rules (SQLite).
    Tra ve 'time_frame' hoac 'max_daily'.
    """
    try:
        db = _get_local_db()
        config = db.get_cached_rules("app_config")
        if config and isinstance(config, dict):
            return config.get("time_limit_mode", "time_frame")
    except Exception:
        pass
    return "time_frame"


def get_daily_usage_minutes_local() -> int:
    """
    Tinh tong so phut da su dung hom nay tu SQLite local.
    KHONG query Supabase -> hoat dong offline.
    """
    try:
        db = _get_local_db()
        today_str = get_vn_now().strftime("%Y-%m-%d")
        return db.get_usage_minutes(today_str)
    except Exception:
        return 0


def is_within_allowed_time(supabase=None) -> tuple[bool, str]:
    """
    Kiem tra hien tai co duoc phep su dung may khong.
    
    LOCAL-FIRST: Doc rules tu SQLite cached_rules.
    Neu chua co cache (lan dau chay) -> thu query Supabase va cache lai.
    
    Ho tro 2 phuong thuc:
    - time_frame: theo khung gio start_time ~ end_time (mac dinh)
    - max_daily: theo tong thoi gian toi da/ngay (max_hours)
    
    Args:
        supabase: Optional Supabase client (dung de fallback query truc tiep neu chua co cache)
    
    Returns:
        tuple[bool, str]: (allowed, reason)
    """
    try:
        db = _get_local_db()

        # STEP 1: KIEM TRA MASTER SWITCH TU APP_CONFIG
        config = db.get_cached_rules("app_config")
        if isinstance(config, dict):
            master_active = config.get("master_time_limit", True)
            if not master_active:
                return True, "Cong tac tong Gioi han thoi gian dang TAT -> Cho phep su dung"

        mode = get_time_limit_mode_local()
        now = get_vn_now()
        current_day = now.weekday()  # 0 = Thu 2 ... 6 = Chu nhat
        current_time = now.time()

        # Doc rules tu SQLite cache
        rules_data = db.get_cached_rules("time_restrictions")
        
        # Fallback: Neu chua co cache, thu query Supabase
        if rules_data is None and supabase is not None:
            try:
                result = supabase.table("time_restrictions")\
                    .select("*")\
                    .eq("device_name", DEVICE_NAME)\
                    .eq("is_active", True)\
                    .execute()
                rules_data = result.data or []
                # Cache lai cho lan sau
                db.save_cached_rules("time_restrictions", rules_data)
            except Exception:
                pass
        
        if not rules_data:
            return True, "Chua cau hinh gioi han gio -> Cho phep"
        
        # Loc rules active cho ngay hien tai
        today_rules = [
            r for r in rules_data 
            if r.get("day_of_week") == current_day and r.get("is_active", True) is True
        ]
        
        if not today_rules:
            return True, "Quy tac ngay hom nay dang tat (Khong gioi han) -> Cho phep"

        if mode == "max_daily":
            # Phuong thuc: Tong thoi gian toi da/ngay
            rule = today_rules[0]
            max_hours = rule.get("max_hours", 0)
            if max_hours <= 0:
                return True, "max_hours = 0 -> Khong gioi han"
            
            used_minutes = get_daily_usage_minutes_local()
            max_minutes = int(max_hours * 60)
            remaining = max_minutes - used_minutes
            
            if used_minutes >= max_minutes:
                return False, f"Da dung het {max_hours} gio/ngay ({used_minutes} phut). Het quota!"
            else:
                return True, f"Da dung {used_minutes}/{max_minutes} phut. Con lai {remaining} phut."
        else:
            # Phuong thuc mac dinh: Theo khung gio
            for rule in today_rules:
                try:
                    start = time.fromisoformat(rule["start_time"])
                    end = time.fromisoformat(rule["end_time"])
                    if start <= current_time <= end:
                        return True, f"Trong gio cho phep ({rule['start_time']} - {rule['end_time']})"
                except (KeyError, ValueError):
                    continue

            return False, f"Ngoai gio cho phep. Hien tai: {current_time.strftime('%H:%M')}"

    except Exception as e:
        print(f"[ERR] Loi kiem tra thoi gian: {e}")
        # LOCAL-FIRST: Neu loi -> VAN KHOA MAY (an toan hon cho phep)
        # Khac voi ban cu tra ve True khi loi
        return True, "Loi kiem tra, tam cho phep"