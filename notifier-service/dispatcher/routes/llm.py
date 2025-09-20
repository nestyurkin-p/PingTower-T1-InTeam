from __future__ import annotations

import asyncio
import logging
from typing import Any

from faststream.rabbit import RabbitQueue
from pydantic import ValidationError

from core.config import settings
from database import DataBase

from smtp import send_email

from ..models import DispatchMessage
from ..services.antispam import AntiSpamService
from ..services import telegram_sender
from ..services.recipients import (
    resolve_site_id,
    telegram_chats_for_site,
    team_email_groups_for_site,
)
from ..utils.formatters import (
    format_email_bodies,
    format_email_subject,
    format_telegram,
)

logger = logging.getLogger(__name__)


def setup_llm_routes(app, exchange, db: DataBase, antispam: AntiSpamService) -> None:
    """Register FastStream subscriber for LLM verdict events."""
    queue = RabbitQueue(
        "llm-to-dispatcher-queue",
        durable=True,
        routing_key=settings.rabbit.llm_routing_key,
    )

    @app.subscriber(queue, exchange)
    async def handle_llm_event(payload: dict[str, Any]) -> None:  # type: ignore[override]
        try:
            message = DispatchMessage.model_validate(payload)
        except ValidationError as exc:
            logger.warning("Invalid LLM payload: %s", exc)
            return

        if message.com and message.com.skip_notification:
            logger.info("Skip notification for site %s due to skip flag", message.id)
            return

        site_id = await resolve_site_id(db, message)
        if site_id is None:
            logger.info("Skip LLM event without known site (id=%s, url=%s)", message.id, message.url)
            return

        incident_key = _incident_key(message)
        if not await antispam.should_send(site_id, incident_key):
            logger.debug("Duplicate LLM event suppressed for site %s (key=%s)", site_id, incident_key)
            return

        chats = await telegram_chats_for_site(db, site_id)
        extra_chat = _extract_extra_chat(message)
        if extra_chat is not None and extra_chat not in chats:
            chats.append(extra_chat)

        site = await db.get_site_by_id(site_id)
        if site is None:
            logger.warning("Site %s not found during dispatch", site_id)
            return

        text = format_telegram(message, site)
        for chat_id in chats:
            await telegram_sender.send_message(chat_id, text)

        email_groups = await team_email_groups_for_site(db, site_id)
        if email_groups:
            subject = format_email_subject(message, site)
            plain_body, html_body = format_email_bodies(message, site)
            tasks = [
                send_email(addresses, subject, plain_body, html_body)
                for _, addresses in email_groups
            ]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for index, result in enumerate(results):
                    if isinstance(result, Exception):
                        team_name, addresses = email_groups[index]
                        logger.exception(
                            "Failed to send email to team %s (%s): %s",
                            team_name,
                            addresses,
                            result,
                        )
        else:
            logger.debug("No email recipients for site %s", site_id)

        await antispam.mark_sent(site_id, incident_key)


def _incident_key(message: DispatchMessage) -> str:
    logs = message.logs
    traffic = (logs.traffic_light or "unknown").upper()
    http_status = logs.http_status if logs.http_status is not None else "-"
    errors_last = logs.errors_last if logs.errors_last is not None else "-"
    return f"{traffic}|{http_status}|{errors_last}"


def _extract_extra_chat(message: DispatchMessage) -> int | None:
    if not message.com or message.com.tg is None:
        return None
    try:
        return int(message.com.tg)
    except (TypeError, ValueError):
        logger.warning("Invalid Telegram chat id in payload: %s", message.com.tg)
        return None
