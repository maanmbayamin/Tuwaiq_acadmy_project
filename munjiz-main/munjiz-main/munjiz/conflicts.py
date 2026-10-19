"""Cross-desk check: clashes BETWEEN the desk sub-requests of one request.

Each desk checks only its own part. Some problems only show when the parts are read together, for example a
truck that may only enter at night while the utility crews who connect its power only work until 23:00.
Munjiz runs these checks in code after the desk checks, before anything is submitted, and suggests a fix the
participant can accept in one tap. Settings live in rules/cross_desk.yaml.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time

from .i18n import fmt_dt
from .rules import active_checks, in_window, load_cross_desk

LANGS = ("en", "ar")


@dataclass
class Conflict:
    check_id: str
    desks: list[str]
    severity: str  # "block" | "note"
    message: dict  # {"en": ..., "ar": ...}
    fix: dict | None = None  # suggested fix in words
    patch: dict = field(default_factory=dict)  # {desk: {field: value}} that applies the fix

    @property
    def blocking(self) -> bool:
        return self.severity == "block"


def _dt(value):
    return datetime.fromisoformat(value) if value else None


def _text(template: dict, values: dict) -> dict:
    return {lang: template[lang].format(**values[lang]) for lang in LANGS}


def _both(**kw) -> dict:
    """Values per language: datetimes are formatted for each language, everything else is shared."""
    return {lang: {k: (fmt_dt(v, lang) if isinstance(v, datetime) else v[lang] if isinstance(v, dict) else v)
                   for k, v in kw.items()} for lang in LANGS}


def _workers_after_truck(c, p, a, params):
    arrival, access = _dt(p["logistics"].get("arrival_datetime")), _dt(p["security"].get("access_datetime"))
    if arrival and access and access > arrival:
        values = _both(arrival=arrival, access=access)
        return values, values, {"security": {"access_datetime": arrival.isoformat()}}


def _permit_expires(c, p, a, params):
    arrival, access = _dt(p["logistics"].get("arrival_datetime")), _dt(p["security"].get("access_datetime"))
    if not (arrival and access) or access > arrival:
        return None
    slot = a.get("logistics", {}).get("slot_minutes", 0) or 0
    hours = params["permit_valid_hours"]
    if access + timedelta(hours=hours) < arrival + timedelta(minutes=slot):
        values = _both(arrival=arrival, access=access, hours=f"{hours:g}")
        return values, values, {"security": {"access_datetime": arrival.isoformat()}}


def _power_outside_crew_hours(c, p, a, params):
    needed = _dt(p["facilities"].get("needed_from"))
    crew = params["utility_crew_hours"]
    if not needed or in_window(needed, crew["start"], crew["end"]):
        return None
    end = time.fromisoformat(crew["end"])
    suggested = needed.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0) - timedelta(hours=1)
    if suggested > needed:  # crews have stopped already today: the evening before
        suggested -= timedelta(days=1)
    values = _both(needed=needed, start=crew["start"], end=crew["end"], suggested=suggested)
    return values, values, {"facilities": {"needed_from": suggested.isoformat()}}


def _badge_pickup_other_gate(c, p, a, params):
    gate = a.get("logistics", {}).get("gate")
    gate_en = gate.get("en") if isinstance(gate, dict) else gate
    if gate_en and "L2" not in gate_en:
        values = _both(gate=gate, minutes=params.get("badge_walk_minutes", 30))
        return values, None, {}


CHECKS = {
    "workers_after_truck": _workers_after_truck,
    "permit_expires_before_delivery": _permit_expires,
    "power_outside_crew_hours": _power_outside_crew_hours,
    "badge_pickup_other_gate": _badge_pickup_other_gate,
}


def check(payloads: dict[str, dict], assigned: dict[str, dict] | None = None) -> list[Conflict]:
    """payloads/assigned: per desk. Returns the clashes between desks, blocking ones first."""
    rules = load_cross_desk()
    assigned = assigned or {}
    out = []
    for c in active_checks(rules):
        if not all(d in payloads and payloads[d] for d in c["desks"]) or c["id"] not in CHECKS:
            continue
        found = CHECKS[c["id"]](c, payloads, assigned, rules["params"])
        if not found:
            continue
        msg_values, fix_values, patch = found
        out.append(Conflict(c["id"], c["desks"], c["severity"], _text(c["message"], msg_values),
                            _text(c["fix"], fix_values) if c.get("fix") and fix_values else None, patch))
    return sorted(out, key=lambda x: not x.blocking)


def count() -> int:
    return len(active_checks(load_cross_desk()))
