from datetime import datetime
from pydantic import BaseModel
from backend.app.models.session import SessionStatus


class SessionCreate(BaseModel):
    user1_id: int
    user2_id: int
    topic: str
    session_uuid: str


class SessionRead(BaseModel):
    session_uuid: str
    user1_id: int
    user2_id: int
    topic: str
    status: SessionStatus
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: int | None = None

    model_config = {"from_attributes": True}


class SessionEnd(BaseModel):
    session_uuid: str
    status: SessionStatus = SessionStatus.ENDED


class MatchRequest(BaseModel):
    telegram_id: int


class MatchResponse(BaseModel):
    matched: bool
    session_uuid: str | None = None
    partner_id: int | None = None
    topic: str | None = None
    queue_position: int | None = None
    message: str = ""
