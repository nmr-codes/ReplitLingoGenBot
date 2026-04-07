import asyncio

import aiohttp
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


def _admin_headers(telegram_id: int) -> dict:
    return {"X-Admin-Id": str(telegram_id)}


class BroadcastState(StatesGroup):
    waiting_for_text = State()


class AddChannelState(StatesGroup):
    waiting_for_channel = State()


class RemoveChannelState(StatesGroup):
    waiting_for_id = State()


# ---------------------------------------------------------------------------
# Generic API helpers
# ---------------------------------------------------------------------------

async def _api_get(path: str, admin_id: int) -> dict | list | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}{path}",
                headers=_admin_headers(admin_id),
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status == 200:
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"Admin API GET {path} error: {e}")
        return None


async def _api_post(path: str, admin_id: int, payload: dict) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}{path}",
                headers=_admin_headers(admin_id),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status in (200, 201):
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"Admin API POST {path} error: {e}")
        return None


async def _api_delete(path: str, admin_id: int) -> bool:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.delete(
                f"{settings.BACKEND_URL}{path}",
                headers=_admin_headers(admin_id),
                timeout=aiohttp.ClientTimeout(total=10),
            )
            return resp.status == 200
    except Exception as e:
        logger.error(f"Admin API DELETE {path} error: {e}")
        return False


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
                InlineKeyboardButton(text="🚨 Flags", callback_data="admin_flags"),
            ],
            [
                InlineKeyboardButton(text="📋 Audit Log", callback_data="admin_audit"),
                InlineKeyboardButton(text="📢 Channels", callback_data="admin_channels"),
            ],
            [
                InlineKeyboardButton(text="📡 Broadcast", callback_data="admin_broadcast"),
            ],
            [
                InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_dashboard"),
            ],
        ]
    )


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="admin_dashboard")]
        ]
    )


def _channels_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Add Channel", callback_data="admin_add_channel"),
                InlineKeyboardButton(text="➖ Remove Channel", callback_data="admin_remove_channel"),
            ],
            [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="admin_dashboard")],
        ]
    )


# ---------------------------------------------------------------------------
# Dashboard helpers
# ---------------------------------------------------------------------------

async def _build_dashboard_text(admin_id: int) -> str:
    data = await _api_get("/api/v1/admin/dashboard", admin_id)
    if not data:
        return "⚠️ Could not load dashboard stats."

    total_users = data.get("total_users", 0)
    active_today = data.get("active_users_today", 0)
    total_sessions = data.get("total_sessions", 0)
    active_sessions = data.get("active_sessions", 0)
    anon_msgs = data.get("total_anonymous_messages", 0)
    pending_flags = data.get("pending_moderation_flags", 0)
    top_xp = data.get("top_user_xp", 0)

    return (
        "🛡️ <b>Admin Dashboard</b>\n\n"
        f"👥 <b>Total users:</b> {total_users}\n"
        f"🟢 <b>Active today:</b> {active_today}\n"
        f"💬 <b>Total sessions:</b> {total_sessions}\n"
        f"🔄 <b>Active sessions now:</b> {active_sessions}\n"
        f"📨 <b>Anonymous messages:</b> {anon_msgs}\n"
        f"🚨 <b>Pending flags:</b> {pending_flags}\n"
        f"🏆 <b>Top XP:</b> {top_xp}\n\n"
        "<i>Use the buttons below to navigate.</i>"
    )


# ---------------------------------------------------------------------------
# /admin command — entry point
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 You are not authorized to use admin commands.")
        return

    text = await _build_dashboard_text(user.id)
    await message.answer(text, parse_mode="HTML", reply_markup=_main_menu_keyboard())


