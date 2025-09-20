from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import clickhouse_connect
import urllib.parse
import os
from datetime import datetime

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "monitor")

# Инициализация клиента ClickHouse
def get_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username="default",
        password="",
        database=CLICKHOUSE_DB,
    )

app = FastAPI()

# CORS для фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/sites")
def get_sites():
    """Возвращаем список уникальных сайтов"""
    client = get_client()
    rows = client.query("""
        SELECT DISTINCT url, name
        FROM site_logs
        ORDER BY name
    """)
    return [dict(zip(rows.column_names, row)) for row in rows.result_rows]


@app.get("/logs")
def get_logs(url: str = Query(...), limit: int = Query(100, gt=0)):
    """Возвращаем последние логи для конкретного сайта"""
    client = get_client()
    decoded_url = urllib.parse.unquote(url)
    rows = client.query(
        """
        SELECT *
        FROM site_logs
        WHERE url = %(url)s
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        """,
        parameters={"url": decoded_url, "limit": limit},
    )
    return [dict(zip(rows.column_names, row)) for row in rows.result_rows]


# ✅ Универсальная мапа для интервалов
GROUP_BY_INTERVALS = {
    "1s": "INTERVAL 1 SECOND",
    "1m": "INTERVAL 1 MINUTE",
    "10m": "INTERVAL 10 MINUTE",
    "1h": "INTERVAL 1 HOUR",
    "1d": "INTERVAL 1 DAY",
    "1w": "INTERVAL 1 WEEK",
}


@app.get("/logs/aggregated")
def get_logs_aggregated(
    since: str = Query(None, description="Начало интервала (ISO8601)"),
    group_by: str = Query("1m", description="Группировка: 1s, 1m, 10m, 1h, 1d, 1w"),
    window: str = Query("5m", description="Длительность интервала по умолчанию"),
):
    if group_by not in GROUP_BY_INTERVALS:
        return {"error": f"Недопустимый group_by: {group_by}"}

    interval = GROUP_BY_INTERVALS[group_by]
    client = get_client()

    # если since не передан — берём now() - window
    if since is None:
        where_clause = f"timestamp >= now() - INTERVAL {window}"
        params = {}
    else:
        where_clause = "timestamp >= parseDateTimeBestEffort(%(since)s)"
        params = {"since": since}

    rows = client.query(
        f"""
        SELECT
            toStartOfInterval(timestamp, {interval}) AS ts,
            count() AS count,
            avgOrNull(latency_ms) AS latency_avg,
            avgOrNull(ping_ms) AS ping_avg,
            avgOrNull(ssl_days_left) AS ssl_days_left_avg,
            avgOrNull(toInt32(dns_resolved)) * 100 AS dns_success_rate,
            sumIf(1, traffic_light = 'green') AS green,
            sumIf(1, traffic_light = 'orange') AS orange,
            sumIf(1, traffic_light = 'red') AS red
        FROM site_logs
        WHERE {where_clause}
        GROUP BY ts
        ORDER BY ts ASC
        """,
        parameters=params,
    )


    buckets = []
    for row in rows.result_rows:
        ts, count, latency, ping, ssl_days, dns, green, orange, red = row
        buckets.append({
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            "count": count,
            "latency_avg": latency,
            "ping_avg": ping,
            "ssl_days_left_avg": ssl_days,
            "dns_success_rate": dns,
            "traffic_light": {
                "green": green,
                "orange": orange,
                "red": red,
            },
        })

    # Считаем summary
    if buckets:
        total = sum(b["count"] for b in buckets)
        summary = {
            "latency_avg": sum((b["latency_avg"] or 0) * b["count"] for b in buckets) / total,
            "ping_avg": sum((b["ping_avg"] or 0) * b["count"] for b in buckets) / total,
            "ssl_days_left_avg": sum((b["ssl_days_left_avg"] or 0) * b["count"] for b in buckets) / total,
            "dns_success_rate": sum((b["dns_success_rate"] or 0) * b["count"] for b in buckets) / total,
            "traffic_light": {
                "green": sum(b["traffic_light"]["green"] for b in buckets),
                "orange": sum(b["traffic_light"]["orange"] for b in buckets),
                "red": sum(b["traffic_light"]["red"] for b in buckets),
            },
        }
    else:
        summary = {
            "latency_avg": None,
            "ping_avg": None,
            "ssl_days_left_avg": None,
            "dns_success_rate": None,
            "traffic_light": {"green": 0, "orange": 0, "red": 0},
        }

    return {"summary": summary, "buckets": buckets}
