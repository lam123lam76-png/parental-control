import os
import time
import shutil
import json
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text, cast, String
from datetime import datetime, timezone, timedelta
from pathlib import Path

from database import get_db, SessionLocal
import models
import schemas
from core.security import verify_api_key, require_system_admin
from core.config import SCREENSHOTS_DIR, UPDATES_DIR, TRASH_DIR, TRASH_SHOTS_DIR, TRASH_RECORDS_DIR

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"], dependencies=[Depends(verify_api_key)])


def purge_old_trash(retention_days: int = 7):
    """Permanently purges files inside storage/trash older than retention_days (default 7 days)."""
    try:
        now = time.time()
        cutoff = now - (retention_days * 86400)
        purged_count = 0
        for item in TRASH_DIR.glob("**/*"):
            if item.is_file() and item.stat().st_mtime < cutoff:
                try:
                    item.unlink()
                    purged_count += 1
                except Exception as e:
                    logger.warning(f"Could not purge old trash file {item}: {e}")
        if purged_count > 0:
            logger.info(f"[RecycleBin] Purged {purged_count} trash items older than {retention_days} days.")
    except Exception as e:
        logger.error(f"[RecycleBin] Error purging old trash: {e}")


@router.get("/api/v1/system/storage", response_model=schemas.StandardResponse)
def get_storage_metrics(db: Session = Depends(get_db)):
    """Returns disk usage, DB size, screenshot storage metrics, and log counts."""
    try:
        total, used, free = shutil.disk_usage("E:\\")
    except Exception as e:
        logger.error(f"Failed to get disk usage for E: : {e}")
        total, used, free = shutil.disk_usage(Path(__file__).parent)
    used_percent = round((used / total) * 100, 1)

    db_file_path = Path(__file__).parent.parent.parent / "parental_control.db"
    if not db_file_path.exists():
        db_file_path = Path(__file__).parent.parent / "parental_control.db"
    db_size_bytes = db_file_path.stat().st_size if db_file_path.exists() else 0
    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

    shots_count = 0
    shots_bytes = 0
    if SCREENSHOTS_DIR.exists():
        for file in SCREENSHOTS_DIR.glob("**/*"):
            if file.is_file():
                shots_count += 1
                shots_bytes += file.stat().st_size
    shots_mb = round(shots_bytes / (1024 * 1024), 2)

    web_count = db.query(models.BrowserHistory).count()
    alerts_count = db.query(models.Alert).count()
    processes_count = db.query(models.ProcessLog).count()

    metrics = {
        "disk": {
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "used_percent": used_percent
        },
        "db_size_mb": db_size_mb,
        "screenshots": {
            "count": shots_count,
            "total_mb": shots_mb
        },
        "web": {
            "count": web_count,
            "total_mb": round(web_count * 0.002, 2)
        },
        "logs": {
            "count": alerts_count,
            "total_mb": round(alerts_count * 0.001, 2)
        },
        "processes": {
            "count": processes_count,
            "total_mb": round(processes_count * 0.0015, 2)
        }
    }
    return schemas.StandardResponse(data=metrics, status_code=200)


def _matches_period(ts_dt, periods: list, period_type: str) -> bool:
    if not ts_dt:
        return False
    if hasattr(ts_dt, "tzinfo") and ts_dt.tzinfo is not None:
        ts_dt = ts_dt.replace(tzinfo=None)
    yyyy = ts_dt.year
    mm = f"{ts_dt.month:02d}"
    dd = f"{ts_dt.day:02d}"
    if period_type == "day":
        key = f"{yyyy}-{mm}-{dd}"
    elif period_type == "week":
        first_day = datetime(yyyy, 1, 1)
        past_days = (ts_dt - first_day).days
        week_num = int((past_days + first_day.weekday() + 1) / 7) + 1
        key = f"{yyyy}-W{week_num:02d}"
    elif period_type == "month":
        key = f"{yyyy}-{mm}"
    else:
        key = f"{yyyy}-{mm}-{dd}"
    return key in periods


@router.post("/api/v1/storage/cleanup-by-period", response_model=schemas.StandardResponse)
def cleanup_storage_by_period_endpoint(req: schemas.StoragePeriodCleanRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_bg_cleanup_storage_by_period, req)
    return schemas.StandardResponse(data={"msg": "Tiến trình dọn dẹp đang được chạy ngầm. Vui lòng kiểm tra lại sau ít phút.", "freed_mb": 0}, status_code=202)

