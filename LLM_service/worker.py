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
# llm = OpenAIWrapper(api_key="sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16")

llm = OpenAIWrapper("sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16")

# Pydantic модель для валидации входящих сообщений
class LLMRequest(BaseModel):
    query: str

# Подписчик: слушает входящую очередь
@broker.subscriber(RabbitQueue("pinger-to-llm-queue", durable=True, routing_key="pinger.group"), pinger_exchange)
async def handle_llm_request(message: LLMRequest):
    logging.info(f"[x] Получено сообщение: {message.query}")

    try:
        result = llm.send_message(message.query)
        response = {"query": message.query, "response": result}

        await broker.publish(
            response,
            exchange=llm_exchange,
            routing_key='llm.group',
        )
        logging.info(f"[✓] Отправлен результат: {str(result)[:60]}...")

    except Exception as e:
        logging.error(f"[!] Ошибка обработки сообщения: {e}")

# Запуск FastStream
async def start_faststream():
    await app.run()

if __name__ == "__main__":
    asyncio.run(start_faststream())
