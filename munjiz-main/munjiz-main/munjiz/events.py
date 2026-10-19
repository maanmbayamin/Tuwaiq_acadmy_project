"""Outbound events to n8n.

Munjiz posts one JSON event per lifecycle change (ticket_submitted, sub_decided, ticket_completed) to the
n8n webhook. n8n routes each desk's part to that desk's system and sends notifications. Delivery runs in a
background thread with a short timeout and is recorded in the event log; if n8n is down, the app carries on.
"""
import threading

import requests

from . import config
from .db import connect, log

TIMEOUT_S = 4
SYNC = False  # tests deliver inline instead of on a thread


def _post(url: str, body: dict) -> int:
    return requests.post(url, json=body, timeout=TIMEOUT_S).status_code


def _deliver(body: dict):
    url = config.N8N_WEBHOOK_URL
    try:
        status = _post(url, body)
        ok = 200 <= status < 300
        detail = {"event": body["event"], "http_status": status}
    except requests.RequestException as exc:
        ok, detail = False, {"event": body["event"], "error": type(exc).__name__}
    with connect() as conn:
        log(conn, "n8n_sent" if ok else "n8n_failed", config.now().isoformat(), body.get("ticket_id"), body.get("sub_id"),
            **detail)


def emit(event: str, payload: dict, wait: bool = False):
    """Send an event to n8n if the integration is configured. Never raises."""
    if not config.N8N_WEBHOOK_URL:
        return
    body = {"event": event, "source": "munjiz", "sent_at": config.now().isoformat(),
            "api_base": config.PUBLIC_API_URL, **payload}
    if wait or SYNC:
        _deliver(body)
    else:
        threading.Thread(target=_deliver, args=(body,), daemon=True).start()
