import asyncio

import aiohttp
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


def _admin_headers(telegram_id: int) -> dict:
    return {"X-Admin-Id": str(telegram_id)}


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
# /admin — dashboard
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    if not _is_admin(user.id):
        await message.answer("🚫 You are not authorized to use admin commands.")
        return

    data = await _api_get("/api/v1/admin/dashboard", user.id)
    if not data:
        await message.answer("⚠️ Could not load admin dashboard.")
        return

    total_users = data.get("total_users", 0)
    active_today = data.get("active_users_today", 0)
    total_sessions = data.get("total_sessions", 0)
    active_sessions = data.get("active_sessions", 0)
    anon_msgs = data.get("total_anonymous_messages", 0)
    pending_flags = data.get("pending_moderation_flags", 0)
    top_xp = data.get("top_user_xp", 0)

    await message.answer(
        "🛡️ <b>Admin Dashboard</b>\n\n"
        f"👥 <b>Total users:</b> {total_users}\n"
        f"🟢 <b>Active today:</b> {active_today}\n"
        f"💬 <b>Total sessions:</b> {total_sessions}\n"
        f"🔄 <b>Active sessions now:</b> {active_sessions}\n"
        f"📨 <b>Anonymous messages:</b> {anon_msgs}\n"
        f"🚨 <b>Pending flags:</b> {pending_flags}\n"
        f"🏆 <b>Top XP:</b> {top_xp}\n\n"
        "📋 <b>Commands:</b>\n"
        "/admin_users — List recent users\n"
        "/admin_flags — Pending moderation flags\n"
        "/admin_audit — Recent admin actions\n"
        "/admin_channels — Required channels list\n"
        "/admin_add_channel — Add a required channel\n"
        "/admin_remove_channel — Remove a required channel\n"
        "/broadcast — Send a message to all users",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# /admin_users
# ---------------------------------------------------------------------------

@router.message(Command("admin_users"))
async def cmd_admin_users(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    data = await _api_get("/api/v1/admin/users?limit=10", user.id)
    if not data:
        await message.answer("⚠️ Could not load users.")
        return
    if not isinstance(data, list) or not data:
        await message.answer("No users found.")
        return

    lines = ["👥 <b>Recent Users</b>\n"]
    for u in data[:10]:
        name = u.get("first_name") or u.get("username") or f"ID:{u.get('telegram_id')}"
        active = "✅" if u.get("is_active") else "❌"
        lvl = u.get("level", 1)
        xp = u.get("xp", 0)
        convs = u.get("total_conversations", 0)
        lines.append(f"{active} <b>{name}</b> | Lvl {lvl} ({xp} XP) | {convs} chats")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ---------------------------------------------------------------------------
# /admin_flags
# ---------------------------------------------------------------------------

@router.message(Command("admin_flags"))
async def cmd_admin_flags(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    data = await _api_get("/api/v1/admin/flags", user.id)
    if data is None:
        await message.answer("⚠️ Could not load flags.")
        return
    if not data:
        await message.answer("✅ No pending moderation flags.")
        return

    lines = ["🚨 <b>Pending Moderation Flags</b>\n"]
    for flag in data[:10]:
        flag_id = flag.get("id")
        reason = flag.get("reason", "")
        ctype = flag.get("content_type", "")
        cid = flag.get("content_id", "")
        lines.append(f"🔴 #{flag_id} [{ctype}:{cid}] — {reason}")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ---------------------------------------------------------------------------
# /admin_audit
# ---------------------------------------------------------------------------

@router.message(Command("admin_audit"))
async def cmd_admin_audit(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    data = await _api_get("/api/v1/admin/audit-log?limit=10", user.id)
    if data is None:
        await message.answer("⚠️ Could not load audit log.")
        return
    if not data:
        await message.answer("📋 Audit log is empty.")
        return

    lines = ["📋 <b>Recent Admin Actions</b>\n"]
    for log in data[:10]:
        action = log.get("action", "")
        target = log.get("target_id", "")
        admin = log.get("admin_telegram_id", "")
        created_raw = log.get("created_at", "")
        created = str(created_raw)[:10] if created_raw else "unknown"
        lines.append(f"🔹 <b>{action}</b> → {target} by {admin} ({created})")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ---------------------------------------------------------------------------
# /admin_channels — list required channels
# ---------------------------------------------------------------------------

@router.message(Command("admin_channels"))
async def cmd_admin_channels(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    data = await _api_get("/api/v1/admin/channels", user.id)
    if data is None:
        await message.answer("⚠️ Could not load channels.")
        return
    if not data:
        await message.answer(
            "📢 <b>No required channels configured.</b>\n\n"
            "Use /admin_add_channel to add one.",
            parse_mode="HTML",
        )
        return

    lines = ["📢 <b>Required Channels</b>\n"]
    for ch in data:
        db_id = ch.get("id")
        title = ch.get("title", "Unknown")
        username = ch.get("channel_username") or "—"
        active = "✅ Active" if ch.get("is_active") else "❌ Inactive"
        lines.append(f"• <b>{title}</b> ({username}) | {active} | ID: {db_id}")

    lines.append(
        "\n<i>Use /admin_remove_channel &lt;ID&gt; to remove a channel.</i>"
    )
    await message.answer("\n".join(lines), parse_mode="HTML")


# ---------------------------------------------------------------------------
# /admin_add_channel @username  or  /admin_add_channel -100xxx Title
# ---------------------------------------------------------------------------

@router.message(Command("admin_add_channel"))
async def cmd_admin_add_channel(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Usage:\n"
            "  <code>/admin_add_channel @username</code>\n"
            "  <code>/admin_add_channel -100123456789 Channel Title</code>\n\n"
            "<b>Note:</b> The bot must be a member of the channel to verify users' membership.",
            parse_mode="HTML",
        )
        return

    arg = parts[1].strip()

    # Try to resolve the channel via the Telegram API
    try:
        # Case 1: @username or bare username
        if arg.startswith("@") or (not arg.lstrip("-").isdigit()):
            identifier = arg if arg.startswith("@") else f"@{arg}"
            chat = await bot.get_chat(identifier)
        else:
            # Case 2: numeric ID (possibly with a title after it)
            tokens = arg.split(maxsplit=1)
            chat = await bot.get_chat(int(tokens[0]))
    except Exception as e:
        await message.answer(
            f"❌ Could not resolve channel: <code>{e}</code>\n\n"
            "Make sure the bot is a member of that channel and the username/ID is correct.",
            parse_mode="HTML",
        )
        return

    channel_id = chat.id
    channel_username = f"@{chat.username}" if chat.username else None
    title = chat.title or "Unknown Channel"
    invite_link = getattr(chat, "invite_link", None)

    # Build a usable join URL
    if not invite_link:
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        # Private channels without a set invite_link stay None

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

    if result:
        await message.answer(
            f"✅ <b>Channel added:</b> {title}\n"
            f"Username: {channel_username or '—'}\n"
            f"Telegram ID: <code>{channel_id}</code>",
            parse_mode="HTML",
        )
        logger.info(f"Admin {user.id} added required channel: {title} ({channel_id})")
    else:
        await message.answer("⚠️ Failed to add channel. Please try again.")


# ---------------------------------------------------------------------------
# /admin_remove_channel <db_id>
# ---------------------------------------------------------------------------

@router.message(Command("admin_remove_channel"))
async def cmd_admin_remove_channel(message: Message) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer(
            "Usage: <code>/admin_remove_channel &lt;ID&gt;</code>\n\n"
            "Get the ID from /admin_channels.",
            parse_mode="HTML",
        )
        return

    db_id = int(parts[1].strip())
    ok = await _api_delete(f"/api/v1/admin/channels/{db_id}", user.id)

    if ok:
        await message.answer(
            f"✅ Required channel <b>#{db_id}</b> removed.",
            parse_mode="HTML",
        )
        logger.info(f"Admin {user.id} removed required channel db_id={db_id}")
    else:
        await message.answer(
            f"⚠️ Could not remove channel #{db_id}. "
            "Check the ID with /admin_channels and try again."
        )


# ---------------------------------------------------------------------------
# /broadcast <message>
# ---------------------------------------------------------------------------

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Usage: <code>/broadcast Your message here</code>\n\n"
            "The message will be sent to all active users.",
            parse_mode="HTML",
        )
        return

    broadcast_text = parts[1].strip()

    # Fetch all active user IDs from backend
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
        f"📡 <b>Broadcasting to {total} users…</b>\n\n"
        "This may take a moment.",
        parse_mode="HTML",
    )

    sent = 0
    failed = 0

    for uid in user_ids:
        try:
            await bot.send_message(
                chat_id=uid,
                text=f"📢 <b>Announcement</b>\n\n{broadcast_text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1
        # Respect Telegram's rate limit (~30 messages/second to different users)
        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"✅ <b>Broadcast complete!</b>\n\n"
            f"📤 Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"👥 Total: {total}",
            parse_mode="HTML",
        )
    except Exception:
        await message.answer(
            f"✅ Broadcast done — sent: {sent}, failed: {failed}",
            parse_mode="HTML",
        )

    logger.info(f"Admin {user.id} broadcast message to {sent}/{total} users.")
