import re
import random
import string
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.profile import UserProfile
from backend.app.schemas.profile import ProfileCreate, ProfileUpdate
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


def _generate_slug(base: str) -> str:
    """Generate a URL-friendly slug from a base string."""
    slug = re.sub(r"[^a-z0-9_]", "", base.lower().replace(" ", "_"))
    slug = slug[:32] if slug else "user"
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{slug}_{suffix}"


async def get_profile(db: AsyncSession, telegram_id: int) -> UserProfile | None:
    result = await db.execute(
        select(UserProfile).where(UserProfile.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_profile_by_slug(db: AsyncSession, slug: str) -> UserProfile | None:
    result = await db.execute(
        select(UserProfile).where(UserProfile.profile_slug == slug)
    )
    return result.scalar_one_or_none()


async def create_profile(db: AsyncSession, data: ProfileCreate) -> UserProfile:
    from backend.app.models.user import User
    user_result = await db.execute(
        select(User).where(User.telegram_id == data.telegram_id)
    )
    user = user_result.scalar_one_or_none()

    base = (
        data.display_name
        or (user.username if user else None)
        or (user.first_name if user else None)
        or "user"
    )
    slug = _generate_slug(base)

    # Ensure slug is unique
    attempts = 0
    while attempts < 5:
        existing = await get_profile_by_slug(db, slug)
        if not existing:
            break
        slug = _generate_slug(base)
        attempts += 1

    profile = UserProfile(
        telegram_id=data.telegram_id,
        profile_slug=slug,
        display_name=data.display_name,
        bio=data.bio,
        language_level=data.language_level,
        is_public=data.is_public,
    )
    db.add(profile)
    await db.flush()
    logger.info(f"Created profile for user {data.telegram_id} with slug '{slug}'")
    return profile


async def update_profile(
    db: AsyncSession, telegram_id: int, data: ProfileUpdate
) -> UserProfile | None:
    profile = await get_profile(db, telegram_id)
    if not profile:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return profile


async def get_or_create_profile(db: AsyncSession, data: ProfileCreate) -> UserProfile:
    profile = await get_profile(db, data.telegram_id)
    if profile:
        return profile
    return await create_profile(db, data)
