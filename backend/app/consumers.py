import logging
from database import db
from app.broker import broker, pinger_exchange, pinger_queue, llm_exchange, llm_queue

log = logging.getLogger(__name__)

@broker.subscriber(pinger_queue, exchange=pinger_exchange)
async def handle_pinger(message: dict):
    await db.upsert_from_pinger(message)
    log.info("pinger saved id=%s", message.get("id"))

@broker.subscriber(llm_queue, exchange=llm_exchange)
async def handle_llm(message: dict):
    await db.upsert_from_llm(message)
    log.info("llm saved id=%s", message.get("id"))
