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
        tg_flag = message.com.get("tg")

        try:
            tg_flag = int(tg_flag)
        except (TypeError, ValueError):
            tg_flag = 0

        if tg_flag != 1:
            logger.info(f"[→] Сообщение для {message.url} пропущено (com.tg != 1)")
            return


        logs = message.logs or {}

        # Значения из logs
        traffic_light = logs.get("traffic_light")
        http_status = logs.get("http_status")
        latency_ms = logs.get("latency_ms")
        ping_ms = logs.get("ping_ms")
        ssl_days_left = logs.get("ssl_days_left")
        dns_resolved = logs.get("dns_resolved")
        redirects = logs.get("redirects")
        errors_last = logs.get("errors_last")

        # Иконка статуса
        icon_map = {"green": "✅", "orange": "🟠", "red": "❌"}
        status_icon = icon_map.get(traffic_light, "❔")

        # Блок статистики
        stats_text = (
            f"<b>{message.name}</b> ({message.url})\n"
            f"{status_icon} Светофор: {traffic_light.upper()}\n\n"
            f"🕒 Время: {logs.get('timestamp')}\n"
            f"📡 Код ответа: {http_status}\n"
            f"⚡ Задержка HTTP: {latency_ms} мс\n"
            f"📶 Пинг: {ping_ms} мс\n"
            f"🔐 SSL дней осталось: {ssl_days_left}\n"
            f"🌐 DNS резолвинг: {'OK' if dns_resolved else 'FAIL'}\n"
            f"↪️ Редиректы: {redirects}\n"
            f"❗ Ошибки (последние проверки): {errors_last}\n"
        )

        # Рассылка подписчикам
        chat_ids = await subscriptions.get_all()
        logger.info("Broadcast to %d subscribers", len(chat_ids))
        if not chat_ids:
            logger.info("No subscribers found. Skipping send.")
            return

        for cid in chat_ids:
            try:
                await bot.send_message(cid, stats_text, parse_mode="HTML")

                if message.explanation:
                    await bot.send_message(cid, message.explanation, parse_mode="HTML")

            except Exception as e:
                logger.exception("Send failed to chat_id=%s: %s", cid, e)

    except Exception as e:
        logger.exception("Ошибка обработки сообщения: %s", e)



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
