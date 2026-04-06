from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserUpdate
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def get_or_create_user(db: AsyncSession, data: UserCreate) -> User:
    result = await db.execute(
        select(User).where(User.telegram_id == data.telegram_id)
    )
    user = result.scalar_one_or_none()

    if user:
        user.last_seen = datetime.now(timezone.utc)
        if data.username is not None:
            user.username = data.username
        if data.first_name is not None:
            user.first_name = data.first_name
        await db.flush()
        logger.info(f"User {data.telegram_id} updated.")
        return user

    user = User(
        telegram_id=data.telegram_id,
        username=data.username,
        first_name=data.first_name,
    )
    db.add(user)
    await db.flush()
    logger.info(f"New user registered: {data.telegram_id}")
    return user


async def get_user(db: AsyncSession, telegram_id: int) -> User | None:
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, telegram_id: int, data: UserUpdate) -> User | None:
    user = await get_user(db, telegram_id)
    if not user:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.flush()
    return user
