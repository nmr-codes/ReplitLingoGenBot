from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.session import SessionRead
from backend.app.schemas.rating import RatingCreate, RatingRead
from backend.app.services.session_service import get_session, create_rating, get_session_ratings

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_uuid}", response_model=SessionRead)
async def fetch_session(session_uuid: str, db: AsyncSession = Depends(get_db)):
    session = await get_session(db, session_uuid)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/rating", response_model=RatingRead)
async def submit_rating(data: RatingCreate, db: AsyncSession = Depends(get_db)):
    rating = await create_rating(db, data)
    return rating


@router.get("/{session_uuid}/ratings", response_model=list[RatingRead])
async def fetch_ratings(session_uuid: str, db: AsyncSession = Depends(get_db)):
    return await get_session_ratings(db, session_uuid)
