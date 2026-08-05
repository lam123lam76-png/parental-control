import psutil
from datetime import datetime

def get_running_processes(limit: int = 30):
    """Lấy danh sách process đang chạy (ưu tiên tốn CPU/RAM)"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            memory_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
            processes.append({
                "pid": info['pid'],
                "name": info['name'],
                "cpu_percent": info['cpu_percent'] or 0,
                "memory_mb": round(memory_mb, 1)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sắp xếp theo RAM giảm dần, lấy top
    processes = sorted(processes, key=lambda x: x['memory_mb'], reverse=True)
    return processes[:limit]