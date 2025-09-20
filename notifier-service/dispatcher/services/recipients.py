from __future__ import annotations

import logging
from typing import Optional

from core.config import settings
from database import DataBase

from ..models import DispatchMessage

logger = logging.getLogger(__name__)

_AUTOCREATE = settings.dispatcher.autocreate_sites


async def resolve_site_id(db: DataBase, payload: DispatchMessage) -> Optional[int]:
    """Resolve or create a site id based on the incoming payload."""
    site_id = _extract_int(payload.id)
    if site_id is not None:
        site = await db.get_site_by_id(site_id)
        if site is not None:
            return site.id

    url = payload.url
    if url:
        site = await db.get_site_by_url(url)
        if site is not None:
            return site.id
        if _AUTOCREATE:
            name = payload.name or url
            try:
                return await db.ensure_site(url=url, name=name)
            except Exception as exc:
                logger.exception("Failed to auto-create site %s: %s", url, exc)

    return None


async def telegram_chats_for_site(db: DataBase, site_id: int) -> list[int]:
    """Fetch Telegram chat ids for teams tracking the given site."""
    chats = await db.get_team_tg_chats_for_site(site_id)
    seen: set[int] = set()
    result: list[int] = []
    for chat_id in chats:
        if chat_id not in seen:
            seen.add(chat_id)
            result.append(chat_id)
    return result


async def team_email_groups_for_site(db: DataBase, site_id: int) -> list[tuple[str, list[str]]]:
    """Return list of (team_name, emails) for teams tracking the site."""
    team_ids = await db.get_team_ids_by_site(site_id)
    groups: list[tuple[str, list[str]]] = []
    for team_id in team_ids:
        team = await db.get_team(team_id)
        if not team:
            continue
        raw_list = list(team.email_recipients or [])
        emails = []
        seen: set[str] = set()
        for addr in raw_list:
            if not isinstance(addr, str):
                continue
            normalized = addr.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            emails.append(normalized)
        if emails:
            groups.append((team.name, emails))
    return groups


def _extract_int(value: object) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
