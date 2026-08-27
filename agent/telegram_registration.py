"""
telegram_registration.py — Telegram-based Device Registration

Handles the background polling mechanism for device approval via Telegram.
When a new device is installed, it requests registration and waits for Parent's approval
(Yes/No via Telegram).
If No (rejected) or expired, it self-uninstalls.
If Yes (approved), it saves credentials and proceeds.
"""

import logging
import os
import time
import socket
import subprocess
import sys
from pathlib import Path

import requests

from pairing_ui import get_hardware_uuid
import config
from credential_store import has_credentials, save_credentials

logger = logging.getLogger("TelegramRegistration")

try:
    from utils.config import API_KEY
except Exception:
    API_KEY = "732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7"

SHUTDOWN_SECRET = "PC_WATCHDOG_SAFE_EXIT_a8f3e1b9c2d7"
TARGET_DIR = Path(r"C:\ProgramData\ParentalControl")


def _run_silent(cmd: str) -> None:
    try:
        subprocess.run(cmd, shell=True, capture_output=True, creationflags=0x08000000)
    except Exception:
        pass


def _schedule_folder_cleanup() -> None:
    """Write a detached .bat that deletes the data folders after the agent exits."""
    tmp = Path(os.environ.get("TEMP", r"C:\Windows\Temp")) / "pc_uninstall_cleanup.bat"
    folders = [
        r"C:\ProgramData\ParentalControl",
        Path(os.environ.get("APPDATA", "C:\\")) / "ParentalControl",
        Path(os.environ.get("LOCALAPPDATA", "C:\\")) / "ParentalControl",
    ]
    lines = ["@echo off", "timeout /t 3 /nobreak >nul"]
    for f in folders:
        lines.append(f'if exist "{f}" rmdir /s /q "{f}" 2>nul')
        lines.append(
            f'if exist "{f}" powershell -NoProfile -Command '
            f'"Remove-Item -Path \'{f}\' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1'
        )
    try:
        tmp.write_text("\n".join(lines), encoding="utf-8")
        subprocess.Popen(["cmd.exe", "/c", str(tmp)], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        logger.error(f"Failed to schedule folder cleanup: {e}")


def self_uninstall_and_exit() -> None:
    """Uninstalls the agent completely (programmatic; no dependency on a shipped .bat).

    Handles elevated agent/watchdog (taskkill + Stop-Process), sets the shutdown flag so
    a watchdog can't restart the agent, removes autostart (tasks + Run keys), clears
    Defender exclusions, schedules detached deletion of the data folders, then exits.
    """
    logger.info("Uninstalling agent due to rejected/expired registration...")

    # 1. Block watchdog restart via shutdown flags.
    for d in [TARGET_DIR, Path(os.environ.get("APPDATA", "C:\\")) / "ParentalControl"]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / "shutdown.flag").write_text(SHUTDOWN_SECRET, encoding="utf-8")
        except Exception:
            pass

    # 2. Schedule detached deletion of the data folders FIRST — the taskkill below
    #    kills this very process, so anything after it never runs.
    _schedule_folder_cleanup()

    # 3. Remove autostart (scheduled tasks + Run keys).
    _run_silent('powershell -NoProfile -Command "Get-ScheduledTask -TaskName \'*ParentalControl*\' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false"')
    _run_silent('schtasks /delete /tn "ParentalControlWatchdogTask" /f')
    _run_silent('schtasks /delete /tn "ParentalControlAgentTask" /f')
    for hive in ("HKLM", "HKCU"):
        for val in ("ParentalControlAgent", "ParentalControlWatchdog"):
            _run_silent(f'reg delete "{hive}\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "{val}" /f')

    # 4. Remove Defender exclusions.
    _run_silent('powershell -NoProfile -Command "Remove-MpPreference -ExclusionPath \'C:\\ProgramData\\ParentalControl\' -ErrorAction SilentlyContinue"')

    # 5. Kill all agent/watchdog/updater processes (including this one).
    for name in ("ParentalControlWatchdog", "ParentalControlAgent", "Updater", "ParentalControlAgent_Debug"):
        _run_silent(f'taskkill /f /t /im {name}.exe')
        _run_silent(f'powershell -NoProfile -Command "Get-Process -Name \'{name}\' -ErrorAction SilentlyContinue | Stop-Process -Force"')

    sys.exit(0)

