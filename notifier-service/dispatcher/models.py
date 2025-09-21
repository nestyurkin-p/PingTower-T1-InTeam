from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class SiteCom(BaseModel):
    model_config = ConfigDict(extra="allow")

    llm: Optional[bool] = None
    tg: Optional[int] = None
    skip_notification: Optional[bool] = None


class LogSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: Optional[datetime | str] = None
    traffic_light: Optional[str] = None
    http_status: Optional[int] = None
    latency_ms: Optional[Union[int, float]] = None
    ping_ms: Optional[Union[int, float]] = None
    ssl_days_left: Optional[int] = None
    dns_resolved: Optional[bool] = None
    redirects: Optional[int] = None
    errors_last: Optional[int] = None


class DispatchMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[int, str]
    url: Optional[str] = None
    name: Optional[str] = None
    com: Optional[SiteCom] = None
    logs: LogSnapshot = Field(default_factory=LogSnapshot)
    explanation: Optional[str] = None
