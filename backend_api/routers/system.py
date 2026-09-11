import os
import time
import shutil
import json
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, cast, String, select
from datetime import datetime, timezone, timedelta
from pathlib import Path

from database import get_db, get_db_async, SessionLocal
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
    """Returns cloud storage metrics.

    The system is CLOUD-FIRST (no self-host): screenshots live in Supabase Storage,
    records live in Supabase Postgres. There is no local disk to report, so the
    "disk" block is removed and screenshot usage is read from Supabase Storage.
    """
    # Screenshots: read from Supabase Storage (cloud), not a local folder.
    shots_count = 0
    shots_bytes = 0
    try:
        from core.supabase_storage import list_files
        files = list_files()
        shots_count = len(files)
        shots_bytes = sum(sz for _, sz in files)
    except Exception as e:
        logger.warning(f"Could not read Supabase screenshot storage: {e}")
    shots_mb = round(shots_bytes / (1024 * 1024), 2)

    web_count = db.query(models.BrowserHistory).count()
    alerts_count = db.query(models.Alert).count()
    processes_count = db.query(models.ProcessLog).count()

    metrics = {
        # Cloud storage — no local disk. Report screenshots usage as the driver.
        "storage": "cloud",
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


@router.post("/api/v1/storage/cleanup-by-period", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
def cleanup_storage_by_period_endpoint(req: schemas.StoragePeriodCleanRequest):
    """Delete records + cloud files for the selected category/periods synchronously.

    Runs INLINE (not BackgroundTasks): on Vercel serverless the function is frozen
    as soon as the response is returned, so a background task was frequently killed
    before doing the work — the UI saw "đang chạy ngầm" forever and nothing was
    deleted. Cloud objects are removed with a batched Supabase call, so the whole
    operation is a handful of round-trips and fits the request budget.
    """
    try:
        result = _bg_cleanup_storage_by_period(req)
    except Exception as e:
        logger.error(f"cleanup-by-period failed: {e}", exc_info=True)
        return schemas.StandardResponse(error=f"Dọn dẹp thất bại: {e}", status_code=500)
    deleted = (result or {}).get("deleted_counts", {})
    freed_mb = round((result or {}).get("freed_bytes", 0) / (1024 * 1024), 2)
    total = sum(deleted.values()) if deleted else 0
    orphans = (result or {}).get("orphans_purged", 0)
    msg = f"Đã dọn dẹp {total} mục. Giải phóng ~{freed_mb} MB."
    if orphans:
        msg += f" (gồm {orphans} ảnh mồ côi trên cloud)"
    return schemas.StandardResponse(
        data={
            "msg": msg,
            "deleted_counts": deleted,
            "freed_mb": freed_mb,
            "orphans_purged": orphans,
        },
        status_code=200,
    )

def _bg_cleanup_storage_by_period(req: schemas.StoragePeriodCleanRequest):
    db = SessionLocal()
    try:
        """Deletes records and files for specific categories filtered by period ranges."""
        purge_old_trash(retention_days=7)
        
        freed_bytes = 0
        deleted_counts = {"screenshots": 0, "web": 0, "logs": 0, "processes": 0}
        deleted_cloud = 0
        orphan_count = 0
        cat = req.category.lower()

        # 1. Clean Screenshots
        if cat in ("screenshots", "all"):
            from core.supabase_storage import delete_files, list_files, _filename_from_url
            query = db.query(models.Screenshot)
            if req.item_ids:
                query = query.filter(cast(models.Screenshot.id, String).in_(req.item_ids))
            all_shots = query.all()
            to_delete_cloud = []
            for shot in all_shots:
                if req.item_ids or _matches_period(shot.timestamp, req.periods, req.period_type):
                    to_delete_cloud.append(_filename_from_url(shot.image_url or ""))
                    db.delete(shot)
                    deleted_counts["screenshots"] += 1

            # Commit the DB deletions FIRST (release the connection) before doing any
            # network I/O against Supabase Storage — holding an open transaction while
            # waiting on HTTP is what made this endpoint hang/time out on serverless.
            db.commit()

            # When the parent clears SCREENSHOTS by period (no explicit item selection),
            # also purge ORPHANED bucket objects that have no DB row — otherwise leftover
            # bytes keep occupying the bucket (observed: 179 objects / 75 MB with an
            # empty screenshots table); the DB-driven UI can never select them.
            if cat == "screenshots" and not req.item_ids:
                try:
                    referenced = {
                        _filename_from_url(u)
                        for (u,) in db.query(models.Screenshot.image_url).all()
                        if u
                    }
                    db.commit()  # end the transaction -> don't hold the connection during HTTP I/O
                    pending = set(to_delete_cloud)
                    for name, _size in list_files():
                        if name and name not in referenced and name not in pending:
                            to_delete_cloud.append(name)
                            orphan_count += 1
                except Exception as e:
                    logger.warning(f"Orphan storage scan failed: {e}")

            # Batch-delete the cloud objects (one HTTP call per 100 objects).
            if to_delete_cloud:
                try:
                    deleted_cloud = delete_files(to_delete_cloud)
                except Exception as e:
                    logger.warning(f"Supabase batch delete failed: {e}")
                freed_bytes += 100000 * len(to_delete_cloud)

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

        # NOTE: no VACUUM here. On Supabase's transaction-mode pooler (port 6543)
        # VACUUM cannot run inside a transaction and was closing the SSL connection
        # ("SSL connection has been closed unexpectedly"), which surfaced as failures
        # across unrelated requests. Postgres autovacuum handles reclaiming space.

        return {
            "deleted_counts": deleted_counts,
            "freed_bytes": freed_bytes,
            "cloud_deleted": deleted_cloud,
            "orphans_purged": orphan_count,
        }

    finally:
        db.close()


@router.post("/api/v1/system/storage/clean", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
def clean_system_storage_endpoint(req: schemas.StorageCleanRequest):
    """Clean storage synchronously (see cleanup-by-period: BackgroundTasks are
    unreliable on Vercel serverless because the function freezes on response)."""
    try:
        result = _bg_clean_system_storage(req)
    except Exception as e:
        logger.error(f"storage/clean failed: {e}", exc_info=True)
        return schemas.StandardResponse(error=f"Dọn dẹp thất bại: {e}", status_code=500)
    deleted = (result or {}).get("deleted_counts", {})
    freed_mb = round((result or {}).get("freed_bytes", 0) / (1024 * 1024), 2)
    total = sum(deleted.values()) if deleted else 0
    return schemas.StandardResponse(
        data={
            "msg": f"Đã dọn dẹp {total} mục. Giải phóng ~{freed_mb} MB.",
            "deleted_counts": deleted,
            "freed_mb": freed_mb,
        },
        status_code=200,
    )

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

        # 1. Screenshots (cloud-first: file lives in Supabase Storage)
        if target in ("screenshots", "all"):
            from core.supabase_storage import delete_files, _filename_from_url
            query = db.query(models.Screenshot)
            if cutoff:
                query = query.filter(models.Screenshot.timestamp < cutoff)
            shots = query.all()
            cloud_names = [_filename_from_url(s.image_url or "") for s in shots]
            for shot in shots:
                db.delete(shot)
                deleted_counts["screenshots"] += 1
                freed_bytes += 100000  # approximate per-shot storage freed
            # Commit DB first, then delete cloud objects in one batched call.
            db.commit()
            if cloud_names:
                try:
                    delete_files(cloud_names)  # batch: 1 HTTP call per 100 objects
                except Exception as e:
                    logger.warning(f"Supabase batch delete failed: {e}")

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

        # No VACUUM — see the note in _bg_cleanup_storage_by_period: it breaks the
        # Supabase transaction-mode pooler connection.

        return {"deleted_counts": deleted_counts, "freed_bytes": freed_bytes}

    finally:
        db.close()


@router.post("/api/v1/agent/deploy-update", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
async def deploy_agent_update(version: str = Form(...), file: UploadFile = File(...)):
    """Upload new Agent release.

    SECURITY: previously unauthenticated — anyone on the Internet could upload an
    arbitrary agent-update.zip that every child's agent would auto-download and
    run as Admin (RCE / supply-chain attack). Now restricted to system admins.
    """
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

@router.post("/api/telegram/config", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
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
@router.post("/api/telegram/test", response_model=schemas.StandardResponse, dependencies=[Depends(require_system_admin)])
def test_telegram_notification(req: schemas.TelegramConfigRequest, db: Session = Depends(get_db)):
    url = f"https://api.telegram.org/bot{req.bot_token}/sendMessage"
    
    chat_ids = [cid.strip() for cid in req.chat_id.split(",") if cid.strip()]
    if not chat_ids:
        return schemas.StandardResponse(error="Vui lòng nhập Chat ID hợp lệ.", status_code=400)
    
    errors = []
    success_count = 0
    try:
        for cid in chat_ids:
            payload = {
                "chat_id": cid,
                "text": "🔔 <b>[Parental Control]</b> Thử nghiệm kết nối Telegram Bot thành công!",
                "parse_mode": "HTML"
            }
            res = http_requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                success_count += 1
            else:
                errors.append(f"{cid}: {res.text}")
                
        if success_count > 0:
            save_telegram_config(req, db)
            msg = "Gửi thông báo thành công!" if len(errors) == 0 else f"Gửi thành công {success_count} ID, một số lỗi: {errors}"
            return schemas.StandardResponse(data={"msg": msg}, status_code=200)
        else:
            return schemas.StandardResponse(error=f"Tất cả đều thất bại: {errors}", status_code=500)
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
async def update_period_settings(req: schemas.PeriodSettingsRequest, db: AsyncSession = Depends(get_db_async)):
    """Update period settings and optionally push updated interval config to agent."""
    async def _upsert_setting(k: str, v: str):
        row = (await db.execute(select(models.SystemSetting).where(models.SystemSetting.key == k))).scalars().first()
        if not row:
            row = models.SystemSetting(key=k, value=str(v))
            db.add(row)
        else:
            row.value = str(v)

    if req.screenshot_interval_seconds is not None:
        await _upsert_setting("screenshot_interval_seconds", str(req.screenshot_interval_seconds))
    if req.heartbeat_interval_seconds is not None:
        await _upsert_setting("heartbeat_interval_seconds", str(req.heartbeat_interval_seconds))
    if req.log_batch_interval_seconds is not None:
        await _upsert_setting("log_batch_interval_seconds", str(req.log_batch_interval_seconds))

    await db.commit()

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

