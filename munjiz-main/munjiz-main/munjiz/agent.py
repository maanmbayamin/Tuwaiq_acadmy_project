"""One conversational turn: extract → split per desk → desk rule check → cross-desk check → follow-up or summary.

Also handles the fix loop: when a desk sends one part back, the participant answers in the same chat and only
that part is re-extracted, re-checked and sent again. Parts already approved stay approved.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime

from . import config, conflicts, expo, extract_local
from .conflicts import Conflict
from .i18n import detect_lang, fmt_dt, t
from .rules import DeskCheck, check_desk, load_rules


@dataclass
class AgentResult:
    language: str
    checks: dict[str, DeskCheck]
    reply: str
    conflicts: list[Conflict] = field(default_factory=list)
    fixing: list[str] = field(default_factory=list)  # sub-request ids being fixed (fix loop only)
    locked: dict[str, str] = field(default_factory=dict)  # fix loop: {desk: sub id} of parts that can't change now
    outstanding: list[str] = field(default_factory=list)  # fix loop: sent-back parts with no fix yet
    notes: list[str] = field(default_factory=list)  # fix loop: said before the summary (also inside `reply`)
    waiting: list[str] = field(default_factory=list)  # fix loop: what is still outstanding (also inside `reply`)

    @property
    def blocking_conflicts(self) -> list[Conflict]:
        return [c for c in self.conflicts if c.blocking]

    def can_apply(self, c: Conflict) -> bool:
        """A suggested fix can be applied only if every part it changes is open for changes."""
        return bool(c.patch) and not set(c.patch) & set(self.locked)

    @property
    def ready(self) -> bool:
        return bool(self.checks) and all(c.ok for c in self.checks.values()) and not self.blocking_conflicts

    @property
    def fix_patch(self) -> dict:
        """Every suggested fix merged: {desk: {field: value}}."""
        out: dict = {}
        for c in self.blocking_conflicts:
            if not self.can_apply(c):
                continue
            for desk, fields in c.patch.items():
                out.setdefault(desk, {}).update(fields)
        return out


def pick(value, lang: str):
    """Rule-file values are either plain or {en, ar}."""
    return value.get(lang, value.get("en")) if isinstance(value, dict) and "en" in value else value


def extract(conversation: list[dict], pavilion: str, now: datetime, backend: str) -> dict:
    if backend == "claude":
        from . import extract_claude
        return extract_claude.extract(conversation, pavilion, now)
    return extract_local.extract([m["content"] for m in conversation if m["role"] == "user"], now)


def _complete(subs: dict[str, dict], pavilion: str) -> dict[str, dict]:
    """Derived fields every desk payload needs (Expo phase, worker count, default service, pavilion)."""
    if "logistics" in subs and subs["logistics"].get("arrival_datetime"):  # some site rules depend on the phase
        subs["logistics"]["phase"] = expo.phase(datetime.fromisoformat(subs["logistics"]["arrival_datetime"]))
    if "security" in subs and subs["security"].get("workers") and subs["security"].get("worker_count") is None:
        subs["security"]["worker_count"] = len(subs["security"]["workers"])
    if "facilities" in subs:
        subs["facilities"].setdefault("service", "power_connection")
    for payload in subs.values():
        payload["pavilion"] = pavilion
    return subs


def split(raw: dict, pavilion: str, patch: dict | None = None) -> dict[str, dict]:
    """One sub-request per desk. Shared facts (time, pavilion) are given once and copied to every desk.
    `patch` holds fixes the participant accepted ({desk: {field: value}}); they win over the extraction."""
    subs = {desk: dict(payload) for desk, payload in raw.items() if payload is not None}
    when = (subs.get("logistics", {}).get("arrival_datetime")
            or subs.get("security", {}).get("access_datetime")
            or subs.get("facilities", {}).get("needed_from"))
    if "logistics" in subs:
        subs["logistics"].setdefault("arrival_datetime", when)
    if "security" in subs:
        subs["security"].setdefault("access_datetime", when)
    if "facilities" in subs:
        subs["facilities"].setdefault("needed_from", when)
    for desk, fields in (patch or {}).items():
        if desk in subs:
            subs[desk].update(fields)
    return _complete(subs, pavilion)


def desk_title(desk: str, lang: str) -> str:
    """Plain desk name. The desk's `icon` (a lucide icon name) is drawn only where HTML is rendered."""
    if desk == "cross_desk":
        return conflicts.load_cross_desk()["title"][lang]
    return load_rules()[desk]["title"][lang]


