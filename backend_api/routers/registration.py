from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
import uuid
import logging
from datetime import datetime, timezone, timedelta

from database import get_db
import models
import schemas
from pydantic import BaseModel
from core.telegram_approval import send_registration_message
from core.security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["registration"])
limiter = Limiter(key_func=get_remote_address)

class RegisterRequest(BaseModel):
    hardware_uuid: str
    device_name: str

@router.post("/api/register-request", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
def request_registration(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Agent requests registration. Backend sends Telegram message for approval.
    """
    # Rate limit check (1 active per hw_uuid)
    existing = db.query(models.PendingRegistration).filter(
        models.PendingRegistration.hardware_uuid == body.hardware_uuid,
        models.PendingRegistration.status == "pending"
    ).first()
    
    if existing:
        return schemas.StandardResponse(
            data={"registration_id": str(existing.id), "status": "pending"},
            status_code=200
        )

    # If this hardware was already APPROVED, reuse its device credentials instead of
    # starting a new registration (prevents duplicate devices on reinstall).
    approved = db.query(models.PendingRegistration).filter(
        models.PendingRegistration.hardware_uuid == body.hardware_uuid,
        models.PendingRegistration.status == "approved"
    ).first()
    if approved and approved.device_id and approved.secret_token:
        return schemas.StandardResponse(
            data={
                "registration_id": str(approved.id),
                "status": "approved",
                "device_id": str(approved.device_id),
                "secret_token": approved.secret_token,
            },
            status_code=200
        )
        
    tg_setting = db.query(models.TelegramSetting).first()
    if not tg_setting or not tg_setting.bot_token or not tg_setting.chat_id:
        # If Telegram is not configured, we cannot process this.
        raise HTTPException(status_code=503, detail="Telegram not configured on backend")
        
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    new_reg = models.PendingRegistration(
        hardware_uuid=body.hardware_uuid,
        device_name=body.device_name,
        expires_at=expires,
        status="pending"
    )
    db.add(new_reg)
    db.commit()
    db.refresh(new_reg)
    
    msg_id = send_registration_message(new_reg, tg_setting.bot_token, tg_setting.chat_id)
    if msg_id:
        new_reg.tg_message_id = msg_id
        db.commit()
    else:
        logger.warning(f"Failed to send Telegram message for registration {new_reg.id}")
        
    return schemas.StandardResponse(
        data={"registration_id": str(new_reg.id), "status": "pending"},
        status_code=200
    )


@router.get("/api/register-request/{reg_id}/status", response_model=schemas.StandardResponse)
def get_registration_status(reg_id: str, db: Session = Depends(get_db)):
    try:
        reg_uuid = uuid.UUID(reg_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid registration ID")
        
    reg = db.query(models.PendingRegistration).filter(models.PendingRegistration.id == reg_uuid).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
        
    # Check if expired
    if reg.status == "pending" and reg.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        reg.status = "expired"
        db.commit()
        
    resp_data = {
        "status": reg.status
    }
    if reg.status == "approved":
        resp_data["device_id"] = str(reg.device_id) if reg.device_id else None
        resp_data["secret_token"] = reg.secret_token
        
    return schemas.StandardResponse(data=resp_data, status_code=200)


@router.post("/api/register-request/{reg_id}/resend", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("2/minute")
def resend_registration(request: Request, reg_id: str, db: Session = Depends(get_db)):
    try:
        reg_uuid = uuid.UUID(reg_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid registration ID")
        
    reg = db.query(models.PendingRegistration).filter(models.PendingRegistration.id == reg_uuid).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
        
    if reg.status != "pending":
        return schemas.StandardResponse(error="Request is no longer pending", status_code=400)
        
    tg_setting = db.query(models.TelegramSetting).first()
    if not tg_setting or not tg_setting.bot_token or not tg_setting.chat_id:
        raise HTTPException(status_code=503, detail="Telegram not configured on backend")
        
    msg_id = send_registration_message(reg, tg_setting.bot_token, tg_setting.chat_id)
    if msg_id:
        reg.tg_message_id = msg_id
        reg.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # refresh window on resend
        db.commit()
        return schemas.StandardResponse(data={"msg": "Resent successfully"}, status_code=200)
    else:
        return schemas.StandardResponse(error="Failed to send Telegram message", status_code=500)
