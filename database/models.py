from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notifications_services: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    tracked_services: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer), nullable=True)
    llm_summarization: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class TrackedService(Base):
    __tablename__ = "tracked_services"
    service_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    health_logs: Mapped[list['HealthLog']] = relationship(back_populates='service', cascade='all, delete-orphan', passive_deletes=True)

class HealthLog(Base):
    __tablename__ = "health_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey('tracked_services.service_id', ondelete='CASCADE'), index=True)
    logs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    service: Mapped['TrackedService'] = relationship(back_populates='health_logs')
