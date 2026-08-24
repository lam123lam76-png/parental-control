from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from database import get_db
import models
import schemas
from core.security import verify_api_key, require_permission
from passlib.context import CryptContext

router = APIRouter(tags=["users"], dependencies=[Depends(require_permission("can_manage_users"))])
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

@router.post("/api/v1/users", response_model=schemas.StandardResponse)
def create_sub_account(req: schemas.UserCreate, db: Session = Depends(get_db)):
    """Admin creates/invites a new sub-account (Bố, Mẹ, Anh/Chị...)."""
    existing = db.query(models.User).filter(models.User.email == req.email).first()
    if existing:
        return schemas.StandardResponse(error="Email đã được đăng ký", status_code=409)

    owner_id = None
    if req.admin_email:
        admin_user = db.query(models.User).filter(models.User.email == req.admin_email).first()
        if admin_user:
            owner_id = admin_user.id

    new_user = models.User(
        email=req.email,
        password_hash=pwd_context.hash(req.password),
        role=req.role or "sub_account",
        owner_id=owner_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Assign permissions
    p_req = req.permissions or schemas.PermissionSchema()
    perm = models.UserPermission(
        user_id=new_user.id,
        can_view_screenshots=p_req.can_view_screenshots,
        can_manage_rules=p_req.can_manage_rules,
        can_view_logs=p_req.can_view_logs,
        can_remote_control=p_req.can_remote_control,
        can_manage_users=False
    )
    db.add(perm)
    db.commit()

    perm_data = {
        "can_view_screenshots": perm.can_view_screenshots,
        "can_manage_rules": perm.can_manage_rules,
        "can_view_logs": perm.can_view_logs,
        "can_remote_control": perm.can_remote_control,
        "can_manage_users": perm.can_manage_users
    }

    return schemas.StandardResponse(
        data={
            "user_id": str(new_user.id),
            "email": new_user.email,
            "role": new_user.role,
            "permissions": perm_data
        },
        status_code=201
    )


@router.get("/api/v1/users", response_model=schemas.StandardResponse)
def get_sub_accounts(admin_email: Optional[str] = None, db: Session = Depends(get_db)):
    """Fetch sub-accounts under admin or all accounts."""
    query = db.query(models.User)
    if admin_email:
        admin_user = db.query(models.User).filter(models.User.email == admin_email).first()
        if admin_user:
            query = query.filter(models.User.owner_id == admin_user.id)

    users = query.all()
    user_list = []
    for u in users:
        perm = db.query(models.UserPermission).filter(models.UserPermission.user_id == u.id).first()
        perm_data = {
            "can_view_screenshots": perm.can_view_screenshots if perm else True,
            "can_manage_rules": perm.can_manage_rules if perm else True,
            "can_view_logs": perm.can_view_logs if perm else True,
            "can_remote_control": perm.can_remote_control if perm else True,
            "can_manage_users": perm.can_manage_users if perm else (u.role == "admin")
        }
        user_list.append({
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "owner_id": str(u.owner_id) if u.owner_id else None,
            "permissions": perm_data,
            "created_at": str(u.created_at) if u.created_at else None
        })

    return schemas.StandardResponse(data={"users": user_list}, status_code=200)


@router.put("/api/v1/users/{user_id}/permissions", response_model=schemas.StandardResponse)
def update_user_permissions(user_id: str, req: schemas.PermissionUpdate, db: Session = Depends(get_db)):
    """Update granular permissions for a sub-account."""
    perm = db.query(models.UserPermission).filter(models.UserPermission.user_id == uuid.UUID(user_id)).first()
    if not perm:
        perm = models.UserPermission(user_id=uuid.UUID(user_id))
        db.add(perm)

    p = req.permissions
    perm.can_view_screenshots = p.can_view_screenshots
    perm.can_manage_rules = p.can_manage_rules
    perm.can_view_logs = p.can_view_logs
    perm.can_remote_control = p.can_remote_control
    perm.can_manage_users = p.can_manage_users
    db.commit()

    return schemas.StandardResponse(
        data={
            "user_id": user_id,
            "permissions": {
                "can_view_screenshots": perm.can_view_screenshots,
                "can_manage_rules": perm.can_manage_rules,
                "can_view_logs": perm.can_view_logs,
                "can_remote_control": perm.can_remote_control,
                "can_manage_users": perm.can_manage_users
            }
        },
        status_code=200
    )


@router.delete("/api/v1/users/{user_id}", response_model=schemas.StandardResponse)
def delete_sub_account(user_id: str, db: Session = Depends(get_db)):
    """Delete a sub-account."""
    user = db.query(models.User).filter(models.User.id == uuid.UUID(user_id)).first()
    if not user:
        return schemas.StandardResponse(error="Tài khoản không tồn tại", status_code=404)

    db.delete(user)
    db.commit()
    return schemas.StandardResponse(data={"msg": "Đã xóa tài khoản"}, status_code=200)
