import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Date, DateTime
from sqlalchemy.orm import Session

from database import API_KEY, STORAGE_DIR, SessionLocal, init_db
from models import TABLE_MODELS
from schemas import APIResponse, QueryRequest, RPCRequest, StorageRemoveRequest

app = FastAPI(
    title="Parental Control Backend API",
    description="Self-hosted backend API that replaces Supabase for the Parental Control system.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


@app.on_event("startup")
def startup_event():
    init_db()
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> None:
    if not API_KEY:
        return

    header_value = x_api_key or authorization
    if not header_value:
        raise HTTPException(status_code=401, detail="Missing API key")

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        token = header_value

    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def normalize_path(path: str) -> Path:
    safe_parts = [part for part in Path(path).parts if part not in (".", "..")]
    return Path(*safe_parts)


def parse_comparison_value(column, value):
    if value is None:
        return None

    if isinstance(column.type, DateTime) and isinstance(value, str):
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date) and isinstance(value, str):
        return datetime.fromisoformat(value).date()
    return value


def build_filter(condition, model):
    column = getattr(model, condition.column, None)
    if column is None:
        raise HTTPException(status_code=400, detail=f"Unknown column: {condition.column}")

    value = parse_comparison_value(column, condition.value)
    op = condition.op.lower()
    if op == "eq":
        return column == value
    if op == "neq":
        return column != value
    if op == "lt":
        return column < value
    if op == "lte":
        return column <= value
    if op == "gt":
        return column > value
    if op == "gte":
        return column >= value
    if op == "in":
        if not isinstance(value, list):
            raise HTTPException(status_code=400, detail="Value for 'in' filter must be a list")
        return column.in_(value)
    raise HTTPException(status_code=400, detail=f"Unsupported filter operation: {condition.op}")


def row_to_dict(row: Any) -> Any:
    if hasattr(row, "to_dict"):
        return row.to_dict()
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def execute_query(db: Session, payload: QueryRequest) -> Any:
    model = TABLE_MODELS.get(payload.table)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown table: {payload.table}")

    filters = [build_filter(f, model) for f in (payload.filters or [])]
    query = db.query(model)
    if filters:
        query = query.filter(*filters)

    if payload.operation == "select":
        if payload.order:
            for order_spec in payload.order:
                order_column = getattr(model, order_spec.column, None)
                if order_column is None:
                    raise HTTPException(status_code=400, detail=f"Unknown order column: {order_spec.column}")
                query = query.order_by(order_column.asc() if order_spec.ascending else order_column.desc())
        if payload.limit is not None:
            query = query.limit(payload.limit)

        rows = query.all()
        data = [row_to_dict(row) for row in rows]
        if payload.maybe_single:
            return data[0] if data else None
        return data

    if payload.operation in {"insert", "upsert"}:
        if payload.data is None:
            raise HTTPException(status_code=400, detail="Missing data for insert/upsert")

        items = payload.data if isinstance(payload.data, list) else [payload.data]
        result_items = []

        for item in items:
            if not isinstance(item, dict):
                raise HTTPException(status_code=400, detail="Each insert item must be an object")

            existing = None
            if payload.operation == "upsert":
                if payload.on_conflict:
                    keys = [key.strip() for key in payload.on_conflict.split(",") if key.strip()]
                    conditions = []
                    for key in keys:
                        if key in item and hasattr(model, key):
                            conditions.append(getattr(model, key) == item[key])
                    if conditions:
                        existing = db.query(model).filter(*conditions).first()
                if existing is None and item.get("id"):
                    existing = db.query(model).filter(model.id == item["id"]).first()

            if payload.operation == "insert" or existing is None:
                obj = model(**item)
                db.add(obj)
                db.flush()
                result_items.append(obj)
            else:
                for key, value in item.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                result_items.append(existing)

        db.commit()
        output = [row_to_dict(row) for row in result_items]
        return output if isinstance(payload.data, list) else output[0]

    if payload.operation == "update":
        if payload.data is None:
            raise HTTPException(status_code=400, detail="Missing data for update")
        updated_count = query.update(payload.data, synchronize_session=False)
        db.commit()
        if updated_count:
            rows = query.all()
            return [row_to_dict(row) for row in rows]
        return []

    if payload.operation == "delete":
        deleted_count = query.delete(synchronize_session=False)
        db.commit()
        return {"deleted": deleted_count}

    raise HTTPException(status_code=400, detail=f"Unsupported operation: {payload.operation}")