def describe(check: DeskCheck, lang: str) -> str:
    """One-line human summary of a desk's sub-request and what the desk will assign."""
    p, a, fields = check.payload, {k: pick(v, lang) for k, v in check.assigned.items()}, load_rules()[check.desk]["fields"]
    comma = "، " if lang == "ar" else ", "
    if check.desk == "logistics":
        vehicle = fields["vehicle_type"]["values"].get(p.get("vehicle_type"), {}).get(lang, "—")
        slot = f"{a.get('slot_minutes', '—')} {'دقيقة' if lang == 'ar' else 'min slot'}"
        return (f"{vehicle} · {p.get('vehicle_plate', '—')} · {p.get('cargo_description', '—')} · "
                f"{fmt_dt(p.get('arrival_datetime'), lang)} → **{a.get('gate', '—')}**{comma}{a.get('route', '—')} ({slot})")
    if check.desk == "security":
        people = comma.join(f"{w.get('full_name', '—')} ({w.get('id_number', '—')})" for w in p.get("workers", []))
        count = f"عدد العمال {p.get('worker_count', 0)}" if lang == "ar" else f"{p.get('worker_count', 0)} workers"
        since = "من" if lang == "ar" else "from"
        return (f"{count}: {people} · {since} {fmt_dt(p.get('access_datetime'), lang)} → "
                f"**{a.get('permit_type', '—')}**{comma}{a.get('badge_pickup', '—')}")
    if check.desk == "facilities":
        service = fields["service"]["values"][p.get("service", "power_connection")][lang]
        kw = f"{p['power_kw']:g} {'كيلوواط' if lang == 'ar' else 'kW'}" if p.get("power_kw") is not None else "—"
        since = "من" if lang == "ar" else "from"
        return f"{service} · {kw} {since} {fmt_dt(p.get('needed_from'), lang)} → **{a.get('connection', '—')}**"
    return str(p)


def locked_text(c: Conflict, locked: dict[str, str], lang: str) -> str | None:
    """Why a suggested fix can't be applied here: it would change a part that is not open for changes."""
    desks = [d for d in c.patch if d in locked]
    if not desks:
        return None
    comma = "، " if lang == "ar" else ", "
    return t("fix_locked", lang, desk=comma.join(f"**{desk_title(d, lang)}**" for d in desks),
             sub=comma.join(locked[d] for d in desks))


def _conflict_lines(found: list[Conflict], lang: str, locked: dict[str, str]) -> list[str]:
    lines = []
    for c in found:
        if not c.blocking:
            continue
        lines.append(f"- 🔀 {c.message[lang]}")
        if lock := locked_text(c, locked, lang):
            lines.append(f"  - 🔒 {lock}")
        elif c.fix:
            lines.append(f"  - ✅ {t('suggested_fix', lang)}: {c.fix[lang]}")
    return lines


def compose_reply(checks: dict[str, DeskCheck], lang: str, found: list[Conflict] | None = None,
                  locked: dict[str, str] | None = None) -> str:
    found, locked = found or [], locked or {}
    if not checks:
        return t("nothing_understood", lang)

    missing = [(d, i) for d, c in checks.items() for i in c.blocking if i.kind == "missing"]
    problems = [(d, i) for d, c in checks.items() for i in c.blocking if i.kind == "rule"]
    clashes = [c for c in found if c.blocking]
    if missing or problems or clashes:
        lines = []
        if missing:
            lines.append(t("followup_intro", lang))
            for n, (desk, issue) in enumerate(missing, 1):
                ask = issue.message[lang]
                count = checks[desk].payload.get("worker_count")
                if issue.field == "workers" and count:
                    ask += f" ({t('for_workers', lang, n=count)})"
                lines.append(f"{n}. {ask}  ·  _{load_rules()[desk]['title'][lang]}_")
        if problems:
            lines.append("" if not missing else "\n" + t("problems_intro", lang))
            lines += [f"- ⚠️ {issue.message[lang]}" for _, issue in problems]
        if clashes:
            lines.append(("\n" if lines else "") + t("conflicts_intro", lang))
            lines += _conflict_lines(clashes, lang, locked)
            if any(c.fix and not locked_text(c, locked, lang) for c in clashes):
                lines.append("\n" + t("apply_fix_question", lang))
        return "\n".join(lines).strip()

    lines = [t("summary_intro", lang), ""]
    for desk, check in checks.items():
        lines.append(f"- **{desk_title(desk, lang)}**: {describe(check, lang)}")
        lines += [f"  - ℹ️ {i.message[lang]}" for i in check.notes]
    lines += [f"- ℹ️ {c.message[lang]}" for c in found if not c.blocking]
    lines += ["", t("summary_outro", lang)]
    return "\n".join(lines)


