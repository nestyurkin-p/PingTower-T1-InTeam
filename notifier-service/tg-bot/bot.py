import asyncio
import logging
import json

from aiogram.types import BotCommand
from pydantic import BaseModel

from core.config import dp, bot, app_cfg
from core.logging import setup_logging
from handlers.user_handlers import router as user_router
from handlers import router as user_handlers
from utils.formatter import format_alert
from utils import subscriptions

from broker import broker, app, llm_exchange
from faststream.rabbit import RabbitQueue

logger = logging.getLogger(__name__)

# Pydantic модель для сообщений из очереди
class AlertMessage(BaseModel):
    id: int | None = None
    url: str | None = None
    name: str | None = None
    com: dict | None = None
    logs: dict | None = None
    explanation: str | None = None


# Подписчик FastStream: слушает сообщения из LLM (или пингера)
@broker.subscriber(
    RabbitQueue("llm-to-tg-queue", durable=True, routing_key="llm.group"),
    llm_exchange,
)
async def handle_alert(message: AlertMessage):
    logger.info(f"[x] Получено сообщение для TG: {message.url or message.id}")

    try:
        # формируем текст уведомления
        payload = message.model_dump()
        text = format_alert(payload)

        chat_ids = await subscriptions.get_all()
        logger.info("Broadcast to %d subscribers", len(chat_ids))
        if not chat_ids:
            logger.info("No subscribers found. Skipping send.")
            return

        for cid in chat_ids:
            try:
                await bot.send_message(cid, text)
            except Exception as e:
                logger.exception("Send failed to chat_id=%s: %s", cid, e)

    except Exception as e:
        logger.exception("Ошибка обработки сообщения: %s", e)


async def main() -> None:
    setup_logging(app_cfg.log_level)
    dp.include_router(user_router)
    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_my_commands([
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="stop", description="Отписаться от уведомлений"),
        BotCommand(command="ping", description="Проверка связи"),
    ])

    logger.info("Start polling")

    # запускаем aiogram и FastStream вместе
    await asyncio.gather(
        dp.start_polling(bot),
        app.run(),   # FastStream
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Polling stopped")
