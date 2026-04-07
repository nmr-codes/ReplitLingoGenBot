import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()

AVAILABILITY_LABELS = {
    "online": "🟢 Online",
    "away": "🟡 Away",
    "dnd": "🔴 Do Not Disturb",
    "offline": "⚫ Offline",
}


async def _api_get(path: str) -> dict | list | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}{path}",
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status == 200:
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"API GET {path} error: {e}")
        return None


async def _api_post(path: str, payload: dict) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}{path}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status in (200, 201):
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"API POST {path} error: {e}")
        return None


async def _api_patch(path: str, payload: dict) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}{path}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status == 200:
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"API PATCH {path} error: {e}")
        return None


def _profile_keyboard(token: str) -> InlineKeyboardMarkup:
    """Inline keyboard for profile view."""
    bot_username = settings.BOT_USERNAME
    share_url = f"https://t.me/{bot_username}?start=anon_{token}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📨 Share Anon Link", url=share_url)],
            [InlineKeyboardButton(text="✏️ Edit Bio", callback_data="profile_edit_bio")],
            [
                InlineKeyboardButton(text="🌐 Edit Languages", callback_data="profile_edit_lang"),
                InlineKeyboardButton(text="🎯 Edit Goals", callback_data="profile_edit_goals"),
            ],
            [InlineKeyboardButton(text="🏆 My Achievements", callback_data="profile_achievements")],
        ]
    )


