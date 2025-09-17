import logging
import asyncio
import json
from pydantic import BaseModel
from broker import broker, app, pinger_exchange
from faststream.rabbit import RabbitQueue
from openai_wrapper import OpenAIWrapper

# Логгирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Очереди
QUEUE_IN = RabbitQueue("llm_requests", durable=True, routing_key="llm.requests")
QUEUE_OUT_ROUTING_KEY = "llm.responses"

# LLM клиент
llm = OpenAIWrapper(api_key="sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16")

# Pydantic модель для валидации входящих сообщений
class LLMRequest(BaseModel):
    query: str

# Подписчик: слушает входящую очередь
@broker.subscriber(QUEUE_IN)
async def handle_llm_request(message: LLMRequest):
    logging.info(f"[x] Получено сообщение: {message.query}")

    try:
        result = llm.send_message(message.query)
        response = {"query": message.query, "response": result}

        await broker.publish(
            response,
            exchange=pinger_exchange,
            routing_key=QUEUE_OUT_ROUTING_KEY,
        )
        logging.info(f"[✓] Отправлен результат: {str(result)[:60]}...")

    except Exception as e:
        logging.error(f"[!] Ошибка обработки сообщения: {e}")

# Хук после старта приложения
@app.after_startup
async def startup_test_message():
    await broker.publish(
        {"msg": "LLM worker запущен и готов"},
        exchange=pinger_exchange,
        routing_key="llm.system",
    )
    logging.info("[*] Тестовое сообщение отправлено")

# Запуск FastStream
async def start_faststream():
    await app.run()

if __name__ == "__main__":
    asyncio.run(start_faststream())
