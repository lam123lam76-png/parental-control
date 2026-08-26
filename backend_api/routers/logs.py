from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, timezone
from typing import Optional

from database import get_db, get_db_async
import models
import schemas
from core.security import verify_api_key, require_permission, VALID_API_KEYS, decode_access_token
from core.manager import manager
from core.notifications import send_telegram_notification

# Note: format_local_time could be extracted to utils, using same logic as devices.py for now
from datetime import timedelta
VIETNAM_TZ = timezone(timedelta(hours=7))
def _infer_domain_from_title(title: str) -> Optional[str]:
    if not title: return None
    t_lower = title.lower()
    if "youtube" in t_lower: return "youtube.com"
    elif "facebook" in t_lower or "fb" in t_lower: return "facebook.com"
    elif "google" in t_lower: return "google.com"
    elif "wikipedia" in t_lower: return "vi.wikipedia.org"
    elif "github" in t_lower: return "github.com"
    elif "chatgpt" in t_lower or "openai" in t_lower: return "chatgpt.com"
    elif "tiktok" in t_lower: return "tiktok.com"
    elif "roblox" in t_lower: return "roblox.com"
    return None

def _resolve_device_uuid(device_id_str: Optional[str], db: Session) -> Optional[uuid.UUID]:
    if device_id_str:
        try:
            return uuid.UUID(str(device_id_str).strip())
        except Exception:
            pass
    return None

router = APIRouter(tags=["logs"])


@router.post("/api/v1/logs/browser-history", response_model=schemas.StandardResponse)
def batch_upload_browser_history(payload: schemas.BrowserHistoryBatch, db: Session = Depends(get_db)):
    """Batch upload browser history logs from Agent."""
    device_id_uuid = uuid.UUID(payload.device_id)
    added_count = 0

    for item in payload.items:
        ts = datetime.now(timezone.utc)
        if item.timestamp:
            try:
                ts = datetime.fromisoformat(item.timestamp.replace('Z', '+00:00'))
            except Exception:
                pass

        entry = models.BrowserHistory(
            device_id=device_id_uuid,
            browser_name=item.browser_name,
            url=item.url or "",
            page_title=item.page_title or "",
            timestamp=ts
        )
        db.add(entry)
        added_count += 1

    db.commit()
    return schemas.StandardResponse(data={"added": added_count}, status_code=200)


