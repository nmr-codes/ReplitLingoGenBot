from datetime import datetime
from pydantic import BaseModel


class AdminUserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    role: str = "MODERATOR"


class AdminUserRead(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminLogRead(BaseModel):
    id: int
    admin_telegram_id: int
    action: str
    target_telegram_id: int | None
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_users: int
    active_users_today: int
    total_sessions: int
    active_sessions: int
    total_profiles: int
    total_anonymous_messages: int
    unread_anonymous_messages: int
