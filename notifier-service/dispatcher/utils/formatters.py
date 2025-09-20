from __future__ import annotations

from datetime import datetime

from database.models import Site

from ..models import DispatchMessage

_ICON_MAP = {"green": "✅", "orange": "🟠", "red": "❌"}


def format_telegram(message: DispatchMessage, site: Site) -> str:
    """Compose Telegram message using monitoring snapshot and optional explanation."""
    logs = message.logs

    traffic_light = (logs.traffic_light or "unknown").lower()
    status_icon = _ICON_MAP.get(traffic_light, "❔")

    timestamp_value = logs.timestamp
    if isinstance(timestamp_value, datetime):
        timestamp_text = timestamp_value.isoformat()
    elif isinstance(timestamp_value, str):
        timestamp_text = timestamp_value
    else:
        timestamp_text = "—"

    http_status = _format_value(logs.http_status)
    latency_ms = _format_value(logs.latency_ms)
    ping_ms = _format_value(logs.ping_ms)
    ssl_days_left = _format_value(logs.ssl_days_left)
    dns_resolved = logs.dns_resolved
    if dns_resolved is None:
        dns_text = "—"
    else:
        dns_text = "OK" if dns_resolved else "FAIL"
    redirects = _format_value(logs.redirects)
    errors_last = _format_value(logs.errors_last)

    name = message.name or site.name
    url = message.url or site.url

    stats_text = (
        f"<b>{name}</b> ({url})\n"
        f"{status_icon} Светофор: {traffic_light.upper()}\n\n"
        f"🕒 Время: {timestamp_text}\n"
        f"📡 Код ответа: {http_status}\n"
        f"⚡ Задержка HTTP: {latency_ms} мс\n"
        f"📶 Пинг: {ping_ms} мс\n"
        f"🔐 SSL дней осталось: {ssl_days_left}\n"
        f"🌐 DNS резолвинг: {dns_text}\n"
        f"↪️ Редиректы: {redirects}\n"
        f"❗ Ошибки (последние проверки): {errors_last}\n"
    )

    explanation = (message.explanation or "").strip()
    if explanation:
        stats_text += f"\n💬 <b>Вердикт LLM</b>\n{explanation}"

    return stats_text


def _format_value(value) -> str:
    if value is None:
        return "—"
    return str(value)
