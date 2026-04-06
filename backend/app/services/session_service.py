from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.session import Session, SessionStatus
from backend.app.models.rating import Rating
from backend.app.schemas.rating import RatingCreate
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def get_session(db: AsyncSession, session_uuid: str) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.session_uuid == session_uuid)
    )
    return result.scalar_one_or_none()


async def create_rating(db: AsyncSession, data: RatingCreate) -> Rating:
    existing = await db.execute(
        select(Rating).where(
            Rating.session_uuid == data.session_uuid,
            Rating.rater_telegram_id == data.rater_telegram_id,
        )
    )
    existing_rating = existing.scalar_one_or_none()
    if existing_rating:
        existing_rating.score = data.score
        await db.flush()
        logger.info(f"Rating updated for session {data.session_uuid} by user {data.rater_telegram_id}")
        return existing_rating

    rating = Rating(
        session_uuid=data.session_uuid,
        rater_telegram_id=data.rater_telegram_id,
        score=data.score,
    )
    db.add(rating)
    await db.flush()
    logger.info(f"Rating saved: session={data.session_uuid}, user={data.rater_telegram_id}, score={data.score}")
    return rating


async def get_session_ratings(db: AsyncSession, session_uuid: str) -> list[Rating]:
    result = await db.execute(
        select(Rating).where(Rating.session_uuid == session_uuid)
    )
    return list(result.scalars().all())
