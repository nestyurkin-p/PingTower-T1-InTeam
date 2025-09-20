import asyncio
import logging

from aiogram.types import BotCommand

from core.config import dp, bot, app_cfg
from core.logging import setup_logging
from handlers.user_handlers import router as user_router

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging(app_cfg.log_level)
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
