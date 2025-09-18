import logging
import asyncio
import json
from pydantic import BaseModel
from broker import broker, app, llm_exchange, pinger_exchange
from faststream.rabbit import RabbitQueue
from openai_wrapper import OpenAIWrapper
import os

# Логгирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

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
        if int(os.getenv("USE_SKIP_NOTIFICATION")) == 1:
            logging.info("!!!!!USE_SKIP_NOTIFICATION=1")
            # 1. Проверяем skip_notification
            if message.com.get("skip_notification", False):
                logging.info(f"[→] Пропуск обработки для {message.url} (skip_notification=True)")
                return
        else:
            logging.info("!!!!!USE_SKIP_NOTIFICATION=0")
            logging.info(f"[→] Должен быть пропуск этого сообщения,\nно USE_SKIP_NOTIFICATION=False. {message.url} (skip_notification=True)")

        explanation = ""

        # 2. Если нужно звать LLM
        
        if message.com.get("llm", False):
            prompt = (
                f"Проанализируй статус сайта '{message.name}' ({message.url}).\n"
                f"Данные пингера:\n{json.dumps(message.logs, ensure_ascii=False, indent=2)}\n\n"
                f"Объясни на русском языке, что означают эти показатели и ошибки, "
                f"и в каком состоянии находится сайт."
                f"Не пиши много, нужно сделать короткий пост о текущем статусе работы сервиса."
                f"Никак не форматируй текст."
            )
            explanation = llm.send_message(prompt)
            logging.info(explanation)

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
