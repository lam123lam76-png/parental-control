"""Configuration constants and environment loader for Parental Control Agent."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from multiple locations in order of priority:
# 1. C:\ProgramData\ParentalControl\.env
# 2. Agent source directory .env
# 3. Current working directory .env
# progdata_env = Path(r"C:\ProgramData\ParentalControl\.env")
# if progdata_env.exists():
#     load_dotenv(dotenv_path=progdata_env, override=True)

ENV_PATH = Path(__file__).resolve().parent / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

cwd_env = Path.cwd() / ".env"
if cwd_env.exists() and cwd_env != ENV_PATH:
    load_dotenv(dotenv_path=cwd_env)

def normalize_server_url(raw_url: str) -> tuple[str, str]:
    """
    Normalizes raw server URL into valid HTTP/HTTPS BACKEND_URL and WS/WSS WS_URL.
    Strips trailing slashes and automatically handles http/https and ws/wss schemes.
    """
    url = raw_url.strip().rstrip("/")
    if not url.startswith(("http://", "https://", "ws://", "wss://")):
        # If localhost or IP address, default to http://, else default to https://
        if "127.0.0.1" in url or "localhost" in url:
            url = f"http://{url}"
        else:
            url = f"https://{url}"

    if url.startswith("https://"):
        backend_url = url
        ws_url = "wss://" + url[8:]
    elif url.startswith("http://"):
        backend_url = url
        ws_url = "ws://" + url[7:]
    elif url.startswith("wss://"):
        backend_url = "https://" + url[6:]
        ws_url = url
    elif url.startswith("ws://"):
        backend_url = "http://" + url[5:]
        ws_url = url
    else:
        backend_url = f"http://{url}"
        ws_url = f"ws://{url}"

    return backend_url, ws_url

# Server URL Configuration (Supports SERVER_URL, API_BASE_URL, or BACKEND_URL env overrides)
RAW_SERVER_URL: str = os.getenv("SERVER_URL") or os.getenv("API_BASE_URL") or os.getenv("BACKEND_URL") or "https://nguyentruclam.io.vn"
BACKEND_URL, WS_URL = normalize_server_url(RAW_SERVER_URL)

import socket

DEVICE_NAME: str = os.getenv("DEVICE_NAME") or socket.gethostname()
DEVICE_ID: str | None = os.getenv("DEVICE_ID")

# Intervals (in seconds)
HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "15"))
LOG_BATCH_INTERVAL: int = int(os.getenv("LOG_BATCH_INTERVAL", "300"))
ALERT_RETRY_INTERVAL: int = int(os.getenv("ALERT_RETRY_INTERVAL", "3"))
PROCESS_SCAN_INTERVAL: int = int(os.getenv("PROCESS_SCAN_INTERVAL", "15"))

# Storage paths
_appdata = os.getenv("APPDATA") or os.path.expanduser("~")
CRED_DIR: Path = Path(_appdata) / "ParentalControl"
CRED_PATH: Path = CRED_DIR / "device.cred"
DB_PATH: Path = CRED_DIR / "agent_local.db"

# Ensure directory exists on module load
CRED_DIR.mkdir(parents=True, exist_ok=True)
