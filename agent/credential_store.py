"""DPAPI implementation for secure credential storage with dev fallback."""

import base64
import json
import os
import socket
from pathlib import Path

from config import CRED_DIR, CRED_PATH

# Try importing pywin32 win32crypt for Windows DPAPI support
try:
    import win32crypt
    HAS_WIN32CRYPT = True
except ImportError:
    HAS_WIN32CRYPT = False


def save_credentials(device_id: str, secret_token: str) -> None:
    """Save device credentials using Windows DPAPI if available, with base64 fallback."""
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"device_id": device_id, "secret_token": secret_token}).encode('utf-8')
    
    saved_with_dpapi = False
    encrypted_data = None

    if HAS_WIN32CRYPT:
        try:
            encrypted_data = win32crypt.CryptProtectData(
                payload,
                "ParentalControlDeviceToken",
                None,
                None,
                None,
                0
            )
            saved_with_dpapi = True
        except Exception:
            saved_with_dpapi = False

    if saved_with_dpapi and encrypted_data:
        record = {
            "mode": "dpapi",
            "data": base64.b64encode(encrypted_data).decode('utf-8')
        }
    else:
        record = {
            "mode": "base64",
            "data": base64.b64encode(payload).decode('utf-8')
        }

    # Save to primary CRED_PATH (%APPDATA%\ParentalControl\device.cred)
    try:
        with open(CRED_PATH, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
    except Exception:
        pass

    # Also save to system-wide C:\ProgramData\ParentalControl\device.cred
    prog_data_dir = Path(r"C:\ProgramData\ParentalControl")
    if prog_data_dir.exists():
        try:
            with open(prog_data_dir / "device.cred", "w", encoding="utf-8") as f_pg:
                json.dump(record, f_pg, indent=2)
        except Exception:
            pass


def _try_parse_cred_file(path: Path) -> tuple[str | None, str | None]:
    """Helper to parse a credentials file."""
    if not path.exists():
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return None, None

        try:
            record = json.loads(content)
        except json.JSONDecodeError:
            record = None

        if isinstance(record, dict) and "mode" in record and "data" in record:
            mode = record["mode"]
            raw_bytes = base64.b64decode(record["data"])

            if mode == "dpapi":
                if not HAS_WIN32CRYPT:
                    return None, None
                try:
                    _, decrypted_bytes = win32crypt.CryptUnprotectData(
                        raw_bytes, None, None, None, 0
                    )
                    data = json.loads(decrypted_bytes.decode('utf-8'))
                    return data.get("device_id"), data.get("secret_token")
                except Exception:
                    return None, None
            elif mode == "base64":
                try:
                    data = json.loads(raw_bytes.decode('utf-8'))
                    return data.get("device_id"), data.get("secret_token")
                except Exception:
                    return None, None

        # Fallback for raw legacy binary files or direct base64 strings
        with open(path, "rb") as f_bin:
            raw_file_bytes = f_bin.read()

        if HAS_WIN32CRYPT:
            try:
                _, decrypted_bytes = win32crypt.CryptUnprotectData(
                    raw_file_bytes, None, None, None, 0
                )
                data = json.loads(decrypted_bytes.decode('utf-8'))
                return data.get("device_id"), data.get("secret_token")
            except Exception:
                pass

        try:
            decoded = base64.b64decode(content).decode('utf-8')
            data = json.loads(decoded)
            return data.get("device_id"), data.get("secret_token")
        except Exception:
            pass

        return None, None
    except Exception:
        return None, None


def load_credentials() -> tuple[str | None, str | None]:
    """Load device credentials from primary path, fallback path, or .env file."""
    # 1. Primary: APPDATA/ParentalControl/device.cred
    dev_id, token = _try_parse_cred_file(CRED_PATH)
    if dev_id and token:
        return dev_id, token

    # 2. Fallback: C:\ProgramData\ParentalControl\device.cred
    prog_data_cred = Path(r"C:\ProgramData\ParentalControl\device.cred")
    dev_id, token = _try_parse_cred_file(prog_data_cred)
    if dev_id and token:
        return dev_id, token

    # 3. Fallback to .env configuration ONLY in test mode
    if os.getenv("PC_AGENT_TEST_MODE") == "1":
        try:
            api_key = os.getenv("API_KEY") or os.getenv("SECRET_TOKEN")
            dev_name = os.getenv("DEVICE_NAME") or os.getenv("DEVICE_ID") or socket.gethostname()
            if api_key:
                return dev_name, api_key
        except Exception:
            pass

    return None, None


def has_credentials() -> bool:
    """Return True if credentials exist and can be loaded successfully."""
    device_id, secret_token = load_credentials()
    return bool(device_id and secret_token)


def clear_credentials() -> None:
    """Delete credentials files if they exist."""
    if CRED_PATH.exists():
        try:
            CRED_PATH.unlink()
        except OSError:
            pass
    prog_data_cred = Path(r"C:\ProgramData\ParentalControl\device.cred")
    if prog_data_cred.exists():
        try:
            prog_data_cred.unlink()
        except OSError:
            pass
