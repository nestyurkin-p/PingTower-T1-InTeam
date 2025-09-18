import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.broker import broker, llm_exchange, llm_queue
from app.db.session import async_session
from app.db import crud
from app.schemas import LlmMessage

log = logging.getLogger(__name__)


@broker.subscriber(llm_queue, exchange=llm_exchange)
async def handle_llm(message: LlmMessage):
    id_ = str(message.id)
    raw = message.model_dump()
    verdict = message.result
    async with async_session() as session:  # type: AsyncSession
        async with session.begin():
            await crud.upsert_from_llm(session, id_=id_, verdict=verdict, raw=raw)
    log.info("llm saved id=%s verdict=%s", id_, (verdict[:64] + "...") if verdict and len(verdict) > 64 else verdict)