def _cross_check(checks: dict[str, DeskCheck]) -> list[Conflict]:
    return conflicts.check({d: c.payload for d, c in checks.items()}, {d: c.assigned for d, c in checks.items()})


def run_turn(conversation: list[dict], pavilion: str, now: datetime | None = None,
             backend: str | None = None, patch: dict | None = None) -> AgentResult:
    now = now or config.now()
    last_user = next(m["content"] for m in reversed(conversation) if m["role"] == "user")
    lang = detect_lang(last_user)
    raw = extract(conversation, pavilion, now, backend or config.BACKEND)
    checks = {desk: check_desk(desk, payload, now) for desk, payload in split(raw, pavilion, patch).items()}
    found = _cross_check(checks)
    return AgentResult(language=lang, checks=checks, reply=compose_reply(checks, lang, found), conflicts=found)


# --- Fix loop: a desk sent a part back ------------------------------------------------------------
def _name_tokens(name: str) -> list[str]:
    return [re.sub(r"['’]s$", "", w) for w in (name or "").lower().split()]


def _same_token(new: str, old: str) -> bool:
    return new == old or (len(new) > 3 and new[0] in "لو" and new[1:] == old)  # "لخالد" (for Khalid) → خالد


def _same_person(new: str, old: str) -> bool:
    """Case and possessive don't matter; first + last name, or one name inside the other, is the same person."""
    a, b = _name_tokens(new), _name_tokens(old)
    if not a or not b:
        return False
    if len(a) >= 2 and len(b) >= 2 and _same_token(a[0], b[0]) and _same_token(a[-1], b[-1]):
        return True
    return all(any(_same_token(x, y) for y in b) for x in a) or all(any(_same_token(x, y) for x in a) for y in b)


def _find_worker(workers: list[dict], name: str) -> int | None:
    exact = [i for i, w in enumerate(workers) if _name_tokens(w.get("full_name")) == _name_tokens(name)]
    found = exact or [i for i, w in enumerate(workers) if _same_person(name, w.get("full_name"))]
    return found[0] if len(found) == 1 else None  # two people match: don't guess


def _merge_workers(old: list[dict], new: list[dict], lang: str) -> tuple[list[dict], list[str]]:
    """A named worker keeps their name and gets the corrected ID. Unknown names are added (a full new list
    replaces the old one). Nobody is dropped without the reply saying so (see _worker_notes)."""
    workers, fresh, matched, notes = [dict(w) for w in old], [], False, []
    for w in new:
        i = _find_worker(workers, w.get("full_name", "")) if w.get("full_name") else (0 if len(workers) == 1 else None)
        if i is not None:
            workers[i].update({k: v for k, v in w.items() if v and k != "full_name"})
            matched = True
        elif w.get("full_name"):
            fresh.append(w)
        else:
            notes.append(t("fix_whose_id", lang, id=w.get("id_number", "")))
    if fresh and not matched and len(fresh) >= len(workers):
        return fresh, notes  # the participant gave the whole list again
    return workers + fresh, notes


def _worker_notes(old: list[dict], new: list[dict], lang: str) -> list[str]:
    before = [w.get("full_name", "") for w in old]
    after = [w.get("full_name", "") for w in new]
    added = [n for n in after if not any(_same_person(n, b) for b in before)]
    removed = [b for b in before if not any(_same_person(n, b) for n in after)]
    comma = "، " if lang == "ar" else ", "
    if added and removed:
        return [t("workers_replaced", lang, old=comma.join(removed), new=comma.join(added), n=len(after))]
    if added or removed:
        key = "workers_added" if added else "workers_removed"
        return [t(key, lang, names=comma.join(added or removed), n=len(after), before=len(before))]
    return []


