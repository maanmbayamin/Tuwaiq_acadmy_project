import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from munjiz import expo, osaka, simulate, tickets
from munjiz.agent import desk_title
from munjiz.config import DESKS
from munjiz.db import connect
from munjiz.rules import sla
from views.common import ago, alert, kpi_cards, page_header

# shadcn zinc: today in neutral zinc, Munjiz in emerald; one colour per desk.
DESK_COLOR = {"logistics": "#10B981", "security": "#F59E0B", "facilities": "#60A5FA"}
BEFORE, AFTER = "#A1A1AA", "#10B981"
AXIS, GRID, STAGE, FG = "#A1A1AA", "#27272A", "#09090B", "#FAFAFA"
DESK_NAME = {d: desk_title(d, "en") for d in DESKS}


def style(fig: go.Figure, height=320) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=36, b=10), bargap=0.35, bargroupgap=0.08,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
                      font=dict(family="Geist, -apple-system, Segoe UI, sans-serif", size=12, color=AXIS),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      hoverlabel=dict(font_size=12, bgcolor=STAGE, bordercolor=GRID, font_color=FG,
                                      font_family="Geist, -apple-system, sans-serif"))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True, title_standoff=8, title_font_size=12,
                     linecolor=GRID, tickfont_color=AXIS, title_font_color=AXIS)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True, ticksuffix="  ", tickfont=dict(color=FG, size=12))
    fig.update_traces(marker_line_width=0, textfont=dict(color=FG, size=12), constraintext="none", cliponaxis=False,
                      selector=dict(type="bar"))
    return fig


@st.cache_data(ttl=5)
def load():
    with connect() as conn:
        req = pd.read_sql("SELECT * FROM hist_requests", conn)
        steps = pd.read_sql("SELECT * FROM hist_steps", conn)
    return req, steps


page_header("Organiser dashboard", "Where participant requests wait, and what one ticket changes",
            "Expo 2030 Riyadh participant services across Logistics & Site Access, Accreditation & Security and "
            "Facilities & Utilities.")
req, steps = load()
if req.empty or "cross_desk_conflict" not in req or req.cross_desk_conflict.isna().all():
    simulate.generate()
    load.clear()
    req, steps = load()

alert("Simulated data", f"{len(req)} synthetic participant requests, each run through a model of today's process "
      "and of Munjiz. The assumptions are listed at the bottom; replace them with real figures from the organisers.")

# Headline numbers: stat tiles, not charts.
L, M = req.legacy_hours.mean(), req.munjiz_hours.mean()
LP, MP = req.legacy_participant_minutes.mean(), req.munjiz_participant_minutes.mean()
LF, MF = req.legacy_first_time.mean(), req.munjiz_first_time.mean()
kpi_cards([
    {"label": "Time to complete a request", "value": f"{M:.1f} h", "was": f"{L:.1f} h", "change": f"{M / L - 1:.0%}"},
    {"label": "Participant effort", "value": f"{MP:.0f} min", "was": f"{LP:.0f} min", "change": f"{MP / LP - 1:.0%}"},
    {"label": "Complete first time", "value": f"{MF:.0%}", "was": f"{LF:.0%}", "change": f"+{(MF - LF) * 100:.0f} pts"},
    {"label": "Forms per request", "value": "1", "was": f"{req.legacy_forms.mean():.1f}",
     "change": f"{1 / req.legacy_forms.mean() - 1:.0%}"},
])

# Desk response targets (SLA) and clashes between desks.
target_h = {d: sla(d)["review_minutes"] / 60 for d in DESKS}
steps = steps.assign(breach=steps.wait_hours > steps.desk.map(target_h))
breach = steps.groupby("process").breach.mean()
clashes = int(req.cross_desk_conflict.sum())
multi = int((req.desks.str.count(",") > 0).sum())
kpi_cards([
    {"label": "Desk reviews over their response target", "value": f"{breach['munjiz']:.0%}",
     "was": f"{breach['legacy']:.0%}", "change": f"{(breach['munjiz'] - breach['legacy']) * 100:+.0f} pts"},
    {"label": "Clashes between desks caught before submission", "value": f"{clashes}",
     "change": f"{clashes / multi:.0%} of multi-desk requests · today found after approval"},
])

