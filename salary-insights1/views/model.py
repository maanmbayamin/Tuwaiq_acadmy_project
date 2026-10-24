import pandas as pd
import plotly.express as px
import streamlit as st

from utils import ACCENT, MUTED, SECOND, convert, load_metadata, load_test_predictions, money, note, pad_x, pad_y, page_header, unit

meta = load_metadata()
tp = load_test_predictions()
m = meta["test_metrics"]

page_header("How the Prediction Model Works",
            "From clean data to a salary estimate: the steps, the models we tried and how accurate the "
            "final one is.")

# ---------- Steps ----------
st.subheader("The pipeline")
cols = st.columns(5)
steps = [
    ("1. Clean", f"Remove duplicates and extreme salaries: {meta['rows_raw']:,} rows become {meta['rows_model']:,}."),
    ("2. Group", f"Keep the {len(meta['keep_titles'])} most common titles and {len(meta['keep_countries'])} "
                 "countries. Rare ones become \"Other\"."),
    ("3. Encode", "Turn each category into 0/1 columns (one-hot encoding). No scaling needed."),
    ("4. Compare", "Train 4 models and compare them with 5-fold cross-validation."),
    ("5. Range", "Two extra models predict the 10th and 90th percentile to give a likely range."),
]
for col, (title, text) in zip(cols, steps):
    with col.container(border=True, height=190):
        st.markdown(f"**{title}**")
        st.caption(text)

st.markdown("**Features used:** experience, job family, job title, company country, work setting, company "
            "size and year. **Not used:** the original salary and currency (they would leak the answer), "
            "employment type (99.6% full-time) and employee country (almost always the company country).")

# ---------- Model comparison ----------
st.subheader("Which model won?")
cv = pd.DataFrame(meta["cv_results"])
left, right = st.columns(2)
with left:
    cv_r2 = cv.sort_values("R2")
    fig = px.bar(cv_r2, x="R2", y="Model", orientation="h", text=cv_r2["R2"].map("{:.3f}".format),
                 color=cv_r2["Model"].eq(meta["best_model"]).map({True: ACCENT, False: MUTED}),
                 color_discrete_map="identity")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="R² (higher is better)", yaxis_title="", height=300,
                      yaxis=dict(categoryorder="array", categoryarray=cv_r2["Model"].tolist()))
    pad_x(fig, cv_r2["R2"].max(), 1.25)
    st.plotly_chart(fig, width="stretch")
    note("R² is the share of salary differences the model explains.")
with right:
    cv_mae = cv.sort_values("MAE", ascending=False)
    fig = px.bar(cv_mae, x=convert(cv_mae["MAE"]), y="Model", orientation="h",
                 text=cv_mae["MAE"].apply(lambda v: money(v, short=False)),
                 color=cv_mae["Model"].eq(meta["best_model"]).map({True: ACCENT, False: MUTED}),
                 color_discrete_map="identity")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=f"Average error, MAE ({unit()}, lower is better)", yaxis_title="", height=300,
                      yaxis=dict(categoryorder="array", categoryarray=cv_mae["Model"].tolist()))
    pad_x(fig, convert(cv_mae["MAE"].max()), 1.3)
    st.plotly_chart(fig, width="stretch")
    note("MAE is how far a prediction is from the real salary, on average.")

st.markdown(f"**{meta['best_model']}** was the best, but all four models are close. That tells us the limit "
            "is the data, not the algorithm.")

# ---------- Test results ----------
st.subheader("Results on unseen data (test set)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("R²", f"{m['R2']:.2f}")
c2.metric("Average error (MAE)", money(m["MAE"]))
c3.metric("RMSE", money(m["RMSE"]))
c4.metric("Real salary inside predicted range", f"{m['range_coverage']:.0%}")

left, right = st.columns(2)
with left:
    tp_plot = tp.assign(actual_v=convert(tp["actual"]), predicted_v=convert(tp["predicted"]))
    fig = px.scatter(tp_plot, x="actual_v", y="predicted_v", opacity=0.35, color_discrete_sequence=[SECOND])
    lo, hi = tp_plot["actual_v"].min(), tp_plot["actual_v"].max()
    fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(color=ACCENT, dash="dash"))
    fig.update_layout(xaxis_title=f"Real salary ({unit()})", yaxis_title=f"Predicted ({unit()})", height=400,
                      title="Predicted vs real")
    st.plotly_chart(fig, width="stretch")
    note("Each dot is one person in the test set. Dots on the dashed line are perfect predictions. The model "
         "pulls very high and very low salaries towards the middle.")
with right:
    err = tp_plot.assign(error=tp_plot["actual_v"] - tp_plot["predicted_v"])
    fig = px.histogram(err, x="error", nbins=50, color_discrete_sequence=[SECOND])
    fig.add_vline(x=0, line_dash="dash", line_color=ACCENT)
    fig.update_layout(xaxis_title=f"Real minus predicted ({unit()})", yaxis_title="People", height=400,
                      title="Prediction errors", bargap=0.05)
    st.plotly_chart(fig, width="stretch")
    note("Errors are centered on zero, so the model is not biased up or down on average.")

# ---------- Importance ----------
st.subheader("What the model relies on")
names = {"country_group": "Company country", "experience": "Experience", "job_family": "Job family",
         "title_group": "Job title", "work_year": "Year", "work_setting": "Work setting",
         "company_size": "Company size"}
imp = pd.DataFrame(meta["importance"])
imp["feature"] = imp["feature"].map(names)
imp = imp.sort_values("importance")
fig = px.bar(imp, x="importance", y="feature", orientation="h", text=imp["importance"].map("{:.3f}".format),
             color_discrete_sequence=[ACCENT])
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(xaxis_title="Drop in R² when the feature is shuffled", yaxis_title="", height=340)
pad_x(fig, imp["importance"].max(), 1.2)
st.plotly_chart(fig, width="stretch")
note("Permutation importance: we shuffle one feature and see how much worse the model gets. Country and "
     "experience matter most. Work setting and company size add very little.")

with st.expander("Why is the accuracy not higher?", icon=":material/help:"):
    st.markdown(
        "The data does not include **skills, company name, city, industry or years of experience**. Two "
        "people with the same title, level and country can earn very different salaries because of these "
        "things. So the model gives a good **typical** salary for a profile, plus a range, but it cannot "
        "know everything about one person."
    )
