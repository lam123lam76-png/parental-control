"""Telegram bot handlers for parent device control (no web needed).

Handles text commands (/devices, /lock, /unlock, /shot) and inline callback
buttons (dev:lock:<id>, dev:shot:<id>). Commands are queued as PendingCommand for
the agent to poll (cloud-first, no home WS). Replies via sendMessage/sendPhoto.
"""
import json
import logging
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy.orm import Session

import models

VIETNAM_TZ = timezone(timedelta(hours=7))
BROWSER_EXES = {"chrome.exe", "msedge.exe", "coccoc.exe", "brave.exe", "firefox.exe", "opera.exe", "iexplore.exe"}
# Each active-window process log == one scan tick (matches agent PROCESS_SCAN_INTERVAL=15s).
SCAN_INTERVAL_SEC = 15

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>🛡️ Parental Control Bot</b>\n"
    "Điều khiển thiết bị ngay trên Telegram:\n\n"
    "• /lock [tên] — khóa thiết bị\n"
    "• /unlock [tên] — mở khóa thiết bị\n"
    "• /shot [tên] — chụp & gửi ảnh màn hình\n"
    "• /usage [tên] — báo cáo sử dụng trong ngày\n"
    "• /select [tên] — chọn thiết bị đích để điều khiển\n"
    "• /menu — bật menu nút bấm\n"
    "• /help — menu này"
)


