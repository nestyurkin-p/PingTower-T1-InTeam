from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from .utils.log import setup_logging

setup_logging()

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from broker.broker import app as faststream_app, llm_exchange  # type: ignore  # noqa: E402
from database import DataBase

from .routes.llm import setup_llm_routes
from .services.antispam import AntiSpamService

logger = logging.getLogger(__name__)

_db_url = os.getenv("DATABASE_URL", "").strip()
if not _db_url:
    raise RuntimeError("DATABASE_URL environment variable is required for dispatcher")

db = DataBase(_db_url)


def _parse_ttl(value: str) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        logger.warning("Invalid GROUPING_WINDOW_GLOBAL_SEC=%s, fallback to 60", value)
        return 60

_antispam_ttl = _parse_ttl(os.getenv("GROUPING_WINDOW_GLOBAL_SEC", "60"))
antispam = AntiSpamService(_antispam_ttl)

setup_llm_routes(faststream_app, llm_exchange, db, antispam)

logger.info("Dispatcher initialized (TTL=%s)", _antispam_ttl)

app = faststream_app

__all__ = ["app", "db", "antispam"]
