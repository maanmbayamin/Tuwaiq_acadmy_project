"""Munjiz REST API: what n8n and desk systems call.

Run: uvicorn munjiz.api:app --host 0.0.0.0 --port 8000
Write endpoints and ticket reads (they hold worker names and ID numbers) need the header
`X-Munjiz-Token: <MUNJIZ_API_TOKEN>` when a token is configured. /health is open.

/mock/desks/* stands in for each desk's own system (gate booking, accreditation, utilities). In a pilot,
n8n would call the real systems instead and nothing in Munjiz would change.

Built on Starlette (already a Streamlit dependency), so it needs no extra install.
"""
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import config, tickets
from .db import connect, row

DESK_SYSTEM = {"logistics": "GATE", "security": "ACC", "facilities": "UTL"}


def error(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)


def authorised(request: Request) -> bool:
    return not config.API_TOKEN or request.headers.get("x-munjiz-token") == config.API_TOKEN


async def body_json(request: Request) -> dict | None:
    try:
        data = await request.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


async def health(request: Request):
    return JSONResponse({"ok": True, "n8n": bool(config.N8N_WEBHOOK_URL), "clock": config.now().isoformat()})


async def list_tickets(request: Request):
    if not authorised(request):
        return error(401, "Missing or wrong X-Munjiz-Token header")
    return JSONResponse(tickets.list_tickets())


async def get_ticket(request: Request):
    if not authorised(request):
        return error(401, "Missing or wrong X-Munjiz-Token header")
    ticket = tickets.get_ticket(request.path_params["ticket_id"])
    return JSONResponse(ticket) if ticket else error(404, f"No ticket {request.path_params['ticket_id']}")


async def pending(request: Request):
    """Used by the n8n SLA watchdog to find parts waiting too long."""
    try:
        minutes = float(request.query_params.get("older_than_minutes", 0))
    except ValueError:
        return error(422, "older_than_minutes must be a number")
    items = tickets.pending_older_than(minutes)
    return JSONResponse({"count": len(items), "items": items})


async def decide(request: Request):
    """A desk decides on its part, from the staff console, n8n, or the desk's own system.
    Send {"decision": "approve" | "request_change" | "reject", "staff": ..., "reason": ...}
    (the older {"approve": true/false} form still works)."""
    if not authorised(request):
        return error(401, "Missing or wrong X-Munjiz-Token header")
    data = await body_json(request)
    usage = ('Send JSON like {"decision": "approve", "staff": "logistics.officer"} or '
             '{"decision": "request_change", "staff": "security.officer", "reason": "ID could not be verified"}')
    if data is None or not data.get("staff"):
        return error(422, usage)
    outcome = data.get("decision")
    if outcome is None and isinstance(data.get("approve"), bool):
        outcome = "approve" if data["approve"] else "reject"
    if outcome not in tickets.OUTCOMES:
        return error(422, usage)
    try:
        ticket = tickets.decide(request.path_params["sub_id"], staff=str(data["staff"]),
                                reason=str(data.get("reason") or ""), outcome=outcome)
    except ValueError as exc:
        return error(409, str(exc))
    return JSONResponse({"ticket_id": ticket["id"], "ticket_status": ticket["status"],
                         "subs": {s["id"]: s["status"] for s in ticket["subs"]}})


async def sla_sweep(request: Request):
    """Called by the n8n SLA watchdog: sends each overdue part one reminder, then one escalation."""
    if not authorised(request):
        return error(401, "Missing or wrong X-Munjiz-Token header")
    result = tickets.sla_sweep()
    return JSONResponse({**result, "count": len(result["reminders"]) + len(result["escalations"])})


async def desk_inbox(request: Request):
    """Mock desk system: receives its part from n8n and returns its own reference number."""
    desk = request.path_params["desk"]
    if desk not in DESK_SYSTEM:
        return error(404, f"Unknown desk {desk}")
    if request.method == "GET":
        with connect() as conn:
            rows = conn.execute("SELECT id, ticket_id, status, desk_ref FROM sub_requests"
                                " WHERE desk=? AND desk_ref IS NOT NULL ORDER BY rowid DESC", (desk,))
            return JSONResponse([row(r) for r in rows])
    if not authorised(request):
        return error(401, "Missing or wrong X-Munjiz-Token header")
    data = await body_json(request)
    if data is None or not data.get("sub_id"):
        return error(422, 'Send JSON like {"sub_id": "LOG-1001", "ticket_id": "MNJ-1001"}')
    desk_ref = f"{DESK_SYSTEM[desk]}-{str(data['sub_id']).split('-')[-1]}"
    try:
        receipt = tickets.record_desk_receipt(desk, data["sub_id"], desk_ref)
    except ValueError as exc:
        return error(404, str(exc))
    return JSONResponse({"accepted": True, **receipt})


app = Starlette(routes=[
    Route("/health", health),
    Route("/api/tickets", list_tickets),
    Route("/api/tickets/{ticket_id}", get_ticket),
    Route("/api/subrequests/pending", pending),
    Route("/api/subrequests/{sub_id}/decision", decide, methods=["POST"]),
    Route("/api/sla/sweep", sla_sweep, methods=["POST"]),
    Route("/mock/desks/{desk}/inbox", desk_inbox, methods=["GET", "POST"]),
])
