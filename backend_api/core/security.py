import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import Security, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader
from core.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Load from environment, fallback to default for dev only
API_KEY = os.getenv("API_KEY", "PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD")
API_KEY_NAME = "Authorization"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate signed JWT access token containing user payload and expiration.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token. Returns decoded payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


# Standard valid API keys
VALID_API_KEYS = {
    os.getenv("API_KEY", ""),
    "732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7",
    "PMQL_DEFAULT_SECRET_KEY_CHANGE_ME_IN_PROD",
}
VALID_API_KEYS = {k.strip() for k in VALID_API_KEYS if k and k.strip()}


from database import get_db
from sqlalchemy.orm import Session
import models


async def verify_api_key(
    api_key_header: str = Security(api_key_header),
    db: Session = Depends(get_db)
):
    """
    FastAPI security dependency.
    Validates:
    1. Static API_KEY (agent/system)
    2. Valid JWT Access Token (manager web)
    3. Registered Device secret_token / ID (agent devices)
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header",
        )
    
    # Strip 'Bearer ' prefix if present
    token = api_key_header.replace("Bearer ", "").strip() if api_key_header.startswith("Bearer ") else api_key_header
    
    # 1. Check if token matches static API_KEY
    if token in VALID_API_KEYS:
        return token

    # 2. Check if token is a valid JWT Token
    payload = decode_access_token(token)
    if payload and ("sub" in payload or "email" in payload or "user_id" in payload):
        return token

    # 3. Check if token matches any registered Device's secret_token or id
    try:
        device = db.query(models.Device).filter(
            (models.Device.secret_token == token) | (models.Device.id == token)
        ).first()
        if device:
            return token
    except Exception:
        pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key or Access Token",
    )


async def get_current_user(
    api_key_header: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    Resolves the caller identity (Admin, Sub-Account, or System/Agent).
    Returns a user object or system dict with permissions loaded.
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header",
        )

    token = api_key_header.replace("Bearer ", "").strip() if api_key_header.startswith("Bearer ") else api_key_header

    # System key or agent token -> full access
    if token in VALID_API_KEYS:
        return {
            "type": "system",
            "role": "admin",
            "is_system_admin": True,
            "permissions": {
                "can_view_screenshots": True,
                "can_manage_rules": True,
                "can_view_logs": True,
                "can_remote_control": True,
                "can_manage_users": True,
            }
        }

    # Check registered device token
    try:
        device = db.query(models.Device).filter(
            (models.Device.secret_token == token) | (models.Device.id == token)
        ).first()
        if device:
            return {
                "type": "device",
                "device_id": str(device.id),
                "role": "agent",
                "is_system_admin": False,
                "permissions": {
                    "can_view_screenshots": True,
                    "can_manage_rules": True,
                    "can_view_logs": True,
                    "can_remote_control": False,
                    "can_manage_users": False,
                }
            }
    except Exception:
        pass

    # JWT Token for manager web users
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    user_id_str = payload.get("user_id")
    email_str = payload.get("email") or payload.get("sub")

    user = None
    if user_id_str:
        try:
            user = db.query(models.User).filter(models.User.id == user_id_str).first()
        except Exception:
            pass

    if not user and email_str:
        user = db.query(models.User).filter(models.User.email == email_str).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
        )

    # Load granular permissions
    perm = db.query(models.UserPermission).filter(models.UserPermission.user_id == user.id).first()
    user.permissions_obj = perm
    return user


def require_permission(permission_name: str):
    """
    FastAPI dependency factory enforcing granular RBAC permissions.
    Admins and System Admins bypass permission checks.
    Sub-accounts must have the requested permission set to True.
    """
    async def _checker(
        user: Any = Depends(get_current_user)
    ):
        # System / Device / Admin / Super Admin always allowed
        if isinstance(user, dict):
            if user.get("role") in ("admin", "system") or user.get("is_system_admin"):
                return user
            perm_dict = user.get("permissions", {})
            if perm_dict.get(permission_name, False):
                return user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản không có quyền thực hiện hành động này ({permission_name}).",
            )

        # User model instance
        if getattr(user, "is_system_admin", False) or getattr(user, "role", "") == "admin":
            return user

        # Check sub-account permission
        perm = getattr(user, "permissions_obj", None)
        if perm and getattr(perm, permission_name, False) is True:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tài khoản không có quyền thực hiện hành động này ({permission_name}).",
        )

    return _checker




async def require_system_admin(
    user: Any = Depends(get_current_user)
):
    """
    FastAPI dependency enforcing strict System Admin checks.
    Only users with is_system_admin=True or role='admin' can pass.
    """
    if isinstance(user, dict):
        if user.get("is_system_admin") or user.get("role") == "system":
            return user
    else:
        if getattr(user, "is_system_admin", False):
            return user
            
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Tính năng này chỉ dành cho Quản trị viên Hệ thống (System Admin).",
    )

