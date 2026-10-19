"""Builds the n8n workflow files in n8n/workflows/ (import them into n8n, or run scripts/n8n_setup.sh).

python n8n/make_workflows.py

1. Munjiz · Route ticket to desks   webhook munjiz-events: routes each desk's part (and every corrected version
                                    of a part) to that desk's system, alerts the desk, tells the participant about
                                    decisions, and sends SLA reminders to desks and escalations to the supervisor.
2. Munjiz · SLA watchdog            every 5 min: asks Munjiz to run the SLA sweep (each overdue part gets one
                                    reminder, then one escalation); the alerts come back through workflow 1.
3. Munjiz · Desk decision intake    webhook desk-decision: lets a desk approve, request a change or reject from
                                    its own tools.
"""
import json
import uuid
from pathlib import Path

OUT = Path(__file__).parent / "workflows"
API = "{{ $env.MUNJIZ_API_URL }}"
TOKEN_HEADER = {"parameters": [{"name": "X-Munjiz-Token", "value": "={{ $env.MUNJIZ_API_TOKEN }}"}]}
DESKS = [("logistics", "Logistics & Site Access", "Gate booking system"),
         ("security", "Accreditation & Security", "Accreditation system"),
         ("facilities", "Facilities & Utilities", "Utilities work orders")]


def nid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"munjiz/{name}"))


def node(name, type_, version, pos, params, **extra):
    return {"id": nid(name), "name": name, "type": f"n8n-nodes-base.{type_}", "typeVersion": version,
            "position": list(pos), "parameters": params, **extra}


def equals(left: str, right: str) -> dict:
    return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"id": nid(left + right), "leftValue": left, "rightValue": right,
                            "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and"}


def switch(name, pos, field, cases):
    return node(name, "switch", 3, pos, {
        "rules": {"values": [{"conditions": equals(field, value), "renameOutput": True, "outputKey": label}
                             for value, label in cases]},
        "options": {}})


def code(name, pos, js, per_item=False):
    params = {"jsCode": js}
    if per_item:
        params["mode"] = "runOnceForEachItem"
    return node(name, "code", 2, pos, params)


def http(name, pos, method, url, json_body=None, query=None):
    params = {"method": method, "url": url, "sendHeaders": True, "headerParameters": TOKEN_HEADER, "options": {}}
    if json_body:
        params.update({"sendBody": True, "specifyBody": "json", "jsonBody": json_body})
    if query:
        params.update({"sendQuery": True, "queryParameters": {"parameters": [{"name": k, "value": v} for k, v in query.items()]}})
    return node(name, "httpRequest", 4.2, pos, params)


def noop(name, pos, note):
    return node(name, "noOp", 1, pos, {}, notes=note, notesInFlow=True)


def link(*pairs):
    """pairs: (from, to) or (from, to, output_index)."""
    conns = {}
    for p in pairs:
        src, dst, idx = (p + (0,))[:3]
        outs = conns.setdefault(src, {"main": []})["main"]
        while len(outs) <= idx:
            outs.append([])
        outs[idx].append({"node": dst, "type": "main", "index": 0})
    return conns


def workflow(wid, name, nodes, connections, tags=()):
    return {"id": wid, "name": name, "nodes": nodes, "connections": connections, "active": False,
            "settings": {"executionOrder": "v1", "timezone": "Asia/Riyadh"}, "pinData": {},
            "meta": {"templateCredsSetupCompleted": True}, "tags": []}


# --- 1. Route ticket to desks --------------------------------------------------------------------
SPLIT_JS = """// One item per desk part, carrying the ticket fields each desk needs.
const body = $input.first().json.body;
return body.sub_requests.map((part) => ({
  json: { ...part, ticket_id: body.ticket_id, pavilion: body.pavilion, language: body.language },
}));"""

DESK_ALERT_JS = """// Alert text for the desk team, with a one-click link back to Munjiz.
const part = $('One item per desk part').item.json;
return {
  json: {
    desk: part.desk_title,
    desk_ref: $json.desk_ref,
    text: `New ${part.desk_title} request ${part.id} from ${part.pavilion} (ref ${$json.desk_ref}): ${part.summary}`,
    decision_url: part.decision_url,
  },
};"""

PARTICIPANT_JS = """// Update for the participant, in the language they wrote in.
const b = $input.first().json.body;
const desks = { logistics: 'Logistics & Site Access', security: 'Accreditation & Security', facilities: 'Facilities & Utilities' };
const desksAr = { logistics: 'اللوجستيات ودخول الموقع', security: 'الاعتماد والأمن', facilities: 'المرافق والخدمات' };
const ar = b.language === 'ar';
let text;
if (b.event === 'ticket_completed') {
  text = ar ? `طلبك ${b.ticket_id} منجز. وافقت جميع الجهات.`
            : `Your request ${b.ticket_id} is done. All desks approved in ${b.minutes_to_complete} min.`;
} else if (b.status === 'approved') {
  text = ar ? `${desksAr[b.desk]} وافقت على جزء من طلبك ${b.ticket_id}.` : `${desks[b.desk]} approved its part of ${b.ticket_id}.`;
} else if (b.status === 'changes_requested') {
  text = ar ? `${desksAr[b.desk]} تطلب تعديل جزئها من ${b.ticket_id}: ${b.reason}. افتح منجز وأرسل التصحيح لهذا الجزء فقط.`
            : `${desks[b.desk]} asks for a change to its part of ${b.ticket_id}: ${b.reason}. Open Munjiz and fix that part only.`;
} else {
  text = ar ? `${desksAr[b.desk]} تحتاج تعديلًا على ${b.ticket_id}: ${b.reason}` : `${desks[b.desk]} needs a change on ${b.ticket_id}: ${b.reason}`;
}
return [{ json: { to: b.pavilion, ticket_id: b.ticket_id, channel: 'Expo app push', text } }];"""

