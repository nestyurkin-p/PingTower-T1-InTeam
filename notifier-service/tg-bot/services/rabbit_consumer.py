import asyncio
import json
import logging
from typing import Any, Dict, List

import aio_pika
from aiogram import Bot

from core.config import config
from utils.formatter import format_alert
from utils import subscriptions

logger = logging.getLogger(__name__)


class RabbitConsumer:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._stopping = asyncio.Event()

    async def start(self):
        backoff = 1
        while not self._stopping.is_set():
            try:
                await self._run_once()
                backoff = 1  # reset после успешной сессии
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Rabbit consumer crashed: %s", e)
                await asyncio.sleep(min(backoff, 30))
                backoff = min(backoff * 2, 30)

    async def stop(self):
        self._stopping.set()

    async def _run_once(self):
        logger.info("Connecting to RabbitMQ %s", config.rabbit.url)
        conn = await aio_pika.connect_robust(
            config.rabbit.url,
            client_properties={"connection_name": "notifier-service/tg-bot"},
        )
        async with conn:
            ch = await conn.channel()
            await ch.set_qos(prefetch_count=config.rabbit.prefetch)

            exchange = await ch.declare_exchange(
                config.rabbit.exchange, aio_pika.ExchangeType.TOPIC, durable=True
            )
            queue = await ch.declare_queue(config.rabbit.queue, durable=True)
            # биндимся к exchange — это для публикаций «в обменник»
            await queue.bind(exchange, routing_key=config.rabbit.routing_key)

            logger.info(
                "Consuming: exchange=%s rk=%s queue=%s",
                config.rabbit.exchange,
                config.rabbit.routing_key,
                config.rabbit.queue,
            )

            async with queue.iterator() as it:
                async for message in it:
                    async with message.process(requeue=False):
                        try:
                            payload = self._parse_message(message.body)
                            inc = payload.get("incident_id") or payload.get("event_id") or "<no-id>"
                            logger.info("Alert received: incident_id=%s", inc)
                            await self._broadcast(payload)
                        except Exception:
                            logger.exception("Failed to process message")

    def _parse_message(self, body: bytes) -> Dict[str, Any]:
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {"message": body.decode("utf-8", errors="ignore")}

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        text = format_alert(payload)
        chat_ids: List[int] = await subscriptions.get_all()
        logger.info("Broadcast to %d subscribers", len(chat_ids))
        if not chat_ids:
            # на INFO, чтобы сразу видно было в логах
            logger.info("No subscribers found. Skipping send.")
            return

        # отправляем по одному с логами ошибок, чтобы не терять причины
        for cid in chat_ids:
            try:
                await self.bot.send_message(cid, text)
            except Exception as e:
                logger.exception("Send failed to chat_id=%s: %s", cid, e)
