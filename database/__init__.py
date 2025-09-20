from __future__ import annotations

from core.config import settings

from .database import DataBase

_database_url = settings.database.main_url

db: DataBase | None = DataBase(_database_url) if _database_url else None

__all__ = ["DataBase", "db"]
