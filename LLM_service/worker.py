import logging
import asyncio
import json
import os
from pydantic import BaseModel
from broker import broker, app, llm_exchange, pinger_exchange
from faststream.rabbit import RabbitQueue
from openai_wrapper import OpenAIWrapper

# Логгирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Флаг из окружения
USE_SKIP_NOTIFICATION = int(os.getenv("USE_SKIP_NOTIFICATION", "0"))

# LLM клиент
llm = OpenAIWrapper("sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16")

# Pydantic модель для валидации входящих сообщений
class PingerMessage(BaseModel):
    id: int
    url: str
    name: str
    com: dict
    logs: dict


# Подписчик: слушает сообщения от пингера
@broker.subscriber(
    RabbitQueue("pinger-to-llm-queue", durable=True, routing_key="pinger.group"),
    pinger_exchange,
)
async def handle_pinger_message(message: PingerMessage):
    logging.info(f"[x] Получено сообщение от пингера для сайта {message.name} ({message.url})")

    try:
        # 1. Проверяем skip_notification, если USE_SKIP_NOTIFICATION=1
        if USE_SKIP_NOTIFICATION == 1:
            if message.com.get("skip_notification", False):
                logging.info(f"[→] Пропуск обработки для {message.url} (skip_notification=True)")
                return
        else:
            logging.info(
                f"[→] USE_SKIP_NOTIFICATION=0, сообщение обрабатывается всегда "
                f"(даже если skip_notification=True для {message.url})"
            )

        explanation = ""

        # 2. Если нужно звать LLM
        if message.com.get("llm", False):
            prompt = (
                f"Проанализируй статус сайта '{message.name}' ({message.url}).\n"
                f"Входные данные пингера:\n{json.dumps(message.logs, ensure_ascii=False, indent=2)}\n\n"
                f"Сформулируй краткое резюме о состоянии сайта на русском языке.\n"
                f"Форма ответа:\n"
                f"- Текущее состояние (работает стабильно / есть проблемы / недоступен)\n"
                f"- Основная причина (если есть: задержка, код ответа, SSL, DNS и т.д.)\n"
                f"- Краткий вывод о том, что это значит для пользователей\n\n"
                f"Не используй форматирование, списки Markdown или HTML. Пиши очень коротко и по сути."
            )

            explanation = llm.send_message(prompt)
            logging.info(f"[LLM] {explanation}")

        # 3. Формируем ответ
        response = {
            "id": message.id,
            "url": message.url,
            "name": message.name,
            "com": message.com,
            "logs": message.logs,
            "explanation": explanation,
        }

        # 4. Публикуем в LLM exchange
        await broker.publish(
            response,
            exchange=llm_exchange,
            routing_key="llm.group",
        )
        logging.info(f"[✓] Обработано и отправлено для {message.url}")

    except Exception as e:
        logging.error(f"[!] Ошибка обработки сообщения: {e}")


# Запуск FastStream
async def start_faststream():
    await app.run()


if __name__ == "__main__":
    asyncio.run(start_faststream())
