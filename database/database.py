from __future__ import annotations

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base, Site, Team, User
from core.config import TelegramSettings


class DataBase:
    def __init__(self, database_url: str):
        if not database_url or not database_url.strip():
            raise ValueError("database_url must be a non-empty string")
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        self.async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def create_tables(self) -> None:
        """Create required tables if they are not present."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("ALTER TABLE sites ADD COLUMN IF NOT EXISTS last_ok BOOLEAN"))
            await conn.execute(text("ALTER TABLE sites ADD COLUMN IF NOT EXISTS last_status TEXT"))
            await conn.execute(text("ALTER TABLE sites ADD COLUMN IF NOT EXISTS last_rtt DOUBLE PRECISION"))
            await conn.execute(text("ALTER TABLE sites ADD COLUMN IF NOT EXISTS skip_notification BOOLEAN DEFAULT FALSE NOT NULL"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT TRUE NOT NULL"))

        # -----------------------------   USERS   ----------------------------- #

    async def upsert_user_tg_chat(
        self,
        user_id: int,
        chat_id: int,
        login: str | None = None,
    ) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError('user_id must be a positive integer')
        if not isinstance(chat_id, int) or chat_id <= 0:
            raise ValueError('chat_id must be a positive integer')
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.tg_user_id == user_id).with_for_update()
                )
                user = result.scalar_one_or_none()
                if user is None:
                    user = User(tg_user_id=user_id)
                    session.add(user)
                user.tg_chat_id = chat_id
                user.login = login
                user.enabled = True
                await session.flush()

    async def disable_user_tg(self, user_id: int) -> None:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError('user_id must be a positive integer')
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.tg_user_id == user_id).with_for_update()
                )
                user = result.scalar_one_or_none()
                if user is None:
                    return
                user.enabled = False
                user.tg_chat_id = None
                await session.flush()

# -----------------------------   SITES   ----------------------------- #

    async def ensure_site(
        self,
        url: str,
        name: str,
        com: dict | None = None,
        ping_interval: int | None = None,
    ) -> int:
        """Return an existing site id by URL or create a new record."""
        if not url:
            raise ValueError("url must be provided")
        if not name:
            raise ValueError("name must be provided")
        if ping_interval is not None and ping_interval <= 0:
            raise ValueError("ping_interval must be positive when provided")
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(select(Site).where(Site.url == url))
                site = result.scalar_one_or_none()
                if site:
                    return site.id
                payload: dict[str, Any] = {
                    "url": url,
                    "name": name,
                    "com": com or {},
                    "ping_interval": ping_interval if ping_interval is not None else 30,
                }
                site = Site(**payload)
                session.add(site)
                await session.flush()
                return site.id

    async def get_site_by_id(self, site_id: int) -> Site | None:
        """Fetch site by primary key."""
        async with self.async_session() as session:
            return await session.get(Site, site_id)

    async def get_site_by_url(self, url: str) -> Site | None:
        """Fetch site matched by URL."""
        if not url:
            raise ValueError("url must be provided")
        async with self.async_session() as session:
            result = await session.execute(select(Site).where(Site.url == url))
            return result.scalar_one_or_none()

    async def list_sites(self) -> list[Site]:
        """Return all sites ordered by name then id."""
        async with self.async_session() as session:
            result = await session.execute(select(Site).order_by(Site.name, Site.id))
            return list(result.scalars().all())

    async def update_site(
        self,
        site_id: int,
        *,
        url: str | None = None,
        name: str | None = None,
        com: dict | None = None,
        ping_interval: int | None = None,
    ) -> bool:
        """Update mutable fields of a site record."""
        if url is None and name is None and com is None and ping_interval is None:
            return False
        async with self.async_session() as session:
            async with session.begin():
                site = await session.get(Site, site_id, with_for_update=True)
                if site is None:
                    return False
                if url is not None:
                    if not url:
                        raise ValueError("url cannot be empty")
                    site.url = url
                if name is not None:
                    if not name:
                        raise ValueError("name cannot be empty")
                    site.name = name
                if com is not None:
                    site.com = dict(com)
                if ping_interval is not None:
                    if ping_interval <= 0:
                        raise ValueError("ping_interval must be positive")
                    site.ping_interval = ping_interval
                await session.flush()
                return True

    async def delete_site(self, site_id: int) -> bool:
        """Remove site by id."""
        async with self.async_session() as session:
            async with session.begin():
                site = await session.get(Site, site_id, with_for_update=True)
                if site is None:
                    return False
                await session.delete(site)
                return True

    async def set_ping_interval(self, site_id: int, ping_interval: int) -> bool:
        """Set site's ping interval."""
        if ping_interval <= 0:
            raise ValueError("ping_interval must be positive")
        return await self.update_site(site_id, ping_interval=ping_interval)

    async def update_last_traffic_light(self, site_id: int, traffic_light: str | None) -> bool:
        """Persist latest traffic light state for a site."""
        async with self.async_session() as session:
            async with session.begin():
                site = await session.get(Site, site_id, with_for_update=True)
                if site is None:
                    return False
                site.last_traffic_light = traffic_light
                await session.flush()
                return True

    async def append_history_event(
        self,
        site_id: int,
        event: dict,
        *,
        max_len: int | None = 100,
    ) -> bool:
        """Append an event to site's history while keeping it bounded."""
        if not isinstance(event, dict):
            raise ValueError("event must be a dictionary")
        if max_len is not None and max_len <= 0:
            raise ValueError("max_len must be positive when provided")
        async with self.async_session() as session:
            async with session.begin():
                site = await session.get(Site, site_id, with_for_update=True)
                if site is None:
                    return False
                history = list(site.history or [])
                history.append(event)
                if max_len is not None and len(history) > max_len:
                    history = history[-max_len:]
                site.history = history
                await session.flush()
                return True

    # -----------------------------   TEAMS   ----------------------------- #

    async def create_team(self, name: str, description: str | None = None) -> int:
        """Create a new team and return its id."""
        if not name:
            raise ValueError("name must be provided")
        async with self.async_session() as session:
            async with session.begin():
                team = Team(name=name, description=description)
                session.add(team)
                await session.flush()
                return team.id

    async def get_team(self, team_id: int) -> Team | None:
        """Fetch team by id."""
        async with self.async_session() as session:
            return await session.get(Team, team_id)

    async def get_team_by_name(self, name: str) -> Team | None:
        """Fetch team by unique name."""
        if not name:
            raise ValueError("name must be provided")
        async with self.async_session() as session:
            result = await session.execute(select(Team).where(Team.name == name))
            return result.scalar_one_or_none()

    async def list_teams(self) -> list[Team]:
        """Return all teams ordered by name."""
        async with self.async_session() as session:
            result = await session.execute(select(Team).order_by(Team.name, Team.id))
            return list(result.scalars().all())

    async def update_team(
        self,
        team_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> bool:
        """Update team's main attributes."""
        if name is None and description is None:
            return False
        async with self.async_session() as session:
            async with session.begin():
                team = await session.get(Team, team_id, with_for_update=True)
                if team is None:
                    return False
                if name is not None:
                    if not name:
                        raise ValueError("name cannot be empty")
                    team.name = name
                if description is not None:
                    team.description = description
                await session.flush()
                return True

    async def delete_team(self, team_id: int) -> bool:
        """Delete team by id."""
        async with self.async_session() as session:
            async with session.begin():
                team = await session.get(Team, team_id, with_for_update=True)
                if team is None:
                    return False
                await session.delete(team)
                return True

    async def set_team_tracked_sites(self, team_id: int, site_ids: list[int]) -> bool:
        """Replace a team's tracked sites with the provided set."""
        normalised: list[int] = []
        for site_id in site_ids:
            if not isinstance(site_id, int):
                raise ValueError("site_ids must contain integers")
            if site_id not in normalised:
                normalised.append(site_id)
        async with self.async_session() as session:
            async with session.begin():
                team = await session.get(Team, team_id, with_for_update=True)
                if team is None:
                    return False
                team.tracked_site_ids = normalised
                await session.flush()
                return True

    async def add_team_tracked_site(self, team_id: int, site_id: int) -> bool:
        """Append a site to team's tracked list if missing."""
        async with self.async_session() as session:
            async with session.begin():
                team = await session.get(Team, team_id, with_for_update=True)
                if team is None:
                    return False
                tracked = list(team.tracked_site_ids or [])
                if site_id in tracked:
                    return False
                tracked.append(site_id)
                team.tracked_site_ids = tracked
                await session.flush()
                return True

    async def remove_team_tracked_site(self, team_id: int, site_id: int) -> bool:
        """Remove a site from team's tracked list if present."""
        async with self.async_session() as session:
            async with session.begin():
                team = await session.get(Team, team_id, with_for_update=True)
                if team is None:
                    return False
                tracked = list(team.tracked_site_ids or [])
                if site_id not in tracked:
                    return False
                tracked = [sid for sid in tracked if sid != site_id]
                team.tracked_site_ids = tracked
                await session.flush()
                return True

    async def set_team_tg_chat(self, team_id: int, chat_id: int | None) -> bool:
        """Bind or unbind Telegram chat to a team."""
        async with self.async_session() as session:
            async with session.begin():
                team = await session.get(Team, team_id, with_for_update=True)
                if team is None:
                    return False
                team.tg_chat_id = chat_id
                await session.flush()
                return True

    async def get_team_tg_chat(self, team_id: int) -> int | None:
        """Return Telegram chat id for a team, if any."""
        async with self.async_session() as session:
            team = await session.get(Team, team_id)
            return team.tg_chat_id if team else None

    # -------------------------   DASHBOARD/CHECKER   --------------------- #

    async def get_team_ids_by_site(self, site_id: int) -> list[int]:
        """Return ids of teams tracking a given site."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Team.id).where(Team.tracked_site_ids.contains([site_id]))
            )
            return [row[0] for row in result.all()]

    async def get_team_tg_chats_for_site(self, site_id: int) -> list[int]:
        """Return Telegram chats of all teams tracking a given site."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Team.tg_chat_id)
                .where(Team.tracked_site_ids.contains([site_id]))
                .where(Team.tg_chat_id.is_not(None))
            )
            return [int(row[0]) for row in result.all() if row[0] is not None]

    async def get_sites_for_team(self, team_id: int) -> list[Site]:
        """Return Site objects referenced by team's tracked list."""
        async with self.async_session() as session:
            team = await session.get(Team, team_id)
            if team is None or not team.tracked_site_ids:
                return []
            site_ids = list(team.tracked_site_ids)
            result = await session.execute(
                select(Site).where(Site.id.in_(site_ids)).order_by(Site.name, Site.id)
            )
            return list(result.scalars().all())
