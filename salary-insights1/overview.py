import plotly.express as px
import streamlit as st

from utils import (ACCENT, EXP_ORDER, convert, load_metadata, pad_x, pad_y, load_salaries, median_by, money, note,
                   page_header, unit)

df = load_salaries()
meta = load_metadata()

page_header("Data & AI Salaries",
            "What do data and AI jobs pay around the world, how does Saudi Arabia compare, "
            "and what would a given role likely earn?")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Salary records", f"{len(df):,}")
c2.metric("Median salary", money(df["salary_in_usd"].median()))
c3.metric("Job titles (after cleaning)", meta["titles_after"])
c4.metric("Company countries", df["company_country"].nunique())

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Experience drives salary")
    exp = median_by(df, "experience").reindex(EXP_ORDER).reset_index()
    exp["value"] = convert(exp["median"])
    fig = px.bar(exp, x="experience", y="value", text=exp["median"].apply(money),
                 color_discrete_sequence=[ACCENT])
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}<br>Median: %{text}<br>Records: %{customdata:,}<extra></extra>",
                      customdata=exp["count"])
    fig.update_layout(xaxis_title="", yaxis_title=f"Median salary ({unit()})", height=360)
    pad_y(fig, exp["value"].max())
    st.plotly_chart(fig, width="stretch")
    note("Median salary at each experience level. An executive earns more than twice the salary of an "
         "entry-level employee.")

with right:
    st.subheader("Location matters just as much")
    top = median_by(df, "company_country", min_count=30).tail(8).reset_index()
    top["value"] = convert(top["median"])
    fig = px.bar(top, x="value", y="company_country", orientation="h",
                 text=top["median"].apply(money), color_discrete_sequence=[ACCENT])
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>Median: %{text}<extra></extra>")
    fig.update_layout(xaxis_title=f"Median salary ({unit()})", yaxis_title="", height=360)
    pad_x(fig, top["value"].max())
    st.plotly_chart(fig, width="stretch")
    note("Countries with at least 30 records. US and Canadian companies pay far more than the rest "
         "for the same kind of work.")

st.divider()
st.subheader("Key findings")

f1, f2, f3 = st.columns(3)
with f1:
    with st.container(border=True):
        st.markdown("**1. Experience and country lead**")
        st.write("These two features explain most of what the model can learn. Job family comes next.")
with f2:
    with st.container(border=True):
        st.markdown("**2. ML, AI and Research pay most**")
        st.write("They have the highest medians. Analytics & BI and data management roles pay the least.")
with f3:
    with st.container(border=True):
        st.markdown("**3. Remote does not mean less**")
        st.write("On-site and fully remote jobs have almost the same median salary.")

f4, f5, f6 = st.columns(3)
with f4:
    with st.container(border=True):
        st.markdown("**4. Saudi individual roles**")
        st.write("Analysts and data scientists in Saudi Arabia earn less than in the US, but similar to "
                 "or more than in many European countries.")
with f5:
    with st.container(border=True):
        st.markdown("**5. Saudi leadership roles**")
        st.write("Heads of data, AI and ML in Saudi Arabia are paid above the global median for "
                 "senior leaders.")
with f6:
    with st.container(border=True):
        st.markdown("**6. Predictions are ranges**")
        st.write(f"The best model (Gradient Boosting) is off by about {money(meta['test_metrics']['MAE'])} "
                 "on average, so every estimate comes with a likely range.")

st.info("Use the tabs at the top to read about the data, explore salaries with filters, compare Saudi "
        "Arabia with the world, see how the model works and estimate a salary for any role.",
        icon=":material/info:")
