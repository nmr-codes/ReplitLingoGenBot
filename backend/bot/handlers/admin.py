import aiohttp
from aiogram import Router
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


async def _api_get_admin(path: str, admin_id: int) -> dict | list | None:
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


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    if not _is_admin(user.id):
        await message.answer("🚫 You are not authorized to use admin commands.")
        return

    data = await _api_get_admin("/api/v1/admin/dashboard", user.id)
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
        "/admin_audit — Recent admin actions",
        parse_mode="HTML",
    )


@router.message(Command("admin_users"))
async def cmd_admin_users(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    data = await _api_get_admin("/api/v1/admin/users?limit=10", user.id)
    if not data:
        await message.answer("⚠️ Could not load users.")
        return

    if not data:
        await message.answer("No users found.")
        return

    lines = ["👥 <b>Recent Users</b>\n"]
    for u in data[:10]:
        name = u.get("first_name") or u.get("username") or f"ID:{u.get('telegram_id')}"
        active = "✅" if u.get("is_active") else "❌"
        lvl = u.get("level", 1)
        xp = u.get("xp", 0)
        convs = u.get("total_conversations", 0)
        lines.append(
            f"{active} <b>{name}</b> | Lvl {lvl} ({xp} XP) | {convs} chats"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("admin_flags"))
async def cmd_admin_flags(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    data = await _api_get_admin("/api/v1/admin/flags", user.id)
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


@router.message(Command("admin_audit"))
async def cmd_admin_audit(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    if not _is_admin(user.id):
        await message.answer("🚫 Not authorized.")
        return

    data = await _api_get_admin("/api/v1/admin/audit-log?limit=10", user.id)
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
        created = log.get("created_at", "")[:10]  # date only
        lines.append(f"🔹 <b>{action}</b> → {target} by {admin} ({created})")

    await message.answer("\n".join(lines), parse_mode="HTML")
