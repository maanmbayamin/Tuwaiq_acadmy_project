"""Role separation, rejection path with the participant fix loop, cross-desk conflicts, SLA, organiser rules."""
from datetime import datetime, timedelta

import pytest
from starlette.testclient import TestClient

from munjiz.config import TZ
from tests.test_scenario_a import EN, NOW, converse

TOKEN = "test-token"
CONFLICT_DEMO = ("Our truck brings LED screens the day after tomorrow at 2 am, plate ABC 1234. Two workers come with it: "
                 "Ahmed Ali, ID 1023456789 and John Smith, passport P1234567. The screens need 30 kW of power.")


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    from munjiz import config, rules
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "N8N_WEBHOOK_URL", "")
    monkeypatch.setattr(config, "API_TOKEN", TOKEN)
    rules.clear_cache()
    yield
    rules.clear_cache()


def submitted_ticket():
    from munjiz import tickets
    conv, (_, second) = converse(EN)
    return tickets.submit(second, "France Pavilion", "Demo", conv, now=NOW), conv


# --- Role separation -----------------------------------------------------------------------------
def test_pavilion_code_signs_in_participant_and_wrong_code_fails():
    from munjiz import users
    u = users.sign_in_with_pavilion_code("fra-2030")
    assert u["role"] == "participant" and u["pavilion"] == "France Pavilion"
    assert users.sign_in_with_pavilion_code("FRA-2031") is None
    assert users.sign_in("security.officer", "0000") is None


def test_each_role_sees_only_its_pages_and_desks():
    from munjiz import users
    officer = users.sign_in("security.officer", users.STAFF_PIN)
    participant = users.sign_in_with_pavilion_code("OMN-2030")
    organiser = users.sign_in("expo.organiser", users.STAFF_PIN)
    assert users.visible_desks(officer) == ["security"]
    assert users.can_open(officer, "staff") and not users.can_open(officer, "dashboard")
    assert users.can_open(participant, "participant") and not users.can_open(participant, "staff")
    assert users.visible_desks(participant) == []
    assert users.can_open(organiser, "rules") and users.can_open(organiser, "dashboard")


def test_participant_list_is_filtered_by_pavilion():
    from munjiz import tickets
    submitted_ticket()
    assert len(tickets.list_tickets("France Pavilion")) == 1
    assert tickets.list_tickets("Oman Pavilion") == []


# --- Rejection path ------------------------------------------------------------------------------
def test_request_change_on_one_part_gives_partially_approved_and_fix_resubmits_only_that_part():
    from munjiz import tickets
    from munjiz.agent import run_fix
    tid, conv = submitted_ticket()
    log_id, sec_id, fac_id = (s["id"] for s in tickets.get_ticket(tid)["subs"])
    tickets.decide(log_id, True, "logistics.officer", now=NOW)
    ticket = tickets.decide(sec_id, staff="security.officer", reason="John Smith's passport could not be verified",
                            outcome="request_change", now=NOW)
    assert ticket["status"] == "partially_approved"

    fix = "John Smith's passport is P7654321"
    result = run_fix(ticket, [sec_id], [fix], conv + [{"role": "user", "content": fix}], NOW, backend="local")
    assert result.ready and list(result.checks) == ["security"]
    workers = result.checks["security"].payload["workers"]
    assert [(w["full_name"], w["id_number"]) for w in workers] == [("Ahmed Ali", "1023456789"), ("John Smith", "P7654321")]

    ticket = tickets.resubmit(sec_id, result.checks["security"], now=NOW)
    subs = {s["id"]: s for s in ticket["subs"]}
    assert subs[log_id]["status"] == "approved"           # untouched
    assert subs[sec_id]["status"] == "pending" and subs[sec_id]["version"] == 2
    assert ticket["status"] == "in_review"
    for sid in (sec_id, fac_id):
        ticket = tickets.decide(sid, True, "officer", now=NOW)
    assert ticket["status"] == "completed"


def test_fix_with_no_new_details_asks_again():
    from munjiz import tickets
    from munjiz.agent import run_fix
    tid, conv = submitted_ticket()
    sec_id = tickets.get_ticket(tid)["subs"][1]["id"]
    ticket = tickets.decide(sec_id, False, "security.officer", "ID expired", now=NOW)
    result = run_fix(ticket, [sec_id], ["ok"], conv, NOW, backend="local")
    assert not result.ready and "ID expired" in result.reply


