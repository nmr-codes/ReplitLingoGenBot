from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.user_statistics import UserStatistics
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def get_or_create_stats(db: AsyncSession, telegram_id: int) -> UserStatistics:
    result = await db.execute(
        select(UserStatistics).where(UserStatistics.telegram_id == telegram_id)
    )
    stats = result.scalar_one_or_none()
    if stats:
        return stats
    stats = UserStatistics(telegram_id=telegram_id)
    db.add(stats)
    await db.flush()
    return stats


async def get_stats(db: AsyncSession, telegram_id: int) -> UserStatistics | None:
    result = await db.execute(
        select(UserStatistics).where(UserStatistics.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def record_conversation_completed(
    db: AsyncSession, telegram_id: int, duration_seconds: int = 0
) -> UserStatistics:
    stats = await get_or_create_stats(db, telegram_id)
    stats.total_conversations += 1
    stats.conversations_completed += 1
    stats.total_session_duration_seconds += duration_seconds
    stats.last_conversation_at = datetime.now(timezone.utc)
    stats.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return stats


async def record_messages_sent(db: AsyncSession, telegram_id: int, count: int = 1) -> UserStatistics:
    stats = await get_or_create_stats(db, telegram_id)
    stats.total_messages_sent += count
    stats.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return stats


async def record_rating_given(db: AsyncSession, telegram_id: int, score: int) -> UserStatistics:
    stats = await get_or_create_stats(db, telegram_id)
    # Running average for ratings given
    total = stats.avg_rating_given * stats.ratings_given_count + score
    stats.ratings_given_count += 1
    stats.avg_rating_given = round(total / stats.ratings_given_count, 2)
    stats.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return stats


async def record_rating_received(db: AsyncSession, telegram_id: int, score: int) -> UserStatistics:
    stats = await get_or_create_stats(db, telegram_id)
    # Running average for ratings received
    total = stats.avg_rating_received * stats.ratings_received_count + score
    stats.ratings_received_count += 1
    stats.avg_rating_received = round(total / stats.ratings_received_count, 2)
    stats.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return stats