def _bg_cleanup_storage_by_period(req: schemas.StoragePeriodCleanRequest):
    db = SessionLocal()
    try:
        """Deletes records and files for specific categories filtered by period ranges."""
        purge_old_trash(retention_days=7)
        
        freed_bytes = 0
        deleted_counts = {"screenshots": 0, "web": 0, "logs": 0, "processes": 0}
        cat = req.category.lower()

        # 1. Clean Screenshots
        if cat in ("screenshots", "all"):
            query = db.query(models.Screenshot)
            if req.item_ids:
                query = query.filter(cast(models.Screenshot.id, String).in_(req.item_ids))
            all_shots = query.all()
            for shot in all_shots:
                if req.item_ids or _matches_period(shot.timestamp, req.periods, req.period_type):
                    filename = shot.image_url.split("/")[-1]
                    file_path = SCREENSHOTS_DIR / filename
                    if file_path.exists():
                        try:
                            sz = file_path.stat().st_size
                            freed_bytes += sz
                            trash_path = TRASH_SHOTS_DIR / filename
                            shutil.move(str(file_path), str(trash_path))
                        except Exception:
                            try:
                                file_path.unlink()
                            except Exception:
                                pass
                    db.delete(shot)
                    deleted_counts["screenshots"] += 1

        # 2. Clean Browser History
        if cat in ("web", "all"):
            query = db.query(models.BrowserHistory)
            if req.item_ids:
                query = query.filter(cast(models.BrowserHistory.id, String).in_(req.item_ids))
            all_web = query.all()
            for item in all_web:
                if req.item_ids or _matches_period(item.timestamp, req.periods, req.period_type):
                    db.delete(item)
                    deleted_counts["web"] += 1
                    freed_bytes += 2000

        # 3. Clean Alerts (Logs)
        if cat in ("logs", "all"):
            query = db.query(models.Alert)
            if req.item_ids:
                query = query.filter(cast(models.Alert.id, String).in_(req.item_ids))
            all_alerts = query.all()
            for item in all_alerts:
                if req.item_ids or _matches_period(item.created_at, req.periods, req.period_type):
                    db.delete(item)
                    deleted_counts["logs"] += 1
                    freed_bytes += 500

        # 4. Clean Process Logs
        if cat in ("processes", "all"):
            query = db.query(models.ProcessLog)
            if req.item_ids:
                query = query.filter(cast(models.ProcessLog.id, String).in_(req.item_ids))
            all_procs = query.all()
            for item in all_procs:
                if req.item_ids or _matches_period(item.timestamp, req.periods, req.period_type):
                    db.delete(item)
                    deleted_counts["processes"] += 1
                    freed_bytes += 1500

        db.commit()

        try:
            db.execute(text("VACUUM"))
            db.commit()
        except Exception:
            pass

    finally:
        db.close()


@router.post("/api/v1/system/storage/clean", response_model=schemas.StandardResponse)
def clean_system_storage_endpoint(req: schemas.StorageCleanRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_bg_clean_system_storage, req)
    return schemas.StandardResponse(data={"msg": "Tiến trình dọn dẹp đang được chạy ngầm. Vui lòng kiểm tra lại sau ít phút.", "freed_mb": 0}, status_code=202)

def _bg_clean_system_storage(req: schemas.StorageCleanRequest):
    db = SessionLocal()
    try:
        """Clean all screenshots and logs older than days (or all if days_older_than == 0)."""
        freed_bytes = 0
        deleted_counts = {"screenshots": 0, "web": 0, "logs": 0, "processes": 0}
        target = req.target.lower()
        
        cutoff = None
        if req.days_older_than > 0:
            cutoff = datetime.now() - timedelta(days=req.days_older_than)

        # 1. Screenshots
        if target in ("screenshots", "all"):
            query = db.query(models.Screenshot)
            if cutoff:
                query = query.filter(models.Screenshot.timestamp < cutoff)
            shots = query.all()
            for shot in shots:
                filename = shot.image_url.split("/")[-1]
                file_path = SCREENSHOTS_DIR / filename
                if file_path.exists():
                    try:
                        freed_bytes += file_path.stat().st_size
                        file_path.unlink()
                    except Exception:
                        pass
                db.delete(shot)
                deleted_counts["screenshots"] += 1

        # 2. Browser History
        if target in ("web", "all"):
            query = db.query(models.BrowserHistory)
            if cutoff:
                query = query.filter(models.BrowserHistory.timestamp < cutoff)
            items = query.all()
            for item in items:
                db.delete(item)
                deleted_counts["web"] += 1
                freed_bytes += 2000

        # 3. Alerts
        if target in ("logs", "all"):
            query = db.query(models.Alert)
            if cutoff:
                query = query.filter(models.Alert.created_at < cutoff)
            items = query.all()
            for item in items:
                db.delete(item)
                deleted_counts["logs"] += 1
                freed_bytes += 1000

        # 4. Process Logs
        if target in ("processes", "all"):
            query = db.query(models.ProcessLog)
            if cutoff:
                query = query.filter(models.ProcessLog.timestamp < cutoff)
            items = query.all()
            for item in items:
                db.delete(item)
                deleted_counts["processes"] += 1
                freed_bytes += 1500

        db.commit()

        try:
            db.execute(text("VACUUM"))
            db.commit()
        except Exception:
            pass

    finally:
        db.close()


