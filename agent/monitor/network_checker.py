"""
network_checker.py v4 — Đo Latency HTTP thực tế tới Supabase (DNS + TCP + TLS + HTTP Response).
"""
import urllib.request
import urllib.error
import socket
import time
import statistics
from urllib.parse import urlparse
from utils.config import SUPABASE_URL
from utils.logger import log_debug

FALLBACK_DNS = [("8.8.8.8", 53), ("1.1.1.1", 53)]

def measure_http_latency_ms(url: str = SUPABASE_URL, samples: int = 3, timeout: float = 2.5) -> int:
    """
    Đo HTTP Latency thực tế (DNS -> TCP -> TLS -> HTTP Response) tới Supabase:
    - Sử dụng urllib.request (chuẩn Python standard library) gửi HEAD / GET request nhẹ.
    - Đo n mẫu (mặc định 3 samples) dùng time.perf_counter().
    - Trả về giá trị Median (trung vị ms), hoặc -1 nếu thất bại hoàn toàn.
    """
    if not url:
        return -1

    target_url = url.rstrip('/') + '/'
    sample_latencies = []

    for _ in range(samples):
        try:
            req = urllib.request.Request(target_url, method='HEAD')
            req.add_header('User-Agent', 'ParentalControlAgent/2.0')
            
            t_start = time.perf_counter()
            with urllib.request.urlopen(req, timeout=timeout) as response:
                _ = response.read(1)
            t_elapsed = (time.perf_counter() - t_start) * 1000
            sample_latencies.append(round(t_elapsed))
        except urllib.error.HTTPError as he:
            # Nếu nhận HTTP Status Code (401/403/404), nghĩa là host Supabase & TLS VẮN ĐANG HOẠT ĐỘNG TỐT!
            t_elapsed = (time.perf_counter() - t_start) * 1000
            sample_latencies.append(round(t_elapsed))
        except Exception as e:
            # Timeout / SSL Error / Connection Refused
            pass

    if not sample_latencies:
        return -1

    return int(statistics.median(sample_latencies))

def _check_raw_internet(timeout: float = 2.0) -> bool:
    """Kiểm tra xem máy có kết nối Internet thô qua TCP socket DNS không."""
    for host, port in FALLBACK_DNS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            return True
        except Exception:
            continue
    return False

def check_network(timeout: float = 3.0) -> dict:
    """
    Kiểm tra chất lượng kết nối mạng HTTP Mức 2:
    Returns:
        dict: {
            "online": bool,
            "latency_ms": int,
            "supabase_ok": bool,
            "quality": "good" | "slow" | "down"
        }
    Ngưỡng HTTP:
        good: online=True, supabase_ok=True, 0 <= latency_ms <= 1000ms
        slow: online=True, supabase_ok=True, 1001ms <= latency_ms <= 3500ms
        down: online=False hoặc supabase_ok=False hoặc latency_ms > 3500ms (-1)
    """
    raw_online = _check_raw_internet(timeout=2.0)
    latency_ms = measure_http_latency_ms(url=SUPABASE_URL, samples=3, timeout=min(2.5, timeout))
    supabase_ok = (latency_ms >= 0)
    online = raw_online or supabase_ok

    if not online or not supabase_ok or latency_ms > 3500 or latency_ms < 0:
        quality = "down"
    elif latency_ms <= 1000:
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
