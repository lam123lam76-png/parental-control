from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
import uuid
import logging

from database import get_db
import models
import schemas
from core.config import SYSTEM_ADMIN_EMAIL, SYSTEM_ADMIN_PASSWORD
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

from core.security import create_access_token

@router.post("/api/register", response_model=schemas.StandardResponse)
def register_parent(request: schemas.ParentCreate, db: Session = Depends(get_db)):
    """
    Register a new parent admin account.
    """
    existing_parent = db.query(models.Parent).filter(models.Parent.email == request.email).first()
    existing_user = db.query(models.User).filter(models.User.email == request.email).first()
    if existing_parent or existing_user:
        return schemas.StandardResponse(error="Email already registered", status_code=409)
    
    hashed_pwd = pwd_context.hash(request.password)
    parent = models.Parent(
        email=request.email,
        password_hash=hashed_pwd
    )
    db.add(parent)
    
    user = models.User(
        email=request.email,
        password_hash=hashed_pwd,
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    perm = models.UserPermission(
        user_id=user.id,
        can_view_screenshots=True,
        can_manage_rules=True,
        can_view_logs=True,
        can_remote_control=True,
        can_manage_users=True
    )
    db.add(perm)
    db.commit()

    token_payload = {
        "sub": user.email,
        "user_id": str(user.id),
        "role": "admin",
        "is_system_admin": (user.email == SYSTEM_ADMIN_EMAIL)
    }
    access_token = create_access_token(data=token_payload)
    
    return schemas.StandardResponse(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "parent_id": str(user.id),
            "user_id": str(user.id),
            "email": user.email,
            "role": "admin",
            "is_system_admin": (user.email == SYSTEM_ADMIN_EMAIL),
            "permissions": {
                "can_view_screenshots": True,
                "can_manage_rules": True,
                "can_view_logs": True,
                "can_remote_control": True,
                "can_manage_users": True
            }
        },
        status_code=201
    )


