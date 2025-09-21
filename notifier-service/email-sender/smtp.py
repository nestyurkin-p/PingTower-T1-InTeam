from __future__ import annotations

import logging
from email.message import EmailMessage
from typing import Sequence

import aiosmtplib

from core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: Sequence[str], subject: str, plain: str, html: str | None = None) -> None:
    """Send an email using global settings configuration."""
    recipients = [addr.strip() for addr in to if isinstance(addr, str) and addr.strip()]
    if not recipients:
        logger.debug("No email recipients provided; skipping send")
        return

    smtp = settings.email
    if not smtp.host:
        logger.debug("SMTP host not configured; skipping email send to %s", recipients)
        return

    message = EmailMessage()
    message["From"] = smtp.from_addr
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(plain)
    if html:
        message.add_alternative(html, subtype="html")

    client = aiosmtplib.SMTP(
        hostname=smtp.host,
        port=smtp.port,
        timeout=smtp.timeout,
        use_tls=smtp.ssl,
        start_tls=False if smtp.ssl else smtp.tls,
    )

    try:
        await client.connect()
        if smtp.user:
            await client.login(smtp.user, smtp.password)
        await client.send_message(message)
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("Failed to send email to %s: %s", recipients, exc)
    finally:
        try:
            await client.quit()
        except Exception:
            pass
