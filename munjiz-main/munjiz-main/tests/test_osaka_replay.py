"""Expo 2025 Osaka replay: the real National Day calendar run through the agent and desk rules (offline parser)."""
from datetime import datetime

from munjiz import osaka
from munjiz.config import TZ
from munjiz.extract_local import parse_datetime


def test_dataset_matches_the_organisers_totals():
    days = osaka.daily_attendance()
    assert len(days) == 184 and days[0]["date"] == "2025-04-13" and days[-1]["date"] == "2025-10-13"
    assert sum(d["staff_entries"] for d in days) == 3_438_938
    assert abs(sum(d["general"] for d in days) - 25_578_986) <= 10
    nds = osaka.national_days()
    assert len(nds) == 163 and len({d["osaka_date"] for d in nds}) == 163  # one National or Special Day per day
    assert sum(bool(d["source"]) for d in nds) >= 160  # each links to the organiser's own post for that day


def test_every_national_day_is_asked_once_and_read_correctly():
    results, skipped = osaka.replay()
    assert len(results) == 162 and len(skipped) == 1  # Osaka ran 184 days, Riyadh runs 182
    assert {r["lang"] for r in results} == {"en", "ar"}
    for r in results:
        assert r["desks"] == ["facilities", "logistics", "security"], r
        assert r["asked_once"] and r["ready"], r
        assert r["on_time"] and r["crew_ok"] and r["kw_ok"], r


def test_the_day_word_closest_to_the_time_wins():
    """Found by the replay: "the day after tomorrow" (the National Day) must not move "tomorrow at 10 pm"."""
    now = datetime(2030, 11, 17, 10, 0, tzinfo=TZ)
    text = "Our National Day is the day after tomorrow. The truck comes tomorrow at 10 pm."
    assert parse_datetime(text, now).startswith("2030-11-18T22:00")
    ar = "عندنا اليوم الوطني بعد بكرة. نحتاج إدخال المعدات بكرة الساعة 10 مساءً."
    assert parse_datetime(ar, now).startswith("2030-11-18T22:00")
    assert parse_datetime("The truck comes the day after tomorrow at 2 am.", now).startswith("2030-11-19T02:00")
