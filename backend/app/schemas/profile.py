from datetime import datetime
from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    telegram_id: int
    display_name: str | None = Field(None, max_length=128)
    bio: str | None = Field(None, max_length=500)
    language_level: str | None = Field(None, pattern="^(beginner|intermediate|advanced|native)$")
    is_public: bool = True


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=128)
    bio: str | None = Field(None, max_length=500)
    language_level: str | None = Field(None, pattern="^(beginner|intermediate|advanced|native)$")
    is_public: bool | None = None


class ProfileRead(BaseModel):
    id: int
    telegram_id: int
    profile_slug: str
    display_name: str | None
    bio: str | None
    language_level: str | None
    is_public: bool
    messages_received: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfilePublic(BaseModel):
    profile_slug: str
    display_name: str | None
    bio: str | None
    language_level: str | None

    model_config = {"from_attributes": True}
