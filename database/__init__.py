from app.config import db_config
from .database import DataBase

db = DataBase(db_config.url)

__all__ = ["db"]