def test_resubmit_refuses_parts_that_were_not_sent_back():
    from munjiz import tickets
    from munjiz.rules import DeskCheck
    tid, _ = submitted_ticket()
    sub = tickets.get_ticket(tid)["subs"][0]
    with pytest.raises(ValueError):
        tickets.resubmit(sub["id"], DeskCheck(desk=sub["desk"], payload=sub["payload"]), now=NOW)


# --- Cross-desk conflicts ------------------------------------------------------------------------
def test_scenario_a_has_no_cross_desk_conflict():
    _, (first, second) = converse(EN)
    assert first.conflicts == [] and second.conflicts == [] and second.ready


def test_night_truck_and_crew_hours_clash_is_caught_and_the_fix_applies():
    from munjiz.agent import run_turn
    conv = [{"role": "user", "content": CONFLICT_DEMO}]
    r = run_turn(conv, "France Pavilion", NOW, backend="local")
    assert all(c.ok for c in r.checks.values())          # every desk alone is fine
    assert [c.check_id for c in r.blocking_conflicts] == ["power_outside_crew_hours"]
    assert not r.ready and "23:00" in r.reply
    assert r.fix_patch == {"facilities": {"needed_from": "2030-11-18T22:00:00+03:00"}}  # the evening before

    fixed = run_turn(conv, "France Pavilion", NOW, backend="local", patch=r.fix_patch)
    assert fixed.ready, fixed.reply


def test_permit_rules_compare_security_with_logistics():
    from munjiz import conflicts
    truck = {"arrival_datetime": "2030-11-18T22:00:00+03:00", "vehicle_type": "heavy_truck"}
    late = conflicts.check({"logistics": truck, "security": {"access_datetime": "2030-11-18T23:00:00+03:00"}})
    assert [c.check_id for c in late] == ["workers_after_truck"]
    assert late[0].patch == {"security": {"access_datetime": "2030-11-18T22:00:00+03:00"}}
    early = conflicts.check({"logistics": truck, "security": {"access_datetime": "2030-11-18T08:00:00+03:00"}},
                            {"logistics": {"slot_minutes": 60}})
    assert [c.check_id for c in early] == ["permit_expires_before_delivery"]


def test_badge_pickup_note_when_truck_uses_another_gate():
    from munjiz import conflicts
    found = conflicts.check({"logistics": {"arrival_datetime": "2030-11-18T22:00:00+03:00"},
                             "security": {"access_datetime": "2030-11-18T22:00:00+03:00"}},
                            {"logistics": {"gate": {"en": "Logistics Gate L1", "ar": "بوابة L1"}, "slot_minutes": 45}})
    assert [(c.check_id, c.severity) for c in found] == [("badge_pickup_other_gate", "note")]


# --- SLA -----------------------------------------------------------------------------------------
def test_sla_sends_one_reminder_then_one_escalation():
    from munjiz import tickets
    tid, _ = submitted_ticket()
    t0 = datetime.fromisoformat(tickets.get_ticket(tid)["created_at"])
    assert tickets.sla_sweep(t0 + timedelta(minutes=30)) == {"reminders": [], "escalations": []}
    first = tickets.sla_sweep(t0 + timedelta(minutes=130))  # logistics + facilities (120 min), security is 240
    assert sorted(i["desk"] for i in first["reminders"]) == ["facilities", "logistics"]
    assert tickets.sla_sweep(t0 + timedelta(minutes=135))["reminders"] == []  # only once
    later = tickets.sla_sweep(t0 + timedelta(minutes=250))
    assert sorted(i["desk"] for i in later["escalations"]) == ["facilities", "logistics"]
    assert [i["desk"] for i in later["reminders"]] == ["security"]


def test_supervisor_reassigns_and_overrides():
    from munjiz import tickets
    tid, _ = submitted_ticket()
    sub = tickets.get_ticket(tid)["subs"][0]
    ticket = tickets.reassign(sub["id"], "logistics.officer2", "ops.supervisor")
    assert ticket["subs"][0]["assigned_to"] == "logistics.officer2"
    ticket = tickets.decide(sub["id"], True, "ops.supervisor (override)", now=NOW)
    assert ticket["subs"][0]["decided_by"] == "ops.supervisor (override)"


# --- Organiser rules -----------------------------------------------------------------------------
def test_organiser_rule_change_applies_without_code():
    from munjiz import rules
    rules.set_rule("logistics", "notice", "hours", 48, "expo.organiser")
    _, (_, second) = converse(EN)
    blocked = [i for i in second.checks["logistics"].blocking if i.check_id == "notice"]
    assert blocked and "48 hours" in blocked[0].message["en"]
    rules.set_rule("logistics", "notice", "enabled", False, "expo.organiser")
    _, (_, second) = converse(EN)
    assert second.checks["logistics"].ok
    rules.reset_rules("expo.organiser")
    assert rules.load_rules()["logistics"]["checks"][0]["hours"] == 12


