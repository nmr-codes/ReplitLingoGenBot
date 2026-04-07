from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.channel import RequiredChannelRead
from backend.app.services.channel_service import list_active_channels

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=list[RequiredChannelRead])
async def get_required_channels(db: AsyncSession = Depends(get_db)):
    """Return the list of Telegram channels users must join to use the bot."""
    return await list_active_channels(db)
