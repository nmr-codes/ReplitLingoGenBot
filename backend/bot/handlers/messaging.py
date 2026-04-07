import html
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
    "/admin_audit",
    "/admin_channels",
    "/admin_add_channel",
    "/admin_remove_channel",
    "/broadcast",
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


async def _no_session_msg(message: Message) -> None:
    await message.answer(
        "💬 <b>You are not in a session.</b>\n"
        "Press <b>🔍 Find Partner</b> to get matched!",
        parse_mode="HTML",
    )


async def _partner_unreachable(message: Message) -> None:
    await message.answer(
        "⚠️ Could not reach your partner. The session may have ended.",
        parse_mode="HTML",
    )


async def _relay_failed(message: Message) -> None:
    await message.answer(
        "⚠️ Message could not be delivered. Your partner may have left.",
        parse_mode="HTML",
    )


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
                                    f"<blockquote>{html.escape(content)}</blockquote>\n\n"
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
        await _no_session_msg(message)
        return

    session_uuid = session_info.get("session_uuid")
    if not session_uuid:
        return

    partner_id = await get_partner_id(session_uuid, user.id)
    if not partner_id:
        await _partner_unreachable(message)
        return

    try:
        await bot.send_message(
            chat_id=partner_id,
            text=f"👤 <b>Partner:</b> {message.text}",
            parse_mode="HTML",
        )
        logger.debug(f"Relayed text from {user.id} to {partner_id}")
    except Exception as e:
        logger.error(f"Failed to relay text from {user.id} to {partner_id}: {e}")
        await _relay_failed(message)


@router.message(F.photo)
async def relay_photo(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user or not message.photo:
        return

    session_info = await get_session_info(user.id)
    if not session_info:
        await _no_session_msg(message)
        return

    session_uuid = session_info.get("session_uuid")
    if not session_uuid:
        return

    partner_id = await get_partner_id(session_uuid, user.id)
    if not partner_id:
        await _partner_unreachable(message)
        return

    try:
        caption = f"👤 <b>Partner:</b> {message.caption}" if message.caption else "👤 <b>Partner sent a photo</b>"
        await bot.send_photo(
            chat_id=partner_id,
            photo=message.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML",
        )
        logger.debug(f"Relayed photo from {user.id} to {partner_id}")
    except Exception as e:
        logger.error(f"Failed to relay photo from {user.id} to {partner_id}: {e}")
        await _relay_failed(message)


@router.message(F.video)
async def relay_video(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user or not message.video:
        return

    session_info = await get_session_info(user.id)
    if not session_info:
        await _no_session_msg(message)
        return

    session_uuid = session_info.get("session_uuid")
    if not session_uuid:
        return

    partner_id = await get_partner_id(session_uuid, user.id)
    if not partner_id:
        await _partner_unreachable(message)
        return

    try:
        caption = f"👤 <b>Partner:</b> {message.caption}" if message.caption else "👤 <b>Partner sent a video</b>"
        await bot.send_video(
            chat_id=partner_id,
            video=message.video.file_id,
            caption=caption,
            parse_mode="HTML",
        )
        logger.debug(f"Relayed video from {user.id} to {partner_id}")
    except Exception as e:
        logger.error(f"Failed to relay video from {user.id} to {partner_id}: {e}")
        await _relay_failed(message)


@router.message(F.video_note)
async def relay_video_note(message: Message, bot: Bot) -> None:
    """Relay Telegram round videos (video notes)."""
    user = message.from_user
    if not user or not message.video_note:
        return

    session_info = await get_session_info(user.id)
    if not session_info:
        await _no_session_msg(message)
        return

    session_uuid = session_info.get("session_uuid")
    if not session_uuid:
        return

    partner_id = await get_partner_id(session_uuid, user.id)
    if not partner_id:
        await _partner_unreachable(message)
        return

    try:
        await bot.send_video_note(
            chat_id=partner_id,
            video_note=message.video_note.file_id,
        )
        logger.debug(f"Relayed video note from {user.id} to {partner_id}")
    except Exception as e:
        logger.error(f"Failed to relay video note from {user.id} to {partner_id}: {e}")
        await _relay_failed(message)


@router.message(F.voice)
async def relay_voice(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user or not message.voice:
        return

    session_info = await get_session_info(user.id)
    if not session_info:
        await _no_session_msg(message)
        return

    session_uuid = session_info.get("session_uuid")
    if not session_uuid:
        return

    partner_id = await get_partner_id(session_uuid, user.id)
    if not partner_id:
        await _partner_unreachable(message)
        return

    try:
        await bot.send_voice(
            chat_id=partner_id,
            voice=message.voice.file_id,
            caption="👤 <b>Partner sent a voice message</b>",
            parse_mode="HTML",
        )
        logger.debug(f"Relayed voice from {user.id} to {partner_id}")
    except Exception as e:
        logger.error(f"Failed to relay voice from {user.id} to {partner_id}: {e}")
        await _relay_failed(message)
