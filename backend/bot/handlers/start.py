import aiohttp
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

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


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

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


async def fetch_required_channels() -> list[dict]:
    """Fetch the list of required channels from the backend."""
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/channels",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            if resp.status == 200:
                return await resp.json()
            return []
    except Exception as e:
        logger.error(f"Failed to fetch required channels: {e}")
        return []


async def find_unjoined_channels(bot: Bot, user_id: int, channels: list[dict]) -> list[dict]:
    """Return the subset of channels the user has NOT joined."""
    unjoined: list[dict] = []
    for ch in channels:
        ch_id = ch.get("channel_id")
        if not ch_id:
            continue
        try:
            member = await bot.get_chat_member(ch_id, user_id)
            if member.status in ("left", "kicked", "banned"):
                unjoined.append(ch)
        except (TelegramForbiddenError, TelegramBadRequest):
            # Bot not in channel or channel doesn't exist — skip the check
            logger.warning(f"Cannot check membership for channel {ch_id}; skipping.")
        except Exception as e:
            logger.warning(f"Membership check error for channel {ch_id}: {e}")
            unjoined.append(ch)  # Fail-closed: treat as not joined
    return unjoined


def build_join_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    """Build an inline keyboard with a 'Join' button for each un-joined channel."""
    buttons: list[list[InlineKeyboardButton]] = []
    for ch in channels:
        username = ch.get("channel_username", "").lstrip("@")
        invite = ch.get("invite_link")
        title = ch.get("title", "Channel")

        if invite:
            url = invite
        elif username:
            url = f"https://t.me/{username}"
        else:
            continue  # Cannot build a URL — skip

        buttons.append([InlineKeyboardButton(text=f"📢 Join {title}", url=url)])

    buttons.append(
        [InlineKeyboardButton(text="✅ I've Joined All Channels", callback_data="check_channels")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------------------------------------------------------------------
# /start handler
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user:
        return

    # ── Deep-link: /start anon_TOKEN ──────────────────────────────────────
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

        await register_user_api(user.id, user.username, user.first_name)
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

    # ── Required-channel membership gate ──────────────────────────────────
    required = await fetch_required_channels()
    if required:
        unjoined = await find_unjoined_channels(bot, user.id, required)
        if unjoined:
            names = "\n".join(
                f"• <b>{ch.get('title', 'Unknown')}</b>" for ch in unjoined
            )
            await message.answer(
                "📢 <b>Join required channels to use this bot</b>\n\n"
                f"Please join the following channel(s) first:\n{names}\n\n"
                "After joining, tap <b>✅ I've Joined All Channels</b> below.",
                parse_mode="HTML",
                reply_markup=build_join_keyboard(unjoined),
            )
            logger.info(f"User {user.id} blocked — not in {len(unjoined)} required channel(s).")
            return

    # ── Normal registration & welcome ──────────────────────────────────────
    ok = await register_user_api(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    if not ok:
        logger.warning(f"User registration API call failed for {user.id}")

    await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
    logger.info(f"User {user.id} started the bot.")


# ---------------------------------------------------------------------------
# Callback: "I've Joined All Channels"
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "check_channels")
async def check_channels_callback(callback: CallbackQuery, bot: Bot) -> None:
    user = callback.from_user
    if not user or not callback.message:
        return

    await callback.answer("🔍 Checking membership…")

    required = await fetch_required_channels()
    unjoined = await find_unjoined_channels(bot, user.id, required)

    if unjoined:
        names = "\n".join(f"• <b>{ch.get('title', 'Unknown')}</b>" for ch in unjoined)
        try:
            await callback.message.edit_text(
                "❌ <b>You still haven't joined:</b>\n\n"
                f"{names}\n\n"
                "Please join all channels and tap the button again.",
                parse_mode="HTML",
                reply_markup=build_join_keyboard(unjoined),
            )
        except TelegramBadRequest:
            pass  # Message unchanged — ignore
        return

    # All channels joined — register and welcome
    ok = await register_user_api(user.id, user.username, user.first_name)
    if not ok:
        logger.warning(f"Failed to register user {user.id} after channel verification")

    try:
        await callback.message.edit_text(
            "✅ <b>Verified! Welcome to LingoGenBot.</b>",
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass

    await callback.message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
    logger.info(f"User {user.id} verified channels and registered.")


# ---------------------------------------------------------------------------
# /help handler
# ---------------------------------------------------------------------------

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
        "/setgoals — Set learning goals\n"
        "/setlang — Change bot language (EN/UZ/RU)\n\n"
        "Good luck and enjoy practicing! 🌍"
    )
    await message.answer(help_text, parse_mode="HTML")


# ---------------------------------------------------------------------------
# /setlang — language selection
# ---------------------------------------------------------------------------

@router.message(Command("setlang"))
async def cmd_setlang(message: Message) -> None:
    from backend.bot.locales import get_user_lang, t
    user = message.from_user
    if not user:
        return
    lang = await get_user_lang(user.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("lang_en_btn", lang), callback_data="setlang_en"),
                InlineKeyboardButton(text=t("lang_uz_btn", lang), callback_data="setlang_uz"),
                InlineKeyboardButton(text=t("lang_ru_btn", lang), callback_data="setlang_ru"),
            ]
        ]
    )
    await message.answer(t("choose_language", lang), parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("setlang_"))
async def cb_setlang(callback: CallbackQuery) -> None:
    from backend.bot.locales import set_user_lang, t
    user = callback.from_user
    if not user:
        return
    lang = callback.data.replace("setlang_", "")
    await set_user_lang(user.id, lang)
    await callback.answer(t("language_set", lang), show_alert=True)
    await callback.message.delete()
