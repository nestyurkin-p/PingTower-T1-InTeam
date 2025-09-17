import asyncio
import json
from pathlib import Path
import aio_pika
from environs import Env


def load_env():
    env = Env()
    env.read_env(path=str(Path(__file__).resolve().parents[2] / ".env"))
    return env


async def main():
    env = load_env()
    rabbit_url = env.str("RABBIT_URL", "amqp://root:toor@localhost:5672/")
    exchange_name = env.str("RABBIT_EXCHANGE", "pinger.events")
    routing_key = "alert.triggered"  # consumer слушает '#'

    payload = {
        "severity": "CRITICAL",
        "status": "DOWN",
        "monitor_name": "Landing",
        "target": "https://example.com",
        "reason": "HTTP 502 (10/10 probes failed)",
        "incident_id": env.str("INCIDENT_ID", "test-123"),
    }

    conn = await aio_pika.connect_robust(rabbit_url)
    async with conn:
        ch = await conn.channel()
        ex = await ch.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
        await ex.publish(aio_pika.Message(body=json.dumps(payload).encode()), routing_key=routing_key)
        print(f"published to exchange '{exchange_name}' with rk='{routing_key}'")


if __name__ == "__main__":
    asyncio.run(main())
