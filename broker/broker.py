from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType
import asyncio

broker = RabbitBroker("amqp://root:toor@rabbitmq:5672/")
app = FastStream(broker)

# exchange группируют очереди. если отправляем сообщение по routing_key,
# оно приходит во все очереди с таким routing_key
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
async def startup():
    await broker.declare_exchange(pinger_exchange)
    await broker.declare_exchange(llm_exchange)

    # декларируем очереди
    await broker.declare_queue(
        RabbitQueue("pinger-to-llm-queue", durable=True, routing_key="pinger.group")
        # routing_key может быть любой строкой, но принято писать через точки и осмысленно
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


async def start_faststream():
    await app.run()


if __name__ == "__main__":
    asyncio.run(start_faststream())