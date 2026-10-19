"""Participant side: Munjiz as a feature inside the Expo 2030 Riyadh mobile app (concept mock-up), with a live
agent trace for the presenter.

The phone is a hand-built mobile UI (components/phone/index.html) talking to this page through Streamlit's
component bridge: it sends "send" / "confirm" / "new" events, and this page sends back the conversation,
desk cards and live ticket. The signed-in participant only ever sees their own pavilion's tickets.
"""
import html
from datetime import datetime

import streamlit as st

from munjiz import chat, config, conflicts, expo, osaka, tickets
from munjiz.agent import run_fix, run_turn
from munjiz.chat import is_yes, wants_fix
from munjiz.i18n import detect_lang, fmt_dt, t
from munjiz.tickets import RETURNED
from views.common import STATUS, badge, desk_cards, desk_icon, desk_title, duration, icon, md_bold, rule_count
from views.admin_phone import admin_data, admin_phone
from views.admin_phone import decide as admin_decide
from views.phone_component import phone

CONFLICT_DEMO = ("Our truck brings LED screens the day after tomorrow at 2 am, plate ABC 1234. Two workers come with "
                 "it: Ahmed Ali, ID 1023456789 and John Smith, passport P1234567. The screens need 30 kW of power.")
DEMO = [
    ("1. Request", "I need to bring display equipment into our pavilion tomorrow at 10 pm. Two workers will come with the truck, and the screens need extra power."),
    ("2. Answer", "Plate is ABC 1234. Workers: Ahmed Ali, ID 1023456789 and John Smith, passport P1234567. The screens need 40 kW."),
    ("1. طلب", "أحتاج إدخال معدات عرض إلى جناحنا بكرة الساعة 10 مساءً. بيجي عاملين مع الشاحنة، والشاشات تحتاج كهرباء إضافية."),
    ("2. رد", "لوحة الشاحنة أ ب ج 1234. العمال: محمد العتيبي هوية 1023456789، وخالد الشمري هوية 2098765432. والشاشات تحتاج 40 كيلوواط."),
    ("Rule demo", "We're bringing furniture by truck tomorrow at 3 pm, plate ABC 1234."),
    ("Clash demo", CONFLICT_DEMO),
]
FIX_DEMO = [("Fix: new passport", "John Smith's passport is P7654321"),
            ("Fix: Arabic ID", "رقم هوية خالد الشمري 2012345678")]
INTRO = {"summary": "summary_intro", "followup": "followup_intro", "problems": "problems_intro",
         "conflict": "conflicts_intro", "fix_summary": "fix_summary_intro"}
CARD_STATE = {"ok": {"en": "Ready", "ar": "جاهز"}, "missing": {"en": "Needs info", "ar": "ينقصه معلومات"},
              "blocked": {"en": "Rule", "ar": "مخالفة قاعدة"},
              "conflict": {"en": "Clash between desks", "ar": "تعارض بين الجهات"}}

ss = st.session_state
user = ss.user
for key, default in {"conv": [], "result": None, "ticket_id": None, "started_at": None, "force": None,
                     "last_event": None, "contact": expo.ROLES[2], "backend": config.BACKEND,
                     "patch": {}, "conflicts_seen": set(), "fix_msgs": [], "fix_patch": {}, "announced": set(),
                     "resume_checked": False, "last_admin_event": None, "show_admin": True}.items():
    ss.setdefault(key, default)
ss.pavilion = user["pavilion"]  # a participant only acts for their own pavilion


# --- Conversation state ---------------------------------------------------------------------------
def lang() -> str:
    return ss.result.language if ss.result else "en"


def reset():
    ss.conv, ss.result, ss.ticket_id, ss.started_at = [], None, None, None
    ss.patch, ss.conflicts_seen, ss.fix_msgs, ss.fix_patch, ss.announced = {}, set(), [], {}, set()
    ss.resume_checked = True  # an explicit new request: never jump back to a waiting ticket by itself
    ss.force = {"screen": "chat", "nonce": datetime.now().timestamp()}


def sync_ticket():
    """The chat only ever holds this pavilion's ticket: a stale id (after Reset demo, or another pavilion's) is
    dropped with its conversation. A ticket waiting for a fix is picked up once per sign-in (or browser refresh)."""
    tid = chat.session_ticket(ss.pavilion, ss.ticket_id, auto_resume=not ss.resume_checked and not ss.conv)
    ss.resume_checked = True
    if ss.ticket_id and tid != ss.ticket_id:
        reset()
    elif tid:
        ss.ticket_id = tid


