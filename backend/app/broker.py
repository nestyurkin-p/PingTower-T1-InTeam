import logging
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType, RabbitQueue
from app.config import rabbit_cfg

logger = logging.getLogger(__name__)

broker = RabbitBroker(rabbit_cfg.url)
app = FastStream(broker)

pinger_exchange = RabbitExchange(rabbit_cfg.pinger_exchange, type=ExchangeType.TOPIC, durable=True)
llm_exchange = RabbitExchange(rabbit_cfg.llm_exchange, type=ExchangeType.TOPIC, durable=True)


@broker.after_startup
async def declare():
    await broker.declare_exchange(pinger_exchange)
    await broker.declare_exchange(llm_exchange)


pinger_queue = RabbitQueue(rabbit_cfg.pinger_queue, durable=True, routing_key=rabbit_cfg.pinger_rk)
llm_queue = RabbitQueue(rabbit_cfg.llm_queue, durable=True, routing_key=rabbit_cfg.llm_rk)
