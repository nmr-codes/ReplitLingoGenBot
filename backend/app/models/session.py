from datetime import datetime, timezone
from sqlalchemy import BigInteger, String, DateTime, Enum as SAEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column
import enum
from backend.app.core.database import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    TIMEOUT = "timeout"


class Session(Base):
    __tablename__ = "sessions"

    session_uuid: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user1_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user2_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Session uuid={self.session_uuid} status={self.status}>"
