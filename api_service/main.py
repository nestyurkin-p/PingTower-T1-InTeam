from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import clickhouse_connect
import urllib.parse
import os
import psycopg2
import json

# ----------------- ClickHouse -----------------
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "monitor")

def get_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username="default",
        password="",
        database=CLICKHOUSE_DB,
    )

# ----------------- Postgres -----------------
POSTGRES_URL = os.getenv(
    "INPUT_DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/monitor"
)

def get_pg():
    return psycopg2.connect(POSTGRES_URL)

# ----------------- FastAPI -----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Models -----------------
class SiteIn(BaseModel):
    url: str
    name: str
    ping_interval: int = 30

class SiteParams(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None
    ping_interval: Optional[int] = None
    last_traffic_light: Optional[str] = None
    com: Optional[Dict[str, Any]] = None
    history: Optional[List[Any]] = None

# ----------------- Sites -----------------
@app.get("/sites")
def get_sites():
    conn = get_pg()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, url, name, last_traffic_light, ping_interval, created_at, com, history
        FROM sites ORDER BY id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": row[0],
            "url": row[1],
            "name": row[2],
            "last_traffic_light": row[3],
            "ping_interval": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "com": row[6],
            "history": row[7],
        }
        for row in rows
    ]

@app.post("/sites")
def create_site(site: SiteIn):
    conn = get_pg()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sites (url, name, ping_interval)
        VALUES (%s, %s, %s)
        ON CONFLICT (url) DO UPDATE
            SET name = EXCLUDED.name,
                ping_interval = EXCLUDED.ping_interval
        RETURNING id, url, name, ping_interval
        """,
        (site.url, site.name, site.ping_interval),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return dict(id=row[0], url=row[1], name=row[2], ping_interval=row[3])

@app.put("/sites/{site_id}")
def update_site(site_id: int, site: SiteIn):
    conn = get_pg()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sites
        SET url = %s, name = %s, ping_interval = %s
        WHERE id = %s
        RETURNING id, url, name, ping_interval
        """,
        (site.url, site.name, site.ping_interval, site_id),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Site not found")
    return dict(id=row[0], url=row[1], name=row[2], ping_interval=row[3])

@app.patch("/sites/{site_id}/params")
def patch_site_params(site_id: int, params: SiteParams = Body(...)):
    conn = get_pg()
    cur = conn.cursor()

    updates = []
    values = []

    if params.url is not None:
        updates.append("url = %s")
        values.append(params.url)
    if params.name is not None:
        updates.append("name = %s")
        values.append(params.name)
    if params.ping_interval is not None:
        updates.append("ping_interval = %s")
        values.append(params.ping_interval)
    if params.last_traffic_light is not None:
        updates.append("last_traffic_light = %s")
        values.append(params.last_traffic_light)
    if params.com is not None:
        updates.append("com = %s")
        values.append(json.dumps(params.com))
    if params.history is not None:
        updates.append("history = %s")
        values.append(json.dumps(params.history))

    if not updates:
        raise HTTPException(status_code=400, detail="No parameters to update")

    values.append(site_id)

    query = f"""
        UPDATE sites
        SET {", ".join(updates)}
        WHERE id = %s
        RETURNING id, url, name, ping_interval, last_traffic_light, com, history
    """
    cur.execute(query, tuple(values))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Site not found")

    return {
        "id": row[0],
        "url": row[1],
        "name": row[2],
        "ping_interval": row[3],
        "last_traffic_light": row[4],
        "com": row[5],
        "history": row[6],
    }

@app.delete("/sites/{site_id}")
def delete_site(site_id: int):
    conn = get_pg()
    cur = conn.cursor()
    cur.execute("DELETE FROM sites WHERE id = %s RETURNING id", (site_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"ok": True}

# ----------------- Logs -----------------
@app.get("/logs")
def get_logs(
    url: str | None = Query(None),
    limit: int = Query(100, gt=0),
    since: str | None = Query(None),
):
    client = get_client()
    where_clauses = []
    params = {"limit": limit}

    if url:
        where_clauses.append("url = %(url)s")
        params["url"] = urllib.parse.unquote(url)
    if since:
        where_clauses.append("timestamp >= parseDateTimeBestEffort(%(since)s)")
        params["since"] = since

    where_clause = " AND ".join(where_clauses) or "1=1"

    rows = client.query(
        f"""
        SELECT *
        FROM site_logs
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        """,
        parameters=params,
    )
    return [dict(zip(rows.column_names, row)) for row in rows.result_rows]

WINDOW_INTERVALS = {
    "1s": "1 SECOND",
    "1m": "1 MINUTE",
    "10m": "10 MINUTE",
    "1h": "1 HOUR",
    "1d": "1 DAY",
    "1w": "1 WEEK",
}

@app.get("/logs/aggregated")
def get_logs_raw(group_by: str = Query("1m")):
    if group_by not in WINDOW_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Недопустимый интервал: {group_by}")

    interval = WINDOW_INTERVALS[group_by]
    client = get_client()
    rows = client.query(
        f"""
        SELECT *
        FROM site_logs
        WHERE timestamp >= now() - INTERVAL {interval}
        ORDER BY timestamp ASC
        """
    )
    return [dict(zip(rows.column_names, row)) for row in rows.result_rows]