@app.post("/api/query", response_model=APIResponse)
def query_endpoint(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    _api_key: None = Depends(verify_api_key),
) -> APIResponse:
    try:
        data = execute_query(db, payload)
        return APIResponse(data=data, error=None)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        return APIResponse(data=None, error=str(exc))


@app.post("/api/rpc/{procedure}", response_model=APIResponse)
def rpc_endpoint(
    procedure: str,
    payload: RPCRequest,
    db: Session = Depends(get_db),
    _api_key: None = Depends(verify_api_key),
) -> APIResponse:
    try:
        if procedure == "clean_old_logs":
            now = datetime.utcnow()
            active_deleted = db.query(TABLE_MODELS["active_window_logs"]).filter(
                TABLE_MODELS["active_window_logs"].created_at < now - timedelta(days=30)
            ).delete(synchronize_session=False)
            history_deleted = db.query(TABLE_MODELS["browser_history_logs"]).filter(
                TABLE_MODELS["browser_history_logs"].visit_time < now - timedelta(days=60)
            ).delete(synchronize_session=False)
            commands_deleted = db.query(TABLE_MODELS["system_commands"]).filter(
                TABLE_MODELS["system_commands"].status == "completed"
            ).filter(
                TABLE_MODELS["system_commands"].created_at < now - timedelta(days=7)
            ).delete(synchronize_session=False)
            events_deleted = db.query(TABLE_MODELS["system_events"]).filter(
                TABLE_MODELS["system_events"].created_at < now - timedelta(days=30)
            ).delete(synchronize_session=False)
            db.commit()
            return APIResponse(data={"deleted": {
                "active_window_logs": active_deleted,
                "browser_history_logs": history_deleted,
                "system_commands": commands_deleted,
                "system_events": events_deleted,
            }}, error=None)

        raise HTTPException(status_code=404, detail=f"Unknown RPC procedure '{procedure}'")
    except HTTPException:
        raise
    except Exception as exc:
        return APIResponse(data=None, error=str(exc))


@app.post("/api/storage/{bucket}/upload", response_model=APIResponse)
def storage_upload(
    bucket: str,
    path: str = Form(...),
    file: UploadFile = File(...),
    _api_key: None = Depends(verify_api_key),
) -> APIResponse:
    try:
        relative_path = normalize_path(path)
        target = STORAGE_DIR / bucket / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as buffer:
            buffer.write(file.file.read())
        return APIResponse(data={"path": str(relative_path).replace('\\', '/')}, error=None)
    except Exception as exc:
        return APIResponse(data=None, error=str(exc))


@app.get("/api/storage/{bucket}/download")
def storage_download(
    bucket: str,
    path: str,
    _api_key: None = Depends(verify_api_key),
):
    relative_path = normalize_path(path)
    target = STORAGE_DIR / bucket / relative_path
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target, media_type="application/octet-stream", filename=target.name)


@app.post("/api/storage/{bucket}/remove", response_model=APIResponse)
def storage_remove(
    bucket: str,
    payload: StorageRemoveRequest,
    _api_key: None = Depends(verify_api_key),
) -> APIResponse:
    removed = 0
    try:
        for path in payload.paths:
            relative_path = normalize_path(path)
            target = STORAGE_DIR / bucket / relative_path
            if target.exists() and target.is_file():
                target.unlink()
                removed += 1
        return APIResponse(data={"removed": removed}, error=None)
    except Exception as exc:
        return APIResponse(data=None, error=str(exc))


@app.get("/api/health", response_model=APIResponse)
def health_check() -> APIResponse:
    return APIResponse(data={"status": "ok"}, error=None)
