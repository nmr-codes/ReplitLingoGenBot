import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger
from backend.app.core.redis_client import get_pending_anon_message, clear_pending_anon_message

logger = get_logger(__name__)
router = Router()

CONTROL_TEXTS = {
    "🔍 Find Partner",
    "❌ Stop Searching",
    "🚪 End Session",
    "ℹ️ Help",
    "👤 My Profile",
    "📊 My Stats",
    "/start",
    "/help",
    "/profile",
    "/stats",
    "/achievements",
    "/leaderboard",
    "/messages",
    "/setbio",
    "/setnative",
    "/settarget",
    "/setgoals",
    "/admin",
    "/admin_stats",
    "/admin_users",
    "/admin_flags",
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

    # Check if user is composing an anonymous message
    pending_token = await get_pending_anon_message(user.id)
    if pending_token:
        content = message.text.strip()
        if len(content) > 1000:
            await message.answer("⚠️ Message is too long (max 1000 characters). Please shorten it.")
            return

        try:
            async with aiohttp.ClientSession() as client:
                resp = await client.post(
                    f"{settings.BACKEND_URL}/api/v1/messages/send",
                    json={
                        "recipient_token": pending_token,
                        "sender_id": user.id,
                        "content": content,
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                )
                result = await resp.json() if resp.status == 200 else None
        except Exception as e:
            logger.error(f"Send anon message error: {e}")
            result = None

        await clear_pending_anon_message(user.id)

        if result:
            await message.answer(
                "✅ <b>Anonymous message sent!</b>\n\n"
                "Your message was delivered anonymously.",
                parse_mode="HTML",
            )
            # Notify recipient
            try:
                async with aiohttp.ClientSession() as client:
                    resp = await client.get(
                        f"{settings.BACKEND_URL}/api/v1/profiles/by-token/{pending_token}",
                        timeout=aiohttp.ClientTimeout(total=5),
                    )
                    if resp.status == 200:
                        profile_data = await resp.json()
                        recipient_id = profile_data.get("telegram_id")
                        if recipient_id:
                            await bot.send_message(
                                chat_id=recipient_id,
                                text=(
                                    "📨 <b>You received an anonymous message!</b>\n\n"
                                    f"<blockquote>{content}</blockquote>\n\n"
                                    "Use /messages to view all your anonymous messages."
                                ),
                                parse_mode="HTML",
                            )
            except Exception as e:
                logger.error(f"Failed to notify anon message recipient: {e}")
        else:
            await message.answer(
                "⚠️ <b>Could not send message.</b>\n\n"
                "You may have reached the hourly rate limit (max 5 messages). "
                "Please try again later.",
                parse_mode="HTML",
            )
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
