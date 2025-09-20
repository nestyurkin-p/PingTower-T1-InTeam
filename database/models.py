from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, Text, func, Float, SmallInteger
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    com: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_traffic_light: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    ping_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=30)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracked_site_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    tg_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    email_recipients: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    webhook_urls: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class SiteLog(Base):
    """табличка для архивации старых логов иZ ClickHouse"""
    __tablename__ = "site_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # UInt64 → BigInteger
    url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    traffic_light: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ping_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ssl_days_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dns_resolved: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # UInt8 → SmallInteger
    redirects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    errors_last: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ping_interval: Mapped[int] = mapped_column(Integer, nullable=False)  # UInt32 → Integer
