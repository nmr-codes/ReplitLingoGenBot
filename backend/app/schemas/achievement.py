from datetime import datetime
from pydantic import BaseModel


class AchievementInfo(BaseModel):
    code: str
    name: str
    description: str
    xp_reward: int
    emoji: str


class UserAchievementRead(BaseModel):
    achievement_code: str
    name: str
    description: str
    emoji: str
    xp_reward: int
    unlocked_at: datetime

    model_config = {"from_attributes": True}
