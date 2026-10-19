"""Expo Admin on a desk officer's phone (components/admin_phone/index.html), shown next to the participant's phone on
the live-demo page. A desk's queue fills the moment the participant confirms, and a decision taken here reaches the
participant's ticket on the next refresh. Decisions are recorded as that desk's officer, like the desk console."""
from datetime import datetime

import streamlit.components.v1 as components

from munjiz import config, conflicts, tickets
from munjiz.agent import desk_title
from munjiz.rules import check_desk, load_rules, rule_count
from munjiz.users import officers
from views.common import STATUS, ago, describe_sub, md_bold

admin_phone = components.declare_component("munjiz_admin_phone", path=str(config.ROOT / "components" / "admin_phone"))

CHANGE_REASONS = {
    "logistics": ["Plate number unreadable, please re-send", "Please pick another time slot"],
    "security": ["Passport copy needed for a non-Saudi worker"],
    "facilities": ["Please confirm the load in kW", "Please pick another connection time"],
}
REJECT_REASONS = {
    "logistics": ["Gate fully booked at that time", "Vehicle not allowed on the service road"],
    "security": ["Worker not cleared for site access"],
    "facilities": ["Capacity exceeded at this pavilion"],
}
SHORT = {"logistics": "Logistics", "security": "Accreditation", "facilities": "Utilities"}


def worker_reasons(sub: dict) -> list[str]:
    return [f"{w.get('full_name', 'A worker')}'s ID could not be verified" for w in sub["payload"].get("workers", [])]


def officer(desk: str) -> str:
    return next(iter(officers(desk)), f"{desk}.officer")


def _part(sub: dict, ticket: dict) -> dict:
    desk = sub["desk"]
    info = tickets.sla_info(sub)
    recheck = check_desk(desk, sub["payload"], config.now())
    clashes = [c for c in conflicts.check({s["desk"]: s["payload"] for s in ticket["subs"]},
                                          {s["desk"]: s["assigned"] for s in ticket["subs"]})
               if desk in c.desks and c.blocking]
    change = (worker_reasons(sub) if desk == "security" else []) + CHANGE_REASONS[desk]
    return {
        "id": sub["id"], "ticket": sub["ticket_id"], "pavilion": sub["pavilion"].replace(" (example)", ""),
        "version": sub.get("version") or 1, "ago": ago(sub.get("submitted_at") or sub["created_at"]),
        "sla": f'{info["waited_minutes"]:.0f} of {info["review_minutes"]} min', "level": info["level"],
        "summary": md_bold(describe_sub(sub)),
        "rules_ok": recheck.ok, "rules": f"{rule_count(desk)} checks" if recheck.ok
        else "; ".join(i.message["en"] for i in recheck.blocking),
        "clash": "; ".join(c.message["en"] for c in clashes), "clash_checks": f"{conflicts.count()} checks",
        "ref": sub.get("desk_ref") or "", "notes": [n["en"] for n in sub["notes"]],
        "others": [{"title": desk_title(s["desk"], "en"), "status": s["status"], "label": STATUS[s["status"]]["en"]}
                   for s in ticket["subs"] if s["desk"] != desk],
        "words": sub["request_text"] or "",
        "reasons": [{"text": r, "outcome": "request_change"} for r in change]
        + [{"text": r, "outcome": "reject"} for r in REJECT_REASONS[desk]],
    }


def _activity(e: dict) -> dict | None:
    d, sub, tid = e["detail"] or {}, e["sub_id"], e["ticket_id"]
    who = (e.get("pavilion") or "A pavilion").replace(" (example)", "")
    text = {
        "ticket_submitted": f"{who} filed {tid} · {len(d.get('desks', []))} desks",
        "conflicts_caught_before_submit": f"Munjiz caught {d.get('count')} clash(es) before {tid} was sent",
        "received_by_desk_system": f"n8n routed {sub} to the desk system · {d.get('desk_ref')}",
        "approved": f"{sub} approved by {d.get('staff')}",
        "changes_requested": f"{sub} sent back: {d.get('reason')}",
        "rejected": f"{sub} rejected: {d.get('reason')}",
        "resubmitted": f"{who} fixed {sub} · v{d.get('version')}",
        "sla_reminder": f"Reminder: {sub} passed its response target",
        "sla_escalated": f"{sub} escalated to the supervisor",
        "reassigned": f"{sub} reassigned to {d.get('to')}",
        "ticket_completed": f"{tid} done · every desk approved",
    }.get(e["type"])
    if not text:
        return None
    return {"id": e["id"], "type": e["type"], "text": text, "at": f"{datetime.fromisoformat(e['at']):%H:%M}",
            "ticket": tid, "sub": sub or "", "pavilion": who}


def admin_data() -> dict:
    rules = load_rules()
    seen: dict[str, dict] = {}
    desks = []
    for desk in config.DESKS:
        pending = []
        for sub in tickets.desk_queue(desk):
            ticket = seen.get(sub["ticket_id"]) or seen.setdefault(sub["ticket_id"], tickets.get_ticket(sub["ticket_id"]))
            pending.append(_part(sub, ticket))
        desks.append({"id": desk, "title": desk_title(desk, "en"), "short": SHORT[desk], "icon": rules[desk]["icon"],
                      "officer": officer(desk), "pending": pending})
    decided = [s for desk in config.DESKS for status in (tickets.APPROVED, tickets.CHANGES, tickets.REJECTED)
               for s in tickets.desk_queue(desk, status)]
    decided.sort(key=lambda s: s["decided_at"] or "", reverse=True)
    return {
        "clock": f"{config.now():%H:%M}",
        "desks": desks,
        "decided": [{"id": s["id"], "ticket": s["ticket_id"], "icon": rules[s["desk"]]["icon"],
                     "pavilion": s["pavilion"].replace(" (example)", ""), "status": s["status"],
                     "label": STATUS[s["status"]]["en"], "by": s["decided_by"] or "", "ago": ago(s["decided_at"]),
                     "reason": s["reason"] or ""} for s in decided[:12]],
        "activity": [a for e in tickets.recent_events(40) if (a := _activity(e))][:25],
    }


def decide(event: dict) -> str | None:
    """Apply a decision from the admin phone; None if the part was already decided (double tap, another officer)."""
    sub_id = event.get("sub", "")
    desk = next((d for d, p in tickets.DESK_PREFIX.items() if sub_id.startswith(p + "-")), None)
    if desk is None or event.get("action") not in tickets.OUTCOMES:
        return None
    try:
        tickets.decide(sub_id, staff=officer(desk), reason=event.get("text", ""), outcome=event["action"])
    except ValueError:
        return None
    return sub_id
