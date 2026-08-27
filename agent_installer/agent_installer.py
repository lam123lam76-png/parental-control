"""
agent_installer.py — Agent Installer for Parental Control.

One executable that runs on the target machine, downloads the latest agent
package from the backend and installs / updates the agent — instead of
manually packaging and copying it over.

Usage:
    AgentInstaller.exe [--url <backend_url>] [--install|--update|--auto] [--target <dir>]

Exit codes:
    0  success (installed/updated, or already latest)
    1  generic error (extract, copy, task ...)
    2  network / could not fetch version.json
    3  wrong flow (e.g. --update when agent not installed)
    4  not running as Administrator
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
try:
    from PIL import Image, ImageTk
except ImportError:
    pass

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BACKEND_URL = "https://nguyentruclam.io.vn"
# BACKUP_SERVER_URL mặc định trỏ về chính Worker (nguyentruclam.io.vn) — Worker đã
# xử lý failover home→backup, nên agent không cần biết URL Vercel cụ thể.
DEFAULT_BACKUP_URL = "https://nguyentruclam.io.vn"
DEFAULT_TARGET_DIR = Path(r"C:\ProgramData\ParentalControl")
ZIP_NAME = "agent-update.zip"
VERSION_JSON = "version.json"
REQUIRED_FILES = [
    "ParentalControlAgent.exe",
    "ParentalControlWatchdog.exe",
    "Updater.exe",
]
WATCHDOG_EXE = "ParentalControlWatchdog.exe"
LOG_FILE = Path(tempfile.gettempdir()) / "pc_installer" / "installer.log"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("AgentInstaller")


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )



GUI_QUEUE = queue.Queue()

def log(message: str) -> None:
    logger.info(message)
    try:
        print(message)
    except Exception:
        pass
    if GUI_QUEUE is not None:
        GUI_QUEUE.put(("log", message))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_admin() -> bool:
    """Return True when the current process is elevated.

    Dev/test escape hatch: set PC_INSTALLER_SKIP_ADMIN=1 to bypass the
    admin check (used only for --target sandbox tests).
    """
    if os.environ.get("PC_INSTALLER_SKIP_ADMIN") == "1":
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def resolve_backend_url(raw: str) -> str:
    url = (raw or DEFAULT_BACKEND_URL).strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def version_tuple(version: str):
    """Parse '1.2.3' -> (1, 2, 3); non-numeric parts become 0."""
    parts = []
    for chunk in str(version or "").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def read_local_version(target_dir: Path) -> str:
    """Read the installed agent version from version.json, if present."""
    for candidate in (
        target_dir / VERSION_JSON,
        Path(os.environ.get("APPDATA", "C:\\")) / "ParentalControl" / "updates" / VERSION_JSON,
    ):
        try:
            if candidate.exists():
                data = json.loads(candidate.read_text(encoding="utf-8"))
                ver = str(data.get("version", "")).strip()
                if ver:
                    return ver
        except Exception:
            continue
    return "0.0.0"


def _cache_bust(url: str) -> str:
    """Append a timestamp query param so CDN/proxy caches always revalidate.

    The zip/version.json may be cached by Cloudflare for a long TTL; without
    a cache-buster the installer could download a stale build.
    """
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={int(time.time())}"


def fetch_version_info(backend_url: str) -> dict:
    """GET {url}/static/updates/version.json -> {version, download_url}."""
    url = _cache_bust(f"{backend_url}/static/updates/{VERSION_JSON}")
    log(f"Fetching version info: {url}")
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} from {url}")
    return resp.json()


def download_zip(backend_url: str, dest: Path) -> None:
    """Download agent-update.zip into dest with stream, progress, resume, and retries."""
    url = f"{backend_url}/static/updates/{ZIP_NAME}"
    
    max_retries = 5
    downloaded = 0
    total_size = 0
    
    for attempt in range(max_retries):
        try:
            headers = {}
            if downloaded > 0:
                headers["Range"] = f"bytes={downloaded}-"
                log(f"Đang tiếp tục tải từ {downloaded / (1024*1024):.2f} MB (Lần thử {attempt+1}/{max_retries})...")
            else:
                log(f"Đang chuẩn bị tải về (Lần thử {attempt+1}/{max_retries}) ...")

            resp = requests.get(_cache_bust(url), headers=headers, stream=True, timeout=30)
            
            if resp.status_code not in (200, 206):
                raise RuntimeError(f"HTTP {resp.status_code} from {url}")
            
            if resp.status_code == 200:
                # Start from scratch
                downloaded = 0
                total_size = int(resp.headers.get("content-length", 0))
                if attempt == 0 and total_size > 0:
                    log(f"Kích thước file: {total_size / (1024*1024):.2f} MB")
            
            mode = "ab" if downloaded > 0 else "wb"
            block_size = 1024 * 64
            last_log_percent = 0
            
            with open(dest, mode) as f:
                for data in resp.iter_content(block_size):
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        if GUI_QUEUE is not None:
                            GUI_QUEUE.put(("progress", percent))
                        
                        # Log to console box every 10% to show it's alive
                        if percent >= last_log_percent + 10:
                            log(f"  -> Đã tải {percent}% ...")
                            last_log_percent = (percent // 10) * 10

            if total_size > 0 and downloaded >= total_size:
                log(f"Đã tải xong {downloaded / (1024*1024):.2f} MB -> {dest}")
                return
            elif total_size == 0 and downloaded > 0:
                log(f"Đã tải xong {downloaded / (1024*1024):.2f} MB (không rõ tổng) -> {dest}")
                return
                
        except Exception as e:
            log(f"Lỗi mạng trong lúc tải: {e}")
            if attempt < max_retries - 1:
                log("Sẽ tiếp tục tải lại sau 3 giây...")
                time.sleep(3)
            else:
                raise RuntimeError(f"Không thể hoàn tất tải file sau {max_retries} lần thử.")



def extract_zip(zip_path: Path, out_dir: Path) -> None:
    """Extract zip; raise if required files are missing."""
    log(f"Extracting {zip_path.name} -> {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)

    missing = [f for f in REQUIRED_FILES if not (out_dir / f).exists()]
    if missing:
        raise RuntimeError(f"Package missing required files: {', '.join(missing)}")
    for f in REQUIRED_FILES:
        if (out_dir / f).stat().st_size == 0:
            raise RuntimeError(f"Package file is empty: {f}")


# ---------------------------------------------------------------------------
# Core actions
# ---------------------------------------------------------------------------
def derive_ws_url(backend_url: str) -> str:
    """https://host -> wss://host ; http://host -> ws://host."""
    if backend_url.startswith("https://"):
        return "wss://" + backend_url[len("https://"):]
    if backend_url.startswith("http://"):
        return "ws://" + backend_url[len("http://"):]
    return backend_url


