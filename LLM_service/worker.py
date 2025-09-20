import asyncio
import json
import logging
import sys
from pathlib import Path

from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR.parent))

from core.config import settings  # noqa: E402
from broker import broker, app, llm_exchange, pinger_exchange  # noqa: E402
from faststream.rabbit import RabbitQueue  # noqa: E402
from openai_wrapper import OpenAIWrapper  # noqa: E402

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

llm = OpenAIWrapper(
    api_key=settings.llm.api_key,
    model=settings.llm.model,
    base_url=settings.llm.base_url,
)


class PingerMessage(BaseModel):
    id: int
    url: str
    name: str
    com: dict
    logs: dict


@broker.subscriber(
    RabbitQueue("pinger-to-llm-queue", durable=True, routing_key=settings.rabbit.pinger_routing_key),
    pinger_exchange,
)
async def handle_pinger_message(message: PingerMessage):
    logging.info(f"[x] Получено сообщение от пингера для сервиса {message.name} ({message.url})")

    try:
        if settings.llm.use_skip_notification:
            logging.info("USE_SKIP_NOTIFICATION=1")
            if message.com.get("skip_notification", False):
                logging.info(f"[→] Пропускаем уведомление для {message.url} (skip_notification=True)")
                return
        else:
            logging.info("USE_SKIP_NOTIFICATION=0")

        explanation = ""

        if message.com.get("llm", False) and settings.llm.api_key:
            prompt = (
                f"Проанализируй состояние сервиса '{message.name}' ({message.url}).\n"
                f"Последние метрики:\n{json.dumps(message.logs, ensure_ascii=False, indent=2)}\n\n"
                f"Сформулируй краткий вывод о статусе и укажи рекомендации по устранению проблемы."  # noqa: E501
            )
            explanation = llm.send_message(prompt)

        response = {
            "id": message.id,
            "url": message.url,
            "name": message.name,
            "com": message.com,
            "logs": message.logs,
            "explanation": explanation,
        }

        await broker.publish(
            response,
            exchange=llm_exchange,
            routing_key=settings.rabbit.llm_routing_key,
        )
        logging.info(f"[V] Отправлено в LLM exchange для {message.url}")

    except Exception as e:
        logging.error(f"[!] Ошибка обработки сообщения: {e}")


async def start_faststream():
    await app.run()


if __name__ == "__main__":
    asyncio.run(start_faststream())