def my_ticket() -> dict | None:
    return tickets.get_ticket_for(ss.ticket_id, ss.pavilion) if ss.ticket_id else None


def resume(ticket_id: str):
    """ "Continue fixing MNJ-…": open a ticket of this pavilion that waits for a fix."""
    if ticket_id == ss.ticket_id:
        ss.force = {"screen": "chat", "nonce": datetime.now().timestamp()}
    elif chat.session_ticket(ss.pavilion, ticket_id, auto_resume=False):
        reset()
        ss.ticket_id = ticket_id  # announce_returns() then asks for the part that came back


def returned_parts() -> list[dict]:
    ticket = my_ticket()
    return [s for s in ticket["subs"] if s["status"] in RETURNED] if ticket else []


def remember(result):
    ss.conflicts_seen |= {c.check_id for c in result.blocking_conflicts}


def reply_kind(result, cards) -> str:
    if result.fixing and result.ready:
        return "fix_summary"
    if result.ready:
        return "summary"
    if any(c["missing"] for c in cards):
        return "followup"
    if any(c["problems"] for c in cards if c["desk"] != "cross_desk"):
        return "problems"
    return "conflict" if result.blocking_conflicts else ("problems" if cards else "plain")


def add_reply(result, prefix: str = ""):
    cards = desk_cards(result) if result.checks else []
    kind = reply_kind(result, cards) if cards else "plain"
    msg = {"role": "assistant", "content": (prefix + "\n\n" if prefix else "") + result.reply, "lang": result.language,
           "kind": kind, "cards": cards, "prefix": prefix, "notes": result.notes, "waiting": result.waiting}
    if result.fix_patch and not result.ready:
        msg["actions"] = [t("apply_fix_action", result.language)]
    ss.conv.append(msg)


def submit():
    if not (ss.result and ss.result.ready) or ss.ticket_id:
        return
    ss.ticket_id = tickets.submit(ss.result, ss.pavilion, ss.contact, ss.conv, started_at=ss.started_at,
                                  conflicts_caught=len(ss.conflicts_seen))
    ss.conv.append({"role": "assistant", "content": t("submitted", lang(), ticket=ss.ticket_id), "lang": lang(),
                    "kind": "submitted"})


def send_fix():
    """The participant confirmed the corrected part(s): each part that changed goes back to its desk as a new
    version. A part still waiting for its fix stays with the participant."""
    result = ss.result
    ticket = my_ticket()
    if not (result and result.fixing and result.ready and ticket):
        return
    by_desk = {s["desk"]: s for s in ticket["subs"]}
    for desk, check in result.checks.items():
        sub = by_desk[desk]
        try:
            ticket = tickets.resubmit(sub["id"], check)
        except ValueError:
            continue
        version = next(s["version"] for s in ticket["subs"] if s["id"] == sub["id"])
        ss.conv.append({"role": "assistant", "lang": result.language, "kind": "plain",
                        "content": t("fix_sent", result.language, desk=desk_title(desk, result.language),
                                     sub=sub["id"], version=version, ticket=ticket["id"])})
    ss.result, ss.fix_msgs, ss.fix_patch = None, [], {}


def handle(message: str):
    sync_ticket()
    if ss.ticket_id:
        handle_fix(message)
        return
    if ss.result and ss.result.ready and is_yes(message):
        submit()
        return
    ss.started_at = ss.started_at or config.now()
    ss.conv.append({"role": "user", "content": message, "lang": detect_lang(message)})
    prefix = ""
    if ss.result and ss.result.fix_patch and not ss.result.ready and wants_fix(message):
        for desk, fields in ss.result.fix_patch.items():
            ss.patch.setdefault(desk, {}).update(fields)
        prefix = t("fix_applied", detect_lang(message))
    try:
        result = run_turn(ss.conv, ss.pavilion, backend=ss.backend, patch=ss.patch)
    except Exception as exc:  # Claude unreachable on stage: fall back to the offline parser
        st.toast(f"Claude unavailable ({type(exc).__name__}); using offline parser", icon=":material/warning:")
        result = run_turn(ss.conv, ss.pavilion, backend="local", patch=ss.patch)
    ss.result = result
    remember(result)
    add_reply(result, prefix)


