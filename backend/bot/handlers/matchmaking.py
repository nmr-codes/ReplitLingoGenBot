import asyncio
from datetime import datetime, timezone

import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger
from backend.bot.monitoring import send_monitor_alert

logger = get_logger(__name__)
router = Router()

SEARCH_GIF_URL = "https://media.giphy.com/media/3o7aDczpCChShEG27S/giphy.gif"

SEARCH_CAPTIONS = [
    "🔍 Searching for a partner... Please wait.",
    "⏳ Still looking... Hang tight!",
    "🌍 Scanning the globe for someone to chat with...",
    "🤝 Almost there — finding your perfect match!",
    "💬 Getting ready to connect you soon...",
]


async def call_matchmaking_api(telegram_id: int) -> dict:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/request",
                json={"telegram_id": telegram_id},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            return await resp.json()
    except Exception as e:
        logger.error(f"Matchmaking API error for {telegram_id}: {e}")
        return {"matched": False, "message": "Service temporarily unavailable."}


async def call_cancel_api(telegram_id: int) -> None:
    try:
        async with aiohttp.ClientSession() as client:
            await client.post(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/cancel",
                json={"telegram_id": telegram_id},
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception as e:
        logger.error(f"Cancel API error for {telegram_id}: {e}")


async def check_active_session_api(telegram_id: int) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/session/{telegram_id}",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            data = await resp.json()
            return data if data.get("active") else None
    except Exception as e:
        logger.error(f"Session check API error for {telegram_id}: {e}")
        return None


async def live_search_loop(bot: Bot, chat_id: int, user_id: int) -> None:
    sent_msg = await bot.send_animation(
        chat_id=chat_id,
        animation=SEARCH_GIF_URL,
        caption=SEARCH_CAPTIONS[0],
    )

    elapsed = 0
    caption_idx = 0
    max_wait = settings.MATCH_TIMEOUT_SECONDS
    update_every = settings.SEARCH_UPDATE_INTERVAL

    while elapsed < max_wait:
        await asyncio.sleep(update_every)
        elapsed += update_every

        result = await call_matchmaking_api(user_id)

        if result.get("matched"):
            try:
                await bot.delete_message(chat_id=chat_id, message_id=sent_msg.message_id)
            except Exception:
                pass
            topic = result.get("topic", "General English")
            session_uuid = result.get("session_uuid", "")
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ <b>Partner found!</b>\n\n"
                    f"🎯 <b>Topic:</b> {topic}\n"
                    f"⏱ <b>Session:</b> 5 minutes\n\n"
                    "Start chatting now — your identity is <b>anonymous</b>.\n"
                    "Press <b>🚪 End Session</b> to stop early."
                ),
                parse_mode="HTML",
            )
            logger.info(f"User {user_id} matched. Session: {session_uuid}")
            return

        caption_idx = (caption_idx + 1) % len(SEARCH_CAPTIONS)
        remaining = max_wait - elapsed
        caption = f"{SEARCH_CAPTIONS[caption_idx]}\n\n⏱ Time remaining: {remaining}s"
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=sent_msg.message_id,
                caption=caption,
            )
        except Exception:
            pass

    try:
        await bot.delete_message(chat_id=chat_id, message_id=sent_msg.message_id)
    except Exception:
        pass

    await call_cancel_api(user_id)
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "😕 <b>No partner found</b> within the time limit.\n\n"
            "Try again — there might be more people online soon!\n"
            "Press <b>🔍 Find Partner</b> to retry."
        ),
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} timed out during matchmaking.")


@router.message(F.text == "🔍 Find Partner")
async def find_partner(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user:
        return

    existing = await check_active_session_api(user.id)
    if existing:
        await message.answer(
            "💬 <b>You are already in an active session!</b>\n"
            "Press <b>🚪 End Session</b> first if you want to stop.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        "🔍 <b>Starting partner search...</b>\n"
        "We'll notify you as soon as we find someone!",
        parse_mode="HTML",
    )

    result = await call_matchmaking_api(user.id)

    if result.get("matched"):
        topic = result.get("topic", "General English")
        await message.answer(
            f"✅ <b>Instant match!</b>\n\n"
            f"🎯 <b>Topic:</b> {topic}\n"
            f"⏱ <b>Session:</b> 5 minutes\n\n"
            "Start chatting now! Press <b>🚪 End Session</b> to stop early.",
            parse_mode="HTML",
        )
        return

    asyncio.create_task(live_search_loop(bot, message.chat.id, user.id))


@router.message(F.text == "❌ Stop Searching")
async def stop_searching(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    await call_cancel_api(user.id)
    await message.answer(
        "✅ <b>Search cancelled.</b>\n"
        "Press <b>🔍 Find Partner</b> whenever you're ready to try again.",
        parse_mode="HTML",
    )
    logger.info(f"User {user.id} stopped searching.")
