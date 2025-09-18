import asyncio
import logging
from aiogram.types import BotCommand
from aiogram import Dispatcher
from pydantic import BaseModel

from core import dp, bot, setup_logging
from handlers import router as user_handlers
from utils import subscriptions

from broker import broker, app, llm_exchange
from faststream.rabbit import RabbitQueue

logger = logging.getLogger(__name__)

# Pydantic модель для сообщений
class AlertMessage(BaseModel):
    id: int
    url: str
    name: str
    com: dict
    logs: dict
    explanation: str | None = None


@broker.subscriber(
    RabbitQueue("llm-to-tg-queue", durable=True, routing_key="llm.group"),
    llm_exchange,
)
async def handle_alert(message: AlertMessage):
    logger.info(f"[x] Получено сообщение для TG: {message.url}")

    try:
        # Если есть explanation — используем его
        if message.explanation:
            text = (
                f"📡 <b>{message.name}</b> ({message.url})\n\n"
                f"{message.explanation}"
            )
        else:
            logs = message.logs or {}
            metrics = logs.get("metrics", {}) or {}
            errors = logs.get("errors", []) or []

            status_code = metrics.get("status")
            rtt = metrics.get("rtt")
            ok = status_code == 200

            status_icon = "✅" if ok else "❌"

            # Базовый блок
            text = (
                f"{status_icon} <b>{message.name}</b> ({message.url})\n"
                f"🕒 Время: {logs.get('timestamp')}\n"
                f"📡 Код ответа: {status_code}\n"
                f"⚡ RTT: {rtt} сек\n"
            )

            # Добавляем ошибки, если есть
            if errors:
                text += "\n<b>Ошибки:</b>\n"
                for e in errors:
                    text += f"• {e.get('code')}: {e.get('message')}\n"

        # Рассылка подписчикам
        chat_ids = await subscriptions.get_all()
        logger.info("Broadcast to %d subscribers", len(chat_ids))
        if not chat_ids:
            logger.info("No subscribers found. Skipping send.")
            return

        for cid in chat_ids:
            try:
                await bot.send_message(cid, text, parse_mode="HTML")
            except Exception as e:
                logger.exception("Send failed to chat_id=%s: %s", cid, e)

    except Exception as e:
        logger.exception("Ошибка обработки сообщения: %s", e)


async def main() -> None:
    setup_logging()
    dp.include_router(user_handlers)

    # команды для бота
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
