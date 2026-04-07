from datetime import datetime
from pydantic import BaseModel, field_validator


class AnonymousMessageCreate(BaseModel):
    recipient_token: str
    content: str
    sender_id: int  # used for rate limiting only, NOT stored

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message content cannot be empty")
        if len(v) > 1000:
            raise ValueError("Message is too long (max 1000 characters)")
        return v


class AnonymousMessageRead(BaseModel):
    id: int
    recipient_telegram_id: int
    content: str
    is_read: bool
    is_flagged: bool
    helpful_votes: int
    unhelpful_votes: int
    reply_content: str | None = None
    replied_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnonymousMessageReply(BaseModel):
    reply_content: str

    @field_validator("reply_content")
    @classmethod
    def validate_reply(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Reply cannot be empty")
        if len(v) > 500:
            raise ValueError("Reply is too long (max 500 characters)")
        return v


class MessageVote(BaseModel):
    message_id: int
    telegram_id: int
    vote: str  # "helpful" or "unhelpful"

    @field_validator("vote")
    @classmethod
    def validate_vote(cls, v: str) -> str:
        if v not in {"helpful", "unhelpful"}:
            raise ValueError("vote must be 'helpful' or 'unhelpful'")
        return v


class MessageFlag(BaseModel):
    message_id: int
    reported_by: int
    reason: str
