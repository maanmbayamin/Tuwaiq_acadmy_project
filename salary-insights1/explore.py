import plotly.express as px
import streamlit as st

from utils import (ACCENT, EXP_ORDER, SEQ, SETTING_ORDER, SIZE_ORDER, convert, load_salaries, median_by,
                   money, money_range, note, pad_x, pad_y, page_header, unit)

df = load_salaries()

page_header("Explore Salaries", "Filter the data and see how salaries change by experience, job, "
                                "country, work setting and company size.")

with st.expander("Filters", expanded=True, icon=":material/filter_list:"):
    a, b, c = st.columns(3)
    exp_sel = a.multiselect("Experience", EXP_ORDER, default=EXP_ORDER)
    fam_sel = b.multiselect("Job family", sorted(df["job_family"].unique()))
    set_sel = c.multiselect("Work setting", SETTING_ORDER, default=SETTING_ORDER)
    d, e, f = st.columns(3)
    size_sel = d.multiselect("Company size", SIZE_ORDER, default=SIZE_ORDER)
    year_sel = e.slider("Year", int(df["work_year"].min()), int(df["work_year"].max()),
                        (int(df["work_year"].min()), int(df["work_year"].max())))
    keep_outliers = f.toggle("Include extreme salaries", value=True)

data = df[df["experience"].isin(exp_sel) & df["work_setting"].isin(set_sel)
          & df["company_size"].isin(size_sel) & df["work_year"].between(*year_sel)]
if fam_sel:
    data = data[data["job_family"].isin(fam_sel)]
if not keep_outliers:
    data = data[~data["is_outlier"]]

if data.empty:
    st.warning("No records match these filters. Try selecting more options.")
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Records", f"{len(data):,}")
m2.metric("Median", money(data["salary_in_usd"].median()))
m3.metric("Middle 50% range", money_range(data["salary_in_usd"].quantile(.25),
                                          data["salary_in_usd"].quantile(.75)))

# ---------- Distribution ----------
st.subheader("How salaries are spread")
plot = data.assign(value=convert(data["salary_in_usd"]))
fig = px.histogram(plot, x="value", nbins=60, color_discrete_sequence=[ACCENT])
fig.add_vline(x=convert(data["salary_in_usd"].median()), line_dash="dash", line_color="#E3E8EC",
              annotation_text="median", annotation_position="top")
fig.update_layout(xaxis_title=f"Salary ({unit()})", yaxis_title="Records", height=330, bargap=0.05)
st.plotly_chart(fig, width="stretch")
note("Most salaries sit in the middle with a long tail of very high salaries on the right. That is why "
     "we use the median instead of the average.")

# ---------- Experience and family ----------
left, right = st.columns(2)
with left:
    st.subheader("By experience")
    fig = px.box(plot, x="experience", y="value", category_orders={"experience": EXP_ORDER},
                 points=False, color_discrete_sequence=[ACCENT])
    fig.update_layout(xaxis_title="", yaxis_title=unit(), height=380)
    st.plotly_chart(fig, width="stretch")
    note("Each box shows the middle 50% of salaries and the line inside is the median. Pay rises "
         "clearly with every level.")
with right:
    st.subheader("By job family")
    fam = median_by(data, "job_family").reset_index()
    fam["value"] = convert(fam["median"])
    fig = px.bar(fam, x="value", y="job_family", orientation="h", text=fam["median"].apply(money),
                 color_discrete_sequence=[ACCENT], custom_data=["count"])
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>Median: %{text}<br>Records: %{customdata[0]:,}<extra></extra>")
    fig.update_layout(xaxis_title=f"Median ({unit()})", yaxis_title="", height=380)
    pad_x(fig, fam["value"].max())
    st.plotly_chart(fig, width="stretch")
    note("Machine learning, AI and research jobs have the highest medians in most filter combinations.")

