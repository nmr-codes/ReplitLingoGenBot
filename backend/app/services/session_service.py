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

    # Update statistics and XP for rater
    try:
        from backend.app.services.statistics_service import record_rating_given
        from backend.app.services.profile_service import add_xp
        await record_rating_given(db, data.rater_telegram_id, data.score)
        await add_xp(db, data.rater_telegram_id, 5)  # XP for giving a rating
    except Exception as e:
        logger.error(f"Failed to update stats/XP for rater {data.rater_telegram_id}: {e}")

    # Identify who was rated and update their stats/reputation
    try:
        session_result = await db.execute(
            select(Session).where(Session.session_uuid == data.session_uuid)
        )
        session = session_result.scalar_one_or_none()
        if session:
            rated_id = (
                session.user2_id
                if session.user1_id == data.rater_telegram_id
                else session.user1_id
            )
            from backend.app.services.statistics_service import record_rating_received
            stats = await record_rating_received(db, rated_id, data.score)
            # Update reputation score on profile
            from backend.app.services.profile_service import update_reputation
            await update_reputation(db, rated_id, stats.avg_rating_received)
            # Award XP for high ratings
            if data.score == 5:
                await add_xp(db, rated_id, 25)
            # Check achievements
            from backend.app.services.achievement_service import check_and_award_achievements
            await check_and_award_achievements(db, rated_id)
            await check_and_award_achievements(db, data.rater_telegram_id)
    except Exception as e:
        logger.error(f"Failed to update rated user stats: {e}")

    return rating


async def get_session_ratings(db: AsyncSession, session_uuid: str) -> list[Rating]:
    result = await db.execute(
        select(Rating).where(Rating.session_uuid == session_uuid)
    )
    return list(result.scalars().all())
