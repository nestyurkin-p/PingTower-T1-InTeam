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

DATABASE_URL = os.getenv("INPUT_DATABASE_URL")


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
                    "ping_interval": r[6] or 30,  # fallback на 30 секунд
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
                (traffic_light, json.dumps(history), site_id),
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
            # берём последние 4 записи из истории
            history = site["history"][-4:] if site["history"] else []

            # делаем проверку
            logs = run_checks(url, history)
            traffic_light = logs["traffic_light"]

            # обновляем историю (не больше 10 записей)
            history.append(logs)
            history = history[-10:]

            # проверка изменений
            changed = site["last_traffic_light"] != traffic_light
            skip_notification = not changed

            record = {
                "id": site_id,
                "url": url,
                "name": name,
                "com": {**site["com"], "skip_notification": skip_notification},
                "logs": logs,
            }

            # сохраняем статус в БД
            update_site_status(site_id, traffic_light, history)

            # локальный вывод
            print(json.dumps(record, ensure_ascii=False), flush=True)

            # публикация в RabbitMQ (если не skip_notification)
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
            pass  # прошло время — продолжаем цикл

    logging.info(f"⏹ Мониторинг остановлен для {name} ({url})")


async def site_manager():
    """Менеджер: следит за актуальным списком сайтов"""
    running_tasks: dict[int, dict] = {}

    while True:
        sites = fetch_sites()

        # добавляем/обновляем сайты
        for site_id, site in sites.items():
            existing = running_tasks.get(site_id)

            if existing:
                # если изменился интервал → перезапуск таски
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
                # новый сайт → запуск
                stop_event = asyncio.Event()
                task = asyncio.create_task(monitor_site(site, stop_event))
                running_tasks[site_id] = {
                    "task": task,
                    "stop_event": stop_event,
                    "ping_interval": site["ping_interval"],
                }

        # удаляем сайты, которых больше нет
        for site_id in list(running_tasks.keys()):
            if site_id not in sites:
                logging.info(f"[-] Сайт {site_id} удалён из БД — останавливаю таску")
                running_tasks[site_id]["stop_event"].set()
                running_tasks[site_id]["task"].cancel()
                del running_tasks[site_id]

        await asyncio.sleep(1)


@app.after_startup
async def start_monitor():
    """Запускаем менеджер"""
    asyncio.create_task(site_manager())


if __name__ == "__main__":
    asyncio.run(app.run())
