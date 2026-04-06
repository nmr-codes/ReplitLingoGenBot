import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()

CONTROL_TEXTS = {
    "🔍 Find Partner",
    "❌ Stop Searching",
    "🚪 End Session",
    "ℹ️ Help",
    "🪪 My Profile",
    "📬 Messages",
    "/start",
    "/help",
    "/profile",
    "/profile_url",
    "/messages",
    "/skip",
}


async def get_session_info(telegram_id: int) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/session/{telegram_id}",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            data = await resp.json()
            return data if data.get("active") else None
    except Exception as e:
        logger.error(f"Session info error for {telegram_id}: {e}")
        return None


async def get_partner_id(session_uuid: str, telegram_id: int) -> int | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/partner/{session_uuid}/{telegram_id}",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            if resp.status == 200:
                data = await resp.json()
                return data.get("partner_id")
    except Exception as e:
        logger.error(f"Get partner error: {e}")
    return None


@router.message(F.text & ~F.text.in_(CONTROL_TEXTS))
async def relay_message(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user or not message.text:
        return

    session_info = await get_session_info(user.id)
    if not session_info:
        await message.answer(
            "💬 <b>You are not in a session.</b>\n"
            "Press <b>🔍 Find Partner</b> to get matched!",
            parse_mode="HTML",
        )
        return

    session_uuid = session_info.get("session_uuid")
    if not session_uuid:
        return

    partner_id = await get_partner_id(session_uuid, user.id)
    if not partner_id:
        await message.answer(
            "⚠️ Could not reach your partner. The session may have ended.",
            parse_mode="HTML",
        )
        return

    try:
        await bot.send_message(
            chat_id=partner_id,
            text=f"👤 <b>Partner:</b> {message.text}",
            parse_mode="HTML",
        )
        logger.debug(f"Relayed message from {user.id} to {partner_id}")
    except Exception as e:
        logger.error(f"Failed to relay message from {user.id} to {partner_id}: {e}")
        await message.answer("⚠️ Message could not be delivered. Your partner may have left.")