# ---------------------------------------------------------------------------
# Callback: admin_dashboard — refresh dashboard
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_dashboard")
async def cb_admin_dashboard(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    text = await _build_dashboard_text(user.id)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_main_menu_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_main_menu_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Callback: admin_users
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    data = await _api_get("/api/v1/admin/users?limit=10", user.id)
    if not data or not isinstance(data, list):
        text = "⚠️ Could not load users or no users found."
    else:
        lines = ["👥 <b>Recent Users</b>\n"]
        for u in data[:10]:
            name = u.get("first_name") or u.get("username") or f"ID:{u.get('telegram_id')}"
            active = "✅" if u.get("is_active") else "❌"
            lvl = u.get("level", 1)
            xp = u.get("xp", 0)
            convs = u.get("total_conversations", 0)
            lines.append(f"{active} <b>{name}</b> | Lvl {lvl} ({xp} XP) | {convs} chats")
        text = "\n".join(lines)

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_back_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_back_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Callback: admin_flags
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_flags")
async def cb_admin_flags(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    data = await _api_get("/api/v1/admin/flags", user.id)
    if data is None:
        text = "⚠️ Could not load flags."
    elif not data:
        text = "✅ No pending moderation flags."
    else:
        lines = ["🚨 <b>Pending Moderation Flags</b>\n"]
        for flag in data[:10]:
            flag_id = flag.get("id")
            reason = flag.get("reason", "")
            ctype = flag.get("content_type", "")
            cid = flag.get("content_id", "")
            lines.append(f"🔴 #{flag_id} [{ctype}:{cid}] — {reason}")
        text = "\n".join(lines)

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_back_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_back_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Callback: admin_audit
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_audit")
async def cb_admin_audit(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    data = await _api_get("/api/v1/admin/audit-log?limit=10", user.id)
    if data is None:
        text = "⚠️ Could not load audit log."
    elif not data:
        text = "📋 Audit log is empty."
    else:
        lines = ["📋 <b>Recent Admin Actions</b>\n"]
        for log in data[:10]:
            action = log.get("action", "")
            target = log.get("target_id", "")
            admin_id = log.get("admin_telegram_id", "")
            created_raw = log.get("created_at", "")
            created = str(created_raw)[:10] if created_raw else "unknown"
            lines.append(f"🔹 <b>{action}</b> → {target} by {admin_id} ({created})")
        text = "\n".join(lines)

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_back_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_back_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Callback: admin_channels — list + management
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_channels")
async def cb_admin_channels(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    data = await _api_get("/api/v1/admin/channels", user.id)
    if data is None:
        text = "⚠️ Could not load channels."
    elif not data:
        text = "📢 <b>No required channels configured.</b>\n\nUse ➕ Add Channel to add one."
    else:
        lines = ["📢 <b>Required Channels</b>\n"]
        for ch in data:
            db_id = ch.get("id")
            title = ch.get("title", "Unknown")
            username = ch.get("channel_username") or "—"
            active = "✅ Active" if ch.get("is_active") else "❌ Inactive"
            lines.append(f"• <b>{title}</b> ({username}) | {active} | ID: {db_id}")
        text = "\n".join(lines)

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_channels_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_channels_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Callback: admin_add_channel — prompt for channel input
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_add_channel")
async def cb_admin_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    await state.set_state(AddChannelState.waiting_for_channel)
    await callback.message.answer(
        "📢 <b>Add Required Channel</b>\n\n"
        "Send the channel username or ID:\n"
        "• <code>@channel_username</code>\n"
        "• <code>-100123456789</code>\n\n"
        "<i>The bot must be a member of the channel.</i>\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddChannelState.waiting_for_channel)
async def admin_add_channel_input(message: Message, bot: Bot, state: FSMContext) -> None:
    user = message.from_user
    if not user or not _is_admin(user.id):
        return

    arg = (message.text or "").strip()
    if arg == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    try:
        if not arg.lstrip("-").isdigit():
            identifier: str | int = arg if arg.startswith("@") else f"@{arg}"
        else:
            identifier = int(arg)
        chat = await bot.get_chat(identifier)
    except Exception as e:
        await message.answer(
            f"❌ Could not resolve channel: <code>{e}</code>\n\n"
            "Make sure the bot is a member and the username/ID is correct.\n"
            "Send /cancel to abort.",
            parse_mode="HTML",
        )
        return

    channel_id = chat.id
    channel_username = f"@{chat.username}" if chat.username else None
    title = chat.title or "Unknown Channel"
    invite_link = getattr(chat, "invite_link", None)
    if not invite_link and chat.username:
        invite_link = f"https://t.me/{chat.username}"

    result = await _api_post(
        "/api/v1/admin/channels",
        user.id,
        {
            "channel_id": channel_id,
            "channel_username": channel_username,
            "title": title,
            "invite_link": invite_link,
        },
    )

    await state.clear()

    if result:
        await message.answer(
            f"✅ <b>Channel added:</b> {title}\n"
            f"Username: {channel_username or '—'}\n"
            f"Telegram ID: <code>{channel_id}</code>",
            parse_mode="HTML",
            reply_markup=_back_keyboard(),
        )
        logger.info(f"Admin {user.id} added required channel: {title} ({channel_id})")
    else:
        await message.answer(
            "⚠️ Failed to add channel. It may already exist.",
            reply_markup=_back_keyboard(),
        )


# ---------------------------------------------------------------------------
# Callback: admin_remove_channel — prompt for DB ID
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_remove_channel")
async def cb_admin_remove_channel(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    await state.set_state(RemoveChannelState.waiting_for_id)
    await callback.message.answer(
        "📢 <b>Remove Required Channel</b>\n\n"
        "Send the <b>channel record ID</b> to remove.\n"
        "(Get IDs from the Channels list)\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(RemoveChannelState.waiting_for_id)
async def admin_remove_channel_input(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if not user or not _is_admin(user.id):
        return

    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Cancelled.")
        return

    if not text.isdigit():
        await message.answer("⚠️ Please send a numeric ID. Send /cancel to abort.")
        return

    db_id = int(text)
    ok = await _api_delete(f"/api/v1/admin/channels/{db_id}", user.id)
    await state.clear()

    if ok:
        await message.answer(
            f"✅ Required channel <b>#{db_id}</b> removed.",
            parse_mode="HTML",
            reply_markup=_back_keyboard(),
        )
        logger.info(f"Admin {user.id} removed required channel db_id={db_id}")
    else:
        await message.answer(
            f"⚠️ Could not remove channel #{db_id}. Check the ID and try again.",
            reply_markup=_back_keyboard(),
        )


# ---------------------------------------------------------------------------
# Callback: admin_broadcast — prompt for message text
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not user or not _is_admin(user.id):
        await callback.answer("🚫 Not authorized.", show_alert=True)
        return

    await state.set_state(BroadcastState.waiting_for_text)
    await callback.message.answer(
        "📡 <b>Broadcast Message</b>\n\n"
        "Send the message you want to broadcast to <b>all active users</b>.\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BroadcastState.waiting_for_text)
async def admin_broadcast_input(message: Message, bot: Bot, state: FSMContext) -> None:
    user = message.from_user
    if not user or not _is_admin(user.id):
        return

    text = (message.text or "").strip()
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Broadcast cancelled.")
        return

    await state.clear()

    # Fetch user list
    data = await _api_get("/api/v1/admin/broadcast/users", user.id)
    if data is None:
        await message.answer("⚠️ Could not fetch user list. Try again.")
        return

    user_ids: list[int] = data.get("user_ids", [])
    total = len(user_ids)
    if not total:
        await message.answer("ℹ️ No active users to broadcast to.")
        return

    status_msg = await message.answer(
        f"📡 <b>Broadcasting to {total} users…</b>\n\nThis may take a moment.",
        parse_mode="HTML",
    )

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(
                chat_id=uid,
                text=f"📢 <b>Announcement</b>\n\n{text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"✅ <b>Broadcast complete!</b>\n\n"
            f"📤 Sent: {sent}\n❌ Failed: {failed}\n👥 Total: {total}",
            parse_mode="HTML",
            reply_markup=_back_keyboard(),
        )
    except Exception:
        await message.answer(
            f"✅ Broadcast done — sent: {sent}, failed: {failed}",
            parse_mode="HTML",
            reply_markup=_back_keyboard(),
        )

    logger.info(f"Admin {user.id} broadcast to {sent}/{total} users.")

