import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, String, Integer, DateTime, ForeignKey, Time, Index
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from database import Base

class GUID(TypeDecorator):
    """Platform-independent GUID type for PostgreSQL and SQLite."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

class UTCDateTime(TypeDecorator):
    """Ensure timezone-aware datetime objects in UTC."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

class Parent(Base):
    __tablename__ = "parents"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    devices = relationship("Device", back_populates="parent", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="admin")  # 'admin' or 'sub_account'
    owner_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_system_admin = Column(Boolean, default=False)  # True for built-in super admin only
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    permissions = relationship("UserPermission", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    can_view_screenshots = Column(Boolean, default=True)
    can_manage_rules = Column(Boolean, default=True)
    can_view_logs = Column(Boolean, default=True)
    can_remote_control = Column(Boolean, default=True)
    can_manage_users = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="permissions")


class Device(Base):
    __tablename__ = "devices"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    parent_id = Column(GUID, ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    device_name = Column(String, nullable=False)
    secret_token = Column(String, nullable=False, unique=True)  # Hash of DPAPI token
    pairing_code = Column(String(6), nullable=True) # Only used during pairing process
    last_seen_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))
    is_allowed = Column(Boolean, default=True) # Global kill switch
    is_locked = Column(Boolean, default=False) # Screen lock state
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    parent = relationship("Parent", back_populates="devices")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")
    process_logs = relationship("ProcessLog", back_populates="device", cascade="all, delete-orphan")
    rules = relationship("Rule", back_populates="device", cascade="all, delete-orphan")
    screenshots = relationship("Screenshot", back_populates="device", cascade="all, delete-orphan")
    browser_history = relationship("BrowserHistory", back_populates="device", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="device", cascade="all, delete-orphan")
    pending_commands = relationship("PendingCommand", back_populates="device", cascade="all, delete-orphan")

class PendingCommand(Base):
    __tablename__ = "pending_commands"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    command = Column(String, nullable=False)
    payload = Column(String, nullable=True) # JSON string
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    device = relationship("Device", back_populates="pending_commands")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index('ix_chat_messages_device_id', 'device_id'),
        Index('ix_chat_messages_device_timestamp', 'device_id', 'timestamp'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=False)  # 'admin' or 'child'
    message = Column(String, nullable=False)
    timestamp = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    device = relationship("Device", back_populates="chat_messages")


class BrowserHistory(Base):
    __tablename__ = "browser_history"
    __table_args__ = (
        Index('ix_browser_history_device_id', 'device_id'),
        Index('ix_browser_history_device_timestamp', 'device_id', 'timestamp'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    browser_name = Column(String, nullable=False)
    url = Column(String, nullable=True)
    page_title = Column(String, nullable=True)
    timestamp = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    device = relationship("Device", back_populates="browser_history")


class Screenshot(Base):
    __tablename__ = "screenshots"
    __table_args__ = (
        Index('ix_screenshots_device_id', 'device_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String, nullable=False)
    timestamp = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    device = relationship("Device", back_populates="screenshots")



class Rule(Base):
    """
    Unified rule table for App, Web, and Time restrictions.
    rule_type discriminator: 'app', 'web', 'time'
    - app/web rules use: target, is_banned
    - time rules use: day_of_week, allowed_start, allowed_end
    """
    __tablename__ = "rules"
    __table_args__ = (
        Index('ix_rules_device_id', 'device_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(String, nullable=False)  # 'app', 'web', 'time'
    target = Column(String, nullable=True)  # e.g. 'LienMinh.exe' or 'facebook.com' (null for time rules)
    is_banned = Column(Boolean, default=True)
    daily_limit_minutes = Column(Integer, nullable=True)  # Optional daily limit for app rules
    day_of_week = Column(Integer, nullable=True)  # 0=Monday..6=Sunday (for time rules)
    allowed_start = Column(Time, nullable=True)  # Start of allowed window (for time rules)
    allowed_end = Column(Time, nullable=True)  # End of allowed window (for time rules)
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    device = relationship("Device", back_populates="rules")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index('ix_alerts_device_id', 'device_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String, nullable=False)  # 'banned_app_opened', 'tampered', 'offline_too_long'
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    device = relationship("Device", back_populates="alerts")


class ProcessLog(Base):
    """
    Huge table to track all process/window activity.
    PARTITION READY: In production, convert to range partition by 'timestamp'.
    Requires: ALTER TABLE process_logs PARTITION BY RANGE (timestamp);
    And composite PK: (id, timestamp) — apply via Alembic migration when needed.
    """
    __tablename__ = "process_logs"
    __table_args__ = (
        Index('ix_process_logs_device_id', 'device_id'),
        Index('ix_process_logs_device_timestamp', 'device_id', 'timestamp'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    process_name = Column(String, nullable=False)
    window_title = Column(String, nullable=True)
    timestamp = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    device = relationship("Device", back_populates="process_logs")


class TelegramSetting(Base):
    __tablename__ = "telegram_settings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    bot_token = Column(String, nullable=True)
    chat_id = Column(String, nullable=True)
    updated_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
    updated_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


