import logging

from core.config import settings


def setup_logging(level: str | None = None) -> None:
    """Configure root logger using provided level or global settings value."""
    level_name = (level or settings.log_level).upper()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level_name, logging.INFO))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)
