from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import cast

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent
EMAIL_SENDER_PATH = BASE_DIR / "email-sender"

for candidate in (ROOT_DIR, BASE_DIR, EMAIL_SENDER_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from core.config import settings  # noqa: E402
from dispatcher.utils.log import setup_logging  # noqa: E402

setup_logging()

from broker.broker import app as faststream_app, llm_exchange  # type: ignore  # noqa: E402
from database import DataBase, db as shared_db  # noqa: E402

from dispatcher.routes.llm import setup_llm_routes  # noqa: E402
from dispatcher.services.antispam import AntiSpamService  # noqa: E402

logger = logging.getLogger(__name__)

if shared_db is None:
    raise RuntimeError("DATABASE_URL must be configured in the global settings")

db = cast(DataBase, shared_db)

antispam = AntiSpamService(settings.dispatcher.grouping_window_sec)

setup_llm_routes(faststream_app, llm_exchange, db, antispam)

logger.info("Dispatcher initialized (TTL=%s)", settings.dispatcher.grouping_window_sec)

app = faststream_app

__all__ = ["app", "db", "antispam"]
