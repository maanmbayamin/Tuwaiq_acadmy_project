import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import (ACCENT, EXP_ORDER, MUTED, SECOND, SETTING_ORDER, SIZE_ORDER, USD_TO_SAR, WARM,
                   closest_benchmark_role, convert, load_benchmark, load_metadata, load_model, load_salaries,
                   money, money_range, note, pad_y, page_header, unit)

df = load_salaries()
ksa = load_benchmark()
meta = load_metadata()
bundle = load_model()

page_header("Estimate a Salary", "Describe a role and get the model's estimate with a likely range, in USD "
                                 "and SAR.")

titles = sorted(meta["title_to_family"].keys())
countries = sorted(df["company_country"].unique())

with st.form("profile"):
    a, b, c = st.columns(3)
    title = a.selectbox("Job title", titles, index=titles.index("Data Scientist"))
    experience = b.selectbox("Experience", EXP_ORDER, index=2)
    country = c.selectbox("Company country", countries, index=countries.index("United States"))
    d, e, f = st.columns(3)
    setting = d.selectbox("Work setting", SETTING_ORDER)
    size = e.selectbox("Company size", SIZE_ORDER, index=1)
    year = f.selectbox("Year", [2024, 2023, 2022])
    submitted = st.form_submit_button("Estimate salary", type="primary", icon=":material/calculate:")

family = meta["title_to_family"][title]
title_group = title if title in meta["keep_titles"] else "Other"
country_group = country if country in meta["keep_countries"] else "Other"

X = pd.DataFrame([{
    "experience": experience, "job_family": family, "title_group": title_group,
    "country_group": country_group, "work_setting": setting, "company_size": size, "work_year": str(year),
}])[bundle["features"]]

pred = float(bundle["model"].predict(X)[0])
low = float(bundle["low"].predict(X)[0])
high = float(bundle["high"].predict(X)[0])
low, high = min(low, pred), max(high, pred)  # keep the estimate inside its range

# ---------- Result ----------
st.subheader(f"{experience} {title}, {country}")
r1, r2, r3 = st.columns(3)
r1.metric("Estimated salary", f"${pred:,.0f} / year")
r2.metric("Same in SAR", f"{pred * USD_TO_SAR / 12:,.0f} SAR / month")
r3.metric("Likely range", money_range(low, high))
note(f"About 8 in 10 real salaries for a profile like this fall inside the likely range. Job family: "
     f"{family}.")

if title_group == "Other" or country_group == "Other":
    parts = []
    if title_group == "Other":
        parts.append(f"**{title}** has few records")
    if country_group == "Other":
        parts.append(f"**{country}** has few records")
    st.warning(" and ".join(parts) + ", so the model treats it as \"Other\" and leans on the job family, "
               "experience and the average of smaller countries. Read this estimate as a rough guide.",
               icon=":material/warning:")

# ---------- Where it sits ----------
left, right = st.columns([3, 2])
with left:
    similar = df[(df["experience"] == experience) & (df["job_family"] == family)]
    if country_group != "Other":
        similar = similar[similar["company_country"] == country]
        scope = f"{experience} · {family} · {country}"
    else:
        similar = similar[~similar["company_country"].isin(meta["keep_countries"])]
        scope = f"{experience} · {family} · smaller countries"
    if len(similar) >= 5:
        fig = px.histogram(similar.assign(v=convert(similar["salary_in_usd"])), x="v", nbins=int(min(40, max(10, len(similar) // 3))),
                           color_discrete_sequence=[MUTED])
        fig.add_vrect(x0=convert(low), x1=convert(high), fillcolor=ACCENT, opacity=0.15, line_width=0)
        fig.add_vline(x=convert(pred), line_color=ACCENT, line_width=3,
                      annotation_text="estimate", annotation_position="top")
        fig.update_layout(xaxis_title=unit(), yaxis_title="People", height=360, bargap=0.05,
                          title=f"Real salaries of similar people ({len(similar):,})")
        st.plotly_chart(fig, width="stretch")
        note(f"Gray bars are real salaries in the data for {scope}. The green line is the estimate and the "
             "shaded area is the likely range.")
    else:
        st.caption("Not enough similar records in the data to draw a comparison chart for this profile.")

with right:
    # How the estimate changes with experience (everything else fixed)
    rows = X.loc[X.index.repeat(4)].reset_index(drop=True)
    rows["experience"] = EXP_ORDER
    path = pd.DataFrame({"experience": EXP_ORDER, "usd": bundle["model"].predict(rows)})
    path["value"] = convert(path["usd"])
    path["color"] = path["experience"].eq(experience).map({True: ACCENT, False: SECOND})
    fig = px.bar(path, x="experience", y="value", text=path["usd"].apply(money), color="color",
                 color_discrete_map="identity")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="", yaxis_title=unit(), height=360, title="Same role at every level",
                      xaxis=dict(categoryorder="array", categoryarray=EXP_ORDER))
    pad_y(fig, path["value"].max())
    st.plotly_chart(fig, width="stretch")
    note("The model's estimate if only the experience level changed.")

# ---------- Saudi benchmark ----------
if country == "Saudi Arabia":
    st.divider()
    st.subheader("Saudi benchmark for this role")
    roles = closest_benchmark_role(title, family)
    bench = ksa[ksa["role"].isin(roles)].copy()
    st.markdown(f"The global data has only 2 Saudi rows, so the model estimate above uses the average of "
                f"smaller countries. Here is what Saudi sources say for the closest role: "
                f"**{', '.join(roles)}**.")

    def conv(sar):
        return convert(sar * 12 / USD_TO_SAR)

    bench["label"] = bench["role"] + "  ·  " + bench["source"]
    fig = go.Figure()
    for row in bench.itertuples():
        if pd.notna(row.min_sar_month) and pd.notna(row.max_sar_month):
            fig.add_trace(go.Scatter(x=[conv(row.min_sar_month), conv(row.max_sar_month)], y=[row.label] * 2,
                                     mode="lines", line=dict(color=MUTED, width=10), showlegend=False,
                                     hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=conv(bench["mid_sar_month"]), y=bench["label"], mode="markers",
                             marker=dict(color=WARM, size=12), name="Saudi source (middle)",
                             customdata=bench[["mid_sar_month", "pay_basis"]].values,
                             hovertemplate="%{y}<br>Middle: %{customdata[0]:,.0f} SAR / month"
                                           "<br>Basis: %{customdata[1]}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[convert(pred)], y=["Model estimate"], mode="markers",
                             marker=dict(color=ACCENT, size=14, symbol="diamond"), name="Model estimate",
                             error_x=dict(type="data", symmetric=False, array=[convert(high - pred)],
                                          arrayminus=[convert(pred - low)], color=ACCENT)))
    fig.update_layout(height=140 + 55 * (len(bench) + 1), xaxis_title=unit(), yaxis_title="",
                      yaxis=dict(categoryorder="array", categoryarray=["Model estimate"] + bench.sort_values("mid_sar_month")["label"].tolist()),
                      legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, width="stretch")
    note("Gray bars are the ranges from each Saudi source. The diamond is the model estimate with its range. "
         "When they disagree, trust the Saudi sources more for the local market.")
    st.dataframe(bench[["source", "role", "pay_basis", "min_sar_month", "mid_sar_month", "max_sar_month"]],
                 hide_index=True, width="stretch")
