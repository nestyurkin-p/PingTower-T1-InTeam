import logging
import asyncio
import json
from pydantic import BaseModel
from broker import broker, app, llm_exchange, pinger_exchange
from faststream.rabbit import RabbitQueue
from openai_wrapper import OpenAIWrapper

# Логгирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# LLM клиент
<<<<<<< HEAD
<<<<<<< HEAD
llm = OpenAIWrapper(api_key="sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16")
=======
llm = OpenAIWrapper("sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16")
>>>>>>> 84c27474864f74470f4df2e37ee9ca961b092d39
=======
llm = OpenAIWrapper("sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16")
>>>>>>> ff0b6af37333065e45fa807af709a80d7707af89

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
        # Проверяем skip_notification
        if message.com.get("skip_notification", False):
            logging.info(f"[→] Пропуск обработки для {message.url} (skip_notification=True)")
            return

        # Формируем запрос для LLM
        prompt = (
            f"Проанализируй статус сайта '{message.name}' ({message.url}).\n"
            f"Данные пингера:\n{json.dumps(message.logs, ensure_ascii=False, indent=2)}\n\n"
            f"Объясни на русском языке, что означают эти показатели и ошибки, "
            f"и в каком состоянии находится сайт."
        )

        # Отправляем в LLM
        explanation = llm.send_message(prompt)

        response = {
            "logs": message.model_dump(),   # ✅ вместо .dict()
            "explanation": explanation,
        }

        # Отправляем обратно в очередь LLM
        await broker.publish(
            response,
            exchange=llm_exchange,
            routing_key="llm.group",
        )
        logging.info(f"[✓] Объяснение для сайта {message.url} отправлено")

    except Exception as e:
        logging.error(f"[!] Ошибка обработки сообщения: {e}")


# Запуск FastStream
async def start_faststream():
    await app.run()


if __name__ == "__main__":
    asyncio.run(start_faststream())
