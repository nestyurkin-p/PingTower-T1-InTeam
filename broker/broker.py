from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR.parent))

from core.config import settings  # noqa: E402

broker = RabbitBroker(settings.rabbit.url)
app = FastStream(broker)

pinger_exchange = RabbitExchange(
    settings.rabbit.pinger_exchange,
    type=ExchangeType.TOPIC,
    durable=True,
)

llm_exchange = RabbitExchange(
    settings.rabbit.llm_exchange,
    type=ExchangeType.TOPIC,
    durable=True,
)


@app.after_startup
async def startup() -> None:
    await broker.declare_exchange(pinger_exchange)
    await broker.declare_exchange(llm_exchange)

    await broker.declare_queue(
        RabbitQueue("pinger-to-llm-queue", durable=True, routing_key=settings.rabbit.pinger_routing_key)
    )
    await broker.declare_queue(
        RabbitQueue("pinger-to-web-queue", durable=True, routing_key=settings.rabbit.pinger_routing_key)
    )

    await broker.declare_queue(
        RabbitQueue("llm-to-sender-queue", durable=True, routing_key=settings.rabbit.llm_routing_key)
    )
    await broker.declare_queue(
        RabbitQueue("llm-to-web-queue", durable=True, routing_key=settings.rabbit.llm_routing_key)
    )
    await broker.declare_queue(
        RabbitQueue("llm-to-dispatcher-queue", durable=True, routing_key=settings.rabbit.llm_routing_key)
    )


async def start_faststream() -> None:
    await app.run()


if __name__ == "__main__":
    asyncio.run(start_faststream())