st.subheader("What the last World Expo tells us")
O = expo.OSAKA_2025
st.caption(f"Real figures from Expo 2025 Osaka, Kansai: {O['participants']} countries and regions and "
           f"{O['international_orgs']} international organisations over {O['days']} days. They show how much "
           "participants depend on the service desks, before and during the Expo.")
kpi_cards([
    {"label": "Site passes issued to staff and contractors", "value": f"{O['site_passes']:,}",
     "change": f"{O['site_passes_day']:,} were one-day passes: each one a request to accreditation"},
    {"label": "Self-built pavilions finished on schedule", "value": f"{O['built_on_time']} of {O['type_a_pavilions']}",
     "change": f"target mid-Oct 2024; {O['type_a_done_before_opening']} were done two days before opening"},
    {"label": "Pavilions not ready on opening day", "value": f"{O['not_ready_opening_day']}",
     "change": f"the last one opened {O['last_pavilion_days_late']} days after the Expo did"},
    {"label": "Unpaid construction reports", "value": f"{O['unpaid_construction_reports']}",
     "change": "by Aug 2025; some pavilions were built without the required permits"},
])
riyadh_passes = round(O["site_passes"] * expo.FACTS["expected_participating_countries"] / O["participants"], -3)
st.caption(f"At Osaka's rate per participant, Riyadh's {expo.FACTS['expected_participating_countries']} expected "
           f"countries would need about {riyadh_passes:,.0f} site passes, before any delivery or power request. "
           "Expo 2020 Dubai, the last Expo in the Gulf, had "
           f"{expo.DUBAI_2020['participants']} countries and {expo.DUBAI_2020['visits_millions']} million visits. Sources: "
           + " · ".join(f"[{name}]({url})" for name, url in expo.PRECEDENT_SOURCES))

st.subheader("Osaka 2025 replay")
st.caption("Real data from the last World Expo: staff and contractor entries on site passes, day by day, and the "
           "163 National and Special Days. Each National Day was replayed through Munjiz as that participant's "
           "request for the same day of Expo 2030 Riyadh: equipment the night before, crew passes, power for the "
           "ceremony. Request wording, plates and crew details are generated; dates and participants are real.")


@st.cache_data(show_spinner=False)
def osaka_replay():
    results, skipped = osaka.replay()
    return pd.DataFrame(results), len(skipped)


rep, rep_skipped = osaka_replay()
daily = pd.DataFrame(osaka.daily_attendance())
nd = pd.DataFrame(osaka.national_days()).merge(daily[["expo_day", "staff_entries"]], on="expo_day")
fig = go.Figure([
    go.Scatter(x=daily.date, y=daily.staff_entries, mode="lines", name="Staff and contractor entries",
               line=dict(color=BEFORE, width=2), hovertemplate="%{x}<br>%{y:,} entries<extra></extra>"),
    go.Scatter(x=nd.osaka_date, y=nd.staff_entries, mode="markers", name="National or Special Day",
               marker=dict(color=AFTER, size=8, line=dict(color=STAGE, width=2)), customdata=nd.participant,
               hovertemplate="%{x}<br>%{customdata} National Day<br>%{y:,} entries<extra></extra>"),
])
fig.update_yaxes(title="Entries per day", tickformat=",", gridcolor=GRID, tickfont=dict(color=AXIS))
fig.update_xaxes(title="Expo 2025 Osaka, 13 Apr – 13 Oct 2025", gridcolor="rgba(0,0,0,0)")
st.plotly_chart(style(fig, height=300), width="stretch", theme=None)
ok = rep.ready & rep.on_time & rep.crew_ok & rep.kw_ok
kpi_cards([
    {"label": "Real National Days replayed", "value": f"{len(rep)}",
     "change": f"{rep_skipped} more fell after Riyadh's 182nd day"},
    {"label": "Asked once for what was missing", "value": f"{rep.asked_once.mean():.0%}",
     "change": f"{rep.asked_once.sum()} of {len(rep)} requests"},
    {"label": "Ready for all 3 desks after one answer", "value": f"{ok.mean():.0%}",
     "change": "truck slot, crew passes and kW all read correctly"},
    {"label": "Written in Arabic", "value": f"{(rep.lang == 'ar').sum()}",
     "change": "Arab League participants; the rest in English"},
])
st.caption(f"Peak day at Osaka: {daily.staff_entries.max():,} staff and contractor entries "
           f"({daily.loc[daily.staff_entries.idxmax(), 'date']}). The replay first found a bug in the offline "
           "parser: with \"the day after tomorrow\" and \"tomorrow at 10 pm\" in one message it booked the wrong "
           "day. Fixed and covered by tests/test_osaka_replay.py. Data: datasets/osaka2025, built by "
           "scripts/osaka2025_build.py from the organiser's figures as published on Wikipedia.")

