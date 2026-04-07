from datetime import datetime

from pydantic import BaseModel


class RequiredChannelCreate(BaseModel):
    channel_id: int
    channel_username: str | None = None
    title: str
    invite_link: str | None = None


class RequiredChannelRead(BaseModel):
    id: int
    channel_id: int
    channel_username: str | None
    title: str
    invite_link: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
