"""
network_checker.py v2 — Kiểm tra mạng Mức 2 (Latency RTT + Supabase Host Connection).
"""
import socket
import time
from urllib.parse import urlparse
from utils.config import SUPABASE_URL
from utils.logger import log_debug

TEST_HOSTS = [("8.8.8.8", 53), ("1.1.1.1", 53)]

def _extract_supabase_host() -> str:
    """Rút gọn domain từ SUPABASE_URL (ví dụ: whymvwuzjaffltkjkfoj.supabase.co)."""
    try:
        if not SUPABASE_URL:
            return ""
        parsed = urlparse(SUPABASE_URL)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return ""

def check_network(timeout: float = 3.0) -> dict:
    """
    Kiểm tra mạng Mức 2:
    Returns:
        dict: {
            "online": bool,          # Có kết nối Internet không
            "latency_ms": int,       # RTT ms (-1 nếu fail)
            "supabase_ok": bool      # Kết nối thành công đến host Supabase (port 443) không
        }
    """
    online = False
    latency_ms = -1

    # 1. Đo RTT Latency qua socket TCP connect
    for host, port in TEST_HOSTS:
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            elapsed_ms = int((time.time() - start_time) * 1000)
            online = True
            latency_ms = elapsed_ms
            break
        except Exception:
            continue

    # 2. Kiểm tra kết nối TCP port 443 đến host Supabase
    supabase_ok = False
    sp_host = _extract_supabase_host()
    if sp_host:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((sp_host, 443))
            sock.close()
            supabase_ok = True
        except Exception as e:
            log_debug(f"[NET] Supabase host ({sp_host}) connect failed: {e}")

    return {
        "online": online,
        "latency_ms": latency_ms,
        "supabase_ok": supabase_ok
    }

def is_internet_available(host="8.8.8.8", port=53, timeout=3) -> bool:
    """Hàm wrapper tương thích ngược giữ nguyên cấu trúc cũ."""
    net = check_network(timeout=timeout)
    return net["online"]