def write_env_file(target_dir: Path, backend_url: str, backup_url: str = "") -> None:
    """Create/update ProgramData .env with server URLs.

    Required for machines that never had the agent installed: utils/config.py
    hard-requires BACKEND_URL/WS_URL and sys.exit()s the agent when missing
    (old manual installs shipped a .env, the installer must too). Existing
    keys (AGENT_PASSWORD, TELEGRAM_*, BACKUP_SERVER_URL, ...) are preserved.
    """
    env_path = target_dir / ".env"
    server_url = backend_url.rstrip("/")
    wanted = {
        "SERVER_URL": server_url,
        "BACKEND_URL": server_url,
        "WS_URL": derive_ws_url(server_url),
    }
    if backup_url:
        wanted["BACKUP_SERVER_URL"] = backup_url.rstrip("/")
    lines: list[str] = []
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []
    kept = [ln for ln in lines if not any(ln.strip().startswith(k + "=") for k in wanted)]
    for k, v in wanted.items():
        kept.append(f"{k}={v}")
    try:
        env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        log(f"  .env written ({server_url})" + (f" + backup {backup_url}" if backup_url else ""))
    except Exception as e:
        log(f"  WARNING: could not write .env: {e}")


def install_agent(backend_url: str, target_dir: Path, extracted: Path, enable_autostart: bool = True, backup_url: str = "") -> None:
    """Copy files into target_dir and register autostart (needs admin)."""
    log(f"Installing agent to {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy required files + optional Install bat
    for f in REQUIRED_FILES:
        src = extracted / f
        if src.exists():
            shutil.copy2(src, target_dir / f)
            log(f"  copied {f}")
    install_bat = extracted / "Install_Parental_Control.bat"
    if install_bat.exists():
        shutil.copy2(install_bat, target_dir / "Install_Parental_Control.bat")

    write_env_file(target_dir, backend_url, backup_url)

    if not enable_autostart:
        log("  autostart skipped (--no-autostart test mode)")
        return

    # 2. Register autostart (Registry Run + Scheduled Task battery-safe Highest).
    #    Reuse agent/protection/autostart.py if importable; if the `protection`
    #    package isn't bundled into this exe (PyInstaller lazy-import miss), fall
    #    back gracefully — the WATCHDOG registers autostart itself on startup
    #    (watchdog.py calls install_autostart), so this step must never abort install.
    install_autostart = None
    install_scheduled_task = None
    try:
        from protection.autostart import install_autostart, install_scheduled_task
    except Exception:
        install_autostart = None
        install_scheduled_task = None

    if install_autostart:
        try:
            install_autostart()
            log("  autostart registered (Registry + Scheduled Task)")
        except Exception as e:
            # Scheduled task may need elevation; fall back to task-only attempt
            log(f"  autostart error (watchdog will re-register): {e}")
            try:
                install_scheduled_task()
                log("  scheduled task registered")
            except Exception as e2:
                log(f"  scheduled task error (watchdog will re-register): {e2}")
    else:
        log("  autostart import unavailable — watchdog will register autostart on first run")


def start_watchdog(target_dir: Path) -> None:
    watchdog = target_dir / WATCHDOG_EXE
    if watchdog.exists():
        log(f"Starting watchdog: {watchdog}")
        subprocess.Popen([str(watchdog)], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        log("Watchdog not found; skipping start.")


def stop_agent_processes() -> None:
    """Kill running agent + watchdog before overwriting files.

    taskkill alone often fails with Access denied on the elevated agent/watchdog
    (scheduled-task Highest), which locks the exe and makes the overwrite fail
    with Permission denied. Add PowerShell Stop-Process and wmic fallbacks.
    """
    for name in ("ParentalControlAgent.exe", "ParentalControlWatchdog.exe", "Updater.exe"):
        subprocess.run(f'taskkill /F /T /IM {name} >nul 2>&1', shell=True)
        proc_name = name[:-4] if name.lower().endswith(".exe") else name
        subprocess.run(
            f'powershell -NoProfile -Command "Get-Process -Name \'{proc_name}\' '
            f'-ErrorAction SilentlyContinue | Stop-Process -Force"',
            shell=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        subprocess.run(f'wmic process where "name=\'{name}\'" delete >nul 2>&1', shell=True)
    time.sleep(2)


def write_shutdown_flag(target_dir: Path) -> None:
    """Block watchdog from racing while we overwrite binaries."""
    try:
        flag = target_dir / "shutdown.flag"
        flag.write_text("PC_WATCHDOG_SAFE_EXIT_a8f3e1b9c2d7", encoding="utf-8")
    except Exception:
        pass


def clear_shutdown_flag(target_dir: Path) -> None:
    try:
        flag = target_dir / "shutdown.flag"
        if flag.exists():
            flag.unlink()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------
def cmd_install(args) -> int:
    if not is_admin():
        log("Cần quyền Administrator. Click phải -> Run as administrator.")
        return 4

    backend_url = resolve_backend_url(args.url)
    target_dir = Path(args.target or DEFAULT_TARGET_DIR)

    # Agent already installed?
    if (target_dir / "ParentalControlAgent.exe").exists():
        log("Agent đã cài. Dùng --update để cập nhật.")
        return 0

    # Fetch version (validates connectivity + package existence)
    try:
        version_info = fetch_version_info(backend_url)
        log(f"Latest version: {version_info.get('version', '?')}")
    except Exception as e:
        log(f"Lỗi mạng / không lấy được version.json: {e}")
        return 2

    work = Path(tempfile.gettempdir()) / "pc_installer"
    zip_path = work / ZIP_NAME
    extracted = work / "extracted"

    try:
        download_zip(backend_url, zip_path)
        extract_zip(zip_path, extracted)
        install_agent(backend_url, target_dir, extracted, enable_autostart=not args.no_autostart, backup_url=args.backup_url or DEFAULT_BACKUP_URL)
        if not args.no_start:
            start_watchdog(target_dir)
        log("Cài đặt hoàn tất.")
        return 0
    except Exception as e:
        log(f"Lỗi khi cài đặt: {e}")
        return 1


def cmd_update(args) -> int:
    if not is_admin():
        log("Cần quyền Administrator. Click phải -> Run as administrator.")
        return 4

    backend_url = resolve_backend_url(args.url)
    target_dir = Path(args.target or DEFAULT_TARGET_DIR)

    # Agent not installed yet?
    if not (target_dir / "ParentalControlAgent.exe").exists():
        log("Chưa cài agent. Dùng --install.")
        return 3

    try:
        version_info = fetch_version_info(backend_url)
        latest = str(version_info.get("version", "0.0.0"))
    except Exception as e:
        log(f"Lỗi mạng / không lấy được version.json: {e}")
        return 2

    current = read_local_version(target_dir)
    log(f"Current: {current} | Latest: {latest}")

    if version_tuple(current) >= version_tuple(latest):
        log("Đã là phiên bản mới nhất.")
        return 0

    work = Path(tempfile.gettempdir()) / "pc_installer"
    zip_path = work / ZIP_NAME
    extracted = work / "extracted"

    try:
        write_shutdown_flag(target_dir)
        stop_agent_processes()
        download_zip(backend_url, zip_path)
        extract_zip(zip_path, extracted)

        # Overwrite binaries
        for f in REQUIRED_FILES:
            src = extracted / f
            if src.exists():
                shutil.copy2(src, target_dir / f)
                log(f"  updated {f}")
        install_bat = extracted / "Install_Parental_Control.bat"
        if install_bat.exists():
            shutil.copy2(install_bat, target_dir / "Install_Parental_Control.bat")

        # Persist version for future comparisons
        try:
            (target_dir / VERSION_JSON).write_text(
                json.dumps(version_info, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

        write_env_file(target_dir, backend_url, args.backup_url or DEFAULT_BACKUP_URL)
        clear_shutdown_flag(target_dir)
        if not args.no_start:
            start_watchdog(target_dir)
        log("Cập nhật hoàn tất.")
        return 0
    except Exception as e:
        clear_shutdown_flag(target_dir)
        log(f"Lỗi khi cập nhật: {e}")
        return 1


def cmd_auto(args) -> int:
    target_dir = Path(args.target or DEFAULT_TARGET_DIR)
    if (target_dir / "ParentalControlAgent.exe").exists():
        return cmd_update(args)
    return cmd_install(args)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

class InstallerGUI(tk.Tk):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.title("Parental Control Agent Installer")
        self.geometry("600x420")
        self.configure(bg="#09090b")
        self.resizable(False, False)
        self.eval("tk::PlaceWindow . center")
        
        # Styles for dark mode
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", thickness=8, background="#064E3B", troughcolor="#27272a", bordercolor="#09090b", lightcolor="#064E3B", darkcolor="#064E3B")
        
        # Header
        header = tk.Frame(self, bg="#09090b")
        header.pack(fill=tk.X, padx=20, pady=20)
        
        self.logo_img = None
        try:
            base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            img_path = os.path.join(base_path, "new_logo.png")
            if os.path.exists(img_path):
                img = Image.open(img_path)
                img = img.resize((64, 64), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                lbl = tk.Label(header, image=self.logo_img, bg="#09090b")
                
                lbl.pack(side=tk.LEFT, padx=(0, 15))
                try:
                    self.iconphoto(False, self.logo_img)
                except Exception:
                    pass
        except Exception as e:
            pass
            
        title_lbl = tk.Label(header, text="Agent Installer", font=("Segoe UI", 18, "bold"), fg="#F8E7C9", bg="#09090b")
        title_lbl.pack(side=tk.LEFT, anchor="w")
        
        # Progress and status
        self.status = tk.Label(self, text="Nhấn 'Cài đặt' để bắt đầu...", font=("Segoe UI", 11, "bold"), fg="#d4d4d8", bg="#09090b", justify=tk.LEFT)
        self.status.pack(fill=tk.X, padx=20, pady=(5, 5))
        
        self.progress = ttk.Progressbar(self, style="TProgressbar", mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=20, pady=5)
        
        # Console output
        log_frame = tk.Frame(self, bg="#18181b", bd=1, relief=tk.SOLID, highlightbackground="#27272a", highlightthickness=1)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_text = tk.Text(log_frame, height=6, bg="#18181b", fg="#a1a1aa", font=("Consolas", 9), bd=0, highlightthickness=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#09090b")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.start_btn = tk.Button(btn_frame, text="Cài đặt", font=("Segoe UI", 10, "bold"), bg="#064E3B", fg="#F8E7C9", bd=0, activebackground="#059669", activeforeground="#F8E7C9", cursor="hand2", command=self.start_install, width=15)
        self.start_btn.pack(side=tk.RIGHT)
        
        self.process_queue()
        
    def start_install(self):
        self.start_btn.config(state=tk.DISABLED, bg="#27272a", text="Đang xử lý...")
        self.progress["mode"] = "indeterminate"
        self.progress.start(15)
        self.status.config(text="Đang tải xuống và cấu hình...", fg="#F8E7C9")
        threading.Thread(target=self.run_install, daemon=True).start()
        
    def run_install(self):
        try:
            if self.args.install:
                res = cmd_install(self.args)
            elif self.args.update:
                res = cmd_update(self.args)
            else:
                res = cmd_auto(self.args)
            GUI_QUEUE.put(("done", res))
        except Exception as e:
            GUI_QUEUE.put(("error", str(e)))
            
    def process_queue(self):
        try:
            while True:
                msg_type, content = GUI_QUEUE.get_nowait()
                if msg_type == "log":
                    self.log_text.insert(tk.END, content + "\\n")
                    self.log_text.see(tk.END)
                    if "extracting" in content.lower() or "installing" in content.lower() or "cập nhật" in content.lower():
                        self.progress.stop()
                        self.progress["mode"] = "indeterminate"
                        self.progress.start(15)
                    if "hoàn tất" in content.lower():
                        self.status.config(text=content, fg="#34d399")
                    else:
                        self.status.config(text=content)
                elif msg_type == "progress":
                    self.progress["mode"] = "determinate"
                    self.progress["value"] = content
                    self.status.config(text=f"Đang tải dữ liệu: {content}%", fg="#34d399")
                elif msg_type == "done":
                    self.progress.stop()
                    self.progress["mode"] = "determinate"
                    self.progress["value"] = 100
                    if content == 0:
                        self.status.config(text="Hoàn tất!", fg="#34d399")
                        self.start_btn.config(text="Đóng", state=tk.NORMAL, bg="#064E3B", command=self.destroy)
                        messagebox.showinfo("Thành công", "Cài đặt / Cập nhật thành công!", parent=self)
                    else:
                        self.status.config(text="Thất bại!", fg="#f87171")
                        self.start_btn.config(text="Thử lại", state=tk.NORMAL, bg="#064E3B", command=self.start_install)
                        messagebox.showerror("Lỗi", f"Có lỗi xảy ra (mã lỗi {content}). Vui lòng xem log.", parent=self)
                elif msg_type == "error":
                    self.progress.stop()
                    self.status.config(text="Lỗi nghiêm trọng", fg="#f87171")
                    self.start_btn.config(text="Thử lại", state=tk.NORMAL, bg="#064E3B", command=self.start_install)
                    messagebox.showerror("Lỗi", f"Lỗi không mong muốn:\\n{content}", parent=self)
        except queue.Empty:
            pass
        self.after(50, self.process_queue)

def main() -> int:
    parser = argparse.ArgumentParser(description="Parental Control Agent Installer")
    parser.add_argument("--url", default=None, help="Backend URL (default: https://nguyentruclam.io.vn)")
    parser.add_argument("--backup-url", default=None, help="Backup (Vercel) API URL written to .env as BACKUP_SERVER_URL (default: keep existing)")
    parser.add_argument("--install", action="store_true", help="Install agent (first time)")
    parser.add_argument("--update", action="store_true", help="Update agent to latest")
    parser.add_argument("--auto", action="store_true", help="Install if missing, else update")
    parser.add_argument("--target", default=None, help="Dev/test: custom install directory")
    parser.add_argument("--no-autostart", action="store_true", help="Dev/test: copy files only, skip autostart")
    parser.add_argument("--no-start", action="store_true", help="Dev/test: do not start watchdog after install")
    parser.add_argument("--cli", action="store_true", help="Run without GUI")
    args = parser.parse_args()

    setup_logging()
    
    if args.cli:
        log(f"Agent Installer CLI started. url={resolve_backend_url(args.url)}")
        if args.install: return cmd_install(args)
        if args.update: return cmd_update(args)
        return cmd_auto(args)
    else:
        app = InstallerGUI(args)
        app.mainloop()
        return 0


if __name__ == "__main__":
    sys.exit(main())
