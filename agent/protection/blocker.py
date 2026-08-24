"""
blocker.py — Multi-monitor Screen Blocker UI for Parental Control Agent

Creates a top-most, full-screen dark window overlay on all display monitors using Tkinter.
Blocks system shortcuts (overrideredirect, topmost, Alt+F4 disabled).
Displays customizable lock message, parent password entry for unlocking, and shutdown button.
"""

import logging
import os
import time
import tkinter as tk
from collections.abc import Callable

# Try importing win32api for Windows multi-monitor support
try:
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger("BlockerUI")

DEFAULT_MESSAGE = "Thiết bị đang bị khóa theo lịch hoặc lệnh từ Phụ huynh"


def get_display_monitors() -> list[dict]:
    """Retrieve bounding geometry for all display monitors."""
    monitors_info = []
    if HAS_WIN32:
        try:
            monitors = win32api.EnumDisplayMonitors()
            for hmon, hdc, (left, top, right, bottom) in monitors:
                monitors_info.append({
                    "left": left,
                    "top": top,
                    "width": right - left,
                    "height": bottom - top
                })
            if monitors_info:
                return monitors_info
        except Exception as e:
            logger.warning(f"Error enumerating monitors via win32api: {e}")

    return []


class BlockerUI:
    """
    Multi-monitor fullscreen dark overlay blocker UI.
    """

    def __init__(self, backend_url: str | None = None, password_verifier: Callable[[str], bool] | None = None, verify_password_fn: Callable[[str], bool] | None = None):
        """
        Initialize Blocker UI instance.
        
        :param backend_url: Backend server URL for parent password verification.
        :param password_verifier: Optional custom callback (password: str) -> bool.
        :param verify_password_fn: Optional custom callback alias (password: str) -> bool.
        """
        self.backend_url = backend_url
        self.password_verifier = password_verifier or verify_password_fn
        self.root: tk.Tk | None = None
        self.windows: list[tk.Toplevel | tk.Tk] = []
        self.reason_labels: list[tk.Label] = []
        self.error_label: tk.Label | None = None
        self.password_entry: tk.Entry | None = None
        self.is_showing = False
        self.current_reason = DEFAULT_MESSAGE
        self.countdown_label: tk.Label | None = None
        self.lock_start_time: float = 0.0
        # ── Bảo vệ brute-force mật khẩu ──
        self._failed_attempts: int = 0
        self._lockout_until: float = 0.0
        self.MAX_ATTEMPTS: int = 5
        self.LOCKOUT_SECONDS: int = 30


    @property
    def is_visible(self):
        return self.is_showing

    def _setup_window_blocking(self, win: tk.Tk | tk.Toplevel):
        """Apply top-most, fullscreen, and key-block flags to window."""
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.config(bg="#121212")

        # Disable window close & common shortcut keys
        win.protocol("WM_DELETE_WINDOW", lambda: "break")
        win.bind("<Alt-F4>", lambda e: "break")
        win.bind("<Escape>", lambda e: "break")
        win.bind("<Control-Alt-Delete>", lambda e: "break")
        win.bind("<Alt-Tab>", lambda e: "break")

    def _keep_topmost_loop(self):
        """Periodically ensure all blocker windows stay on top and update countdown timer."""
        if not self.is_showing or not self.root:
            return

        for win in self.windows:
            try:
                win.lift()
                win.attributes('-topmost', True)
            except Exception:
                pass

        # Update live clock and lock duration
        if self.countdown_label and self.lock_start_time > 0:
            elapsed_sec = int(time.time() - self.lock_start_time)
            hrs, rem = divmod(elapsed_sec, 3600)
            mins, secs = divmod(rem, 60)
            dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            self.countdown_label.config(
                text=f"⏰ Thời gian: {time.strftime('%H:%M:%S')}  |  ⏳ Thời lượng khóa: {dur_str}"
            )

        if self.root and self.is_showing:
            self.root.after(1000, self._keep_topmost_loop)


    def _verify_password(self):
        """Verify entered parent password and unlock if correct."""
        import time

        if not self.password_entry:
            return

        # ── Kiểm tra có đang bị lockout không ──
        now = time.time()
        if now < self._lockout_until:
            remaining = int(self._lockout_until - now)
            if self.error_label:
                self.error_label.config(
                    text=f"Đã nhập sai {self.MAX_ATTEMPTS} lần. Vui lòng chờ {remaining}s."
                )
            return

        entered_pwd = self.password_entry.get().strip()
        if not entered_pwd:
            if self.error_label:
                self.error_label.config(text="Vui lòng nhập mật khẩu!")
            return

        is_valid = False

        # 1. Custom callback nếu có
        if self.password_verifier:
            try:
                is_valid = self.password_verifier(entered_pwd)
            except Exception as e:
                logger.error(f"Password verifier callback error: {e}")

        # 2. Gọi endpoint xác thực chuyên dụng (không dùng /api/pair)
        if not is_valid and self.backend_url:
            try:
                import requests
                resp = requests.post(
                    f"{self.backend_url.rstrip('/')}/api/auth/verify-password",
                    json={"password": entered_pwd},
                    timeout=5
                )
                if resp.status_code == 200:
                    is_valid = True
            except Exception as e:
                logger.warning(f"Backend password verification error: {e}")

        # 3. Fallback: kiểm tra AGENT_PASSWORD trong .env
        if not is_valid:
            try:
                from utils.config import AGENT_PASSWORD
                if AGENT_PASSWORD and entered_pwd == AGENT_PASSWORD:
                    is_valid = True
            except Exception:
                pass

        # ── Xử lý kết quả ──
        if is_valid:
            logger.info("Parent password verified successfully. Unlocking screen.")
            self._failed_attempts = 0
            self._lockout_until = 0.0
            if self.password_entry:
                self.password_entry.delete(0, tk.END)
            if self.error_label:
                self.error_label.config(text="")
            self.hide()
        else:
            self._failed_attempts += 1
            remaining_attempts = self.MAX_ATTEMPTS - self._failed_attempts

            if self._failed_attempts >= self.MAX_ATTEMPTS:
                self._lockout_until = time.time() + self.LOCKOUT_SECONDS
                self._failed_attempts = 0  # reset để sau lockout có thể thử tiếp
                msg = f"Sai quá {self.MAX_ATTEMPTS} lần! Chờ {self.LOCKOUT_SECONDS}s."
            else:
                msg = f"Mật khẩu không đúng! Còn {remaining_attempts} lần thử."

            if self.error_label:
                self.error_label.config(text=msg)
            if self.password_entry:
                self.password_entry.delete(0, tk.END)
            logger.warning(f"Failed password attempt #{self._failed_attempts + 1}")


    def _shutdown_system(self):
        """Execute immediate Windows system shutdown."""
        try:
            logger.info("User requested shutdown from blocker screen.")
            os.system("shutdown /s /t 0")
        except Exception as e:
            logger.error(f"Failed to execute shutdown command: {e}")

    def _build_ui(self):
        """Build Tkinter root and multi-monitor windows."""
        monitors = get_display_monitors()

        if not monitors:
            # Fallback screen geometry
            self.root = tk.Tk()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            monitors = [{"left": 0, "top": 0, "width": sw, "height": sh}]
        else:
            self.root = tk.Tk()

        self.windows = []
        self.reason_labels = []

        for idx, mon in enumerate(monitors):
            win = self.root if idx == 0 else tk.Toplevel(self.root)
            self._setup_window_blocking(win)

            geo_str = f"{mon['width']}x{mon['height']}+{mon['left']}+{mon['top']}"
            win.geometry(geo_str)

            # Container frame
            container = tk.Frame(win, bg="#121212")
            container.place(relx=0.5, rely=0.5, anchor="center")

            if idx == 0:
                # Primary display gets lock UI form
                header_lbl = tk.Label(
                    container,
                    text="🔒 THIẾT BỊ ĐÃ BỊ KHÓA",
                    font=("Segoe UI", 26, "bold"),
                    fg="#ff4444",
                    bg="#121212"
                )
                header_lbl.pack(pady=(0, 15))

                # Lock Reason message
                reason_lbl = tk.Label(
                    container,
                    text=self.current_reason,
                    font=("Segoe UI", 14),
                    fg="#e0e0e0",
                    bg="#121212",
                    wraplength=600,
                    justify="center"
                )
                reason_lbl.pack(pady=(0, 15))
                self.reason_labels.append(reason_lbl)

                # Real-time Countdown / Lock Duration indicator
                self.countdown_label = tk.Label(
                    container,
                    text=f"⏰ Thời gian: {time.strftime('%H:%M:%S')}  |  ⏳ Trạng thái: Đang khóa an toàn",
                    font=("Segoe UI", 11, "bold"),
                    fg="#4ade80",
                    bg="#162e20",
                    padx=14,
                    pady=6,
                    bd=1,
                    relief="solid"
                )
                self.countdown_label.pack(pady=(0, 25))

                # Password Frame
                pwd_frame = tk.Frame(container, bg="#1e1e1e", bd=2, relief="groove", padx=25, pady=25)
                pwd_frame.pack(fill="x", pady=10)

                pwd_lbl = tk.Label(
                    pwd_frame,
                    text="Mật khẩu Phụ huynh để giải khóa:",
                    font=("Segoe UI", 12),
                    fg="#cccccc",
                    bg="#1e1e1e"
                )
                pwd_lbl.pack(anchor="w", pady=(0, 8))

                self.password_entry = tk.Entry(
                    pwd_frame,
                    show="•",
                    font=("Segoe UI", 14),
                    width=28,
                    bg="#2d2d2d",
                    fg="#ffffff",
                    insertbackground="#ffffff",
                    bd=1
                )
                self.password_entry.pack(pady=(0, 15))
                self.password_entry.bind("<Return>", lambda e: self._verify_password())

                # Error status message label
                self.error_label = tk.Label(
                    pwd_frame,
                    text="",
                    font=("Segoe UI", 10),
                    fg="#ff5555",
                    bg="#1e1e1e"
                )
                self.error_label.pack(pady=(0, 10))

                # Buttons frame
                btn_frame = tk.Frame(pwd_frame, bg="#1e1e1e")
                btn_frame.pack(fill="x")

                unlock_btn = tk.Button(
                    btn_frame,
                    text="Giải khóa",
                    command=self._verify_password,
                    font=("Segoe UI", 11, "bold"),
                    bg="#007acc",
                    fg="#ffffff",
                    activebackground="#005999",
                    activeforeground="#ffffff",
                    relief="flat",
                    padx=20,
                    pady=8,
                    cursor="hand2"
                )
                unlock_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

                shutdown_btn = tk.Button(
                    btn_frame,
                    text="Tắt máy",
                    command=self._shutdown_system,
                    font=("Segoe UI", 11, "bold"),
                    bg="#cc3333",
                    fg="#ffffff",
                    activebackground="#992222",
                    activeforeground="#ffffff",
                    relief="flat",
                    padx=20,
                    pady=8,
                    cursor="hand2"
                )
                shutdown_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))

            else:
                # Secondary monitors get simple dark overlay message
                sub_header = tk.Label(
                    container,
                    text="🔒 MÀN HÌNH ĐÃ BỊ KHÓA",
                    font=("Segoe UI", 22, "bold"),
                    fg="#ff4444",
                    bg="#121212"
                )
                sub_header.pack(pady=(0, 10))

                reason_lbl = tk.Label(
                    container,
                    text=self.current_reason,
                    font=("Segoe UI", 13),
                    fg="#aaaaaa",
                    bg="#121212",
                    wraplength=500,
                    justify="center"
                )
                reason_lbl.pack()
                self.reason_labels.append(reason_lbl)

            self.windows.append(win)

    def show(self, reason: str | None = None):
        """
        Display the full-screen blocker UI on all monitors asynchronously without blocking caller thread.
        
        :param reason: Optional lock reason string to display to the user.
        """
        if reason:
            self.current_reason = reason
        else:
            self.current_reason = DEFAULT_MESSAGE

        self.is_showing = True
        self.lock_start_time = time.time()

        def _run():
            if not self.root:
                try:
                    self._build_ui()
                    self._keep_topmost_loop()
                    
                    # Safe thread polling for reason updates
                    def _poll_updates():
                        if not self.root: return
                        for lbl in self.reason_labels:
                            try:
                                if lbl.cget("text") != self.current_reason:
                                    lbl.config(text=self.current_reason)
                            except Exception:
                                pass
                        if self.is_showing:
                            for win in self.windows:
                                try:
                                    if win.state() != "normal":
                                        win.deiconify()
                                        win.lift()
                                        win.attributes('-topmost', True)
                                except Exception:
                                    pass
                        self.root.after(1000, _poll_updates)
                    
                    self.root.after(1000, _poll_updates)
                    self.root.mainloop()
                except Exception as e:
                    logger.error(f"Error in BlockerUI mainloop: {e}")

        if not self.root:
            import threading
            threading.Thread(target=_run, daemon=True).start()

    def hide(self):
        """Hide all blocker overlay windows safely from any thread."""
        self.is_showing = False
        if self.root:
            def _destroy():
                for win in self.windows:
                    try:
                        win.withdraw()
                    except Exception:
                        pass
                try:
                    self.root.quit()
                    self.root.destroy()
                except Exception:
                    pass
                self.root = None
                self.windows = []
                self.reason_labels = []

            try:
                self.root.after(0, _destroy)
            except Exception:
                self.root = None
                self.windows = []
                self.reason_labels = []


if __name__ == "__main__":
    blocker = BlockerUI()
    blocker.show("Thiết bị đang bị khóa theo lịch hoặc lệnh từ Phụ huynh")