@router.post("/api/v1/agent/deploy-update", response_model=schemas.StandardResponse)
async def deploy_agent_update(version: str = Form(...), file: UploadFile = File(...)):
    """Upload new Agent release."""
    save_path = UPDATES_DIR / "agent-update.zip"
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    version_data = {
        "version": version,
        "download_url": "/static/updates/agent-update.zip",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    with open(UPDATES_DIR / "version.json", "w", encoding="utf-8") as vf:
        json.dump(version_data, vf, indent=2)
    return schemas.StandardResponse(data=version_data, status_code=200)


import threading
import asyncio
pack_zip_lock = threading.Lock()

def _sync_pack_agent_zip(version: str):
    from core.config import PROJECT_ROOT, UPDATES_DIR
    import zipfile
    import os
    from datetime import datetime, timezone
    import json

    agent_dir = PROJECT_ROOT.parent / "agent"
    if not agent_dir.exists():
        return schemas.StandardResponse(error="Agent directory not found", status_code=500)

    zip_path = UPDATES_DIR / "agent-update.zip"

    with pack_zip_lock:
        try:
            dist_dir = agent_dir / "dist"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                agent_exe = dist_dir / "ParentalControlAgent.exe"
                updater_exe = dist_dir / "Updater.exe"
                watchdog_exe = dist_dir / "ParentalControlWatchdog.exe"
                checker_exe = dist_dir / "Agent_check_good.exe"
                
                if agent_exe.exists():
                    zipf.write(agent_exe, arcname="ParentalControlAgent.exe")
                else:
                    return schemas.StandardResponse(
                        error=f"ParentalControlAgent.exe not found at {agent_exe}",
                        status_code=400
                    )
                    
                if updater_exe.exists():
                    zipf.write(updater_exe, arcname="Updater.exe")
                else:
                    return schemas.StandardResponse(
                        error=f"Updater.exe not found at {updater_exe}",
                        status_code=400
                    )

                if watchdog_exe.exists():
                    zipf.write(watchdog_exe, arcname="ParentalControlWatchdog.exe")

                if checker_exe.exists():
                    zipf.write(checker_exe, arcname="Agent_check_good.exe")

            # Update version.json
            version_data = {
                "version": version,
                "download_url": "/static/updates/agent-update.zip",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            with open(UPDATES_DIR / "version.json", "w", encoding="utf-8") as vf:
                json.dump(version_data, vf, indent=2)
                
            return schemas.StandardResponse(data={"msg": f"Packed successfully as version {version}"}, status_code=200)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return schemas.StandardResponse(error=f"Failed to pack zip: {str(e)}", status_code=500)

@router.post("/api/v1/agent/pack-zip", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
async def pack_agent_zip(version: str = Form(...)):
    """Packs agent source files async without blocking the event loop."""
    return await asyncio.to_thread(_sync_pack_agent_zip, version)


@router.get("/api/v1/agent/version", response_model=schemas.StandardResponse)
def get_latest_agent_version():
    """Returns current published Agent version information."""
    version_json_path = UPDATES_DIR / "version.json"
    if not version_json_path.exists():
        return schemas.StandardResponse(
            data={"version": "v0001", "download_url": "/static/updates/agent-update.zip"},
            status_code=200
        )
    with open(version_json_path, "r", encoding="utf-8") as vf:
        vdata = json.load(vf)
    return schemas.StandardResponse(data=vdata, status_code=200)

from pydantic import BaseModel
from typing import List, Optional

class DiagnosticCheck(BaseModel):
    name: str
    status: str
    detail: Optional[str] = None

class DiagnosticReport(BaseModel):
    device_name: str
    test_timestamp: str
    checks: List[DiagnosticCheck]

@router.post("/api/diagnostics/report", response_model=schemas.StandardResponse)
def receive_diagnostic_report(report: DiagnosticReport):
    """Receive diagnostic test results from Agent."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=== DIAGNOSTIC REPORT RECEIVED ===")
    logger.info(f"Device: {report.device_name}")
    logger.info(f"Time: {report.test_timestamp}")
    for check in report.checks:
        logger.info(f" - [{check.status}] {check.name}: {check.detail}")
    logger.info("==================================")
    return schemas.StandardResponse(data={"msg": "Report received"}, status_code=200)

@router.get("/api/telegram/config", response_model=schemas.StandardResponse)
def get_telegram_config(db: Session = Depends(get_db)):
    t_setting = db.query(models.TelegramSetting).first()
    bot_token = t_setting.bot_token if (t_setting and t_setting.bot_token) else "8838573041:AAFhpXyKVZib1_Y0wv29At1JlkiC1F-V-w4"
    chat_id = t_setting.chat_id if (t_setting and t_setting.chat_id) else "1326412172"
    return schemas.StandardResponse(data={"bot_token": bot_token, "chat_id": chat_id}, status_code=200)

@router.post("/api/telegram/config", response_model=schemas.StandardResponse)
def save_telegram_config(req: schemas.TelegramConfigRequest, db: Session = Depends(get_db)):
    t_setting = db.query(models.TelegramSetting).first()
    if not t_setting:
        t_setting = models.TelegramSetting(bot_token=req.bot_token, chat_id=req.chat_id)
        db.add(t_setting)
    else:
        t_setting.bot_token = req.bot_token
        t_setting.chat_id = req.chat_id
        t_setting.updated_at = datetime.now(timezone.utc)
    db.commit()
    return schemas.StandardResponse(data={"msg": "Đã lưu cấu hình Telegram thành công!"}, status_code=200)

import requests as http_requests
@router.post("/api/telegram/test", response_model=schemas.StandardResponse)
def test_telegram_notification(req: schemas.TelegramConfigRequest, db: Session = Depends(get_db)):
    url = f"https://api.telegram.org/bot{req.bot_token}/sendMessage"
    payload = {
        "chat_id": req.chat_id,
        "text": "🔔 <b>[Parental Control]</b> Thử nghiệm kết nối Telegram Bot thành công!",
        "parse_mode": "HTML"
    }
    try:
        res = http_requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            save_telegram_config(req, db)
            return schemas.StandardResponse(data={"msg": "Gửi thông báo thành công!"}, status_code=200)
    except Exception as e:
        return schemas.StandardResponse(error=f"Không thể kết nối Telegram: {e}", status_code=500)


# ============================================================================
# PERIOD SETTINGS (CÀI ĐẶT CHU KỲ HOẠT ĐỘNG)
# ============================================================================
@router.get("/api/settings/periods", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
def get_period_settings(db: Session = Depends(get_db)):
    """Fetch period settings (screenshot interval, heartbeat interval, log batch interval)."""
    screenshot_setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "screenshot_interval_seconds").first()
    heartbeat_setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "heartbeat_interval_seconds").first()
    log_batch_setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "log_batch_interval_seconds").first()

    data = {
        "screenshot_interval_seconds": int(screenshot_setting.value) if screenshot_setting else 60,
        "heartbeat_interval_seconds": int(heartbeat_setting.value) if heartbeat_setting else 15,
        "log_batch_interval_seconds": int(log_batch_setting.value) if log_batch_setting else 300,
    }
    return schemas.StandardResponse(data=data, status_code=200)


@router.put("/api/settings/periods", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
async def update_period_settings(req: schemas.PeriodSettingsRequest, db: Session = Depends(get_db)):
    """Update period settings and optionally push updated interval config to agent."""
    def _upsert_setting(k: str, v: str):
        row = db.query(models.SystemSetting).filter(models.SystemSetting.key == k).first()
        if not row:
            row = models.SystemSetting(key=k, value=str(v))
            db.add(row)
        else:
            row.value = str(v)

    if req.screenshot_interval_seconds is not None:
        _upsert_setting("screenshot_interval_seconds", str(req.screenshot_interval_seconds))
    if req.heartbeat_interval_seconds is not None:
        _upsert_setting("heartbeat_interval_seconds", str(req.heartbeat_interval_seconds))
    if req.log_batch_interval_seconds is not None:
        _upsert_setting("log_batch_interval_seconds", str(req.log_batch_interval_seconds))

    db.commit()

    # Push config command to ALL online devices since this is a global setting
    from core.manager import manager
    cmd_payload = {
        "type": "command",
        "command": "update_period_intervals",
        "payload": {
            "screenshot_interval_seconds": req.screenshot_interval_seconds,
            "heartbeat_interval_seconds": req.heartbeat_interval_seconds,
            "log_batch_interval_seconds": req.log_batch_interval_seconds,
        }
    }
    for active_device_id in list(manager.active_connections.keys()):
        await manager.send_command(active_device_id, cmd_payload)

    return schemas.StandardResponse(
        data={"msg": "Đã lưu cài đặt chu kỳ thành công và áp dụng cho toàn bộ thiết bị trực tuyến!"},
        status_code=200
    )

