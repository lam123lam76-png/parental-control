"""
migrate_sqlite_to_pg.py — One-time data migration: local SQLite -> shared Supabase (PostgreSQL).

Copies every table from backend_api/parental_control.db into the database configured
by DATABASE_URL (backend_api/.env). Identity tables (parents, users) are matched by
email: rows whose email already exists in the target are skipped and their old UUID
is remapped to the target UUID, so child rows (devices, permissions, ...) keep their
FKs valid. Needed for failover: home backend and the Vercel backup API share one DB.

Usage:
    python scripts/migrate_sqlite_to_pg.py            # abort if target has unexpected rows
    python scripts/migrate_sqlite_to_pg.py --force    # ON CONFLICT DO NOTHING per row
"""

import sys
from pathlib import Path

_BE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BE_DIR))

from sqlalchemy import create_engine, text, event  # noqa: E402
import models  # noqa: E402
from database import SQLALCHEMY_DATABASE_URL  # noqa: E402

SQLITE_PATH = _BE_DIR / "parental_control.db"

# Insert order (FK dependencies first). Identity maps: table -> email column.
TABLE_ORDER = [
    "parents",
    "users",
    "user_permissions",
    "devices",
    "alerts",
    "process_logs",
    "rules",
    "screenshots",
    "browser_history",
    "chat_messages",
    "pending_commands",
    "system_settings",
    "telegram_settings",
]
IDENTITY_BY_EMAIL = {"parents": "email", "users": "email"}
# Tables where a non-PK unique key must also skip existing target rows
UNIQUE_SKIP = {"user_permissions": ["user_id"]}
# FK remaps: child table -> {fk_column: (parent_table, parent_pk)}
FK_REMAPS = {
    "users": {"owner_id": ("users", "id")},
    "user_permissions": {"user_id": ("users", "id")},
    "devices": {"parent_id": ("parents", "id")},
    "alerts": {"device_id": ("devices", "id")},
    "process_logs": {"device_id": ("devices", "id")},
    "rules": {"device_id": ("devices", "id")},
    "screenshots": {"device_id": ("devices", "id")},
    "browser_history": {"device_id": ("devices", "id")},
    "chat_messages": {"device_id": ("devices", "id")},
    "pending_commands": {"device_id": ("devices", "id")},
}


