import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

BOT_DIR = Path(__file__).resolve().parent
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))
ROOT_DIR = BOT_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import settings  # noqa: E402
from app_core import setup_logging  # noqa: E402
from handlers.admin import router as admin_router  # noqa: E402
from handlers.user_handlers import router as user_router  # noqa: E402
from database import db  # noqa: E402

logger = logging.getLogger(__name__)

if not settings.telegram.token:
    raise RuntimeError("TG_TOKEN must be configured in the global .env file")

bot = Bot(token=settings.telegram.token, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


async def main() -> None:
    setup_logging(settings.log_level)
    if db is None:
        raise RuntimeError("Database connection is not configured")
    logger.info("Ensuring database schema is up to date")
    await db.create_tables()
    logger.info(
        "Bot starting with admins=%s, rabbit_url=%s",
        settings.telegram.admin_ids or "<none>",
        settings.rabbit.url,
    )
    dp.include_router(admin_router)
    dp.include_router(user_router)
    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_my_commands([
        BotCommand(command="start", description="Subscribe to notifications"),
        BotCommand(command="stop", description="Unsubscribe from notifications"),
        BotCommand(command="ping", description="Check bot availability"),
    ])

    logger.info("Start polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Polling stopped")
