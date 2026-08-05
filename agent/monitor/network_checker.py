"""
network_checker.py v3 — Đo Latency RTT chính xác (Median perf_counter, Supabase Host, Quality Rating).
"""
import socket
import time
import statistics
from urllib.parse import urlparse
from utils.config import SUPABASE_URL
from utils.logger import log_debug

FALLBACK_TEST_HOSTS = [("8.8.8.8", 53), ("1.1.1.1", 53)]

def _extract_supabase_host() -> str:
    """Rút gọn domain từ SUPABASE_URL (ví dụ: whymvwuzjaffltkjkfoj.supabase.co)."""
    try:
        if not SUPABASE_URL:
            return ""
        parsed = urlparse(SUPABASE_URL)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return ""

def measure_latency_ms(host: str, port: int = 443, samples: int = 3, timeout: float = 2.0) -> int:
    """
    Đo latency RTT chính xác bằng TCP Connect:
    - Resolve DNS 1 lần trước khi đo để khử nhiễu DNS lookup
    - Đo n mẫu (mặc định 3 samples) dùng time.perf_counter()
    - Trả về giá trị Median (trung vị ms), hoặc -1 nếu thất bại hoàn toàn.
    """
    if not host:
        return -1

    try:
        # Resolve DNS 1 lần trước
        ip = socket.gethostbyname(host)
    except Exception as de:
        log_debug(f"[NET] DNS resolve failed for {host}: {de}")
        return -1

    sample_latencies = []
    for _ in range(samples):
        sock = None
        try:
            t_start = time.perf_counter()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            t_elapsed = (time.perf_counter() - t_start) * 1000
            sample_latencies.append(round(t_elapsed))
        except Exception:
            pass
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    if not sample_latencies:
        return -1

    # Trả về trung vị (median) để lọc nhiễu các điểm đột biến (outliers)
    return int(statistics.median(sample_latencies))

def check_network(timeout: float = 3.0) -> dict:
    """
    Kiểm tra chất lượng kết nối mạng:
    Returns:
        dict: {
            "online": bool,
            "latency_ms": int,
            "supabase_ok": bool,
            "quality": "good" | "slow" | "down"
        }
    Ngưỡng:
        good: online=True, latency_ms <= 800ms, supabase_ok=True
        slow: online=True, 800ms < latency_ms <= 3000ms
        down: online=False, latency_ms > 3000ms hoặc fail (-1)
    """
    sp_host = _extract_supabase_host()
    sp_latency = -1
    supabase_ok = False

    if sp_host:
        sp_latency = measure_latency_ms(sp_host, port=443, samples=3, timeout=timeout)
        if sp_latency != -1:
            supabase_ok = True

    online = supabase_ok
    latency_ms = sp_latency

    # Nếu không kết nối được Supabase, thử fallback sang DNS public để xác định có Internet hay không
    if not online:
        for host, port in FALLBACK_TEST_HOSTS:
            fb_lat = measure_latency_ms(host, port=port, samples=2, timeout=2.0)
            if fb_lat != -1:
                online = True
                latency_ms = fb_lat
                break

    # Phân loại chất lượng mạng (quality)
    if not online or latency_ms == -1 or latency_ms > 3000:
        quality = "down"
    elif latency_ms <= 800 and supabase_ok:
        quality = "good"
    else:
        quality = "slow"

    return {
        "online": online,
        "latency_ms": latency_ms,
        "supabase_ok": supabase_ok,
        "quality": quality
    }

def is_internet_available(host="8.8.8.8", port=53, timeout=3) -> bool:
    """Hàm wrapper tương thích ngược giữ nguyên cấu trúc cũ."""
    net = check_network(timeout=timeout)
    return net["online"]
