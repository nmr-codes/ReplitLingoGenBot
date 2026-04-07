import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()


def _rating_keyboard(session_uuid: str) -> InlineKeyboardMarkup:
    """Build rating keyboard with session_uuid embedded in callback data."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_{session_uuid}_1"),
                InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_{session_uuid}_2"),
                InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{session_uuid}_3"),
                InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{session_uuid}_4"),
                InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{session_uuid}_5"),
            ]
        ]
    )


async def get_session_info_api(telegram_id: int) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/session/{telegram_id}",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            data = await resp.json()
            return data if data.get("active") else None
    except Exception as e:
        logger.error(f"Session info API error: {e}")
        return None


async def end_session_api(session_uuid: str) -> bool:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/end-session",
                json={"session_uuid": session_uuid, "status": "ended"},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            return resp.status == 200
    except Exception as e:
        logger.error(f"End session API error: {e}")
        return False


async def get_partner_id_api(session_uuid: str, telegram_id: int) -> int | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/matchmaking/partner/{session_uuid}/{telegram_id}",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            if resp.status == 200:
                return (await resp.json()).get("partner_id")
    except Exception as e:
        logger.error(f"Get partner API error: {e}")
    return None


async def submit_rating_api(session_uuid: str, rater_id: int, score: int) -> bool:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/api/v1/sessions/rating",
                json={
                    "session_uuid": session_uuid,
                    "rater_telegram_id": rater_id,
                    "score": score,
                },
                timeout=aiohttp.ClientTimeout(total=5),
            )
            return resp.status == 200
    except Exception as e:
        logger.error(f"Rating API error: {e}")
        return False


@router.message(F.text == "🚪 End Session")
async def end_session(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user:
        return

    session_info = await get_session_info_api(user.id)
    if not session_info:
        await message.answer(
            "ℹ️ <b>You are not in an active session.</b>",
            parse_mode="HTML",
        )
        return

    session_uuid = session_info.get("session_uuid")
    if not session_uuid:
        return

    partner_id = await get_partner_id_api(session_uuid, user.id)

    ok = await end_session_api(session_uuid)
    if not ok:
        await message.answer("⚠️ Could not end session. Please try again.")
        return

    await message.answer(
        "🏁 <b>Session ended!</b>\n\n"
        "How was your partner? Please rate the session:",
        parse_mode="HTML",
        reply_markup=_rating_keyboard(session_uuid),
    )

    if partner_id:
        try:
            await bot.send_message(
                chat_id=partner_id,
                text=(
                    "🏁 <b>Your partner has ended the session.</b>\n\n"
                    "How was your experience? Please rate the session:"
                ),
                parse_mode="HTML",
                reply_markup=_rating_keyboard(session_uuid),
            )
        except Exception as e:
            logger.error(f"Failed to notify partner {partner_id} of session end: {e}")

    logger.info(f"Session {session_uuid} ended by user {user.id}")


@router.callback_query(F.data.startswith("rate_"))
async def handle_rating(callback: CallbackQuery) -> None:
    if not callback.message or not callback.from_user:
        return

    # callback_data format: "rate_{session_uuid}_{score}"
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("⚠️ Invalid rating data.", show_alert=True)
        return

    # score is last element, session_uuid is everything between first and last underscore
    try:
        score = int(parts[-1])
        session_uuid = "_".join(parts[1:-1])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Invalid rating data.", show_alert=True)
        return

    stars = "⭐" * score
    await callback.message.edit_text(
        f"✅ <b>Thanks for rating!</b>\n\n"
        f"You gave: {stars} ({score}/5)\n\n"
        "Press <b>🔍 Find Partner</b> to start a new session!",
        parse_mode="HTML",
    )

    ok = await submit_rating_api(session_uuid, callback.from_user.id, score)
    if ok:
        logger.info(f"User {callback.from_user.id} rated session {session_uuid}: {score}/5")
    else:
        logger.warning(f"Rating submission failed for user {callback.from_user.id}, session {session_uuid}")

    await callback.answer("Rating submitted! Thank you.")
