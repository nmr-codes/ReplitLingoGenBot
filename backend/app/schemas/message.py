from datetime import datetime
from pydantic import BaseModel, Field


class AnonMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    sender_token: str | None = None


class AnonMessageReply(BaseModel):
    reply_content: str = Field(..., min_length=1, max_length=500)


class AnonMessageRead(BaseModel):
    id: int
    recipient_telegram_id: int
    content: str
    is_read: bool
    reply_content: str | None
    replied_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
