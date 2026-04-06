from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None


class UserRead(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    is_active: bool
    created_at: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = None
    first_name: str | None = None
    is_active: bool | None = None
