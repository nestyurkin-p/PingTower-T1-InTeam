from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class SiteLog(BaseModel):
    id: int
    url: str
    name: str
    traffic_light: str | None = None
    timestamp: datetime
    http_status: int | None = None
    latency_ms: int | None = None
    ping_ms: float | None = None
    ssl_days_left: int | None = None
    dns_resolved: int
    redirects: int | None = None
    errors_last: int | None = None
    ping_interval: int