"""Desk rule engine. Each desk's rules live in rules/<desk>.yaml and are checked here, in code.

Organisers can change a rule's numbers (notice hours, limits, time windows, SLA targets) or switch a rule off
on the Desk rules page. Those changes are stored as overrides in the database, logged, and applied on top of
the YAML files, so no code or file edit is needed.
"""
import copy
import json
import re
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, time
from functools import cache

import yaml

from . import config
from .config import DESKS, RULES_DIR

CROSS = "cross_desk"
# Rule settings an organiser may change, per check type.
EDITABLE = {"min_notice_hours": ["hours"], "max_value": ["value"], "time_window": ["start", "end"],
            "count_match": [], "item_pattern": []}
_TTL_S = 3
CROSS_LABEL = {
    "workers_after_truck": "Workers' permits start after the truck arrives",
    "permit_expires_before_delivery": "Workers' permits expire before the truck's slot",
    "power_outside_crew_hours": "Power needed outside the utility crews' hours",
    "badge_pickup_other_gate": "Note: workers collect passes at a different gate from the truck",
}


@dataclass
class Issue:
    desk: str
    field: str
    kind: str  # "missing" | "rule" | "conflict"
    severity: str  # "block" | "note"
    message: dict  # {"en": ..., "ar": ...}
    check_id: str = ""


@dataclass
class DeskCheck:
    desk: str
    payload: dict
    assigned: dict = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)

    @property
    def blocking(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "block"]

    @property
    def notes(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "note"]

    @property
    def ok(self) -> bool:
        return not self.blocking


# --- Loading rules (YAML + organiser overrides) ----------------------------------------------------
@cache
def _base() -> dict[str, dict]:
    return {d: yaml.safe_load((RULES_DIR / f"{d}.yaml").read_text(encoding="utf-8")) for d in [*DESKS, CROSS]}


_merged: dict = {}  # db path -> (loaded_at, rules)


def overrides() -> list[dict]:
    from .db import connect, row
    with connect() as conn:
        return [row(r) for r in conn.execute("SELECT * FROM rule_overrides ORDER BY desk, rule_id, key")]


def _apply(rules: dict, ov: dict):
    target = rules
    if ov["rule_id"] == "sla":
        target = rules.setdefault("sla", {})
    elif ov["rule_id"] == "params":
        target = rules.setdefault("params", {})
    else:
        target = next((c for c in rules.get("checks", []) if c["id"] == ov["rule_id"]), None)
        if target is None:
            return
    value = json.loads(ov["value"])
    if "." in ov["key"]:  # e.g. utility_crew_hours.start
        outer, inner = ov["key"].split(".", 1)
        target.setdefault(outer, {})[inner] = value
    else:
        target[ov["key"]] = value


def _all_rules() -> dict[str, dict]:
    key = str(config.DB_PATH)
    hit = _merged.get(key)
    if hit and _time.monotonic() - hit[0] < _TTL_S:
        return hit[1]
    rules = copy.deepcopy(_base())
    for ov in overrides():
        if ov["desk"] in rules:
            _apply(rules[ov["desk"]], ov)
    _merged[key] = (_time.monotonic(), rules)
    return rules


def load_rules() -> dict[str, dict]:
    """The three desks' rules, with any organiser changes applied."""
    rules = _all_rules()
    return {d: rules[d] for d in DESKS}


def load_cross_desk() -> dict:
    return _all_rules()[CROSS]


def clear_cache():
    _merged.clear()


def active_checks(rules: dict) -> list[dict]:
    return [c for c in rules.get("checks", []) if c.get("enabled", True)]


def sla(desk: str) -> dict:
    return load_rules()[desk]["sla"]


def set_rule(desk: str, rule_id: str, key: str, value, by: str):
    """Store one organiser change (and log it), then reload the rules everywhere in this process."""
    from .db import connect, log
    now = config.now().isoformat()
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO rule_overrides (desk, rule_id, key, value, changed_by, changed_at)"
                     " VALUES (?,?,?,?,?,?)", (desk, rule_id, key, json.dumps(value), by, now))
        log(conn, "rule_changed", now, desk=desk, rule=rule_id, key=key, value=value, by=by)
    clear_cache()


def reset_rules(by: str):
    from .db import connect, log
    with connect() as conn:
        conn.execute("DELETE FROM rule_overrides")
        log(conn, "rules_reset", config.now().isoformat(), by=by)
    clear_cache()


