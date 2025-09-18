import os
import json
import logging
import psycopg2
import asyncio
from broker import broker, app, pinger_exchange
from pinger_checks import run_checks

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
                SELECT id, url, name, com, last_traffic_light, history
                FROM sites;
            """)
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "url": r[1],
                    "name": r[2],
                    "com": r[3],
                    "last_traffic_light": r[4],
                    "history": r[5] or [],
                }
                for r in rows
            ]


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
                (traffic_light, json.dumps(history), site_id),
            )
            conn.commit()


async def monitor():
    """Основной цикл мониторинга"""
    while True:
        sites = fetch_sites()
        logging.info(f"Загружено {len(sites)} сайтов для проверки")

        for site in sites:
            # берём последние 4 записи из истории
            history = site["history"][-4:] if site["history"] else []

            # делаем проверку
            logs = run_checks(site["url"], history)
            traffic_light = logs["traffic_light"]

            # обновляем историю (не больше 10 записей)
            history.append(logs)
            history = history[-10:]

            # определяем skip_notification
            changed = site["last_traffic_light"] != traffic_light
            skip_notification = not changed

            record = {
                "id": site["id"],
                "url": site["url"],
                "name": site["name"],
                "com": {**site["com"], "skip_notification": skip_notification},
                "logs": logs,
            }

            # сохраняем статус в БД
            update_site_status(site["id"], traffic_light, history)

            # локальный вывод
            print(json.dumps(record, ensure_ascii=False), flush=True)

            # публикация в RabbitMQ (если не skip_notification)
            if not skip_notification:
                try:
                    await broker.publish(
                        record,
                        exchange=pinger_exchange,
                        routing_key="pinger.group",
                    )
                    logging.info(f"[✓] ID={site['id']} отправлен в RMQ")
                except Exception as e:
                    logging.error(f"[!] Ошибка публикации в RMQ для ID={site['id']}: {e}")
            else:
                logging.info(f"[→] Пропуск публикации ID={site['id']} (skip_notification=True)")

        await asyncio.sleep(INTERVAL)


@app.after_startup
async def start_monitor():
    """Запускаем мониторинг после старта FastStream"""
    asyncio.create_task(monitor())


if __name__ == "__main__":
    asyncio.run(app.run())
