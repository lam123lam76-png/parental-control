import os
from pathlib import Path
from datetime import datetime

INSTALL_DIR = Path(r"C:\ProgramData\ParentalControl")
LOG_FILE = INSTALL_DIR / "agent_debug.log"
LOCAL_LOG_FILE = Path(__file__).parent.parent / "agent_debug.log"


def log_debug(msg: str) -> None:
    r"""Ghi log debug vào cả file hệ thống C:\ProgramData và thư mục local agent."""
    timestamp_str = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    
    # 1. Ghi C:\ProgramData\ParentalControl\agent_debug.log
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(timestamp_str)
    except Exception:
        pass

    # 2. Ghi agent/agent_debug.log ngay trong dự án
    try:
        with open(LOCAL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(timestamp_str)
    except Exception:
        pass