def editable_settings() -> list[dict]:
    """Every setting an organiser may change, with its current value and the value in the rule file."""
    rules, base, out = _all_rules(), _base(), []

    def add(desk, rule_id, label, key, value, default, kind):
        out.append({"desk": desk, "rule_id": rule_id, "rule": label, "key": key, "value": value,
                    "default": default, "kind": kind})

    for desk in DESKS:
        r, b = rules[desk], base[desk]
        for key in ("review_minutes", "escalate_minutes"):
            add(desk, "sla", "Response target (SLA)", key, r["sla"][key], b["sla"][key], "number")
        for c in r.get("checks", []):
            bc = next(x for x in b["checks"] if x["id"] == c["id"])
            for key in EDITABLE[c["type"]]:
                add(desk, c["id"], _fill(c["message"], c)["en"], key, c[key], bc[key],
                    "time" if key in ("start", "end") else "number")
            add(desk, c["id"], _fill(c["message"], c)["en"], "enabled", c.get("enabled", True), True, "bool")
    r, b = rules[CROSS], base[CROSS]
    for key in ("start", "end"):
        add(CROSS, "params", "Utility crews connect power", f"utility_crew_hours.{key}",
            r["params"]["utility_crew_hours"][key], b["params"]["utility_crew_hours"][key], "time")
    add(CROSS, "params", "Single-visit contractor pass is valid for (hours)", "permit_valid_hours",
        r["params"]["permit_valid_hours"], b["params"]["permit_valid_hours"], "number")
    for c in r["checks"]:
        add(CROSS, c["id"], CROSS_LABEL.get(c["id"], c["id"]), "enabled", c.get("enabled", True), True, "bool")
    return out


# --- Checking ------------------------------------------------------------------------------------
def _empty(v) -> bool:
    return v is None or v == "" or v == []


def _matches(cond: dict | None, payload: dict) -> bool:
    for key, expected in (cond or {}).items():
        actual = payload.get(key)
        if isinstance(expected, dict):
            if actual is None:
                return False
            ops = {"lte": actual <= expected.get("lte", actual), "gte": actual >= expected.get("gte", actual),
                   "lt": "lt" not in expected or actual < expected["lt"],
                   "gt": "gt" not in expected or actual > expected["gt"]}
            if not all(ops.values()):
                return False
        elif actual != expected:
            return False
    return True


def in_window(dt: datetime, start: str, end: str) -> bool:
    s, e, t = time.fromisoformat(start), time.fromisoformat(end), dt.time()
    return s <= t <= e if s <= e else (t >= s or t <= e)


_in_window = in_window  # older name


def _violates(check: dict, payload: dict, now: datetime) -> bool:
    value = payload.get(check["field"])
    if _empty(value) or not _matches(check.get("when"), payload):
        return False
    kind = check["type"]
    if kind == "min_notice_hours":
        return (datetime.fromisoformat(value) - now).total_seconds() < check["hours"] * 3600
    if kind == "time_window":
        return not in_window(datetime.fromisoformat(value), check["start"], check["end"])
    if kind == "max_value":
        return float(value) > check["value"]
    if kind == "count_match":
        expected = payload.get(check["count_field"])
        return expected is not None and len(value) != expected
    if kind == "item_pattern":
        pat = re.compile(check["pattern"])
        return any(not pat.match(str(item.get(check["item_field"], "")).upper().replace(" ", "")) for item in value)
    raise ValueError(f"unknown check type {kind}")


def _fill(message: dict, check: dict) -> dict:
    """Messages may mention the rule's own numbers ({hours}, {value}, {start}, {end}) so edits show up in them."""
    keys = {k: (f"{check[k]:g}" if isinstance(check[k], float) else check[k])
            for k in ("hours", "value", "start", "end") if k in check}
    try:
        return {lang: text.format(**keys) for lang, text in message.items()}
    except (KeyError, IndexError):
        return message


def check_desk(desk: str, payload: dict, now: datetime) -> DeskCheck:
    rules = load_rules()[desk]
    result = DeskCheck(desk=desk, payload=payload)

    for name in rules["required"]:
        spec = rules["fields"][name]
        value = payload.get(name)
        incomplete = spec.get("type") == "list" and not _empty(value) and any(
            any(_empty(item.get(f)) for f in spec["item_fields"]) for item in value)
        if _empty(value) or incomplete:
            result.issues.append(Issue(desk, name, "missing", "block", spec["ask"]))

    for check in active_checks(rules):
        if _violates(check, payload, now):
            result.issues.append(Issue(desk, check["field"], "rule", check["severity"], _fill(check["message"], check),
                                       check["id"]))

    for rule in rules.get("assign", []):
        if _matches(rule.get("when"), payload):
            result.assigned = dict(rule["set"])
            break
    return result


def rule_count(desk: str) -> int:
    rules = load_rules()[desk]
    return len(rules["required"]) + len(active_checks(rules))