st.subheader("At Expo 2030 Riyadh scale")
s1, s2, s3 = st.columns(3)
participants = s1.number_input("Participating countries", 50, 250, expo.FACTS["expected_participating_countries"],
                               help="Organisers expect 197 participating countries (Swiss Federal Council notice, Apr 2026).")
per_month = s2.number_input("Cross-desk requests per participant per month", 1, 100, 10,
                            help="Assumption. Ask mentors for a real figure.")
months = s3.number_input("Months of build-up and operations", 1, 36, 18,
                         help="Assumption: about 12 months of pavilion build-up plus the 6 months the Expo is open.")
total = participants * per_month * months
reworks = steps.groupby("process").reworked.sum() / len(req)
kpi_cards([
    {"label": "Requests in one window", "value": f"{total:,.0f}", "plain": True},
    {"label": "Participant hours saved", "value": f"{total * (LP - MP) / 60:,.0f}"},
    {"label": "Request-days of waiting removed", "value": f"{total * (L - M) / 24:,.0f}"},
    {"label": "Bounced forms avoided", "value": f"{total * (reworks['legacy'] - reworks['munjiz']):,.0f}"},
])
st.caption("Projection = the simulated per-request savings above × requests at Expo scale. Only the participant "
           "count is a public figure; everything else is an assumption to replace with organiser data.")

left, right = st.columns(2)
with left:
    st.subheader("Completion time, before vs after")
    by_type = req.groupby("request_type")[["legacy_hours", "munjiz_hours"]].mean().sort_values("legacy_hours")
    fig = go.Figure([
        go.Bar(y=by_type.index, x=by_type.legacy_hours, name="Today (3 desks, one by one)", orientation="h",
               marker_color=BEFORE, hovertemplate="%{y}<br>Today: %{x:.1f} h<extra></extra>"),
        go.Bar(y=by_type.index, x=by_type.munjiz_hours, name="Munjiz (one ticket, in parallel)", orientation="h",
               marker_color=AFTER, text=[f"{v:.1f} h" for v in by_type.munjiz_hours], textposition="outside",
               hovertemplate="%{y}<br>Munjiz: %{x:.1f} h<extra></extra>"),
    ])
    fig.update_xaxes(title="Average hours from request to all approvals")
    st.plotly_chart(style(fig), width="stretch", theme=None)

with right:
    st.subheader("Requests by type and desk")
    exploded = req.assign(desk=req.desks.str.split(",")).explode("desk")
    counts = exploded.groupby(["request_type", "desk"]).size().unstack(fill_value=0)
    counts = counts.loc[counts.sum(axis=1).sort_values().index]
    fig = go.Figure([go.Bar(y=counts.index, x=counts[d], name=DESK_NAME[d], orientation="h",
                            marker_color=DESK_COLOR[d],
                            hovertemplate="%{y}<br>" + DESK_NAME[d] + ": %{x} sub-requests<extra></extra>")
                     for d in DESKS if d in counts])
    fig.update_layout(barmode="stack")
    fig.update_traces(marker_line_color=STAGE)  # 2px gap between stacked segments
    fig.update_xaxes(title="Desk sub-requests")
    st.plotly_chart(style(fig).update_traces(marker_line_width=2), width="stretch", theme=None)

