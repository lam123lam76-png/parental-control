"""Unified device online/offline presence notifier (cloud/serverless-safe).

Why this module exists
----------------------
Before, online/offline Telegram notifications came from several places with no
shared guard:
  - the agent POSTed `agent_online` / `agent_shutdown` alerts, and the backend
    wrapped each into a Telegram message in `create_alert`;
  - the backend also detected offline in `check_devices_offline`, which ran on
    *every* request (middleware) and on a background thread. On Vercel serverless
    many lambdas run that check concurrently with no locking, so a single
    offline transition could fire several "đã tắt" messages; and the graceful
    flag lived only in RAM (`core.state`), so it was lost between invocations,
    producing a duplicate (the agent_shutdown wrapper *plus* the offline one).

This module makes ONE reconciler the single source of Telegram on/off messages:
  - It reads each device's real presence from `last_seen_at`.
  - It only notifies on a *real* transition (online<->offline).
  - The state flip is an atomic compare-and-swap on a persisted row
    (`presence:<device_id>`), so concurrent serverless instances can never
    double-send: the single instance that wins the UPDATE is the only one that
    messages.
  - Hysteresis (different online vs offline thresholds) + a minimum time between
    switches stops brief network blips / reboots from flapping messages.

The agent's own `agent_online` / `agent_offline` / `agent_shutdown` alerts are
now recorded to the DB but do NOT send Telegram themselves; this reconciler
decides. `check_devices_offline` in main.py just calls `reconcile_presence`.
"""
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import text

logger = logging.getLogger(__name__)

# A device is treated ONLINE while its last poll is fresher than ONLINE_SECONDS,
# and OFFLINE only once it has been silent for longer than OFFLINE_SECONDS.
# The gap between them is a "hold" zone: during a blip we keep the last known
# state instead of toggling, which is what stops ON/OFF/ON/OFF spam.
ONLINE_SECONDS = 45
OFFLINE_SECONDS = 90
# Don't flip the same device more often than this (seconds). Guards against a
# device that is genuinely rebooting in a loop (watchdog restart) spamming.
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


def _notify(db, text: str) -> None:
    # Import lazily to avoid a circular import at module load.
    from core.notifications import send_telegram_notification
    try:
        send_telegram_notification(db, text)
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"[presence] telegram send failed: {e}")


def reconcile_presence(db) -> None:
    """Compute each device's live presence and emit ONE concise Telegram message
    per genuine transition. Safe to call on every request (serverless) and from
    a background thread; the atomic UPDATE guarantees single-sender semantics.
    """
    import models
    try:
        now = datetime.now(timezone.utc)
        devices = db.query(models.Device).all()
        for d in devices:
            if not d.last_seen_at:
                # Never seen online yet -> nothing to reconcile.
                continue
            last = d.last_seen_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            age = (now - last).total_seconds()

            # Hysteresis target: ONLINE if fresh, OFFLINE only if silent long,
            # otherwise hold (no change, no message).
            if age <= ONLINE_SECONDS:
                target = "1"
            elif age > OFFLINE_SECONDS:
                target = "0"
            else:
                continue  # uncertain window -> keep last state, notify nothing

            key = f"presence:{d.id}"
            try:
                row = db.execute(
                    text("SELECT value FROM system_settings WHERE key = :k"),
                    {"k": key},
                ).first()
            except Exception:
                # Table/migration issue — be safe, skip device.
                logger.warning(f"[presence] read failed for {key}", exc_info=True)
                continue

            if row is None:
                # First time we observe this device: seed its current state
                # silently so we don't spam "đã bật" for devices that were
                # already up before this reconciler existed.
                try:
                    db.execute(
                        text(
                            "INSERT INTO system_settings (key, value) VALUES (:k, :v) "
                            "ON CONFLICT (key) DO NOTHING"
                        ),
                        {"k": key, "v": f"{target}:{_now_epoch()}"},
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                continue

            cur_state, cur_ts = _parse(row[0])
            if cur_state == target:
                continue
            # Anti-flap: if we flipped very recently, skip this pass entirely.
            if _now_epoch() - cur_ts < MIN_SWITCH_INTERVAL:
                continue

            # Atomic compare-and-swap: only ONE concurrent instance can flip and
            # thus only ONE can send the Telegram message.
            new_val = f"{target}:{_now_epoch()}"
            try:
                res = db.execute(
                    text(
                        "UPDATE system_settings SET value = :nv "
                        "WHERE key = :k AND value = :ov"
                    ),
                    {"nv": new_val, "k": key, "ov": row[0]},
                )
                db.commit()
            except Exception:
                db.rollback()
                continue
            if res.rowcount != 1:
                continue  # Lost the race — another instance already flipped.

            name = d.device_name or str(d.id)[:8]
            if target == "1":
                _notify(db, f"🟢 PC <b>{name}</b> đã bật.")
            else:
                _notify(db, f"🔴 PC <b>{name}</b> đã tắt.")
            logger.info(f"[presence] {name} -> {'online' if target=='1' else 'offline'}")
    except Exception as e:  # pragma: no cover - never let presence break a request
        logger.error(f"[presence] reconcile error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
