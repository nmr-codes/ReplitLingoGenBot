from datetime import datetime, timezone
from sqlalchemy import BigInteger, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} username={self.username}>"
