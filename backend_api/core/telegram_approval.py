import requests
import logging
import uuid
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

import models
from database import SessionLocal
from core import telegram_bot  # điều khiển thiết bị qua text commands

logger = logging.getLogger(__name__)

TG_API_URL = "https://api.telegram.org/bot{}"

def _tg_send(method: str, payload: dict, bot_token: str):
    url = f"{TG_API_URL.format(bot_token)}/{method}"
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Telegram API {method} error: {e}")
        return None

def send_registration_message(registration: models.PendingRegistration, bot_token: str, chat_id: str):
    text = (
        f"🔒 <b>Yêu cầu kết nối thiết bị mới</b>\n\n"
        f"💻 Tên thiết bị: <b>{registration.device_name}</b>\n"
        f"🔑 ID phần cứng: <code>{registration.hardware_uuid}</code>\n"
        f"⏳ Hết hạn: {registration.expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        f"Bạn có muốn cho phép thiết bị này kết nối không?"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Đồng ý", "callback_data": f"approve:{registration.id}"},
                {"text": "❌ Từ chối", "callback_data": f"reject:{registration.id}"}
            ],
            [{"text": "🔄 Gửi lại", "callback_data": f"resend:{registration.id}"}]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    
    result = _tg_send("sendMessage", payload, bot_token)
    if result and result.get("ok"):
        return result["result"]["message_id"]
    return None

def edit_registration_message(chat_id: str, message_id: int, new_text: str, bot_token: str):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "HTML"
    }
    _tg_send("editMessageText", payload, bot_token)

def answer_callback(callback_query_id: str, text: str, bot_token: str):
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": False
    }
    _tg_send("answerCallbackQuery", payload, bot_token)


