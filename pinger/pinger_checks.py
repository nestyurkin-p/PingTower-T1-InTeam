# -*- coding: utf-8 -*-
import re, json, socket, ssl, datetime as dt
import requests
from urllib.parse import urlparse

CHECKS = {
    "allowed_status": {200},
    "max_latency_ms": 1500,
    "min_content_len": 256,
    "max_redirects": 5,
    "expect_content_type": r"^text/html",
    "require_hsts": True,
    "min_tls_days_left": 7,
    "body_must_contain": [r"<html", r"</html>"],
    "body_must_not_contain": [r"error\s*500", r"exception", r"stacktrace"],
    "json_expect_keys_any": [],
    "json_expect_keys_all": [],
}

DEFAULT_TIMEOUT = 10
DEFAULT_HEADERS = {"User-Agent": "Pinger/1.0 (+healthcheck)"}

class CheckFailure(Exception):
    def __init__(self, code: str, message: str, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

def fail(code, msg, **details):
    return {"code": code, "message": msg, "details": details}

def fetch_cert_expiry(hostname: str, port: int = 443, timeout: int = 10) -> dt.datetime:
    context = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
    return dt.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc)

def flatten_keys(obj, prefix=""):
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            keys.add(full); keys |= flatten_keys(v, full)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5]):
            full = f"{prefix}[{i}]"
            keys.add(full); keys |= flatten_keys(v, full)
    return keys

def run_checks(url: str, checks: dict):
    """
    Возвращает: (errors, metrics)
      errors: list[ {code, message, details} ]
      metrics: dict
    """
    errors = []
    metrics = {
        "final_url": None,
        "scheme": None,
        "status_code": None,
        "latency_ms": None,
        "redirects": None,
        "content_type": None,
        "content_length": None,
        "hsts_present": None,
        "tls_days_left": None,
    }

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    except requests.exceptions.RequestException as e:
        errors.append(fail("REQUEST_ERROR", "Request failed", exception=repr(e)))
        return errors, metrics

    metrics.update({
        "final_url": resp.url,
        "scheme": urlparse(resp.url).scheme,
        "status_code": resp.status_code,
        "latency_ms": int(resp.elapsed.total_seconds() * 1000),
        "redirects": len(resp.history),
        "content_type": resp.headers.get("Content-Type", ""),
        "content_length": len(resp.content or b""),
    })

    if resp.status_code not in checks["allowed_status"]:
        errors.append(fail("HTTP_STATUS",
                           f"Unexpected HTTP status {resp.status_code}",
                           expected=list(checks["allowed_status"]), got=resp.status_code))

    if len(resp.history) > checks["max_redirects"]:
        errors.append(fail("REDIRECTS",
                           "Too many redirects",
                           redirects=len(resp.history), max_redirects=checks["max_redirects"]))

    if metrics["latency_ms"] is not None and metrics["latency_ms"] > checks["max_latency_ms"]:
        errors.append(fail("LATENCY",
                           "Latency too high",
                           latency_ms=metrics["latency_ms"], threshold_ms=checks["max_latency_ms"]))

    pattern = checks.get("expect_content_type")
    if pattern and re.search(pattern, metrics["content_type"] or "", re.I) is None:
        errors.append(fail("CONTENT_TYPE",
                           "Content-Type does not match",
                           content_type=metrics["content_type"], pattern=pattern))

    if metrics["content_length"] is not None and metrics["content_length"] < checks["min_content_len"]:
        errors.append(fail("CONTENT_LENGTH",
                           "Response body too short",
                           length=metrics["content_length"], min_len=checks["min_content_len"]))

    parsed = urlparse(resp.url)
    if parsed.scheme == "https" and checks.get("require_hsts", False):
        hsts = resp.headers.get("Strict-Transport-Security")
        metrics["hsts_present"] = bool(hsts and "max-age" in hsts.lower())
        if not metrics["hsts_present"]:
            errors.append(fail("HSTS_MISSING", "Strict-Transport-Security missing or invalid"))

    try:
        if parsed.scheme == "https":
            host = parsed.hostname
            port = parsed.port or 443
            not_after = fetch_cert_expiry(host, port, timeout=DEFAULT_TIMEOUT)
            days_left = (not_after - dt.datetime.now(dt.timezone.utc)).days
            metrics["tls_days_left"] = days_left
            if days_left < checks["min_tls_days_left"]:
                errors.append(fail("TLS_EXPIRY",
                                   "TLS certificate expires soon",
                                   days_left=days_left, min_days=checks["min_tls_days_left"]))
    except Exception as e:
        errors.append(fail("TLS_CHECK_ERROR", "Failed to check TLS certificate", exception=repr(e)))

    text = ""
    try:
        if (metrics["content_type"] or "").lower().startswith("text") or resp.apparent_encoding:
            resp.encoding = resp.encoding or resp.apparent_encoding or "utf-8"
            text = resp.text
    except Exception:
        pass

    for rx in checks.get("body_must_contain", []):
        if re.search(rx, text, re.I | re.S) is None:
            errors.append(fail("BODY_MISSING", "Required pattern not found", pattern=rx))

    for rx in checks.get("body_must_not_contain", []):
        if re.search(rx, text, re.I | re.S) is not None:
            errors.append(fail("BODY_FORBIDDEN", "Forbidden pattern found", pattern=rx))

    # 9) JSON-ключи
    try:
        if re.search(r"application/(json|.+\+json)", metrics["content_type"] or "", re.I):
            data = resp.json()
            all_keys = flatten_keys(data)
            need_any = set(checks.get("json_expect_keys_any", []))
            need_all = set(checks.get("json_expect_keys_all", []))
            if need_any and not any(k in all_keys for k in need_any):
                errors.append(fail("JSON_KEYS_ANY", "None of the expected JSON keys found",
                                   expected_any=sorted(need_any)))
            if need_all:
                missing = [k for k in need_all if k not in all_keys]
                if missing:
                    errors.append(fail("JSON_KEYS_ALL", "Some required JSON keys are missing",
                                       missing=missing))
    except (ValueError, json.JSONDecodeError):
        errors.append(fail("JSON_PARSE", "Failed to parse JSON"))

    return errors, metrics
