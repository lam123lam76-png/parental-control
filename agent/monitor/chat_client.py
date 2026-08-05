import tkinter as tk
from tkinter import scrolledtext
import threading
from utils.config import DEVICE_NAME

def check_unread_messages(supabase):
    """
    Kiểm tra tin nhắn chưa đọc từ Admin. Nếu có tin mới, bật cửa sổ Chat trong thread riêng.
    """
    try:
        res = supabase.table("chat_messages")\
            .select("*")\
            .eq("device_name", DEVICE_NAME)\
            .eq("sender", "admin")\
            .eq("is_read", False)\
            .execute()
        
        unread = res.data or []
        if unread:
            # Đánh dấu đã đọc
            for msg in unread:
                supabase.table("chat_messages")\
                    .update({"is_read": True})\
                    .eq("id", msg["id"])\
                    .execute()
            
            # Hiển thị cửa sổ Chat trong thread riêng để KHÔNG chặn vòng lặp chính
            chat_thread = threading.Thread(target=show_chat_window, args=(supabase,), daemon=True)
            chat_thread.start()
    except Exception as e:
        print(f"Lỗi kiểm tra chat: {e}")

def show_chat_window(supabase):
    root = tk.Tk()
    root.title("Tro Chuyen Cung Anh/Chi Quan Ly")
    root.geometry("450x500")
    root.attributes("-topmost", True)
    root.configure(bg="#0f172a")

    # Header
    header_frame = tk.Frame(root, bg="#1e293b", pady=10)
    header_frame.pack(fill="x")
    title_label = tk.Label(header_frame, text="Cua So Tro Chuyen Direct", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#1e293b")
    title_label.pack()

    # Chat History Frame
    msg_box = scrolledtext.ScrolledText(root, width=48, height=16, font=("Segoe UI", 10), bg="#020617", fg="#f8fafc", wrap=tk.WORD)
    msg_box.pack(pady=10, padx=10, fill="both", expand=True)

    # Load toàn bộ lịch sử tin nhắn
    try:
        res = supabase.table("chat_messages")\
            .select("*")\
            .eq("device_name", DEVICE_NAME)\
            .order("created_at", ascending=True)\
            .limit(30)\
            .execute()
        msgs = res.data or []
        for m in msgs:
            sender_label = "Anh/Chi Quan Ly" if m["sender"] == "admin" else "Em"
            msg_box.insert(tk.END, f"[{sender_label}]: {m['message']}\n")
    except Exception as e:
        msg_box.insert(tk.END, "(Khong the tai lich su chat)\n")

    msg_box.config(state=tk.DISABLED)
    msg_box.see(tk.END)

    # Input Frame
    input_frame = tk.Frame(root, bg="#0f172a", pady=10)
    input_frame.pack(fill="x", padx=10)

    entry = tk.Entry(input_frame, font=("Segoe UI", 11), bg="#1e293b", fg="#ffffff", insertbackground="white")
    entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
    entry.focus()

    def send_reply(event=None):
        text = entry.get().strip()
        if text:
            try:
                supabase.table("chat_messages").insert({
                    "device_name": DEVICE_NAME,
                    "sender": "student",
                    "message": text
                }).execute()
                msg_box.config(state=tk.NORMAL)
                msg_box.insert(tk.END, f"[Em]: {text}\n")
                msg_box.config(state=tk.DISABLED)
                msg_box.see(tk.END)
                entry.delete(0, tk.END)
            except Exception as e:
                print(f"Loi gui tin nhan: {e}")

    entry.bind("<Return>", send_reply)

    btn = tk.Button(input_frame, text="Gui", font=("Segoe UI", 10, "bold"), bg="#3b82f6", fg="white", activebackground="#2563eb", padx=15, command=send_reply)
    btn.pack(side="right")

    root.mainloop()