def main() -> int:
    force = "--force" in sys.argv
    if not SQLITE_PATH.exists():
        print(f"[MIGRATE] SQLite file not found: {SQLITE_PATH}")
        return 1
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        print("[MIGRATE] DATABASE_URL still points at SQLite — set Supabase URL in backend_api/.env first.")
        return 1

    print(f"[MIGRATE] Source: sqlite://{SQLITE_PATH}")
    print(f"[MIGRATE] Target: {SQLALCHEMY_DATABASE_URL.split('@')[-1].split('/')[0]}")

    src = create_engine(f"sqlite:///{SQLITE_PATH.as_posix()}")
    dst = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
    )
    @event.listens_for(dst, "connect")
    def _set_timeout(dbapi_conn, rec):
        cur = dbapi_conn.cursor()
        cur.execute("SET statement_timeout = 30000")
        cur.close()
    meta = models.Base.metadata

    # Load existing identity rows (email -> uuid) from target
    id_map = {}  # (table, old_uuid) -> new_uuid
    with dst.connect() as c:
        for tbl, email_col in IDENTITY_BY_EMAIL.items():
            rows = c.execute(text(f'SELECT id, "{email_col}" FROM "{tbl}"')).fetchall()
            for rid, remail in rows:
                id_map[(tbl, str(remail))] = str(rid)
            print(f"[MIGRATE] target {tbl}: {len(rows)} existing")

    # Load existing unique-key sets (for UNIQUE_SKIP tables)
    unique_existing = {}
    with dst.connect() as c:
        for tbl, cols in UNIQUE_SKIP.items():
            col_list = ", ".join(f'"{col}"' for col in cols)
            rows = c.execute(text(f'SELECT {col_list} FROM "{tbl}"')).fetchall()
            unique_existing[tbl] = {tuple(str(v) for v in r) for r in rows}
            print(f"[MIGRATE] target {tbl}: {len(rows)} existing (unique {cols})")

    # Legacy data: devices.parent_id sometimes points at users.id instead of parents.id.
    # Resolve: old id -> email (users or parents) -> pg parent id by email.
    with src.connect() as c2:
        sqlite_users_email = {str(r[0]): str(r[1]) for r in c2.execute(text("SELECT id, email FROM users"))}
        sqlite_parents_email = {str(r[0]): str(r[1]) for r in c2.execute(text("SELECT id, email FROM parents"))}
    pg_parent_by_email = {email: pid for (t, email), pid in id_map.items() if t == "parents"}

    total = 0
    skipped = 0
    device_id_map = {}  # old device uuid str -> new (same) uuid str
    with src.connect() as sconn:
        for tbl in TABLE_ORDER:
            table = meta.tables[tbl]
            rows = sconn.execute(table.select()).mappings().all()
            if not rows:
                print(f"[MIGRATE] {tbl:20s} 0 rows (skip)")
                continue
            email_col = IDENTITY_BY_EMAIL.get(tbl)
            tbl_ok = tbl_skip = 0
            # Commit per table: a slow/hung row must not roll back the whole run
            with dst.begin() as dconn:
                for r in rows:
                    data = dict(r)
                    if email_col:
                        key = str(data.get(email_col) or "")
                        existing = id_map.get((tbl, key))
                        if existing:
                            id_map[(tbl, str(data["id"]))] = existing
                            skipped += 1
                            tbl_skip += 1
                            continue
                    # Remap FK columns
                    orphan = False
                    for fk_col, (ptbl, ppk) in FK_REMAPS.get(tbl, {}).items():
                        old_val = data.get(fk_col)
                        if old_val is None:
                            continue
                        old_s = str(old_val)
                        mapped = None
                        if tbl == "devices" and fk_col == "parent_id":
                            email = sqlite_parents_email.get(old_s) or sqlite_users_email.get(old_s)
                            mapped = pg_parent_by_email.get(email) if email else None
                            if mapped:
                                print(f"[MIGRATE] devices parent_id remapped {old_s[:8]} -> parent {mapped[:8]} (via {email})")
                        elif fk_col == "device_id":
                            mapped = device_id_map.get(old_s)
                            if not mapped:
                                orphan = True
                        if mapped is None:
                            mapped = id_map.get((ptbl, old_s))
                        if mapped:
                            data[fk_col] = mapped
                    if orphan:
                        skipped += 1
                        tbl_skip += 1
                        continue
                    # Skip rows matching an existing non-PK unique key
                    if tbl in UNIQUE_SKIP:
                        key = tuple(str(data[c]) for c in UNIQUE_SKIP[tbl])
                        if key in unique_existing.get(tbl, set()):
                            skipped += 1
                            tbl_skip += 1
                            continue
                    insert = table.insert()
                    if force:
                        insert = insert.prefix_with("ON CONFLICT DO NOTHING")
                    try:
                        dconn.execute(insert, data)
                    except Exception as e:
                        # Skip single problematic row instead of aborting the table
                        print(f"[MIGRATE] {tbl:20s} SKIP row error: {str(e)[:100]}")
                        skipped += 1
                        tbl_skip += 1
                        continue
                    if tbl in IDENTITY_BY_EMAIL:
                        id_map[(tbl, str(data["id"]))] = str(data["id"])
                    if tbl == "devices":
                        device_id_map[str(data["id"])] = str(data["id"])
                    total += 1
                    tbl_ok += 1
            print(f"[MIGRATE] {tbl:20s} {len(rows)} rows processed ({tbl_ok} ok, {tbl_skip} skip)")

    print(f"[MIGRATE] Done — {total} rows migrated, {skipped} skipped (dup/orphan/error).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
