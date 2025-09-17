from broker import broker, app, pinger_exchange
from faststream.rabbit import RabbitQueue
from pydantic import BaseModel
import logging
import asyncio

# логгирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

class MessageClassExample(BaseModel):
    some_message: str
    something: dict

@broker.subscriber(RabbitQueue("pinger-to-web-queue", durable=True, routing_key="pinger.group"))
# название очереди может быть другое. берём этот аргумент из брокера
async def handler_example(message: MessageClassExample): # лучше типизировать при помощи модели Pydantic,
    # её мы определяем сами
    logging.info(f"Got message: {message}")


@app.after_startup
async def send_test_message():
    await broker.publish( # НАПРЯМУЮ, В ОЧЕРЕДЬ
        {
            "some_message": "ZZZZZZVVVVV",
            "something": {"ZoV": "alice"}
        },
        queue="pinger-to-web-queue",
    )
    # await broker.publish(
    #     {
    #         "some_message": "VVVVVZZZZZZ",
    #         "something": {"VoZ": "alice"}
    #     },
    #     exchange=pinger_exchange, # exchange, который заимпортили
    #     routing_key="pinger.group",  # совпадёт с твоими очередями группы pinger
    # )
    logging.info("Test message published!")


async def start_faststream():
    await app.run()


if __name__ == "__main__":
    asyncio.run(start_faststream())
