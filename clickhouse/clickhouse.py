from asynch import connect
from asynch.cursors import DictCursor
from core.config import settings
from .models import SiteLog


class Clickhouse:
    def __init__(self):
        self.settings = settings.clickhouse

    async def _get_connection(self):
        dsn = (
            f"clickhouse://{self.settings.user}:{self.settings.password}"
            f"@{self.settings.host}:{self.settings.port}/{self.settings.database}"
        )
        return await connect(dsn)

    async def fetch_old_logs(self, cutoff: str) -> list[SiteLog]:
        """Достать все логи старше cutoff (строка в формате 'YYYY-MM-DD HH:MM:SS')."""
        conn = await self._get_connection()
        try:
            async with conn.cursor(cursor=DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT id, url, name, traffic_light, timestamp, http_status, latency_ms,
                           ping_ms, ssl_days_left, dns_resolved, redirects, errors_last, ping_interval
                    FROM site_logs
                    WHERE timestamp < %(cutoff)s
                    """,
                    {"cutoff": cutoff},
                )
                rows = await cursor.fetchall()
                return [SiteLog(**row) for row in rows]
        finally:
            await conn.close()