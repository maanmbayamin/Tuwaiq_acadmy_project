"""Generate SIMULATED participant requests for the Expo 2030 Riyadh dashboard.

The same 500 requests are run through two models of the process:
- legacy: one form per desk, desks one after another, incomplete forms bounce back;
- munjiz: one conversation, rules checked before submission, desks review in parallel.

Each multi-desk request may also hide a cross-desk clash. Today it is found late, after a desk has approved;
Munjiz catches it before submission. The clash flag uses its own random stream, so the other numbers don't move.

Every number below is an ASSUMPTION, shown on the dashboard. Replace them with figures from mentors.
Run: python -m munjiz.simulate
"""
import random
from datetime import timedelta

from . import config
from .db import connect

SEED = 2030
N_REQUESTS = 500

ASSUMPTIONS = {
    "legacy_desk_median_hours": 5.0,       # queue + review time per desk form
    "legacy_incomplete_rate": 0.35,        # forms bounced back for missing or wrong info
    "legacy_rework_median_hours": 10.0,    # delay added by each bounce
    "legacy_minutes_per_form": 15,         # participant time filling one desk's form
    "legacy_minutes_per_rework": 10,
    "munjiz_desk_median_hours": 1.5,       # desk reviews a pre-checked request
    "munjiz_incomplete_rate": 0.05,        # rules caught gaps before submission
    "munjiz_rework_median_hours": 2.0,
    "munjiz_minutes_base": 3,              # one conversation
    "munjiz_minutes_per_extra_desk": 1,
    "security_slowdown": 1.4,              # accreditation checks take longer
    "cross_desk_conflict_rate": 0.12,      # multi-desk requests whose parts clash (e.g. night truck vs crew hours)
}

DESK_FACTOR = {"logistics": 1.0, "security": ASSUMPTIONS["security_slowdown"], "facilities": 0.9}

REQUEST_TYPES = {  # type: (weight, desks)
    "Exhibit equipment delivery": (0.30, ["logistics", "security", "facilities"]),
    "Pavilion staff accreditation": (0.25, ["security", "facilities"]),
    "Catering and retail restock": (0.15, ["logistics", "security"]),
    "National Day / VIP delegation": (0.10, ["security", "logistics", "facilities"]),
    "Exhibit maintenance (night works)": (0.10, ["logistics", "security", "facilities"]),
    "Pavilion power upgrade": (0.10, ["facilities"]),
}

# Simulated requesters. Country names are examples; organisation and company entries are placeholders.
PAVILIONS = [("Country", f"{p} Pavilion") for p in [
    "France", "Bahrain", "Oman", "Switzerland", "Country A", "Country B", "Country C", "Country D",
    "Country E", "Country F", "Country G", "Country H"]] + \
    [("International organisation", f"International Organisation {c}") for c in "ABCD"] + \
    [("Company", f"Corporate Pavilion {c}") for c in "ABCDEF"]


def _lognormal(rng: random.Random, median: float, sigma: float = 0.6) -> float:
    return rng.lognormvariate(0, sigma) * median


def _desk_run(rng, desk, median, incomplete_rate, rework_median):
    wait = _lognormal(rng, median * DESK_FACTOR[desk])
    reworked = rng.random() < incomplete_rate
    if reworked:
        wait += _lognormal(rng, rework_median)
    return wait, reworked


def generate():
    rng = random.Random(SEED)
    clash_rng = random.Random(SEED + 1)
    a = ASSUMPTIONS
    now = config.now()
    types = list(REQUEST_TYPES)
    weights = [REQUEST_TYPES[t][0] for t in types]
    requests, steps = [], []

    for i in range(N_REQUESTS):
        rid = f"SIM-{i + 1:04d}"
        rtype = rng.choices(types, weights)[0]
        desks = REQUEST_TYPES[rtype][1]
        ptype, pavilion = rng.choice(PAVILIONS)
        submitted = now - timedelta(days=rng.uniform(1, 60), hours=rng.uniform(0, 10))

        legacy_total, legacy_first, legacy_reworks = 0.0, True, 0
        for desk in desks:  # one after another
            wait, reworked = _desk_run(rng, desk, a["legacy_desk_median_hours"], a["legacy_incomplete_rate"],
                                       a["legacy_rework_median_hours"])
            legacy_total += wait
            legacy_first &= not reworked
            legacy_reworks += reworked
            steps.append((rid, desk, "legacy", round(wait, 2), int(reworked)))

        munjiz_waits, munjiz_first = [], True
        for desk in desks:  # in parallel
            wait, reworked = _desk_run(rng, desk, a["munjiz_desk_median_hours"], a["munjiz_incomplete_rate"],
                                       a["munjiz_rework_median_hours"])
            munjiz_waits.append(wait)
            munjiz_first &= not reworked
            steps.append((rid, desk, "munjiz", round(wait, 2), int(reworked)))

        requests.append((
            rid, ptype, pavilion, rtype, ",".join(desks), submitted.isoformat(),
            round(legacy_total, 2), round(max(munjiz_waits), 2), int(legacy_first), int(munjiz_first),
            len(desks) * a["legacy_minutes_per_form"] + legacy_reworks * a["legacy_minutes_per_rework"],
            a["munjiz_minutes_base"] + (len(desks) - 1) * a["munjiz_minutes_per_extra_desk"],
            len(desks),
            int(len(desks) > 1 and clash_rng.random() < a["cross_desk_conflict_rate"]),
        ))

    with connect() as conn:
        conn.executescript("DELETE FROM hist_requests; DELETE FROM hist_steps;")
        conn.executemany(
            "INSERT INTO hist_requests (request_id, participant_type, pavilion, request_type, desks, submitted_at,"
            " legacy_hours, munjiz_hours, legacy_first_time, munjiz_first_time, legacy_participant_minutes,"
            " munjiz_participant_minutes, legacy_forms, cross_desk_conflict) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            requests)
        conn.executemany("INSERT INTO hist_steps VALUES (?,?,?,?,?)", steps)
    return len(requests)


if __name__ == "__main__":
    print(f"Generated {generate()} simulated requests in {config.DB_PATH}")