def handle_fix(message: str):
    """After submission: the participant answers a desk that sent a part back."""
    returned = returned_parts()
    if not returned:
        return
    if ss.result and ss.result.fixing and ss.result.ready and is_yes(message):
        send_fix()
        return
    ss.conv.append({"role": "user", "content": message, "lang": detect_lang(message)})
    prefix = ""
    if ss.result and ss.result.fixing and ss.result.fix_patch and wants_fix(message):
        for desk, fields in ss.result.fix_patch.items():
            ss.fix_patch.setdefault(desk, {}).update(fields)
        prefix = t("fix_applied", detect_lang(message))
    else:
        ss.fix_msgs.append(message)
    ticket = my_ticket()
    ids = [s["id"] for s in returned]
    try:
        result = run_fix(ticket, ids, ss.fix_msgs, ss.conv, backend=ss.backend, patch=ss.fix_patch)
    except Exception as exc:
        st.toast(f"Claude unavailable ({type(exc).__name__}); using offline parser", icon=":material/warning:")
        result = run_fix(ticket, ids, ss.fix_msgs, ss.conv, backend="local", patch=ss.fix_patch)
    ss.result = result
    add_reply(result, prefix)


def announce_returns():
    """When a desk sends a part back, Munjiz says so in the chat and asks only for that part."""
    ticket = my_ticket()
    if not ticket:
        return
    lang_ = ticket["language"] or "en"
    approved = sum(s["status"] == "approved" for s in ticket["subs"])
    for s in ticket["subs"]:
        key = (s["id"], s["version"])
        if s["status"] in RETURNED and key not in ss.announced:
            ss.announced.add(key)
            ss.result, ss.fix_msgs, ss.fix_patch = None, [], {}
            ss.conv.append({"role": "assistant", "lang": lang_, "kind": "returned", "content": t(
                "part_returned", lang_, desk=desk_title(s["desk"], lang_), sub=s["id"], reason=s["reason"] or "—",
                approved=t("approved_kept", lang_, n=approved) if approved else "")})
            ss.force = {"screen": "chat", "nonce": datetime.now().timestamp()}


def send_demo(msg: str):
    handle(msg)
    ss.force = {"screen": "chat", "nonce": datetime.now().timestamp()}


# --- What the phone shows -------------------------------------------------------------------------
def phone_message(m: dict, last: bool) -> dict:
    lang_, kind = m.get("lang", "en"), m.get("kind", "plain")
    out = {"role": "user" if m["role"] == "user" else "bot", "text": m["content"], "dir": "rtl" if lang_ == "ar" else "ltr",
           "anchor": kind == "submitted", "returned": kind == "returned"}
    if m["role"] != "user" and m.get("cards") and kind in INTRO:
        intro = "fix_summary_intro_many" if kind == "fix_summary" and len(m["cards"]) > 1 else INTRO[kind]
        out["intro"] = "\n\n".join([x for x in [m.get("prefix")] + m.get("notes", []) if x] + [t(intro, lang_)])
        outro = (t("summary_outro", lang_) if kind == "summary" else t("fix_summary_outro", lang_)
                 if kind == "fix_summary" else t("apply_fix_question", lang_) if m.get("actions") else "")
        out["outro"] = "\n\n".join([x for x in m.get("waiting", []) + [outro] if x])
        out["cards"] = [{
            "icon": c["icon"], "title": c["title"], "state": c["state"],
            "state_label": CARD_STATE[c["state"]][lang_], "notes": c["notes"] + [f"✅ {f}" for f in c.get("fixes", [])],
            "body": md_bold(c["detail"]) if c["state"] == "ok"
            else "<br>".join("• " + html.escape(x) for x in c["missing"] + c["problems"]),
        } for c in m["cards"]]
    if last and m.get("actions"):
        out["actions"] = m["actions"]
    return out


