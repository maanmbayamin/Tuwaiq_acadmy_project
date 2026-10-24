import pandas as pd
import plotly.express as px
import streamlit as st

from utils import pad_x, ACCENT, MUTED, load_benchmark, load_metadata, load_salaries, note, page_header

df = load_salaries()
ksa = load_benchmark()
meta = load_metadata()

page_header("The Data", "Where the numbers come from, what each column means and how we cleaned it.")

tab1, tab2, tab3 = st.tabs(["Global salaries", "Saudi benchmark", "Cleaning steps"])

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{meta['rows_raw']:,}")
    c2.metric("Years", f"{df['work_year'].min()} to {df['work_year'].max()}")
    c3.metric("Missing values", "0")
    c4.metric("Rows from Saudi Arabia", int((df["company_location"] == "SA").sum()))

    left, right = st.columns(2)
    with left:
        counts = df["company_country"].value_counts()
        top = counts.head(8)
        other = pd.Series({"All other countries": counts.iloc[8:].sum()})
        share = pd.concat([top, other]).reset_index()
        share.columns = ["country", "records"]
        fig = px.bar(share, x="records", y="country", orientation="h", text="records",
                     color=share["country"].eq("United States").map({True: ACCENT, False: MUTED}),
                     color_discrete_map="identity")
        fig.update_layout(yaxis=dict(autorange="reversed", title="", categoryorder="array",
                                     categoryarray=share["country"].tolist()),
                          xaxis_title="Records", height=360, title="Records by company country")
        pad_x(fig, share["records"].max())
        st.plotly_chart(fig, width="stretch")
        note(f"About {counts.iloc[0] / len(df):.0%} of the records are from US companies, so global "
             "averages mostly describe the US market.")

    with right:
        years = df["work_year"].value_counts().sort_index().reset_index()
        years.columns = ["year", "records"]
        fig = px.bar(years, x="year", y="records", text="records", color_discrete_sequence=[ACCENT])
        fig.update_layout(xaxis=dict(type="category", title=""), yaxis_title="Records", height=360,
                          title="Records by year")
        st.plotly_chart(fig, width="stretch")
        note("Most records are from 2023 and 2024. 2020 and 2021 have very few rows, so trends for those "
             "years are less reliable.")

    st.markdown("#### Columns")
    st.dataframe(pd.DataFrame({
        "Column": ["work_year", "experience", "employment", "job_title", "job_family", "salary_in_usd",
                   "salary_sar_month", "company_country", "employee_country", "work_setting",
                   "company_size", "is_outlier"],
        "Meaning": ["Year the salary was paid", "Entry, Mid, Senior or Executive",
                    "Full-time, Part-time, Contract or Freelance", "Job title (after unifying synonyms)",
                    "One of 7 job families we created from the title", "Yearly salary in USD (the target)",
                    "Same salary in SAR per month (x 3.75 / 12)", "Country of the company",
                    "Country where the employee lives", "On-site, Hybrid or Remote",
                    "Small, Medium or Large", "True if the salary is an extreme value (IQR method)"],
    }), hide_index=True, width="stretch")

    st.markdown("#### Browse the clean data")
    f1, f2 = st.columns(2)
    fam = f1.multiselect("Job family", sorted(df["job_family"].unique()))
    ctry = f2.multiselect("Company country", sorted(df["company_country"].unique()))
    view = df
    if fam:
        view = view[view["job_family"].isin(fam)]
    if ctry:
        view = view[view["company_country"].isin(ctry)]
    st.dataframe(view.drop(columns=["company_location", "remote_ratio"]), hide_index=True,
                 width="stretch", height=320)
    st.download_button("Download clean data (CSV)", df.to_csv(index=False), "salaries_clean.csv",
                       "text/csv", icon=":material/download:")

with tab2:
    st.markdown("The main dataset has only **2 rows** from Saudi Arabia, so we use **11 salary ranges** "
                "collected from recruiters and salary websites as a Saudi benchmark.")
    show = ksa[["source", "source_type", "role", "pay_basis", "min_sar_month", "mid_sar_month",
                "max_sar_month", "mid_is_estimated", "data_year"]]
    st.dataframe(show, hide_index=True, width="stretch")
    note("Values are monthly SAR. Some sources report basic salary only, others report total pay, "
         "so the numbers are not perfectly comparable. Where the middle value was missing we used the "
         "average of min and max (mid_is_estimated = True).")
    st.download_button("Download clean benchmark (CSV)", ksa.to_csv(index=False),
                       "saudi_benchmark_clean.csv", "text/csv", icon=":material/download:")

with tab3:
    steps = [
        ("Duplicates", f"{meta['duplicates']:,} rows ({meta['duplicates'] / meta['rows_raw']:.0%}) repeat "
                       "another row with a different ID. We keep them in the charts and remove them before "
                       "training the model."),
        ("Job titles", f"Synonyms were merged into one name (for example ML Engineer becomes Machine "
                       f"Learning Engineer). Titles went from {meta['titles_before']} to {meta['titles_after']}."),
        ("Job families", "Each title was placed into one of 7 families using keywords, to make "
                         "comparisons easier."),
        ("Readable labels", "Codes such as SE, FT, M and US were replaced with Senior, Full-time, "
                            "Medium and United States."),
        ("Leakage", "salary and salary_currency were dropped from modeling because salary_in_usd is "
                    "calculated from them."),
        ("Outliers", "Extreme salaries were flagged with the IQR method. They stay in the charts and are "
                     "removed only for the model."),
        ("Saudi benchmark", "Missing middle values were filled with (min + max) / 2 and every value was "
                            "converted to yearly USD."),
    ]
    for name, text in steps:
        st.markdown(f"**{name}.** {text}")

    fam_counts = df["job_family"].value_counts().reset_index()
    fam_counts.columns = ["family", "records"]
    fig = px.bar(fam_counts, x="records", y="family", orientation="h", text="records",
                 color_discrete_sequence=[ACCENT])
    fig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis_title="Records", height=330,
                      title="Records by job family")
    pad_x(fig, fam_counts["records"].max())
    st.plotly_chart(fig, width="stretch")
    note("The 7 job families we created. Engineering, data science and analytics roles make up most of "
         "the data.")
