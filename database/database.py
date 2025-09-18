from __future__ import annotations
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from .models import Base, User, TrackedService, HealthLog


class DataBase:
    def __init__(self, database_url: str | None = None):
        from os import getenv
        self.database_url = database_url or getenv('DATABASE_URL',
                                                   'postgresql+asyncpg://postgres:postgres@localhost:5432/notifier')
        self.engine = create_async_engine(self.database_url, echo=False, pool_pre_ping=True)
        self.async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(self.engine, expire_on_commit=False,
                                                                                  class_=AsyncSession)

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Users
    async def get_user(self, user_id: int) -> Optional[User]:
        async with self.async_session() as session:
            r = await session.execute(select(User).where(User.id == user_id))
            return r.scalar_one_or_none()

    async def upsert_user_tg_chat(self, user_id: int, chat_id: int, login: str | None = None):
        async with self.async_session() as session:
            async with session.begin():
                r = await session.execute(select(User).where(User.id == user_id))
                user = r.scalar_one_or_none()
                if user is None:
                    user = User(id=user_id, login=login, notifications_services={'tg_bot': chat_id},
                                tracked_services=[])
                    session.add(user)
                else:
                    services = dict(user.notifications_services or {})
                    services['tg_bot'] = chat_id
                    user.notifications_services = services
                await session.flush()

    async def disable_user_tg(self, user_id: int):
        async with self.async_session() as session:
            async with session.begin():
                r = await session.execute(select(User).where(User.id == user_id))
                user = r.scalar_one_or_none()
                if user:
                    services = dict(user.notifications_services or {})
                    services.pop('tg_bot', None)
                    user.notifications_services = services
                await session.flush()

    async def get_recipients_for_service(self, service_id: int) -> list[dict[str, int]]:
        async with self.async_session() as session:
            r = await session.execute(select(User))
            out: list[dict[str, int]] = []
            for user in r.scalars().all():
                if user.tracked_services and service_id in user.tracked_services:
                    chat_id = (user.notifications_services or {}).get('tg_bot')
                    if chat_id:
                        out.append({'user_id': user.id, 'tg_chat_id': int(chat_id)})
            return out

    # Tracked services
    async def ensure_tracked_service(self, url: str) -> int:
        async with self.async_session() as session:
            async with session.begin():
                r = await session.execute(select(TrackedService).where(TrackedService.url == url))
                svc = r.scalar_one_or_none()
                if svc:
                    return svc.service_id
                svc = TrackedService(url=url)
                session.add(svc)
                await session.flush()
                return svc.service_id

    async def get_service_by_url(self, url: str) -> Optional[TrackedService]:
        async with self.async_session() as session:
            r = await session.execute(select(TrackedService).where(TrackedService.url == url))
            return r.scalar_one_or_none()

    # Health logs
    async def add_health_log(self, service_id: int, logs: dict[str, Any]) -> int:
        async with self.async_session() as session:
            async with session.begin():
                row = HealthLog(service_id=service_id, logs=logs)
                session.add(row)
                await session.flush()
                return row.id

    async def latest_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self.async_session() as session:
            from sqlalchemy import select, desc
            q = (
                select(HealthLog.id, HealthLog.service_id, TrackedService.url, HealthLog.logs, HealthLog.created_at)
                .join(TrackedService, TrackedService.service_id == HealthLog.service_id)
                .order_by(desc(HealthLog.created_at))
                .limit(limit)
            )
            res = await session.execute(q)
            return [dict(id=r[0], service_id=r[1], url=r[2], logs=r[3], created_at=r[4]) for r in res.all()]

    async def get_users_notifications_for_service(self, service_id: int) -> list[dict[str, Any]]:
        """Возвращает [{'user_id': int, 'notifications': dict}] для всех, кто трекает service_id."""
        async with self.async_session() as session:
            r = await session.execute(select(User))
            out: list[dict[str, Any]] = []
            for user in r.scalars().all():
                if user.tracked_services and service_id in user.tracked_services:
                    out.append({
                        "user_id": user.id,
                        "notifications": dict(user.notifications_services or {}),
                    })
            return out


db = DataBase()
