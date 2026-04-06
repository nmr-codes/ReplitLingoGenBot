from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

# Predefined achievement codes
ACHIEVEMENT_FIRST_CHAT = "first_chat"
ACHIEVEMENT_SOCIAL_BUTTERFLY = "social_butterfly"      # 10 conversations
ACHIEVEMENT_CHATTERBOX = "chatterbox"                  # 100 conversations
ACHIEVEMENT_PERFECT_RATING = "perfect_rating"          # receive a 5-star
ACHIEVEMENT_TOP_RATED = "top_rated"                    # 4.5+ avg with 10+ ratings
ACHIEVEMENT_HELPFUL_RATER = "helpful_rater"            # rate 10 sessions
ACHIEVEMENT_MESSAGE_MASTER = "message_master"          # send 100 messages
ACHIEVEMENT_RISING_STAR = "rising_star"                # reach level 5
ACHIEVEMENT_VETERAN = "veteran"                        # reach level 20
ACHIEVEMENT_STREAK_7 = "streak_7"                      # 7-day streak
ACHIEVEMENT_ANON_POPULAR = "anon_popular"              # receive 10 anonymous messages

ACHIEVEMENTS_META: dict[str, dict] = {
    ACHIEVEMENT_FIRST_CHAT: {
        "name": "First Chat",
        "description": "Complete your first conversation",
        "xp_reward": 20,
        "emoji": "🎉",
    },
    ACHIEVEMENT_SOCIAL_BUTTERFLY: {
        "name": "Social Butterfly",
        "description": "Complete 10 conversations",
        "xp_reward": 50,
        "emoji": "🦋",
    },
    ACHIEVEMENT_CHATTERBOX: {
        "name": "Chatterbox",
        "description": "Complete 100 conversations",
        "xp_reward": 200,
        "emoji": "💬",
    },
    ACHIEVEMENT_PERFECT_RATING: {
        "name": "Perfect Rating",
        "description": "Receive your first 5-star rating",
        "xp_reward": 25,
        "emoji": "⭐",
    },
    ACHIEVEMENT_TOP_RATED: {
        "name": "Top Rated",
        "description": "Maintain 4.5+ average rating with 10+ ratings",
        "xp_reward": 100,
        "emoji": "🏅",
    },
    ACHIEVEMENT_HELPFUL_RATER: {
        "name": "Helpful Rater",
        "description": "Rate 10 sessions",
        "xp_reward": 30,
        "emoji": "✅",
    },
    ACHIEVEMENT_MESSAGE_MASTER: {
        "name": "Message Master",
        "description": "Send 100 messages",
        "xp_reward": 50,
        "emoji": "✉️",
    },
    ACHIEVEMENT_RISING_STAR: {
        "name": "Rising Star",
        "description": "Reach level 5",
        "xp_reward": 50,
        "emoji": "🌟",
    },
    ACHIEVEMENT_VETERAN: {
        "name": "Veteran",
        "description": "Reach level 20",
        "xp_reward": 150,
        "emoji": "🎖️",
    },
    ACHIEVEMENT_STREAK_7: {
        "name": "On Fire",
        "description": "Maintain a 7-day conversation streak",
        "xp_reward": 75,
        "emoji": "🔥",
    },
    ACHIEVEMENT_ANON_POPULAR: {
        "name": "Popular",
        "description": "Receive 10 anonymous messages",
        "xp_reward": 30,
        "emoji": "📬",
    },
}


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    achievement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<UserAchievement telegram_id={self.telegram_id} code={self.achievement_code}>"
