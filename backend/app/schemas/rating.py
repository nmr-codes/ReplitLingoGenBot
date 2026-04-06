from datetime import datetime
from pydantic import BaseModel, field_validator


class RatingCreate(BaseModel):
    session_uuid: str
    rater_telegram_id: int
    score: int

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Score must be between 1 and 5")
        return v


class RatingRead(BaseModel):
    session_uuid: str
    rater_telegram_id: int
    score: int
    created_at: datetime

    model_config = {"from_attributes": True}
