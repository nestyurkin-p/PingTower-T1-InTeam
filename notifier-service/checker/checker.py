import asyncio
import json
import logging
from typing import Any, Dict

import aio_pika
from aio_pika import ExchangeType
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

from checker.config import rabbit_cfg, app_cfg, tg_cfg
from database import db  # общий пакет БД из корня проекта

logging.basicConfig(
    level=getattr(logging, app_cfg.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

_MAX_LEN = 3800  # безопасная длина (HTML)


def _split(text: str, limit: int = _MAX_LEN) -> list[str]:
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
    out: list[str] = []
    for p in parts:
        if len(p) <= limit:
            out.append(p)
        else:
            for i in range(0, len(p), limit):
                out.append(p[i:i + limit])
    return out


def format_alert(payload: dict) -> str:
    sev = payload.get("severity") or payload.get("level") or "INFO"
    status = payload.get("status") or payload.get("event_type") or "EVENT"
    name = payload.get("monitor_name") or payload.get("service") or payload.get("url") or "<service>"
    target = payload.get("target") or payload.get("url") or ""
    reason = payload.get("reason") or payload.get("message") or ""
    inc = payload.get("incident_id") or payload.get("event_id") or ""
    parts = [f"<b>[{sev}] {status}</b> — {name}"]
    if target:
        parts.append(target)
    if reason:
        parts.append(reason)
    if inc:
        parts.append(f"<i>{inc}</i>")
    return "\n".join(parts)


async def resolve_service_id(payload: Dict[str, Any]) -> int | None:
    sid = payload.get("service_id")
    if isinstance(sid, int):
        return sid
    url = payload.get("url") or payload.get("target") or (payload.get("metrics") or {}).get("final_url")
    if not url:
        return None
    svc = await db.get_service_by_url(url)
    return svc.service_id if svc else None


async def _send_tg(bot: Bot, chat_id: int, text: str) -> None:
    chunks = _split(text)
    for idx, part in enumerate(chunks, start=1):
        attempt, backoff = 0, 0.6
        while True:
            try:
                await bot.send_message(chat_id, part)
                if idx < len(chunks):
                    await asyncio.sleep(0.05)
                break
            except TelegramRetryAfter as e:
                delay = getattr(e, "retry_after", 1.5)
                log.warning("RetryAfter chat_id=%s sleep %.2fs", chat_id, delay)
                await asyncio.sleep(delay)
            except TelegramForbiddenError:
                log.warning("Forbidden chat_id=%s; skip further", chat_id)
                return
            except TelegramBadRequest as e:
                if "message is too long" in str(e).lower() and len(part) > 1000:
                    # на всякий случай — перестраховка (хотя мы уже делим)
                    extra = _split(part, limit=1500)
                    chunks[idx - 1: idx] = extra
                    break
                log.exception("BadRequest chat_id=%s: %s", chat_id, e)
                return
            except Exception as e:
                attempt += 1
                if attempt > 3:
                    log.exception("TG send failed chat_id=%s after retries: %s", chat_id, e)
                    return
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 5.0)


async def main():
    # Чекер сам отправляет в TG — не трогаем бота.
    bot = Bot(tg_cfg.token, default=DefaultBotProperties(parse_mode="HTML"))

    log.info("Checker connecting to RabbitMQ %s", rabbit_cfg.url)
    conn = await aio_pika.connect_robust(
        rabbit_cfg.url,
        client_properties={"connection_name": "notifier-checker"},
    )
    async with conn:
        ch = await conn.channel()
        await ch.set_qos(prefetch_count=32)

        alert_ex = await ch.declare_exchange(rabbit_cfg.alert_exchange, ExchangeType.TOPIC, durable=True)
        queue = await ch.declare_queue("", exclusive=True, auto_delete=True)
        await queue.bind(alert_ex, routing_key=rabbit_cfg.alert_rk)
        log.info("Consuming from %s rk=%s", rabbit_cfg.alert_exchange, rabbit_cfg.alert_rk)

        async with queue.iterator() as it:
            async for msg in it:
                async with msg.process(requeue=False):
                    try:
                        payload = json.loads(msg.body.decode("utf-8"))
                    except Exception:
                        payload = {"message": msg.body.decode("utf-8", errors="ignore")}

                    sid = await resolve_service_id(payload)
                    if sid is None:
                        log.info("Skip: cannot resolve service_id")
                        continue

                    # ключевая БД-функция: все пользователи, кто следит за service_id (+ их notifications_services)
                    targets = await db.get_users_notifications_for_service(sid)
                    if not targets:
                        log.info("No recipients for service_id=%s", sid)
                        continue

                    text = format_alert(payload)
                    for item in targets:
                        services = item.get("notifications") or {}
                        chat_id = services.get("tg_bot")
                        if chat_id:
                            await _send_tg(bot, int(chat_id), text)
                            log.info("Sent TG to chat_id=%s", chat_id)


if __name__ == "__main__":
    asyncio.run(main())
