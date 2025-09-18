def format_alert(payload: dict) -> str:
    sev = payload.get('severity') or payload.get('level') or 'INFO'
    status = payload.get('status') or payload.get('event_type') or 'EVENT'
    name = payload.get('monitor_name') or payload.get('service') or payload.get('url') or '<service>'
    target = payload.get('target') or payload.get('url') or ''
    reason = payload.get('reason') or payload.get('message') or ''
    inc = payload.get('incident_id') or payload.get('event_id') or ''
    parts = [f"<b>[{sev}] {status}</b> — {name}"]
    if target: parts.append(target)
    if reason: parts.append(reason)
    if inc: parts.append(f"<i>{inc}</i>")
    return '\n'.join(parts)
