import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://whymvwuzjaffltkjkfoj.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndoeW12d3V6amFmZmx0a2prZm9qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUzOTU4ODgsImV4cCI6MjEwMDk3MTg4OH0.Cfqfgi-1uGQlj3S2_2yI8uaNYNGTDOYawD8do7qnohI"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8754890738:AAEGB2dZCXJzlQ-Bzk1zwN3n2HLxAyj8imA"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "1326412172"
AGENT_PASSWORD = os.getenv("AGENT_PASSWORD") or "Truc@1905s0825811915"
DEVICE_NAME = os.getenv("DEVICE_NAME") or "May_Em_Trai"

# Thời gian gửi dữ liệu (giây) - có thể chỉnh trong .env
try:
    SEND_INTERVAL = int(os.getenv("SEND_INTERVAL", "60"))
except:
    SEND_INTERVAL = 60

from datetime import datetime, timezone, timedelta
VN_TZ = timezone(timedelta(hours=7))

def get_vn_now() -> datetime:
    """Lay datetime hien tai theo mui gio Viet Nam (UTC+7 / ICT)."""
    return datetime.now(timezone.utc).astimezone(VN_TZ)