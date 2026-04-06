from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate, ProfilePublic
from backend.app.services.profile_service import (
    get_profile,
    get_profile_by_slug,
    create_profile,
    update_profile,
    get_or_create_profile,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileRead)
async def create_user_profile(data: ProfileCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_profile(db, data.telegram_id)
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists")
    profile = await create_profile(db, data)
    return profile


@router.get("/me/{telegram_id}", response_model=ProfileRead)
async def get_my_profile(telegram_id: int, db: AsyncSession = Depends(get_db)):
    profile = await get_profile(db, telegram_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/me/{telegram_id}", response_model=ProfileRead)
async def update_my_profile(
    telegram_id: int, data: ProfileUpdate, db: AsyncSession = Depends(get_db)
):
    profile = await update_profile(db, telegram_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/get-or-create", response_model=ProfileRead)
async def get_or_create_user_profile(data: ProfileCreate, db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_profile(db, data)
    return profile


@router.get("/{slug}", response_model=ProfilePublic)
async def get_public_profile(slug: str, db: AsyncSession = Depends(get_db)):
    profile = await get_profile_by_slug(db, slug)
    if not profile or not profile.is_public:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
