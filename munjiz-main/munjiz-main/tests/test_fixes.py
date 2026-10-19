"""Regression tests for the review fixes: resume, partial fixes, locked clashes, names, ids, SLA, n8n, sign-in, API."""
import json
from datetime import datetime, timedelta

import pytest
from starlette.testclient import TestClient

from munjiz.config import ROOT
from tests.test_changes import TOKEN, submitted_ticket
from tests.test_scenario_a import AR, NOW, converse


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    from munjiz import config, rules
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "N8N_WEBHOOK_URL", "")
    monkeypatch.setattr(config, "API_TOKEN", TOKEN)
    rules.clear_cache()
    yield
    rules.clear_cache()


def send_back(tid, *prefixes, reason="Please check"):
    from munjiz import tickets
    ticket = None
    for p in prefixes:
        ticket = tickets.decide(f"{p}-{tid[4:]}", staff="officer", reason=reason, outcome="request_change", now=NOW)
    return ticket


def fix(ticket, prefixes, message, conv, **kw):
    from munjiz.agent import run_fix
    return run_fix(ticket, [f"{p}-{ticket['id'][4:]}" for p in prefixes], [message],
                   conv + [{"role": "user", "content": message}], NOW, backend="local", **kw)


def workers(result):
    return [(w["full_name"], w["id_number"]) for w in result.checks["security"].payload["workers"]]


# --- 1. Resume a ticket waiting for a fix only once per sign-in -----------------------------------
def test_waiting_ticket_is_resumed_once_and_never_after_new_request():
    from munjiz import chat
    tid, _ = submitted_ticket()
    send_back(tid, "SEC")
    assert chat.session_ticket("France Pavilion", None, auto_resume=True) == tid  # first load after sign-in
    assert chat.session_ticket("France Pavilion", None, auto_resume=False) is None  # after "New request"
    assert chat.session_ticket("France Pavilion", tid, auto_resume=False) == tid  # "continue fixing"
    assert [t["id"] for t in chat.waiting_for_fix("France Pavilion")] == [tid]


# --- 2. Only the parts that changed are resubmitted -----------------------------------------------
def test_fixing_one_of_two_returned_parts_sends_only_that_part_and_names_the_other():
    from munjiz import tickets
    tid, conv = submitted_ticket()
    ticket = send_back(tid, "LOG", "SEC", reason="Check this part")
    r = fix(ticket, ["LOG", "SEC"], "John Smith's passport is P7654321", conv)
    assert r.ready and list(r.checks) == ["security"]
    assert r.outstanding == [f"LOG-{tid[4:]}"]
    assert "Logistics" in r.reply and f"LOG-{tid[4:]}" in r.reply and "Check this part" in r.reply
    ticket = tickets.resubmit(f"SEC-{tid[4:]}", r.checks["security"], now=NOW)
    status = {s["desk"]: s["status"] for s in ticket["subs"]}
    assert status == {"logistics": "changes_requested", "security": "pending", "facilities": "pending"}


# --- 3. A clash whose fix would change a part that is not being fixed ------------------------------
@pytest.mark.parametrize("lang,message", [("en", "Move the truck to 4 am tomorrow"),
                                          ("ar", "انقل الشاحنة بكرة الساعة 4 الفجر")])
def test_clash_with_a_locked_part_offers_no_fix_button_and_names_the_other_desk(lang, message):
    from munjiz import tickets
    from munjiz.agent import desk_title
    conv, (_, second) = converse(AR) if lang == "ar" else converse_en()
    tid = tickets.submit(second, "France Pavilion", "Demo", conv, now=NOW)
    ticket = send_back(tid, "LOG")
    r = fix(ticket, ["LOG"], message, conv)
    assert r.language == lang
    assert [c.check_id for c in r.blocking_conflicts] == ["workers_after_truck"]
    assert r.fix_patch == {} and not r.ready  # nothing to apply, so "apply" can never loop
    assert desk_title("security", lang).split(" ", 1)[1] in r.reply and f"SEC-{tid[4:]}" in r.reply
    again = fix(ticket, ["LOG"], message, conv, patch=r.fix_patch)
    assert again.fix_patch == {}


def converse_en():
    from tests.test_scenario_a import EN
    return converse(EN)


