import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import (ACCENT, ISO3, USD_TO_SAR, convert, global_group, load_benchmark, load_salaries, money, note,
                   page_header, unit)

df = load_salaries()
ksa = load_benchmark()

# Colors for this page
SAUDI = "#2fa37f"        # Saudi Arabia, always the same green
EX_US = "#3987e5"        # global excluding the US
US = "#c98500"           # United States
LESS = "#4a7fb5"         # map: pays less than Saudi Arabia
MORE = "#d39a4c"         # map: pays more than Saudi Arabia
MID = "#8a949e"          # map: about the same (light gray so it differs from "no data")
LAND = "#1c242d"
BORDER = "#0f1419"
TYPE_COLORS = {"Recruiter survey": "#2fa37f", "Crowd-sourced": "#3987e5", "HR platform guide": "#c98500"}

page_header("Saudi Arabia vs the World",
            "How Saudi salaries for data and AI roles compare with the US and the rest of the world.")

st.info("The global dataset has only 2 rows from Saudi Arabia (both remote, mid-level), which is too few to "
        "describe the market. So the Saudi numbers on this page come from 11 benchmark ranges published by "
        "recruiters and salary websites.", icon=":material/info:")


def sar_to_usd_year(v):
    return v * 12 / USD_TO_SAR


def fmt(usd):
    """Full value in the selected currency, for hovers."""
    v = convert(usd)
    return f"{v:,.0f} SAR / month" if unit().startswith("SAR") else f"${v:,.0f} / year"


saudi_role = ksa.groupby("role")["mid_sar_month"].median()
INDIVIDUAL = ["Data Scientist", "Data Analyst", "Data Engineer"]
ALL_IND = "Analyst, Scientist & Engineer"

# =====================================================================
# 1. World map
# =====================================================================
st.subheader("How the world compares to Saudi Arabia")

c1, c2, c3 = st.columns([2, 2, 1.4])
role = c1.selectbox("Role", [ALL_IND] + INDIVIDUAL, key="map_role")
mode = c2.segmented_control("Color the map by", ["Difference vs Saudi", "Median salary"],
                            default="Difference vs Saudi", required=True, key="map_mode")
min_n = c3.number_input("Min. records per country", 3, 50, 5, 1, key="map_min",
                        help="Countries with fewer records are hidden because their median is not reliable.")

roles = INDIVIDUAL if role == ALL_IND else [role]
g = df[df["job_title"].isin(roles)]
saudi_usd = sar_to_usd_year(ksa[ksa["role"].isin(roles)]["mid_sar_month"].median())

stats = g.groupby(["company_location", "company_country"])["salary_in_usd"].agg(["median", "count"]).reset_index()
stats = stats[(stats["count"] >= min_n) & (stats["company_location"] != "SA")]
stats["iso3"] = stats["company_location"].map(ISO3)
stats["diff"] = (stats["median"] / saudi_usd - 1) * 100
stats = pd.concat([stats, pd.DataFrame([{"company_location": "SA", "company_country": "Saudi Arabia",
                                         "median": saudi_usd, "count": None, "iso3": "SAU", "diff": 0.0}])],
                  ignore_index=True)

hover = [
    f"<b>{r.company_country}</b><br>{fmt(r.median)}<br>"
    + ("Saudi benchmark (median of sources)" if r.iso3 == "SAU"
       else f"{r.diff:+.0f}% vs Saudi Arabia<br>{int(r.count)} records")
    for r in stats.itertuples()
]

if mode == "Difference vs Saudi":
    lim = max(100, stats["diff"].abs().max())
    z, zmin, zmax = stats["diff"].clip(-lim, lim), -lim, lim
    scale = [[0, LESS], [0.5, MID], [1, MORE]]
    cbar = dict(title=dict(text="vs Saudi", side="top"), ticksuffix="%", len=0.6, thickness=10, x=1.0)
else:
    z, zmin, zmax = convert(stats["median"]), None, None
    scale = [[0, "#1e3b3a"], [0.35, "#2c5d57"], [0.7, "#3f8277"], [1, "#a8dccd"]]
    cbar = dict(title=dict(text=unit(), side="top"), len=0.6, thickness=10, x=1.0)

fig = go.Figure(go.Choropleth(
    locations=stats["iso3"], z=z, zmin=zmin, zmax=zmax, colorscale=scale, colorbar=cbar,
    text=hover, hovertemplate="%{text}<extra></extra>",
    marker=dict(line=dict(color=BORDER, width=0.6)),
))
# Outline Saudi Arabia and pin it
fig.add_trace(go.Choropleth(locations=["SAU"], z=[0], colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                            showscale=False, marker=dict(line=dict(color=SAUDI, width=2.2)), hoverinfo="skip"))
fig.add_trace(go.Scattergeo(lat=[24.0], lon=[45.0], mode="markers+text", text=["Saudi Arabia"],
                            textposition="bottom center", textfont=dict(color="#e6eaee", size=12),
                            marker=dict(size=11, color=SAUDI, line=dict(color="#e6eaee", width=1.5)),
                            hovertext=[hover[-1]], hovertemplate="%{hovertext}<extra></extra>", showlegend=False))
