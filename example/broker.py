from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

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
