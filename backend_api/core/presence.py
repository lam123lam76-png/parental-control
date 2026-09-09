"""Unified device online/offline presence notifier (cloud/serverless-safe).

WHY THIS MODULE
---------------
On Vercel serverless each request runs in a fresh, short-lived process with no
guaranteed background thread. Two past bugs were fixed here:

1. Telegram sends MUST be synchronous (blocking requests) — a daemon thread
   fired inside `send_telegram_notification` is killed when the lambda returns,
   silently dropping the message. Every notification here POSTs inline.

2. On/off must be driven by BOTH the agent's own events AND staleness:
   - `agent_online`  -> device just booted -> mark online NOW (send "đã bật")
   - `agent_shutdown`/`agent_offline` -> device is going off -> mark offline NOW
   - staleness reconcile -> crash / power-loss / unplug backstop (last_seen old)
   This guarantees a graceful shutdown reports immediately, instead of only
   when a later request (or next-day reboot) happens to run the staleness check.

All state changes are an ATOMIC compare-and-swap on a persisted row
(`presence:<device_id>`), so concurrent serverless instances can never
double-send: the single instance that wins the UPDATE is the only one that
messages. The agent's `agent_online` / `agent_offline` / `agent_shutdown` alerts
are routed here (create_alert) rather than each pushing their own message.
"""
import logging
import os
import time
from datetime import datetime, timezone

from sqlalchemy import text

logger = logging.getLogger(__name__)

# A device is treated ONLINE while its last poll is fresher than ONLINE_SECONDS,
# and OFFLINE only once silent longer than OFFLINE_SECONDS (staleness backstop).
ONLINE_SECONDS = 45
OFFLINE_SECONDS = 90
# Don't flip the same device more often than this (seconds). Guards against a
# device that is rebooting in a loop (watchdog) spamming on/off.
MIN_SWITCH_INTERVAL = 90


def _now_epoch() -> int:
    return int(time.time())


def _parse(row_value: str):
    """Parse stored 'state:epoch'. Missing/invalid -> default offline, epoch 0."""
    try:
        state, ts = row_value.split(":", 1)
        return state, int(ts)
    except Exception:
        return "0", 0


def _send_sync(db, text: str) -> None:
    """Synchronously POST the Telegram message (blocking, inline).

    IMPORTANT: must NOT fire-and-forget a thread — on Vercel serverless the
    process is frozen once the response returns, so a background thread would
    be killed before the HTTP request completes and the message would be lost.
    """
    try:
        import requests as http_requests
        import models
        t_setting = db.query(models.TelegramSetting).first()
        token = (t_setting.bot_token if t_setting and t_setting.bot_token else None) or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id_str = (t_setting.chat_id if t_setting and t_setting.chat_id else None) or os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id_str:
            logger.warning("[presence] Telegram not configured; skipping notify")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        for chat_id in [c.strip() for c in chat_id_str.split(",") if c.strip()]:
            try:
                resp = http_requests.post(
                    url,
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                    timeout=8,
                )
                if resp.status_code != 200:
                    logger.warning(f"[presence] Telegram send HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"[presence] Telegram send failed: {e}")
    except Exception as e:  # pragma: no cover - never let a notify break a request
        logger.warning(f"[presence] notify error: {e}")


def _read_row(db, key: str):
    try:
        return db.execute(text("SELECT value FROM system_settings WHERE key = :k"), {"k": key}).first()
    except Exception:
        logger.warning(f"[presence] read failed for {key}", exc_info=True)
        return None


def _flip(db, device, target: str, *, now=None) -> None:
    """Flip a device's presence to `target` ("1"/"0") atomically and, if this
    instance won the CAS, send ONE concise message. Seeds silently on first
    sight. Respects MIN_SWITCH_INTERVAL unless `force` short-circuits it.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    key = f"presence:{device.id}"
    row = _read_row(db, key)

    if row is None:
        # First time observing this device: seed current state silently so we
        # don't spam "đã bật" for devices that predate the reconciler.
        try:
            db.execute(
                text("INSERT INTO system_settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO NOTHING"),
                {"k": key, "v": f"{target}:{_now_epoch()}"},
            )
            db.commit()
        except Exception:
            db.rollback()
        return

    cur_state, cur_ts = _parse(row[0])
    if cur_state == target:
        return  # already in target state — no change, no message

    # Atomic compare-and-swap: only ONE concurrent instance flips + sends.
    new_val = f"{target}:{_now_epoch()}"
    try:
        res = db.execute(
            text("UPDATE system_settings SET value = :nv WHERE key = :k AND value = :ov"),
            {"nv": new_val, "k": key, "ov": row[0]},
        )
        db.commit()
    except Exception:
        db.rollback()
        return
    if res.rowcount != 1:
        return  # lost the race — another instance already flipped.

    name = device.device_name or str(device.id)[:8]
    msg = f"🟢 PC <b>{name}</b> đã bật." if target == "1" else f"🔴 PC <b>{name}</b> đã tắt."
    _send_sync(db, msg)
    logger.info(f"[presence] {name} -> {'online' if target=='1' else 'offline'}")


def mark_online(db, device) -> None:
    """Agent reported it came online (agent_online alert / boot). Immediate."""
    try:
        _flip(db, device, "1")
    except Exception as e:  # pragma: no cover
        logger.error(f"[presence] mark_online error: {e}")
        try:
            db.rollback()
        except Exception:
            pass


def mark_offline(db, device) -> None:
    """Agent reported a graceful shutdown/offline (agent_shutdown/agent_offline)."""
    try:
        _flip(db, device, "0")
    except Exception as e:  # pragma: no cover
        logger.error(f"[presence] mark_offline error: {e}")
        try:
            db.rollback()
        except Exception:
            pass


def reconcile_presence(db) -> None:
    """Staleness backstop: if a device's last poll is old enough it must have
    gone offline without reporting (crash / power loss / network unplug), flip
    it offline and notify. Called from the middleware (every request) and from
    the background thread. Handles the online transition too (a device that was
    offline now polls again).
    """
    import models
    try:
        now = datetime.now(timezone.utc)
        devices = db.query(models.Device).all()
        for d in devices:
            if not d.last_seen_at:
                continue
            last = d.last_seen_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            age = (now - last).total_seconds()

            # Hysteresis: ONLINE if fresh, OFFLINE only if silent long.
            if age <= ONLINE_SECONDS:
                target = "1"
            elif age > OFFLINE_SECONDS:
                target = "0"
            else:
                continue  # hold zone — no flip, no message

            # Enforce anti-flap: skip if we flipped very recently (only in the
            # staleness path; agent events are authoritative and should always win).
            key = f"presence:{d.id}"
            row = _read_row(db, key)
            if row is not None:
                cur_state, cur_ts = _parse(row[0])
                if cur_state == target:
                    continue
                if _now_epoch() - cur_ts < MIN_SWITCH_INTERVAL:
                    continue
            _flip(db, d, target, now=now)
    except Exception as e:  # pragma: no cover - never let presence break a request
        logger.error(f"[presence] reconcile error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
