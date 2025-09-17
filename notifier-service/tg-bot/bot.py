import asyncio
import logging

from aiogram.types import BotCommand

from core import dp, bot, setup_logging
from handlers import router as user_handlers
from services.rabbit_consumer import RabbitConsumer

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()

    dp.include_router(user_handlers)

    consumer = RabbitConsumer(bot)
    consumer_task: asyncio.Task | None = None

    async def _startup():
        nonlocal consumer_task
        consumer_task = asyncio.create_task(consumer.start())
        logger.info("Rabbit consumer started")

    async def _shutdown():
        nonlocal consumer_task
        await consumer.stop()
        if consumer_task:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Rabbit consumer stopped")

    dp.startup.register(_startup)
    dp.shutdown.register(_shutdown)

    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_my_commands([
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="stop", description="Отписаться от уведомлений"),
        BotCommand(command="ping", description="Проверка связи"),
    ])

    logger.info("Start polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Polling stopped")
