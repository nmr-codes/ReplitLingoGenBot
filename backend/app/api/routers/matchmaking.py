from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.redis_client import get_user_session, get_session_data
from backend.app.schemas.session import MatchRequest, MatchResponse, SessionEnd
from backend.app.services.matchmaking_service import (
    request_match, cancel_search, end_session, get_session_partner
)
from backend.app.models.session import SessionStatus

router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


@router.post("/request", response_model=MatchResponse)
async def request_partner(data: MatchRequest, db: AsyncSession = Depends(get_db)):
    result = await request_match(db, data.telegram_id)
    return result


@router.post("/cancel")
async def cancel_partner_search(data: MatchRequest):
    await cancel_search(data.telegram_id)
    return {"status": "cancelled", "telegram_id": data.telegram_id}


@router.post("/end-session")
async def end_active_session(data: SessionEnd, db: AsyncSession = Depends(get_db)):
    session = await end_session(db, data.session_uuid, data.status)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ended", "session_uuid": data.session_uuid}


@router.get("/session/{telegram_id}")
async def get_active_session(telegram_id: int):
    session_uuid = await get_user_session(telegram_id)
    if not session_uuid:
        return {"active": False}
    data = await get_session_data(session_uuid)
    return {"active": True, "session_uuid": session_uuid, "data": data}


@router.get("/partner/{session_uuid}/{telegram_id}")
async def get_partner(session_uuid: str, telegram_id: int):
    partner = await get_session_partner(session_uuid, telegram_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {"partner_id": partner}
