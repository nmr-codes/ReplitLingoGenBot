from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.message import AnonMessageCreate, AnonMessageRead, AnonMessageReply
from backend.app.services.message_service import (
    check_rate_limit,
    send_anonymous_message,
    get_messages_for_user,
    count_unread_messages,
    mark_message_read,
    mark_all_read,
    reply_to_message,
)

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/{profile_slug}", response_model=AnonMessageRead)
async def send_message(
    profile_slug: str,
    data: AnonMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    allowed = await check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many messages. Please wait before sending another.",
        )

    msg = await send_anonymous_message(db, profile_slug, data)
    if msg is None:
        raise HTTPException(status_code=404, detail="Profile not found or is private")
    return msg


@router.get("/inbox/{telegram_id}", response_model=list[AnonMessageRead])
async def get_inbox(
    telegram_id: int,
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    msgs = await get_messages_for_user(db, telegram_id, unread_only, limit, offset)
    return msgs


@router.get("/inbox/{telegram_id}/count")
async def get_unread_count(telegram_id: int, db: AsyncSession = Depends(get_db)):
    count = await count_unread_messages(db, telegram_id)
    return {"unread": count}


@router.post("/inbox/{telegram_id}/read-all")
async def read_all_messages(telegram_id: int, db: AsyncSession = Depends(get_db)):
    count = await mark_all_read(db, telegram_id)
    return {"marked_read": count}


@router.post("/inbox/{telegram_id}/{message_id}/read")
async def read_message(
    telegram_id: int, message_id: int, db: AsyncSession = Depends(get_db)
):
    ok = await mark_message_read(db, message_id, telegram_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"ok": True}


@router.post("/inbox/{telegram_id}/{message_id}/reply", response_model=AnonMessageRead)
async def reply_message(
    telegram_id: int,
    message_id: int,
    data: AnonMessageReply,
    db: AsyncSession = Depends(get_db),
):
    msg = await reply_to_message(db, message_id, telegram_id, data)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg
