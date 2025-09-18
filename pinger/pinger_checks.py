# -*- coding: utf-8 -*-
import socket, ssl, datetime as dt, requests, re, subprocess
from urllib.parse import urlparse
from time import strftime

DEFAULT_TIMEOUT = 10
DEFAULT_HEADERS = {"User-Agent": "Pinger/2.0 (+healthcheck)"}


def fetch_cert_expiry(hostname: str, port: int = 443, timeout: int = 10) -> int | None:
    """Возвращает количество дней до истечения сертификата, либо None при ошибке"""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        not_after = dt.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        days_left = (not_after - dt.datetime.utcnow()).days
        return days_left
    except Exception:
        return None


def check_ping(hostname: str) -> float | None:
    """Пробуем ping, возвращаем среднее время (мс) или None"""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(DEFAULT_TIMEOUT), hostname],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        match = re.search(r"time[=<](\d+(?:\.\d+)?) ms", result.stdout)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


def traffic_light_from_history(history: list[dict], current: dict) -> str:
    """
    Определяем traffic_light на основе истории и текущей проверки.
    history: список прошлых логов (макс 4 последних)
    current: словарь с метриками текущей проверки
    """
    http_status = current.get("http_status")
    latency_ms = current.get("latency_ms")
    ping_ms = current.get("ping_ms")
    ssl_days_left = current.get("ssl_days_left")
    dns_resolved = current.get("dns_resolved")
    redirects = current.get("redirects")

    # История последних 5 проверок (включая текущую)
    last5 = (history[-4:] if history else []) + [current]
    statuses = [h.get("http_status") for h in last5]

    # --- HTTP ---
    if http_status is None:
        return "red"
    if http_status >= 500:
        if len(last5) >= 2 and all(s and s >= 500 for s in last5[-2:]):
            return "red"
        if sum(1 for s in statuses if s and s >= 500) > 2:
            return "red"
        return "orange"
    if 400 <= http_status < 500:
        return "orange"

    # --- Время ответа ---
    if latency_ms is None or latency_ms > 5000:
        return "red"
    if latency_ms > 2000:
        return "red"
    if latency_ms > 800:
        return "orange"

    # --- Ping ---
    if ping_ms is not None:
        if len(last5) >= 2 and all(h.get("ping_ms", 0) and h["ping_ms"] > 800 for h in last5[-2:]):
            return "red"
        if ping_ms > 800:
            return "red"
        if ping_ms > 150:
            return "orange"

    # --- SSL ---
    if ssl_days_left is not None:
        if ssl_days_left <= 0:
            return "red"
        if ssl_days_left < 7:
            return "orange"

    # --- DNS ---
    if not dns_resolved:
        return "red"

    # --- Редиректы ---
    if redirects is not None and redirects > 5:
        return "orange"

    return "green"


def run_checks(url: str, history: list[dict] | None = None):
    """Главная функция: возвращает logs-словарь"""
    parsed = urlparse(url)
    hostname = parsed.hostname

    http_status = None
    latency_ms = None
    redirects = None
    ssl_days_left = None
    dns_resolved = False
    ping_ms = None

    # DNS
    try:
        socket.gethostbyname(hostname)
        dns_resolved = True
    except Exception:
        dns_resolved = False

    # HTTP
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
        http_status = resp.status_code
        latency_ms = int(resp.elapsed.total_seconds() * 1000)
        redirects = len(resp.history)
    except Exception:
        http_status = None

    # SSL
    if parsed.scheme == "https":
        ssl_days_left = fetch_cert_expiry(hostname)

    # Ping
    ping_ms = check_ping(hostname)

    current_metrics = {
        "http_status": http_status,
        "latency_ms": latency_ms,
        "ping_ms": ping_ms,
        "ssl_days_left": ssl_days_left,
        "dns_resolved": dns_resolved,
        "redirects": redirects,
    }

    traffic = traffic_light_from_history(history or [], current_metrics)

    logs = {
        "timestamp": strftime("%Y-%m-%dT%H:%M:%S"),
        "traffic_light": traffic,
        **current_metrics,
    }
    return logs
