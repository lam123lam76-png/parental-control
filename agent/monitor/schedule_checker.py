from datetime import datetime
from utils.config import DEVICE_NAME

def check_current_schedule(supabase) -> tuple[bool, str]:
    """
    Kiểm tra hiện tại có đang trong giờ học theo Lịch (Schedule) không.
    Trả về (is_study_time, title)
    """
    try:
        now_time_str = datetime.now().strftime("%H:%M:%S")
        res = supabase.table("schedules")\
            .select("*")\
            .eq("device_name", DEVICE_NAME)\
            .lte("start_time", now_time_str)\
            .gte("end_time", now_time_str)\
            .execute()
        
        events = res.data or []
        for ev in events:
            if ev.get("event_type") == "study":
                return True, ev.get("title", "Giờ học tập")
        return False, ""
    except Exception as e:
        print(f"Lỗi kiểm tra lịch học: {e}")
        return False, ""
