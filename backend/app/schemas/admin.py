from datetime import datetime
from pydantic import BaseModel


class UserStatisticsRead(BaseModel):
    telegram_id: int
    total_conversations: int
    total_messages_sent: int
    total_messages_received: int
    conversations_completed: int
    ratings_given_count: int
    ratings_received_count: int
    avg_rating_received: float
    avg_rating_given: float
    total_session_duration_seconds: int
    last_conversation_at: datetime | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    telegram_id: int
    username: str | None
    first_name: str | None
    xp: int
    level: int
    reputation_score: float
    total_conversations: int

    model_config = {"from_attributes": True}


class AdminDashboardStats(BaseModel):
    total_users: int
    active_users_today: int
    total_sessions: int
    active_sessions: int
    total_anonymous_messages: int
    pending_moderation_flags: int
    top_user_xp: int


class AdminUserDetail(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    is_active: bool
    created_at: datetime
    last_seen: datetime
    xp: int
    level: int
    reputation_score: float
    total_conversations: int
    avg_rating_received: float

    model_config = {"from_attributes": True}


class AdminActionRequest(BaseModel):
    admin_telegram_id: int
    target_telegram_id: int
    action: str  # "suspend" | "unsuspend" | "reset_xp"
    reason: str | None = None


class ModerationFlagRead(BaseModel):
    id: int
    content_type: str
    content_id: int
    reported_by: int | None
    reason: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminLogRead(BaseModel):
    id: int
    admin_telegram_id: int
    action: str
    target_type: str | None
    target_id: str | None
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
