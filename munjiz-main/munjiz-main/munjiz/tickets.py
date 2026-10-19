"""Mock desk services: one ticket fanned out to desks; desk staff approve, request a change or reject; the
participant fixes only the part that came back; SLA reminders and escalation for parts that wait too long."""
import json
from datetime import datetime, timedelta

from . import config
from . import events
from .agent import AgentResult, describe
from .db import connect, log, row
from .rules import DeskCheck, load_rules, sla

DESK_PREFIX = {"logistics": "LOG", "security": "SEC", "facilities": "FAC"}
APPROVED, PENDING, CHANGES, REJECTED = "approved", "pending", "changes_requested", "rejected"
RETURNED = (CHANGES, REJECTED)  # parts the participant has to fix
OUTCOMES = {"approve": APPROVED, "request_change": CHANGES, "reject": REJECTED}


def _next_ticket_id(conn) -> str:
    """One more than the highest id ever given out. The counter lives in `meta`, so ids are not reused after
    "Reset demo" (a participant window could otherwise still hold an old id that now means another ticket)."""
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")  # two submits at once must not get the same id
    last = conn.execute("SELECT value FROM meta WHERE key='last_ticket'").fetchone()
    top = conn.execute("SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) FROM tickets WHERE id LIKE 'MNJ-%'").fetchone()[0]
    n = max(int(last[0]) if last else 1000, top or 1000) + 1
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_ticket', ?)", (str(n),))
    return f"MNJ-{n}"


def ticket_status(statuses: list[str]) -> str:
    """completed: every desk approved · partially_approved: some approved, some sent back ·
    action_needed: sent back, nothing approved yet · in_review: with the desks."""
    if statuses and all(s == APPROVED for s in statuses):
        return "completed"
    if any(s in RETURNED for s in statuses):
        return "partially_approved" if APPROVED in statuses else "action_needed"
    return "in_review"


def submit(result: AgentResult, pavilion: str, contact: str, conversation: list[dict],
           started_at: datetime | None = None, now: datetime | None = None, conflicts_caught: int = 0) -> str:
    if not result.ready:
        raise ValueError("request is not complete")
    now = now or config.now()
    followups = sum(1 for m in conversation if m["role"] == "assistant") - 1
    first_user = next(m["content"] for m in conversation if m["role"] == "user")
    with connect() as conn:
        tid = _next_ticket_id(conn)
        conn.execute(
            "INSERT INTO tickets (id, pavilion, contact, language, request_text, conversation, status, followups,"
            " conflicts_caught, started_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (tid, pavilion, contact, result.language, first_user, json.dumps(conversation, ensure_ascii=False),
             "in_review", max(followups, 0), conflicts_caught, (started_at or now).isoformat(), now.isoformat()))
        log(conn, "ticket_submitted", now.isoformat(), tid, desks=list(result.checks))
        if conflicts_caught:
            log(conn, "conflicts_caught_before_submit", now.isoformat(), tid, count=conflicts_caught)
        for desk, check in result.checks.items():
            sid = f"{DESK_PREFIX[desk]}-{tid[4:]}"
            notes = [i.message for i in check.notes] + [c.message for c in result.conflicts
                                                        if not c.blocking and desk in c.desks]
            conn.execute(
                "INSERT INTO sub_requests (id, ticket_id, desk, payload, assigned, notes, status, version, submitted_at,"
                " sla_state) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (sid, tid, desk, json.dumps(check.payload, ensure_ascii=False),
                 json.dumps(check.assigned, ensure_ascii=False), json.dumps(notes, ensure_ascii=False), PENDING,
                 1, now.isoformat(), ""))
            log(conn, "sent_to_desk", now.isoformat(), tid, sid, desk=desk)
    events.emit("ticket_submitted", _ticket_event(get_ticket(tid)))
    return tid


def _plain(markdown: str) -> str:
    return markdown.replace("**", "")


def _part_event(s: dict, rules: dict) -> dict:
    return {
        "id": s["id"], "desk": s["desk"], "desk_title": rules[s["desk"]]["title"]["en"], "version": s.get("version") or 1,
        "summary": _plain(describe(DeskCheck(desk=s["desk"], payload=s["payload"], assigned=s["assigned"]), "en")),
        "payload": s["payload"], "notes": [n["en"] for n in s["notes"]],
        "decision_url": f"{config.PUBLIC_API_URL}/api/subrequests/{s['id']}/decision",
        "sla_review_minutes": rules[s["desk"]]["sla"]["review_minutes"],
    }


