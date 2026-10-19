"""Expo Admin · desk console. Desk staff see only their desk's parts, already checked against the desk's rules
and against the other desks' parts. A person approves, requests a change or rejects."""
import streamlit as st

from munjiz import config, conflicts, tickets
from munjiz.agent import desk_title
from munjiz.rules import check_desk, rule_count
from munjiz.users import DESK_STAFF, SUPERVISOR
from views.admin_phone import CHANGE_REASONS, REJECT_REASONS, worker_reasons
from views.common import ago, describe_sub, desk_icon, icon, page_header, pill, sla_pill

user = st.session_state.user

page_header("Expo Admin · desk staff", "Desk console",
            "Each desk sees only its part of the ticket, already checked against its rules and against the other "
            "desks' parts. The agent prepares; a person decides.")

if user["role"] == DESK_STAFF:
    desk = user["desk"]
    st.markdown(f'<div class="cardtitle">{desk_icon(desk)}{desk_title(desk, "en")}</div>', unsafe_allow_html=True)
else:
    desk = st.segmented_control("Desk", config.DESKS, default="logistics", format_func=lambda d: desk_title(d, "en"),
                                key="staff_desk") or "logistics"
staff = user["id"] if user["role"] == DESK_STAFF else f"{user['id']} (override)"
if user["role"] == SUPERVISOR:
    st.caption("You're signed in as a supervisor: decisions here are recorded as overrides.")


def decide(sub_id: str, outcome: str, reason_key: str = "", note_key: str = ""):
    reason = st.session_state.get(reason_key, "") if reason_key else ""
    note = (st.session_state.get(note_key) or "").strip() if note_key else ""
    if note:
        reason = f"{reason}: {note}" if reason else note
    try:
        tickets.decide(sub_id, staff=staff, reason=reason, outcome=outcome)
    except ValueError:
        return  # already decided (double click or another officer)
    label = {"approve": "approved", "request_change": "sent back for a change", "reject": "rejected"}[outcome]
    st.toast(f"{sub_id} {label}", icon=":material/check_circle:" if outcome == "approve"
             else ":material/undo:" if outcome == "request_change" else ":material/block:")


@st.fragment(run_every="3s")
def queue():
    tickets.sla_sweep()
    pending = tickets.desk_queue(desk)
    st.subheader(f"Pending ({len(pending)})")
    if not pending:
        st.caption("Nothing waiting. New sub-requests appear here as soon as a participant confirms.")
    for sub in pending:
        ticket = tickets.get_ticket(sub["ticket_id"])
        info = tickets.sla_info(sub)
        with st.container(border=True, key=f"card_q_{sub['id']}"):
            version = sub.get("version") or 1
            head = (f"**{sub['id']}** · ticket `{sub['ticket_id']}` · {sub['pavilion']} · "
                    f"submitted {ago(sub.get('submitted_at') or sub['created_at'])} &nbsp; {sla_pill(info)}")
            if version > 1:
                head += f" &nbsp; {pill('pending')} <b>v{version}</b> · corrected by the participant"
            st.markdown(head, unsafe_allow_html=True)
            if sub.get("assigned_to"):
                st.caption(f"Reassigned by the supervisor to {sub['assigned_to']}")
            if info["state"] == "escalated":
                st.error("Escalated to the supervisor: this part has waited past the escalation target.", icon=":material/error:")
            elif info["state"] == "reminded":
                st.warning(f"Reminder: this part has waited past the {info['review_minutes']}-minute target.", icon=":material/schedule:")
            st.markdown(describe_sub(sub))

            recheck = check_desk(desk, sub["payload"], config.now())
            if recheck.ok:
                st.markdown(f'<div class="line ok">{icon("shield-check")}<span>Desk rules: <b>passed</b> '
                            f'<span class="muted">· {rule_count(desk)} checks</span></span></div>', unsafe_allow_html=True)
            else:
                st.warning("Rule check now fails: " + "; ".join(i.message["en"] for i in recheck.blocking))
            clashes = conflicts.check({s["desk"]: s["payload"] for s in ticket["subs"]},
                                      {s["desk"]: s["assigned"] for s in ticket["subs"]})
            mine = [c for c in clashes if desk in c.desks]
            blocking = [c for c in mine if c.blocking]
            if blocking:
                st.warning("Cross-desk clash: " + "; ".join(c.message["en"] for c in blocking), icon=":material/merge:")
            else:
                st.markdown(f'<div class="line ok">{icon("git-merge")}<span>Cross-desk check: <b>no clashes</b> with the '
                            f'other desks\' parts <span class="muted">· {conflicts.count()} checks</span></span></div>',
                            unsafe_allow_html=True)
            if sub.get("desk_ref"):
                st.markdown(f'<div class="line">{icon("link")}<span>Routed by n8n to the desk system '
                            f'<span class="muted">· ref</span> <code>{sub["desk_ref"]}</code></span></div>',
                            unsafe_allow_html=True)
            for note in sub["notes"]:
                st.info(note["en"], icon=":material/info:")

            others = [s for s in ticket["subs"] if s["desk"] != desk]
            st.markdown('<div class="line" style="flex-wrap:wrap;margin-top:8px"><span class="muted">Other desks on this ticket</span>'
                        + "".join(f"<span>{desk_title(s['desk'], 'en')}</span>{pill(s['status'])}" for s in others) + "</div>",
                        unsafe_allow_html=True)
            with st.expander("Participant's original words"):
                st.write(sub["request_text"])

            sid = sub["id"]
            reasons = worker_reasons(sub) + CHANGE_REASONS[desk] if desk == "security" else CHANGE_REASONS[desk]
            c1, c2 = st.columns([1, 3])
            c1.button("Approve", key=f"ok_{sid}", type="primary", on_click=decide, args=(sid, "approve"),
                      width="stretch")
            with c2.popover("Send back to the participant", width="stretch"):
                st.selectbox("What needs to change", reasons + REJECT_REASONS[desk], key=f"why_{sid}")
                st.text_input("Note (optional)", key=f"note_{sid}", placeholder="Shown to the participant")
                b1, b2 = st.columns(2)
                b1.button("Request a change", key=f"chg_{sid}", on_click=decide, width="stretch",
                          args=(sid, "request_change", f"why_{sid}", f"note_{sid}"),
                          help="The participant fixes this part only. Other desks' approvals stay.")
                b2.button("Reject", key=f"no_{sid}", on_click=decide, width="stretch",
                          args=(sid, "reject", f"why_{sid}", f"note_{sid}"),
                          help="This part can't go ahead as asked. The participant can send a new version.")

    done = (tickets.desk_queue(desk, "approved") + tickets.desk_queue(desk, "changes_requested")
            + tickets.desk_queue(desk, "rejected"))
    if done:
        st.subheader("Recently decided")
        for sub in sorted(done, key=lambda s: s["decided_at"], reverse=True)[:8]:
            st.markdown(f"`{sub['id']}` {sub['pavilion']} &nbsp; {pill(sub['status'])} &nbsp; "
                        f"by {sub['decided_by']} {ago(sub['decided_at'])}" + (f" · {sub['reason']}" if sub["reason"] else ""),
                        unsafe_allow_html=True)


queue()
