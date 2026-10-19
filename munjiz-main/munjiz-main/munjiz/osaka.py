"""Expo 2025 Osaka, Kansai replay: the last World Expo's real National Day calendar, run through Munjiz.

Real (datasets/osaka2025, built by scripts/osaka2025_build.py): which participant held its National or Special Day
on which day of the Expo, its pavilion type, and the daily staff and contractor entries on site passes.
Generated: the wording of each request, plates, crew names and IDs. Personal details are never taken from
the source.

Each National Day becomes the request that participant would send Munjiz for the same day of Expo 2030 Riyadh
(Osaka day N = Riyadh day N): equipment delivered the night before, crew passes, and power for the ceremony.
The participant writes once in plain words two days ahead, Munjiz asks once, the participant answers.
"""
import csv
import hashlib
from datetime import date, datetime, time, timedelta
from functools import cache

from . import config, expo
from .agent import run_turn

DATA = config.ROOT / "datasets" / "osaka2025"
OSAKA_OPENS = date(2025, 4, 13)
# Arab League members write to Munjiz in Arabic in the replay; everyone else in English.
ARABIC = {"DZA", "BHR", "COM", "DJI", "EGY", "IRQ", "JOR", "KWT", "LBN", "LBY", "MRT", "MAR", "OMN", "PSE", "QAT",
          "SAU", "SOM", "SDN", "SYR", "TUN", "ARE", "YEM"}
NAMES_EN = ["Anna Weber", "Luca Rossi", "Maria Silva", "Kenji Sato", "David Okafor", "Sara Novak", "Tom Hughes",
            "Elena Petrova", "Jonas Berg", "Amira Haddad"]
NAMES_AR = ["محمد العتيبي", "خالد الشمري", "سالم الكعبي", "أحمد الحارثي", "يوسف البلوشي", "علي الزهراني"]
NUM_WORDS = {2: "Two", 3: "Three", 4: "Four"}
NUM_AR = {2: "عاملين", 3: "ثلاثة عمال", 4: "أربعة عمال"}
STAGE_KW = [20, 30, 40, 45]  # ceremony stage, screens and sound: within the 50 kW no-sign-off band


@cache
def national_days() -> list[dict]:
    with open(DATA / "national_days.csv", encoding="utf-8") as f:
        return [dict(r, expo_day=int(r["expo_day"])) for r in csv.DictReader(f)]


@cache
def daily_attendance() -> list[dict]:
    with open(DATA / "daily_attendance.csv", encoding="utf-8") as f:
        return [{k: (v if k == "date" else int(v)) for k, v in r.items()} for r in csv.DictReader(f)]


def riyadh_date(expo_day: int) -> date | None:
    """The same day of Expo 2030 Riyadh (182 days, so Osaka's days 183 and 184 have none)."""
    return expo.OPENS + timedelta(days=expo_day - 1) if expo_day <= expo.DAYS else None


def _seed(code: str) -> int:
    return int(hashlib.sha256(code.encode()).hexdigest(), 16)


