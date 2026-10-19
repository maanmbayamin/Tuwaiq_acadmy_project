import pandas as pd
import streamlit as st

from munjiz import tickets
from views.common import page_header, ticket_card

page_header("Expo Admin · supervisors and organisers", "Ticket tracker",
            "Every ticket, its desk sub-requests and the full event log.")


@st.fragment(run_every="3s")
def board():
    all_tickets = tickets.list_tickets()
    if not all_tickets:
        st.info("No tickets yet. Submit one from the Participant page.")
        return
    full = {t["id"]: tickets.get_ticket(t["id"]) for t in all_tickets}
    st.dataframe(pd.DataFrame([{
        "Ticket": t["id"], "Pavilion": t["pavilion"], "Status": t["status"].replace("_", " "),
        "Desks approved": f"{sum(s['status'] == 'approved' for s in t['subs'])} / {len(t['subs'])}",
        "Follow-ups": t["followups"], "Submitted": t["created_at"][:16].replace("T", " "),
    } for t in full.values()]), hide_index=True, width="stretch")

    chosen = st.selectbox("Open ticket", list(full), key="tracker_pick")
    ticket = full[chosen]
    ticket_card(ticket, ticket["language"] or "en")
    with st.expander("Event log"):
        st.dataframe(pd.DataFrame([{"Time": e["at"][11:19], "Event": e["type"].replace("_", " "),
                                    "Sub-request": e["sub_id"] or "", "Detail": e["detail"]} for e in ticket["events"]]),
                     hide_index=True, width="stretch")


board()

with st.sidebar.expander("Reset demo"):
    st.caption("Deletes demo tickets only. Simulated history stays.")
    if st.checkbox("I understand") and st.button("Delete demo tickets"):
        tickets.reset_live()
        st.rerun()
