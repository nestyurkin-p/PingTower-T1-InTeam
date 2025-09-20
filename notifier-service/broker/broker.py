from __future__ import annotations

import asyncio
import os

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://root:toor@rabbitmq:5672/")

broker = RabbitBroker(RABBIT_URL)
app = FastStream(broker)

pinger_exchange = RabbitExchange(
    "pinger.events",
    type=ExchangeType.TOPIC,
    durable=True,
)

llm_exchange = RabbitExchange(
    "llm.events",
    type=ExchangeType.TOPIC,
    durable=True,
)


@app.after_startup
async def startup() -> None:
    await broker.declare_exchange(pinger_exchange)
    await broker.declare_exchange(llm_exchange)

    await broker.declare_queue(
        RabbitQueue("pinger-to-llm-queue", durable=True, routing_key="pinger.group")
    )
    await broker.declare_queue(
        RabbitQueue("pinger-to-web-queue", durable=True, routing_key="pinger.group")
    )
    await broker.declare_queue(
        RabbitQueue("llm-to-sender-queue", durable=True, routing_key="llm.group")
    )
    await broker.declare_queue(
        RabbitQueue("llm-to-web-queue", durable=True, routing_key="llm.group")
    )
    await broker.declare_queue(
        RabbitQueue("llm-to-dispatcher-queue", durable=True, routing_key="llm.group")
    )


async def start_faststream() -> None:
    await app.run()


if __name__ == "__main__":
    asyncio.run(start_faststream())