def run_telegram_registration(backend_url: str) -> bool:
    """
    Registers the device via Telegram and polls for approval status.
    Returns True if approved, False if rejected or failed.
    If rejected, triggers self uninstall.
    """
    if has_credentials():
        logger.info("Device is already paired with credentials. Skipping Telegram registration.")
        return True

    hw_uuid = get_hardware_uuid()
    device_name = config.DEVICE_NAME or socket.gethostname()

    # Normalize target server URL
    try:
        from config import normalize_server_url
        target_backend_url, _ = normalize_server_url(backend_url)
    except Exception:
        target_backend_url = backend_url

    endpoint_request = f"{target_backend_url.rstrip('/')}/api/register-request"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    logger.info(f"Sending registration request for {hw_uuid} ({device_name}) to {endpoint_request}")
    try:
        resp = requests.post(
            endpoint_request,
            json={"hardware_uuid": hw_uuid, "device_name": device_name},
            headers=headers,
            timeout=10
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Registration request failed: {resp.status_code} - {resp.text}")
            return False
        
        # Handle dict or wrapped response
        resp_json = resp.json()
        data = resp_json.get("data") if isinstance(resp_json.get("data"), dict) else resp_json
        
        registration_id = data.get("registration_id") if data else resp_json.get("registration_id")
        
        if not registration_id:
            logger.error("No registration_id returned from server.")
            return False

        logger.info(f"Registration pending (ID: {registration_id}). Waiting for approval...")
        
        # Poll for status
        endpoint_status = f"{target_backend_url.rstrip('/')}/api/register-request/{registration_id}/status"
        
        while True:
            try:
                status_resp = requests.get(endpoint_status, timeout=10)
                if status_resp.status_code == 200:
                    status_json = status_resp.json()
                    status_data = status_json.get("data") if isinstance(status_json.get("data"), dict) else status_json
                    
                    current_status = status_data.get("status") if status_data else status_json.get("status")
                    
                    if current_status == "approved":
                        device_id = status_data.get("device_id") if status_data else status_json.get("device_id")
                        secret_token = status_data.get("secret_token") if status_data else status_json.get("secret_token")
                        if device_id and secret_token:
                            save_credentials(str(device_id), str(secret_token))
                            logger.info("Registration approved. Credentials saved.")
                            
                            # Update config .env if needed
                            try:
                                from config import CRED_DIR
                                env_file = CRED_DIR / ".env"
                                env_file.write_text(f"SERVER_URL={target_backend_url}\nBACKEND_URL={target_backend_url}\n", encoding="utf-8")
                                pg_env = Path(r"C:\ProgramData\ParentalControl\.env")
                                if pg_env.parent.exists():
                                    pg_env.write_text(f"SERVER_URL={target_backend_url}\nBACKEND_URL={target_backend_url}\n", encoding="utf-8")
                            except Exception as _env_err:
                                logger.warning(f"Could not persist SERVER_URL to .env: {_env_err}")
                            
                            return True
                        else:
                            logger.error("Approved but missing device_id/secret_token.")
                            return False
                    elif current_status == "rejected":
                        logger.warning("Registration rejected. Self-uninstalling agent.")
                        self_uninstall_and_exit()
                        return False
                    elif current_status == "expired":
                        # Parent never responded within the window. Do NOT uninstall —
                        # resend the request and keep waiting. Only an explicit REJECT
                        # triggers self-uninstall (backend resend refreshes expires_at).
                        logger.warning("Registration expired — resending registration request.")
                        try:
                            requests.post(
                                f"{target_backend_url.rstrip('/')}/api/register-request/{registration_id}/resend",
                                headers=headers, timeout=10,
                            )
                        except Exception as _rs:
                            logger.debug(f"Resend failed: {_rs}")
            except Exception as e:
                logger.debug(f"Error polling status: {e}")
            
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        return False
