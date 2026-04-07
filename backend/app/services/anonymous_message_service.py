from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.anonymous_message import AnonymousMessage
from backend.app.models.moderation import ModerationFlag
from backend.app.models.profile import UserProfile
from backend.app.schemas.anonymous_message import AnonymousMessageCreate
from backend.app.core.redis_client import check_anon_rate_limit
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)

MAX_MESSAGES_PER_HOUR = 5


async def send_anonymous_message(
    db: AsyncSession, data: AnonymousMessageCreate
) -> AnonymousMessage | None:
    """
    Look up recipient by token, enforce rate limit, persist the message.
    Returns None if rate-limited or profile not found.
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.profile_token == data.recipient_token)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        logger.warning(f"Anonymous message to unknown token {data.recipient_token}")
        return None

    if not profile.is_public:
        logger.warning(f"Anonymous message to private profile {profile.telegram_id}")
        return None

    within_limit = await check_anon_rate_limit(
        data.sender_id, profile.telegram_id, MAX_MESSAGES_PER_HOUR
    )
    if not within_limit:
        logger.info(f"Rate limit hit: sender={data.sender_id} → recipient={profile.telegram_id}")
        return None

    msg = AnonymousMessage(
        recipient_telegram_id=profile.telegram_id,
        content=data.content,
    )
    db.add(msg)
    profile.total_anon_messages_received += 1
    await db.flush()
    logger.info(f"Anonymous message {msg.id} sent to user {profile.telegram_id}")
    return msg


async def get_messages_for_user(
    db: AsyncSession, telegram_id: int, unread_only: bool = False
) -> list[AnonymousMessage]:
    query = select(AnonymousMessage).where(
        AnonymousMessage.recipient_telegram_id == telegram_id,
        AnonymousMessage.is_flagged.is_(False),
    )
    if unread_only:
        query = query.where(AnonymousMessage.is_read.is_(False))
    query = query.order_by(AnonymousMessage.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


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


async def vote_message(
    db: AsyncSession, message_id: int, vote: str
) -> AnonymousMessage | None:
    result = await db.execute(
        select(AnonymousMessage).where(AnonymousMessage.id == message_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return None
    if vote == "helpful":
        msg.helpful_votes += 1
    elif vote == "unhelpful":
        msg.unhelpful_votes += 1
    await db.flush()
    return msg


async def flag_message(
    db: AsyncSession, message_id: int, reported_by: int, reason: str
) -> ModerationFlag | None:
    result = await db.execute(
        select(AnonymousMessage).where(AnonymousMessage.id == message_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        return None
    msg.is_flagged = True
    flag = ModerationFlag(
        content_type="anonymous_message",
        content_id=message_id,
        reported_by=reported_by,
        reason=reason,
    )
    db.add(flag)
    await db.flush()
    logger.info(f"Message {message_id} flagged by {reported_by}")
    return flag
