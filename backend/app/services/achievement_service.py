from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.achievement import UserAchievement, ACHIEVEMENTS_META
from backend.app.models.profile import UserProfile
from backend.app.models.user_statistics import UserStatistics
from backend.app.schemas.achievement import UserAchievementRead
from backend.app.services.profile_service import add_xp
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def get_user_achievements(db: AsyncSession, telegram_id: int) -> list[UserAchievementRead]:
    result = await db.execute(
        select(UserAchievement).where(UserAchievement.telegram_id == telegram_id).order_by(UserAchievement.unlocked_at)
    )
    rows = result.scalars().all()
    out: list[UserAchievementRead] = []
    for row in rows:
        meta = ACHIEVEMENTS_META.get(row.achievement_code, {})
        out.append(UserAchievementRead(
            achievement_code=row.achievement_code,
            name=meta.get("name", row.achievement_code),
            description=meta.get("description", ""),
            emoji=meta.get("emoji", "🏆"),
            xp_reward=meta.get("xp_reward", 0),
            unlocked_at=row.unlocked_at,
        ))
    return out


async def _has_achievement(db: AsyncSession, telegram_id: int, code: str) -> bool:
    result = await db.execute(
        select(UserAchievement).where(
            UserAchievement.telegram_id == telegram_id,
            UserAchievement.achievement_code == code,
        )
    )
    return result.scalar_one_or_none() is not None


async def _award_achievement(
    db: AsyncSession, telegram_id: int, code: str
) -> UserAchievementRead | None:
    """Award achievement if not already unlocked. Returns the achievement or None."""
    if await _has_achievement(db, telegram_id, code):
        return None

    meta = ACHIEVEMENTS_META.get(code)
    if not meta:
        return None

    ua = UserAchievement(telegram_id=telegram_id, achievement_code=code)
    db.add(ua)
    await db.flush()

    # Award XP bonus for the achievement
    xp_reward = meta.get("xp_reward", 0)
    if xp_reward:
        await add_xp(db, telegram_id, xp_reward)

    logger.info(f"Achievement '{code}' awarded to user {telegram_id}")
    return UserAchievementRead(
        achievement_code=code,
        name=meta["name"],
        description=meta["description"],
        emoji=meta["emoji"],
        xp_reward=xp_reward,
        unlocked_at=ua.unlocked_at,
    )


async def check_and_award_achievements(
    db: AsyncSession,
    telegram_id: int,
) -> list[UserAchievementRead]:
    """
    Check all achievement conditions for a user and award any newly unlocked ones.
    Returns list of newly awarded achievements.
    """
    from backend.app.models.achievement import (
        ACHIEVEMENT_FIRST_CHAT, ACHIEVEMENT_SOCIAL_BUTTERFLY, ACHIEVEMENT_CHATTERBOX,
        ACHIEVEMENT_PERFECT_RATING, ACHIEVEMENT_TOP_RATED, ACHIEVEMENT_HELPFUL_RATER,
        ACHIEVEMENT_MESSAGE_MASTER, ACHIEVEMENT_RISING_STAR, ACHIEVEMENT_VETERAN,
        ACHIEVEMENT_STREAK_7, ACHIEVEMENT_ANON_POPULAR,
    )

    stats_result = await db.execute(
        select(UserStatistics).where(UserStatistics.telegram_id == telegram_id)
    )
    stats = stats_result.scalar_one_or_none()

    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.telegram_id == telegram_id)
    )
    profile = profile_result.scalar_one_or_none()

    newly_unlocked: list[UserAchievementRead] = []

    if stats is None and profile is None:
        return newly_unlocked

    if stats:
        # Conversation-based
        if stats.total_conversations >= 1:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_FIRST_CHAT)
            if ach:
                newly_unlocked.append(ach)
        if stats.total_conversations >= 10:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_SOCIAL_BUTTERFLY)
            if ach:
                newly_unlocked.append(ach)
        if stats.total_conversations >= 100:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_CHATTERBOX)
            if ach:
                newly_unlocked.append(ach)
        # Rating-based
        if stats.ratings_received_count >= 1 and stats.avg_rating_received >= 5.0:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_PERFECT_RATING)
            if ach:
                newly_unlocked.append(ach)
        if stats.ratings_received_count >= 10 and stats.avg_rating_received >= 4.5:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_TOP_RATED)
            if ach:
                newly_unlocked.append(ach)
        if stats.ratings_given_count >= 10:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_HELPFUL_RATER)
            if ach:
                newly_unlocked.append(ach)
        # Message-based
        if stats.total_messages_sent >= 100:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_MESSAGE_MASTER)
            if ach:
                newly_unlocked.append(ach)

    if profile:
        # Level-based
        if profile.level >= 5:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_RISING_STAR)
            if ach:
                newly_unlocked.append(ach)
        if profile.level >= 20:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_VETERAN)
            if ach:
                newly_unlocked.append(ach)
        # Streak-based
        if profile.streak_days >= 7:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_STREAK_7)
            if ach:
                newly_unlocked.append(ach)
        # Anonymous message popularity
        if profile.total_anon_messages_received >= 10:
            ach = await _award_achievement(db, telegram_id, ACHIEVEMENT_ANON_POPULAR)
            if ach:
                newly_unlocked.append(ach)

    return newly_unlocked
