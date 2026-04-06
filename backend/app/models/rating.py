from datetime import datetime, timezone
from sqlalchemy import BigInteger, SmallInteger, String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rater_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Rating session={self.session_uuid} score={self.score}>"
