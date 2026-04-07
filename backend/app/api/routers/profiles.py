from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.profile import UserProfileCreate, UserProfileRead, UserProfilePublicRead, UserProfileUpdate
from backend.app.schemas.achievement import UserAchievementRead
from backend.app.schemas.admin import UserStatisticsRead
from backend.app.services.profile_service import get_or_create_profile, get_profile, get_profile_by_token, update_profile
from backend.app.services.achievement_service import get_user_achievements
from backend.app.services.statistics_service import get_stats

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=UserProfileRead)
async def create_or_get_profile(data: UserProfileCreate, db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_profile(db, data.telegram_id)
    # Apply any provided fields
    update_data = UserProfileUpdate(
        bio=data.bio,
        native_language=data.native_language,
        target_language=data.target_language,
        language_level=data.language_level,
        is_public=data.is_public,
        availability=data.availability,
        learning_goals=data.learning_goals,
    )
    profile = await update_profile(db, data.telegram_id, update_data)
    return profile


@router.get("/{telegram_id}", response_model=UserProfileRead)
async def fetch_profile(telegram_id: int, db: AsyncSession = Depends(get_db)):
    profile = await get_profile(db, telegram_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/{telegram_id}", response_model=UserProfileRead)
async def patch_profile(telegram_id: int, data: UserProfileUpdate, db: AsyncSession = Depends(get_db)):
    profile = await update_profile(db, telegram_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/public/{token}", response_model=UserProfilePublicRead)
async def fetch_public_profile(token: str, db: AsyncSession = Depends(get_db)):
    profile = await get_profile_by_token(db, token)
    if not profile or not profile.is_public:
        raise HTTPException(status_code=404, detail="Profile not found or private")
    return profile


@router.get("/by-token/{token}", response_model=UserProfileRead)
async def fetch_profile_by_token(token: str, db: AsyncSession = Depends(get_db)):
    """Internal endpoint: return full profile (including telegram_id) by token."""
    profile = await get_profile_by_token(db, token)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/{telegram_id}/achievements", response_model=list[UserAchievementRead])
async def fetch_achievements(telegram_id: int, db: AsyncSession = Depends(get_db)):
    return await get_user_achievements(db, telegram_id)


@router.get("/{telegram_id}/stats", response_model=UserStatisticsRead)
async def fetch_user_stats(telegram_id: int, db: AsyncSession = Depends(get_db)):
    stats = await get_stats(db, telegram_id)
    if not stats:
        raise HTTPException(status_code=404, detail="No statistics found for this user")
    return stats
