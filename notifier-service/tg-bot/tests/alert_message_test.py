import asyncio
import uuid
from pathlib import Path
from environs import Env
from faststream.rabbit import RabbitBroker


def load_env():
    env = Env()
    env.read_env(path=str(Path(__file__).resolve().parents[2] / ".env"))
    return env


async def main():
    env = load_env()
    rabbit_url = env.str("RABBIT_URL", "amqp://root:toor@localhost:5672/")
    queue_name = env.str("RABBIT_QUEUE", "pinger-to-notifier-queue")

    broker = RabbitBroker(rabbit_url)
    await broker.start()
    try:
        payload = {
            "severity": "CRITICAL",
            "status": "DOWN",
            "monitor_name": "Landing",
            "target": "https://example.com",
            "reason": "HTTP 502 (10/10 probes failed)",
            "incident_id": f"test-{uuid.uuid4()}",
        }
        # default exchange -> routing_key == имя очереди
        await broker.publish(payload, queue=queue_name)
        print(f"published directly to queue '{queue_name}'")
    finally:
        # FastStream >=0.5.44 рекомендует stop()
        await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