def case(day: dict) -> dict | None:
    """The two messages this participant sends for its National Day, and when it sends them."""
    when = riyadh_date(day["expo_day"])
    if when is None:
        return None
    h = _seed(day["code"])
    crew = 2 + h % 3
    kw = STAGE_KW[h // 3 % len(STAGE_KW)]
    plate_letters = "".join(chr(65 + (h >> (5 * i)) % 26) for i in range(3))
    plate = f"{plate_letters} {1000 + h % 9000}"
    arabic = day["code"] in ARABIC
    names = NAMES_AR if arabic else NAMES_EN
    crew_people = [(names[(h + i) % len(names)], (str(2_000_000_000 + (h >> 8) % 999_999_999 + i) if arabic
                                                 else f"P{(h >> (16 + i)) % 9_000_000 + 1_000_000}"))
                   for i in range(crew)]
    if arabic:
        first = (f"عندنا اليوم الوطني بعد بكرة. نحتاج إدخال معدات الحفل إلى جناحنا بكرة الساعة 10 مساءً. بيجي "
                 f"{NUM_AR[crew]} مع الشاحنة، والمسرح يحتاج كهرباء إضافية.")
        second = (f"لوحة الشاحنة {plate}. العمال: " + "، و".join(f"{n} هوية {i}" for n, i in crew_people)
                  + f". والمسرح يحتاج {kw} كيلوواط.")
    else:
        first = (f"Our National Day is the day after tomorrow. We need to bring the ceremony equipment into our "
                 f"pavilion tomorrow at 10 pm. {NUM_WORDS[crew]} workers will come with the truck, and the stage "
                 "needs extra power.")
        second = (f"Plate is {plate}. Workers: " + ", ".join(f"{n}, passport {i}" for n, i in crew_people)
                  + f". The stage needs {kw} kW.")
    sent = datetime.combine(when - timedelta(days=2), time(10, 0), tzinfo=config.TZ)
    return {"code": day["code"], "participant": day["participant"], "pavilion": day["pavilion"],
            "osaka_date": day["osaka_date"], "expo_day": day["expo_day"], "riyadh_date": when.isoformat(),
            "lang": "ar" if arabic else "en", "messages": [first, second], "sent": sent, "crew": crew, "kw": kw}


def run_case(c: dict, backend: str = "local") -> dict:
    """Run the two turns through the real agent and desk rules; report what happened at each step."""
    pavilion = f"{c['participant']} Pavilion"
    conv = [{"role": "user", "content": c["messages"][0]}]
    first = run_turn(conv, pavilion, now=c["sent"], backend=backend)
    conv += [{"role": "assistant", "content": first.reply}, {"role": "user", "content": c["messages"][1]}]
    second = run_turn(conv, pavilion, now=c["sent"] + timedelta(minutes=5), backend=backend)
    issues = sorted({i.check_id for chk in second.checks.values() for i in chk.blocking})
    night_before = datetime.combine(date.fromisoformat(c["riyadh_date"]) - timedelta(days=1), time(22, 0),
                                    tzinfo=config.TZ).isoformat()
    payloads = {desk: chk.payload for desk, chk in second.checks.items()}
    return {
        "code": c["code"], "participant": c["participant"], "pavilion": c["pavilion"], "osaka_date": c["osaka_date"],
        "riyadh_date": c["riyadh_date"], "lang": c["lang"],
        "desks": sorted(second.checks), "asked_once": not first.ready and bool(first.checks),
        "ready": second.ready, "issues": issues,
        "on_time": payloads.get("logistics", {}).get("arrival_datetime") == night_before,
        "crew_ok": len(payloads.get("security", {}).get("workers", [])) == c["crew"],
        "kw_ok": payloads.get("facilities", {}).get("power_kw") == c["kw"], "clashes": sorted(x.check_id for x in second.blocking_conflicts),
        "notes": sorted({i.check_id for chk in second.checks.values() for i in chk.notes}),
    }


def replay(backend: str = "local") -> tuple[list[dict], list[dict]]:
    """Every Osaka National Day that has a Riyadh day: (results, skipped days)."""
    results, skipped = [], []
    for day in national_days():
        c = case(day)
        if c is None:
            skipped.append(day)
        else:
            results.append(run_case(c, backend))
    return results, skipped


if __name__ == "__main__":
    res, skip = replay()
    ok = sum(r["ready"] and r["on_time"] and r["crew_ok"] and r["kw_ok"] for r in res)
    print(f"{len(res)} National Days replayed ({len(skip)} fall after Riyadh's last day); "
          f"asked once: {sum(r['asked_once'] for r in res)}; ready and read correctly after one answer: {ok}")
    for r in res:
        if not (r["ready"] and r["asked_once"] and r["on_time"] and r["crew_ok"] and r["kw_ok"]) or \
                r["desks"] != ["facilities", "logistics", "security"]:
            print(r)
