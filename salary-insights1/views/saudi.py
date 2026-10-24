import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils import (ACCENT, MUTED, SECOND, WARM, USD_TO_SAR, convert, global_group, load_benchmark,
                   load_salaries, money, note, pad_x, pad_y, page_header, unit)

df = load_salaries()
ksa = load_benchmark()

page_header("Saudi Arabia vs the World",
            "How Saudi salaries for data and AI roles compare with the US and the rest of the world.")

st.info("The global dataset has only 2 rows from Saudi Arabia (both remote, mid-level), which is too few to "
        "describe the market. So the Saudi numbers on this page come from 11 benchmark ranges published by "
        "recruiters and salary websites.", icon=":material/info:")


def from_sar_month(v):
    """Benchmark values are SAR per month; turn them into the selected currency."""
    return convert(v * 12 / USD_TO_SAR)


# ---------- Benchmark ranges ----------
st.subheader("What each Saudi source says")
b = ksa.copy()
b["label"] = b["role"] + "  ·  " + b["source"]
b = b.sort_values("mid_sar_month")
fig = go.Figure()
for row in b.itertuples():
    if pd.notna(row.min_sar_month) and pd.notna(row.max_sar_month):
        fig.add_trace(go.Scatter(x=[from_sar_month(row.min_sar_month), from_sar_month(row.max_sar_month)],
                                 y=[row.label, row.label], mode="lines", line=dict(color=MUTED, width=9),
                                 hoverinfo="skip", showlegend=False))
fig.add_trace(go.Scatter(
    x=from_sar_month(b["mid_sar_month"]), y=b["label"], mode="markers",
    marker=dict(color=ACCENT, size=12, line=dict(color="#11161C", width=2)), showlegend=False,
    customdata=b[["min_sar_month", "mid_sar_month", "max_sar_month", "pay_basis"]].values,
    hovertemplate="%{y}<br>Min: %{customdata[0]:,.0f} SAR<br>Middle: %{customdata[1]:,.0f} SAR"
                  "<br>Max: %{customdata[2]:,.0f} SAR<br>Basis: %{customdata[3]}<extra></extra>"))
fig.update_layout(height=470, xaxis_title=unit(), yaxis_title="",
                  yaxis=dict(categoryorder="array", categoryarray=b["label"].tolist()))
pad_x(fig, from_sar_month(b["max_sar_month"].max()), 1.05)
st.plotly_chart(fig, width="stretch")
note("Gray bar = range reported by the source, dot = middle value. Sources disagree a lot: recruiter "
     "surveys (Robert Walters) cover senior roles in big companies, while salary websites include all "
     "levels. Hover to see if a source reports basic salary or total pay.")

# ---------- Role comparison ----------
st.subheader("Same role, different markets")
saudi_role = ksa.groupby("role")["mid_sar_month"].median()
rows = []
for role, sar in saudi_role.items():
    g = global_group(df, role)
    rows.append({"role": role, "Saudi Arabia": sar * 12 / USD_TO_SAR,
                 "Global excl. US": g[g["company_location"] != "US"]["salary_in_usd"].median(),
                 "United States": g[g["company_location"] == "US"]["salary_in_usd"].median(),
                 "Global": g["salary_in_usd"].median(), "records": len(g)})
comp = pd.DataFrame(rows)

kind = st.segmented_control("Role type", ["Individual roles", "Leadership roles"], default="Individual roles")
ind = comp["role"].isin(["Data Analyst", "Data Scientist", "Data Engineer"])
sub = comp[ind] if kind != "Leadership roles" else comp[~ind]

long = sub.melt(id_vars="role", value_vars=["Saudi Arabia", "Global excl. US", "United States"],
                var_name="market", value_name="usd")
long["value"] = convert(long["usd"])
long["text"] = long["usd"].apply(money)
fig = px.bar(long, x="role", y="value", color="market", barmode="group", text="text",
             color_discrete_map={"Saudi Arabia": ACCENT, "Global excl. US": SECOND, "United States": WARM})
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(xaxis_title="", yaxis_title=f"Median ({unit()})", legend_title="", height=420)
pad_y(fig, long["value"].max())
st.plotly_chart(fig, width="stretch")
if kind == "Leadership roles":
    note("Leadership roles are compared with senior and executive people in the Leadership & Management "
         "family of the global data. The Saudi values come from one recruiter survey of top roles, so they "
         "sit above the global median. Saudi Arabia clearly pays well for senior data leaders.")
else:
    note("For analysts and data scientists, Saudi pay is close to the global level outside the US and well "
         "below the US. The Data Engineer value comes from one source only (PayScale), so treat it with care.")

ratio = sub.assign(**{"Saudi as % of global": (sub["Saudi Arabia"] / sub["Global"] * 100).round(0),
                      "Saudi as % of US": (sub["Saudi Arabia"] / sub["United States"] * 100).round(0)})
ratio = ratio[["role", "Saudi as % of global", "Saudi as % of US", "records"]]
ratio = ratio.rename(columns={"records": "global records used"})
st.dataframe(ratio, hide_index=True, width="stretch",
             column_config={"Saudi as % of global": st.column_config.ProgressColumn(format="%d%%", min_value=0, max_value=250),
                            "Saudi as % of US": st.column_config.ProgressColumn(format="%d%%", min_value=0, max_value=250)})
note("100% means Saudi Arabia pays the same as the comparison group.")

# ---------- Country ranking ----------
st.subheader("Where Saudi Arabia ranks")
role = st.selectbox("Role", ["Data Scientist", "Data Analyst", "Data Engineer"])
min_n = st.slider("Minimum records per country", 5, 50, 10, 5)
g = df[df["job_title"] == role]
counts = g["company_country"].value_counts()
cty = g[g["company_country"].isin(counts[counts >= min_n].index)].groupby("company_country")["salary_in_usd"].median()
cty["Saudi Arabia (benchmark)"] = saudi_role[role] * 12 / USD_TO_SAR
cty = cty.sort_values().reset_index()
cty.columns = ["country", "usd"]
cty["value"] = convert(cty["usd"])
cty["color"] = cty["country"].str.contains("Saudi").map({True: ACCENT, False: MUTED})
fig = px.bar(cty, x="value", y="country", orientation="h", text=cty["usd"].apply(money),
             color="color", color_discrete_map="identity")
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(xaxis_title=f"Median ({unit()})", yaxis_title="", height=max(300, 42 * len(cty)),
                  yaxis=dict(categoryorder="array", categoryarray=cty["country"].tolist()))
pad_x(fig, cty["value"].max())
st.plotly_chart(fig, width="stretch")
note(f"Median {role} salary by company country, with the Saudi benchmark highlighted. Only countries with "
     f"at least {min_n} records are shown.")

with st.expander("Things to keep in mind", icon=":material/lightbulb:"):
    st.markdown(
        "- Saudi salaries are **tax-free**, while US and European salaries are usually before tax.\n"
        "- Many Saudi offers add **housing and transport allowances** on top of the basic salary. Sources "
        "that report basic salary only will look lower than the real package.\n"
        "- Benchmark sources use different methods and years (2024 to 2026), while the global data is "
        "mostly 2023 and 2024. Read Saudi numbers as a range, not one exact value.\n"
        "- Currency: 1 USD = 3.75 SAR (fixed peg)."
    )
