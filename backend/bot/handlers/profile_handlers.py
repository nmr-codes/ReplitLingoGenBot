import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()


class ProfileForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_bio = State()
    waiting_for_level = State()


def _level_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌱 Beginner", callback_data="level:beginner"),
            InlineKeyboardButton(text="📚 Intermediate", callback_data="level:intermediate"),
        ],
        [
            InlineKeyboardButton(text="🎓 Advanced", callback_data="level:advanced"),
            InlineKeyboardButton(text="🌟 Native", callback_data="level:native"),
        ],
        [InlineKeyboardButton(text="⏭ Skip", callback_data="level:skip")],
    ])


async def _get_profile_api(telegram_id: int) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/profiles/me/{telegram_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status == 200:
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"Get profile error for {telegram_id}: {e}")
        return None


async def _create_or_update_profile_api(telegram_id: int, payload: dict) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            # Try creating first
            create_resp = await client.post(
                f"{settings.BACKEND_URL}/api/v1/profiles",
                json={"telegram_id": telegram_id, **payload},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if create_resp.status in (200, 201):
                return await create_resp.json()
            # Profile exists — update it
            update_resp = await client.put(
                f"{settings.BACKEND_URL}/api/v1/profiles/me/{telegram_id}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if update_resp.status == 200:
                return await update_resp.json()
            return None
    except Exception as e:
        logger.error(f"Create/update profile error for {telegram_id}: {e}")
        return None


def _format_profile(profile: dict, site_url: str) -> str:
    name = profile.get("display_name") or "Not set"
    bio = profile.get("bio") or "Not set"
    level = profile.get("language_level") or "Not set"
    slug = profile.get("profile_slug", "")
    visibility = "🌍 Public" if profile.get("is_public") else "🔒 Private"
    url = f"{site_url}/chat/{slug}"
    msgs = profile.get("messages_received", 0)
    return (
        f"🪪 <b>Your Profile</b>\n\n"
        f"👤 <b>Name:</b> {name}\n"
        f"📝 <b>Bio:</b> {bio}\n"
        f"🗣 <b>Level:</b> {level}\n"
        f"👁 <b>Visibility:</b> {visibility}\n"
        f"✉️ <b>Messages received:</b> {msgs}\n\n"
        f"🔗 <b>Your anonymous link:</b>\n<code>{url}</code>\n\n"
        f"Share this link so others can message you anonymously!"
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if not user:
        return

    profile = await _get_profile_api(user.id)
    if profile:
        site_url = settings.BACKEND_URL
        text = _format_profile(profile, site_url)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Edit Name", callback_data="profile_edit:name")],
            [InlineKeyboardButton(text="📝 Edit Bio", callback_data="profile_edit:bio")],
            [InlineKeyboardButton(text="🗣 Edit Level", callback_data="profile_edit:level")],
            [InlineKeyboardButton(text="🔒 Toggle Visibility", callback_data="profile_edit:visibility")],
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer(
            "👋 <b>Create Your Profile</b>\n\n"
            "Your profile lets others send you anonymous messages!\n\n"
            "What should your display name be?\n"
            "<i>(Send any name, or /skip to use your Telegram name)</i>",
            parse_mode="HTML",
        )
        await state.set_state(ProfileForm.waiting_for_name)


@router.message(Command("skip"), ProfileForm.waiting_for_name)
@router.message(F.text == "/skip", ProfileForm.waiting_for_name)
async def profile_skip_name(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if not user:
        return
    name = user.first_name or user.username or "Anonymous"
    await state.update_data(display_name=name)
    await message.answer(
        "📝 <b>Got it!</b>\n\nNow write a short bio about yourself.\n"
        "<i>(Or send /skip to leave it empty)</i>",
        parse_mode="HTML",
    )
    await state.set_state(ProfileForm.waiting_for_bio)


@router.message(ProfileForm.waiting_for_name)
async def profile_get_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    name = message.text.strip()[:128]
    await state.update_data(display_name=name)
    await message.answer(
        "📝 <b>Great!</b>\n\nNow write a short bio about yourself.\n"
        "<i>(Or send /skip to leave it empty)</i>",
        parse_mode="HTML",
    )
    await state.set_state(ProfileForm.waiting_for_bio)


@router.message(Command("skip"), ProfileForm.waiting_for_bio)
@router.message(F.text == "/skip", ProfileForm.waiting_for_bio)
async def profile_skip_bio(message: Message, state: FSMContext) -> None:
    await state.update_data(bio=None)
    await message.answer(
        "🗣 <b>What's your English level?</b>",
        parse_mode="HTML",
        reply_markup=_level_keyboard(),
    )
    await state.set_state(ProfileForm.waiting_for_level)


@router.message(ProfileForm.waiting_for_bio)
async def profile_get_bio(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    bio = message.text.strip()[:500]
    await state.update_data(bio=bio)
    await message.answer(
        "🗣 <b>What's your English level?</b>",
        parse_mode="HTML",
        reply_markup=_level_keyboard(),
    )
    await state.set_state(ProfileForm.waiting_for_level)


@router.callback_query(F.data.startswith("level:"), ProfileForm.waiting_for_level)
async def profile_get_level(callback: CallbackQuery, state: FSMContext) -> None:
    level_val = callback.data.split(":")[1]
    level = None if level_val == "skip" else level_val

    data = await state.get_data()
    await state.clear()

    user = callback.from_user
    payload = {
        "display_name": data.get("display_name"),
        "bio": data.get("bio"),
        "language_level": level,
        "is_public": True,
    }

    profile = await _create_or_update_profile_api(user.id, payload)
    await callback.message.edit_reply_markup(reply_markup=None)

    if profile:
        site_url = settings.BACKEND_URL
        text = (
            "✅ <b>Profile created!</b>\n\n"
            + _format_profile(profile, site_url)
        )
        await callback.message.answer(text, parse_mode="HTML")
    else:
        await callback.message.answer(
            "⚠️ Could not save your profile. Please try /profile again.",
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("profile_edit:"))
async def profile_edit_callback(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":")[1]
    user = callback.from_user

    if field == "name":
        await callback.message.answer(
            "✏️ Send your new display name:", parse_mode="HTML"
        )
        await state.set_state(ProfileForm.waiting_for_name)
        await state.update_data(_editing=True)
    elif field == "bio":
        await callback.message.answer(
            "📝 Send your new bio (max 500 chars):", parse_mode="HTML"
        )
        await state.set_state(ProfileForm.waiting_for_bio)
        await state.update_data(_editing=True)
    elif field == "level":
        await callback.message.answer(
            "🗣 Choose your new language level:",
            parse_mode="HTML",
            reply_markup=_level_keyboard(),
        )
        await state.set_state(ProfileForm.waiting_for_level)
        await state.update_data(_editing=True)
    elif field == "visibility":
        profile = await _get_profile_api(user.id)
        if profile:
            new_visibility = not profile.get("is_public", True)
            updated = await _create_or_update_profile_api(user.id, {"is_public": new_visibility})
            vis_text = "🌍 Public" if new_visibility else "🔒 Private"
            await callback.message.answer(
                f"👁 Profile visibility changed to <b>{vis_text}</b>", parse_mode="HTML"
            )
    await callback.answer()


@router.message(Command("profile_url"))
async def cmd_profile_url(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    profile = await _get_profile_api(user.id)
    if not profile:
        await message.answer(
            "❌ You don't have a profile yet.\n\n"
            "Create one with /profile first!",
            parse_mode="HTML",
        )
        return

    slug = profile.get("profile_slug", "")
    site_url = settings.BACKEND_URL
    url = f"{site_url}/chat/{slug}"

    await message.answer(
        f"🔗 <b>Your Anonymous Link</b>\n\n"
        f"<code>{url}</code>\n\n"
        f"📤 Share this link in your Telegram channel or with friends.\n"
        f"Anyone who visits it can send you an anonymous message!\n\n"
        f"✉️ Check messages with /messages",
        parse_mode="HTML",
    )
