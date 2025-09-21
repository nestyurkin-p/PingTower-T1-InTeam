from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Iterable, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import settings  # noqa: E402
from database import DataBase  # noqa: E402
from database.models import Team  # noqa: E402

DEMO_SITES = [
    {
        "slug": "google",
        "url": "https://www.google.com",
        "name": "Google",
        "com": {"category": "demo"},
        "ping_interval": 30,
    },
]

DEMO_TEAMS = [
    {
        "name": "SRE",
        "description": "Site Reliability team",
        "emails": ["sre@example.com"],
        "webhooks": [],
        "sites": ["google"],
    },
    {
        "name": "QA",
        "description": "Quality Assurance team",
        "emails": ["qa@example.com", "qa-lead@example.com"],
        "webhooks": [],
        "sites": [],
    },
]


async def _update_team_contacts(
    database: DataBase,
    team_id: int,
    *,
    emails: Sequence[str] | None,
    webhooks: Sequence[str] | None,
) -> None:
    if emails is None and webhooks is None:
        return
    async with database.async_session() as session:
        async with session.begin():
            team = await session.get(Team, team_id, with_for_update=True)
            if team is None:
                return
            if emails is not None:
                team.email_recipients = list(_deduplicate(emails))
            if webhooks is not None:
                team.webhook_urls = list(_deduplicate(webhooks))
            await session.flush()


def _deduplicate(items: Iterable[str]) -> Iterable[str]:
    seen: set[str] = set()
    for item in items:
        if not item:
            continue
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        yield normalized


async def seed_demo_data() -> None:
    if not settings.database.main_url:
        raise RuntimeError("DATABASE_URL is not configured")

    db = DataBase(settings.database.main_url)
    await db.create_tables()

    site_ids: dict[str, int] = {}
    for site in DEMO_SITES:
        site_id = await db.ensure_site(
            url=site["url"],
            name=site["name"],
            com=site.get("com"),
            ping_interval=site.get("ping_interval"),
        )
        site_ids[site["slug"]] = site_id

    for team in DEMO_TEAMS:
        existing = await db.get_team_by_name(team["name"])
        if existing:
            team_id = existing.id
            if team.get("description") and existing.description != team["description"]:
                await db.update_team(team_id, description=team["description"])
        else:
            team_id = await db.create_team(team["name"], team.get("description"))

        await _update_team_contacts(
            db,
            team_id,
            emails=team.get("emails"),
            webhooks=team.get("webhooks"),
        )

        tracked_slugs = team.get("sites", [])
        tracked_ids = [site_ids[slug] for slug in tracked_slugs if slug in site_ids]
        if tracked_ids:
            await db.set_team_tracked_sites(team_id, tracked_ids)

    print("Seeded demo data:")
    print(f"  sites: {len(site_ids)}")
    print(f"  teams: {len(DEMO_TEAMS)}")


def main() -> None:
    asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()
