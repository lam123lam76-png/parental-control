from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from pydantic import BaseModel, Field, conint
import uuid

from database import get_db, get_db_async
import models
import schemas
from core.security import verify_api_key, require_permission
from core.manager import manager

router = APIRouter(tags=["rules"], dependencies=[Depends(verify_api_key)])


def _resolve_device_uuid(device_id_str: Optional[str], db: Session) -> Optional[uuid.UUID]:
    """Safely resolves string device_id."""
    if device_id_str:
        try:
            return uuid.UUID(str(device_id_str).strip())
        except Exception:
            pass
    return None


@router.get("/api/device/{device_id}/rules", response_model=schemas.StandardResponse)
def get_device_rules(device_id: str, db: Session = Depends(get_db)):
    """
    Returns list of rules for the device.
    """
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        return schemas.StandardResponse(data={"rules": []}, status_code=200)

    rules = db.query(models.Rule).filter(
        models.Rule.device_id == device_uuid
    ).all()

    data = [
        schemas.RuleResponse.model_validate(r).model_dump(mode="json")
        for r in rules
    ]
    return schemas.StandardResponse(data={"rules": data}, status_code=200)


@router.post("/api/device/{device_id}/rules", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_manage_rules"))])
async def create_device_rule(
    device_id: str,
    rule_data: schemas.RuleCreate,
    db: AsyncSession = Depends(get_db_async)
):
    """
    Creates a new rule for the specified device.
    Pushes 'refresh_rules' command via WebSocket if the device is online.
    """
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        raise HTTPException(status_code=404, detail="Device not found")

    db_rule = models.Rule(
        device_id=device_uuid,
        rule_type=rule_data.rule_type,
        target=rule_data.target,
        is_banned=rule_data.is_banned,
        daily_limit_minutes=rule_data.daily_limit_minutes,
        day_of_week=rule_data.day_of_week,
        allowed_start=rule_data.allowed_start,
        allowed_end=rule_data.allowed_end
    )
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)

    # Fetch all rules for the device
    device_id_str = str(device_uuid)
    all_rules = (await db.execute(
        select(models.Rule).where(models.Rule.device_id == device_uuid)
    )).scalars().all()
    rules_list = [
        schemas.RuleResponse.model_validate(r).model_dump(mode="json")
        for r in all_rules
    ]

    if manager.is_online(device_id_str):
        ws_command = {
            "type": "command",
            "command": "refresh_rules",
            "payload": {"rules": rules_list}
        }
        await manager.send_command(device_id_str, ws_command)

    created_rule_data = schemas.RuleResponse.model_validate(db_rule).model_dump(mode="json")
    return schemas.StandardResponse(data={"rule": created_rule_data, "rules": rules_list}, status_code=200)