def _merge(desk: str, old: dict, new: dict, lang: str = "en") -> tuple[dict, list[str]]:
    """Old payload + what the participant just said. Returns the merged payload and notes for the reply."""
    merged, notes, new = dict(old), [], new or {}
    for key, value in new.items():
        if key == "workers" and value and old.get("workers"):
            merged["workers"], notes = _merge_workers(old["workers"], value, lang)
            notes += _worker_notes(old["workers"], merged["workers"], lang)
            if len(merged["workers"]) != len(old["workers"]) and not new.get("worker_count"):
                merged["worker_count"] = len(merged["workers"])  # the reply says so
        elif value not in (None, "", []):
            merged[key] = value
    return merged, notes


def run_fix(ticket: dict, sub_ids: list[str], fix_messages: list[str], conversation: list[dict],
            now: datetime | None = None, backend: str | None = None, patch: dict | None = None) -> AgentResult:
    """Re-check only the parts a desk sent back, using what the participant just wrote.
    The other parts (approved or still with their desk) are used as they are, for the cross-desk check, and are
    locked: a suggested fix that would change them is not offered. Only parts that actually changed go back;
    a sent-back part with no fix yet stays with the participant and the reply says so."""
    now = now or config.now()
    backend = backend or config.BACKEND
    lang = detect_lang(fix_messages[-1]) if fix_messages else (ticket.get("language") or "en")
    if backend == "claude":  # Claude needs the whole conversation for context; it returns the latest values
        raw = extract(conversation, ticket["pavilion"], now, backend)
    else:
        raw = extract_local.extract(fix_messages, now)
    subs = {s["desk"]: s for s in ticket["subs"]}
    fixing = {desk: s for desk, s in subs.items() if s["id"] in sub_ids}
    locked = {desk: s["id"] for desk, s in subs.items() if desk not in fixing}

    checks, all_payloads, all_assigned, notes = {}, {}, {}, []
    for desk, sub in subs.items():
        payload = dict(sub["payload"])
        if desk in fixing:
            payload, merge_notes = _merge(desk, payload, raw.get(desk) or {}, lang)
            notes += merge_notes
            payload.update((patch or {}).get(desk, {}))
            payload = _complete({desk: payload}, ticket["pavilion"])[desk]
            checks[desk] = check_desk(desk, payload, now)
            all_assigned[desk] = checks[desk].assigned
        else:
            all_assigned[desk] = sub["assigned"]
        all_payloads[desk] = payload
    changed = [d for d in checks if checks[d].payload != {**fixing[d]["payload"], "pavilion": ticket["pavilion"]}]
    checks = {d: c for d, c in checks.items() if d in changed}
    found = [c for c in conflicts.check(all_payloads, all_assigned) if set(c.desks) & set(changed)]
    outstanding = [fixing[d] for d in fixing if d not in changed]
    waiting = [t("fix_still_outstanding", lang, desk=desk_title(s["desk"], lang), sub=s["id"],
                 reason=s["reason"] or "—") for s in outstanding] if changed else []

    if not changed:
        reasons = "; ".join(s["reason"] or "" for s in fixing.values() if s.get("reason"))
        body = t("fix_nothing_changed", lang, reasons=reasons)
    elif not all(c.ok for c in checks.values()) or any(c.blocking for c in found):
        body = "\n\n".join([compose_reply(checks, lang, found, locked)] + waiting)
    else:
        lines = [t("fix_summary_intro" if len(checks) == 1 else "fix_summary_intro_many", lang), ""]
        for desk, check in checks.items():
            lines.append(f"- **{desk_title(desk, lang)}**: {describe(check, lang)}")
        lines += ([""] + waiting if waiting else []) + ["", t("fix_summary_outro", lang)]
        body = "\n".join(lines)
    return AgentResult(language=lang, checks=checks, reply="\n\n".join(notes + [body]), conflicts=found,
                       fixing=list(sub_ids), locked=locked, outstanding=[s["id"] for s in outstanding],
                       notes=notes, waiting=waiting)
