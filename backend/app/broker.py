import logging
import sys
from pathlib import Path

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import settings  # noqa: E402

logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.rabbit.url)
app = FastStream(broker)

pinger_exchange = RabbitExchange(settings.rabbit.pinger_exchange, type=ExchangeType.TOPIC, durable=True)
llm_exchange = RabbitExchange(settings.rabbit.llm_exchange, type=ExchangeType.TOPIC, durable=True)


@app.after_startup
async def declare():
    await broker.declare_exchange(pinger_exchange)
    await broker.declare_exchange(llm_exchange)


pinger_queue = RabbitQueue(settings.rabbit.pinger_queue, durable=True, routing_key=settings.rabbit.pinger_routing_key)
llm_queue = RabbitQueue(settings.rabbit.llm_queue, durable=True, routing_key=settings.rabbit.llm_routing_key)
