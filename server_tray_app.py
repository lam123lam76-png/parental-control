"""
PARENTAL CONTROL - WINDOWS SYSTEM TRAY SERVER & TUNNEL APP (v3.0 ENTERPRISE RESILIENT & SELF-HEALING)
Runs Master Local Server (FastAPI + Web UI) & Cloudflare Tunnel silently in Windows System Tray.
Features:
 - Automatic process supervisor / watchdog: Auto-restarts backend/tunnel instantly if they crash or exit.
 - Hot-reloading enabled for uvicorn (--reload) so code updates reload in RAM automatically.
 - Single-port unified serving (FastAPI serves both API and Web UI on Port 8000).
 - Thread-safe tray menu callbacks for Status, Open Browser, Copy Link, Restart & Exit.
"""

import os
import sys
import re
import time
import subprocess
import threading
import webbrowser
import pystray
from PIL import Image, ImageDraw

# Global state
backend_proc = None
web_proc = None
tunnel_proc = None
tunnel_url = ""
is_running = False
supervisor_thread = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL_FILE = os.path.join(BASE_DIR, ".cloudflared_url.txt")
TOKEN_FILE = os.path.join(BASE_DIR, ".cloudflare_token.txt")
OFFICIAL_DOMAIN = "https://nguyentruclam.io.vn"

def _ensure_single_instance() -> bool:
    """Prevent multiple tray apps (each would spawn its own backend/tunnel/web),
    which is what caused many duplicate uvicorn instances all bound to port 8000."""
    try:
        import ctypes
        name = "Global\\ParentalControlServerTray_SingleInstance"
        ctypes.WinDLL('kernel32', use_last_error=True).CreateMutexW(None, False, name)
        err = ctypes.get_last_error()
        if err == 183:  # ERROR_ALREADY_EXISTS
            print("[TRAY] Another server instance is already running — exiting this one.")
            return False
    except Exception as e:
        print(f"[TRAY] Single-instance check failed (continuing): {e}")
    return True


class _DummyProc:
    """Stand-in for a subprocess that is managed externally (e.g. a Windows
    service); poll() returning None makes the supervisor treat it as running."""
    def poll(self):
        return None