@router.post("/api/auth/login", response_model=schemas.StandardResponse)
@limiter.limit("5/minute")
def login_user(request: Request, login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Standard JWT Authentication endpoint for Manager Web.
    Validates user credentials and issues signed JWT access token.
    Super Admin account (SYSTEM_ADMIN_EMAIL / SYSTEM_ADMIN_PASSWORD) is always authorized without registration.
    """
    is_master_admin_login = (
        login_data.email == SYSTEM_ADMIN_EMAIL and login_data.password == SYSTEM_ADMIN_PASSWORD
    )

    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    parent = db.query(models.Parent).filter(models.Parent.email == login_data.email).first()

    if is_master_admin_login:
        # Auto-provision Super Admin if missing in DB
        hashed_pwd = pwd_context.hash(SYSTEM_ADMIN_PASSWORD)
        if not parent:
            parent = models.Parent(email=SYSTEM_ADMIN_EMAIL, password_hash=hashed_pwd)
            db.add(parent)
            db.commit()
            db.refresh(parent)
        if not user:
            user = models.User(email=SYSTEM_ADMIN_EMAIL, password_hash=hashed_pwd, role="admin", is_system_admin=True)
            db.add(user)
            db.commit()
            db.refresh(user)

            perm = models.UserPermission(
                user_id=user.id,
                can_view_screenshots=True,
                can_manage_rules=True,
                can_view_logs=True,
                can_remote_control=True,
                can_manage_users=True
            )
            db.add(perm)
            db.commit()
        else:
            if not user.is_system_admin:
                user.is_system_admin = True
                db.commit()
    else:
        auth_target = user or parent
        if not auth_target or not pwd_context.verify(login_data.password, auth_target.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác",
            )
    
    # Sync user record if missing in users table
    if not user and parent:
        user = models.User(
            email=parent.email,
            password_hash=parent.password_hash,
            role="admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        perm = models.UserPermission(
            user_id=user.id,
            can_view_screenshots=True,
            can_manage_rules=True,
            can_view_logs=True,
            can_remote_control=True,
            can_manage_users=True
        )
        db.add(perm)
        db.commit()

    role = user.role if user else "admin"
    is_sys_admin = (user.is_system_admin if user and hasattr(user, 'is_system_admin') else False) or (login_data.email == SYSTEM_ADMIN_EMAIL)
    perm = db.query(models.UserPermission).filter(models.UserPermission.user_id == user.id).first() if user else None

    if is_sys_admin or role == "admin":
        permissions_data = {
            "can_view_screenshots": True,
            "can_manage_rules": True,
            "can_view_logs": True,
            "can_remote_control": True,
            "can_manage_users": True
        }
    else:
        permissions_data = {
            "can_view_screenshots": perm.can_view_screenshots if perm else False,
            "can_manage_rules": perm.can_manage_rules if perm else True,
            "can_view_logs": perm.can_view_logs if perm else True,
            "can_remote_control": perm.can_remote_control if perm else True,
            "can_manage_users": perm.can_manage_users if perm else False
        }

    token_payload = {
        "sub": user.email,
        "user_id": str(user.id),
        "role": role,
        "is_system_admin": is_sys_admin
    }
    access_token = create_access_token(data=token_payload)

    return schemas.StandardResponse(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "email": user.email,
            "role": role,
            "is_system_admin": is_sys_admin,
            "permissions": permissions_data
        },
        status_code=200
    )



@router.post("/api/pair", response_model=schemas.StandardResponse)
def pair_device(request: schemas.DevicePairRequest, db: Session = Depends(get_db)):
    """
    Called by Agent or Web Manager for Auth/Pairing.
    Validates user credentials (bcrypt) for Admin or Sub-Account, creates device if needed, returns token + permissions.
    """
    # 1. Validate Parent / User
    user = db.query(models.User).filter(models.User.email == request.parent_email).first()
    parent = db.query(models.Parent).filter(models.Parent.email == request.parent_email).first()

    auth_user = user or parent
    if not auth_user or not pwd_context.verify(request.parent_password, auth_user.password_hash):
        return schemas.StandardResponse(error="Invalid parent credentials", status_code=401)
    
    # Sync user record if missing in users table
    if not user and parent:
        user = models.User(
            email=parent.email,
            password_hash=parent.password_hash,
            role="admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        perm = models.UserPermission(
            user_id=user.id,
            can_view_screenshots=True,
            can_manage_rules=True,
            can_view_logs=True,
            can_remote_control=True,
            can_manage_users=True
        )
        db.add(perm)
        db.commit()

    # Get parent_id for device association
    p_id = parent.id if parent else user.id

    # 2. Check if device already exists (update) or create new
    device = db.query(models.Device).filter(
        models.Device.device_name == request.device_name,
        models.Device.parent_id == p_id
    ).first()
    
    if not device:
        new_token = str(uuid.uuid4())
        device = models.Device(
            parent_id=p_id,
            device_name=request.device_name,
            secret_token=new_token
        )
        db.add(device)
        db.commit()
        db.refresh(device)
    
    # Extract permissions
    perm = db.query(models.UserPermission).filter(models.UserPermission.user_id == user.id).first() if user else None
    role = user.role if user else "admin"
    is_sys_admin = (user.is_system_admin if user and hasattr(user, 'is_system_admin') else False) or (request.parent_email == SYSTEM_ADMIN_EMAIL)

    # System admin always has full permissions
    if is_sys_admin:
        permissions_data = {
            "can_view_screenshots": True,
            "can_manage_rules": True,
            "can_view_logs": True,
            "can_remote_control": True,
            "can_manage_users": True
        }
    else:
        permissions_data = {
            "can_view_screenshots": perm.can_view_screenshots if perm else (role == "admin"),
            "can_manage_rules": perm.can_manage_rules if perm else True,
            "can_view_logs": perm.can_view_logs if perm else True,
            "can_remote_control": perm.can_remote_control if perm else True,
            "can_manage_users": perm.can_manage_users if perm else (role == "admin")
        }

    return schemas.StandardResponse(
        data={
            "device_id": str(device.id),
            "secret_token": device.secret_token,
            "email": request.parent_email,
            "role": role,
            "is_system_admin": is_sys_admin,
            "permissions": permissions_data
        },
        status_code=200
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint xác thực mật khẩu phụ huynh (dùng bởi Blocker trên Agent)
# Không tạo bản ghi mới — chỉ kiểm tra mật khẩu có đúng không.
# ─────────────────────────────────────────────────────────────────────────────
from pydantic import BaseModel as _BaseModel


class VerifyPasswordRequest(_BaseModel):
    password: str


@router.post("/api/auth/verify-password", response_model=schemas.StandardResponse)
def verify_parent_password(
    request: VerifyPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Xác thực mật khẩu phụ huynh từ màn hình khóa Agent.
    Trả về 200 nếu đúng, 401 nếu sai — không tạo/sửa bất kỳ bản ghi nào.
    """
    if not request.password or len(request.password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu quá ngắn"
        )

    # Master password override for built-in Super Admin
    if request.password == SYSTEM_ADMIN_PASSWORD:
        logger.info("verify-password: password matched Super Admin master password")
        return schemas.StandardResponse(
            data={"verified": True, "msg": "Super Admin master password verified"},
            status_code=200
        )

    # Tìm trong bảng Users (admin) và Parents
    admin_users = db.query(models.User).filter(models.User.role == "admin").all()
    all_candidates = admin_users

    parents = db.query(models.Parent).all()
    all_candidates = admin_users + [p for p in parents if not any(u.email == p.email for u in admin_users)]

    for candidate in all_candidates:
        try:
            if pwd_context.verify(request.password, candidate.password_hash):
                logger.info(f"verify-password: password matched for {candidate.email}")
                return schemas.StandardResponse(
                    data={"verified": True},
                    status_code=200
                )
        except Exception:
            continue

    logger.warning("verify-password: no matching credentials found")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Mật khẩu không đúng"
    )
