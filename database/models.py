from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, Text, func
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
    last_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_rtt: Mapped[float | None] = mapped_column(Float, nullable=True)
    skip_notification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    tg_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    login: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SiteLog(Base):
    __tablename__ = "site_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    traffic_light: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ping_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ssl_days_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dns_resolved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    redirects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    errors_last: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ping_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_logs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
