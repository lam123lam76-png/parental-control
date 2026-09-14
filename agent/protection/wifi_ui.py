"""
wifi_ui.py — Wi-Fi connection UI for the lock screen.

When the device is locked but has no network, the parent cannot unlock it from
the backend. This module lets the child/user connect to a Wi-Fi network directly
from the lock screen so the agent can regain connectivity (and thus be unlocked).

Built on `netsh wlan` (built into Windows) — no third-party deps.
"""
import logging
import subprocess
import tkinter as tk
from tkinter import messagebox

logger = logging.getLogger("WifiUI")

# Windows netsh WLAN commands
def _run(cmd: list[str]) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20, creationflags=0x08000000)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        logger.warning(f"netsh command failed: {e}")
        return ""


def list_wifi_networks() -> list[dict]:
    """Scan available Wi-Fi networks via netsh. Returns [{ssid, signal, auth, bssid}]."""
    out = _run(["netsh", "wlan", "show", "networks", "mode=bssid"])
    networks = []
    current = None
    for line in out.splitlines():
        line = line.strip()
        low = line.lower()
        if low.startswith("ssid"):
            name = line.split(":", 1)[1].strip() if ":" in line else ""
            current = {"ssid": name, "signal": "", "auth": ""}
            networks.append(current)
        elif current is not None:
            if low.startswith("signal"):
                current["signal"] = line.split(":", 1)[1].strip()
            elif low.startswith("authentication"):
                current["auth"] = line.split(":", 1)[1].strip()
    return networks


def connect_to_wifi(ssid: str, password: str) -> tuple[bool, str]:
    """
    Connect to a Wi-Fi network. Creates a temporary profile if a password is given,
    otherwise connects to an existing open/saved profile by name.
    Returns (ok, message).
    """
    try:
        # If password provided, build an XML profile and add it.
        if password:
            import tempfile
            from pathlib import Path
            auth = "WPA2PSK"
            encr = "AES"
            xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{ssid}</name>
  <SSIDConfig>
    <SSID><name>{ssid}</name></SSID>
  </SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM>
    <security>
      <authEncryption>
        <authentication>{auth}</authentication>
        <encryption>{encr}</encryption>
        <useOneX>false</useOneX>
      </authEncryption>
      <sharedKey>
        <keyType>passPhrase</keyType>
        <protected>false</protected>
        <keyMaterial>{password}</keyMaterial>
      </sharedKey>
    </security>
  </MSM>