# ---------- Titles and countries ----------
st.subheader("Job titles and countries")
min_n = st.slider("Minimum records per group (hides groups that are too small to trust)", 5, 100, 30, 5)
left, right = st.columns(2)
with left:
    titles = median_by(data, "job_title", min_count=min_n).tail(12).reset_index()
    if titles.empty:
        st.caption("No job title has enough records with these filters.")
    else:
        titles["value"] = convert(titles["median"])
        fig = px.bar(titles, x="value", y="job_title", orientation="h", text=titles["median"].apply(money),
                     color_discrete_sequence=[ACCENT], custom_data=["count"])
        fig.update_traces(textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>Median: %{text}<br>Records: %{customdata[0]:,}<extra></extra>")
        fig.update_layout(xaxis_title=f"Median ({unit()})", yaxis_title="", height=430,
                          title="Top paying job titles")
        pad_x(fig, titles["value"].max(), 1.28)
        st.plotly_chart(fig, width="stretch")
        note("The 12 best paid titles among those with enough records.")
with right:
    ctry = median_by(data, "company_country", min_count=min_n).reset_index()
    if ctry.empty:
        st.caption("No country has enough records with these filters.")
    else:
        ctry["value"] = convert(ctry["median"])
        fig = px.bar(ctry, x="value", y="company_country", orientation="h", text=ctry["median"].apply(money),
                     color_discrete_sequence=[ACCENT], custom_data=["count"])
        fig.update_traces(textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>Median: %{text}<br>Records: %{customdata[0]:,}<extra></extra>")
        fig.update_layout(xaxis_title=f"Median ({unit()})", yaxis_title="", height=430,
                          title="Median salary by company country")
        pad_x(fig, ctry["value"].max())
        st.plotly_chart(fig, width="stretch")
        note("The same work can pay several times more depending on where the company is.")

# ---------- Setting and size ----------
left, right = st.columns(2)
with left:
    st.subheader("Work setting")
    ws = median_by(data, "work_setting").reindex([s for s in SETTING_ORDER if s in set(data["work_setting"])]).reset_index()
    ws["value"] = convert(ws["median"])
    fig = px.bar(ws, x="work_setting", y="value", text=ws["median"].apply(money),
                 color_discrete_sequence=[ACCENT], custom_data=["count"])
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}<br>Median: %{text}<br>Records: %{customdata[0]:,}<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis_title=f"Median ({unit()})", height=340)
    pad_y(fig, ws["value"].max())
    st.plotly_chart(fig, width="stretch")
    note("On-site and remote pay about the same. Hybrid is lower, but it is under 2% of the data.")
with right:
    st.subheader("Company size")
    cs = median_by(data, "company_size").reindex([s for s in SIZE_ORDER if s in set(data["company_size"])]).reset_index()
    cs["value"] = convert(cs["median"])
    fig = px.bar(cs, x="company_size", y="value", text=cs["median"].apply(money),
                 color_discrete_sequence=[ACCENT], custom_data=["count"])
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}<br>Median: %{text}<br>Records: %{customdata[0]:,}<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis_title=f"Median ({unit()})", height=340)
    pad_y(fig, cs["value"].max())
    st.plotly_chart(fig, width="stretch")
    note("Small companies pay noticeably less than medium and large ones.")

# ---------- Trend and heatmap ----------
st.subheader("Over time")
trend = data.groupby(["work_year", "experience"])["salary_in_usd"].median().reset_index()
trend["value"] = convert(trend["salary_in_usd"])
fig = px.line(trend, x="work_year", y="value", color="experience", markers=True,
              category_orders={"experience": EXP_ORDER})
fig.update_layout(xaxis=dict(dtick=1, title=""), yaxis_title=f"Median ({unit()})", height=360,
                  legend_title="")
st.plotly_chart(fig, width="stretch")
note("Median salary per year for each level. Salaries rose until 2023 and then stayed about flat. "
     "Years with few records (2020, 2021) jump around more.")

st.subheader("Experience and job family together")
pivot = data.pivot_table(index="job_family", columns="experience", values="salary_in_usd", aggfunc="median")
pivot = convert(pivot[[e for e in EXP_ORDER if e in pivot.columns]])
fig = px.imshow(pivot, text_auto=".3s", color_continuous_scale=SEQ, aspect="auto")
fig.update_layout(xaxis_title="", yaxis_title="", height=400, coloraxis_colorbar_title=unit())
st.plotly_chart(fig, width="stretch")
note("Each cell is a median salary. Darker means lower, lighter means higher. Experience raises pay in "
     "every family, and the gap between families stays at every level.")
