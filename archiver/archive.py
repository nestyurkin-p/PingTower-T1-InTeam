from database import db
from clickhouse import ch
from datetime import datetime, timedelta


async def run_archive():
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    old_logs = await ch.fetch_old_logs(cutoff)
    print("Старые логи:", old_logs)
    for log in old_logs:
        await db.add_site_log(**log.dict())
    print(f"Перенесено {len(old_logs)} логов из ClickHouse в PostgreSQL")