@router.delete("/api/rules/{rule_id}", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_manage_rules"))])
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db_async)):
    """
    Deletes specified rule.
    Pushes 'refresh_rules' command with updated rules via WebSocket if device is online.
    """
    try:
        rule_uuid = uuid.UUID(rule_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    db_rule = (await db.execute(select(models.Rule).where(models.Rule.id == rule_uuid))).scalars().first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    device_id_str = str(db_rule.device_id)
    await db.delete(db_rule)
    await db.commit()

    # Fetch remaining rules for the device
    all_rules = (await db.execute(
        select(models.Rule).where(models.Rule.device_id == uuid.UUID(device_id_str))
    )).scalars().all()
    rules_list = [
        schemas.RuleResponse.model_validate(r).model_dump(mode="json")
        for r in all_rules
    ]

    if manager.is_online(device_id_str):
        ws_command = {
            "type": "command",
            "command": "refresh_rules",
            "payload": {"rules": rules_list}
        }
        await manager.send_command(device_id_str, ws_command)

    return schemas.StandardResponse(data={"msg": "Rule deleted", "rules": rules_list}, status_code=200)


# ==========================================
# FOCUS MODE (CHẾ ĐỘ HỌC BÀI 1 CHẠM)
# ==========================================
class FocusModeRequest(BaseModel):
    duration_minutes: int = 60
    enabled: bool = True

FOCUS_MODE_TARGETS = [
    # Games
    {"rule_type": "app", "target": "LeagueClient.exe"},
    {"rule_type": "app", "target": "RiotClientServices.exe"},
    {"rule_type": "app", "target": "LienMinh.exe"},
    {"rule_type": "app", "target": "RobloxPlayerBeta.exe"},
    {"rule_type": "app", "target": "steam.exe"},
    {"rule_type": "app", "target": "Garena.exe"},
    {"rule_type": "app", "target": "javaw.exe"},
    {"rule_type": "app", "target": "GenshinImpact.exe"},
    {"rule_type": "app", "target": "Valorant.exe"},
    {"rule_type": "app", "target": "Discord.exe"},
    # Social / Entertainment
    {"rule_type": "web", "target": "facebook.com"},
    {"rule_type": "web", "target": "tiktok.com"},
    {"rule_type": "web", "target": "youtube.com"},
    {"rule_type": "web", "target": "bilibili.tv"},
    {"rule_type": "web", "target": "netflix.com"},
    {"rule_type": "web", "target": "twitch.tv"},
]


def _send_notification(text: str) -> None:
    """Sends a Telegram notification via its own short-lived SYNC session.

    core.notifications.send_telegram_notification only supports a sync
    Session (it calls db.query), so async endpoints must not hand it the
    AsyncSession. A fresh sync session keeps the notification working
    without touching the async one.
    """
    from core.notifications import send_telegram_notification
    from database import SessionLocal
    ndb = SessionLocal()
    try:
        send_telegram_notification(ndb, text)
    finally:
        ndb.close()


@router.post("/api/device/{device_id}/focus-mode", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_manage_rules"))])
async def toggle_focus_mode(
    device_id: str,
    req: FocusModeRequest,
    db: AsyncSession = Depends(get_db_async)
):
    """
    Toggle 1-Click Focus Mode (Chế độ Học Bài).
    When enabled, auto-applies strict ban rules for games and social media.
    """
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        raise HTTPException(status_code=404, detail="Device not found")

    device = (await db.execute(select(models.Device).where(models.Device.id == device_uuid))).scalars().first()
    existing_rules = (await db.execute(select(models.Rule).where(models.Rule.device_id == device_uuid))).scalars().all()
    existing_targets = {(r.rule_type, r.target.lower()) for r in existing_rules if r.target}

    device_id_str = str(device_uuid)

    if req.enabled:
        added_count = 0
        for item in FOCUS_MODE_TARGETS:
            key = (item["rule_type"], item["target"].lower())
            if key not in existing_targets:
                new_r = models.Rule(
                    device_id=device_uuid,
                    rule_type=item["rule_type"],
                    target=item["target"],
                    is_banned=True
                )
                db.add(new_r)
                added_count += 1
        await db.commit()

        # Push to agent
        all_rules = (await db.execute(select(models.Rule).where(models.Rule.device_id == device_uuid))).scalars().all()
        rules_list = [schemas.RuleResponse.model_validate(r).model_dump(mode="json") for r in all_rules]
        if manager.is_online(device_id_str):
            await manager.send_command(device_id_str, {"type": "command", "command": "refresh_rules", "payload": {"rules": rules_list}})

        _send_notification(
            f"🎯 <b>[CHẾ ĐỘ HỌC BÀI]</b> Đã kích hoạt Focus Mode ({req.duration_minutes} phút) cho thiết bị <b>{device.device_name if device else 'Máy Con'}</b>! Đã bật chặn các ứng dụng game và mạng xã hội."
        )

        return schemas.StandardResponse(
            data={"focus_mode": True, "duration_minutes": req.duration_minutes, "rules_added": added_count, "rules": rules_list},
            status_code=200
        )
    else:
        # Revert focus mode targets
        deleted_count = 0
        focus_target_names = {t["target"].lower() for t in FOCUS_MODE_TARGETS}
        for r in existing_rules:
            if r.target and r.target.lower() in focus_target_names:
                await db.delete(r)
                deleted_count += 1
        await db.commit()

        all_rules = (await db.execute(select(models.Rule).where(models.Rule.device_id == device_uuid))).scalars().all()
        rules_list = [schemas.RuleResponse.model_validate(r).model_dump(mode="json") for r in all_rules]
        if manager.is_online(device_id_str):
            await manager.send_command(device_id_str, {"type": "command", "command": "refresh_rules", "payload": {"rules": rules_list}})

        _send_notification(
            f"🟢 <b>[TẮT CHẾ ĐỘ HỌC BÀI]</b> Đã tắt Focus Mode cho thiết bị <b>{device.device_name if device else 'Máy Con'}</b>. Đã khôi phục quy tắc thông thường."
        )

        return schemas.StandardResponse(
            data={"focus_mode": False, "rules_removed": deleted_count, "rules": rules_list},
            status_code=200
        )


# ==========================================
# TIME CONTROL & RESTRICTIONS (ALLOWED HOURS & APP/WEB RESTRICTIONS)
# ==========================================
class ScheduleItem(BaseModel):
    days: List[conint(ge=0, le=6)] = Field(..., min_length=1)
    start: str = Field(..., min_length=5, max_length=5, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")  # "07:00"
    end: str = Field(..., min_length=5, max_length=5, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")    # "22:00"

class TimeControlRequest(BaseModel):
    device_id: Optional[str] = None
    schedules: List[ScheduleItem] = Field(default_factory=list)


@router.get("/api/settings/time-control/allowed-hours", response_model=schemas.StandardResponse)
async def get_time_control(device_id: Optional[str] = None, db: AsyncSession = Depends(get_db_async)):
    """Fetch allowed operating hours for device."""
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        return schemas.StandardResponse(data={"schedules": []}, status_code=200)

    rules = (await db.execute(
        select(models.Rule).where(
            models.Rule.device_id == device_uuid,
            models.Rule.rule_type == "time"
        )
    )).scalars().all()
    
    # Group rules by start and end time to reconstruct schedules array
    schedules_dict = {}
    
    def format_time(t):
        if hasattr(t, 'strftime'):
            return t.strftime('%H:%M')
        # Fallback for string or other types
        s = str(t)
        parts = s.split(':')
        if len(parts) >= 2:
            try:
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
            except ValueError:
                pass
        return s[:5]

    for r in rules:
        if r.allowed_start is None or r.allowed_end is None or r.day_of_week is None:
            continue
            
        start_str = format_time(r.allowed_start)
        end_str = format_time(r.allowed_end)
        
        key = f"{start_str}-{end_str}"
        if key not in schedules_dict:
            schedules_dict[key] = {
                "days": [],
                "start": start_str,
                "end": end_str
            }
        schedules_dict[key]["days"].append(r.day_of_week)
    
    schedules = list(schedules_dict.values())
    return schemas.StandardResponse(data={"schedules": schedules}, status_code=200)


@router.put("/api/settings/time-control/allowed-hours", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_manage_rules"))])
async def update_time_control(req: TimeControlRequest, db: AsyncSession = Depends(get_db_async)):
    """Update allowed operating hours and push refresh_rules immediately to agent."""
    device_uuid = _resolve_device_uuid(req.device_id, db)
    if not device_uuid:
        return schemas.StandardResponse(error="Không tìm thấy thiết bị để áp dụng khung giờ", status_code=404)
    
    try:
        # 1. Delete all existing time rules for device
        await db.execute(
            delete(models.Rule).where(
                models.Rule.device_id == device_uuid,
                models.Rule.rule_type == "time"
            )
        )
        
        # 2. Add new time rules
        from datetime import time
        added_count = 0
        for schedule in req.schedules:
            try:
                start_hour, start_min = map(int, schedule.start.split(":"))
                end_hour, end_min = map(int, schedule.end.split(":"))
                st = time(start_hour, start_min)
                et = time(end_hour, end_min)
            except Exception as parse_e:
                await db.rollback()
                return schemas.StandardResponse(error=f"Định dạng giờ không hợp lệ: {schedule.start} - {schedule.end}", status_code=400)
                
            for day in schedule.days:
                new_r = models.Rule(
                    device_id=device_uuid,
                    rule_type="time",
                    day_of_week=day,
                    allowed_start=st,
                    allowed_end=et,
                    is_banned=True
                )
                db.add(new_r)
                added_count += 1
                
        await db.commit()
    except Exception as e:
        await db.rollback()
        return schemas.StandardResponse(error=f"Lỗi khi lưu thời gian: {str(e)}", status_code=500)
    
    # 3. Push to agent
    device_id_str = str(device_uuid)
    all_rules = (await db.execute(select(models.Rule).where(models.Rule.device_id == device_uuid))).scalars().all()
    rules_list = [schemas.RuleResponse.model_validate(r).model_dump(mode="json") for r in all_rules]
    if manager.is_online(device_id_str):
        await manager.send_command(device_id_str, {"type": "command", "command": "refresh_rules", "payload": {"rules": rules_list}})
        
    return schemas.StandardResponse(data={"msg": "Đã lưu khung giờ thành công", "rules_added": added_count}, status_code=200)


@router.get("/api/settings/time-control/restrictions", response_model=schemas.StandardResponse)
async def get_time_control_restrictions(device_id: Optional[str] = None, db: AsyncSession = Depends(get_db_async)):
    """Fetch App/Web restrictions list for TimeControlSettingsCard Tab 2."""
    device_uuid = _resolve_device_uuid(device_id, db)
    if not device_uuid:
        return schemas.StandardResponse(data={"rules": []}, status_code=200)

    rules = (await db.execute(
        select(models.Rule).where(
            models.Rule.device_id == device_uuid,
            models.Rule.rule_type.in_(["app", "web"])
        )
    )).scalars().all()

    items = []
    for r in rules:
        mode = "limit" if r.daily_limit_minutes else ("ban" if r.is_banned else "allow")
        items.append({
            "id": str(r.id),
            "type": r.rule_type,
            "target": r.target or "",
            "mode": mode,
            "daily_limit_minutes": r.daily_limit_minutes
        })

    return schemas.StandardResponse(data={"rules": items}, status_code=200)


@router.put("/api/settings/time-control/restrictions", response_model=schemas.StandardResponse, dependencies=[Depends(require_permission("can_manage_rules"))])
async def update_time_control_restrictions(req: schemas.RestrictionsRequest, db: AsyncSession = Depends(get_db_async)):
    """Update App/Web restrictions in batch and push refresh_rules to agent."""
    device_uuid = _resolve_device_uuid(req.device_id, db)
    if not device_uuid:
        return schemas.StandardResponse(error="Không tìm thấy thiết bị để áp dụng quy tắc", status_code=404)

    try:
        # Delete existing app and web rules
        await db.execute(
            delete(models.Rule).where(
                models.Rule.device_id == device_uuid,
                models.Rule.rule_type.in_(["app", "web"])
            )
        )

        for item in req.rules:
            target = item.target.strip()
            if not target:
                continue
            is_banned = (item.mode != "allow")
            db_rule = models.Rule(
                device_id=device_uuid,
                rule_type=item.type,
                target=target,
                is_banned=is_banned,
                daily_limit_minutes=item.daily_limit_minutes if item.mode == "limit" else None
            )
            db.add(db_rule)

        await db.commit()
    except Exception as e:
        await db.rollback()
        return schemas.StandardResponse(error=f"Lỗi khi lưu quy tắc: {str(e)}", status_code=500)

    # Push to agent
    device_id_str = str(device_uuid)
    all_rules = (await db.execute(select(models.Rule).where(models.Rule.device_id == device_uuid))).scalars().all()
    rules_list = [schemas.RuleResponse.model_validate(r).model_dump(mode="json") for r in all_rules]
    if manager.is_online(device_id_str):
        await manager.send_command(device_id_str, {"type": "command", "command": "refresh_rules", "payload": {"rules": rules_list}})

    return schemas.StandardResponse(data={"msg": "Đã lưu danh sách giới hạn thành công", "rules": rules_list}, status_code=200)

print('LOADING RULES.PY END!')
