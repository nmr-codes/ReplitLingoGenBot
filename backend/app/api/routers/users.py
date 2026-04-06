from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.user import UserCreate, UserRead
from backend.app.services.user_service import get_or_create_user, get_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserRead)
async def register_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await get_or_create_user(db, data)
    return user


@router.get("/{telegram_id}", response_model=UserRead)
async def fetch_user(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