def _format_profile(profile: dict, user_id: int) -> str:
    token = profile.get("profile_token", "")
    bot_username = settings.BOT_USERNAME
    share_url = f"https://t.me/{bot_username}?start=anon_{token}"

    bio = profile.get("bio") or "<i>No bio set</i>"
    native = profile.get("native_language") or "—"
    target = profile.get("target_language") or "—"
    level = profile.get("language_level") or "—"
    xp = profile.get("xp", 0)
    lvl = profile.get("level", 1)
    rep = profile.get("reputation_score", 0.0)
    streak = profile.get("streak_days", 0)
    anon_count = profile.get("total_anon_messages_received", 0)
    avail = AVAILABILITY_LABELS.get(profile.get("availability", "online"), "🟢 Online")
    goals = profile.get("learning_goals") or "<i>Not set</i>"

    return (
        f"👤 <b>Your Profile</b>\n\n"
        f"📝 <b>Bio:</b> {bio}\n"
        f"🌐 <b>Native Language:</b> {native}\n"
        f"📚 <b>Learning:</b> {target} ({level})\n"
        f"🎯 <b>Goals:</b> {goals}\n\n"
        f"⭐ <b>Reputation:</b> {rep:.1f}/100\n"
        f"🏅 <b>Level:</b> {lvl} ({xp} XP)\n"
        f"🔥 <b>Streak:</b> {streak} days\n"
        f"📬 <b>Anon messages received:</b> {anon_count}\n"
        f"{avail}\n\n"
        f"🔗 <b>Your anonymous link:</b>\n{share_url}\n\n"
        "<i>Share this link so anyone can message you anonymously!</i>"
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    # Ensure profile exists
    data = await _api_post(
        "/api/v1/profiles",
        {"telegram_id": user.id},
    )
    if not data:
        data = await _api_get(f"/api/v1/profiles/{user.id}")

    if not data:
        await message.answer("⚠️ Could not load your profile. Please try again.")
        return

    token = data.get("profile_token", "")
    await message.answer(
        _format_profile(data, user.id),
        parse_mode="HTML",
        reply_markup=_profile_keyboard(token),
    )


@router.callback_query(F.data == "profile_edit_bio")
async def cb_edit_bio(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "✏️ <b>Send your new bio</b> (max 500 characters):\n\n"
        "Type your bio in the next message.",
        parse_mode="HTML",
    )
    # We store state via the pending_bio pattern; for simplicity use Redis via API
    # The next text message from this user will be caught by the bot state logic.
    # For a clean implementation without FSM, we prompt here and rely on /setbio command.
    await callback.message.answer(
        "Use /setbio followed by your text, e.g.:\n<code>/setbio I love learning languages!</code>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile_edit_lang")
async def cb_edit_lang(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "🌐 <b>Update your languages</b>\n\n"
        "Use these commands:\n"
        "• <code>/setnative English</code> — your native language\n"
        "• <code>/settarget Spanish B2</code> — target language and level (A1–C2)",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile_edit_goals")
async def cb_edit_goals(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "🎯 <b>Set your learning goals</b>\n\n"
        "Use: <code>/setgoals Your goals here</code>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile_achievements")
async def cb_achievements(callback: CallbackQuery) -> None:
    await callback.answer()
    user = callback.from_user
    if not user:
        return
    data = await _api_get(f"/api/v1/profiles/{user.id}/achievements")
    if data is None:
        await callback.message.answer("⚠️ Could not load achievements.")
        return
    if not data:
        await callback.message.answer(
            "🏆 <b>No achievements yet!</b>\n\nComplete conversations to earn your first badge.",
            parse_mode="HTML",
        )
        return
    lines = ["🏆 <b>Your Achievements</b>\n"]
    for ach in data:
        emoji = ach.get("emoji", "🏅")
        name = ach.get("name", "")
        desc = ach.get("description", "")
        lines.append(f"{emoji} <b>{name}</b> — {desc}")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")


# ---- Profile edit commands ----

@router.message(F.text == "👤 My Profile")
async def btn_profile(message: Message) -> None:
    await cmd_profile(message)


@router.message(F.text == "📊 My Stats")
async def btn_stats(message: Message) -> None:
    await cmd_stats(message)


@router.message(Command("setbio"))
async def cmd_setbio(message: Message) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /setbio <your bio>")
        return
    bio = parts[1][:500]
    data = await _api_patch(f"/api/v1/profiles/{user.id}", {"bio": bio})
    if data:
        await message.answer("✅ Bio updated!", parse_mode="HTML")
    else:
        await message.answer("⚠️ Could not update bio.")


@router.message(Command("setnative"))
async def cmd_setnative(message: Message) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /setnative <language>")
        return
    lang = parts[1][:64]
    data = await _api_patch(f"/api/v1/profiles/{user.id}", {"native_language": lang})
    if data:
        await message.answer(f"✅ Native language set to: <b>{lang}</b>", parse_mode="HTML")
    else:
        await message.answer("⚠️ Could not update native language.")


@router.message(Command("settarget"))
async def cmd_settarget(message: Message) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Usage: /settarget <language> [level]\nExample: /settarget Spanish B2")
        return
    lang = parts[1][:64]
    level = parts[2].upper() if len(parts) > 2 else None
    payload: dict = {"target_language": lang}
    if level in {"A1", "A2", "B1", "B2", "C1", "C2"}:
        payload["language_level"] = level
    data = await _api_patch(f"/api/v1/profiles/{user.id}", payload)
    if data:
        level_str = f" ({level})" if level in {"A1", "A2", "B1", "B2", "C1", "C2"} else ""
        await message.answer(f"✅ Target language set to: <b>{lang}{level_str}</b>", parse_mode="HTML")
    else:
        await message.answer("⚠️ Could not update target language.")


@router.message(Command("setgoals"))
async def cmd_setgoals(message: Message) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /setgoals <your learning goals>")
        return
    goals = parts[1][:300]
    data = await _api_patch(f"/api/v1/profiles/{user.id}", {"learning_goals": goals})
    if data:
        await message.answer("✅ Learning goals updated!", parse_mode="HTML")
    else:
        await message.answer("⚠️ Could not update learning goals.")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    data = await _api_get(f"/api/v1/profiles/{user.id}/stats")
    if not data:
        await message.answer(
            "📊 <b>No statistics yet!</b>\n\nComplete your first conversation to start tracking stats.",
            parse_mode="HTML",
        )
        return

    total_conv = data.get("total_conversations", 0)
    completed = data.get("conversations_completed", 0)
    msgs_sent = data.get("total_messages_sent", 0)
    avg_recv = data.get("avg_rating_received", 0.0)
    avg_given = data.get("avg_rating_given", 0.0)
    total_dur = data.get("total_session_duration_seconds", 0)
    hours = total_dur // 3600
    minutes = (total_dur % 3600) // 60

    await message.answer(
        f"📊 <b>Your Statistics</b>\n\n"
        f"💬 <b>Conversations:</b> {total_conv} (completed: {completed})\n"
        f"✉️ <b>Messages sent:</b> {msgs_sent}\n"
        f"⭐ <b>Avg rating received:</b> {avg_recv:.1f}/5\n"
        f"🗳 <b>Avg rating given:</b> {avg_given:.1f}/5\n"
        f"⏱ <b>Total chat time:</b> {hours}h {minutes}m",
        parse_mode="HTML",
    )


@router.message(Command("achievements"))
async def cmd_achievements(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    data = await _api_get(f"/api/v1/profiles/{user.id}/achievements")
    if data is None:
        await message.answer("⚠️ Could not load achievements.")
        return
    if not data:
        await message.answer(
            "🏆 <b>No achievements yet!</b>\n\nComplete conversations to earn your first badge.",
            parse_mode="HTML",
        )
        return
    lines = ["🏆 <b>Your Achievements</b>\n"]
    for ach in data:
        emoji = ach.get("emoji", "🏅")
        name = ach.get("name", "")
        desc = ach.get("description", "")
        lines.append(f"{emoji} <b>{name}</b>\n   <i>{desc}</i>")
    await message.answer("\n\n".join(lines), parse_mode="HTML")


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    data = await _api_get("/api/v1/leaderboard/global?limit=10")
    rank_data = await _api_get(f"/api/v1/leaderboard/rank/{user.id}")

    if not data:
        await message.answer("📈 Leaderboard is empty — be the first to earn XP!")
        return

    lines = ["🏆 <b>Global Leaderboard — Top 10</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for entry in data:
        rank = entry.get("rank", 0)
        medal = medals[rank - 1] if rank <= 3 else f"#{rank}"
        name = entry.get("first_name") or entry.get("username") or f"User{entry.get('telegram_id','')}"
        xp = entry.get("xp", 0)
        lvl = entry.get("level", 1)
        lines.append(f"{medal} <b>{name}</b> — Lvl {lvl} ({xp} XP)")

    if rank_data and rank_data.get("rank"):
        your_rank = rank_data["rank"]
        your_xp = rank_data.get("xp", 0)
        lines.append(f"\n📍 <b>Your rank:</b> #{your_rank} ({your_xp} XP)")

    await message.answer("\n".join(lines), parse_mode="HTML")
