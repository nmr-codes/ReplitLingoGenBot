import secrets
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.profile import UserProfile
from backend.app.schemas.profile import UserProfileCreate, UserProfileUpdate
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)

XP_PER_CONVERSATION = 10
XP_PER_MESSAGE_BATCH = 5    # awarded per 10 messages sent
XP_FOR_FIVE_STAR = 25
XP_FOR_GIVING_RATING = 5

LEVEL_XP_THRESHOLD = 100    # XP needed per level


def _calculate_level(xp: int) -> int:
    level = 1 + xp // LEVEL_XP_THRESHOLD
    return min(level, 50)


async def get_or_create_profile(db: AsyncSession, telegram_id: int) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
    profile = result.scalar_one_or_none()
    if profile:
        return profile

    profile = UserProfile(
        telegram_id=telegram_id,
        profile_token=secrets.token_urlsafe(16),
    )
    db.add(profile)
    await db.flush()
    logger.info(f"Created profile for user {telegram_id}")
    return profile


async def get_profile(db: AsyncSession, telegram_id: int) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_profile_by_token(db: AsyncSession, token: str) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.profile_token == token))
    return result.scalar_one_or_none()


async def update_profile(db: AsyncSession, telegram_id: int, data: UserProfileUpdate) -> UserProfile | None:
    profile = await get_or_create_profile(db, telegram_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(timezone.utc)
    await db.flush()
    logger.info(f"Profile updated for user {telegram_id}")
    return profile


async def add_xp(db: AsyncSession, telegram_id: int, amount: int) -> tuple[UserProfile, list[str]]:
    """Add XP and return the updated profile + list of newly unlocked level milestones."""
    profile = await get_or_create_profile(db, telegram_id)
    old_level = profile.level
    profile.xp += amount
    profile.level = _calculate_level(profile.xp)
    await db.flush()

    level_ups: list[str] = []
    if profile.level > old_level:
        for lvl in range(old_level + 1, profile.level + 1):
            level_ups.append(f"Level {lvl}")

    return profile, level_ups


async def update_reputation(db: AsyncSession, telegram_id: int, new_avg: float) -> UserProfile:
    profile = await get_or_create_profile(db, telegram_id)
    profile.reputation_score = round(new_avg * 20, 1)  # scale 0-5 → 0-100
    await db.flush()
    return profile


async def update_streak(db: AsyncSession, telegram_id: int) -> int:
    """Update daily streak. Returns current streak count."""
    profile = await get_or_create_profile(db, telegram_id)
    today = datetime.now(timezone.utc).date()
    if profile.last_streak_date:
        last = profile.last_streak_date.date()
        diff = (today - last).days
        if diff == 0:
            return profile.streak_days  # already counted today
        elif diff == 1:
            profile.streak_days += 1
        else:
            profile.streak_days = 1
    else:
        profile.streak_days = 1

    if profile.streak_days > profile.longest_streak:
        profile.longest_streak = profile.streak_days
    profile.last_streak_date = datetime.now(timezone.utc)
    await db.flush()
    return profile.streak_days
