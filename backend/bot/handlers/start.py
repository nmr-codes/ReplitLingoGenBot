from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import aiohttp

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Find Partner")],
        [KeyboardButton(text="❌ Stop Searching"), KeyboardButton(text="🚪 End Session")],
        [KeyboardButton(text="🪪 My Profile"), KeyboardButton(text="📬 Messages")],
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
    "🪪 Create a profile & receive anonymous messages\n\n"
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


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    ok = await register_user_api(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    if not ok:
        logger.warning(f"User registration API call failed for {user.id}")

    await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
    logger.info(f"User {user.id} started the bot.")


@router.message(F.text == "🪪 My Profile")
async def btn_my_profile(message: Message) -> None:
    # Delegate to the /profile command
    from aiogram.filters import Command as _Command
    from backend.bot.handlers.profile_handlers import cmd_profile as _cmd_profile
    from aiogram.fsm.context import FSMContext as _FSMContext
    # We can't easily inject FSMContext here, so just forward with a tip
    await message.answer(
        "Use /profile to view or create your profile.\n"
        "Use /profile_url to get your shareable link.",
        parse_mode="HTML",
    )


@router.message(F.text == "📬 Messages")
async def btn_messages(message: Message) -> None:
    # Delegate to the /messages command handler
    from backend.bot.handlers.message_handlers import cmd_messages as _cmd_messages
    await _cmd_messages(message)


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
        "<b>Profile & Anonymous Messages:</b>\n"
        "🪪 /profile — Create or edit your profile\n"
        "🔗 /profile_url — Get your shareable anonymous link\n"
        "📬 /messages — View messages sent to you anonymously\n\n"
        "Good luck and enjoy practicing! 🌍"
    )
    await message.answer(help_text, parse_mode="HTML")