left, right = st.columns(2)
with left:
    st.subheader("Bottlenecks: average wait per desk")
    wait = steps.groupby(["desk", "process"]).wait_hours.mean().unstack().sort_values("legacy")
    names = [DESK_NAME[d] for d in wait.index]
    fig = go.Figure([
        go.Bar(y=names, x=wait.legacy, name="Today", orientation="h", marker_color=BEFORE,
               hovertemplate="%{y}<br>Today: %{x:.1f} h<extra></extra>"),
        go.Bar(y=names, x=wait.munjiz, name="Munjiz", orientation="h", marker_color=AFTER,
               text=[f"{v:.1f} h" for v in wait.munjiz], textposition="outside",
               hovertemplate="%{y}<br>Munjiz: %{x:.1f} h<extra></extra>"),
    ])
    fig.update_xaxes(title="Average hours at the desk")
    st.plotly_chart(style(fig, 260), width="stretch", theme=None)
    rework = steps[steps.process == "legacy"].reworked.mean()
    st.caption(f"{names[-1]} is the slowest desk today ({wait.legacy.iloc[-1]:.1f} h on average), and {rework:.0%} "
               "of desk forms bounce back for missing information. Munjiz checks each desk's rules before "
               "anything is sent, and the desks work in parallel.")

with right:
    st.subheader("Live: waiting longest")

    @st.fragment(run_every="5s")
    def live():
        rows = [dict(sub, waiting=ago(sub["created_at"])) for d in DESKS for sub in tickets.desk_queue(d)]
        live_tickets = tickets.list_tickets()
        c = st.columns(3)
        c[0].metric("Demo tickets", len(live_tickets))
        c[1].metric("Completed", sum(t["status"] == "completed" for t in live_tickets))
        c[2].metric("Sub-requests pending", len(rows))
        if rows:
            rows.sort(key=lambda r: r["created_at"])
            st.dataframe(pd.DataFrame([{"Sub-request": r["id"], "Desk": DESK_NAME[r["desk"]],
                                        "Pavilion": r["pavilion"], "Waiting": r["waiting"]} for r in rows[:8]]),
                         hide_index=True, width="stretch")
        else:
            st.caption("No live sub-requests waiting.")

    live()

left, right = st.columns(2)
with left:
    st.subheader("SLA breaches by desk, before vs after")
    by_desk = steps.groupby(["desk", "process"]).breach.mean().unstack().sort_values("legacy")
    names = [f"{DESK_NAME[d]} ({sla(d)['review_minutes']} min)" for d in by_desk.index]
    fig = go.Figure([
        go.Bar(y=names, x=by_desk.legacy, name="Today", orientation="h", marker_color=BEFORE,
               text=[f"{v:.0%}" for v in by_desk.legacy], textposition="outside",
               hovertemplate="%{y}<br>Today: %{x:.0%} of reviews over target<extra></extra>"),
        go.Bar(y=names, x=by_desk.munjiz, name="Munjiz", orientation="h", marker_color=AFTER,
               text=[f"{v:.0%}" for v in by_desk.munjiz], textposition="outside",
               hovertemplate="%{y}<br>Munjiz: %{x:.0%} of reviews over target<extra></extra>"),
    ])
    fig.update_xaxes(title="Share of desk reviews over the desk's response target", tickformat=".0%",
                     range=[0, by_desk.values.max() * 1.18])
    st.plotly_chart(style(fig, 260), width="stretch", theme=None)
    st.caption("Response target per desk in brackets (set on the Desk rules page). Pre-checked parts reach "
               "the desks complete, so they are reviewed well inside the target.")

with right:
    st.subheader("Live: SLA and clashes")

    @st.fragment(run_every="5s")
    def live_sla():
        tickets.sla_sweep()
        waiting = [tickets.sla_info(s) for d in DESKS for s in tickets.desk_queue(d)]
        live = tickets.list_tickets()
        c = st.columns(3)
        c[0].metric("Parts over target now", sum(w["level"] != "on_time" for w in waiting))
        c[1].metric("Escalated to supervisor", sum(w["state"] == "escalated" for w in waiting))
        c[2].metric("Clashes caught live", sum(t.get("conflicts_caught") or 0 for t in live))
        returned = sum(t["status"] in ("partially_approved", "action_needed") for t in live)
        st.caption(f"{returned} demo ticket{'s' if returned != 1 else ''} waiting for a participant fix. "
                   "Each fix goes back as a new version of that part only.")

    live_sla()

with st.expander("Simulation assumptions (replace with organiser figures)"):
    st.dataframe(pd.DataFrame(simulate.ASSUMPTIONS.items(), columns=["Assumption", "Value"]), hide_index=True)
    st.caption("Generated by munjiz/simulate.py with a fixed seed, so the numbers are reproducible.")

with st.expander("Data table"):
    st.dataframe(req, hide_index=True, width="stretch")
