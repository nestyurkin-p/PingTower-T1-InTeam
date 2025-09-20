from __future__ import annotations

import logging
import os

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging() -> None:
    """Configure root logger based on LOG_LEVEL env."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)
