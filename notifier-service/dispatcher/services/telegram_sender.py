from __future__ import annotations

import logging
import os
from typing import Final

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

logger = logging.getLogger(__name__)

_token: Final[str] = os.getenv("TG_TOKEN", "").strip()
_bot: Bot | None = None
if _token:
    _bot = Bot(token=_token, default=DefaultBotProperties(parse_mode="HTML"))

_warning_logged = False


async def send_message(chat_id: int, text: str, disable_web_page_preview: bool = True) -> None:
    """Send a Telegram message if a token is configured."""
    global _warning_logged
    if not _token or _bot is None:
        if not _warning_logged:
            logger.warning("Telegram token is not set; skipping all messages")
            _warning_logged = True
        return
    try:
        await _bot.send_message(chat_id, text, disable_web_page_preview=disable_web_page_preview)
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("Failed to send Telegram message to chat %s: %s", chat_id, exc)
