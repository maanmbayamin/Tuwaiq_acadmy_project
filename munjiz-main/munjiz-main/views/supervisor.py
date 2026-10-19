"""Expo Admin · supervisor: SLA reminders and escalations across desks, reassign or decide on a desk's behalf."""
import pandas as pd
import streamlit as st

from munjiz import config, tickets, users
from munjiz.agent import desk_title
from munjiz.rules import sla
from views.common import describe_sub, page_header, sla_pill

user = st.session_state.user

page_header("Expo Admin · supervisor", "SLA & escalations",
            "Every desk has a response target. A part that passes it gets one reminder to the desk; if it waits "
            "until the escalation target, it lands here. Reassign it or decide on the desk's behalf.")

targets = pd.DataFrame([{"Desk": desk_title(d, "en"), "Reminder after": f"{sla(d)['review_minutes']} min",
                         "Escalate after": f"{sla(d)['escalate_minutes']} min"} for d in config.DESKS])
with st.expander("Response targets per desk (organisers change them on the Desk rules page)"):
    st.dataframe(targets, hide_index=True, width="stretch")


def reassign(sub_id: str, key: str):
    officer = st.session_state.get(key)
    if officer:
        tickets.reassign(sub_id, officer, user["id"])
        st.toast(f"{sub_id} reassigned to {officer}", icon=":material/person:")


def override(sub_id: str, outcome: str):
    try:
        tickets.decide(sub_id, staff=f"{user['id']} (override)", outcome=outcome,
                       reason="" if outcome == "approve" else "Supervisor: please check the details and re-send")
    except ValueError:
        return
    st.toast(f"{sub_id} {'approved' if outcome == 'approve' else 'sent back'} by supervisor override", icon=":material/shield:")


@st.fragment(run_every="3s")
def board():
    tickets.sla_sweep()
    pending = [(d, s, tickets.sla_info(s)) for d in config.DESKS for s in tickets.desk_queue(d)]
    escalated = [x for x in pending if x[2]["state"] == "escalated"]
    reminded = [x for x in pending if x[2]["state"] == "reminded"]
    c = st.columns(4)
    c[0].metric("Parts waiting at desks", len(pending))
    c[1].metric("Reminders sent", len(reminded))
    c[2].metric("Escalated to you", len(escalated))
    c[3].metric("Oldest wait", f"{max((x[2]['waited_minutes'] for x in pending), default=0):.0f} min")

    def card(desk, sub, info):
        with st.container(border=True, key=f"card_sv_{sub['id']}"):
            st.markdown(f"**{sub['id']}** · {desk_title(desk, 'en')} · ticket `{sub['ticket_id']}` · {sub['pavilion']} "
                        f"&nbsp; {sla_pill(info)}" + (f" · reassigned to **{sub['assigned_to']}**" if sub.get("assigned_to") else ""),
                        unsafe_allow_html=True)
            st.markdown(describe_sub(sub))
            a, b, c2, d = st.columns([2, 1, 1, 1], vertical_alignment="bottom")
            others = [o for o in users.officers(desk) if o != sub.get("assigned_to")]
            a.selectbox("Reassign to", others, key=f"to_{sub['id']}")
            b.button("Reassign", key=f"re_{sub['id']}", on_click=reassign, args=(sub["id"], f"to_{sub['id']}"),
                     width="stretch")
            c2.button("Approve", key=f"ov_ok_{sub['id']}", on_click=override, args=(sub["id"], "approve"),
                      width="stretch", help="Decide on the desk's behalf (recorded as an override)")
            d.button("Send back", key=f"ov_chg_{sub['id']}", on_click=override, args=(sub["id"], "request_change"),
                     width="stretch")

    for title, items, empty in (
            ("Escalated to you", escalated, "Nothing escalated. Parts appear here once they pass their desk's escalation target."),
            ("Reminder sent to the desk", reminded, "No reminders outstanding.")):
        st.subheader(f"{title} ({len(items)})")
        if not items:
            st.caption(empty)
        for desk, sub, info in sorted(items, key=lambda x: -x[2]["waited_minutes"]):
            card(desk, sub, info)

    st.subheader("Waiting now, by desk")
    rows = [{"Desk": desk_title(d, "en"), "Waiting": sum(x[0] == d for x in pending),
             "Over target": sum(x[0] == d and x[2]["level"] != "on_time" for x in pending),
             "Escalated": sum(x[0] == d and x[2]["state"] == "escalated" for x in pending)} for d in config.DESKS]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


board()

with st.expander("Presenter control · SLA demo"):
    st.caption("Demo only: moves every waiting part's clock back, as if it had waited longer, so reminders and "
               "escalations can be shown in a 5-minute pitch.")
    cols = st.columns(3)
    for col, minutes in zip(cols, (60, 150, 300)):
        if col.button(f"+{minutes} min", key=f"age_{minutes}", width="stretch"):
            tickets.age_pending(minutes)
            st.rerun()
