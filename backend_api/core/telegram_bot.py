"""Telegram bot handlers for parent device control (no web needed).

Handles text commands (/devices, /lock, /unlock, /shot) and inline callback
buttons (dev:lock:<id>, dev:shot:<id>). Commands are queued as PendingCommand for
the agent to poll (cloud-first, no home WS). Replies via sendMessage/sendPhoto.
"""
import json
import logging
import time
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>🛡️ Parental Control Bot</b>\n"
    "Điều khiển thiết bị ngay trên Telegram:\n\n"
    "• /devices — danh sách thiết bị + nút điều khiển\n"
    "• /lock [tên] — khóa thiết bị\n"
    "• /unlock [tên] — mở khóa thiết bị\n"
    "• /shot [tên] — chụp & gửi ảnh màn hình\n"
    "• /help — menu này"
)


def _tg(method: str, token: str, **kw):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        return requests.post(url, json=kw, timeout=12).json()
    except Exception as e:
        logger.error(f"tg {method} err: {e}")
        return None


def send_message(token, chat_id, text, reply_markup=None):
    return _tg("sendMessage", token, chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=reply_markup)


def send_photo(token, chat_id, url, caption=""):
    return _tg("sendPhoto", token, chat_id=chat_id, photo=url, caption=caption, parse_mode="HTML")


def answer_cb(token, cb_id, text):
    return _tg("answerCallbackQuery", token, callback_query_id=cb_id, text=text, show_alert=False)


def _is_online(dev) -> bool:
    if not dev.last_seen_at:
        return False
    last = dev.last_seen_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds() <= 45


def _resolve_device(db: Session, arg: str):
    devs = db.query(models.Device).all()
    if not devs:
        return None
    if not arg:
        return devs[0] if len(devs) == 1 else None
    for d in devs:
        if d.device_name == arg or str(d.id) == arg:
            return d
    # case-insensitive
    low = arg.lower()
    for d in devs:
        if d.device_name.lower() == low:
            return d
    return None


def _queue_command(db: Session, device, command: str, payload=None):
    db.add(models.PendingCommand(
        device_id=device.id,
        command=command,
        payload=json.dumps(payload or {}),
    ))
    db.commit()


# --------------------------------------------------------------------------- commands
def cmd_devices(token, chat_id, db):
    devs = db.query(models.Device).all()
    if not devs:
        send_message(token, chat_id, "Không có thiết bị nào được đăng ký.")
        return
    lines = ["<b>📱 Danh sách thiết bị</b>"]
    kb = {"inline_keyboard": []}
    for d in devs:
        on = "🟢" if _is_online(d) else "🔴"
        lock = "🔒" if d.is_locked else "🔓"
        lines.append(f"{on} {lock} <b>{d.device_name}</b> (<code>{str(d.id)[:8]}</code>)")
        kb["inline_keyboard"].append([
            {"text": "🔒 Khóa", "callback_data": f"dev:lock:{d.id}"},
            {"text": "🔓 Mở", "callback_data": f"dev:unlock:{d.id}"},
            {"text": "📸 Ảnh", "callback_data": f"dev:shot:{d.id}"},
        ])
    send_message(token, chat_id, "\n".join(lines), reply_markup=kb)


def cmd_lock(token, chat_id, db, arg):
    dev = _resolve_device(db, arg)
    if not dev:
        send_message(token, chat_id, "Không tìm thấy thiết bị. Dùng /devices để xem.")
        return
    _queue_command(db, dev, "lock_screen", {"reason": "Khóa từ Telegram"})
    send_message(token, chat_id, f"🔒 Đã gửi lệnh <b>khóa</b> {dev.device_name}.")


def cmd_unlock(token, chat_id, db, arg):
    dev = _resolve_device(db, arg)
    if not dev:
        send_message(token, chat_id, "Không tìm thấy thiết bị.")
        return
    _queue_command(db, dev, "unlock_screen", {})
    send_message(token, chat_id, f"🔓 Đã gửi lệnh <b>mở khóa</b> {dev.device_name}.")


def cmd_shot(token, chat_id, db, arg):
    dev = _resolve_device(db, arg)
    if not dev:
        send_message(token, chat_id, "Không tìm thấy thiết bị.")
        return
    # latest screenshot timestamp before this request
    before = db.query(models.Screenshot).filter(
        models.Screenshot.device_id == dev.id
    ).order_by(models.Screenshot.timestamp.desc()).first()
    before_ts = before.timestamp if before else datetime(1970, 1, 1, tzinfo=timezone.utc)

    _queue_command(db, dev, "take_screenshot", {})
    send_message(token, chat_id, f"📸 Đã yêu cầu chụp màn hình <b>{dev.device_name}</b>. Đang chờ ảnh...")

    # Poll for a NEW screenshot (timeout ~20s).
    for _ in range(20):
        time.sleep(1)
        shot = db.query(models.Screenshot).filter(
            models.Screenshot.device_id == dev.id
        ).order_by(models.Screenshot.timestamp.desc()).first()
        if shot and shot.timestamp and shot.timestamp > before_ts:
            send_photo(token, chat_id, shot.image_url, caption=f"📸 {dev.device_name} — {shot.timestamp.strftime('%d/%m %H:%M:%S')}")
            return
    send_message(token, chat_id, f"⏳ Chưa nhận được ảnh từ {dev.device_name} (thiết bị có thể offline).")


def handle_message(update, token, chat_id, db):
    msg = update.get("message") or {}
    text = (msg.get("text") or "").strip()
    if not text:
        return
    low = text.lower()
    if low == "/start" or low == "/help":
        send_message(token, chat_id, HELP_TEXT)
    elif low.startswith("/devices"):
        cmd_devices(token, chat_id, db)
    elif low.startswith("/lock"):
        cmd_lock(token, chat_id, db, _arg(text))
    elif low.startswith("/unlock"):
        cmd_unlock(token, chat_id, db, _arg(text))
    elif low.startswith("/shot"):
        cmd_shot(token, chat_id, db, _arg(text))
    else:
        send_message(token, chat_id, "Dùng /help để xem các lệnh điều khiển.")


def _arg(text: str) -> str:
    parts = text.split(" ", 1)
    return parts[1].strip() if len(parts) > 1 else ""


# --------------------------------------------------------------------------- callbacks
def handle_dev_callback(data, db, token, chat_id):
    """data = dev:lock:<id> | dev:unlock:<id> | dev:shot:<id>"""
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "dev":
        return False
    action, dev_id = parts[1], parts[2]
    dev = db.query(models.Device).filter(models.Device.id == dev_id).first()
    if not dev:
        return False
    if action == "lock":
        _queue_command(db, dev, "lock_screen", {"reason": "Khóa từ Telegram"})
        send_message(token, chat_id, f"🔒 Đã gửi lệnh <b>khóa</b> {dev.device_name}.")
    elif action == "unlock":
        _queue_command(db, dev, "unlock_screen", {})
        send_message(token, chat_id, f"🔓 Đã gửi lệnh <b>mở khóa</b> {dev.device_name}.")
    elif action == "shot":
        cmd_shot(token, chat_id, db, str(dev.id))
    return True