def _ticket_event(ticket: dict, only: list[str] | None = None) -> dict:
    """What n8n needs to route each part: desk, a human-readable summary, the raw fields, and callback URLs."""
    rules = load_rules()
    return {
        "ticket_id": ticket["id"], "pavilion": ticket["pavilion"], "contact": ticket["contact"],
        "language": ticket["language"], "request_text": ticket["request_text"], "created_at": ticket["created_at"],
        "sub_requests": [_part_event(s, rules) for s in ticket["subs"] if only is None or s["id"] in only],
    }


def decide(sub_id: str, approve: bool | None = None, staff: str = "", reason: str = "",
           now: datetime | None = None, outcome: str | None = None) -> dict:
    """A desk decides on its part. outcome: approve | request_change | reject (or approve=True/False)."""
    if outcome is None:
        if approve is None:
            raise ValueError("say approve=True/False or give an outcome")
        outcome = "approve" if approve else "reject"
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {', '.join(OUTCOMES)}")
    status = OUTCOMES[outcome]
    if status != APPROVED and not reason.strip():
        reason = "No reason given"
    now = (now or config.now()).isoformat()
    with connect() as conn:
        sub = conn.execute("SELECT * FROM sub_requests WHERE id=?", (sub_id,)).fetchone()
        if sub is None or sub["status"] != PENDING:
            raise ValueError(f"{sub_id} is not pending")
        conn.execute("UPDATE sub_requests SET status=?, decided_by=?, decided_at=?, reason=? WHERE id=?",
                     (status, staff, now, reason if status != APPROVED else "", sub_id))
        log(conn, status, now, sub["ticket_id"], sub_id, desk=sub["desk"], staff=staff, reason=reason,
            version=sub["version"] or 1)
        _update_ticket(conn, sub["ticket_id"], now)
    ticket = get_ticket(sub["ticket_id"])
    events.emit("sub_decided", {"ticket_id": ticket["id"], "sub_id": sub_id, "desk": sub["desk"], "status": status,
                                "staff": staff, "reason": reason if status != APPROVED else "",
                                "ticket_status": ticket["status"], "pavilion": ticket["pavilion"],
                                "language": ticket["language"]})
    if ticket["status"] == "completed":
        minutes = (datetime.fromisoformat(ticket["closed_at"]) - datetime.fromisoformat(ticket["created_at"])).total_seconds() / 60
        events.emit("ticket_completed", {"ticket_id": ticket["id"], "pavilion": ticket["pavilion"],
                                         "language": ticket["language"], "closed_at": ticket["closed_at"],
                                         "minutes_to_complete": round(minutes, 1)})
    return ticket


def _update_ticket(conn, ticket_id: str, now: str):
    statuses = [r[0] for r in conn.execute("SELECT status FROM sub_requests WHERE ticket_id=?", (ticket_id,))]
    before = conn.execute("SELECT status FROM tickets WHERE id=?", (ticket_id,)).fetchone()[0]
    status = ticket_status(statuses)
    conn.execute("UPDATE tickets SET status=?, closed_at=? WHERE id=?",
                 (status, now if status == "completed" else None, ticket_id))
    if status != before:
        log(conn, "ticket_status", now, ticket_id, status=status)
        if status == "completed":
            log(conn, "ticket_completed", now, ticket_id)


