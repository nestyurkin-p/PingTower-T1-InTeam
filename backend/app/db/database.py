from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, update, func, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base, User, TrackedService, HealthLog


class DataBase:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(self.database_url, echo=False, pool_pre_ping=True)
        self.async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # ------------- вспомогательное -------------

    async def ensure_tracked_service(self, url: str) -> int:
        """Вернёт service_id; создаст, если нет."""
        async with self.async_session() as session:
            async with session.begin():
                q = select(TrackedService).where(TrackedService.url == url)
                r = await session.execute(q)
                svc = r.scalar_one_or_none()
                if svc:
                    return svc.service_id
                svc = TrackedService(url=url)
                session.add(svc)
                await session.flush()
                return svc.service_id

    # ------------- приём событий -------------

    async def upsert_from_pinger(self, payload: dict[str, Any]) -> None:
        """
        Сохраняем событие пингера:
        - ищем/создаём tracked_service по url (или metrics.final_url)
        - пишем запись в health_logs (JSON целиком).
        """
        url = (
                payload.get("url")
                or (payload.get("metrics") or {}).get("final_url")
                or ""
        )
        if not url:
            # без URL не сможем связать с сервисом — но всё равно сохраним как 'unknown'
            url = "unknown"

        service_id = await self.ensure_tracked_service(url)

        async with self.async_session() as session:
            async with session.begin():
                log = HealthLog(service_id=service_id, logs=payload)
                session.add(log)

    async def upsert_from_llm(self, payload: dict[str, Any]) -> None:
        """
        Сохраняем событие LLM:
        - ищем последнюю запись health_logs, где logs->>'id' совпадает (если пингер кладёт id в JSON)
        - если нет — просто создаём новую запись (будет висеть без service_id только если его нет)
        """
        ext_id = payload.get("id")
        # попробуем достать URL из payload (могут прислать вместе с вердиктом)
        url = payload.get("url")

        async with self.async_session() as session:
            async with session.begin():
                log_row: Optional[HealthLog] = None

                if ext_id is not None:
                    # ищем по JSONB: logs->>'id' = ext_id
                    q = (
                        select(HealthLog)
                        .where(HealthLog.logs["id"].astext == str(ext_id))
                        .order_by(desc(HealthLog.created_at))
                        .limit(1)
                    )
                    r = await session.execute(q)
                    log_row = r.scalar_one_or_none()

                if log_row:
                    # аккуратно мерджим JSON: добавим/обновим поле "llm_result"
                    new_logs = dict(log_row.logs or {})
                    new_logs["llm_result"] = payload.get("result")
                    # опционально: переложим что-то ещё из LLM
                    session.add(log_row)  # не обязательно, но ок
                    await session.execute(
                        update(HealthLog)
                        .where(HealthLog.id == log_row.id)
                        .values(logs=new_logs, created_at=func.coalesce(HealthLog.created_at, func.now()))
                    )
                else:
                    # не нашли пару по id — создадим новую запись
                    if url:
                        service_id = await self.ensure_tracked_service(url)
                    else:
                        service_id = await self.ensure_tracked_service("unknown")
                    session.add(HealthLog(service_id=service_id, logs=payload))

    # ------------- запросы -------------

    async def list_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Возвращает последние N логов с URL сервиса.
        Формат элемента: {"id": <int>, "service_id": <int>, "url": <str>, "logs": <dict>, "created_at": <dt>}
        """
        async with self.async_session() as session:
            q = (
                select(
                    HealthLog.id,
                    HealthLog.service_id,
                    TrackedService.url,
                    HealthLog.logs,
                    HealthLog.created_at,
                )
                .join(TrackedService, TrackedService.service_id == HealthLog.service_id)
                .order_by(HealthLog.created_at.desc())
                .limit(limit)
            )
            res = await session.execute(q)
            rows = res.all()
            return [
                dict(id=r[0], service_id=r[1], url=r[2], logs=r[3], created_at=r[4])
                for r in rows
            ]
