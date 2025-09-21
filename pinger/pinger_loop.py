import asyncio
import json
import logging
import sys
from pathlib import Path
from time import strftime

import psycopg2

try:
    import clickhouse_connect  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    clickhouse_connect = None

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

_ASYNC_MAIN_URL = settings.database.main_url or ""
if _ASYNC_MAIN_URL.startswith("postgresql+asyncpg://"):
    _SYNC_MAIN_URL = "postgresql://" + _ASYNC_MAIN_URL[len("postgresql+asyncpg://"):]
else:
    _SYNC_MAIN_URL = _ASYNC_MAIN_URL

DATABASE_URL = settings.pinger.input_database_url or _SYNC_MAIN_URL or "postgresql://postgres:postgres@postgres:5432/pingtower"
INTERVAL = settings.pinger.interval_sec
NOTIFY_ALWAYS = settings.pinger.notify_always

CLICKHOUSE_HOST = settings.clickhouse.host
CLICKHOUSE_PORT = settings.clickhouse.port
CLICKHOUSE_DB = settings.clickhouse.database
CLICKHOUSE_USER = settings.clickhouse.user
CLICKHOUSE_PASSWORD = settings.clickhouse.password
CLICKHOUSE_TABLE = settings.clickhouse.table
CLICKHOUSE_ENABLED = bool(settings.clickhouse.enabled and clickhouse_connect is not None)
CH_CLIENT = None


def _init_clickhouse() -> None:
    global CH_CLIENT
    if not CLICKHOUSE_ENABLED:
        if CLICKHOUSE_HOST and clickhouse_connect is None:
            logging.warning("clickhouse-connect is not installed; disabling ClickHouse export")
        return

    CH_CLIENT = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DB,
    )
    CH_CLIENT.command(
        f"""
        CREATE TABLE IF NOT EXISTS {CLICKHOUSE_TABLE} (
            id UInt64,
            url String,
            name String,
            timestamp DateTime,
            traffic_light String,
            http_status Nullable(Int32),
            latency_ms Nullable(Int32),
            ping_ms Nullable(Float64),
            ssl_days_left Nullable(Int32),
            dns_resolved UInt8,
            redirects Nullable(Int32),
            errors_last Nullable(Int32),
            ping_interval UInt32
        ) ENGINE = MergeTree()
        ORDER BY (url, timestamp)
        """
    )


def fetch_sites():
    """Fetch sites configuration and status flags."""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, url, name, com, last_traffic_light, history, ping_interval,
                       last_ok, last_status, last_rtt, skip_notification
                FROM sites;
                """
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "url": r[1],
                    "name": r[2],
                    "com": r[3] or {},
                    "last_traffic_light": r[4],
                    "history": r[5] or [],
                    "ping_interval": int(r[6] or 30),
                    "last_ok": r[7],
                    "last_status": r[8],
                    "last_rtt": r[9],
                    "skip_notification": r[10],
                }
                for r in rows
            ]


def update_site_status(site_id, *, ok, status, rtt, skip_notification, traffic_light, history):
    """Persist computed status back to Postgres."""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sites
                SET last_ok=%s,
                    last_status=%s,
                    last_rtt=%s,
                    skip_notification=%s,
                    last_traffic_light=%s,
                    history=%s
                WHERE id=%s
                """,
                (ok, status, rtt, skip_notification, traffic_light, json.dumps(history, ensure_ascii=False), site_id),
            )
            conn.commit()


def write_clickhouse(record: dict, logs: dict, ping_interval: int) -> None:
    if CH_CLIENT is None:
        return
    try:
        CH_CLIENT.insert(
            CLICKHOUSE_TABLE,
            [[
                int(record["id"]),
                record["url"],
                record["name"],
                logs.get("timestamp") or strftime("%Y-%m-%dT%H:%M:%S"),
                logs.get("traffic_light"),
                logs.get("http_status"),
                logs.get("latency_ms"),
                logs.get("ping_ms"),
                logs.get("ssl_days_left"),
                1 if logs.get("dns_resolved") else 0,
                logs.get("redirects"),
                logs.get("errors_last"),
                ping_interval,
            ]],
            column_names=[
                "id",
                "url",
                "name",
                "timestamp",
                "traffic_light",
                "http_status",
                "latency_ms",
                "ping_ms",
                "ssl_days_left",
                "dns_resolved",
                "redirects",
                "errors_last",
                "ping_interval",
            ],
        )
    except Exception as exc:  # pragma: no cover - diagnostics only
        logging.warning("Failed to write ClickHouse row: %s", exc)


async def monitor():
    """Run monitoring loop publishing updates to RabbitMQ."""
    while True:
        sites = fetch_sites()
        logging.info("Загружено %d сервисов для проверки", len(sites))

        for site in sites:
            history = list(site["history"] or [])
            short_history = history[-4:]

            logs = run_checks(site["url"], short_history)
            traffic_light = logs.get("traffic_light")
            http_status = logs.get("http_status")
            latency_ms = logs.get("latency_ms")

            history.append(logs)
            history = history[-10:]

            ok = traffic_light == "green"
            status = http_status
            rtt = latency_ms

            changed = (
                site["last_ok"] != ok
                or site["last_status"] != status
                or site["last_rtt"] != rtt
            )
            skip_notification = False if NOTIFY_ALWAYS else not changed

            com = dict(site["com"] or {})
            com["skip_notification"] = skip_notification

            record = {
                "id": site["id"],
                "url": site["url"],
                "name": site["name"],
                "com": com,
                "logs": logs,
            }

            update_site_status(
                site["id"],
                ok=ok,
                status=status,
                rtt=rtt,
                skip_notification=skip_notification,
                traffic_light=traffic_light,
                history=history,
            )

            print(json.dumps(record, ensure_ascii=False), flush=True)

            if CLICKHOUSE_ENABLED:
                write_clickhouse(record, logs, site["ping_interval"])

            if skip_notification:
                logging.info(
                    "[→] Пропускаем уведомление для %s (изменений нет)",
                    site["url"],
                )
                continue

            try:
                await broker.publish(
                    record,
                    exchange=pinger_exchange,
                    routing_key=settings.rabbit.pinger_routing_key,
                )
                logging.info("[V] ID=%s отправлено в брокер", site["id"])
            except Exception as exc:  # pragma: no cover - diagnostics only
                logging.error("[!] Ошибка публикации в RabbitMQ для ID=%s: %s", site["id"], exc)

        await asyncio.sleep(INTERVAL)


@app.after_startup
async def start_monitor():
    _init_clickhouse()
    asyncio.create_task(monitor())


if __name__ == "__main__":
    asyncio.run(app.run())
