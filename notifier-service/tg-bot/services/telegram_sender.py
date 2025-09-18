import asyncio
import logging
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

logger = logging.getLogger(__name__)
_MAX = 3800  # безопасный лимит под HTML


def _split(text: str, limit: int = _MAX) -> List[str]:
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        cand = (cur + "\n" + line) if cur else line
        if len(cand) <= limit:
            cur = cand
        else:
            if cur:
                parts.append(cur)
            cur = line
    if cur:
        parts.append(cur)

    out: List[str] = []
    for p in parts:
        if len(p) <= limit:
            out.append(p)
        else:
            for i in range(0, len(p), limit):
                out.append(p[i:i + limit])
    return out


async def send_message(
        bot: Bot,
        chat_id: int | str,
        text: str,
        *,
        disable_notification: bool = False,
        protect_content: bool = False,
        max_retries: int = 3,
) -> None:
    chunks = _split(text, _MAX)
    for idx, part in enumerate(chunks, start=1):
        attempt, backoff = 0, 0.6
        while True:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=part,
                    disable_notification=disable_notification,
                    protect_content=protect_content,
                )
                if idx < len(chunks):
                    await asyncio.sleep(0.05)
                break
            except TelegramRetryAfter as e:
                delay = getattr(e, "retry_after", 1.5)
                logger.warning("RetryAfter chat_id=%s sleep %.2fs", chat_id, delay)
                await asyncio.sleep(delay)
            except TelegramForbiddenError:
                logger.warning("Forbidden chat_id=%s; stop", chat_id)
                return
            except TelegramBadRequest as e:
                if "message is too long" in str(e).lower() and len(part) > 1000:
                    extra = _split(part, limit=1500)
                    chunks[idx - 1:idx] = extra
                    break
                logger.exception("BadRequest chat_id=%s: %s", chat_id, e)
                return
            except Exception as e:
                attempt += 1
                if attempt > max_retries:
                    logger.exception("Send failed after retries chat_id=%s: %s", chat_id, e)
                    return
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 5.0)
