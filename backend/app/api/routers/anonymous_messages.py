from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.anonymous_message import (
    AnonymousMessageCreate, AnonymousMessageRead, MessageVote, MessageFlag
)
from backend.app.services.anonymous_message_service import (
    send_anonymous_message, get_messages_for_user, mark_message_read, vote_message,
    flag_message, count_unread_messages, mark_all_read, reply_to_message,
)

router = APIRouter(prefix="/messages", tags=["anonymous_messages"])


class _ReplyBody(BaseModel):
    reply_content: str


@router.post("/send", response_model=AnonymousMessageRead)
async def send_message(data: AnonymousMessageCreate, db: AsyncSession = Depends(get_db)):
    msg = await send_anonymous_message(db, data)
    if not msg:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded or profile not found / private",
        )
    return msg


@router.get("/inbox/{telegram_id}", response_model=list[AnonymousMessageRead])
async def get_inbox(
    telegram_id: int,
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await get_messages_for_user(db, telegram_id, unread_only=unread_only, limit=limit, offset=offset)


@router.get("/inbox/{telegram_id}/count")
async def get_unread_count(telegram_id: int, db: AsyncSession = Depends(get_db)):
    count = await count_unread_messages(db, telegram_id)
    return {"unread": count}


@router.post("/inbox/{telegram_id}/read-all")
async def read_all_messages(telegram_id: int, db: AsyncSession = Depends(get_db)):
    count = await mark_all_read(db, telegram_id)
    return {"marked_read": count}


@router.post("/inbox/{telegram_id}/{message_id}/reply", response_model=AnonymousMessageRead)
async def reply_message(
    telegram_id: int,
    message_id: int,
    data: _ReplyBody,
    db: AsyncSession = Depends(get_db),
):
    msg = await reply_to_message(db, message_id, telegram_id, data.reply_content)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg


@router.get("/{telegram_id}", response_model=list[AnonymousMessageRead])
async def get_messages(telegram_id: int, unread_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await get_messages_for_user(db, telegram_id, unread_only=unread_only)


@router.patch("/{message_id}/read")
async def read_message(message_id: int, telegram_id: int, db: AsyncSession = Depends(get_db)):
    ok = await mark_message_read(db, message_id, telegram_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "ok"}


@router.post("/vote", response_model=AnonymousMessageRead)
async def vote_on_message(data: MessageVote, db: AsyncSession = Depends(get_db)):
    msg = await vote_message(db, data.message_id, data.vote)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg


@router.post("/flag")
async def flag_a_message(data: MessageFlag, db: AsyncSession = Depends(get_db)):
    flag = await flag_message(db, data.message_id, data.reported_by, data.reason)
    if not flag:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "flagged", "flag_id": flag.id}