def resubmit(sub_id: str, check: DeskCheck, staff_note: str = "", now: datetime | None = None) -> dict:
    """The participant fixed a part a desk sent back: a new version goes to the same desk, on the same ticket.
    Approved parts are not touched."""
    if not check.ok:
        raise ValueError("the corrected part still breaks a rule")
    now = (now or config.now()).isoformat()
    with connect() as conn:
        sub = conn.execute("SELECT * FROM sub_requests WHERE id=?", (sub_id,)).fetchone()
        if sub is None or sub["status"] not in RETURNED:
            raise ValueError(f"{sub_id} was not sent back to the participant")
        version = (sub["version"] or 1) + 1
        notes = [i.message for i in check.notes]
        conn.execute(
            "UPDATE sub_requests SET payload=?, assigned=?, notes=?, status=?, decided_by=NULL, decided_at=NULL,"
            " reason=NULL, version=?, submitted_at=?, sla_state='', assigned_to=NULL WHERE id=?",
            (json.dumps(check.payload, ensure_ascii=False), json.dumps(check.assigned, ensure_ascii=False),
             json.dumps(notes, ensure_ascii=False), PENDING, version, now, sub_id))
        log(conn, "resubmitted", now, sub["ticket_id"], sub_id, desk=sub["desk"], version=version,
            previous_reason=sub["reason"], note=staff_note)
        _update_ticket(conn, sub["ticket_id"], now)
    ticket = get_ticket(sub["ticket_id"])
    events.emit("sub_resubmitted", _ticket_event(ticket, only=[sub_id]))
    return ticket


def record_desk_receipt(desk: str, sub_id: str, desk_ref: str, via: str = "n8n") -> dict:
    """A desk's own system confirms it received its part (called by the mock desk systems through n8n)."""
    with connect() as conn:
        sub = conn.execute("SELECT * FROM sub_requests WHERE id=?", (sub_id,)).fetchone()
        if sub is None or sub["desk"] != desk:
            raise ValueError(f"{sub_id} is not a {desk} sub-request")
        conn.execute("UPDATE sub_requests SET desk_ref=? WHERE id=?", (desk_ref, sub_id))
        log(conn, "received_by_desk_system", config.now().isoformat(), sub["ticket_id"], sub_id,
            desk=desk, desk_ref=desk_ref, via=via)
    return {"sub_id": sub_id, "desk": desk, "desk_ref": desk_ref}


# --- SLA -----------------------------------------------------------------------------------------
def sla_info(sub: dict, now: datetime | None = None) -> dict:
    """How long this version has waited at its desk, against the desk's targets."""
    now = now or config.now()
    target = sla(sub["desk"])
    since = datetime.fromisoformat(sub.get("submitted_at") or sub["created_at"])
    waited = (now - since).total_seconds() / 60
    level = ("escalate" if waited >= target["escalate_minutes"] else
             "overdue" if waited >= target["review_minutes"] else "on_time")
    return {"waited_minutes": round(waited, 1), "review_minutes": target["review_minutes"],
            "escalate_minutes": target["escalate_minutes"], "level": level, "state": sub.get("sla_state") or ""}


def sla_sweep(now: datetime | None = None) -> dict:
    """Send each overdue part ONE reminder, then ONE escalation to the supervisor. Safe to call often
    (the app calls it on every refresh of the admin screens, n8n every 5 minutes)."""
    now = now or config.now()
    due = []  # (item, state it was in when read, new state)
    for desk in config.DESKS:
        for sub in desk_queue(desk):
            info = sla_info(sub, now)
            item = {"id": sub["id"], "ticket_id": sub["ticket_id"], "desk": desk, "pavilion": sub["pavilion"],
                    "waiting_minutes": info["waited_minutes"], "review_minutes": info["review_minutes"],
                    "escalate_minutes": info["escalate_minutes"], "assigned_to": sub.get("assigned_to")}
            if info["level"] == "escalate" and info["state"] != "escalated":
                due.append((item, info["state"], "escalated"))
            elif info["level"] == "overdue" and info["state"] == "":
                due.append((item, "", "reminded"))
    reminders, escalations = [], []
    with connect() as conn:
        for it, seen, state in due:
            # Only the sweep that moves the state on sends the alert (n8n and the admin pages sweep at the same time).
            moved = conn.execute("UPDATE sub_requests SET sla_state=? WHERE id=? AND status=?"
                                 " AND COALESCE(sla_state, '')=?", (state, it["id"], PENDING, seen)).rowcount
            if moved == 1:
                (escalations if state == "escalated" else reminders).append(it)
                log(conn, "sla_escalated" if state == "escalated" else "sla_reminder", now.isoformat(),
                    it["ticket_id"], it["id"], desk=it["desk"], waited_minutes=it["waiting_minutes"])
    for kind, items in (("sla_reminder", reminders), ("sla_escalated", escalations)):
        for it in items:
            events.emit(kind, it)
    return {"reminders": reminders, "escalations": escalations}


