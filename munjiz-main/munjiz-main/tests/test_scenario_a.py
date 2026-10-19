import importlib
from datetime import datetime

import pytest

from munjiz.config import TZ

NOW = datetime(2030, 11, 17, 14, 0, tzinfo=TZ)  # Expo day 48
EN = [
    "I need to bring display equipment into our pavilion tomorrow at 10 pm. Two workers will come with the truck, and the screens need extra power.",
    "Plate is ABC 1234. Workers: Ahmed Ali, ID 1023456789 and John Smith, passport P1234567. The screens need 40 kW.",
]
AR = [
    "أحتاج إدخال معدات عرض إلى جناحنا بكرة الساعة 10 مساءً. بيجي عاملين مع الشاحنة، والشاشات تحتاج كهرباء إضافية.",
    "لوحة الشاحنة أ ب ج 1234. العمال: محمد العتيبي هوية 1023456789، وخالد الشمري هوية 2098765432. والشاشات تحتاج 40 كيلوواط.",
]


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    from munjiz import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "N8N_WEBHOOK_URL", "")  # never call a real n8n from tests


def converse(messages):
    from munjiz.agent import run_turn
    conv, results = [], []
    for m in messages:
        conv.append({"role": "user", "content": m})
        r = run_turn(conv, "France Pavilion", NOW, backend="local")
        conv.append({"role": "assistant", "content": r.reply})
        results.append(r)
    return conv, results


@pytest.mark.parametrize("messages,lang", [(EN, "en"), (AR, "ar")])
def test_first_message_splits_into_three_desks_and_asks_once(messages, lang):
    _, (first, _) = converse(messages)
    assert first.language == lang
    assert set(first.checks) == {"logistics", "security", "facilities"}
    missing = {(d, i.field) for d, c in first.checks.items() for i in c.blocking}
    assert missing == {("logistics", "vehicle_plate"), ("security", "workers"), ("facilities", "power_kw")}
    # The time is said once and shared with every desk.
    assert first.checks["security"].payload["access_datetime"] == "2030-11-18T22:00:00+03:00"
    assert first.checks["facilities"].payload["needed_from"] == "2030-11-18T22:00:00+03:00"


@pytest.mark.parametrize("messages", [EN, AR])
def test_follow_up_completes_the_request(messages):
    _, (_, second) = converse(messages)
    assert second.ready, second.reply
    sec = second.checks["security"].payload
    assert sec["worker_count"] == 2 and len(sec["workers"]) == 2
    assert all(w["full_name"] for w in sec["workers"])
    assert second.checks["facilities"].payload["power_kw"] == 40
    assert second.checks["logistics"].assigned["gate"]["en"] == "Logistics Gate L2"


def test_submit_and_approve_gives_one_completed_ticket():
    from munjiz import tickets
    conv, (_, second) = converse(EN)
    tid = tickets.submit(second, "France Pavilion", "Demo", conv, now=NOW)
    ticket = tickets.get_ticket(tid)
    assert ticket["status"] == "in_review" and ticket["followups"] == 1
    assert [s["desk"] for s in ticket["subs"]] == ["logistics", "security", "facilities"]
    for s in ticket["subs"]:
        ticket = tickets.decide(s["id"], True, "officer", now=NOW)
    assert ticket["status"] == "completed"


def test_rejection_flags_ticket():
    from munjiz import tickets
    conv, (_, second) = converse(EN)
    tid = tickets.submit(second, "France Pavilion", "Demo", conv, now=NOW)
    sub = tickets.get_ticket(tid)["subs"][1]
    assert tickets.decide(sub["id"], False, "officer", "ID expired", now=NOW)["status"] == "action_needed"


def test_heavy_truck_in_daytime_is_blocked_by_rule():
    _, (r,) = converse(["Bringing furniture by truck tomorrow at 3 pm, plate ABC 1234."])
    rules = [i.check_id for i in r.checks["logistics"].blocking if i.kind == "rule"]
    assert rules == ["heavy_vehicle_window"]
    assert "22:00" in r.reply


def test_heavy_truck_in_daytime_is_allowed_during_build_up():
    from munjiz.agent import run_turn
    build_up = datetime(2030, 6, 1, 9, 0, tzinfo=TZ)
    r = run_turn([{"role": "user", "content": "Bringing furniture by truck tomorrow at 3 pm, plate ABC 1234."}],
                 "France Pavilion", build_up, backend="local")
    assert r.checks["logistics"].payload["phase"] == "build_up"
    assert not [i for i in r.checks["logistics"].blocking if i.kind == "rule"]


def test_bad_id_and_short_notice_are_blocked():
    _, (r,) = converse(["Two workers tonight at 11 pm: Sara Lee 12345 and Omar Nasser 1023456789"])
    # 12345 isn't an ID token, so only one worker is captured and the count no longer matches.
    blocked = [i.check_id for i in r.checks["security"].blocking]
    assert "names_match_count" in blocked and "notice" in blocked  # 9 hours' notice < 12


def test_arabic_and_prefix_is_stripped_from_names():
    _, (_, second) = converse(AR)
    assert [w["full_name"] for w in second.checks["security"].payload["workers"]] == ["محمد العتيبي", "خالد الشمري"]


def test_over_50kw_adds_note_not_block():
    _, (_, second) = converse([EN[0], EN[1].replace("40 kW", "75 kW")])
    assert second.ready
    assert [i.check_id for i in second.checks["facilities"].notes] == ["engineer_signoff"]
    assert second.checks["facilities"].assigned["connection"]["en"] == "125 A temporary distribution board"


def test_simulation_is_reproducible():
    from munjiz import simulate
    from munjiz.db import connect
    assert simulate.generate() == 500
    with connect() as conn:
        legacy, munjiz = conn.execute("SELECT AVG(legacy_hours), AVG(munjiz_hours) FROM hist_requests").fetchone()
    assert munjiz < legacy