@router.get("/api/device/{device_id}/browser-history", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_logs"))])
def get_device_browser_history(
    device_id: str,
    limit: int = 100,
    search: Optional[str] = None,
    browser: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Fetch browser history logs with optional search query and browser filter."""
    dev_uuid = _resolve_device_uuid(device_id, db)
    if not dev_uuid:
        return schemas.StandardResponse(data={"history": []}, status_code=200)

    query = db.query(models.BrowserHistory).filter(
        models.BrowserHistory.device_id == dev_uuid
    )

    if browser and browser.lower() != "all":
        query = query.filter(models.BrowserHistory.browser_name.ilike(f"%{browser}%"))

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (models.BrowserHistory.page_title.ilike(search_fmt)) |
            (models.BrowserHistory.url.ilike(search_fmt))
        )

    history = query.order_by(models.BrowserHistory.timestamp.desc()).limit(limit).all()

    data = [
        {
            "id": str(h.id),
            "browser_name": h.browser_name,
            "url": h.url,
            "page_title": h.page_title,
            "timestamp": str(h.timestamp) if h.timestamp else None
        }
        for h in history
    ]
    return schemas.StandardResponse(data={"history": data}, status_code=200)


@router.post("/api/device/{device_id}/chat", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_remote_control"))])
async def send_chat_message(
    device_id: str,
    req: schemas.ChatMessageSend,
    db: AsyncSession = Depends(get_db_async)
):
    """Admin posts a chat message to child device."""
    dev_uuid = _resolve_device_uuid(device_id, db)
    if not dev_uuid:
        raise HTTPException(status_code=404, detail="Device not found")
    
    chat_entry = models.ChatMessage(
        device_id=dev_uuid,
        sender="admin",
        message=req.message,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(chat_entry)
    await db.commit()
    await db.refresh(chat_entry)

    # Push to device if online via WebSocket
    cmd_payload = {
        "type": "command",
        "command": "chat_message",
        "payload": {
            "sender": "admin",
            "message": req.message,
            "timestamp": str(chat_entry.timestamp)
        }
    }
    await manager.send_command(str(dev_uuid), cmd_payload)

    return schemas.StandardResponse(
        data={
            "id": str(chat_entry.id),
            "sender": "admin",
            "message": chat_entry.message,
            "timestamp": str(chat_entry.timestamp)
        },
        status_code=201
    )


@router.get("/api/device/{device_id}/chat/history", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_key)])
def get_chat_history(device_id: str, limit: int = 100, db: Session = Depends(get_db)):
    """Fetches chat history for device."""
    dev_uuid = _resolve_device_uuid(device_id, db)
    if not dev_uuid:
        return schemas.StandardResponse(data={"messages": []}, status_code=200)

    chats = db.query(models.ChatMessage).filter(
        models.ChatMessage.device_id == dev_uuid
    ).order_by(models.ChatMessage.timestamp.asc()).limit(limit).all()

    data = [
        {
            "id": str(c.id),
            "sender": c.sender,
            "message": c.message,
            "timestamp": str(c.timestamp) if c.timestamp else None
        }
        for c in chats
    ]
    return schemas.StandardResponse(data={"messages": data}, status_code=200)


@router.post("/api/logs/batch", response_model=schemas.StandardResponse)
def batch_insert_logs(
    batch: schemas.LogBatchUpload,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Receive a batch of process activity logs from a device agent."""
    dev_id_str = str(batch.device_id)
    device = None
    try:
        dev_uuid = uuid.UUID(dev_id_str)
        device = db.query(models.Device).filter(models.Device.id == dev_uuid).first()
    except Exception:
        device = db.query(models.Device).filter(
            (models.Device.secret_token == dev_id_str) | (models.Device.device_name == dev_id_str)
        ).first()

    if not device:
        if authorization:
            token = authorization.replace("Bearer ", "").strip()
            if token not in VALID_API_KEYS and not decode_access_token(token):
                raise HTTPException(status_code=401, detail="Unauthorized")
        else:
            raise HTTPException(status_code=401, detail="Unauthorized: Unregistered device")

    resolved_device_id = device.id if device else batch.device_id

    db_logs = [
        models.ProcessLog(
            device_id=resolved_device_id,
            process_name=log.process_name,
            window_title=log.window_title,
            timestamp=log.timestamp
        )
        for log in batch.logs
    ]
    db.add_all(db_logs)
    db.commit()
    
    return schemas.StandardResponse(
        data={"msg": f"Inserted {len(db_logs)} logs"},
        status_code=200
    )


@router.get("/api/device/{device_id}/logs", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_logs"))])
def get_device_logs(device_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Returns recent process activity logs for the device."""
    dev_uuid = _resolve_device_uuid(device_id, db)
    if not dev_uuid:
        return schemas.StandardResponse(data={"logs": []}, status_code=200)

    logs = db.query(models.ProcessLog).filter(
        models.ProcessLog.device_id == dev_uuid
    ).order_by(models.ProcessLog.timestamp.desc()).limit(limit).all()

    data = [
        {
            "id": str(l.id),
            "process_name": l.process_name,
            "window_title": l.window_title,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None
        }
        for l in logs
    ]
    return schemas.StandardResponse(data={"logs": data}, status_code=200)


# Need to expose this globally for other modules or move to core/manager?
# device_graceful_shutdown is used here and in websockets
from core.manager import manager # manager instance is there, what about states?
# Since state is used in multiple places, we'll import it from core.state or assume it's moved there.
# Let's create core.state for these dicts.
import core.state

@router.post("/api/alerts", response_model=schemas.StandardResponse)
def create_alert(
    alert: schemas.AlertCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Receive an urgent alert from a device agent (e.g., banned app opened)."""
    dev_id_str = str(alert.device_id)
    device = None
    try:
        dev_uuid = uuid.UUID(dev_id_str)
        device = db.query(models.Device).filter(models.Device.id == dev_uuid).first()
    except Exception:
        device = db.query(models.Device).filter(
            (models.Device.secret_token == dev_id_str) | (models.Device.device_name == dev_id_str)
        ).first()

    if not device:
        if authorization:
            token = authorization.replace("Bearer ", "").strip()
            if token not in VALID_API_KEYS and not decode_access_token(token):
                raise HTTPException(status_code=401, detail="Unauthorized")
        else:
            raise HTTPException(status_code=401, detail="Unauthorized: Unregistered device")

    resolved_device_id = device.id if device else alert.device_id

    db_alert = models.Alert(
        device_id=resolved_device_id,
        alert_type=alert.alert_type,
        message=alert.message
    )
    db.add(db_alert)
    db.commit()
    
    # Check if this is a graceful shutdown alert
    if alert.alert_type == "agent_shutdown":
        core.state.device_graceful_shutdown[str(resolved_device_id)] = True

    # Send instant Telegram Alert
    dev_name = device.device_name if device else "Agent PC"
    msg_text = f"🚨 <b>[PARENTAL CONTROL ALERTS]</b>\n<b>Thiết bị:</b> {dev_name}\n<b>Loại Cảnh Báo:</b> {alert.alert_type}\n<b>Nội dung:</b> {alert.message}"
    send_telegram_notification(db, msg_text)
    
    return schemas.StandardResponse(data={"msg": "Alert received"}, status_code=200)


@router.get("/api/device/{device_id}/alerts", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_logs"))])
def get_device_alerts(device_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Returns recent alerts for the device."""
    dev_uuid = _resolve_device_uuid(device_id, db)
    if not dev_uuid:
        return schemas.StandardResponse(data={"alerts": []}, status_code=200)

    alerts = db.query(models.Alert).filter(
        models.Alert.device_id == dev_uuid
    ).order_by(models.Alert.created_at.desc()).limit(limit).all()

    data = [
        {
            "id": str(a.id),
            "alert_type": a.alert_type,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in alerts
    ]
    return schemas.StandardResponse(data={"alerts": data}, status_code=200)


from collections import Counter
from urllib.parse import urlparse

@router.get("/api/device/{device_id}/analytics", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_logs"))])
def get_device_analytics(device_id: str, db: Session = Depends(get_db)):
    """
    Computes weekly/monthly usage analytics for the device:
    - Daily activity distribution for past 7 days
    - Top 5 applications by activity
    - Top 5 websites visited
    - Trend comparison (% vs previous 7-day period)
    """
    dev_uuid = _resolve_device_uuid(device_id, db)
    if not dev_uuid:
        return schemas.StandardResponse(data={"total_logs_week": 0, "prev_logs_week": 0, "trend_percentage": 0, "top_apps": [], "top_sites": [], "daily_trend": []}, status_code=200)

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # 1. Process Logs in the last 7 days vs previous 7 days
    recent_logs = db.query(models.ProcessLog).filter(
        models.ProcessLog.device_id == dev_uuid,
        models.ProcessLog.timestamp >= week_ago
    ).all()

    prev_logs_count = db.query(models.ProcessLog).filter(
        models.ProcessLog.device_id == dev_uuid,
        models.ProcessLog.timestamp >= two_weeks_ago,
        models.ProcessLog.timestamp < week_ago
    ).count()

    # App usage ranking
    app_counts = Counter(l.process_name for l in recent_logs if l.process_name)
    top_apps = [{"name": app, "count": count} for app, count in app_counts.most_common(5)]

    # Daily breakdown (Mon - Sun)
    daily_counts = {i: 0 for i in range(7)}
    for l in recent_logs:
        if l.timestamp:
            day_idx = l.timestamp.weekday()
            daily_counts[day_idx] += 1

    day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    daily_trend = [{"day": day_names[i], "count": daily_counts[i]} for i in range(7)]

    # 2. Browser History Ranking
    recent_history = db.query(models.BrowserHistory).filter(
        models.BrowserHistory.device_id == dev_uuid,
        models.BrowserHistory.timestamp >= week_ago
    ).all()

    domains = []
    for h in recent_history:
        if h.url:
            try:
                parsed = urlparse(h.url)
                netloc = parsed.netloc.replace("www.", "")
                if netloc:
                    domains.append(netloc)
            except Exception:
                pass

    domain_counts = Counter(domains)
    top_sites = [{"domain": dom, "count": count} for dom, count in domain_counts.most_common(5)]

    # Trend calculation
    curr_count = len(recent_logs)
    if prev_logs_count > 0:
        trend_pct = round(((curr_count - prev_logs_count) / prev_logs_count) * 100, 1)
    else:
        trend_pct = 0.0

    return schemas.StandardResponse(
        data={
            "total_logs_week": curr_count,
            "prev_logs_week": prev_logs_count,
            "trend_percentage": trend_pct,
            "top_apps": top_apps,
            "top_sites": top_sites,
            "daily_trend": daily_trend
        },
        status_code=200
    )


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    rem_mins = minutes % 60
    if rem_mins == 0:
        return f"{hours}h"
    return f"{hours}h {rem_mins}m"


@router.get("/api/device/{device_id}/screen-time/today", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_logs"))])
def get_today_screen_time(device_id: str, db: Session = Depends(get_db)):
    """
    Computes precise today's active screen time (since 00:00 local time):
    - Total active screen time in seconds and formatted (e.g. 2h 15m)
    - App usage breakdown with duration and percentage
    - Web usage breakdown with duration
    - Hourly activity timeline (0h - 23h)
    """
    dev_uuid = _resolve_device_uuid(device_id, db)
    if not dev_uuid:
        return schemas.StandardResponse(data={"total_screen_seconds": 0, "formatted_total": "0m", "top_apps": [], "top_sites": [], "hourly_distribution": [0]*24}, status_code=200)

    now_vn = datetime.now(VIETNAM_TZ)
    midnight_vn = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_utc = midnight_vn.astimezone(timezone.utc).replace(tzinfo=None)

    # 1. Fetch today's process logs (each log represents ~5s active scan)
    today_logs = db.query(models.ProcessLog).filter(
        models.ProcessLog.device_id == dev_uuid,
        models.ProcessLog.timestamp >= midnight_utc
    ).order_by(models.ProcessLog.timestamp.asc()).all()

    BROWSER_EXES = {"chrome.exe", "msedge.exe", "coccoc.exe", "brave.exe", "firefox.exe", "opera.exe", "iexplore.exe"}

    app_seconds = Counter()
    web_seconds = Counter()
    hourly_distribution = [0] * 24

    for log in today_logs:
        p_name = log.process_name or "Unknown"
        # Each active log scan = 15 seconds (Matches agent config.PROCESS_SCAN_INTERVAL)
        app_seconds[p_name] += 15
        if log.timestamp:
            try:
                log_vn = log.timestamp.replace(tzinfo=timezone.utc).astimezone(VIETNAM_TZ)
                hourly_distribution[log_vn.hour] += 15
            except Exception:
                pass
        
        # Calculate web time from process logs of browsers
        if p_name.lower() in BROWSER_EXES:
            domain = _infer_domain_from_title(log.window_title)
            if domain:
                web_seconds[domain] += 15

    total_screen_seconds = sum(app_seconds.values())
    top_apps_today = [
        {
            "name": app,
            "seconds": sec,
            "minutes": round(sec / 60, 1),
            "formatted": format_duration(sec),
            "percentage": round((sec / total_screen_seconds) * 100, 1) if total_screen_seconds > 0 else 0
        }
        for app, sec in app_seconds.most_common(10)
    ]

    total_web_seconds = sum(web_seconds.values())
    top_sites_today = [
        {
            "domain": dom,
            "seconds": sec,
            "minutes": round(sec / 60, 1),
            "formatted": format_duration(sec),
            "percentage": round((sec / total_web_seconds) * 100, 1) if total_web_seconds > 0 else 0
        }
        for dom, sec in web_seconds.most_common(10)
    ]

    # Format hourly breakdown
    hourly_breakdown = [
        {"hour": f"{h:02d}:00", "minutes": round(hourly_distribution[h] / 60, 1)}
        for h in range(24)
    ]

    return schemas.StandardResponse(
        data={
            "device_id": device_id,
            "date": now_vn.strftime("%Y-%m-%d"),
            "total_screen_seconds": total_screen_seconds,
            "total_screen_minutes": round(total_screen_seconds / 60, 1),
            "formatted_total_time": format_duration(total_screen_seconds),
            "top_apps_today": top_apps_today,
            "top_sites_today": top_sites_today,
            "hourly_breakdown": hourly_breakdown
        },
        status_code=200
    )

