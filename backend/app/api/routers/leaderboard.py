from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.app.core.database import get_db
from backend.app.models.profile import UserProfile
from backend.app.models.user import User
from backend.app.models.user_statistics import UserStatistics
from backend.app.schemas.admin import LeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/global", response_model=list[LeaderboardEntry])
async def global_leaderboard(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserProfile).order_by(desc(UserProfile.xp)).limit(min(limit, 100))
    )
    profiles = result.scalars().all()
    entries: list[LeaderboardEntry] = []
    for rank, profile in enumerate(profiles, start=1):
        user_res = await db.execute(
            select(User).where(User.telegram_id == profile.telegram_id)
        )
        user = user_res.scalar_one_or_none()
        stats_res = await db.execute(
            select(UserStatistics).where(UserStatistics.telegram_id == profile.telegram_id)
        )
        stats = stats_res.scalar_one_or_none()
        entries.append(LeaderboardEntry(
            rank=rank,
            telegram_id=profile.telegram_id,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
            xp=profile.xp,
            level=profile.level,
            reputation_score=profile.reputation_score,
            total_conversations=stats.total_conversations if stats else 0,
        ))
    return entries


@router.get("/rank/{telegram_id}")
async def get_user_rank(telegram_id: int, db: AsyncSession = Depends(get_db)):
    profile_res = await db.execute(
        select(UserProfile).where(UserProfile.telegram_id == telegram_id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return {"rank": None, "xp": 0, "level": 1}

    rank_result = await db.execute(
        select(UserProfile).where(UserProfile.xp > profile.xp)
    )
    rank = len(rank_result.scalars().all()) + 1
    return {"telegram_id": telegram_id, "rank": rank, "xp": profile.xp, "level": profile.level}