def create_device_for_registration(registration: models.PendingRegistration, db: Session):
    # Device.parent_id FK references parents.id — MUST use a Parent.id (NOT a User.id),
    # otherwise PostgreSQL raises a foreign-key violation when creating the device.
    from core.config import SYSTEM_ADMIN_EMAIL
    parent = db.query(models.Parent).filter(models.Parent.email == SYSTEM_ADMIN_EMAIL).first()
    if not parent:
        parent = db.query(models.Parent).first()
    if not parent:
        logger.error("No parent found to attach the device to.")
        return False
    p_id = parent.id
        
    device = db.query(models.Device).filter(
        models.Device.device_name == registration.device_name,
        models.Device.parent_id == p_id
    ).first()
    
    if not device:
        new_token = str(uuid.uuid4())
        device = models.Device(
            parent_id=p_id,
            device_name=registration.device_name,
            secret_token=new_token
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
    registration.device_id = device.id
    registration.secret_token = device.secret_token
    registration.status = "approved"
    db.commit()
    return True


def process_callback_query(update: dict, db: Session, bot_token: str, chat_id: str):
    cb = update.get("callback_query")
    if not cb:
        return
        
    cb_id = cb["id"]
    data = cb.get("data", "")
    msg = cb.get("message")

    if not data:
        answer_callback(cb_id, "Dữ liệu không hợp lệ", bot_token)
        return

    # ── Điều khiển thiết bị: dev:lock/unlock/shot/select:<id> ────────────────
    if data.startswith("dev:"):
        telegram_bot.answer_cb(bot_token, cb_id, "Đang xử lý...")
        telegram_bot.handle_dev_callback(data, db, bot_token, chat_id)
        return

    # ── Phản hồi cảnh báo ban đêm: night:allow/deny:<device_id> ─────────────
    if data.startswith("night:"):
        telegram_bot.answer_cb(bot_token, cb_id, "Đang xử lý...")
        telegram_bot.handle_night_callback(data, db, bot_token, chat_id)
        return

    # ── Phê duyệt / từ chối đăng ký thiết bị mới ────────────────────────────
    if ":" not in data:
        answer_callback(cb_id, "Dữ liệu không hợp lệ", bot_token)
        return
        
    action, reg_id_str = data.split(":", 1)
    
    try:
        reg_uuid = uuid.UUID(reg_id_str)
    except ValueError:
        answer_callback(cb_id, "ID không hợp lệ", bot_token)
        return
        
    reg = db.query(models.PendingRegistration).filter(models.PendingRegistration.id == reg_uuid).first()
    if not reg:
        answer_callback(cb_id, "Không tìm thấy yêu cầu này", bot_token)
        return
        
    if reg.status != "pending":
        answer_callback(cb_id, f"Yêu cầu này đã được xử lý ({reg.status})", bot_token)
        if msg:
            edit_registration_message(chat_id, msg["message_id"], f"Yêu cầu kết nối cho <b>{reg.device_name}</b> đã được xử lý: {reg.status}", bot_token)
        return
        
    if action == "approve":
        success = create_device_for_registration(reg, db)
        if success:
            answer_callback(cb_id, "Đã phê duyệt!", bot_token)
            if msg:
                edit_registration_message(chat_id, msg["message_id"], f"✅ Đã <b>phê duyệt</b> thiết bị <b>{reg.device_name}</b>.", bot_token)
        else:
            answer_callback(cb_id, "Lỗi khi tạo thiết bị", bot_token)
            
    elif action == "reject":
        reg.status = "rejected"
        db.commit()
        answer_callback(cb_id, "Đã từ chối", bot_token)
        if msg:
            edit_registration_message(chat_id, msg["message_id"], f"❌ Đã <b>từ chối</b> thiết bị <b>{reg.device_name}</b>.", bot_token)

    elif action == "resend":
        # Re-send the registration request (parent can request a fresh copy).
        msg_id = send_registration_message(reg, bot_token, chat_id)
        if msg_id:
            reg.tg_message_id = msg_id
            db.commit()
        answer_callback(cb_id, "Đã gửi lại yêu cầu đăng ký", bot_token)


def get_updates_poller():
    """Long-poll Telegram getUpdates và xử lý:
    - message (text commands: /lock /unlock /shot /devices /usage /select /menu /help)
    - callback_query (nút bấm inline: dev:lock, dev:unlock, dev:shot, approve/reject đăng ký)
    """
    offset = 0
    while True:
        try:
            db = SessionLocal()
            try:
                tg_setting = db.query(models.TelegramSetting).first()
                if not tg_setting or not tg_setting.bot_token or not tg_setting.chat_id:
                    time.sleep(10)
                    continue

                bot_token = tg_setting.bot_token
                chat_id = tg_setting.chat_id

                url = f"{TG_API_URL.format(bot_token)}/getUpdates"
                payload = {
                    "offset": offset,
                    "timeout": 30,
                    # BUG FIX: phải subscribe cả "message" mới nhận được text commands
                    # Trước chỉ có ["callback_query"] → /lock /unlock /shot bị bỏ qua hoàn toàn
                    "allowed_updates": ["message", "callback_query"],
                }

                try:
                    resp = requests.post(url, json=payload, timeout=40)
                    resp.raise_for_status()
                    data = resp.json()

                    if data.get("ok") and data.get("result"):
                        for update in data["result"]:
                            update_id = update["update_id"]
                            offset = update_id + 1

                            # Lấy chat_id từ update (tin nhắn hoặc callback)
                            update_chat_id = chat_id  # fallback
                            if "message" in update and update["message"].get("chat"):
                                update_chat_id = str(update["message"]["chat"]["id"])
                            elif "callback_query" in update:
                                cb_msg = update["callback_query"].get("message")
                                if cb_msg and cb_msg.get("chat"):
                                    update_chat_id = str(cb_msg["chat"]["id"])

                            if "message" in update:
                                # Text commands: /lock /unlock /shot /devices /usage /select /menu /help
                                telegram_bot.handle_message(update, bot_token, update_chat_id, db)
                            elif "callback_query" in update:
                                # Inline buttons: dev:lock/unlock/shot/select, approve/reject/resend, night:allow/deny
                                process_callback_query(update, db, bot_token, update_chat_id)

                except requests.exceptions.RequestException as req_err:
                    logger.warning(f"[tg-poller] getUpdates network error: {req_err}")
                    time.sleep(5)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[tg-poller] exception: {e}")
            time.sleep(5)
