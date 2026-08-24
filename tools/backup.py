#!/usr/bin/env python3
"""
backup.py - Automated Backup Engine for Parental Control System
- Backs up SQLite or PostgreSQL database
- Compresses backend storage into a timestamped zip
- Enforces 7-day retention policy
"""

import os
import sys
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend_api"
STORAGE_DIR = BACKEND_DIR / "storage"
BACKUP_DEST_DIR = PROJECT_ROOT / "backups"

RETENTION_DAYS = 7


def run_backup():
    print("=" * 60)
    print("  PARENTAL CONTROL - TIEN TRINH SAO LUU TU DONG (BACKUP)")
    print(f"  Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    BACKUP_DEST_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_backup_dir = BACKUP_DEST_DIR / f"backup_{timestamp}"
    current_backup_dir.mkdir(parents=True, exist_ok=True)

    success_items = []

    # 1. Database Backup
    db_file = BACKEND_DIR / "parental_control.db"
    if db_file.exists():
        target_db = current_backup_dir / "parental_control.db"
        shutil.copy2(db_file, target_db)
        print(f"  [OK] Da sao luu SQLite Database: {db_file.name} ({db_file.stat().st_size / 1024:.1f} KB)")
        success_items.append("SQLite Database")
    else:
        print("  [INFO] Khong tim thay file SQLite cuc bo.")

    # 2. Storage Backup
    if STORAGE_DIR.exists():
        zip_path = current_backup_dir / "storage_backup.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in STORAGE_DIR.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(STORAGE_DIR)
                    zf.write(file, arcname)
        print(f"  [OK] Da nen va sao luu thu muc storage: {zip_path.name} ({zip_path.stat().st_size / 1024:.1f} KB)")
        success_items.append("Storage Media")

    # 3. Create Master Archive
    master_zip = BACKUP_DEST_DIR / f"parental_control_backup_{timestamp}.zip"
    with zipfile.ZipFile(master_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in current_backup_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(current_backup_dir))

    shutil.rmtree(current_backup_dir, ignore_errors=True)
    print(f"\n  [PACKAGE] Da tao file nen tong hop: {master_zip.name} ({master_zip.stat().st_size / 1024:.1f} KB)")

    # 4. Retention Policy
    cutoff_time = datetime.now() - timedelta(days=RETENTION_DAYS)
    for old_file in BACKUP_DEST_DIR.glob("parental_control_backup_*.zip"):
        if old_file.stat().st_mtime < cutoff_time.timestamp():
            try:
                old_file.unlink()
                print(f"  [CLEAN] Da xoa ban backup cu hon {RETENTION_DAYS} ngay: {old_file.name}")
            except Exception as e:
                print(f"  [WARN] Khong the xoa {old_file.name}: {e}")

    print("=" * 60)
    print(f"  HOAN TAT SAO LUU: {len(success_items)} thanh phan da luu tru an toan!")
    print(f"  Vi tri luu: {BACKUP_DEST_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    run_backup()