fig.update_geos(projection_type="natural earth", showframe=False, showcoastlines=False,
                showland=True, landcolor=LAND, showocean=True, oceancolor="rgba(0,0,0,0)",
                showcountries=True, countrycolor=BORDER, showlakes=False, bgcolor="rgba(0,0,0,0)",
                lataxis_range=[-50, 78])
fig.update_layout(height=470, margin=dict(l=0, r=0, t=10, b=0), dragmode="pan")
st.plotly_chart(fig, width="stretch", config={"scrollZoom": True})

others = stats[stats["iso3"] != "SAU"]
more, less = (others["diff"] > 10).sum(), (others["diff"] < -10).sum()
same = len(others) - more - less
k1, k2, k3, k4 = st.columns(4)
k1.metric("Saudi benchmark", money(saudi_usd))
k2.metric("Countries paying more", int(more), help="More than 10% above Saudi Arabia")
k3.metric("About the same", int(same), help="Within 10% of Saudi Arabia")
k4.metric("Countries paying less", int(less), help="More than 10% below Saudi Arabia")
if mode == "Difference vs Saudi":
    note("Orange = the country pays more than Saudi Arabia, blue = it pays less, light gray = about the same. "
         "Hover a country for its median salary. Drag to move and scroll to zoom. Countries in plain gray have "
         "too few records.")
else:
    note("Lighter = higher median salary. Saudi Arabia is outlined in green. Drag to move and scroll to zoom.")

with st.expander("See the same countries as a ranking", icon=":material/leaderboard:"):
    rank = stats.sort_values("median")
    is_ksa = rank["iso3"] == "SAU"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[v for x0 in convert(rank["median"]) for v in (0, x0, None)],
        y=[v for c in rank["company_country"] for v in (c, c, None)],
        mode="lines", line=dict(color="#2b343e", width=3), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=convert(rank["median"]), y=rank["company_country"], mode="markers+text",
        text=[money(v) for v in rank["median"]], textposition="middle right",
        textfont=dict(color="#a7b1bb", size=12),
        marker=dict(size=[16 if s else 11 for s in is_ksa], color=[SAUDI if s else "#8b97a3" for s in is_ksa],
                    line=dict(color="#0f1419", width=2)),
        customdata=[hover[i] for i in rank.index],
        hovertemplate="%{customdata}<extra></extra>", showlegend=False))
    fig.update_layout(height=max(280, 34 * len(rank)), xaxis_title=unit(), yaxis_title="",
                      xaxis=dict(range=[0, convert(rank["median"].max()) * 1.2]))
    st.plotly_chart(fig, width="stretch")

# =====================================================================
# 2. Same role, different markets
# =====================================================================
st.subheader("Same role, three markets")

rows = []
for r, sar in saudi_role.items():
    grp = global_group(df, r)
    rows.append({"role": r, "Saudi Arabia": sar_to_usd_year(sar),
                 "Global excl. US": grp[grp["company_location"] != "US"]["salary_in_usd"].median(),
                 "United States": grp[grp["company_location"] == "US"]["salary_in_usd"].median()})
comp = pd.DataFrame(rows)

kind = st.segmented_control("Role type", ["Individual roles", "Leadership roles"], default="Individual roles",
                            required=True, key="kind")
sub = comp[comp["role"].isin(INDIVIDUAL)] if kind == "Individual roles" else comp[~comp["role"].isin(INDIVIDUAL)]
sub = sub.sort_values("Saudi Arabia")

fig = go.Figure()
lo = sub[["Saudi Arabia", "Global excl. US", "United States"]].min(axis=1)
hi = sub[["Saudi Arabia", "Global excl. US", "United States"]].max(axis=1)
fig.add_trace(go.Scatter(
    x=[v for a, b in zip(convert(lo), convert(hi)) for v in (a, b, None)],
    y=[v for r in sub["role"] for v in (r, r, None)],
    mode="lines", line=dict(color="#2b343e", width=10), hoverinfo="skip", showlegend=False))
