import traceback
from datetime import datetime, timezone

from aiogram import Bot
from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


async def send_monitor_alert(bot: Bot, level: str, message: str, extra: dict | None = None) -> None:
    if not settings.MONITOR_CHANNEL_ID:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    level_emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔴"}.get(level, "📌")

    text = (
        f"{level_emoji} <b>[{level}] {settings.APP_NAME}</b>\n"
        f"🕐 <code>{timestamp}</code>\n"
        f"📋 {message}"
    )

    if extra:
        for k, v in extra.items():
            text += f"\n• <b>{k}</b>: <code>{v}</code>"

    try:
        await bot.send_message(
            chat_id=settings.MONITOR_CHANNEL_ID,
            text=text,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to send monitor alert: {e}")


async def send_error_alert(bot: Bot, error: Exception, context: str, user_id: int | None = None) -> None:
    tb = traceback.format_exc()
    extra: dict = {"Context": context, "Error": str(error)[:200]}
    if user_id:
        extra["User ID"] = str(user_id)
    if tb and tb != "NoneType: None\n":
        extra["Traceback"] = f"\n<pre>{tb[:800]}</pre>"

    await send_monitor_alert(bot, "ERROR", f"Unhandled exception in {context}", extra)
