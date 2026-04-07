from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class AnonymousMessage(Base):
    __tablename__ = "anonymous_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # Sender identity is intentionally NOT stored — rate-limit key is ephemeral in Redis
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    helpful_votes: Mapped[int] = mapped_column(Integer, default=0)
    unhelpful_votes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AnonymousMessage id={self.id} recipient={self.recipient_telegram_id}>"
