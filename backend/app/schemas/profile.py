from datetime import datetime
from pydantic import BaseModel, field_validator

VALID_LANGUAGE_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}


class UserProfileCreate(BaseModel):
    telegram_id: int
    bio: str | None = None
    native_language: str | None = None
    target_language: str | None = None
    language_level: str | None = None
    is_public: bool = True
    availability: str = "online"
    learning_goals: str | None = None

    @field_validator("language_level")
    @classmethod
    def validate_level(cls, v: str | None) -> str | None:
        if v and v.upper() not in VALID_LANGUAGE_LEVELS:
            raise ValueError(f"language_level must be one of {VALID_LANGUAGE_LEVELS}")
        return v.upper() if v else v

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v: str) -> str:
        valid = {"online", "away", "dnd", "offline"}
        if v.lower() not in valid:
            raise ValueError(f"availability must be one of {valid}")
        return v.lower()


class UserProfileUpdate(BaseModel):
    bio: str | None = None
    native_language: str | None = None
    target_language: str | None = None
    language_level: str | None = None
    is_public: bool | None = None
    availability: str | None = None
    learning_goals: str | None = None

    @field_validator("language_level")
    @classmethod
    def validate_level(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v.upper() not in VALID_LANGUAGE_LEVELS:
            raise ValueError(f"language_level must be one of {VALID_LANGUAGE_LEVELS}")
        return v.upper()

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"online", "away", "dnd", "offline"}
        if v.lower() not in valid:
            raise ValueError(f"availability must be one of {valid}")
        return v.lower()


class UserProfileRead(BaseModel):
    telegram_id: int
    bio: str | None
    native_language: str | None
    target_language: str | None
    language_level: str | None
    profile_token: str
    is_public: bool
    xp: int
    level: int
    reputation_score: float
    streak_days: int
    longest_streak: int
    availability: str
    learning_goals: str | None
    total_anon_messages_received: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfilePublicRead(BaseModel):
    """Publicly visible profile info (no telegram_id exposed)."""
    bio: str | None
    native_language: str | None
    target_language: str | None
    language_level: str | None
    xp: int
    level: int
    reputation_score: float
    streak_days: int
    availability: str
    learning_goals: str | None

    model_config = {"from_attributes": True}
