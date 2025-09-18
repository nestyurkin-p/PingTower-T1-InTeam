from __future__ import annotations
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    password: Mapped[Optional[str]] = mapped_column(String)
    # список каналов нотификаций (например, {"tg": true, "sms": false})
    notifications_services: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    # список id'ов трекаемых сервисов (быстрый способ связать без join'а)
    tracked_services: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer))
    # включена ли сводка/переформулировка LLM для пользователя
    llm_summarization: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class TrackedService(Base):
    __tablename__ = "tracked_services"

    service_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    health_logs: Mapped[list["HealthLog"]] = relationship(
        back_populates="service", cascade="all, delete-orphan", passive_deletes=True
    )  # backref на логи


class HealthLog(Base):
    __tablename__ = "health_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tracked_services.service_id", ondelete="CASCADE"), nullable=False, index=True
    )
    logs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # сырые логи (pinger / llm и т.п.)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    service: Mapped["TrackedService"] = relationship(back_populates="health_logs")
