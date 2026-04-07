from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.channel import RequiredChannel
from backend.app.schemas.channel import RequiredChannelCreate, RequiredChannelRead
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def list_active_channels(db: AsyncSession) -> list[RequiredChannelRead]:
    """Return all currently-active required channels."""
    result = await db.execute(
        select(RequiredChannel)
        .where(RequiredChannel.is_active == True)  # noqa: E712
        .order_by(RequiredChannel.id)
    )
    channels = result.scalars().all()
    return [RequiredChannelRead.model_validate(c) for c in channels]


async def list_all_channels(db: AsyncSession) -> list[RequiredChannelRead]:
    """Return all channels (active and inactive) — for admin panel."""
    result = await db.execute(
        select(RequiredChannel).order_by(RequiredChannel.id)
    )
    channels = result.scalars().all()
    return [RequiredChannelRead.model_validate(c) for c in channels]


async def add_channel(
    db: AsyncSession, data: RequiredChannelCreate
) -> RequiredChannelRead:
    """Add a new required channel, or reactivate an existing one."""
    existing_result = await db.execute(
        select(RequiredChannel).where(RequiredChannel.channel_id == data.channel_id)
    )
    channel = existing_result.scalar_one_or_none()

    if channel:
        # Reactivate and update metadata
        channel.is_active = True
        channel.channel_username = data.channel_username
        channel.title = data.title
        if data.invite_link:
            channel.invite_link = data.invite_link
        await db.flush()
        logger.info(f"Required channel reactivated: {data.title} ({data.channel_id})")
        return RequiredChannelRead.model_validate(channel)

    channel = RequiredChannel(
        channel_id=data.channel_id,
        channel_username=data.channel_username,
        title=data.title,
        invite_link=data.invite_link,
    )
    db.add(channel)
    await db.flush()
    logger.info(f"Required channel added: {data.title} ({data.channel_id})")
    return RequiredChannelRead.model_validate(channel)


async def remove_channel(db: AsyncSession, channel_db_id: int) -> bool:
    """Soft-delete a required channel (sets is_active=False)."""
    result = await db.execute(
        select(RequiredChannel).where(RequiredChannel.id == channel_db_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        return False

    channel.is_active = False
    await db.flush()
    logger.info(f"Required channel deactivated: {channel.title} (db_id={channel_db_id})")
    return True
