import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from backend.app.core.config import settings
from backend.app.core.logging_config import setup_logging, get_logger
from backend.bot.handlers import start, matchmaking, messaging, session
from backend.bot.monitoring import send_monitor_alert

setup_logging()
logger = get_logger(__name__)


async def main() -> None:
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "your-telegram-bot-token":
        logger.error("BOT_TOKEN is not configured. Set it in your .env file.")
        return

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(matchmaking.router)
    dp.include_router(session.router)
    dp.include_router(messaging.router)

    await send_monitor_alert(bot, "INFO", "LingoGenBot started and polling.")
    logger.info("Bot polling started.")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await send_monitor_alert(bot, "WARNING", "LingoGenBot stopped polling.")
        await bot.session.close()
        logger.info("Bot shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
