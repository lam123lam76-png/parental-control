from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime, time
import uuid



# =============
# Common Wrapper
# =============
class StandardResponse(BaseModel):
    data: Optional[dict] = None
    error: Optional[str] = None
    status_code: int = 200


# =============
# Parent & Auth (Phụ huynh & Đăng nhập)
# =============
class ParentCreate(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    is_system_admin: bool = False
    permissions: dict = Field(default_factory=dict)

class ParentResponse(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# =============
# RBAC & User Management
# =============
class PermissionSchema(BaseModel):
    can_view_screenshots: bool = True
    can_manage_rules: bool = True
    can_view_logs: bool = True
    can_remote_control: bool = True
    can_manage_users: bool = False

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: str
    password: str
    admin_email: Optional[str] = None
    role: str = "sub_account"
    permissions: Optional[PermissionSchema] = None

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    owner_id: Optional[uuid.UUID] = None
    permissions: Optional[PermissionSchema] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PermissionUpdate(BaseModel):
    permissions: PermissionSchema


# =============
# System Storage & Cleanup
# =============
class StorageCleanRequest(BaseModel):
    target: str = Field("all", description="'screenshots', 'logs', or 'all'")
    days_older_than: int = Field(0, description="0 = all, 7 = older than 7 days, 30 = older than 30 days")


# =============
# Browser History
# =============
class BrowserHistoryItem(BaseModel):
    browser_name: str
    url: Optional[str] = None
    page_title: Optional[str] = None
    timestamp: Optional[str] = None

class BrowserHistoryBatch(BaseModel):
    device_id: str
    items: List[BrowserHistoryItem]


# =============
# Two-Way Chat
# =============
class ChatMessageSend(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    sender: str
    message: str
    timestamp: datetime

    class Config:
        from_attributes = True


# =============
# Device (Thiết bị)
# =============
class DevicePairRequest(BaseModel):
    hardware_uuid: str
    device_name: str
    parent_email: str
    parent_password: str

class DevicePairResponse(BaseModel):
    device_id: uuid.UUID
    secret_token: str

class DeviceResponse(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID
    device_name: str
    is_allowed: bool
    last_seen_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    is_allowed: Optional[bool] = None


# =============
# Rule (Luật App/Web/Time)
# =============
class RuleCreate(BaseModel):
    device_id: Optional[uuid.UUID] = None
    rule_type: str = Field(..., description="'app', 'web', or 'time'")
    target: Optional[str] = Field(None, description="App name or URL pattern (null for time rules)")
    is_banned: bool = True
    daily_limit_minutes: Optional[int] = None
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="0=Monday..6=Sunday")
    allowed_start: Optional[time] = None
    allowed_end: Optional[time] = None

class RuleResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    rule_type: str
    target: Optional[str] = None
    is_banned: bool
    daily_limit_minutes: Optional[int] = None
    day_of_week: Optional[int] = None
    allowed_start: Optional[time] = None
    allowed_end: Optional[time] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =============
# Alert (Cảnh báo - Luồng 2)
# =============
class AlertCreate(BaseModel):
    device_id: uuid.UUID
    alert_type: str = Field(..., description="E.g., banned_app_opened, tampered")
    message: str

class AlertResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    alert_type: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# =============
# Process Log (Luồng 3)
# =============
class ProcessLogItem(BaseModel):
    process_name: str
    window_title: Optional[str] = None
    timestamp: datetime

class LogBatchUpload(BaseModel):
    device_id: uuid.UUID
    logs: List[ProcessLogItem]

class ProcessLogResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    process_name: str
    window_title: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# =============
# Screenshot (Ảnh màn hình)
# =============
class ScreenshotCreate(BaseModel):
    device_id: uuid.UUID
    image_url: str

class ScreenshotResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    image_url: str
    timestamp: datetime

    class Config:
        from_attributes = True


# =============
# Storage Management & Data Hub
# =============
class StorageCleanRequest(BaseModel):
    target: str = Field("all", description="'screenshots', 'logs', 'all'")
    days_older_than: int = Field(0, description="0 for all time, or number of days like 7, 30, 90")

class StoragePeriodCleanRequest(BaseModel):
    category: str = Field("all", description="'screenshots', 'web', 'logs', 'processes', 'all'")
    periods: List[str] = Field(default_factory=list, description="List of periods like ['2026-08-11']")
    period_type: str = Field("day", description="'day', 'week', 'month'")
    item_ids: Optional[List[str]] = Field(None, description="List of explicit item IDs to delete. If provided, periods is ignored for deletion filtering.")


# =============
# WebSocket Command (Lệnh tức thì)
# =============
class DeviceCommand(BaseModel):
    """Command to send to a device via WebSocket."""
    command: str = Field(..., description="E.g., 'kill_process', 'lock_screen', 'refresh_rules'")
    payload: Optional[dict] = None


# =============
# Telegram Config
# =============
class TelegramConfigRequest(BaseModel):
    bot_token: str
    chat_id: str


# =============
# Period Settings (Cài đặt chu kỳ)
# =============
class PeriodSettingsRequest(BaseModel):
    screenshot_interval_seconds: Optional[int] = Field(60, ge=5, le=7200)
    heartbeat_interval_seconds: Optional[int] = Field(15, ge=5, le=300)
    log_batch_interval_seconds: Optional[int] = Field(300, ge=10, le=3600)
    device_id: Optional[str] = None

class PeriodSettingsResponse(BaseModel):
    screenshot_interval_seconds: int = 60
    heartbeat_interval_seconds: int = 15
    log_batch_interval_seconds: int = 300


# =============
# Restrictions (Giới hạn Web & App)
# =============
class RestrictionItem(BaseModel):
    id: Optional[Any] = None
    type: str = Field("web", description="'web' or 'app'")
    target: str = Field(..., max_length=1000)
    mode: str = Field("ban", description="'ban', 'allow', or 'limit'")
    daily_limit_minutes: Optional[int] = None

class RestrictionsRequest(BaseModel):
    device_id: Optional[str] = None
    rules: List[RestrictionItem] = []





