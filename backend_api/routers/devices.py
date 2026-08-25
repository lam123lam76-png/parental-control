from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from database import get_db
import models
import schemas
from core.security import verify_api_key, require_permission, VALID_API_KEYS
from core.manager import manager
from core.config import SCREENSHOTS_DIR

# Note: format_local_time can be moved to a utils module, for now defining inline to avoid circular imports.
from datetime import timezone, timedelta
VIETNAM_TZ = timezone(timedelta(hours=7))

# A device is "online" if its last heartbeat was within this many seconds.
# `manager.active_connections` is in-memory and is lost on backend restart /
# reload, so we fall back to `last_seen_at` (written by every 15s heartbeat).
ONLINE_HEARTBEAT_THRESHOLD_SECONDS = 45


def _is_online(device) -> bool:
    """True if the device has an active WS connection OR a fresh heartbeat."""
    if manager.is_online(str(device.id)):
        return True
    last_seen = device.last_seen_at
    if not last_seen:
        return False
    # last_seen_at is stored in UTC (naive after SQLite round-trip).
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_seen).total_seconds() <= ONLINE_HEARTBEAT_THRESHOLD_SECONDS
def _resolve_device_uuid(device_id_str: str | None, db: Session) -> uuid.UUID | None:
    if device_id_str:
        try:
            return uuid.UUID(str(device_id_str).strip())
        except Exception:
            pass
    return None


router = APIRouter(tags=["devices"])


@router.get("/api/devices", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_key)])
def get_all_devices(db: Session = Depends(get_db)):
    """Returns list of all paired devices with online status."""
    devices = db.query(models.Device).all()
    data = [
        {
            "device_id": str(d.id),
            "device_name": d.device_name,
            "is_online": _is_online(d),
            "is_locked": bool(d.is_locked),
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None
        }
        for d in devices
    ]
    return schemas.StandardResponse(data={"devices": data}, status_code=200)


@router.get("/api/device/{device_id}/status", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_key)])
def get_device_status(device_id: str, db: Session = Depends(get_db)):
    """Check if a device is currently connected via WebSocket."""
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device = db.query(models.Device).filter(models.Device.id == device_uuid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_id_str = str(device_uuid)
    return schemas.StandardResponse(
        data={
            "device_id": device_id_str,
            "device_name": device.device_name,
            "is_online": _is_online(device),
            "is_locked": bool(device.is_locked),
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None
        },
        status_code=200
    )


@router.post("/api/screenshots/upload", response_model=schemas.StandardResponse)
async def upload_screenshot(
    device_id: str = Form(...),
    file: UploadFile = File(...),
    auth_token: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Upload a screenshot from a device agent.
    Accepts both authenticated requests and registered device IDs.
    Saves file to storage/screenshots/{unique_filename} and stores DB record.
    """
    target_device = None
    try:
        dev_uuid = uuid.UUID(device_id)
        target_device = db.query(models.Device).filter(models.Device.id == dev_uuid).first()
    except Exception:
        target_device = db.query(models.Device).filter(
            (models.Device.secret_token == device_id) | (models.Device.device_name == device_id)
        ).first()

    if not target_device:
        raise HTTPException(status_code=401, detail="Device not registered")

    target_device_id = target_device.id

    if auth_token not in VALID_API_KEYS and auth_token != target_device.secret_token and auth_token != str(target_device.id):
        raise HTTPException(status_code=403, detail="Forbidden: Token does not match device")

    # Determine extension dynamically
    ext = "jpg"
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
    elif file.content_type:
        mime_ext = file.content_type.split("/")[-1].lower()
        if mime_ext in ["webp", "png", "jpeg", "jpg"]:
            ext = "jpg" if mime_ext == "jpeg" else mime_ext

    unique_filename = f"shot_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}.{ext}"
    file_path = SCREENSHOTS_DIR / unique_filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    image_url = f"/static/screenshots/{unique_filename}"
    db_shot = models.Screenshot(
        device_id=target_device_id,
        image_url=image_url
    )
    db.add(db_shot)
    db.commit()
    db.refresh(db_shot)

    return schemas.StandardResponse(
        data={"screenshot_id": str(db_shot.id), "image_url": image_url},
        status_code=200
    )


@router.get("/api/device/{device_id}/screenshots", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_screenshots"))])
def get_device_screenshots(device_id: str, db: Session = Depends(get_db)):
    """
    Returns list of screenshots for the device ordered by timestamp desc.
    """
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        return schemas.StandardResponse(data={"screenshots": []}, status_code=200)

    screenshots = db.query(models.Screenshot).filter(
        models.Screenshot.device_id == device_uuid
    ).order_by(models.Screenshot.timestamp.desc()).all()

    data = [
        schemas.ScreenshotResponse.model_validate(s).model_dump(mode="json")
        for s in screenshots
    ]
    return schemas.StandardResponse(data={"screenshots": data}, status_code=200)


@router.delete("/api/screenshots/{screenshot_id}", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_screenshots"))])
def delete_screenshot(screenshot_id: str, db: Session = Depends(get_db)):
    """
    Deletes a specific screenshot file and its database record.
    """
    try:
        shot_uuid = uuid.UUID(screenshot_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid screenshot ID format")

    shot = db.query(models.Screenshot).filter(models.Screenshot.id == shot_uuid).first()
    if not shot:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    device_id = shot.device_id
    filename = shot.image_url.split("/")[-1]
    file_path = SCREENSHOTS_DIR / filename

    # Safely remove physical image file
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete physical screenshot file {file_path}: {e}")

    db.delete(shot)
    db.commit()

    # Return updated screenshots list for device
    remaining = db.query(models.Screenshot).filter(
        models.Screenshot.device_id == device_id
    ).order_by(models.Screenshot.timestamp.desc()).all()

    data = [
        schemas.ScreenshotResponse.model_validate(s).model_dump(mode="json")
        for s in remaining
    ]
    return schemas.StandardResponse(
        data={"msg": "Screenshot deleted successfully", "screenshots": data},
        status_code=200
    )


@router.delete("/api/device/{device_id}/screenshots", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_view_screenshots"))])
def delete_all_device_screenshots(device_id: str, db: Session = Depends(get_db)):
    """
    Deletes all screenshots for the specified device (both files and DB records).
    """
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        return schemas.StandardResponse(data={"msg": "No device found", "deleted_count": 0, "screenshots": []}, status_code=200)

    shots = db.query(models.Screenshot).filter(models.Screenshot.device_id == device_uuid).all()
    deleted_count = 0
    for shot in shots:
        filename = shot.image_url.split("/")[-1]
        file_path = SCREENSHOTS_DIR / filename
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        db.delete(shot)
        deleted_count += 1

    db.commit()
    return schemas.StandardResponse(
        data={"msg": f"Deleted {deleted_count} screenshots", "deleted_count": deleted_count, "screenshots": []},
        status_code=200
    )


