"""
web_rules.py v2 — Local-First Architecture.
Doc rules tu SQLite cached_rules, dem thoi gian su dung trong SQLite local.
"""
import psutil
from datetime import date
from utils.config import DEVICE_NAME, SEND_INTERVAL
from utils.telegram_notify import send_telegram

BROWSER_PROCESSES = ['chrome.exe', 'msedge.exe', 'brave.exe', 'firefox.exe', 'opera.exe']


def _get_local_db():
    """Lazy import de tranh circular dependency."""
    from storage.local_db import LocalDB
    return LocalDB()


def get_web_rules_local(supabase=None) -> list:
    """
    Lay danh sach quy tac website tu SQLite cached_rules.
    Fallback: Query Supabase neu chua co cache.
    """
    try:
        db = _get_local_db()
        rules = db.get_cached_rules("web_rules")
        
        if rules is not None:
            return rules if isinstance(rules, list) else []
        
        # Fallback: Query Supabase
        if supabase:
            try:
                res = supabase.table("web_rules")\
                    .select("*")\
                    .eq("device_name", DEVICE_NAME)\
                    .eq("is_active", True)\
                    .execute()
                rules = res.data or []
                db.save_cached_rules("web_rules", rules)
                return rules
            except Exception:
                pass
        
        return []
    except Exception:
        return []


def clean_domain(raw_domain: str) -> str:
    """Chuan hoa domain: bo protocol, www, path."""
    d = raw_domain.lower().strip()
    d = d.replace("https://", "").replace("http://", "").replace("www.", "")
    return d.split('/')[0]


def enforce_web_rules(supabase, active_window_info: dict, processes: list) -> list:
    """
    Giam sat trang web dang mo dua vao tieu de cua so trinh duyet va quy tac web_rules.
    - forbidden: Tat ngay trinh duyet dang mo trang web cam.
    - limited: Dem phut su dung web, neu vuot max_minutes_per_day thi tat trinh duyet.
    
    LOCAL-FIRST: Doc rules tu SQLite, dem thoi gian trong SQLite.
    """
    web_rules = get_web_rules_local(supabase)
    if not web_rules or not active_window_info:
        return []

    title = (active_window_info.get("title") or "").lower()
    proc_name = (active_window_info.get("process_name") or "").lower()
    pid = active_window_info.get("pid")

    if not title or proc_name not in BROWSER_PROCESSES:
        return []

    alerts = []
    db = _get_local_db()
    today_str = date.today().isoformat()
    minutes_per_cycle = max(1, round(SEND_INTERVAL / 60))

    for rule in web_rules:
        target_domain = clean_domain(rule.get("domain", ""))
        if not target_domain:
            continue

        category = rule.get("category", "forbidden")
        max_minutes = rule.get("max_minutes_per_day", 0)

        # Kiem tra domain co xuat hien trong tieu de cua so trinh duyet
        if target_domain in title:
            # 1. TRANG WEB CAM
            if category == "forbidden":
                try:
                    if pid:
                        p = psutil.Process(pid)
                        p.terminate()
                    alerts.append(f"Da dong trinh duyet do truy cap web cam: {target_domain}")
                    
                    try:
                        send_telegram(
                            f"[BLOCKED] CANH BAO TRUY CAP WEB CAM\n"
                            f"Thiet bi: {DEVICE_NAME}\n"
                            f"Domain: {target_domain}"
                        )
                    except Exception:
                        pass
                    
                    # Ghi vao pending_logs
                    db.add_pending_log("system_event", {
                        "device_name": DEVICE_NAME,
                        "event_type": "web_blocked",
                        "message": f"Closed browser for domain: {target_domain}"
                    })
                except Exception as e:
                    alerts.append(f"Loi dong web cam {target_domain}: {e}")

            # 2. TRANG WEB GIOI HAN GIO TRUY CAP
            elif category == "limited" and max_minutes > 0:
                total_used = db.increment_web_usage(today_str, target_domain, minutes_per_cycle)
                print(f"[WEB] Gioi han [{target_domain}]: Da dung {total_used}/{max_minutes} phut hom nay.")

                if total_used >= max_minutes:
                    try:
                        if pid:
                            p = psutil.Process(pid)
                            p.terminate()
                        alerts.append(
                            f"Da dong trinh duyet do web {target_domain} vuot qua gioi han "
                            f"({max_minutes} phut/ngay)"
                        )
                        try:
                            send_telegram(
                                f"[TIMEOUT] HET GIO DUYET WEB\n"
                                f"Thiet bi: {DEVICE_NAME}\n"
                                f"Domain: {target_domain}\n"
                                f"Da dung: {total_used}/{max_minutes} phut hom nay."
                            )
                        except Exception:
                            pass
                    except Exception:
                        pass

    return alerts
