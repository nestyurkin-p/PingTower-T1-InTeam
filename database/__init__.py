from __future__ import annotations

import os

from .database import DataBase

_db_url = os.getenv("DATABASE_URL")
db: DataBase | None = DataBase(_db_url) if _db_url and _db_url.strip() else None

__all__ = ["DataBase", "db"]