def _menu_keyboard():
    """Reply keyboard with tap-to-action buttons (no typing needed)."""
    return {
        "keyboard": [
            [{"text": "📸 Chụp ảnh màn hình"}],
            [{"text": "🔒 Khóa máy"}, {"text": "🔓 Mở khóa"}],
            [{"text": "📊 Báo cáo sử dụng"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def _cmd_menu(token, chat_id):
    send_message(token, chat_id, "Menu điều khiển nhanh:", reply_markup=_menu_keyboard())


def _tg(method: str, token: str, **kw):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        resp = requests.post(url, json=kw, timeout=12)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if not data.get("ok", True):
            logger.error(f"tg {method} FAILED: {data}")
        return data
    except Exception as e:
        logger.error(f"tg {method} err: {e}")
        return None


def send_message(token, chat_id, text, reply_markup=None):
    kw = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        kw["reply_markup"] = reply_markup
    return _tg("sendMessage", token, **kw)


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


def _get_selected_device_id(db: Session, chat_id: str) -> str | None:
    """Return the device id this chat has selected (persisted in system_settings)."""
    try:
        s = db.query(models.SystemSetting).filter(
            models.SystemSetting.key == f"tg_selected_device:{chat_id}"
        ).first()
        if s and s.value:
            return s.value
    except Exception:
        pass
    return None


def _set_selected_device(db: Session, chat_id: str, device_id) -> None:
    key = f"tg_selected_device:{chat_id}"
    try:
        s = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
        if s:
            s.value = str(device_id)
        else:
            db.add(models.SystemSetting(key=key, value=str(device_id)))
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def _resolve_device(db: Session, arg: str, chat_id: str | None = None):
    """Resolve the target device for a command.

    Priority:
      1. explicit arg (device name or id)
      2. device selected for this chat (/select)
      3. the single device if only one exists
    Returns None if ambiguous.
    """
    devs = db.query(models.Device).all()
    if not devs:
        return None

    # 1. Explicit arg
    if arg:
        for d in devs:
            if d.device_name == arg or str(d.id) == arg:
                return d
        low = arg.lower()
        for d in devs:
            if d.device_name.lower() == low:
                return d
        return None

    # 2. Per-chat selected device
    if chat_id:
        sel_id = _get_selected_device_id(db, chat_id)
        if sel_id:
            for d in devs:
                if str(d.id) == sel_id:
                    return d

    # 3. Single device fallback
    return devs[0] if len(devs) == 1 else None


def _no_device_message(db: Session, chat_id: str) -> str:
    """Friendly message when a command can't resolve a target device."""
    devs = db.query(models.Device).all()
    if not devs:
        return "Không có thiết bị nào được đăng ký."
    if len(devs) > 1:
        sel_id = _get_selected_device_id(db, chat_id)
        names = ", ".join(f"<b>{d.device_name}</b>" for d in devs)
        if not sel_id:
            return (f"Có {len(devs)} thiết bị: {names}.\n"
                    "Hãy chọn thiết bị đích bằng lệnh <b>/select &lt;tên&gt;</b> hoặc bấm ⭐ Chọn trong /devices, "
                    "hoặc kèm tên thiết bị vào lệnh (vd: /lock DESKTOP-IDUQ3QB).")
        return (f"Thiết bị đang chọn không còn tồn tại. Hãy chọn lại bằng /select.\n"
                f"Danh sách: {names}.")
    return f"Thiết bị <b>{devs[0].device_name}</b> không tồn tại."


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
    sel_id = _get_selected_device_id(db, chat_id)
    lines = ["<b>📱 Danh sách thiết bị</b>",
             "Lệnh /lock, /unlock, /shot (không kèm tên) tác động lên thiết bị đang chọn (⭐).\n"]
    kb = {"inline_keyboard": []}
    for d in devs:
        on = "🟢" if _is_online(d) else "🔴"
        lock = "🔒" if d.is_locked else "🔓"
        star = " ⭐" if sel_id and str(d.id) == sel_id else ""
        lines.append(f"{on} {lock} <b>{d.device_name}</b>{star} (<code>{str(d.id)[:8]}</code>)")
        kb["inline_keyboard"].append([
            {"text": "🔒 Khóa", "callback_data": f"dev:lock:{d.id}"},
            {"text": "🔓 Mở", "callback_data": f"dev:unlock:{d.id}"},
            {"text": "📸 Ảnh", "callback_data": f"dev:shot:{d.id}"},
            {"text": "⭐ Chọn", "callback_data": f"dev:select:{d.id}"},
        ])
    send_message(token, chat_id, "\n".join(lines), reply_markup=kb)


def cmd_select(token, chat_id, db, arg):
    """Select the target device for this chat (used by lock/unlock/shot without a name)."""
    dev = _resolve_device(db, arg, None)
    if not dev:
        send_message(token, chat_id, "Không tìm thấy thiết bị. Dùng /devices để xem.")
        return
    _set_selected_device(db, chat_id, dev.id)
    on = "🟢" if _is_online(dev) else "🔴"
    send_message(token, chat_id, f"⭐ Đã chọn thiết bị <b>{dev.device_name}</b> {on}.\n"
                                 "Các lệnh /lock, /unlock, /shot sẽ tác động lên thiết bị này.")


def cmd_lock(token, chat_id, db, arg):
    dev = _resolve_device(db, arg, chat_id)
    if not dev:
        send_message(token, chat_id, _no_device_message(db, chat_id))
        return
    _queue_command(db, dev, "lock_screen", {"reason": "Khóa từ Telegram"})
    send_message(token, chat_id, f"🔒 Đã gửi lệnh <b>khóa</b> {dev.device_name}.")


def cmd_unlock(token, chat_id, db, arg):
    dev = _resolve_device(db, arg, chat_id)
    if not dev:
        send_message(token, chat_id, _no_device_message(db, chat_id))
        return
    _queue_command(db, dev, "unlock_screen", {})
    send_message(token, chat_id, f"🔓 Đã gửi lệnh <b>mở khóa</b> {dev.device_name}.")


def cmd_shot(token, chat_id, db, arg):
    dev = _resolve_device(db, arg, chat_id)
    if not dev:
        send_message(token, chat_id, _no_device_message(db, chat_id))
        return
    # latest screenshot timestamp before this request
    before = db.query(models.Screenshot).filter(
        models.Screenshot.device_id == dev.id
    ).order_by(models.Screenshot.timestamp.desc()).first()
    before_ts = before.timestamp if before else datetime(1970, 1, 1, tzinfo=timezone.utc)

    _queue_command(db, dev, "take_screenshot", {})
    send_message(token, chat_id, f"📸 Đã yêu cầu chụp màn hình <b>{dev.device_name}</b>. Đang chờ ảnh...")

    # Poll for a NEW screenshot (timeout ~30s — allows boto3 cold start on Vercel).
    for _ in range(30):
        time.sleep(1)
        shot = db.query(models.Screenshot).filter(
            models.Screenshot.device_id == dev.id
        ).order_by(models.Screenshot.timestamp.desc()).first()
        if shot and shot.timestamp and shot.timestamp > before_ts:
            send_photo(token, chat_id, shot.image_url, caption=f"📸 {dev.device_name} — {shot.timestamp.strftime('%d/%m %H:%M:%S')}")
            return
    send_message(token, chat_id, f"⏳ Chưa nhận được ảnh từ {dev.device_name} (thiết bị có thể offline).")


def _fmt_duration(sec: int) -> str:
    """Format seconds as 'Xh Ym' or 'Ym' (or 'Xs')."""
    sec = int(sec or 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _infer_domain_from_title(title) -> str | None:
    if not title:
        return None
    t = title.lower()
    known = {
        "youtube": "youtube.com", "facebook": "facebook.com", "fb ": "facebook.com",
        "google": "google.com", "wikipedia": "vi.wikipedia.org", "github": "github.com",
        "chatgpt": "chatgpt.com", "openai": "openai.com", "tiktok": "tiktok.com",
        "roblox": "roblox.com", "zalo": "zalo.me", "messenger": "messenger.com",
    }
    for key, dom in known.items():
        if key in t:
            return dom
    return None


def cmd_usage(token, chat_id, db, arg):
    """Báo cáo sử dụng đơn giản trong ngày: thời gian dùng máy, app & web nhiều nhất."""
    dev = _resolve_device(db, arg, chat_id)
    if not dev:
        send_message(token, chat_id, _no_device_message(db, chat_id))
        return

    now_vn = datetime.now(VIETNAM_TZ)
    midnight_vn = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_utc = midnight_vn.astimezone(timezone.utc).replace(tzinfo=None)

    logs = db.query(models.ProcessLog).filter(
        models.ProcessLog.device_id == dev.id,
        models.ProcessLog.timestamp >= midnight_utc,
    ).all()
    if not logs:
        send_message(token, chat_id,
                     f"📊 Chưa có dữ liệu sử dụng hôm nay của <b>{dev.device_name}</b>.\n"
                     "Thiết bị có thể đang tắt hoặc agent chưa gửi log.")
        return

    app_seconds = Counter()
    web_seconds = Counter()
    for log in logs:
        p = log.process_name or "Unknown"
        # Duration from state-change logging (fall back to 15s for legacy rows).
        secs = int(getattr(log, "duration", 0) or 0)
        if secs <= 0:
            secs = SCAN_INTERVAL_SEC
        app_seconds[p] += secs
        if p.lower() in BROWSER_EXES:
            dom = _infer_domain_from_title(log.window_title)
            if dom:
                web_seconds[dom] += secs

    total = sum(app_seconds.values())
    top_app = app_seconds.most_common(1)
    top_site = web_seconds.most_common(1)

    lines = [f"📊 <b>Báo cáo sử dụng</b> — {dev.device_name} ({now_vn.strftime('%d/%m')})"]
    lines.append(f"💻 Đã sử dụng máy tính: <b>{_fmt_duration(total)}</b>")
    if top_app:
        name, sec = top_app[0]
        lines.append(f"🖥️ Ứng dụng dùng nhiều nhất: <b>{name}</b> — {_fmt_duration(sec)}")
    if top_site:
        dom, sec = top_site[0]
        lines.append(f"🌐 Web truy cập nhiều nhất: <b>{dom}</b> — {_fmt_duration(sec)}")
    send_message(token, chat_id, "\n".join(lines))


def handle_message(update, token, chat_id, db):
    msg = update.get("message") or {}
    text = (msg.get("text") or "").strip()
    if not text:
        return
    low = text.lower()
    if low == "/start":
        send_message(token, chat_id, HELP_TEXT, reply_markup=_menu_keyboard())
    elif low == "/help":
        send_message(token, chat_id, HELP_TEXT)
    elif low == "/menu":
        _cmd_menu(token, chat_id)
    elif low.startswith("/devices"):
        cmd_devices(token, chat_id, db)
    elif low.startswith("/select"):
        cmd_select(token, chat_id, db, _arg(text))
    elif low.startswith("/lock") or low == "🔒 khóa máy":
        cmd_lock(token, chat_id, db, _arg(text))
    elif low.startswith("/unlock") or low == "🔓 mở khóa":
        cmd_unlock(token, chat_id, db, _arg(text))
    elif low.startswith("/shot") or low == "📸 chụp ảnh màn hình":
        cmd_shot(token, chat_id, db, _arg(text))
    elif low.startswith("/usage") or low == "📊 báo cáo sử dụng":
        cmd_usage(token, chat_id, db, _arg(text))
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
    elif action == "select":
        _set_selected_device(db, chat_id, dev.id)
        on = "🟢" if _is_online(dev) else "🔴"
        send_message(token, chat_id, f"⭐ Đã chọn thiết bị <b>{dev.device_name}</b> {on}.\n"
                                     "Các lệnh /lock, /unlock, /shot sẽ tác động lên thiết bị này.")
    return True


def handle_night_callback(data, db, token, chat_id):
    """data = night:allow:<device_id> | night:deny:<device_id>.

    Parent responds to the 00:00 "chơi quá muộn" warning:
      - allow -> do NOT lock (parent permits continued use)
      - deny  -> lock the device until 06:00 next morning
    """
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "night":
        return False
    action, dev_id = parts[1], parts[2]
    dev = db.query(models.Device).filter(models.Device.id == dev_id).first()
    if not dev:
        return False
    if action == "allow":
        send_message(token, chat_id, f"✅ Đã <b>cho phép</b> {dev.device_name} tiếp tục sử dụng.")
    elif action == "deny":
        _queue_command(db, dev, "lock_screen", {
            "reason": "Phụ huynh không cho phép chơi quá muộn. Khóa đến 6 giờ sáng.",
            "until_hour": 6,
        })
        send_message(token, chat_id, f"🚫 Đã <b>khóa</b> {dev.device_name} đến 6 giờ sáng.")
    return True
