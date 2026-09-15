from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

def _get_real_client_ip(request: Request) -> str:
    """Lấy IP thật của client từ header X-Forwarded-For hoặc X-Real-IP.

    Khi chạy sau nginx proxy, `request.client.host` trả về IP của nginx container
    (172.x.x.x) khiến tất cả user dùng chung 1 rate-limit bucket → bị từ chối
    hàng loạt. Header này được nginx set với giá trị $remote_addr (IP client thật).
    """
    forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded_for:
        # Lấy IP đầu tiên (client gốc), bỏ qua các proxy trung gian
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    return get_remote_address(request)

limiter = Limiter(key_func=_get_real_client_ip)
import uuid
import logging
import secrets

from database import get_db
import models
import schemas
from core.config import SYSTEM_ADMIN_EMAIL, MASTER_UNLOCK_PASSWORD
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

    # Không bao giờ tạo tài khoản với mật khẩu rỗng/ngắn: hash của chuỗi rỗng từng
    # tồn tại trong DB và cho phép đăng nhập bằng mật khẩu trống.
    if not request.password or len(request.password.strip()) < 8:
        return schemas.StandardResponse(
            error="Mật khẩu phải có ít nhất 8 ký tự.", status_code=400
        )

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
    Đăng nhập Web Manager. CHỈ chấp nhận mật khẩu tài khoản trong DB.

    HAI LOẠI MẬT KHẨU, TÁCH BIỆT HOÀN TOÀN (yêu cầu nghiệp vụ):
      - mật khẩu WEB (bảng users/parents)      -> đăng nhập quản trị, KHÔNG mở khoá máy con
      - mật khẩu MỞ MÁY CON (SYSTEM_ADMIN_PASSWORD) -> chỉ dùng ở /api/auth/verify-password

    Vì sao không còn "master login" ở đây: khi SYSTEM_ADMIN_PASSWORD còn được nhận
    làm mật khẩu đăng nhập, đặt biến đó vừa cấp quyền system admin cho web vừa khiến
    seeder ghi đè mật khẩu tài khoản admin (xem main.py) — tức mật khẩu "chỉ để mở
    máy" lại trở thành mật khẩu web và xoá mất mật khẩu web thật.
    """
    # Mật khẩu rỗng/whitespace KHÔNG BAO GIỜ hợp lệ. Đây là lỗ hổng đã xảy ra thật:
    # bảng users có tài khoản admin với hash của chuỗi rỗng (do seed khi biến
    # SYSTEM_ADMIN_PASSWORD tồn tại nhưng rỗng), nên POST /api/auth/login với
    # password="" trả về token system-admin hợp lệ cho bất kỳ ai trên Internet.
    # Chặn ở đây TRƯỚC khi truy vấn DB (và test không cần DB).
    if not login_data.password or not login_data.password.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
        )

    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    parent = db.query(models.Parent).filter(models.Parent.email == login_data.email).first()

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
    # Cùng lý do như login_user: mật khẩu rỗng không bao giờ hợp lệ (hash chuỗi rỗng
    # từng tồn tại trong DB và sẽ khớp với mật khẩu rỗng).
    if not request.parent_password or not request.parent_password.strip():
        return schemas.StandardResponse(error="Invalid parent credentials", status_code=401)
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
    Xác thực mật khẩu để MỞ KHOÁ MÀN HÌNH máy con. Trả 200 nếu đúng, 401 nếu sai —
    không tạo/sửa bất kỳ bản ghi nào.

    Nhận CẢ HAI loại mật khẩu (đúng thiết kế 2 mật khẩu tách biệt):
      1. mật khẩu MỞ MÁY CON  = SYSTEM_ADMIN_PASSWORD (biến môi trường của server)
      2. mật khẩu TÀI KHOẢN   = hash trong DB (bảng users role=admin + bảng parents)
    Ngược lại, mật khẩu mở máy con KHÔNG dùng để đăng nhập web (xem login_user).
    """
    if not request.password or len(request.password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu quá ngắn"
        )

    # 1. Mật khẩu chuyên dụng để mở khoá máy con (KHÔNG phải mật khẩu đăng nhập web).
    # Chỉ hoạt động khi biến môi trường được đặt — trước đây nó có giá trị mặc định
    # công khai trong repo, nghĩa là đứa trẻ tự mở khoá được máy mình.
    if MASTER_UNLOCK_PASSWORD and secrets.compare_digest(request.password, MASTER_UNLOCK_PASSWORD):
        logger.info("verify-password: khớp mật khẩu mở khoá máy con")
        return schemas.StandardResponse(
            data={"verified": True, "msg": "Đã mở khoá bằng mật khẩu mở máy"},
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
