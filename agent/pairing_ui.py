"""
pairing_ui.py — Desktop Device Pairing UI for Parental Control Agent

Displays a Tkinter desktop pairing form when the device is not yet paired.
Prompts for Parent Email, Parent Password, and Device Name (defaulting to socket.gethostname()).
Sends hardware registration request to Backend API (/api/pair) and securely saves DPAPI credentials upon success.
Includes robust DNS NameResolutionError & ConnectionError exception handling.
"""

import logging
import os
import socket
import tkinter as tk
import uuid
from tkinter import messagebox

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from credential_store import has_credentials, save_credentials

logger = logging.getLogger("PairingUI")


def get_hardware_uuid() -> str:
    """Get system hardware UUID on Windows, with fallback to mac address based UUID."""
    if os.name == 'nt':
        try:
            import subprocess
            cmd = "wmic csproduct get uuid"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
            lines = [line.strip() for line in output.splitlines() if line.strip() and "UUID" not in line]
            if lines and lines[0]:
                return lines[0]
        except Exception:
            pass
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if guid:
                return str(guid)
        except Exception:
            pass
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, str(uuid.getnode())))


def run_pairing_ui(backend_url: str | None = None) -> bool:
    """
    Run Tkinter pairing UI form to register device with Backend server.
    
    :param backend_url: Base URL of Backend API (e.g. http://127.0.0.1:8000).
    :return: True if device paired successfully and credentials saved, False otherwise.
    """
    if has_credentials():
        logger.info("Device is already paired with credentials. Skipping Pairing UI.")
        return True

    if not backend_url:
        try:
            from config import BACKEND_URL
            backend_url = BACKEND_URL
        except ImportError:
            backend_url = "http://127.0.0.1:8000"

    paired_success = False

    # Create Tkinter Window
    root = tk.Tk()
    root.title("Đăng ký Thiết bị - Parental Control Agent")
    root.configure(bg="#181825")
    root.resizable(False, False)

    # Center window on screen
    width, height = 460, 610
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")

    # Top Header Frame
    header_frame = tk.Frame(root, bg="#1e1e2e", pady=18)
    header_frame.pack(fill="x")

    title_lbl = tk.Label(
        header_frame,
        text="🛡️ ĐĂNG KÝ THIẾT BỊ",
        font=("Segoe UI", 18, "bold"),
        fg="#cba6f7",
        bg="#1e1e2e"
    )
    title_lbl.pack()

    subtitle_lbl = tk.Label(
        header_frame,
        text="Nhập thông tin Phụ huynh để kết nối Agent với Máy chủ",
        font=("Segoe UI", 10),
        fg="#bac2de",
        bg="#1e1e2e"
    )
    subtitle_lbl.pack(pady=(4, 0))

    # Form Body Frame
    body_frame = tk.Frame(root, bg="#181825", padx=30, pady=18)
    body_frame.pack(fill="both", expand=True)

    # Field 0: Server URL
    server_lbl = tk.Label(
        body_frame,
        text="Địa chỉ Máy chủ (Server URL):",
        font=("Segoe UI", 10, "bold"),
        fg="#cdd6f4",
        bg="#181825"
    )
    server_lbl.pack(anchor="w", pady=(0, 4))

    server_entry = tk.Entry(
        body_frame,
        font=("Segoe UI", 11),
        bg="#313244",
        fg="#cdd6f4",
        insertbackground="#cdd6f4",
        bd=1,
        relief="solid"
    )
    server_entry.insert(0, backend_url or "https://nguyentruclam.io.vn")
    server_entry.pack(fill="x", pady=(0, 12), ipady=4)

    # Field 1: Email
    email_lbl = tk.Label(
        body_frame,
        text="Email Phụ huynh:",
        font=("Segoe UI", 10, "bold"),
        fg="#cdd6f4",
        bg="#181825"
    )
    email_lbl.pack(anchor="w", pady=(0, 4))

    email_entry = tk.Entry(
        body_frame,
        font=("Segoe UI", 11),
        bg="#313244",
        fg="#cdd6f4",
        insertbackground="#cdd6f4",
        bd=1,
        relief="solid"
    )
    email_entry.pack(fill="x", pady=(0, 12), ipady=4)
    email_entry.focus_set()

    # Field 2: Password
    pwd_lbl = tk.Label(
        body_frame,
        text="Mật khẩu Phụ huynh:",
        font=("Segoe UI", 10, "bold"),
        fg="#cdd6f4",
        bg="#181825"
    )
    pwd_lbl.pack(anchor="w", pady=(0, 4))

    pwd_entry = tk.Entry(
        body_frame,
        show="•",
        font=("Segoe UI", 11),
        bg="#313244",
        fg="#cdd6f4",
        insertbackground="#cdd6f4",
        bd=1,
        relief="solid"
    )
    pwd_entry.pack(fill="x", pady=(0, 12), ipady=4)

    # Field 3: Device Name
    device_lbl = tk.Label(
        body_frame,
        text="Tên thiết bị:",
        font=("Segoe UI", 10, "bold"),
        fg="#cdd6f4",
        bg="#181825"
    )
    device_lbl.pack(anchor="w", pady=(0, 4))

    default_hostname = socket.gethostname()
    device_entry = tk.Entry(
        body_frame,
        font=("Segoe UI", 11),
        bg="#313244",
        fg="#cdd6f4",
        insertbackground="#cdd6f4",
        bd=1,
        relief="solid"
    )
    device_entry.insert(0, default_hostname)
    device_entry.pack(fill="x", pady=(0, 12), ipady=4)

    # Status / Error Label
    status_lbl = tk.Label(
        body_frame,
        text="",
        font=("Segoe UI", 9),
        fg="#f38ba8",
        bg="#181825",
        wraplength=380,
        justify="center"
    )
    status_lbl.pack(pady=(0, 10))

    # Action Button Handler
    def on_pair_submit():
        nonlocal paired_success

        raw_server_url = server_entry.get().strip()
        parent_email = email_entry.get().strip()
        parent_password = pwd_entry.get().strip()
        device_name = device_entry.get().strip()

        if not raw_server_url or not parent_email or not parent_password or not device_name:
            status_lbl.config(text="Vui lòng điền đầy đủ các trường thông tin!", fg="#f38ba8")
            return

        # Normalize target server URL
        try:
            from config import normalize_server_url
            target_backend_url, _ = normalize_server_url(raw_server_url)
        except Exception:
            target_backend_url = raw_server_url

        status_lbl.config(text="Đang kết nối đến máy chủ...", fg="#89b4fa")
        root.update_idletasks()

        hw_uuid = get_hardware_uuid()
        pair_endpoint = f"{target_backend_url.rstrip('/')}/api/pair"

        payload = {
            "hardware_uuid": hw_uuid,
            "device_name": device_name,
            "parent_email": parent_email,
            "parent_password": parent_password
        }

        try:
            if HAS_REQUESTS:
                resp = requests.post(pair_endpoint, json=payload, timeout=10)
                status_code = resp.status_code
                try:
                    res_json = resp.json()
                except Exception:
                    res_json = {}
            else:
                import json
                import urllib.request
                req = urllib.request.Request(
                    pair_endpoint,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    status_code = response.status
                    res_json = json.loads(response.read().decode('utf-8'))

            if status_code in (200, 201):
                data = res_json.get("data") if isinstance(res_json.get("data"), dict) else res_json
                device_id = data.get("device_id")
                secret_token = data.get("secret_token")

                if device_id and secret_token:
                    save_credentials(str(device_id), str(secret_token))
                    try:
                        from config import CRED_DIR
                        env_file = CRED_DIR / ".env"
                        env_file.write_text(f"SERVER_URL={target_backend_url}\nBACKEND_URL={target_backend_url}\n", encoding="utf-8")
                        pg_env = Path(r"C:\ProgramData\ParentalControl\.env")
                        if pg_env.parent.exists():
                            pg_env.write_text(f"SERVER_URL={target_backend_url}\nBACKEND_URL={target_backend_url}\n", encoding="utf-8")
                    except Exception as _env_err:
                        logger.warning(f"Could not persist SERVER_URL to .env: {_env_err}")
                    paired_success = True
                    messagebox.showinfo("Thành công", "Đăng ký thiết bị thành công!")
                    root.destroy()
                else:
                    error_msg = res_json.get("error") or "Không nhận được device_id / secret_token từ máy chủ."
                    status_lbl.config(text=f"Lỗi: {error_msg}", fg="#f38ba8")
            else:
                error_msg = res_json.get("error") or f"Lỗi máy chủ (HTTP {status_code})"
                status_lbl.config(text=f"Đăng ký thất bại: {error_msg}", fg="#f38ba8")

        except Exception as e:
            err_str = str(e)
            logger.error(f"Pairing request failed: {err_str}")
            
            # Specific DNS & Network Connection Error Handling
            if "NameResolutionError" in err_str or "getaddrinfo failed" in err_str or "[Errno 11001]" in err_str:
                display_msg = "Không thể phân giải địa chỉ Server. Vui lòng kiểm tra DNS/Internet hoặc cấu hình SERVER_URL trong file .env"
            elif "ConnectionRefusedError" in err_str or "10061" in err_str or "Max retries exceeded" in err_str:
                display_msg = f"Không thể kết nối đến Máy chủ ({backend_url}). Vui lòng kiểm tra xem Backend Server đã bật chưa."
            else:
                display_msg = f"Lỗi kết nối máy chủ: {err_str}"

            status_lbl.config(text=display_msg, fg="#f38ba8")

    # Submit Button
    submit_btn = tk.Button(
        body_frame,
        text="Đăng ký thiết bị",
        command=on_pair_submit,
        font=("Segoe UI", 12, "bold"),
        bg="#89b4fa",
        fg="#11111b",
        activebackground="#b4befe",
        activeforeground="#11111b",
        relief="flat",
        cursor="hand2"
    )
    submit_btn.pack(fill="x", ipady=6)

    root.bind("<Return>", lambda e: on_pair_submit())

    root.mainloop()
    return paired_success


if __name__ == "__main__":
    success = run_pairing_ui()
    print(f"Pairing result: {success}")
