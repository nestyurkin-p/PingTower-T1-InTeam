from __future__ import annotations

import logging
import os
from typing import Optional

from database import DataBase

from ..models import DispatchMessage

logger = logging.getLogger(__name__)

_AUTOCREATE = os.getenv("NOTIFIER_AUTOCREATE_SITES", "false").lower() in {"1", "true", "yes", "on"}


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


def _extract_int(value: object) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
