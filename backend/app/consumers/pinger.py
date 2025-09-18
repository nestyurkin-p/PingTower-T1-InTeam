import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.broker import broker, pinger_exchange, pinger_queue
from app.db.session import async_session
from app.db import crud
from app.schemas import PingerMessage

log = logging.getLogger(__name__)


@broker.subscriber(pinger_queue, exchange=pinger_exchange)
async def handle_pinger(message: PingerMessage):
    id_ = str(message.id)
    ts = message.timestamp
    url = message.url
    ok = message.ok
    status_code = message.metrics.status_code if message.metrics else None
    latency_ms = message.metrics.latency_ms if message.metrics else None
    raw = message.model_dump()
    async with async_session() as session:  # type: AsyncSession
        async with session.begin():
            await crud.upsert_from_pinger(session, id_=id_, timestamp=ts, url=url, ok=ok,
                                          status_code=status_code, latency_ms=latency_ms, raw=raw)
    log.info("pinger saved id=%s ok=%s status=%s", id_, ok, status_code)