def test_crew_hours_are_editable():
    from munjiz import rules
    from munjiz.agent import run_turn
    rules.set_rule("cross_desk", "params", "utility_crew_hours.end", "03:00", "expo.organiser")
    r = run_turn([{"role": "user", "content": CONFLICT_DEMO}], "France Pavilion", NOW, backend="local")
    assert r.ready  # 02:00 is now inside the crews' hours (06:00 to 03:00 overnight)


# --- API -----------------------------------------------------------------------------------------
def test_api_request_change_and_sla_sweep(monkeypatch):
    from munjiz import config
    from munjiz.api import app
    monkeypatch.setattr(config, "now", lambda: NOW)  # the sweep reads the clock; keep it at submission time
    api = TestClient(app)
    tid, _ = submitted_ticket()
    headers = {"X-Munjiz-Token": TOKEN}
    r = api.post(f"/api/subrequests/SEC-{tid[4:]}/decision", headers=headers,
                 json={"decision": "request_change", "staff": "security.officer", "reason": "ID unreadable"})
    assert r.status_code == 200 and r.json()["subs"][f"SEC-{tid[4:]}"] == "changes_requested"
    assert api.post(f"/api/subrequests/LOG-{tid[4:]}/decision", headers=headers,
                    json={"decision": "maybe", "staff": "x"}).status_code == 422
    assert api.post("/api/sla/sweep").status_code == 401
    assert api.post("/api/sla/sweep", headers=headers).json()["count"] == 0


def test_simulation_has_cross_desk_conflicts_and_same_headline_numbers():
    from munjiz import simulate
    from munjiz.db import connect
    simulate.generate()
    with connect() as conn:
        clashes, multi = conn.execute(
            "SELECT SUM(cross_desk_conflict), SUM(desks LIKE '%,%') FROM hist_requests").fetchone()
        legacy = conn.execute("SELECT AVG(legacy_hours) FROM hist_requests").fetchone()[0]
    assert 0 < clashes < multi
    assert round(legacy, 5) == 24.63306  # the clash flag has its own random stream: earlier numbers don't move


def test_arabic_fix_replaces_one_workers_id():
    from munjiz import tickets
    from munjiz.agent import run_fix
    from tests.test_scenario_a import AR
    conv, (_, second) = converse(AR)
    tid = tickets.submit(second, "France Pavilion", "Demo", conv, now=NOW)
    sec = tickets.get_ticket(tid)["subs"][1]
    ticket = tickets.decide(sec["id"], staff="security.officer", reason="خالد الشمري: الهوية غير صالحة",
                            outcome="request_change", now=NOW)
    fix = "رقم هوية خالد الشمري 2012345678"
    result = run_fix(ticket, [sec["id"]], [fix], conv, NOW, backend="local")
    assert result.ready and result.language == "ar"
    assert [w["id_number"] for w in result.checks["security"].payload["workers"]] == ["1023456789", "2012345678"]


def test_n8n_gets_change_request_fix_and_sla_events(monkeypatch):
    from munjiz import config, events, tickets
    from munjiz.agent import run_fix
    sent = []
    monkeypatch.setattr(config, "N8N_WEBHOOK_URL", "http://n8n.test/webhook/munjiz-events")
    monkeypatch.setattr(events, "SYNC", True)
    monkeypatch.setattr(events, "_post", lambda url, body: sent.append(body) or 200)
    tid, conv = submitted_ticket()
    sec_id = f"SEC-{tid[4:]}"
    ticket = tickets.decide(sec_id, staff="security.officer", reason="ID unreadable", outcome="request_change", now=NOW)
    result = run_fix(ticket, [sec_id], ["John Smith's passport is P7654321"], conv, NOW, backend="local")
    tickets.resubmit(sec_id, result.checks["security"], now=NOW)
    t0 = datetime.fromisoformat(tickets.get_ticket(tid)["created_at"])
    tickets.sla_sweep(t0 + timedelta(minutes=500))
    kinds = [e["event"] for e in sent]
    assert kinds[:3] == ["ticket_submitted", "sub_decided", "sub_resubmitted"]
    assert sent[1]["status"] == "changes_requested" and sent[1]["ticket_status"] == "action_needed"
    assert [p["id"] for p in sent[2]["sub_requests"]] == [sec_id] and sent[2]["sub_requests"][0]["version"] == 2
    assert kinds.count("sla_escalated") == 3
