import os
import json
import logging
import psycopg2
import asyncio
from time import strftime
from broker import broker, app, pinger_exchange
from pinger_checks import run_checks, CHECKS as DEFAULT_CHECKS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Конфиги из окружения
DATABASE_URL = os.getenv("INPUT_DATABASE_URL")
INTERVAL = int(os.getenv("INTERVAL", "5"))


def fetch_sites():
    """Загрузка всех сайтов из таблицы"""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, url, name, com, last_ok, last_status, last_rtt, skip_notification
                FROM sites;
            """)
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
    """Обновляем сохранённый статус сайта"""
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
    """Основной цикл мониторинга"""
    while True:
        sites = fetch_sites()
        logging.info(f"Загружено {len(sites)} сайтов для проверки")

        for site in sites:
            errors, metrics = run_checks(site["url"], DEFAULT_CHECKS)
            ok = len(errors) == 0
            status = metrics.get("status")
            rtt = metrics.get("rtt")

            # проверка изменений
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

            # сохраняем статус в БД
            update_site_status(site["id"], ok, status, rtt, skip_notification)

            # локальный вывод
            print(json.dumps(record, ensure_ascii=False), flush=True)

            if skip_notification:
                logging.info(f"[→] Пропущено уведомление для {site['url']} (статус не изменился)")
                continue

            # публикация в RabbitMQ
            try:
                await broker.publish(
                    record,
                    exchange=pinger_exchange,
                    routing_key="pinger.group",
                )
                logging.info(f"[✓] ID={site['id']} отправлен в RMQ")
            except Exception as e:
                logging.error(f"[!] Ошибка публикации в RMQ для ID={site['id']}: {e}")

        await asyncio.sleep(INTERVAL)


@app.after_startup
async def start_monitor():
    """Запускаем мониторинг после старта FastStream"""
    asyncio.create_task(monitor())


if __name__ == "__main__":
    asyncio.run(app.run())