for market, color in [("Global excl. US", EX_US), ("United States", US), ("Saudi Arabia", SAUDI)]:
    fig.add_trace(go.Scatter(
        x=convert(sub[market]), y=sub["role"], mode="markers", name=market,
        marker=dict(size=17 if market == "Saudi Arabia" else 14, color=color, line=dict(color="#0f1419", width=2)),
        customdata=[fmt(v) for v in sub[market]],
        hovertemplate=f"<b>%{{y}}</b><br>{market}: %{{customdata}}<extra></extra>"))
fig.update_layout(height=110 + 70 * len(sub), xaxis_title=unit(), yaxis_title="", hovermode="closest",
                  legend=dict(orientation="h", y=1.12, x=0, title=""),
                  xaxis=dict(range=[0, convert(hi.max()) * 1.08]))
st.plotly_chart(fig, width="stretch")

cols = st.columns(len(sub))
for col, r in zip(cols, sub.sort_values("Saudi Arabia", ascending=False).itertuples()):
    vs = (r._2 / r._3 - 1) * 100
    with col.container(border=True):
        st.metric(r.role, money(r._2), f"{vs:+.0f}% vs global excl. US", delta_color="off")
if kind == "Leadership roles":
    note("Each line shows the gap between the three markets for one role, and the green dot is Saudi Arabia. "
         "Saudi leaders are paid above both the global and the US medians. These values come from one recruiter "
         "survey of top roles in large companies, so read them as a strong signal, not an exact gap.")
else:
    note("Each line shows the gap between the three markets for one role, and the green dot is Saudi Arabia. "
         "Analysts and data scientists earn close to the global level outside the US. The Data Engineer value "
         "comes from one source only (PayScale), so treat it with care.")

# =====================================================================
# 3. What each Saudi source says
# =====================================================================
st.subheader("What each Saudi source says")
all_roles = ksa.sort_values("mid_sar_month")["role"].unique().tolist()
picked = st.pills("Roles", all_roles, selection_mode="multi", default=all_roles, key="src_roles")
b = ksa[ksa["role"].isin(picked or all_roles)].copy()
b["label"] = b["role"] + "  ·  " + b["source"].str.replace(" 2025 Salary Survey", "")
b = b.sort_values("mid_sar_month")
b["lo"] = b["min_sar_month"].fillna(b["mid_sar_month"])
b["hi"] = b["max_sar_month"].fillna(b["mid_sar_month"])

fig = go.Figure()
for stype, color in TYPE_COLORS.items():
    part = b[b["source_type"] == stype]
    if part.empty:
        continue
    lo_v = convert(sar_to_usd_year(part["lo"]))
    hi_v = convert(sar_to_usd_year(part["hi"]))
    fig.add_trace(go.Bar(
        y=part["label"], x=(hi_v - lo_v).clip(lower=convert(sar_to_usd_year(300))), base=lo_v, orientation="h",
        name=stype, marker=dict(color=color, opacity=0.35, line=dict(width=0)),
        customdata=part[["min_sar_month", "mid_sar_month", "max_sar_month", "pay_basis"]].values,
        hovertemplate="<b>%{y}</b><br>Min: %{customdata[0]:,.0f} SAR<br>Middle: %{customdata[1]:,.0f} SAR"
                      "<br>Max: %{customdata[2]:,.0f} SAR<br>%{customdata[3]}<extra></extra>"))
    fig.add_trace(go.Scatter(
        y=part["label"], x=convert(sar_to_usd_year(part["mid_sar_month"])), mode="markers", showlegend=False,
        marker=dict(color=color, size=12, line=dict(color="#e6eaee", width=1.5)), hoverinfo="skip"))
fig.update_layout(height=120 + 40 * len(b), barmode="overlay", barcornerradius=6, bargap=0.45,
                  xaxis_title=unit(), yaxis_title="",
                  yaxis=dict(categoryorder="array", categoryarray=b["label"].tolist()),
                  legend=dict(orientation="h", y=1.08, x=0, title=""))
st.plotly_chart(fig, width="stretch")
note("Each bar is the range a source reports and the dot is its middle value. Colors show the type of source: "
     "recruiter surveys cover senior roles in big companies, while salary websites include all levels. Click a "
     "role above to hide or show it, and hover a bar to see whether it is basic salary or total pay.")

with st.expander("Things to keep in mind", icon=":material/lightbulb:"):
    st.markdown(
        "- Saudi salaries are **tax-free**, while US and European salaries are usually before tax.\n"
        "- Many Saudi offers add **housing and transport allowances** on top of the basic salary. Sources "
        "that report basic salary only will look lower than the real package.\n"
        "- Benchmark sources use different methods and years (2024 to 2026), while the global data is "
        "mostly 2023 and 2024. Read Saudi numbers as a range, not one exact value.\n"
        "- Currency: 1 USD = 3.75 SAR (fixed peg)."
    )