</WLANProfile>"""
            tmp = Path(tempfile.gettempdir()) / f"wifi_{abs(hash(ssid))}.xml"
            tmp.write_text(xml, encoding="utf-8")
            _run(["netsh", "wlan", "add", "profile", f"filename={tmp}", "user=current"])
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

        # Connect by profile name
        res = _run(["netsh", "wlan", "connect", f"name={ssid}", f"ssid={ssid}"])
        if "connection request was completed successfully" in res.lower() or "successfully" in res.lower():
            return True, f"Đã kết nối {ssid}"
        return False, res.strip()[:200] or f"Không kết nối được {ssid}"
    except Exception as e:
        logger.error(f"connect_to_wifi error: {e}")
        return False, str(e)


class WiFiDialog(tk.Toplevel):
    """Modal Wi-Fi picker shown from the lock screen."""

    def __init__(self, parent, on_close=None):
        super().__init__(parent)
        self.title("Kết nối Wi-Fi")
        self.configure(bg="#1a1a1a")
        self.geometry("520x560")
        self.transient(parent)
        self.grab_set()
        self.attributes("-topmost", True)
        self._on_close = on_close
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._selected_ssid = ""
        self._build()
        self.refresh()

    def destroy(self):
        if getattr(self, "_on_close", None):
            try:
                self._on_close()
            except Exception:
                pass
        super().destroy()

    def _build(self):
        header = tk.Label(self, text="📶 Kết nối Wi-Fi",
                          font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#1a1a1a")
        header.pack(pady=(16, 4))
        sub = tk.Label(self, text="Chọn mạng để kết nối lại Internet",
                       font=("Segoe UI", 10), fg="#aaaaaa", bg="#1a1a1a")
        sub.pack(pady=(0, 12))

        # Refresh button
        top = tk.Frame(self, bg="#1a1a1a")
        top.pack(fill="x", padx=16)
        self.refresh_btn = tk.Button(top, text="🔄 Quét lại", command=self.refresh,
                                     font=("Segoe UI", 10), bg="#333333", fg="#ffffff",
                                     activebackground="#444444", relief="flat", cursor="hand2")
        self.refresh_btn.pack(side="right")

        # Network list
        self.list_frame = tk.Frame(self, bg="#1a1a1a")
        self.list_frame.pack(fill="both", expand=True, padx=16, pady=(8, 8))
        self.net_buttons = []

        # Password area
        pwd_frame = tk.Frame(self, bg="#1a1a1a")
        pwd_frame.pack(fill="x", padx=16, pady=(4, 8))
        tk.Label(pwd_frame, text="Mật khẩu (để trống nếu mạng không mật khẩu):",
                 font=("Segoe UI", 9), fg="#cccccc", bg="#1a1a1a").pack(anchor="w")
        self.pwd_entry = tk.Entry(pwd_frame, show="•", font=("Segoe UI", 12),
                                  bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff")
        self.pwd_entry.pack(fill="x", pady=(4, 0))

        self.status_lbl = tk.Label(self, text="", font=("Segoe UI", 9), fg="#4ade80", bg="#1a1a1a")
        self.status_lbl.pack(pady=(2, 0))

        # Connect + close
        btn_frame = tk.Frame(self, bg="#1a1a1a")
        btn_frame.pack(fill="x", padx=16, pady=(4, 14))
        tk.Button(btn_frame, text="Kết nối", command=self._connect,
                  font=("Segoe UI", 11, "bold"), bg="#007acc", fg="#ffffff",
                  activebackground="#005999", relief="flat", cursor="hand2").pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(btn_frame, text="Đóng", command=self.destroy,
                  font=("Segoe UI", 11), bg="#444444", fg="#ffffff",
                  activebackground="#555555", relief="flat", cursor="hand2").pack(side="right", expand=True, fill="x", padx=(4, 0))

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.net_buttons = []
        networks = list_wifi_networks()
        if not networks:
            tk.Label(self.list_frame, text="Không tìm thấy mạng Wi-Fi nào.",
                     font=("Segoe UI", 11), fg="#ff5555", bg="#1a1a1a").pack(pady=20)
            return
        for net in networks:
            ssid = net.get("ssid") or "(ẩn)"
            label = f"{ssid}   |   {net.get('signal') or '?'}   |   {net.get('auth') or '?'}"
            b = tk.Button(self.list_frame, text=label,
                          command=lambda s=ssid: self._select(s),
                          font=("Segoe UI", 10), anchor="w", bg="#242424", fg="#e0e0e0",
                          activebackground="#2e2e2e", relief="flat", cursor="hand2")
            b.pack(fill="x", pady=2)
            self.net_buttons.append(b)
        self.status_lbl.config(text=f"{len(networks)} mạng khả dụng")

    def _select(self, ssid):
        self._selected_ssid = ssid
        self.status_lbl.config(text=f"Đã chọn: {ssid}", fg="#cccccc")
        self.pwd_entry.focus_set()

    def _connect(self):
        ssid = self._selected_ssid
        pwd = self.pwd_entry.get().strip()
        if not ssid:
            self.status_lbl.config(text="Hãy chọn một mạng Wi-Fi trước.", fg="#ff5555")
            return
        self.status_lbl.config(text=f"Đang kết nối {ssid}...", fg="#ffcc00")
        self.update_idletasks()
        ok, msg = connect_to_wifi(ssid, pwd)
        self.status_lbl.config(text=msg, fg="#4ade80" if ok else "#ff5555")
        if ok:
            messagebox.showinfo("Kết nối Wi-Fi", msg, parent=self)


def show_wifi_dialog(root, on_close=None):
    """Open the Wi-Fi dialog as a child of the blocker window."""
    try:
        WiFiDialog(root, on_close=on_close)
    except Exception as e:
        logger.error(f"show_wifi_dialog error: {e}")
