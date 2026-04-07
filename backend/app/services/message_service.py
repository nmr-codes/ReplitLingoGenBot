from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.models.admin import AnonymousMessage
from backend.app.models.profile import UserProfile
from backend.app.schemas.message import AnonMessageCreate, AnonMessageReply
from backend.app.core.logging_config import get_logger
from backend.app.core.redis_client import get_redis

logger = get_logger(__name__)

RATE_LIMIT_KEY_PREFIX = "anon_msg_rate:"
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds


async def check_rate_limit(sender_ip: str) -> bool:
    """Returns True if the sender is within rate limits."""
    try:
        r = await get_redis()
        key = f"{RATE_LIMIT_KEY_PREFIX}{sender_ip}"
        count = await r.get(key)
        if count and int(count) >= RATE_LIMIT_MAX:
            return False
        pipe = r.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, RATE_LIMIT_WINDOW)
        await pipe.execute()
        return True
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}. Allowing message.")
        return True


async def send_anonymous_message(
    db: AsyncSession, profile_slug: str, data: AnonMessageCreate
) -> AnonymousMessage | None:
    result = await db.execute(
        select(UserProfile).where(UserProfile.profile_slug == profile_slug)
    )
    profile = result.scalar_one_or_none()
    if not profile or not profile.is_public:
        return None

    msg = AnonymousMessage(
        recipient_telegram_id=profile.telegram_id,
        content=data.content,
        sender_token=data.sender_token,
    )
    db.add(msg)

    # Increment the counter on the profile
    profile.messages_received += 1
    await db.flush()
    logger.info(f"Anonymous message sent to {profile.telegram_id}")
    return msg


async def get_messages_for_user(
    db: AsyncSession, telegram_id: int, unread_only: bool = False, limit: int = 20, offset: int = 0
) -> list[AnonymousMessage]:
    query = select(AnonymousMessage).where(
        AnonymousMessage.recipient_telegram_id == telegram_id
    )
    if unread_only:
        query = query.where(AnonymousMessage.is_read == False)  # noqa: E712
    query = query.order_by(AnonymousMessage.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_unread_messages(db: AsyncSession, telegram_id: int) -> int:
    result = await db.execute(
        select(func.count(AnonymousMessage.id)).where(
            AnonymousMessage.recipient_telegram_id == telegram_id,
            AnonymousMessage.is_read == False,  # noqa: E712
        )
    )
    return result.scalar_one() or 0


async def mark_message_read(db: AsyncSession, message_id: int, telegram_id: int) -> bool:
    result = await db.execute(
        select(AnonymousMessage).where(
            AnonymousMessage.id == message_id,
            AnonymousMessage.recipient_telegram_id == telegram_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return False
    msg.is_read = True
    await db.flush()
    return True


async def mark_all_read(db: AsyncSession, telegram_id: int) -> int:
    result = await db.execute(
        select(AnonymousMessage).where(
            AnonymousMessage.recipient_telegram_id == telegram_id,
            AnonymousMessage.is_read == False,  # noqa: E712
        )
    )
    msgs = result.scalars().all()
    for msg in msgs:
        msg.is_read = True
    await db.flush()
    return len(msgs)


async def reply_to_message(
    db: AsyncSession, message_id: int, telegram_id: int, data: AnonMessageReply
) -> AnonymousMessage | None:
    result = await db.execute(
        select(AnonymousMessage).where(
            AnonymousMessage.id == message_id,
            AnonymousMessage.recipient_telegram_id == telegram_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return None
    msg.reply_content = data.reply_content
    msg.replied_at = datetime.now(timezone.utc)
    msg.is_read = True
    await db.flush()
    return msg
