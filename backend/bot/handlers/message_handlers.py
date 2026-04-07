import aiohttp
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)
router = Router()

PAGE_SIZE = 5


class ReplyState(StatesGroup):
    waiting_for_reply = State()


async def _get_inbox(telegram_id: int, limit: int = PAGE_SIZE, offset: int = 0) -> list[dict]:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/messages/inbox/{telegram_id}",
                params={"limit": limit, "offset": offset},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status == 200:
                return await resp.json()
            return []
    except Exception as e:
        logger.error(f"Get inbox error for {telegram_id}: {e}")
        return []


async def _get_unread_count(telegram_id: int) -> int:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/v1/messages/inbox/{telegram_id}/count",
                timeout=aiohttp.ClientTimeout(total=5),
            )
            if resp.status == 200:
                data = await resp.json()
                return data.get("unread", 0)
            return 0
    except Exception as e:
        logger.error(f"Get unread count error: {e}")
        return 0


async def _mark_all_read(telegram_id: int) -> None:
    try:
        async with aiohttp.ClientSession() as client:
            await client.post(
                f"{settings.BACKEND_URL}/api/v1/messages/inbox/{telegram_id}/read-all",
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception as e:
        logger.error(f"Mark all read error: {e}")


async def _reply_to_message(telegram_id: int, message_id: int, reply: str) -> dict | None:
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/api/v1/messages/inbox/{telegram_id}/{message_id}/reply",
                json={"reply_content": reply},
                timeout=aiohttp.ClientTimeout(total=10),
            )
            if resp.status == 200:
                return await resp.json()
            return None
    except Exception as e:
        logger.error(f"Reply to message error: {e}")
        return None


def _format_message(msg: dict, index: int) -> str:
    is_read = msg.get("is_read", False)
    status = "✅" if is_read else "🔔"
    reply = msg.get("reply_content")
    created = msg.get("created_at", "")[:10]
    text = (
        f"{status} <b>Message #{msg['id']}</b> <i>({created})</i>\n"
        f"💬 {msg['content']}\n"
    )
    if reply:
        text += f"↩️ <i>Your reply:</i> {reply}\n"
    return text


@router.message(Command("messages"))
async def cmd_messages(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    unread = await _get_unread_count(user.id)
    msgs = await _get_inbox(user.id, limit=PAGE_SIZE, offset=0)

    if not msgs:
        await message.answer(
            "📭 <b>No messages yet</b>\n\n"
            "Share your profile URL to start receiving anonymous messages!\n"
            "Use /profile_url to get your link.",
            parse_mode="HTML",
        )
        return

    header = f"📬 <b>Your Messages</b> ({unread} unread)\n\n"
    body = "\n".join(_format_message(m, i) for i, m in enumerate(msgs, 1))

    keyboard_rows = []
    for m in msgs:
        if not m.get("reply_content"):
            keyboard_rows.append([
                InlineKeyboardButton(
                    text=f"↩️ Reply to #{m['id']}",
                    callback_data=f"reply_msg:{m['id']}",
                )
            ])
    if len(msgs) == PAGE_SIZE:
        keyboard_rows.append([
            InlineKeyboardButton(text="➡️ Next page", callback_data=f"msgs_page:{PAGE_SIZE}")
        ])
    keyboard_rows.append([
        InlineKeyboardButton(text="✅ Mark all read", callback_data="msgs_mark_read")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows) if keyboard_rows else None
    await message.answer(header + body, parse_mode="HTML", reply_markup=keyboard)

    # Mark messages as read after displaying
    await _mark_all_read(user.id)


@router.callback_query(F.data.startswith("msgs_page:"))
async def msgs_next_page(callback: CallbackQuery) -> None:
    user = callback.from_user
    offset = int(callback.data.split(":")[1])
    msgs = await _get_inbox(user.id, limit=PAGE_SIZE, offset=offset)

    if not msgs:
        await callback.answer("No more messages!", show_alert=True)
        return

    body = "\n".join(_format_message(m, i) for i, m in enumerate(msgs, 1))
    keyboard_rows = []
    for m in msgs:
        if not m.get("reply_content"):
            keyboard_rows.append([
                InlineKeyboardButton(
                    text=f"↩️ Reply to #{m['id']}",
                    callback_data=f"reply_msg:{m['id']}",
                )
            ])
    if len(msgs) == PAGE_SIZE:
        keyboard_rows.append([
            InlineKeyboardButton(text="➡️ Next page", callback_data=f"msgs_page:{offset + PAGE_SIZE}")
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows) if keyboard_rows else None
    await callback.message.answer(body, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "msgs_mark_read")
async def msgs_mark_read(callback: CallbackQuery) -> None:
    user = callback.from_user
    await _mark_all_read(user.id)
    await callback.answer("✅ All messages marked as read!", show_alert=True)


@router.callback_query(F.data.startswith("reply_msg:"))
async def reply_message_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    message_id = int(callback.data.split(":")[1])
    await state.set_state(ReplyState.waiting_for_reply)
    await state.update_data(reply_to_id=message_id)
    await callback.message.answer(
        f"↩️ <b>Replying to message #{message_id}</b>\n\n"
        "Send your reply (max 500 chars):\n"
        "<i>Note: Your identity remains semi-anonymous — "
        "the sender will see your reply but won't know who you are.</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ReplyState.waiting_for_reply)
async def send_reply(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if not user or not message.text:
        return

    data = await state.get_data()
    message_id = data.get("reply_to_id")
    await state.clear()

    if not message_id:
        await message.answer("⚠️ Something went wrong. Please try /messages again.")
        return

    reply_text = message.text.strip()[:500]
    result = await _reply_to_message(user.id, message_id, reply_text)

    if result:
        await message.answer(
            "✅ <b>Reply sent!</b>\n\n"
            "Your reply has been saved with the anonymous message.",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "⚠️ Could not send reply. The message may not exist.",
            parse_mode="HTML",
        )