def phone_ticket(ticket: dict) -> dict:
    lang_ = ticket["language"] or "en"
    ar = lang_ == "ar"
    from munjiz.rules import load_rules
    rules = load_rules()
    created = datetime.fromisoformat(ticket["created_at"])
    started = datetime.fromisoformat(ticket["started_at"] or ticket["created_at"])
    end = datetime.fromisoformat(ticket["closed_at"]) if ticket["closed_at"] else config.now()
    approved = sum(s["status"] == "approved" for s in ticket["subs"])
    subs = []
    for s in ticket["subs"]:
        version = f' · v{s["version"]}' if (s.get("version") or 1) > 1 else ""
        if s["status"] == "pending":
            who = f'{s["id"]}{version} · ' + (f'{s["desk_ref"]} · ' if s.get("desk_ref") else "") + (
                "بانتظار مراجعة الموظف" if ar else "waiting for desk review")
        else:
            who = f'{s["id"]}{version} · {s["decided_by"]} · {fmt_dt(s["decided_at"], lang_)}'
            if s.get("reason"):
                who += f' · {s["reason"]}'
        subs.append({"id": s["id"], "icon": rules[s["desk"]]["icon"], "title": rules[s["desk"]]["title"][lang_],
                     "status": s["status"], "label": STATUS[s["status"]][lang_], "who": who})
    foot = (f"{duration((created - started).total_seconds(), lang_)} " + ("حتى الإرسال" if ar else "to submit")
            + " · " + (("أُنجز خلال " if ar else "done in ") if ticket["closed_at"] else ("مفتوحة منذ " if ar else "open for "))
            + duration((end - created).total_seconds(), lang_)
            + f" · {approved}/{len(subs)} " + ("موافقات" if ar else "approved"))
    done = ""
    if ticket["status"] == "completed":
        done = "تمت موافقة جميع الجهات. طلبك منجز." if ar else "All desks approved. Your request is done."
    return {"id": ticket["id"], "status": ticket["status"], "label": STATUS[ticket["status"]][lang_],
            "dir": "rtl" if ar else "ltr", "one": "تذكرة واحدة" if ar else "One ticket", "subs": subs,
            "foot": foot, "done": done,
            "fix": t("fix_this_request", lang_) if ticket["status"] in ("partially_approved", "action_needed") else ""}


def phone_data() -> dict:
    now = config.now()
    mine = [tickets.get_ticket(x["id"]) for x in tickets.list_tickets(ss.pavilion)]
    mine = [m for m in mine if m]
    current = my_ticket()
    fixing = bool(current and any(s["status"] in RETURNED for s in current["subs"]))
    r = ss.result
    ready = bool(r and r.ready and (not ss.ticket_id or r.fixing))
    if r and r.fixing:
        names = " + ".join(desk_title(d, lang()) for d in r.checks)
        confirm = f"إرسال التصحيح إلى {names}" if lang() == "ar" else f"Send the fix to {names}"
    else:
        n_desks = len(r.checks) if r else 0
        confirm = f"تأكيد وإرسال إلى {n_desks} جهات" if lang() == "ar" else f"Confirm and send to {n_desks} desks"
    name = ss.pavilion.replace(" (example)", "")
    return {
        "clock": f"{now:%H:%M}", "expo_day": expo.expo_day(now) or "—", "days": expo.DAYS,
        "pavilion": name, "pavilion_type": expo.PARTICIPANTS[ss.pavilion], "role": ss.contact,
        "initials": "".join(w[0] for w in name.split()[:2]).upper(),
        "messages": [phone_message(m, i == len(ss.conv) - 1) for i, m in enumerate(ss.conv)],
        "ready": ready, "confirm_label": confirm, "fixing": fixing,
        "ticket": phone_ticket(current) if current else None,
        "tickets": [{"id": tk["id"], "status": tk["status"], "label": STATUS[tk["status"]]["en"],
                     "text": tk["request_text"], "subs": [s["status"] for s in tk["subs"]]} for tk in mine],
        "all_tickets": {tk["id"]: phone_ticket(tk) for tk in mine},
        "open_count": sum(tk["status"] != "completed" for tk in mine),
        "force": ss.force,
    }


if ss.show_admin:  # stage view: the participant's phone and an Expo Admin phone side by side
    phone_col, admin_col, panel = st.columns([1, 1, 1.05], gap="medium")
else:
    phone_col, panel = st.columns([1, 1.15], gap="large")

with phone_col:
    @st.fragment(run_every="2s")
    def phone_fragment():
        before = len(ss.conv)
        sync_ticket()
        announce_returns()
        event = phone(data=phone_data(), key="munjiz_phone", default=None)
        if event and event.get("nonce") != ss.last_event:
            ss.last_event = event["nonce"]
            if event["action"] == "send":
                handle(event["text"])
            elif event["action"] == "confirm":
                send_fix() if ss.result and ss.result.fixing else submit()
            elif event["action"] == "new":
                reset()
            elif event["action"] == "resume":
                resume(event["text"])
            st.rerun()  # whole page, so the agent trace updates at once
        if len(ss.conv) != before:
            st.rerun()

    phone_fragment()

