from __future__ import annotations

import html
from datetime import datetime

from database.models import Site

from ..models import DispatchMessage

_ICON_MAP = {"green": "✅", "orange": "🟠", "red": "❌"}


def format_telegram(message: DispatchMessage, site: Site) -> str:
    """Compose Telegram message using monitoring snapshot and optional explanation."""
    ctx = _build_context(message, site)
    stats_text = (
        f"<b>{ctx['name']}</b> ({ctx['url']})\n"
        f"{ctx['icon']} Светофор: {ctx['traffic_light']}\n\n"
        f"🕒 Время: {ctx['timestamp']}\n"
        f"📡 Код ответа: {ctx['http_status']}\n"
        f"⚡ Задержка HTTP: {ctx['latency_ms']} мс\n"
        f"📶 Пинг: {ctx['ping_ms']} мс\n"
        f"🔐 SSL дней осталось: {ctx['ssl_days_left']}\n"
        f"🌐 DNS резолвинг: {ctx['dns_resolved']}\n"
        f"↪️ Редиректы: {ctx['redirects']}\n"
        f"❗ Ошибки (последние проверки): {ctx['errors_last']}\n"
    )

    if ctx["explanation"]:
        stats_text += f"\n💬 <b>Вердикт LLM</b>\n{ctx['explanation']}"

    return stats_text


def format_email_subject(message: DispatchMessage, site: Site) -> str:
    ctx = _build_context(message, site)
    return f"[{ctx['traffic_light']}] {ctx['name']} — статус обновлён"


def format_email_bodies(message: DispatchMessage, site: Site) -> tuple[str, str]:
    ctx = _build_context(message, site)

    plain_lines = [
        f"{ctx['name']} ({ctx['url']})",
        f"Светофор: {ctx['traffic_light']}",
        "",
        f"Время: {ctx['timestamp']}",
        f"Код ответа: {ctx['http_status']}",
        f"Задержка HTTP: {ctx['latency_ms']} мс",
        f"Пинг: {ctx['ping_ms']} мс",
        f"SSL дней осталось: {ctx['ssl_days_left']}",
        f"DNS резолвинг: {ctx['dns_resolved']}",
        f"Редиректы: {ctx['redirects']}",
        f"Ошибки (последние проверки): {ctx['errors_last']}",
    ]

    if ctx["explanation"]:
        plain_lines.extend(["", "Вердикт LLM:", ctx["explanation_plain"]])

    plain_text = "\n".join(plain_lines)

    html_lines = [
        "<html><body>",
        f"<h3>{html.escape(ctx['name'])} ({html.escape(ctx['url'])})</h3>",
        f"<p><strong>Светофор:</strong> {html.escape(ctx['traffic_light'])}</p>",
        "<table style='border-collapse: collapse;'>",
        _html_row("Время", ctx['timestamp']),
        _html_row("Код ответа", ctx['http_status']),
        _html_row("Задержка HTTP", f"{ctx['latency_ms']} мс"),
        _html_row("Пинг", f"{ctx['ping_ms']} мс"),
        _html_row("SSL дней осталось", ctx['ssl_days_left']),
        _html_row("DNS резолвинг", ctx['dns_resolved']),
        _html_row("Редиректы", ctx['redirects']),
        _html_row("Ошибки (последние проверки)", ctx['errors_last']),
        "</table>",
    ]

    if ctx["explanation"]:
        html_lines.append("<p><strong>Вердикт LLM:</strong><br>" + html.escape(ctx["explanation"]) + "</p>")

    html_lines.append("</body></html>")
    html_text = "".join(html_lines)

    return plain_text, html_text


def _build_context(message: DispatchMessage, site: Site) -> dict[str, str]:
    logs = message.logs

    traffic_light = (logs.traffic_light or "unknown").lower()
    icon = _ICON_MAP.get(traffic_light, "❔")

    timestamp_value = logs.timestamp
    if isinstance(timestamp_value, datetime):
        timestamp_text = timestamp_value.isoformat()
    elif isinstance(timestamp_value, str):
        timestamp_text = timestamp_value
    else:
        timestamp_text = "—"

    def _fmt(value) -> str:
        return "—" if value is None else str(value)

    dns_resolved = logs.dns_resolved
    dns_text = "—" if dns_resolved is None else ("OK" if dns_resolved else "FAIL")

    explanation = (message.explanation or "").strip()

    return {
        "name": message.name or site.name,
        "url": message.url or site.url,
        "traffic_light": traffic_light.upper(),
        "icon": icon,
        "timestamp": timestamp_text,
        "http_status": _fmt(logs.http_status),
        "latency_ms": _fmt(logs.latency_ms),
        "ping_ms": _fmt(logs.ping_ms),
        "ssl_days_left": _fmt(logs.ssl_days_left),
        "dns_resolved": dns_text,
        "redirects": _fmt(logs.redirects),
        "errors_last": _fmt(logs.errors_last),
        "explanation": explanation,
        "explanation_plain": explanation,
    }


def _html_row(label: str, value: str) -> str:
    return (
        "<tr>"
        f"<td style='padding:4px 8px;border:1px solid #ddd;'><strong>{html.escape(label)}</strong></td>"
        f"<td style='padding:4px 8px;border:1px solid #ddd;'>{html.escape(str(value))}</td>"
        "</tr>"
    )
