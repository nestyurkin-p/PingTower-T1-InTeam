import os
import json
import logging
import psycopg2
import asyncio
import clickhouse_connect
from broker import broker, app, pinger_exchange
from pinger_checks import run_checks
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

DATABASE_URL = os.getenv("INPUT_DATABASE_URL")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "monitor")
NOTIFY_ALWAYS = int(os.getenv("NOTIFY_ALWAYS", "0"))  # 0 = только при изменениях, 1 = всегда

# ClickHouse клиент
ch_client = clickhouse_connect.get_client(
    host=CLICKHOUSE_HOST,
    port=CLICKHOUSE_PORT,
    username="default",
    password=""
)

# создаём таблицу если нет
ch_client.command(f"""
CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.site_logs (
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
""")

def fetch_sites():
    """Загрузка всех сайтов из таблицы"""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, url, name, com, last_traffic_light, history, ping_interval
                FROM sites;
            """)
            rows = cur.fetchall()
            return {
                r[0]: {
                    "id": r[0],
                    "url": r[1],
                    "name": r[2],
                    "com": r[3],
                    "last_traffic_light": r[4],
                    "history": r[5] or [],
                    "ping_interval": r[6] or 30,
                }
                for r in rows
            }

def update_site_status(site_id, traffic_light, history):
    """Обновляем сохранённый traffic_light и историю в sites"""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sites
                SET last_traffic_light=%s,
                    history=%s
                WHERE id=%s
                """,
                (traffic_light, json.dumps(history, ensure_ascii=False), site_id),
            )
            conn.commit()

async def monitor_site(site, stop_event: asyncio.Event):
    """Отдельная таска для одного сайта"""
    site_id = site["id"]
    url = site["url"]
    name = site["name"]
    ping_interval = site["ping_interval"]

    logging.info(f"▶ Запуск мониторинга {name} ({url}), интервал {ping_interval} сек")

    while not stop_event.is_set():
        try:
            history = site["history"][-4:] if site["history"] else []

            logs = run_checks(url, history)
            traffic_light = logs["traffic_light"]

            history.append(logs)
            history = history[-10:]

            changed = site["last_traffic_light"] != traffic_light

            # если NOTIFY_ALWAYS=1 → всегда уведомляем
            if NOTIFY_ALWAYS == 1:
                skip_notification = False
            else:
                skip_notification = not changed

            record = {
                "id": site_id,
                "url": url,
                "name": name,
                "com": {**site["com"], "skip_notification": skip_notification},
                "logs": logs,
            }

            update_site_status(site_id, traffic_light, history)

            # запись в ClickHouse
            ch_client.insert(
                f"{CLICKHOUSE_DB}.site_logs",
                [[
                    site_id,
                    url,
                    name,
                    datetime.strptime(logs["timestamp"], "%Y-%m-%dT%H:%M:%S"),
                    traffic_light,
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
                    "id", "url", "name", "timestamp", "traffic_light",
                    "http_status", "latency_ms", "ping_ms", "ssl_days_left",
                    "dns_resolved", "redirects", "errors_last", "ping_interval"
                ]
            )

            print(json.dumps(record, ensure_ascii=False), flush=True)

            if not skip_notification:
                await broker.publish(
                    record,
                    exchange=pinger_exchange,
                    routing_key="pinger.group",
                )
                logging.info(f"[✓] ID={site_id} отправлен в RMQ")
            else:
                logging.info(f"[→] Пропуск публикации ID={site_id} (skip_notification=True)")

        except Exception as e:
            logging.error(f"[!] Ошибка мониторинга сайта {name}: {e}")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=ping_interval)
        except asyncio.TimeoutError:
            pass

    logging.info(f"⏹ Мониторинг остановлен для {name} ({url})")

async def site_manager():
    """Менеджер: следит за актуальным списком сайтов"""
    running_tasks: dict[int, dict] = {}

    while True:
        sites = fetch_sites()

        for site_id, site in sites.items():
            existing = running_tasks.get(site_id)

            if existing:
                if existing["ping_interval"] != site["ping_interval"]:
                    logging.info(f"[↻] Перезапуск сайта {site['name']} (новый интервал)")
                    existing["stop_event"].set()
                    existing["task"].cancel()

                    stop_event = asyncio.Event()
                    task = asyncio.create_task(monitor_site(site, stop_event))
                    running_tasks[site_id] = {
                        "task": task,
                        "stop_event": stop_event,
                        "ping_interval": site["ping_interval"],
                    }
            else:
                stop_event = asyncio.Event()
                task = asyncio.create_task(monitor_site(site, stop_event))
                running_tasks[site_id] = {
                    "task": task,
                    "stop_event": stop_event,
                    "ping_interval": site["ping_interval"],
                }

        for site_id in list(running_tasks.keys()):
            if site_id not in sites:
                logging.info(f"[-] Сайт {site_id} удалён из БД — останавливаю таску")
                running_tasks[site_id]["stop_event"].set()
                running_tasks[site_id]["task"].cancel()
                del running_tasks[site_id]

        await asyncio.sleep(1)

@app.after_startup
async def start_monitor():
    asyncio.create_task(site_manager())

if __name__ == "__main__":
    asyncio.run(app.run())