def create_tray_icon_image():
    """Generate a clean 64x64 Emerald Green Shield icon for Windows System Tray."""
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw Emerald Ink Shield Circle background (#064E3B)
    draw.ellipse((4, 4, 60, 60), fill="#064E3B", outline="#F8E7C9", width=3)
    # Inner Emerald core dot (#10B981)
    draw.ellipse((20, 20, 44, 44), fill="#10B981")
    return image

def is_port_in_use(port=8000):
    """Returns True if port is currently in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def free_port_8000():
    """Safely terminate any process listening on Port 8000 using native psutil."""
    import psutil
    current_pid = os.getpid()
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == 8000:
                pid = conn.pid
                if pid and pid > 0 and pid != current_pid:
                    try:
                        proc = psutil.Process(pid)
                        pname = proc.name().lower()
                        # Never kill agent or watchdog!
                        if "parentalcontrolagent" not in pname and "parentalcontrolwatchdog" not in pname:
                            proc.kill()
                            print(f"[TRAY WATCHDOG] Terminated PID {pid} ({proc.name()}) holding port 8000")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                        pass
    except Exception as e:
        print(f"[TRAY WATCHDOG] free_port_8000 note: {e}")

def get_current_tunnel_url():
    """Returns official domain URL or captured Cloudflare Tunnel URL."""
    global tunnel_url
    if os.path.exists(TOKEN_FILE):
        return OFFICIAL_DOMAIN
    if tunnel_url and tunnel_url.startswith("https://"):
        return tunnel_url
    if os.path.exists(URL_FILE):
        try:
            with open(URL_FILE, "r", encoding="utf-8") as f:
                saved = f.read().strip()
                if saved.startswith("https://"):
                    tunnel_url = saved
                    return saved
        except Exception:
            pass
    return OFFICIAL_DOMAIN

def _start_backend_proc():
    """Internal helper to start FastAPI backend with --reload."""
    global backend_proc
    free_port_8000()
    backend_dir = os.path.join(BASE_DIR, "backend_api")
    py_exec = sys.executable
    if "pythonw" in py_exec.lower():
        py_exec = re.sub(r'pythonw', 'python', py_exec, flags=re.IGNORECASE)
    backend_cmd = [py_exec, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    try:
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=backend_dir,
            creationflags=subprocess.CREATE_NO_WINDOW  # no console window spam
        )
        print("[TRAY WATCHDOG] FastAPI Backend started on port 8000")
        return True
    except Exception as e:
        print(f"[TRAY ERROR] Failed to start backend: {e}")
        return False

def _start_web_proc():
    """Internal helper to start Vite Dev Server (optional fallback)."""
    global web_proc
    web_dir = os.path.join(BASE_DIR, "manager-web")
    web_cmd = "cmd.exe /c npm run dev -- --host 0.0.0.0"
    try:
        web_proc = subprocess.Popen(
            web_cmd,
            cwd=web_dir,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print("[TRAY WATCHDOG] Web Manager UI started on port 5173")
        return True
    except Exception as e:
        print(f"[TRAY ERROR] Failed to start web ui: {e}")
        return False

def _start_tunnel_proc(icon=None):
    """Internal helper to start Cloudflare Tunnel (skips if the Cloudflared
    Windows service is already managing it, to avoid duplicate tunnels)."""
    global tunnel_proc, tunnel_url

    # If the Cloudflared service is already running, it owns the named tunnel
    # for nguyentruclam.io.vn -> localhost:8000. Do not spawn a second one.
    try:
        import subprocess as _sp
        svc_check = _sp.run(["sc", "query", "Cloudflared"], capture_output=True, text=True, timeout=10)
        if svc_check.returncode == 0 and "RUNNING" in svc_check.stdout.upper():
            print("[TRAY TUNNEL] Cloudflared service already RUNNING — using it; skipping duplicate tunnel.")
            tunnel_url = OFFICIAL_DOMAIN
            tunnel_proc = _DummyProc()  # poll() returns None -> supervisor treats it as running
            return
    except Exception as e:
        print(f"[TRAY TUNNEL] service check skipped: {e}")

    cloudflared_bin = "C:\\Cloudflared\\cloudflared.exe" if os.path.exists("C:\\Cloudflared\\cloudflared.exe") else "cloudflared"
    
    token = ""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                token = f.read().strip()
        except Exception:
            pass

    if token:
        tunnel_cmd = [cloudflared_bin, "tunnel", "run", "--token", token]
    else:
        # Tunnel points to Port 8000 which serves both API and static Web UI SPA!
        tunnel_cmd = [cloudflared_bin, "tunnel", "--url", "http://localhost:8000"]

    try:
        tunnel_proc = subprocess.Popen(
            tunnel_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if token:
            tunnel_url = OFFICIAL_DOMAIN
            print(f"[TRAY SUCCESS] Named Tunnel active: {OFFICIAL_DOMAIN}")
            if icon:
                icon.title = f"Parental Control Active\n{OFFICIAL_DOMAIN}"
        else:
            def read_tunnel_output():
                global tunnel_url, tunnel_proc
                if not tunnel_proc or not tunnel_proc.stdout:
                    return
                for line in iter(tunnel_proc.stdout.readline, ''):
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        captured = match.group(0)
                        tunnel_url = captured
                        print(f"[TRAY SUCCESS] Live Cloudflare Tunnel: {tunnel_url}")
                        try:
                            with open(URL_FILE, "w", encoding="utf-8") as f:
                                f.write(tunnel_url)
                        except Exception:
                            pass
                        if icon:
                            icon.title = f"Parental Control Active\n{tunnel_url}"
                        break
            threading.Thread(target=read_tunnel_output, daemon=True).start()
    except Exception as e:
        print(f"[TRAY ERROR] Tunnel exception: {e}")

def _supervisor_loop(icon=None):
    """
    Self-healing watchdog loop running every 4 seconds.
    If backend or tunnel process dies unexpectedly while is_running is True,
    it automatically restarts them to guarantee 100% server uptime.
    """
    global is_running, backend_proc, web_proc, tunnel_proc
    while is_running:
        time.sleep(4)
        if not is_running:
            break

        # Check Backend (Port 8000)
        if (backend_proc is None or backend_proc.poll() is not None) and not is_port_in_use(8000):
            print("[TRAY WATCHDOG ALERT] Backend process exited unexpectedly! Auto-restarting backend now...")
            _start_backend_proc()

        # Check Web UI (Port 5173)
        if (web_proc is None or web_proc.poll() is not None) and not is_port_in_use(5173):
            print("[TRAY WATCHDOG ALERT] Web UI process exited unexpectedly! Auto-restarting web UI now...")
            _start_web_proc()

        # Check Tunnel
        if tunnel_proc is None or tunnel_proc.poll() is not None:
            print("[TRAY WATCHDOG ALERT] Cloudflare tunnel exited unexpectedly! Auto-restarting tunnel now...")
            _start_tunnel_proc(icon)

def start_services(icon=None):
    global is_running, supervisor_thread
    if is_running:
        return

    is_running = True
    if icon:
        icon.title = f"Parental Control Server Starting..."

    _start_backend_proc()
    _start_web_proc()
    _start_tunnel_proc(icon)

    # Start continuous self-healing supervisor watchdog thread
    supervisor_thread = threading.Thread(target=_supervisor_loop, args=(icon,), daemon=True)
    supervisor_thread.start()
    print("[TRAY WATCHDOG] Continuous self-healing supervisor active.")

def stop_services(icon=None):
    global backend_proc, web_proc, tunnel_proc, is_running, tunnel_url
    is_running = False
    tunnel_url = ""

    if backend_proc:
        try:
            backend_proc.terminate()
        except Exception:
            pass
        backend_proc = None

    if web_proc:
        try:
            web_proc.terminate()
        except Exception:
            pass
        web_proc = None

    if tunnel_proc:
        try:
            tunnel_proc.terminate()
        except Exception:
            pass
        tunnel_proc = None

    free_port_8000()
    if icon:
        icon.title = "Parental Control Server (Đã dừng)"

def restart_services(icon=None):
    """Cleanly restart all server processes asynchronously."""
    def _do_restart():
        print("[TRAY SYSTEM] Restarting all services...")
        stop_services(icon)
        time.sleep(2)
        start_services(icon)
        print("[TRAY SYSTEM] All services restarted successfully.")
    threading.Thread(target=_do_restart, daemon=True).start()

# --- DYNAMIC MENU LABELS ---

def get_cloudflare_menu_label(item):
    url = get_current_tunnel_url()
    return f"🌐 Mở Web Tên Miền ({url})"

def get_copy_menu_label(item):
    url = get_current_tunnel_url()
    return f"📋 Sao Chép Link Tên Miền ({url})"

# --- THREAD-SAFE CONTEXT MENU CALLBACKS ---

def open_local_web(icon, item):
    """Open Local Web UI in default browser asynchronously."""
    threading.Thread(target=lambda: webbrowser.open("http://localhost:8000"), daemon=True).start()

def open_tunnel_web(icon, item):
    """Open Cloudflare Tunnel URL / Domain in default browser asynchronously."""
    url = get_current_tunnel_url()
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

def copy_tunnel_url(icon, item):
    """Copy Domain / Cloudflare Tunnel URL to Windows Clipboard."""
    def _copy():
        url = get_current_tunnel_url()
        try:
            cmd = f'echo | set /p="{url}" | clip'
            subprocess.run(cmd, shell=True, check=True)
            print(f"[TRAY APP] Copied URL to Clipboard: {url}")
        except Exception as e:
            print(f"[TRAY APP ERROR] Copy failed: {e}")

    threading.Thread(target=_copy, daemon=True).start()

def toggle_services(icon, item):
    """Toggle server start/stop state asynchronously."""
    def _toggle():
        if is_running:
            stop_services(icon)
        else:
            start_services(icon)
    threading.Thread(target=_toggle, daemon=True).start()

def trigger_restart(icon, item):
    """Trigger clean restart of all services."""
    restart_services(icon)

def exit_tray(icon, item):
    """Stop all background services and exit tray app cleanly."""
    def _exit():
        stop_services(icon)
        icon.stop()
    threading.Thread(target=_exit, daemon=True).start()

def main():
    if not _ensure_single_instance():
        return
    image = create_tray_icon_image()
    
    menu = pystray.Menu(
        pystray.MenuItem("🛡️ Parental Control Server v3.0 (Self-Healing)", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌐 Mở Web Quản Lý (Local http://localhost:8000)", open_local_web),
        pystray.MenuItem(get_cloudflare_menu_label, open_tunnel_web),
        pystray.MenuItem(get_copy_menu_label, copy_tunnel_url),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🔄 Khởi Động Lại Hệ Thống (Restart All)", trigger_restart),
        pystray.MenuItem(lambda item: "🛑 Dừng Máy Chủ" if is_running else "🟢 Khởi Động Máy Chủ", toggle_services),
        pystray.MenuItem("❌ Thoát (Exit)", exit_tray),
    )

    icon = pystray.Icon(
        "ParentalControlServer",
        image,
        "Parental Control Server & Tunnel Active",
        menu
    )

    # Start services on launch asynchronously
    threading.Thread(target=lambda: start_services(icon), daemon=True).start()
    icon.run()

if __name__ == "__main__":
    main()