SLA_JS = """// SLA alert: a reminder goes to the desk, an escalation goes to the supervisor.
const b = $input.first().json.body;
const desks = { logistics: 'Logistics & Site Access', security: 'Accreditation & Security', facilities: 'Facilities & Utilities' };
const escalated = b.event === 'sla_escalated';
return [{ json: {
  to: escalated ? 'Participant services supervisor' : `${desks[b.desk]} desk`,
  sub_id: b.id, ticket_id: b.ticket_id,
  text: escalated
    ? `Escalated: ${b.id} for ${b.pavilion} has waited ${b.waiting_minutes} min at ${desks[b.desk]} (escalation target ${b.escalate_minutes} min).`
    : `Reminder: ${b.id} for ${b.pavilion} has waited ${b.waiting_minutes} min (target ${b.review_minutes} min). Please review.`,
} }];"""

route_nodes = [
    node("Munjiz event", "webhook", 2, (0, 300), {"httpMethod": "POST", "path": "munjiz-events",
                                                  "responseMode": "onReceived", "options": {}},
         webhookId=nid("webhook-munjiz-events")),
    switch("Which event?", (240, 300), "={{ $json.body.event }}",
           [("ticket_submitted", "Ticket submitted"), ("sub_decided", "Desk decided"), ("ticket_completed", "Ticket done"),
            ("sub_resubmitted", "Part fixed and resent"), ("sla_reminder", "SLA reminder"),
            ("sla_escalated", "SLA escalation")]),
    code("One item per desk part", (480, 140), SPLIT_JS),
    switch("Which desk?", (720, 140), "={{ $json.desk }}", [(d, title) for d, title, _ in DESKS]),
]
for i, (desk, title, system) in enumerate(DESKS):
    route_nodes.append(http(system, (980, 0 + i * 140), "POST", f"={API}/mock/desks/{desk}/inbox",
                            json_body="={{ JSON.stringify({ sub_id: $json.id, ticket_id: $json.ticket_id, summary: $json.summary }) }}"))
route_nodes += [
    code("Compose desk alert", (1240, 140), DESK_ALERT_JS, per_item=True),
    noop("Notify desk team", (1480, 140), "Connect Slack, Teams or email here"),
    code("Compose participant update", (480, 440), PARTICIPANT_JS),
    noop("Send to participant", (720, 440), "Connect Expo app push or WhatsApp here"),
    code("Compose SLA alert", (480, 620), SLA_JS),
    noop("Alert desk or supervisor", (720, 620), "Connect Slack, Teams or email here"),
]
route = workflow("MunjizRouteDesks", "Munjiz · Route ticket to desks", route_nodes, link(
    ("Munjiz event", "Which event?"),
    ("Which event?", "One item per desk part", 0),
    ("Which event?", "Compose participant update", 1),
    ("Which event?", "Compose participant update", 2),
    ("Which event?", "One item per desk part", 3),
    ("Which event?", "Compose SLA alert", 4),
    ("Which event?", "Compose SLA alert", 5),
    ("One item per desk part", "Which desk?"),
    *[("Which desk?", system, i) for i, (_, _, system) in enumerate(DESKS)],
    *[(system, "Compose desk alert") for _, _, system in DESKS],
    ("Compose desk alert", "Notify desk team"),
    ("Compose participant update", "Send to participant"),
    ("Compose SLA alert", "Alert desk or supervisor"),
))

# --- 2. SLA watchdog -----------------------------------------------------------------------------
# Munjiz owns the SLA state (one reminder, then one escalation per part), so n8n only triggers the sweep.
# The alerts it produces arrive as sla_reminder / sla_escalated events in workflow 1.
watch = workflow("MunjizSlaWatchdog", "Munjiz · SLA watchdog", [
    node("Every 5 minutes", "scheduleTrigger", 1.2, (0, 200), {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}}),
    node("Run now", "manualTrigger", 1, (0, 380), {}),
    http("Run the SLA sweep in Munjiz", (260, 280), "POST", f"={API}/api/sla/sweep"),
], link(
    ("Every 5 minutes", "Run the SLA sweep in Munjiz"),
    ("Run now", "Run the SLA sweep in Munjiz"),
))

# --- 3. Desk decision intake ---------------------------------------------------------------------
decision = workflow("MunjizDeskDecision", "Munjiz · Desk decision intake", [
    node("Desk decision", "webhook", 2, (0, 200), {"httpMethod": "POST", "path": "desk-decision",
                                                   "responseMode": "lastNode", "options": {}},
         webhookId=nid("webhook-desk-decision")),
    http("Record decision in Munjiz", (260, 200), "POST",
         f"={API}/api/subrequests/{{{{ $json.body.sub_id }}}}/decision",
         # Passed through as sent: a body with neither decision nor approve gets a 422 from Munjiz, never a rejection.
         json_body="={{ JSON.stringify({ decision: $json.body.decision, approve: $json.body.approve, staff: $json.body.staff, reason: $json.body.reason || '' }) }}"),
], link(("Desk decision", "Record decision in Munjiz")))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for wf, fname in [(route, "munjiz_route_ticket.json"), (watch, "munjiz_sla_watchdog.json"),
                      (decision, "munjiz_desk_decision.json")]:
        (OUT / fname).write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
        print("wrote", OUT / fname)