if ss.show_admin:
    with admin_col:
        @st.fragment(run_every="2s")
        def admin_fragment():
            event = admin_phone(data=admin_data(), key="munjiz_admin_phone", default=None)
            if event and event.get("nonce") != ss.last_admin_event:
                ss.last_admin_event = event["nonce"]
                if admin_decide(event):
                    st.rerun()  # whole page, so the participant's ticket and the trace update at once

        admin_fragment()

# --- Presenter side: the story and the live agent trace ------------------------------------------
with panel:
    st.markdown('<div class="lead">' + badge('<span class="dot"></span>Live demo · Participant app' + (' + Expo Admin' if ss.show_admin else ''), "outline")
                + '<h2>One request. One ticket. Done.</h2><div class="ar">طلب واحد. تذكرة واحدة. منجز.</div>'
                '<p>Munjiz lives inside the Expo 2030 Riyadh app. A pavilion team asks once; the agent splits the '
                'request across the service desks, checks each desk\'s rules and the clashes between them, and sends '
                'one ticket. Expo Admin staff decide.</p>'
                + ('<p>Next to it, Expo Admin on a desk officer\'s phone: each desk\'s part lands there the moment the '
                   'participant confirms, and every decision shows on the participant\'s ticket.</p>' if ss.show_admin else '')
                + '</div>', unsafe_allow_html=True)

    @st.fragment(run_every="2s")
    def trace():
        sync_ticket()
        r, tid = ss.result, ss.ticket_id
        ticket = my_ticket()
        followups = sum(1 for m in ss.conv if m.get("kind") == "followup")
        user_msgs = [m for m in ss.conv if m["role"] == "user"]
        desks = list(r.checks) if r and not r.fixing else []
        if ticket:
            desks = [s["desk"] for s in ticket["subs"]]
        n_rules = sum(rule_count(d) for d in desks)
        checks = r.checks.values() if r and not r.fixing else []
        missing = sum(len([i for i in c.blocking if i.kind == "missing"]) for c in checks)
        broken = sum(len([i for i in c.blocking if i.kind == "rule"]) for c in checks)
        clashes = len(r.blocking_conflicts) if r and not r.fixing else 0
        caught = len(ss.conflicts_seen) if not ticket else (ticket.get("conflicts_caught") or 0)
        approved = sum(s["status"] == "approved" for s in ticket["subs"]) if ticket else 0
        returned = [s for s in ticket["subs"] if s["status"] in RETURNED] if ticket else []
        fixed = [s for s in ticket["subs"] if (s.get("version") or 1) > 1] if ticket else []
        desk_ok = bool(ticket) or bool(r and all(c.ok for c in r.checks.values()))
        ready = bool(ticket) or bool(r and r.ready)

        def step(state, title, detail="", chips=()):
            chip_html = "".join(badge((desk_icon(c[0], "i sm") if c[0] else "") + html.escape(c[1]), "outline") for c in chips)
            mark = (icon("circle-check") if state == "done" else '<span class="dot"></span>' if state == "active"
                    else icon("circle", width=1.5))
            return (f'<div class="step {state}"><div class="ic">{mark}</div><div><div class="t">{title}</div>'
                    + (f'<div class="d">{detail}</div>' if detail else "")
                    + (f'<div class="chips">{chip_html}</div>' if chips else "") + "</div></div>")

        lang_name = {"en": "English", "ar": "Arabic"}.get(lang(), "")
        steps = [
            step("done" if user_msgs else "active", "Understands a plain-language request",
                 f"{lang_name} · {len(user_msgs)} message{'s' if len(user_msgs) != 1 else ''}" if user_msgs
                 else "Waiting for the participant's message"),
            step("done" if desks else "pending", "Splits it into one sub-request per desk",
                 f"{len(desks)} desks; shared details (time, pavilion) entered once" if desks else "",
                 [(d, desk_title(d, "en")) for d in desks]),
            step("done" if desk_ok else "active" if r else "pending", "Checks each desk's rules in code",
                 ("all passed" if desk_ok and ticket else
                  (f"{n_rules} rules checked · all passed" if desk_ok else
                   f"{n_rules} rules checked · {missing} detail{'s' if missing != 1 else ''} missing"
                   + (f" · {broken} rule{'s' if broken != 1 else ''} broken" if broken else ""))) if r or ticket else ""),
            step("done" if ready else "active" if desk_ok and r else "pending", "Checks clashes between desks",
                 (f"{conflicts.count()} cross-desk checks · "
                  + (f"{clashes} clash{'es' if clashes != 1 else ''} · fix suggested" if clashes else "no clashes")
                  + (f" · {caught} caught before submission" if caught else "")) if r or ticket else ""),
            step("done" if ready else "active" if r else "pending", "Asks once for what's missing",
                 (f"{followups} follow-up question" + ("s" if followups != 1 else "") if ready
                  else "Waiting for the participant's answer") if r or ticket else ""),
            step("done" if tid else "active" if r and r.ready else "pending", "Participant confirms the summary",
                 "Confirmed" if tid else "Waiting for confirmation" if r and r.ready else ""),
            step("done" if tid else "pending", "Sends everything under one ticket",
                 (f"{tid} · {len(ticket['subs'])} desks notified at once"
                  + (f" · n8n routed {routed} to desk systems" if (routed := sum(1 for s in ticket['subs'] if s.get('desk_ref'))) else ""))
                 if ticket else "",
                 [(None, s["desk_ref"]) for s in ticket["subs"] if s.get("desk_ref")] if ticket else ()),
        ]
        if returned or fixed:
            steps.append(step("active" if returned else "done", "A desk sent a part back; only that part is fixed",
                              (f"{', '.join(s['id'] for s in returned)} waiting for the participant's fix" if returned else
                               f"{', '.join(s['id'] + ' v' + str(s['version']) for s in fixed)} resent · "
                               f"{approved} approved part{'s' if approved != 1 else ''} untouched")))
        steps.append(step("done" if ticket and ticket["status"] == "completed" else "active" if ticket else "pending",
                          "Expo Admin staff decide (a human always decides)",
                          f"{approved} of {len(ticket['subs'])} approved" if ticket else ""))
        st.markdown('<div class="card"><div class="hd"><div><div class="ct">Agent trace</div>'
                    '<div class="cd">What the agent does with each message, as it happens.</div></div>'
                    + badge('<span class="dot"></span>Live', "outline") + '</div>'
                    '<div class="bd steps">' + "".join(steps) + "</div></div>", unsafe_allow_html=True)

    trace()

    st.markdown('<div class="demo-label">Demo scripts <span>· sends the message into the app</span></div>',
                unsafe_allow_html=True)
    # A real Expo 2025 Osaka National Day: this pavilion's own if it held one, else Saudi Arabia's.
    country = ss.pavilion.replace(" Pavilion", "")
    days = osaka.national_days()
    osaka_day = next((d for d in days if d["participant"] == country), next(d for d in days if d["code"] == "SAU"))
    osaka_case = osaka.case(osaka_day)
    fixing_now = bool(returned_parts())
    others_waiting = [w["id"] for w in chat.waiting_for_fix(ss.pavilion) if w["id"] != ss.ticket_id]
    with st.container(key="demo", horizontal=True):
        for label, msg in DEMO:
            st.button(label, key=f"demo_{label}", disabled=bool(ss.ticket_id), on_click=send_demo, args=(msg,))
        for n, msg in enumerate(osaka_case["messages"], 1):
            st.button(f"Osaka case {n}", key=f"demo_osaka_{n}", disabled=bool(ss.ticket_id), on_click=send_demo,
                      args=(msg,))
        if fixing_now:
            for label, msg in FIX_DEMO:
                st.button(label, key=f"demo_{label}", on_click=send_demo, args=(msg,))
        st.button("New request", type="primary", on_click=reset)
        for tid in others_waiting[:3]:  # a desk sent a part back on an earlier request
            st.button(f"Continue fixing {tid}", key=f"resume_{tid}", on_click=resume, args=(tid,))
    st.caption(f"Osaka cases: {osaka_day['participant']} held its National Day at Expo 2025 Osaka on "
               f"{datetime.fromisoformat(osaka_day['osaka_date']):%-d %b %Y} (day {osaka_day['expo_day']}). The "
               "same request, sent to Munjiz two days ahead; crew names and IDs are made up.")
    if fixing_now:
        st.caption("A desk sent a part back. Fix scripts: John Smith's passport (English demo) or "
                   "Khalid Al-Shammari's ID (Arabic demo).")

    with st.expander("Presenter settings"):
        st.markdown(f"Signed in for **{ss.pavilion}** · {expo.PARTICIPANTS[ss.pavilion]}")
        st.selectbox("Role", expo.ROLES, key="contact")
        st.toggle("Show the Expo Admin phone", key="show_admin")
        st.radio("Agent backend", ["local", "claude"], key="backend", horizontal=True,
                 format_func={"local": "Offline parser (free)", "claude": "Claude (API)"}.get)
