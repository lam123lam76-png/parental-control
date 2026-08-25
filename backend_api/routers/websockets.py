import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid
import asyncio

from database import get_db, SessionLocal
import models
import schemas
from core.manager import manager
import core.state

# Use same VIETNAM_TZ logic
from datetime import timedelta
VIETNAM_TZ = timezone(timedelta(hours=7))

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websockets"])

def _get_session() -> Session:
    """Create a new DB session (caller must close it)."""
    return SessionLocal()


@router.websocket("/ws/device/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str, token: str):
    """
    WebSocket endpoint for device agents.
    - Authenticates via secret_token (query param)
    - Maintains heartbeat loop
    """
    db = _get_session()
    try:
        from core.security import VALID_API_KEYS
        device = None
        try:
            dev_uuid = uuid.UUID(device_id)
            device = db.query(models.Device).filter(models.Device.id == dev_uuid).first()
        except Exception:
            device = db.query(models.Device).filter(
                (models.Device.secret_token == device_id) | (models.Device.device_name == device_id)
            ).first()

        is_auth = False
        if device and (device.secret_token == token or token in VALID_API_KEYS or str(device.id) == token):
            is_auth = True

        if not is_auth:
            logger.warning(f"WebSocket auth rejected for device_id={device_id}, token={token[:6] if token else 'None'}...")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        device_id_str = str(device.id)
    finally:
        db.close()

    await manager.connect(websocket, device_id_str)

    # Always send the current rules when an agent reconnects. REST updates are
    # persisted even while the agent is offline, so relying only on the
    # original PUT-time push leaves the agent enforcing stale local rules.
    sync_db = _get_session()
    try:
        current_rules = sync_db.query(models.Rule).filter(
            models.Rule.device_id == device.id
        ).all()
        rules_list = [
            schemas.RuleResponse.model_validate(rule).model_dump(mode="json")
            for rule in current_rules
        ]
        await manager.send_command(device_id_str, {
            "type": "command",
            "command": "refresh_rules",
            "payload": {"rules": rules_list},
        })
    except Exception as e:
        logger.error(f"Failed to sync rules on reconnect for {device_id_str}: {e}")
    finally:
        sync_db.close()

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("type") == "heartbeat":
                # Performance Optimization: Only update DB if last update was > 10s ago,
                # or just use short-lived session sparingly.
                db = _get_session()
                try:
                    db.query(models.Device).filter(
                        models.Device.id == device.id
                    ).update({"last_seen_at": datetime.now(timezone.utc)})
                    db.commit()
                finally:
                    db.close()
                
                await websocket.send_text(json.dumps({
                    "type": "heartbeat_ack",
                    "status": "ok"
                }))
            elif payload.get("type") == "version_info":
                msg_id = payload.get("msg_id")
                version = payload.get("version")
                if msg_id and version:
                    core.state.version_replies[msg_id] = version
            elif payload.get("type") == "chat_message":
                msg_text = payload.get("message") or ""
                sender_name = payload.get("sender") or "child"
                if msg_text:
                    db = _get_session()
                    try:
                        chat_entry = models.ChatMessage(
                            device_id=device.id,
                            sender=sender_name,
                            message=msg_text,
                            timestamp=datetime.now(timezone.utc)
                        )
                        db.add(chat_entry)
                        db.commit()
                    finally:
                        db.close()
                    logger.info(f"Saved chat message from {sender_name} on device {device_id_str}: {msg_text}")

    except WebSocketDisconnect:
        manager.disconnect(device_id_str)
    except Exception as e:
        logger.error(f"WebSocket error for device {device_id_str}: {e}")
        manager.disconnect(device_id_str)


# Commands use REST auth
from core.security import verify_api_key, require_permission, require_system_admin

@router.post("/api/device/{device_id}/command", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_remote_control"))])
async def send_device_command(
    device_id: str,
    command: schemas.DeviceCommand,
    db: Session = Depends(get_db)
):
    """Parent sends a command to a connected device."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if not manager.is_online(device_id):
        return schemas.StandardResponse(
            error="Device is offline.",
            status_code=503
        )
    
    msg_id = str(uuid.uuid4())
    cmd_payload = {
        "type": "command",
        "command": command.command,
        "payload": {**command.payload, "msg_id": msg_id} if command.payload else {"msg_id": msg_id}
    }
    success = await manager.send_command(device_id, cmd_payload)
    
    if success:
        if command.command == "check_version":
            for _ in range(20):
                await asyncio.sleep(0.25)
                if msg_id in core.state.version_replies:
                    ver = core.state.version_replies.pop(msg_id)
                    return schemas.StandardResponse(
                        data={"msg": f"kiểm tra phiên bản thành công : {ver}"},
                        status_code=200
                    )
            return schemas.StandardResponse(
                error="Hết thời gian chờ phản hồi từ Agent",
                status_code=408
            )

        from core.notifications import send_telegram_notification

        if command.command == "lock_screen":
            device.is_locked = True
            db.commit()
            send_telegram_notification(db, f"🔒 <b>[KHÓA THIẾT BỊ]</b> Thiết bị <b>{device.device_name}</b> đã bị khóa màn hình từ xa!")
        elif command.command == "unlock_screen":
            device.is_locked = False
            db.commit()
            send_telegram_notification(db, f"🔓 <b>[MỞ KHÓA THIẾT BỊ]</b> Thiết bị <b>{device.device_name}</b> đã được mở khóa từ xa!")
        elif command.command == "shutdown_pc":
            send_telegram_notification(db, f"⚡ <b>[TẮT NGUỒN TỪ XA]</b> Lệnh tắt nguồn máy tính đã được gửi tới thiết bị <b>{device.device_name}</b>!")

        return schemas.StandardResponse(
            data={"msg": f"Command '{command.command}' sent to device {device_id}"},
            status_code=200
        )
    else:
        return schemas.StandardResponse(
            error="Failed to send command. Device may have disconnected.",
            status_code=503
        )


@router.post("/api/device/{device_id}/shutdown", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_key)])
async def shutdown_device(
    device_id: str,
    payload: dict = None,
    db: Session = Depends(get_db)
):
    """Sends a graceful shutdown command to the remote device."""
    from core.notifications import send_telegram_notification
    dev = db.query(models.Device).filter(models.Device.id == uuid.UUID(device_id)).first()
    if not dev:
        return schemas.StandardResponse(error="Device not found", status_code=404)

    reason = (payload or {}).get("reason", "Thiết bị được tắt theo lệnh từ Phụ huynh")
    cmd_payload = {
        "type": "command",
        "command": "shutdown_pc",
        "payload": {
            "delay": 10,
            "reason": reason
        }
    }

    success = await manager.send_command(device_id, cmd_payload)
    if success:
        send_telegram_notification(db, f"⚡ <b>[TẮT NGUỒN TỪ XA]</b> Đã phát lệnh tắt nguồn tới <b>{dev.device_name}</b>!")
        return schemas.StandardResponse(
            data={"msg": f"Lệnh tắt nguồn đã được gửi tới thiết bị {dev.device_name} (Hẹn giờ 10s)"},
            status_code=200
        )
    else:
        return schemas.StandardResponse(
            error="Không thể gửi lệnh tắt nguồn. Thiết bị có thể đang ngoại tuyến.",
            status_code=503
        )


@router.post("/api/devices/force-update-all", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
async def force_update_all_devices():
    """Broadcasts WebSocket force_update command to all online devices."""
    from core.config import UPDATES_DIR
    import json
    
    version_json_path = UPDATES_DIR / "version.json"
    vdata = {"version": "2.0.0", "download_url": "/static/updates/agent-update.zip"}
    if version_json_path.exists():
        with open(version_json_path, "r", encoding="utf-8") as vf:
            vdata = json.load(vf)

    cmd_payload = {
        "type": "command",
        "command": "force_update",
        "payload": vdata
    }

    broadcast_count = 0
    for device_id in list(manager.active_connections.keys()):
        success = await manager.send_command(device_id, cmd_payload)
        if success:
            broadcast_count += 1

    return schemas.StandardResponse(
        data={"notified_devices": broadcast_count, "version": vdata["version"]},
        status_code=200
    )
