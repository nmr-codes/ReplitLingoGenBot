import aiohttp
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger
from backend.app.core.redis_client import set_pending_anon_message

logger = get_logger(__name__)
router = Router()

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Find Partner")],
        [KeyboardButton(text="❌ Stop Searching"), KeyboardButton(text="🚪 End Session")],
        [KeyboardButton(text="👤 My Profile"), KeyboardButton(text="📊 My Stats")],
        [KeyboardButton(text="ℹ️ Help")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Choose an action or type a message...",
)

WELCOME_TEXT = (
    "👋 <b>Welcome to LingoGenBot!</b>\n\n"
    "Practice English with real people from around the world — <b>anonymously</b>.\n\n"
    "🗣 You'll be randomly matched with a partner\n"
    "🎯 Each session has a random conversation topic\n"
    "⏱ Sessions last 5 minutes\n"
    "⭐️ Rate your partner at the end\n"
    "🏆 Earn XP, achievements, and climb the leaderboard!\n\n"
    "<b>Tap 🔍 Find Partner to begin!</b>"
)


async def register_user_api(telegram_id: int, username: str | None, first_name: str | None) -> bool:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/api/v1/users/register",
                json={
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
            return resp.status == 200
    except Exception as e:
        logger.error(f"Failed to register user {telegram_id}: {e}")
        return False


async def _get_public_profile(token: str) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/profiles/public/{token}",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            if resp.status == 200:
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"Get public profile error: {e}")
        return None


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    # Check for deep link args (e.g., /start anon_TOKEN)
    text = message.text or ""
    parts = text.split(maxsplit=1)
    deep_link_arg = parts[1].strip() if len(parts) > 1 else ""

    if deep_link_arg.startswith("anon_"):
        token = deep_link_arg[5:]
        profile = await _get_public_profile(token)
        if not profile:
            await message.answer(
                "❌ <b>Profile not found.</b>\n\nThis link may be invalid or the profile is private.",
                parse_mode="HTML",
            )
            return

        # Register the sender (so they exist in the system)
        await register_user_api(user.id, user.username, user.first_name)

        # Store pending anon message state
        await set_pending_anon_message(user.id, token)

        bio = profile.get("bio") or "No bio available"
        await message.answer(
            f"📨 <b>Send an anonymous message</b>\n\n"
            f"You're about to message someone who says:\n"
            f"<i>{bio}</i>\n\n"
            "✏️ <b>Type your message below</b> and send it.\n"
            "Your identity remains completely anonymous.\n\n"
            "<i>You have 5 minutes to compose your message.</i>",
            parse_mode="HTML",
        )
        logger.info(f"User {user.id} initiated anon message to token {token[:4]}***")
        return

    # Normal /start flow
    ok = await register_user_api(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    if not ok:
        logger.warning(f"User registration API call failed for {user.id}")

    await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
    logger.info(f"User {user.id} started the bot.")


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Help")
async def cmd_help(message: Message) -> None:
    help_text = (
        "📖 <b>How LingoGenBot works</b>\n\n"
        "1️⃣ Press <b>🔍 Find Partner</b> to enter the matchmaking queue\n"
        "2️⃣ Wait while we find someone for you\n"
        "3️⃣ Chat freely — your identity stays anonymous\n"
        "4️⃣ Each session has a <b>random topic</b> to get the conversation started\n"
        "5️⃣ Sessions last <b>5 minutes</b>\n"
        "6️⃣ After the session, <b>rate your partner</b> (1–5 ⭐️)\n\n"
        "🔴 To stop searching: press <b>❌ Stop Searching</b>\n"
        "🚪 To end a session early: press <b>🚪 End Session</b>\n\n"
        "👤 <b>Profile commands:</b>\n"
        "/profile — View & edit your profile\n"
        "/stats — Your conversation statistics\n"
        "/achievements — Your badges & rewards\n"
        "/leaderboard — Global XP rankings\n"
        "/messages — View anonymous messages\n"
        "/setbio — Set your bio\n"
        "/setnative — Set native language\n"
        "/settarget — Set target language\n"
        "/setgoals — Set learning goals\n\n"
        "Good luck and enjoy practicing! 🌍"
    )
    await message.answer(help_text, parse_mode="HTML")
