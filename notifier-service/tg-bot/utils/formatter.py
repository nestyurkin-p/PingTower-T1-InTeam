from typing import Dict, Any


def format_alert(payload: Dict[str, Any]) -> str:
    sev = payload.get("severity") or payload.get("level") or "INFO"
    status = payload.get("status") or payload.get("event_type") or ""
    name = payload.get("monitor_name") or payload.get("monitor_id") or payload.get("service") or "Service"
    target = payload.get("target") or payload.get("url") or payload.get("host") or ""
    reason = payload.get("reason") or payload.get("message") or ""
    incident_id = payload.get("incident_id") or payload.get("event_id") or ""

    lines = [f"<b>[{sev}] {name} — {status}</b>"]
    if target:
        lines.append(str(target))
    if reason:
        lines.append(str(reason))
    if incident_id:
        lines.append(f"incident_id: <code>{incident_id}</code>")

    return "\n".join(lines)
