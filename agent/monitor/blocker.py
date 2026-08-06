"""
blocker.py v2 — Man hinh khoa voi bao ve nang cao.
Chong bypass bang nhieu lop bao ve:
1. Tkinter Fullscreen tren tat ca monitors
2. Disable Task Manager qua Registry
3. Periodic force-focus moi 2 giay
4. Suppress hotkey bang event binding
5. Kiem tra is_paused tu Supabase moi 10 giay
"""
import os
import atexit
import ctypes
import winreg
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

import win32api

from utils.config import AGENT_PASSWORD, DEVICE_NAME


class ScreenBlocker:
    def __init__(self, supabase=None):
        self.root = tk.Tk()
        self.root.title("May da bi khoa")
        self.password_correct = False
        self.remote_unlocked = False
        self.supabase = supabase
        self._protections_cleaned = False

        # --- Cau hinh cua so chinh ---
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0f172a")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_attempt)

        # --- Suppress hotkey ---
        self.root.bind("<Alt-F4>", lambda e: "break")
        self.root.bind("<Escape>", lambda e: "break")
        self.root.bind("<Control-Escape>", lambda e: "break")  # Win key
        self.root.bind("<Alt-Tab>", lambda e: "break")

        # --- Multi-monitor block ---
        self.extra_windows = []
        self.setup_multimonitor_block()

        # --- Enable protections ---
        self._enable_protections()

        # Safety net: luon cleanup khi thoat
        atexit.register(self.cleanup_protections)

        # --- Build UI ---
        self.build_ui()

        # --- Kiem tra is_paused tu xa moi 10 giay ---
        if self.supabase:
            self.check_remote_pause()

        # --- Periodic force-focus moi 2 giay ---
        self._force_focus_loop()

    def _enable_protections(self):
        """Bat cac lop bao ve chong bypass."""
        # 1. Disable Task Manager qua Registry
        try:
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            print("[BLOCKER] Disabled Task Manager via Registry")
        except Exception as e:
            print(f"[BLOCKER] Cannot disable TaskMgr: {e}")

        # 2. Disable hotkeys (SPI_SETSCREENSAVERRUNNING trick)
        try:
            SPI_SETSCREENSAVERRUNNING = 0x0061
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETSCREENSAVERRUNNING, 1, None, 0
            )
            print("[BLOCKER] Disabled system hotkeys")
        except Exception as e:
            print(f"[BLOCKER] Cannot disable hotkeys: {e}")

    def cleanup_protections(self):
        """CRITICAL: Phuc hoi moi thu ve binh thuong. Phai luon duoc goi."""
        if self._protections_cleaned:
            return
        self._protections_cleaned = True

        # 1. Re-enable Task Manager
        try:
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            print("[BLOCKER] Re-enabled Task Manager")
        except Exception as e:
            print(f"[BLOCKER] Cannot re-enable TaskMgr: {e}")

        # 2. Re-enable hotkeys
        try:
            SPI_SETSCREENSAVERRUNNING = 0x0061
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETSCREENSAVERRUNNING, 0, None, 0
            )
            print("[BLOCKER] Re-enabled system hotkeys")
        except Exception as e:
            print(f"[BLOCKER] Cannot re-enable hotkeys: {e}")

    def _force_focus_loop(self):
        """Moi 2 giay, ep cua so blocker len tren cung va lay focus."""
        try:
            self.root.lift()
            self.root.focus_force()
            self.root.attributes("-topmost", True)
            # Cung lift cac cua so phu (multi-monitor)
            for w in self.extra_windows:
                try:
                    w.lift()
                    w.attributes("-topmost", True)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self.root.after(2000, self._force_focus_loop)
        except Exception:
            pass

    def setup_multimonitor_block(self):
        """Tao cac cua so phu tren tat ca man hinh phu ngoai man hinh chinh."""
        try:
            monitors = win32api.EnumDisplayMonitors()
            for i in range(1, len(monitors)):
                hMonitor, hdcMonitor, pyRect = monitors[i]
                left, top, right, bottom = pyRect
                width = right - left
                height = bottom - top

                win = tk.Toplevel(self.root)
                win.title(f"May da bi khoa (Man hinh {i+1})")
                win.geometry(f"{width}x{height}+{left}+{top}")
                win.overrideredirect(True)
                win.attributes("-topmost", True)
                win.configure(bg="#0f172a")
                win.protocol("WM_DELETE_WINDOW", lambda: "break")

                win.bind("<Alt-F4>", lambda e: "break")
                win.bind("<Escape>", lambda e: "break")
                win.bind("<Control-Escape>", lambda e: "break")
                win.bind("<Alt-Tab>", lambda e: "break")

                self.build_ui_on_window(win, is_primary=False)
                self.extra_windows.append(win)
            print(f"[BLOCKER] Multi-monitor block enabled for {len(monitors)} monitor(s)")
        except Exception as e:
            print(f"[BLOCKER] Multi-monitor error: {e}")

    def build_ui(self):
        """Xay dung giao dien man hinh khoa tren man hinh chinh."""
        self.build_ui_on_window(self.root, is_primary=True)

    def build_ui_on_window(self, container, is_primary=True):
        """Xay dung giao dien man hinh khoa tren mot cua so (primary hoac secondary)."""
        frame = tk.Frame(container, bg="#0f172a")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame,
            text="⛔ MÁY ĐÃ BỊ KHÓA",
            font=("Segoe UI", 28, "bold"),
            fg="#ef4444",
            bg="#0f172a"
        ).pack(pady=(0, 10))

        tk.Label(
            frame,
            text="Ngoài giờ sử dụng được phép\nLiên hệ anh/chị để được mở khóa",
            font=("Segoe UI", 14),
            fg="#94a3b8",
            bg="#0f172a",
            justify="center"
        ).pack(pady=(0, 20))

        tk.Label(
            frame,
            text=f"Thiết bị: {DEVICE_NAME}\nThời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}",
            font=("Segoe UI", 11),
            fg="#64748b",
            bg="#0f172a",
            justify="center"
        ).pack(pady=(0, 25))

        if is_primary:
            tk.Label(
                frame,
                text="Nhập mật khẩu quản lý để mở khóa:",
                font=("Segoe UI", 12),
                fg="#e2e8f0",
                bg="#0f172a"
            ).pack()

            self.password_entry = tk.Entry(
                frame,
                font=("Segoe UI", 14),
                show="*",
                width=22,
                justify="center"
            )
            self.password_entry.pack(pady=10)
            self.password_entry.focus()
            self.password_entry.bind("<Return>", self.check_password)

            btn_frame = tk.Frame(frame, bg="#0f172a")
            btn_frame.pack(pady=15)

            tk.Button(
                btn_frame,
                text="Mở khóa",
                font=("Segoe UI", 12, "bold"),
                bg="#3b82f6",
                fg="white",
                activebackground="#2563eb",
                relief="flat",
                padx=20,
                pady=8,
                command=self.check_password
            ).pack(side=tk.LEFT, padx=8)

            tk.Button(
                btn_frame,
                text="🔴 Tắt máy (Shutdown)",
                font=("Segoe UI", 12, "bold"),
                bg="#ef4444",
                fg="white",
                activebackground="#dc2626",
                relief="flat",
                padx=20,
                pady=8,
                command=self.shutdown_pc
            ).pack(side=tk.LEFT, padx=8)

            self.error_label = tk.Label(
                frame,
                text="",
                font=("Segoe UI", 11),
                fg="#ef4444",
                bg="#0f172a"
            )
            self.error_label.pack()

            self.remote_status = tk.Label(
                frame,
                text="🔄 Đang kiểm tra lệnh mở khóa từ xa...",
                font=("Segoe UI", 9),
                fg="#475569",
                bg="#0f172a"
            )
            self.remote_status.pack(pady=(15, 0))
        else:
            # Tren man hinh phu: Hien thi thong bao khoa va nut Tat May
            tk.Button(
                frame,
                text="🔴 Tắt máy (Shutdown)",
                font=("Segoe UI", 13, "bold"),
                bg="#ef4444",
                fg="white",
                activebackground="#dc2626",
                relief="flat",
                padx=25,
                pady=10,
                command=self.shutdown_pc
            ).pack(pady=20)

    def check_password(self, event=None):
        """Kiem tra mat khau nhap vao."""
        entered = self.password_entry.get().strip()
        if entered == AGENT_PASSWORD:
            self.password_correct = True
            self.cleanup_protections()
            self.root.destroy()
        else:
            self.error_label.config(text="Sai mat khau!")
            self.password_entry.delete(0, tk.END)

    def shutdown_pc(self):
        """Tat may tinh sau khi xac nhan."""
        confirm = messagebox.askyesno(
            "Xac nhan tat may",
            "Ban co chac chan muon tat may ngay bay gio khong?"
        )
        if confirm:
            self.cleanup_protections()
            os.system("shutdown /s /t 0")

    def check_remote_pause(self):
        """Kiem tra is_paused tu Supabase moi 5 giay. Neu paused -> tu mo khoa. Gui heartbeat duy tri ket noi."""
        paused = False
        query_success = False

        if self.supabase:
            try:
                res = self.supabase.table("app_config").select("is_paused").eq("device_name", DEVICE_NAME).execute()
                if res and hasattr(res, "data") and res.data and len(res.data) > 0:
                    paused = bool(res.data[0].get("is_paused", False))
                    query_success = True
            except Exception as e:
                if hasattr(self, "remote_status"):
                    self.remote_status.config(
                        text=f"Dang thu ket noi lai... ({datetime.now().strftime('%H:%M:%S')})"
                    )

        # Fallback local DB cached rules when cloud query fails on Lock Screen
        if not query_success:
            try:
                from storage.local_db import LocalDB
                db = LocalDB()
                cached_config = db.get_cached_rules("app_config")
                if isinstance(cached_config, dict):
                    paused = bool(cached_config.get("is_paused", False))
            except Exception:
                pass

        if paused:
            self.remote_unlocked = True
            if hasattr(self, "remote_status"):
                self.remote_status.config(
                    text="Admin da mo khoa tu xa!",
                    fg="#22c55e"
                )
            self.cleanup_protections()
            self.root.after(300, self.root.destroy)
            return
        else:
            if hasattr(self, "remote_status") and query_success:
                self.remote_status.config(
                    text=f"Dang giu ket noi. Kiem tra: {datetime.now().strftime('%H:%M:%S')}"
                )

        try:
            self.root.after(5000, self.check_remote_pause)
        except Exception:
            pass

    def on_close_attempt(self):
        """Chan dong cua so."""
        messagebox.showwarning(
            "Canh bao",
            "Khong the tat cua so nay.\nHay nhap mat khau de mo khoa."
        )

    def run(self) -> bool:
        """Chay blocker. Tra ve True neu da mo khoa thanh cong."""
        try:
            self.root.mainloop()
        finally:
            self.cleanup_protections()
        return self.password_correct or self.remote_unlocked


def start_blocker(supabase=None) -> bool:
    """Module-level function khoi dong blocker."""
    blocker = ScreenBlocker(supabase=supabase)
    return blocker.run()