def test_clash_fix_applies_when_both_parts_are_being_fixed():
    tid, conv = submitted_ticket()
    ticket = send_back(tid, "LOG", "SEC")
    r = fix(ticket, ["LOG", "SEC"], "Move the truck to 4 am tomorrow", conv)
    assert r.fix_patch == {"security": {"access_datetime": "2030-11-18T04:00:00+03:00"}}
    applied = fix(ticket, ["LOG", "SEC"], "Move the truck to 4 am tomorrow", conv, patch=r.fix_patch)
    assert applied.ready and set(applied.checks) == {"logistics", "security"}


# --- 4. Names in the fix loop ----------------------------------------------------------------------
@pytest.mark.parametrize("message", ["Ahmed Ali's correct ID is 1098765432", "Correct ID for Ahmed Ali: 1098765432",
                                     "ahmed ali's new ID is 1098765432", "The updated ID of Ahmed is 1098765432"])
def test_corrected_id_updates_the_named_worker_only(message):
    tid, conv = submitted_ticket()
    r = fix(send_back(tid, "SEC"), ["SEC"], message, conv)
    assert r.ready, r.reply
    assert workers(r) == [("Ahmed Ali", "1098765432"), ("John Smith", "P1234567")]


@pytest.mark.parametrize("message,expected", [
    ("رقم هوية خالد الشمري الصحيح 2012345678", [("محمد العتيبي", "1023456789"), ("خالد الشمري", "2012345678")]),
    ("هوية محمد العتيبي الصحيحة 1098765432", [("محمد العتيبي", "1098765432"), ("خالد الشمري", "2098765432")]),
    ("رقم الهوية الجديد لخالد الشمري 2012345678", [("محمد العتيبي", "1023456789"), ("خالد الشمري", "2012345678")]),
])
def test_arabic_corrected_id_updates_the_named_worker_only(message, expected):
    from munjiz import tickets
    conv, (_, second) = converse(AR)
    tid = tickets.submit(second, "France Pavilion", "Demo", conv, now=NOW)
    r = fix(send_back(tid, "SEC"), ["SEC"], message, conv)
    assert r.ready and r.language == "ar", r.reply
    assert workers(r) == expected


def test_name_parser_drops_filler_words():
    from munjiz.extract_local import _workers
    assert _workers("Ahmed Ali's correct ID is 1098765432") == [{"full_name": "Ahmed Ali", "id_number": "1098765432"}]
    assert _workers("رقم هوية محمد العتيبي الصحيح 1098765432")[0]["full_name"] == "محمد العتيبي"


def test_a_new_worker_is_added_and_the_count_change_is_said():
    tid, conv = submitted_ticket()
    r = fix(send_back(tid, "SEC"), ["SEC"], "Add Sara Lee, ID 1034567890", conv)
    assert workers(r) == [("Ahmed Ali", "1023456789"), ("John Smith", "P1234567"), ("Sara Lee", "1034567890")]
    assert r.checks["security"].payload["worker_count"] == 3
    assert "Sara Lee" in r.reply and "3" in r.reply


# --- 5. "fix"/"apply" inside a real fix message ----------------------------------------------------
def test_only_short_confirmations_accept_the_suggested_fix():
    from munjiz.chat import wants_fix
    for yes in ("Apply the suggested fix", "طبّق الحل المقترح", "yes", "ok apply it", "نعم", "fix it"):
        assert wants_fix(yes), yes
    for no in ("Here's the fixed ID: P7654321", "Please fix John's passport, it is P7654321",
               "move the truck to 4 am tomorrow", "طبق الرقم ٢٠١٢٣٤٥٦٧٨"):
        assert not wants_fix(no), no


# --- 6. Ticket ids are never reused and a participant only loads their own -------------------------
def test_ticket_ids_survive_reset_and_other_pavilions_tickets_are_not_loaded():
    from munjiz import chat, tickets
    first, conv = submitted_ticket()
    tickets.reset_live()
    _, (_, second) = converse_en()
    oman = tickets.submit(second, "Oman Pavilion", "Demo", conv, now=NOW)
    assert oman != first and int(oman[4:]) > int(first[4:])
    assert tickets.get_ticket_for(oman, "France Pavilion") is None
    assert tickets.get_ticket_for(oman, "Oman Pavilion")["id"] == oman
    assert chat.session_ticket("France Pavilion", oman, auto_resume=True) is None


def test_ticket_id_follows_the_highest_existing_id():
    from munjiz.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO tickets (id, pavilion, status, created_at) VALUES ('MNJ-1500', 'x', 'completed', '')")
    tid, _ = submitted_ticket()
    assert tid == "MNJ-1501"


