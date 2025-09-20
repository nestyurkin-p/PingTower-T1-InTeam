import asyncio
import json
import logging
import sys
from pathlib import Path
from time import strftime

import psycopg2

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR.parent))

from core.config import settings  # noqa: E402
from broker import app, broker, pinger_exchange  # noqa: E402
from pinger_checks import CHECKS as DEFAULT_CHECKS, run_checks  # noqa: E402

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

DATABASE_URL = settings.pinger.input_database_url
INTERVAL = settings.pinger.interval_sec


def fetch_sites():
    """Fetch sites from the monitoring database."""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, url, name, com, last_ok, last_status, last_rtt, skip_notification
                FROM sites;
                """
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "url": r[1],
                    "name": r[2],
                    "com": r[3],
                    "last_ok": r[4],
                    "last_status": r[5],
                    "last_rtt": r[6],
                    "skip_notification": r[7],
                }
                for r in rows
            ]


def update_site_status(site_id, ok, status, rtt, skip_notification):
    """Persist the latest probe status back to the database."""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sites
                SET last_ok=%s,
                    last_status=%s,
                    last_rtt=%s,
                    skip_notification=%s
                WHERE id=%s
                """,
                (ok, status, rtt, skip_notification, site_id),
            )
            conn.commit()


async def monitor():
    """Run monitoring loop publishing updates to RabbitMQ."""
    while True:
        sites = fetch_sites()
        logging.info("Загружено %d сервисов для проверки", len(sites))

        for site in sites:
            errors, metrics = run_checks(site["url"], DEFAULT_CHECKS)
            ok = len(errors) == 0
            status = metrics.get("status")
            rtt = metrics.get("rtt")

            changed = (
                site["last_ok"] != ok
                or site["last_status"] != status
                or site["last_rtt"] != rtt
            )
            skip_notification = not changed

            record = {
                "id": site["id"],
                "url": site["url"],
                "name": site["name"],
                "com": {**site["com"], "skip_notification": skip_notification},
                "logs": {
                    "timestamp": strftime("%Y-%m-%dT%H:%M:%S"),
                    "ok": ok,
                    "errors": errors,
                    "metrics": metrics,
                },
            }

            update_site_status(site["id"], ok, status, rtt, skip_notification)

            print(json.dumps(record, ensure_ascii=False), flush=True)

            if skip_notification:
                logging.info("[→] Пропускаем уведомление для %s (изменений нет)", site["url"])
                continue

            try:
                await broker.publish(
                    record,
                    exchange=pinger_exchange,
                    routing_key=settings.rabbit.pinger_routing_key,
                )
                logging.info("[V] ID=%s отправлено в брокер", site["id"])
            except Exception as e:
                logging.error("[!] Ошибка публикации в RabbitMQ для ID=%s: %s", site["id"], e)

        await asyncio.sleep(INTERVAL)


@app.after_startup
async def start_monitor():
    asyncio.create_task(monitor())


if __name__ == "__main__":
    asyncio.run(app.run())
