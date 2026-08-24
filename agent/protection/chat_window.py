"""
chat_window.py — Tkinter Desktop Chat Popup UI for Child Machine.

Pops up a clean mini chat window when Phụ huynh sends a chat message from Web Manager,
allowing the child to reply in real time.
"""
import logging
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

logger = logging.getLogger(__name__)

class ChatWindow:
    def __init__(self, send_callback=None):
        self.send_callback = send_callback
        self.root = None
        self.chat_area = None
        self.entry = None
        self.is_showing = False
        self.messages = []

    def show(self, initial_message: str = ""):
        """Opens or brings to front the chat popup window."""
        if initial_message:
            self.messages.append({"sender": "admin", "text": initial_message})

        if self.is_showing and self.root:
            try:
                self._update_chat_area()
                self.root.deiconify()
                self.root.lift()
                self.root.attributes('-topmost', True)
                self._play_beep()
                return
            except Exception:
                pass

        # Create window in main thread
        threading.Thread(target=self._run_window, daemon=True).start()

    def add_message(self, sender: str, text: str):
        """Adds a new message to the chat and refreshes UI."""
        self.messages.append({"sender": sender, "text": text})
        if self.is_showing and self.root:
            try:
                self.root.after(0, self._update_chat_area)
                if sender == "admin":
                    self._play_beep()
            except Exception:
                pass
        else:
            self.show()

    def _play_beep(self):
        if sys.platform == "win32":
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _run_window(self):
        try:
            self.is_showing = True
            self.root = tk.Tk()
            self.root.title("Trò Chuyện Với Người Quản Lý (Admin)")
            self.root.geometry("380x480")
            self.root.attributes('-topmost', True)
            self.root.configure(bg="#101614")

            # Style
            style = ttk.Style()
            style.theme_use("clam")

            # Header
            header_frame = tk.Frame(self.root, bg="#064E3B", height=45)
            header_frame.pack(fill="x", side="top")
            
            lbl_title = tk.Label(
                header_frame,
                text="💬 Tin Nhắn Từ Người Quản Lý",
                fg="#F8E7C9",
                bg="#064E3B",
                font=("Segoe UI", 11, "bold")
            )
            lbl_title.pack(side="left", padx=12, pady=10)

            # Chat Display Area
            self.chat_area = scrolledtext.ScrolledText(
                self.root,
                wrap=tk.WORD,
                bg="#18221f",
                fg="#f4f4f5",
                font=("Segoe UI", 10),
                state="disabled",
                bd=0,
                padx=8,
                pady=8
            )
            self.chat_area.pack(fill="both", expand=True, padx=10, pady=10)

            # Text Tags for Bubbles
            self.chat_area.tag_config("admin_tag", foreground="#34d399", font=("Segoe UI", 10, "bold"))
            self.chat_area.tag_config("child_tag", foreground="#60a5fa", font=("Segoe UI", 10, "bold"))
            self.chat_area.tag_config("msg_tag", foreground="#f4f4f5", font=("Segoe UI", 10))

            # Input Frame
            input_frame = tk.Frame(self.root, bg="#101614")
            input_frame.pack(fill="x", side="bottom", padx=10, pady=10)

            self.entry = tk.Entry(
                input_frame,
                bg="#18221f",
                fg="#ffffff",
                insertbackground="#ffffff",
                font=("Segoe UI", 10),
                bd=1,
                relief="solid"
            )
            self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
            self.entry.bind("<Return>", lambda e: self._send_reply())

            btn_send = tk.Button(
                input_frame,
                text="Gửi",
                bg="#064E3B",
                fg="#F8E7C9",
                font=("Segoe UI", 10, "bold"),
                relief="flat",
                command=self._send_reply,
                padx=12
            )
            btn_send.pack(side="right")

            self._update_chat_area()

            # Protocol close handler
            def on_close():
                self.is_showing = False
                self.root.destroy()

            self.root.protocol("WM_DELETE_WINDOW", on_close)
            self.root.mainloop()
        except Exception as e:
            logger.error(f"[ChatWindow] GUI error: {e}")
        finally:
            self.is_showing = False

    def _update_chat_area(self):
        if not self.chat_area:
            return
        self.chat_area.config(state="normal")
        self.chat_area.delete("1.0", tk.END)

        for m in self.messages:
            if m["sender"] == "admin":
                self.chat_area.insert(tk.END, "Người Quản Lý: ", "admin_tag")
            else:
                self.chat_area.insert(tk.END, "Bạn: ", "child_tag")
            self.chat_area.insert(tk.END, f"{m['text']}\n\n", "msg_tag")

        self.chat_area.see(tk.END)
        self.chat_area.config(state="disabled")

    def _send_reply(self):
        if not self.entry:
            return
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)

        # Add to local list
        self.messages.append({"sender": "child", "text": text})
        self._update_chat_area()

        # Execute callback to WS
        if self.send_callback:
            try:
                self.send_callback(text)
            except Exception as e:
                logger.error(f"Failed to send chat reply callback: {e}")