# --- 7. Concurrent SLA sweeps send each alert once -------------------------------------------------
def test_concurrent_sla_sweeps_do_not_send_the_same_reminder_twice(monkeypatch):
    from munjiz import config, events, tickets
    sent = []
    monkeypatch.setattr(config, "N8N_WEBHOOK_URL", "http://n8n.test/webhook")
    monkeypatch.setattr(events, "SYNC", True)
    monkeypatch.setattr(events, "_post", lambda url, body: sent.append(body) or 200)
    tid, _ = submitted_ticket()
    later = datetime.fromisoformat(tickets.get_ticket(tid)["created_at"]) + timedelta(minutes=130)
    stale = {d: tickets.desk_queue(d) for d in config.DESKS}  # what a second sweep read before the first wrote
    assert len(tickets.sla_sweep(later)["reminders"]) == 2
    monkeypatch.setattr(tickets, "desk_queue", lambda desk, status="pending": stale[desk])
    assert tickets.sla_sweep(later) == {"reminders": [], "escalations": []}
    assert [e["event"] for e in sent].count("sla_reminder") == 2


# --- 8. n8n desk decision passes the body through --------------------------------------------------
def test_desk_decision_workflow_does_not_invent_a_rejection():
    wf = json.loads((ROOT / "n8n" / "workflows" / "munjiz_desk_decision.json").read_text())
    body = next(n for n in wf["nodes"] if n["type"].endswith("httpRequest"))["parameters"]["jsonBody"]
    assert "'reject'" not in body and "$json.body.decision" in body and "$json.body.approve" in body
    from munjiz.api import app
    tid, _ = submitted_ticket()
    r = TestClient(app).post(f"/api/subrequests/LOG-{tid[4:]}/decision", headers={"X-Munjiz-Token": TOKEN},
                             json={"staff": "logistics.officer", "reason": ""})
    assert r.status_code == 422


# --- 9. Sign-in hardening --------------------------------------------------------------------------
def test_session_token_has_no_pavilion_code_and_round_trips():
    from munjiz import users
    u = users.sign_in_with_pavilion_code("FRA-2030")
    assert u["id"] == "p-france" and u["pavilion"] == "France Pavilion"
    token = users.session_token(u)
    assert "2030" not in token and users.from_token(token) == u
    assert users.from_token("p-france.ünïcode") is None and users.from_token("ü.ü") is None
    assert users.from_token("p-france." + "0" * 20) is None


@pytest.mark.parametrize("configured", ["", "change-me"])
def test_no_known_fallback_secret(monkeypatch, configured):
    import hmac
    from munjiz import config, users
    monkeypatch.setattr(config, "API_TOKEN", configured)
    assert users._secret() not in (b"", b"change-me", b"munjiz-demo-session") and users._secret() == users._secret()
    forged = "p-france." + hmac.new(b"munjiz-demo-session", b"p-france", "sha256").hexdigest()[:20]
    assert users.from_token(forged) is None


# --- 10. Ticket reads need the token ---------------------------------------------------------------
def test_ticket_reads_need_the_token():
    from munjiz.api import app
    api = TestClient(app)
    tid, _ = submitted_ticket()
    assert api.get("/health").status_code == 200
    assert api.get("/api/tickets").status_code == 401
    assert api.get(f"/api/tickets/{tid}").status_code == 401
    headers = {"X-Munjiz-Token": TOKEN}
    assert api.get("/api/tickets", headers=headers).json()[0]["id"] == tid
    assert api.get(f"/api/tickets/{tid}", headers=headers).json()["subs"][1]["payload"]["workers"]


def test_replacing_workers_or_an_unnamed_id_is_said_not_silent():
    tid, conv = submitted_ticket()
    ticket = send_back(tid, "SEC")
    r = fix(ticket, ["SEC"], "Workers: Peter Pan, ID 1098765432 and Mary Jane, ID 1076543210", conv)
    assert workers(r) == [("Peter Pan", "1098765432"), ("Mary Jane", "1076543210")]
    assert "replaces Ahmed Ali, John Smith with Peter Pan, Mary Jane" in r.reply
    r = fix(ticket, ["SEC"], "The ID is 1098765432", conv)
    assert not r.checks and "whose ID 1098765432" in r.reply