def reassign(sub_id: str, officer: str, supervisor: str) -> dict:
    with connect() as conn:
        sub = conn.execute("SELECT * FROM sub_requests WHERE id=?", (sub_id,)).fetchone()
        if sub is None or sub["status"] != PENDING:
            raise ValueError(f"{sub_id} is not pending")
        conn.execute("UPDATE sub_requests SET assigned_to=? WHERE id=?", (officer, sub_id))
        log(conn, "reassigned", config.now().isoformat(), sub["ticket_id"], sub_id, desk=sub["desk"],
            to=officer, by=supervisor)
    return get_ticket(sub["ticket_id"])


def age_pending(minutes: float):
    """Presenter control for the SLA demo: move every pending part's clock back, as if it had waited longer."""
    with connect() as conn:
        for r in conn.execute("SELECT id, submitted_at FROM sub_requests WHERE status=?", (PENDING,)).fetchall():
            if r["submitted_at"]:
                moved = datetime.fromisoformat(r["submitted_at"]) - timedelta(minutes=minutes)
                conn.execute("UPDATE sub_requests SET submitted_at=? WHERE id=?", (moved.isoformat(), r["id"]))


def pending_older_than(minutes: float) -> list[dict]:
    now = config.now()
    out = []
    for desk in config.DESKS:
        for sub in desk_queue(desk):
            info = sla_info(sub, now)
            if info["waited_minutes"] >= minutes:
                out.append({"id": sub["id"], "ticket_id": sub["ticket_id"], "desk": desk, "pavilion": sub["pavilion"],
                            "waiting_minutes": info["waited_minutes"], "sla_review_minutes": info["review_minutes"],
                            "sla_state": info["state"]})
    return sorted(out, key=lambda x: -x["waiting_minutes"])


# --- Reading -------------------------------------------------------------------------------------
def get_ticket(ticket_id: str) -> dict | None:
    with connect() as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if t is None:
            return None
        ticket = row(t)
        ticket["subs"] = [row(r) for r in conn.execute(
            "SELECT * FROM sub_requests WHERE ticket_id=? ORDER BY rowid", (ticket_id,))]
        ticket["events"] = [row(r) for r in conn.execute(
            "SELECT * FROM events WHERE ticket_id=? ORDER BY id", (ticket_id,))]
    return ticket


def get_ticket_for(ticket_id: str, pavilion: str) -> dict | None:
    """A participant's view: the ticket only if it belongs to their pavilion."""
    ticket = get_ticket(ticket_id) if ticket_id else None
    return ticket if ticket and ticket["pavilion"] == pavilion else None


def list_tickets(pavilion: str | None = None) -> list[dict]:
    """All tickets for the Expo Admin side; one pavilion's tickets for a participant."""
    with connect() as conn:
        if pavilion is None:
            rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC")
        else:
            rows = conn.execute("SELECT * FROM tickets WHERE pavilion=? ORDER BY created_at DESC", (pavilion,))
        return [row(r) for r in rows]


def desk_queue(desk: str, status: str = PENDING) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT s.*, t.pavilion, t.contact, t.created_at, t.request_text FROM sub_requests s"
            " JOIN tickets t ON t.id = s.ticket_id WHERE s.desk=? AND s.status=? ORDER BY COALESCE(s.submitted_at, t.created_at)",
            (desk, status))
        return [row(r) for r in rows]


def recent_events(limit: int = 30) -> list[dict]:
    """Newest ticket events first, with the ticket's pavilion: the Expo Admin activity feed."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT e.*, t.pavilion FROM events e LEFT JOIN tickets t ON t.id = e.ticket_id"
            " WHERE e.ticket_id IS NOT NULL ORDER BY e.id DESC LIMIT ?", (limit,))
        return [row(r) for r in rows]


def reset_live():
    """Clear demo tickets; simulated history, users and rule changes stay."""
    with connect() as conn:
        conn.executescript("DELETE FROM events WHERE ticket_id IS NOT NULL; DELETE FROM sub_requests; DELETE FROM tickets;")
