"""Expo Admin · organiser: change desk rules without code. Changes apply at once and are logged."""
import re
from itertools import groupby

import pandas as pd
import streamlit as st

from munjiz import rules
from munjiz.agent import desk_title
from munjiz.db import connect, row
from views.common import alert, page_header

user = st.session_state.user
KEY_LABEL = {"hours": "Notice (hours)", "value": "Limit", "start": "From", "end": "Until", "enabled": "Active",
             "review_minutes": "Reminder after (min)", "escalate_minutes": "Escalate after (min)",
             "utility_crew_hours.start": "From", "utility_crew_hours.end": "Until",
             "permit_valid_hours": "Hours"}
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def forget_widgets():
    for k in [k for k in st.session_state if str(k).startswith("r_")]:
        del st.session_state[k]

page_header("Expo Admin · organiser", "Desk rules",
            "Change notice periods, limits, time windows and response targets, or switch a rule off. Munjiz "
            "checks every request against these in code, so a change applies to the next message, with no code "
            "or file edit. Every change is logged.")
alert("Simulated rules", "Modelled on how World Expos usually run participant services. Replace them with "
      "Expo 2030 Riyadh's Special Regulations when available.")

settings = rules.editable_settings()
tabs = st.tabs([desk_title(d, "en") for d in [*rules.DESKS, rules.CROSS]])
for tab, (desk, items) in zip(tabs, groupby(settings, key=lambda s: s["desk"])):
    with tab, st.form(f"rules_{desk}", border=False):
        changes = []
        for rule_id, group in groupby(list(items), key=lambda s: (s["rule_id"], s["rule"])):
            group = list(group)
            st.markdown(f"**{group[0]['rule']}**")
            cols = st.columns(len(group))
            for col, s in zip(cols, group):
                key = f"r_{desk}_{s['rule_id']}_{s['key']}"
                label = KEY_LABEL.get(s["key"], s["key"])
                edited = " (edited)" if s["value"] != s["default"] else ""
                if s["kind"] == "bool":
                    new = col.toggle(label + edited, value=bool(s["value"]), key=key)
                elif s["kind"] == "time":
                    new = col.text_input(label + edited, value=s["value"], key=key, help="24-hour time, HH:MM")
                else:
                    whole = float(s["value"]).is_integer()
                    new = col.number_input(label + edited, value=int(s["value"]) if whole else float(s["value"]),
                                           min_value=0 if whole else 0.0, step=1 if whole else 0.5, key=key,
                                           help=f"Rule file value: {s['default']}")
                if new != s["value"]:
                    changes.append((s, new))
        if st.form_submit_button("Save changes", type="primary"):
            bad = [s for s, v in changes if s["kind"] == "time" and not TIME.match(str(v))]
            if bad:
                st.error("Times must look like 22:00.")
            else:
                for s, v in changes:
                    rules.set_rule(s["desk"], s["rule_id"], s["key"], v, user["id"])
                st.toast(f"Saved {len(changes)} change{'s' if len(changes) != 1 else ''}" if changes else "No changes",
                         icon=":material/check_circle:")
                forget_widgets()
                st.rerun()

st.subheader("Change log")
with connect() as conn:
    log = [row(r) for r in conn.execute(
        "SELECT at, type, detail FROM events WHERE type IN ('rule_changed', 'rules_reset') ORDER BY id DESC LIMIT 50")]
if log:
    st.dataframe(pd.DataFrame([{
        "When": e["at"][:16].replace("T", " "), "By": e["detail"].get("by", ""),
        "Desk": e["detail"].get("desk", "all"), "Rule": e["detail"].get("rule", ""),
        "Setting": KEY_LABEL.get(e["detail"].get("key", ""), e["detail"].get("key", "")),
        "New value": str(e["detail"].get("value", "reset to rule files")),
    } for e in log]), hide_index=True, width="stretch")
else:
    st.caption("No changes yet. Values come straight from the rule files in rules/.")

with st.expander("Reset every rule to the rule files"):
    if st.checkbox("I understand this removes every change above") and st.button("Reset rules"):
        rules.reset_rules(user["id"])
        forget_widgets()
        st.rerun()
