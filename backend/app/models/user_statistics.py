from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class UserStatistics(Base):
    __tablename__ = "user_statistics"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    total_messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_messages_received: Mapped[int] = mapped_column(Integer, default=0)
    conversations_completed: Mapped[int] = mapped_column(Integer, default=0)
    # Ratings
    ratings_given_count: Mapped[int] = mapped_column(Integer, default=0)
    ratings_received_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating_received: Mapped[float] = mapped_column(Float, default=0.0)
    avg_rating_given: Mapped[float] = mapped_column(Float, default=0.0)
    # Duration
    total_session_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    last_conversation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<UserStatistics telegram_id={self.telegram_id} conversations={self.total_conversations}>"
