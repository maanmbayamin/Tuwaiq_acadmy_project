"""Munjiz ↔ n8n contract: events out, desk receipts and decisions back in through the API."""
from datetime import datetime

import pytest
from starlette.testclient import TestClient

from munjiz.config import TZ
from tests.test_scenario_a import EN, converse

NOW = datetime(2030, 11, 17, 14, 0, tzinfo=TZ)
TOKEN = "test-token"


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    from munjiz import config, events
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "N8N_WEBHOOK_URL", "http://n8n.test/webhook/munjiz-events")
    monkeypatch.setattr(config, "API_TOKEN", TOKEN)
    monkeypatch.setattr(events, "SYNC", True)
    sent = []
    monkeypatch.setattr(events, "_post", lambda url, body: sent.append(body) or 200)
    return sent


@pytest.fixture
def ticket_id():
    from munjiz import tickets
    conv, (_, second) = converse(EN)
    return tickets.submit(second, "France Pavilion", "Pavilion operations lead", conv, now=NOW)


@pytest.fixture
def api():
    from munjiz.api import app
    return TestClient(app)


def test_submit_sends_one_event_with_every_desk_part(setup, ticket_id):
    (event,) = setup
    assert event["event"] == "ticket_submitted" and event["ticket_id"] == ticket_id
    parts = {p["desk"]: p for p in event["sub_requests"]}
    assert set(parts) == {"logistics", "security", "facilities"}
    assert "Logistics Gate L2" in parts["logistics"]["summary"] and "**" not in parts["logistics"]["summary"]
    assert parts["security"]["decision_url"].endswith(f"/api/subrequests/SEC-{ticket_id[4:]}/decision")


def test_delivery_is_logged_and_failure_does_not_break_submit(monkeypatch, ticket_id):
    from munjiz import events, tickets
    assert "n8n_sent" in [e["type"] for e in tickets.get_ticket(ticket_id)["events"]]

    def down(url, body):
        raise events.requests.ConnectionError("n8n is down")
    monkeypatch.setattr(events, "_post", down)
    conv, (_, second) = converse(EN)
    tid = tickets.submit(second, "Oman Pavilion", "Pavilion director", conv, now=NOW)
    assert "n8n_failed" in [e["type"] for e in tickets.get_ticket(tid)["events"]]


def test_desk_system_receipt_through_api(api, ticket_id):
    sid = f"LOG-{ticket_id[4:]}"
    assert api.post("/mock/desks/logistics/inbox", json={"sub_id": sid}).status_code == 401
    r = api.post("/mock/desks/logistics/inbox", json={"sub_id": sid, "ticket_id": ticket_id},
                 headers={"X-Munjiz-Token": TOKEN})
    assert r.status_code == 200 and r.json()["desk_ref"] == f"GATE-{ticket_id[4:]}"
    assert api.post("/mock/desks/security/inbox", json={"sub_id": sid}, headers={"X-Munjiz-Token": TOKEN}).status_code == 404


def test_decisions_through_api_close_ticket_and_notify(setup, api, ticket_id):
    headers = {"X-Munjiz-Token": TOKEN}
    for prefix in ("LOG", "SEC", "FAC"):
        r = api.post(f"/api/subrequests/{prefix}-{ticket_id[4:]}/decision",
                     json={"approve": True, "staff": f"{prefix.lower()}.officer"}, headers=headers)
        assert r.status_code == 200
    assert r.json()["ticket_status"] == "completed"
    assert [e["event"] for e in setup] == ["ticket_submitted", "sub_decided", "sub_decided", "sub_decided",
                                           "ticket_completed"]
    again = api.post(f"/api/subrequests/LOG-{ticket_id[4:]}/decision", json={"approve": True, "staff": "x"},
                     headers=headers)
    assert again.status_code == 409


def test_watchdog_lists_parts_waiting_too_long(api):
    from datetime import timedelta
    from munjiz import config, tickets
    conv, (_, second) = converse(EN)
    tickets.submit(second, "Bahrain Pavilion", "Pavilion director", conv, now=config.now() - timedelta(minutes=40))
    overdue = api.get("/api/subrequests/pending", params={"older_than_minutes": 30}).json()
    assert overdue["count"] == 3 and all(i["waiting_minutes"] >= 40 for i in overdue["items"])
    assert api.get("/api/subrequests/pending", params={"older_than_minutes": 60}).json()["count"] == 0
