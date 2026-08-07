import uuid
from datetime import date
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Text,
    JSON,
    Date,
    func,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def uuid_str():
    return str(uuid.uuid4())


class ModelMixin:
    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if value is None:
                result[column.name] = None
            elif isinstance(value, (date, DateTime)):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result


class Device(Base, ModelMixin):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, unique=True, nullable=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())


class ProcessLog(Base, ModelMixin):
    __tablename__ = "process_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    process_name = Column(String, nullable=False)
    pid = Column(Integer)
    cpu_percent = Column(Integer, default=0)
    memory_mb = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())


class ActiveWindowLog(Base, ModelMixin):
    __tablename__ = "active_window_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    process_name = Column(String, nullable=False)
    window_title = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())


class ScreenshotLog(Base, ModelMixin):
    __tablename__ = "screenshot_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())


class SystemEvent(Base, ModelMixin):
    __tablename__ = "system_events"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())


class TimeRestriction(Base, ModelMixin):
    __tablename__ = "time_restrictions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(String, default="07:00:00")
    end_time = Column(String, default="21:00:00")
    is_active = Column(Boolean, default=True)
    max_hours = Column(Integer, default=4)
    created_at = Column(DateTime(timezone=True), default=func.now())


class AppRule(Base, ModelMixin):
    __tablename__ = "app_rules"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    process_name = Column(String, nullable=False)
    category = Column(String, default="allowed")
    max_minutes_per_day = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())


class AppConfig(Base, ModelMixin):
    __tablename__ = "app_config"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, unique=True, nullable=False)
    agent_password = Column(String, default="Truc@1905s0825811915")
    admin_pin = Column(String, default="123456")
    screenshot_interval_minutes = Column(Integer, default=3)
    custom_roles = Column(JSON, default=lambda: ["Phụ huynh", "Em trai", "Gia sư"])
    role_passwords = Column(JSON, default=lambda: {})
    role_permissions = Column(JSON, default=lambda: {})
    is_allowed = Column(Boolean, default=True)
    time_limit_mode = Column(String, default="time_frame")
    updated_at = Column(DateTime(timezone=True), default=func.now())


class AppUsageLog(Base, ModelMixin):
    __tablename__ = "app_usage_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    process_name = Column(String, nullable=False)
    usage_date = Column(Date, default=date.today)
    used_minutes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())


class Schedule(Base, ModelMixin):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(String, default="study")
    created_at = Column(DateTime(timezone=True), default=func.now())


class ChatMessage(Base, ModelMixin):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())


class SystemCommand(Base, ModelMixin):
    __tablename__ = "system_commands"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    command = Column(String, nullable=False)
    status = Column(String, default="pending")
    result = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())


class WebRule(Base, ModelMixin):
    __tablename__ = "web_rules"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    category = Column(String, default="forbidden")
    max_minutes_per_day = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())


class WebUsageLog(Base, ModelMixin):
    __tablename__ = "web_usage_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    used_minutes = Column(Integer, default=0)
    usage_date = Column(Date, default=date.today)
    created_at = Column(DateTime(timezone=True), default=func.now())


class WebAccessSession(Base, ModelMixin):
    __tablename__ = "web_access_sessions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    session_id = Column(String, unique=True, nullable=False)
    user_role = Column(String, default="Viewer")
    is_blocked = Column(Boolean, default=False)
    device_info = Column(Text)
    last_active = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())


class TodoNote(Base, ModelMixin):
    __tablename__ = "todo_notes"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    task_title = Column(String, nullable=False)
    task_type = Column(String, default="admin_assigned")
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())


class BrowserHistoryLog(Base, ModelMixin):
    __tablename__ = "browser_history_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    device_name = Column(String, nullable=False)
    browser_name = Column(String, default="Chrome")
    title = Column(Text)
    url = Column(Text)
    visit_time = Column(DateTime(timezone=True), default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())


class AgentVersion(Base, ModelMixin):
    __tablename__ = "agent_versions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    version = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    changelog = Column(Text)
    uploaded_by = Column(String, default="admin")
    is_latest = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())


TABLE_MODELS = {
    "devices": Device,
    "process_logs": ProcessLog,
    "active_window_logs": ActiveWindowLog,
    "screenshot_logs": ScreenshotLog,
    "system_events": SystemEvent,
    "time_restrictions": TimeRestriction,
    "app_rules": AppRule,
    "app_config": AppConfig,
    "app_usage_logs": AppUsageLog,
    "schedules": Schedule,
    "chat_messages": ChatMessage,
    "system_commands": SystemCommand,
    "web_rules": WebRule,
    "web_usage_logs": WebUsageLog,
    "web_access_sessions": WebAccessSession,
    "todo_notes": TodoNote,
    "browser_history_logs": BrowserHistoryLog,
    "agent_versions": AgentVersion,
}
