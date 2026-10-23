"""Data & AI Salaries: an interactive explainer and salary estimator.

Run locally with:  streamlit run app.py
The analysis itself lives in notebooks/salary_analysis.ipynb. This app reads the
same data, the model saved by the notebook, and the evaluation files it wrote.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import features as F
from src import modeling as M
from src import style as S

ROLES_FOR_HERO = ["Data Scientist", "Data Engineer", "Data Analyst", "Machine Learning Engineer",
                  "Research Scientist", "Data Architect"]
UNITS = {"USD / year": 1.0, "SAR / month": F.USD_TO_SAR / 12, "SAR / year": F.USD_TO_SAR}
UNIT_WORDS = {"USD / year": "USD per year", "SAR / month": "SAR per month", "SAR / year": "SAR per year"}
INPUT_NAMES = {"job_title": "Job title", "experience_level": "Experience level",
               "company_location": "Company country", "company_size": "Company size",
               "remote_ratio": "Work mode", "employment_type": "Employment type", "work_year": "Year"}
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}

CSS = """
<style>
.stMainBlockContainer { max-width: 1180px; padding-top: 2.4rem; padding-bottom: 4rem; }
p.lede { font-size: 1.08rem; line-height: 1.6; opacity: 0.82; max-width: 68ch; margin-top: -0.35rem; }
.hero-answer { font-family: 'Bricolage Grotesque', 'Instrument Sans', sans-serif; font-weight: 650;
  font-size: clamp(1.9rem, 3.4vw, 2.85rem); line-height: 1.12; letter-spacing: -0.015em;
  max-width: 24ch; margin: 0.6rem 0 0.7rem 0; }
.hero-detail { font-size: 1.08rem; line-height: 1.6; opacity: 0.82; max-width: 62ch; margin-bottom: 0.4rem; }
.finding { display: grid; grid-template-columns: 9.5rem 1fr; gap: 1.1rem; align-items: baseline;
  padding: 0.95rem 0; border-top: 1px solid rgba(128, 141, 163, 0.28); }
.finding-figure { font-family: 'Bricolage Grotesque', 'Instrument Sans', sans-serif; font-weight: 650;
  font-size: 1.55rem; line-height: 1.1; color: #2a78d6; font-variant-numeric: tabular-nums; }
.finding-text { line-height: 1.55; max-width: 60ch; }
.finding-text strong { font-weight: 650; }
.note { border-left: 3px solid #eb6834; padding: 0.15rem 0 0.15rem 0.9rem; line-height: 1.55; max-width: 72ch;
  opacity: 0.9; }
.big-estimate { font-family: 'Bricolage Grotesque', 'Instrument Sans', sans-serif; font-weight: 650;
  font-size: clamp(2.2rem, 4vw, 3.1rem); line-height: 1.05; letter-spacing: -0.02em; margin: 0.2rem 0 0.3rem; }
.estimate-sub { opacity: 0.82; line-height: 1.55; }
.step { display: grid; grid-template-columns: 2rem 1fr; gap: 0.6rem; padding: 0.5rem 0; line-height: 1.55; }
.step-n { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 650; color: #2a78d6; font-size: 1.15rem; }
@media (max-width: 640px) { .finding { grid-template-columns: 1fr; gap: 0.2rem; } }
</style>
"""


# =============================================================== data loading
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    return F.load_clean()


@st.cache_data(show_spinner=False)
def load_benchmark() -> pd.DataFrame:
    return F.load_saudi_benchmark()


@st.cache_data(show_spinner=False)
def load_artifacts() -> dict:
    files = {"comparison": "model_comparison.csv", "test": "test_predictions.csv",
             "importance": "feature_importance.csv", "duplicates": "duplicates_experiment.csv",
             "classification": "classification_comparison.csv"}
    out = {}
    for key, name in files.items():
        path = M.MODEL_DIR / name
        out[key] = pd.read_csv(path) if path.exists() else None
    out["meta"] = json.loads(M.METRICS_PATH.read_text()) if M.METRICS_PATH.exists() else {}
    return out


@st.cache_resource(show_spinner="Loading the salary model...")
def load_model() -> tuple[dict, str]:
    """Load the model saved by the notebook. If it cannot be loaded (for example a
    different scikit-learn version), train the same model again from the data."""
    try:
        bundle = M.load_bundle()
        M.predict_salary(bundle, load_data().head(3))
        return bundle, "saved"
    except Exception:
        from sklearn.linear_model import Ridge

        meta = load_artifacts()["meta"]
        alpha = meta.get("best_params", {}).get("alpha", 10.0)
        bundle = M.train_bundle(F.model_frame(load_data()), "Linear Regression (Ridge)", Ridge(alpha=alpha),
                                scale_numeric=True, log_target=True, test_metrics=meta.get("test_metrics"))
        return bundle, "retrained"


# ================================================================== helpers
def unit() -> str:
    return st.session_state.get("unit_value", "USD / year")


def to_unit(usd_per_year):
    return usd_per_year * UNITS[unit()]


def money(usd_per_year: float, short: bool = False) -> str:
    """Format a USD-per-year amount in the unit the viewer picked."""
    value = float(usd_per_year) * UNITS[unit()]
    if short and abs(value) >= 1000:
        text = f"{value / 1000:,.0f}k"
    else:
        text = f"{value:,.0f}"
    return f"${text}" if unit().startswith("USD") else f"{text} SAR"


def sar_month_to_usd_year(v):
    return v * 12 / F.USD_TO_SAR


def unit_words() -> str:
    return UNIT_WORDS[unit()]


def unit_picker(key: str) -> None:
    current = unit()
    choice = st.segmented_control("Show amounts in", list(UNITS), default=current, key=f"unit_{key}")
    st.session_state["unit_value"] = choice or current


def tokens() -> dict:
    try:
        mode = st.context.theme.type or "light"
    except Exception:
        mode = "light"
    return S.APP_CHART["dark" if mode == "dark" else "light"]


def money_axis(fig, axis: str = "y") -> None:
    prefix, suffix = ("$", "") if unit().startswith("USD") else ("", " SAR")
    getattr(fig, f"update_{axis}axes")(tickprefix=prefix, ticksuffix=suffix, tickformat="~s",
                                        title_text=f"Salary ({unit_words()})")


def style_fig(fig, height: int = 380, legend: bool = False, grid: str = "y"):
    """Shared chart look. `grid` sets which axis carries gridlines: the value axis only."""
    t = tokens()
    fig.update_layout(
        height=height, margin=dict(l=6, r=18, t=36 if legend else 12, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=S.APP_FONT, size=13, color=t["muted"]),
        hoverlabel=dict(bgcolor=t["hover_bg"], bordercolor=t["axis"],
                        font=dict(family=S.APP_FONT, size=13, color=t["ink"])),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text="",
                    font=dict(color=t["ink"])),
        bargap=0.38,
    )
    for update in (fig.update_xaxes, fig.update_yaxes):
        update(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False, tickfont=dict(color=t["muted"]),
               title_font=dict(color=t["muted"], size=13), automargin=True)
    fig.update_xaxes(showgrid=grid in ("x", "both"))
    fig.update_yaxes(showgrid=grid in ("y", "both"))
    return fig


def show(fig, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG, theme=None, key=key)


def page_header(title: str, intro: str, key: str, with_units: bool = True) -> None:
    st.html(CSS)
    left, right = st.columns([2.5, 1.5], vertical_alignment="bottom")
    with left:
        st.title(title)
    if with_units:
        with right:
            unit_picker(key)
    st.markdown(f"<p class='lede'>{intro}</p>", unsafe_allow_html=True)


def esc(text: str) -> str:
    """Streamlit markdown reads $...$ as a math formula, so escape dollar signs."""
    return text.replace("$", "\\$")


def how_to_read(text: str) -> None:
    st.caption(esc(text))


def insight(text: str) -> None:
    st.markdown(esc(f"**What this shows:** {text}"))


def text_table(data: pd.DataFrame) -> None:
    """A static table that wraps long text instead of cutting it off."""
    st.table(data, hide_index=True, border="horizontal")


def table(data: pd.DataFrame, **kwargs) -> None:
    """A static table sized to show every row without scrolling."""
    st.dataframe(data, hide_index=True, width="stretch", height=35 * (len(data) + 1) + 3, **kwargs)


def join_words(items: list[str]) -> str:
    """['Spain', 'France', 'Italy'] -> 'Spain, France and Italy'."""
    items = [i if i != "United States" else "the United States" for i in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def summary_by(df: pd.DataFrame, col: str, order=None) -> pd.DataFrame:
    g = df.groupby(col, observed=True).salary_in_usd
    out = pd.DataFrame({"median": g.median(), "mean": g.mean(), "p25": g.quantile(0.25),
                        "p75": g.quantile(0.75), "n": g.size()})
    return out.reindex(order).dropna(subset=["n"]) if order is not None else out


# ================================================================= overview
def page_overview() -> None:
    df = load_data()
    page_header("Data & AI salaries",
                f"What {len(df):,} salaries from {df.work_year.min()} to {df.work_year.max()} say about pay in data "
                "and AI jobs, how Saudi Arabia compares, and what a profile like yours might earn.", "overview")

    t = tokens()
    role = st.pills("Pick a role", ROLES_FOR_HERO, default="Data Scientist", key="hero_role") or "Data Scientist"
    sub = df[df.job_title == role]
    med, p25, p75 = sub.salary_in_usd.median(), sub.salary_in_usd.quantile(0.25), sub.salary_in_usd.quantile(0.75)
    st.html(f"<div class='hero-answer'>{role}s earn a median of {money(med)} a year.</div>"
            if unit() != "SAR / month" else
            f"<div class='hero-answer'>{role}s earn a median of {money(med)} a month.</div>")
    other = (f"{med * F.USD_TO_SAR / 12:,.0f} SAR a month" if unit().startswith("USD")
             else f"${med:,.0f} a year")
    st.html(f"<div class='hero-detail'>That is about {other}. Half of the {len(sub):,} {role}s in the data earn "
            f"between {money(p25)} and {money(p75)}. The ladder below shows how much the level of experience "
            f"changes that.</div>")

    ladder = summary_by(sub, "experience_label", F.EXPERIENCE_ORDER)
    fig = go.Figure(go.Bar(
        x=ladder.index, y=to_unit(ladder["median"]), marker_color=t["ramp4"][: len(ladder)],
        text=[money(v, short=True) for v in ladder["median"]], textposition="outside",
        textfont=dict(color=t["ink"], size=14), cliponaxis=False,
        customdata=np.stack([[money(v) for v in ladder.p25], [money(v) for v in ladder.p75], ladder.n], axis=1),
        hovertemplate="<b>%{x}</b><br>Median %{text}<br>Middle half %{customdata[0]} to %{customdata[1]}"
                      "<br>%{customdata[2]} records<extra></extra>"))
    style_fig(fig, height=300)
    money_axis(fig)
    fig.update_yaxes(range=[0, to_unit(ladder["median"].max()) * 1.25], title_text="", showticklabels=False,
                     showgrid=False, showline=False)
    fig.update_xaxes(title_text="", tickfont=dict(size=14, color=t["ink"]))
    show(fig, key="hero_ladder")

    st.subheader("What the data tells us")
    us, rest = df[df.is_us == 1].salary_in_usd.median(), df[df.is_us == 0].salary_in_usd.median()
    exp = summary_by(df, "experience_label", F.EXPERIENCE_ORDER)["median"]
    fam = df.groupby("job_family").salary_in_usd.median().sort_values()
    wm = summary_by(df, "work_mode", F.WORK_MODE_ORDER)["median"]
    bench = load_benchmark()
    ds_sa = bench[bench.role == "Data Scientist"].mid_sar_month.dropna()
    profile = (F.model_frame(df).groupby(F.MODEL_INPUTS).salary_in_usd.agg(["size", "min", "max"])
               .sort_values("size", ascending=False).iloc[0])
    findings = [
        (f"×{us / rest:.1f}", "Location matters most.",
         f"US companies pay a median of {money(us)}, about {us / rest:.1f} times the rest of the world ({money(rest)})."),
        (f"×{exp.iloc[-1] / exp.iloc[0]:.1f}", "Experience pays at every step.",
         f"Executives earn a median of {money(exp.iloc[-1])}, against {money(exp.iloc[0])} at entry level."),
        (f"+{fam.iloc[-1] / fam.iloc[0] - 1:.0%}", "The kind of work matters.",
         f"{fam.index[-1]} roles earn a median of {money(fam.iloc[-1])}, {fam.index[0]} roles {money(fam.iloc[0])}."),
        ("Equal", "Remote work does not lower pay.",
         f"Remote and on-site medians are {money(wm['Remote'])} and {money(wm['On-site'])}. Hybrid looks lower "
         "only because most hybrid jobs are outside the US."),
        (f"{ds_sa.min() / 1000:.0f}K to {ds_sa.max() / 1000:.0f}K", "Saudi Arabia sits between Europe and the US.",
         f"Published sources put Data Scientist pay at {ds_sa.min():,.0f} to {ds_sa.max():,.0f} SAR a month, above "
         "continental Europe in this data and below the US."),
        (f"{profile['min'] / 1000:.0f}K to {profile['max'] / 1000:.0f}K", "Same profile, very different pay.",
         f"{int(profile['size'])} Senior Data Scientists at medium US companies in 2023 earn from "
         f"${profile['min']:,.0f} to ${profile['max']:,.0f}. That is why any estimate comes with a range."),
    ]
    rows = "".join(f"<div class='finding'><div class='finding-figure'>{fig_}</div>"
                   f"<div class='finding-text'><strong>{head}</strong> {body}</div></div>"
                   for fig_, head, body in findings)
    st.html(rows)

    st.subheader("Where to go next")
    cols = st.columns(2)
    links = [("data", "See how the data was checked and cleaned."),
             ("explore", "Filter by year, level, job and location, and compare salaries."),
             ("saudi", "Compare published Saudi salaries with other countries."),
             ("model", "Understand how the estimate works and how accurate it is."),
             ("estimate", "Enter a job, level and country to get an estimate.")]
    for i, (key, text) in enumerate(links):
        with cols[i % 2]:
            st.page_link(PAGES[key], icon=PAGES[key].icon)
            st.caption(text)

    st.html(f"<div class='note'>Read the numbers with care: {(df.is_us == 1).mean():.1%} of the records come from "
            f"US companies, only {(df.company_location == 'SA').sum()} come from Saudi Arabia, and the data ends in "
            f"{df.work_year.max()}. Saudi figures in this app come from separate published sources.</div>")


# ===================================================================== data
def page_data() -> None:
    df = load_data()
    raw = F.load_raw()
    art = load_artifacts()
    page_header("The data", "Where the numbers come from, what each column means, and every check and cleaning "
                "decision made before the analysis. Nothing was deleted without measuring the effect first.", "data")

    c = st.columns(5)
    c[0].metric("Records", f"{len(df):,}", border=True)
    c[1].metric("Columns", f"{len(F.RAW_COLUMNS)}", border=True)
    c[2].metric("Years", f"{df.work_year.min()}-{df.work_year.max()}", border=True)
    c[3].metric("Company countries", f"{df.company_location.nunique()}", border=True)
    c[4].metric("Job titles", f"{df.job_title.nunique()}", border=True)

    tabs = st.tabs(["Columns", "Quality checks", "Duplicates", "Outliers", "New columns", "Browse the data"])

    with tabs[0]:
        how_to_read("Each row of the data is one salary. These are the 11 original columns.")
        dictionary = pd.DataFrame([
            ("work_year", "Year the salary was paid", "Date (year)", "Model input"),
            ("experience_level", "EN Entry, MI Mid, SE Senior, EX Executive", "Ordered category", "Model input"),
            ("employment_type", "FT Full-time, PT Part-time, CT Contract, FL Freelance", "Category", "Model input"),
            ("job_title", "Job title (146 different titles)", "Category", "Model input (grouped)"),
            ("salary", "Gross salary in the original currency", "Number", "Left out: it is the target in another currency"),
            ("salary_currency", "Currency of salary", "Category", "Left out: tied to salary"),
            ("salary_in_usd", "Salary converted to US dollars", "Number", "Target (what we predict)"),
            ("employee_residence", "Country where the employee lives", "Category", "Left out: same as company country for 99%"),
            ("remote_ratio", "0 on-site, 50 hybrid, 100 remote", "Category stored as a number", "Model input"),
            ("company_location", "Country of the employer", "Category", "Model input"),
            ("company_size", "S Small, M Medium, L Large", "Ordered category", "Model input"),
        ], columns=["Column", "Meaning", "Type", "Use in the model"])
        text_table(dictionary)

    with tabs[1]:
        how_to_read("Every check below is calculated live from the data file.")
        text_cols = raw.select_dtypes(exclude="number").columns
        changed_by_strip = int(sum((raw[c] != raw[c].str.strip()).sum() for c in text_cols))
        low_b, high_b = F.iqr_bounds(raw.salary_in_usd)
        checks = pd.DataFrame([
            ("Missing values", int(raw.isna().sum().sum()), "Nothing to fix"),
            ("Hidden spaces found by strip()", changed_by_strip, "Nothing to fix; strip() kept as a safeguard"),
            ("Exact duplicate rows", int(raw.duplicated().sum()), "Kept for charts, removed for model training"),
            ("Salaries that are zero or negative", int((raw.salary_in_usd <= 0).sum()), "Nothing to fix"),
            ("Invalid codes (level, size, type, work mode)", int(
                (~raw.experience_level.isin(F.EXPERIENCE_LABELS)).sum()
                + (~raw.company_size.isin(F.COMPANY_SIZE_LABELS)).sum()
                + (~raw.employment_type.isin(F.EMPLOYMENT_LABELS)).sum()
                + (~raw.remote_ratio.isin(F.WORK_MODE_LABELS)).sum()), "Nothing to fix"),
            ("USD rows where salary differs from salary_in_usd", int(
                ((raw.salary_currency == "USD") & (raw.salary != raw.salary_in_usd)).sum()), "Nothing to fix"),
            ("Outliers (IQR rule)", int(((raw.salary_in_usd < low_b) | (raw.salary_in_usd > high_b)).sum()),
             "Kept and flagged: real high salaries"),
        ], columns=["Check", "Rows found", "Decision"])
        text_table(checks)
        st.markdown("**Cleaning decisions log**")
        how_to_read("Following the course method: understand, detect, measure the impact, decide, and write the "
                    "decision down.")
        log = pd.DataFrame([
            ("Duplicate rows", "38.5% of rows", "Statistics barely move; model accuracy the same; a random split "
             "would put copies of training rows in the test set", "Keep for charts, drop for the model"),
            ("Outliers", "1.8% of rows, all high", "Mostly Senior and Executive roles at US companies",
             "Keep, flag, use the median and a log target"),
            ("Currency (USD vs SAR)", "Fixed peg 3.75", "Identical results in both currencies",
             "Analyse in USD, show SAR next to it"),
            ("Imbalance", "87.5% US, 99.6% full-time", "Results mostly describe the US market",
             "Keep, state it clearly, add Saudi benchmarks"),
        ], columns=["Issue", "Detected", "Impact", "Decision"])
        text_table(log)

    with tabs[2]:
        dup = raw.duplicated(keep=False)
        groups = raw.groupby(F.RAW_COLUMNS).size()
        st.markdown(
            f"**{int(raw.duplicated().sum()):,} rows** are exact copies of another row, after removing hidden spaces. "
            f"The largest group is **{groups.max()} identical rows**, which looks like many people on the same salary "
            "band rather than a typing mistake. There is no ID column, so we measured both options instead of guessing.")
        by_year = raw.assign(dup=dup).groupby("work_year").dup.mean().reset_index()
        fig = px.bar(by_year, x="work_year", y="dup", text=[f"{v:.0%}" for v in by_year.dup])
        fig.update_traces(marker_color=tokens()["blue"], textposition="outside", cliponaxis=False,
                          hovertemplate="%{x}: %{text} of rows have an identical twin<extra></extra>")
        style_fig(fig, height=260)
        fig.update_yaxes(tickformat=".0%", title_text="Rows with an identical twin", range=[0, 0.75])
        fig.update_xaxes(title_text="", type="category")
        show(fig, key="dup_year")
        how_to_read("Duplicates are almost absent in 2020 and 2021 and common from 2022 onward.")
        if art["duplicates"] is not None:
            d = art["duplicates"].copy()
            d["MAE"] = d["MAE"].map(lambda v: money(v))
            d["R2"] = d["R2"].round(3)
            st.markdown("**Effect on the model** (same test rows, 5 repeated splits)")
            table(d[["model", "training data", "MAE", "R2"]])
        insight("keeping or dropping duplicates changes the model's average error by less than $100. They are kept "
                "in every chart, and removed only for training, so no test row is a copy of a training row.")

    with tabs[3]:
        q1, q3 = raw.salary_in_usd.quantile([0.25, 0.75])
        iqr = q3 - q1
        st.markdown(esc(f"The IQR rule marks a salary as an outlier if it is above Q3 + 1.5 × IQR. Here Q1 is "
                        f"{money(q1)}, Q3 is {money(q3)}, so the upper limit is **{money(q3 + 1.5 * iqr)}**."))
        fig = px.box(df, x=to_unit(df.salary_in_usd), points="outliers",
                     hover_data={"job_title": True, "experience_label": True, "company_country": True})
        fig.update_traces(marker=dict(color=tokens()["blue"], size=5, opacity=0.5),
                          line=dict(color=tokens()["blue"]), fillcolor="rgba(42,120,214,0.15)")
        style_fig(fig, height=240, grid="x")
        money_axis(fig, "x")
        show(fig, key="outlier_box")
        out = df[df.is_outlier == 1]
        insight(f"{len(out):,} salaries ({len(out) / len(df):.1%}) are above the limit. "
                f"{(out.company_location == 'US').mean():.0%} are at US companies and "
                f"{out.experience_level.isin(['SE', 'EX']).mean():.0%} are Senior or Executive, so they look like "
                "real top salaries. They are kept and flagged, and hovering a dot shows who it is.")

    with tabs[4]:
        how_to_read("Columns added to make the data easier to read and to model. They are built in src/features.py.")
        new_cols = pd.DataFrame([
            ("experience_label, experience_rank", "Entry to Executive, and 1 to 4"),
            ("company_size_label, company_size_rank", "Small to Large, and 1 to 3"),
            ("work_mode", "On-site, Hybrid, Remote instead of 0, 50, 100"),
            ("job_family", "146 titles grouped into 7 families"),
            ("title_seniority, is_management", "Leadership words in the title (Head, Director, Manager, Lead)"),
            ("company_country, region, is_us", "Country names, world region, and a US flag"),
            ("cross_border", "Employee lives in a different country than the company"),
            ("salary_sar, monthly_sar", "Salary in Saudi riyals per year and per month"),
            ("salary_band", "Low, Medium, High, Very high (quarters of the data, for charts only)"),
            ("is_outlier, log_salary", "Outlier flag and the log of salary used by the model"),
        ], columns=["New column", "What it holds"])
        text_table(new_cols)
        fam_table = (df.groupby("job_family").agg(records=("job_title", "size"), titles=("job_title", "nunique"),
                                                  examples=("job_title", lambda s: ", ".join(s.value_counts().index[:3])))
                     .sort_values("records", ascending=False).reset_index())
        st.markdown("**The seven job families**")
        table(fam_table)

    with tabs[5]:
        how_to_read("Search and filter the cleaned data, then download your selection as a CSV file.")
        c1, c2 = st.columns(2)
        title_pick = c1.multiselect("Job title", sorted(df.job_title.unique()), placeholder="All job titles")
        country_pick = c2.multiselect("Company country", sorted(df.company_country.unique()),
                                      placeholder="All countries")
        view = df
        if title_pick:
            view = view[view.job_title.isin(title_pick)]
        if country_pick:
            view = view[view.company_country.isin(country_pick)]
        cols = ["work_year", "job_title", "job_family", "experience_label", "company_country", "company_size_label",
                "work_mode", "employment_label", "salary_in_usd", "monthly_sar", "is_outlier"]
        st.dataframe(view[cols], hide_index=True, width="stretch", height=380,
                     column_config={"salary_in_usd": st.column_config.NumberColumn("Salary (USD/year)", format="$%d"),
                                    "monthly_sar": st.column_config.NumberColumn("Salary (SAR/month)", format="%d")})
        st.download_button("Download this selection (CSV)", view[cols].to_csv(index=False).encode("utf-8"),
                           file_name="salaries_selection.csv", mime="text/csv")
        st.caption(f"{len(view):,} rows shown.")


# ================================================================== explore
FILTER_KEYS = ["f_years", "f_exp", "f_size", "f_mode", "f_family", "f_region"]


def reset_filters() -> None:
    for k in FILTER_KEYS:
        st.session_state.pop(k, None)


def page_explore() -> None:
    df = load_data()
    t = tokens()
    page_header("Explore salaries", "Narrow the data with the filters, then switch between the tabs. Every chart, "
                "number and sentence on this page updates to your selection. Hover over any chart for details.",
                "explore")

    with st.container(border=True):
        r1 = st.columns([1.2, 1.6, 1.1])
        years = r1[0].slider("Year", 2020, 2024, (2020, 2024), key="f_years")
        exp_sel = r1[1].pills("Experience", F.EXPERIENCE_ORDER, selection_mode="multi",
                              default=F.EXPERIENCE_ORDER, key="f_exp")
        size_sel = r1[2].pills("Company size", F.COMPANY_SIZE_ORDER, selection_mode="multi",
                               default=F.COMPANY_SIZE_ORDER, key="f_size")
        r2 = st.columns([1.1, 1.2, 1.2, 0.5], vertical_alignment="bottom")
        mode_sel = r2[0].pills("Work mode", F.WORK_MODE_ORDER, selection_mode="multi",
                               default=F.WORK_MODE_ORDER, key="f_mode")
        fam_sel = r2[1].multiselect("Job family", F.JOB_FAMILY_ORDER, placeholder="All job families", key="f_family")
        reg_sel = r2[2].multiselect("Company region", F.REGION_ORDER, placeholder="All regions", key="f_region")
        r2[3].button("Reset", on_click=reset_filters, width="stretch")

    view = df[df.work_year.between(*years)]
    for col, sel in [("experience_label", exp_sel), ("company_size_label", size_sel), ("work_mode", mode_sel),
                     ("job_family", fam_sel), ("region", reg_sel)]:
        if sel:
            view = view[view[col].astype(str).isin(sel)]

    if view.empty:
        st.info("No salaries match these filters. Widen a filter or press Reset.")
        return

    m = st.columns(4)
    m[0].metric("Salaries in selection", f"{len(view):,}", border=True)
    m[1].metric("Median salary", esc(money(view.salary_in_usd.median())), border=True)
    m[2].metric("Middle half", esc(f"{money(view.salary_in_usd.quantile(0.25), True)} to "
                                   f"{money(view.salary_in_usd.quantile(0.75), True)}"), border=True)
    m[3].metric("From US companies", f"{view.is_us.mean():.0%}", border=True)
    if len(view) < 30:
        st.warning(f"Only {len(view)} salaries match. Patterns in groups this small can be due to chance.")

    tabs = st.tabs(["Distribution", "Experience", "Job roles", "Location", "Over time", "Work setup", "Heatmap"])

    with tabs[0]:
        fig = px.histogram(x=to_unit(view.salary_in_usd), nbins=50, marginal="box")
        fig.update_traces(marker_color=t["blue"], marker_line_width=0, selector=dict(type="histogram"),
                          hovertemplate="%{x}<br>%{y} salaries<extra></extra>")
        fig.update_traces(marker_color=t["blue"], line_color=t["blue"], fillcolor="rgba(42,120,214,0.15)",
                          selector=dict(type="box"))
        med = to_unit(view.salary_in_usd.median())
        fig.add_vline(x=med, line_color=t["ink"], line_width=1.5, row=1, col=1,
                      annotation_text=f"Median {money(view.salary_in_usd.median())}", annotation_position="top right",
                      annotation_font=dict(color=t["ink"]))
        style_fig(fig, height=420)
        money_axis(fig, "x")
        fig.update_xaxes(title_text="", row=2, col=1)
        fig.update_yaxes(title_text="Number of salaries", row=1, col=1)
        fig.update_layout(bargap=0.04)
        show(fig, key="ex_hist")
        how_to_read("Each bar counts the salaries in a range. The box on top marks the middle half; dots are outliers.")
        q1, q3 = view.salary_in_usd.quantile([0.25, 0.75])
        insight(f"half of the selected salaries are between {money(q1)} and {money(q3)}. The mean "
                f"({money(view.salary_in_usd.mean())}) is above the median because a few very high salaries pull it up.")

    with tabs[1]:
        s = summary_by(view, "experience_label", F.EXPERIENCE_ORDER)
        stat = st.segmented_control("Show", ["Median", "Mean"], default="Median", key="ex_stat") or "Median"
        col = stat.lower()
        ramp = dict(zip(F.EXPERIENCE_ORDER, t["ramp4"]))
        fig = go.Figure(go.Bar(
            x=s.index, y=to_unit(s[col]), marker_color=[ramp[i] for i in s.index],
            text=[money(v, True) for v in s[col]], textposition="outside", cliponaxis=False,
            textfont=dict(color=t["ink"]),
            customdata=np.stack([[money(v) for v in s.p25], [money(v) for v in s.p75], s.n], axis=1),
            hovertemplate="<b>%{x}</b><br>" + stat + " %{text}<br>Middle half %{customdata[0]} to %{customdata[1]}"
                          "<br>%{customdata[2]} salaries<extra></extra>"))
        style_fig(fig, height=360)
        money_axis(fig)
        fig.update_yaxes(range=[0, to_unit(s[col].max()) * 1.2])
        fig.update_xaxes(title_text="")
        show(fig, key="ex_exp")
        how_to_read("Bars show the typical salary at each level. Switch to the mean to see the effect of high earners.")
        if {"Entry", "Executive"} <= set(s.index):
            insight(f"Executives earn {s.loc['Executive', 'median'] / s.loc['Entry', 'median']:.1f} times as much as "
                    f"entry-level staff in this selection ({money(s.loc['Executive', 'median'])} against "
                    f"{money(s.loc['Entry', 'median'])}).")

    with tabs[2]:
        left, right = st.columns(2)
        with left:
            fam = summary_by(view, "job_family").sort_values("median")
            fig = go.Figure(go.Bar(
                y=fam.index, x=to_unit(fam["median"]), orientation="h", marker_color=t["blue"],
                text=[money(v, True) for v in fam["median"]], textposition="outside", cliponaxis=False,
                textfont=dict(color=t["ink"]), customdata=fam.n,
                hovertemplate="<b>%{y}</b><br>Median %{text}<br>%{customdata} salaries<extra></extra>"))
            style_fig(fig, height=360, grid="x")
            money_axis(fig, "x")
            fig.update_xaxes(range=[0, to_unit(fam["median"].max()) * 1.25])
            st.markdown("**By job family**")
            show(fig, key="ex_fam")
        with right:
            min_n = st.slider("Only titles with at least this many salaries", 5, 100, 30, step=5, key="ex_min_n")
            ttl = summary_by(view, "job_title")
            ttl = ttl[ttl.n >= min_n].sort_values("median").tail(15)
            st.markdown(f"**Top {len(ttl)} job titles by median salary**")
            if ttl.empty:
                st.info("No job title has that many salaries in this selection. Lower the minimum.")
            else:
                fig = go.Figure(go.Bar(
                    y=ttl.index, x=to_unit(ttl["median"]), orientation="h", marker_color=t["blue_soft"],
                    text=[money(v, True) for v in ttl["median"]], textposition="outside", cliponaxis=False,
                    textfont=dict(color=t["ink"]), customdata=ttl.n,
                    hovertemplate="<b>%{y}</b><br>Median %{text}<br>%{customdata} salaries<extra></extra>"))
                style_fig(fig, height=max(300, 26 * len(ttl) + 60), grid="x")
                money_axis(fig, "x")
                fig.update_xaxes(range=[0, to_unit(ttl["median"].max()) * 1.3])
                show(fig, key="ex_titles")
        if len(fam) >= 2:
            insight(f"{fam.index[-1]} pays the most here ({money(fam['median'].iloc[-1])}) and {fam.index[0]} the "
                    f"least ({money(fam['median'].iloc[0])}). The minimum-count slider stops a title with a handful "
                    "of salaries from topping the list by chance.")

    with tabs[3]:
        how_bar, how_map = "Countries", "World map"
        kind = st.segmented_control("View", [how_bar, how_map], default=how_bar, key="ex_loc_view") or how_bar
        min_c = st.slider("Only countries with at least this many salaries", 5, 100, 20, step=5, key="ex_min_c")
        ctry = view.groupby(["company_location", "company_country"]).salary_in_usd.agg(["median", "size"]).reset_index()
        ctry = ctry[ctry["size"] >= min_c].sort_values("median")
        if ctry.empty:
            st.info("No country has that many salaries in this selection. Lower the minimum.")
        elif kind == how_bar:
            colors = [t["blue"] if c == "US" else t["blue_soft"] for c in ctry.company_location]
            fig = go.Figure(go.Bar(
                y=ctry.company_country, x=to_unit(ctry["median"]), orientation="h", marker_color=colors,
                text=[money(v, True) for v in ctry["median"]], textposition="outside", cliponaxis=False,
                textfont=dict(color=t["ink"]), customdata=ctry["size"],
                hovertemplate="<b>%{y}</b><br>Median %{text}<br>%{customdata} salaries<extra></extra>"))
            style_fig(fig, height=max(280, 28 * len(ctry) + 60), grid="x")
            money_axis(fig, "x")
            fig.update_xaxes(range=[0, to_unit(ctry["median"].max()) * 1.25])
            show(fig, key="ex_ctry")
        else:
            ctry = ctry.assign(iso3=ctry.company_location.map(F.COUNTRY_ISO3), shown=to_unit(ctry["median"]),
                               label=[money(v) for v in ctry["median"]])
            fig = px.choropleth(ctry, locations="iso3", color="shown", hover_name="company_country",
                                custom_data=["label", "size"], color_continuous_scale=t["sequential"])
            fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Median %{customdata[0]}<br>"
                                            "%{customdata[1]} salaries<extra></extra>",
                              marker_line_color=t["surface"], marker_line_width=0.5)
            fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth",
                            projection_rotation=dict(lon=10, lat=0), center=dict(lon=10, lat=15),
                            lataxis_range=[-58, 85], bgcolor="rgba(0,0,0,0)", landcolor=t["grid"], showland=True,
                            showcountries=False)
            style_fig(fig, height=430)
            fig.update_layout(coloraxis_colorbar=dict(title=unit_words(), tickformat="~s"))
            show(fig, key="ex_map")
            how_to_read("Grey countries have fewer salaries than the minimum you set.")
        if not ctry.empty and (ctry.company_location == "US").any() and len(ctry) > 1:
            us_med = ctry.loc[ctry.company_location == "US", "median"].iloc[0]
            others = view[view.company_location != "US"].salary_in_usd.median()
            insight(f"US companies pay a median of {money(us_med)}, against {money(others)} for all other countries "
                    "in this selection combined.")

    with tabs[4]:
        tr = view.groupby(["work_year", "experience_label"], observed=True).salary_in_usd.agg(["median", "size"]).reset_index()
        fig = go.Figure()
        for level, color in zip(F.EXPERIENCE_ORDER, t["ramp4"]):
            sub = tr[tr.experience_label == level]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub.work_year, y=to_unit(sub["median"]), name=level, mode="lines+markers",
                line=dict(color=color, width=2.5), marker=dict(size=9, line=dict(color=t["surface"], width=2)),
                customdata=np.stack([[money(v) for v in sub["median"]], sub["size"]], axis=1),
                hovertemplate=f"<b>{level}</b>, %{{x}}<br>Median %{{customdata[0]}}<br>%{{customdata[1]}} salaries"
                              "<extra></extra>"))
        style_fig(fig, height=380, legend=True)
        money_axis(fig)
        fig.update_xaxes(dtick=1, title_text="")
        fig.update_layout(hovermode="closest")
        show(fig, key="ex_time")
        how_to_read("Each line is one experience level. Hover a point to see how many salaries it is based on: "
                    "2020 and 2021 have few records, so their points move a lot by chance.")
        yr = view.groupby("work_year").salary_in_usd.median()
        if len(yr) >= 2:
            insight(f"the median salary of the selection went from {money(yr.iloc[0])} in {yr.index[0]} to "
                    f"{money(yr.iloc[-1])} in {yr.index[-1]}. Part of any change comes from who is in the data each "
                    "year, not only from pay rises.")

    with tabs[5]:
        left, right = st.columns(2)
        for holder, col, order, title, key in [(left, "work_mode", F.WORK_MODE_ORDER, "By work mode", "ex_wm"),
                                               (right, "company_size_label", F.COMPANY_SIZE_ORDER, "By company size",
                                                "ex_cs")]:
            with holder:
                st.markdown(f"**{title}**")
                sub = view[view[col].astype(str).isin(order)]
                fig = go.Figure()
                for name in order:
                    grp = sub[sub[col].astype(str) == name]
                    if grp.empty:
                        continue
                    vals = grp.salary_in_usd
                    q1, med, q3 = vals.quantile([0.25, 0.5, 0.75])
                    lo = max(vals.min(), q1 - 1.5 * (q3 - q1))
                    hi = min(vals.max(), q3 + 1.5 * (q3 - q1))
                    label = f"{name}<br>{grp.is_us.mean():.0%} US"
                    fig.add_trace(go.Box(
                        x=[label], q1=[to_unit(q1)], median=[to_unit(med)], q3=[to_unit(q3)],
                        lowerfence=[to_unit(lo)], upperfence=[to_unit(hi)], name=label, marker_color=t["blue"],
                        fillcolor="rgba(42,120,214,0.15)", line=dict(color=t["blue"], width=1.5),
                        hoverinfo="skip"))
                    fig.add_trace(go.Scatter(
                        x=[label], y=[to_unit(med)], mode="markers", marker=dict(size=18, opacity=0),
                        showlegend=False, hovertemplate=(
                            f"<b>{name}</b><br>Median {money(med)}<br>Middle half {money(q1)} to {money(q3)}"
                            f"<br>{len(vals):,} salaries, {grp.is_us.mean():.0%} at US companies<extra></extra>")))
                style_fig(fig, height=360)
                money_axis(fig)
                show(fig, key=key)
        how_to_read("Each box covers the middle half of salaries and the line inside is the median. Whiskers reach "
                    "the usual 1.5 × IQR limit; higher salaries are left out for readability. The label under each box "
                    "shows the share of US companies, which explains most of the differences.")
        wm = summary_by(view, "work_mode", F.WORK_MODE_ORDER)
        if {"Hybrid", "On-site"} <= set(wm.index):
            hy_us = view[view.work_mode == "Hybrid"].is_us.mean()
            insight(f"hybrid jobs have a median of {money(wm.loc['Hybrid', 'median'])} against "
                    f"{money(wm.loc['On-site', 'median'])} on-site, but only {hy_us:.0%} of hybrid jobs here are at US "
                    "companies. Location, not the work mode, drives most of that gap.")

    with tabs[6]:
        heat = view.pivot_table(index="job_family", columns="experience_label", values="salary_in_usd",
                                aggfunc="median", observed=True)
        cnt = view.pivot_table(index="job_family", columns="experience_label", values="salary_in_usd",
                               aggfunc="size", observed=True)
        cols = [c for c in F.EXPERIENCE_ORDER if c in heat.columns]
        heat, cnt = heat[cols].where(cnt[cols] >= 10), cnt[cols]
        heat = heat.loc[heat.median(axis=1).sort_values(ascending=False).index]
        shown = to_unit(heat)
        text = shown.map(lambda v: "" if pd.isna(v) else (f"{v / 1000:.0f}k"))
        fig = go.Figure(go.Heatmap(
            z=shown.values, x=cols, y=heat.index, colorscale=t["sequential"], text=text.values,
            texttemplate="%{text}", textfont=dict(size=13), customdata=cnt.loc[heat.index].values,
            hovertemplate="<b>%{y}</b>, %{x}<br>Median %{text}<br>%{customdata} salaries<extra></extra>",
            xgap=3, ygap=3, colorbar=dict(title=unit_words(), tickformat="~s")))
        style_fig(fig, height=400)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False, autorange="reversed")
        show(fig, key="ex_heat")
        how_to_read("Darker cells mean higher pay. Blank cells have fewer than 10 salaries.")
        insight("the step up with experience appears in every job family, and the gap between families grows at "
                "senior levels.")


# ==================================================================== saudi
def page_saudi() -> None:
    df = load_data()
    bench = load_benchmark()
    t = tokens()
    page_header("Saudi Arabia vs the world",
                "The dataset has only two salaries from Saudi companies, so this page uses salaries published by a "
                "recruiter survey, an HR platform and salary websites. They are shown next to the dataset's countries "
                "for the same job, but kept out of the model because they were measured differently.", "saudi")

    st.html("<div class='note'>Robert Walters reports <b>basic salary</b>, which in Saudi Arabia usually excludes "
            "allowances such as housing and transport, so full packages are higher. Crowd-sourced sites report total "
            "pay from small samples. Treat every Saudi figure as an indication, not an exact number.</div>")
    st.write("")

    c1, c2 = st.columns([1, 1.2])
    role = c1.segmented_control("Job", ["Data Scientist", "Data Analyst"], default="Data Scientist",
                                key="sa_role") or "Data Scientist"
    level = c2.segmented_control("Add this app's estimate for Saudi Arabia at level", F.EXPERIENCE_ORDER,
                                 default="Senior", key="sa_level")

    world = df[df.job_title == role].groupby(["company_location", "company_country"]).salary_in_usd
    world = pd.DataFrame({"low": world.quantile(0.25), "mid": world.median(), "high": world.quantile(0.75),
                          "n": world.size()}).reset_index()
    world = world[world.n >= 15].sort_values("mid")
    sa = bench[bench.role == role].copy()
    for c in ["min_sar_month", "mid_sar_month", "max_sar_month"]:
        sa[c] = sar_month_to_usd_year(sa[c])
    sa = sa.sort_values("mid_sar_month", na_position="first")

    rows = []
    for r in world.itertuples():
        rows.append(dict(label=f"{r.company_country} (dataset)", low=r.low, mid=r.mid, high=r.high, saudi=False,
                         detail=f"Dataset, {r.n} salaries<br>Middle half and median"))
    if level:
        bundle, _ = load_model()
        code = {v: k for k, v in F.EXPERIENCE_LABELS.items()}[level]
        est = M.predict_salary(bundle, pd.DataFrame([{"job_title": role, "experience_level": code,
                                                       "company_location": "SA", "company_size": "M",
                                                       "remote_ratio": 0, "employment_type": "FT",
                                                       "work_year": 2024}])).iloc[0]
        rows.append(dict(label=f"Saudi Arabia: this app's estimate ({level})", low=est.low, mid=est.predicted,
                         high=est.high, saudi=True, detail="Model estimate, medium company, on-site, 2024<br>"
                                                           "Built from very few Middle East records"))
    for r in sa.itertuples():
        basis = r.pay_basis.split(" (")[0].lower()
        rows.append(dict(label=f"Saudi Arabia: {r.source} ({basis})", low=r.min_sar_month, mid=r.mid_sar_month,
                         high=r.max_sar_month, saudi=True,
                         detail=f"{r.source_type}, {r.data_year}<br>{r.range_definition}<br>{r.sample_note}"))

    fig = go.Figure()
    for i, r in enumerate(rows):
        color, soft = (t["orange"], t["orange_soft"]) if r["saudi"] else (t["blue"], t["blue_soft"])
        if pd.notna(r["low"]) and pd.notna(r["high"]):
            fig.add_trace(go.Scatter(x=[to_unit(r["low"]), to_unit(r["high"])], y=[r["label"]] * 2, mode="lines",
                                     line=dict(color=soft, width=10), hoverinfo="skip", showlegend=False))
        if pd.notna(r["mid"]):
            rng = (f"{money(r['low'])} to {money(r['high'])}" if pd.notna(r["low"]) and pd.notna(r["high"])
                   else "no range published")
            fig.add_trace(go.Scatter(
                x=[to_unit(r["mid"])], y=[r["label"]], mode="markers", showlegend=False,
                marker=dict(color=color, size=12, line=dict(color=t["surface"], width=2)),
                hovertemplate=f"<b>{r['label']}</b><br>Middle value {money(r['mid'])}<br>Range {rng}<br>"
                              f"{r['detail']}<extra></extra>"))
    for name, color in [("Saudi Arabia (published or estimated)", t["orange"]), ("Dataset country", t["blue"])]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(color=color, size=11), name=name))
    style_fig(fig, height=max(320, 42 * len(rows) + 70), legend=True, grid="x")
    money_axis(fig, "x")
    x_top = max(v for r in rows for v in (r["high"], r["mid"]) if pd.notna(v))
    fig.update_xaxes(range=[0, to_unit(x_top) * 1.06])
    fig.update_yaxes(title_text="", categoryorder="array", categoryarray=[r["label"] for r in rows])
    show(fig, key="sa_range")
    how_to_read("Bars show a range and the dot its middle value. Blue rows are countries in the dataset (middle "
                "half of salaries). Orange rows are Saudi figures. Hover a row to see where it comes from.")

    sa_mid = bench[bench.role == role].mid_sar_month.dropna()
    sa_mid_usd = sar_month_to_usd_year(sa_mid)
    below = world[world.mid < sa_mid_usd.min()].company_country.tolist()
    above = world[world.mid > sa_mid_usd.max()].company_country.tolist()
    parts = []
    if below:
        parts.append(f"above {join_words(below)}")
    if above:
        parts.append(f"below {join_words(above)}")
    position = f" That places Saudi Arabia {', and '.join(parts)} in this data." if parts else ""
    insight(f"published Saudi figures for a {role} run from {money(sa_mid_usd.min())} to "
            f"{money(sa_mid_usd.max())}.{position}")

    st.subheader("Senior leadership")
    lead_titles = ["Head of Data", "Director of Data Science", "Head of Data Science", "Data Science Manager"]
    ds = df[df.job_title.isin(lead_titles)].groupby("job_title").salary_in_usd.agg(["median", "size"])
    ds = ds.assign(label=[f"{i} (dataset, mostly US)" for i in ds.index], saudi=False)
    lsa = bench[bench.level_note == "Leadership"].set_index("role")
    lsa = pd.DataFrame({"median": sar_month_to_usd_year(lsa.mid_sar_month), "size": np.nan,
                        "label": [f"{i} (Saudi Arabia, basic salary)" for i in lsa.index], "saudi": True})
    lead = pd.concat([ds, lsa]).sort_values("median")
    fig = go.Figure(go.Bar(
        y=lead.label, x=to_unit(lead["median"]), orientation="h",
        marker_color=[t["orange"] if s else t["blue"] for s in lead.saudi],
        text=[money(v, True) for v in lead["median"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=t["ink"]),
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"))
    style_fig(fig, height=360, grid="x")
    money_axis(fig, "x")
    fig.update_xaxes(range=[0, to_unit(lead["median"].max()) * 1.2])
    show(fig, key="sa_lead")
    insight("Robert Walters' Saudi averages for heads of AI, machine learning and analytics, and for Chief Data "
            "Officers, are at or above the dataset medians for similar, mostly US, leadership titles, even though "
            "they count basic salary only. Titles are not perfectly comparable, so read this as a direction, not a "
            "precise gap.")

    st.subheader("Sources")
    src = bench[["source", "role", "pay_basis", "min_sar_month", "mid_sar_month", "max_sar_month", "range_definition",
                 "sample_note", "data_year", "url"]].copy()
    for c in ["min_sar_month", "mid_sar_month", "max_sar_month"]:
        src[c] = src[c].map(lambda v: "n/a" if pd.isna(v) else f"{v:,.0f}")
    table(src, column_config={
        "url": st.column_config.LinkColumn("Link", display_text="Open"),
        "min_sar_month": "Low (SAR/month)", "mid_sar_month": "Middle (SAR/month)", "max_sar_month": "High (SAR/month)",
        "pay_basis": "Pay basis", "range_definition": "Range shown", "sample_note": "Sample",
        "data_year": "Period", "source": "Source", "role": "Role"})
    with st.expander("Why do the Saudi sources disagree?"):
        st.markdown(
            "* **Recruiter surveys** (Robert Walters) describe roles filled through recruiters, which are often "
            "senior and at large employers, and count basic salary only.\n"
            "* **Crowd-sourced sites** (Glassdoor, Levels.fyi, Paylab, PayScale) collect what people report, from "
            "small samples and with different definitions of pay.\n"
            "* **HR platforms** (ZenHR) publish typical ranges for a stated experience band.\n\n"
            "Looking at all of them together gives a more honest picture than picking one.")


# ==================================================================== model
def page_model() -> None:
    df = load_data()
    art = load_artifacts()
    bundle, status = load_model()
    meta = bundle["meta"]
    tm = meta.get("test_metrics") or art["meta"].get("test_metrics", {})
    t = tokens()
    page_header("How the model works", "A plain-language look at the salary estimator: what it learns from, how "
                "accurate it is on salaries it has never seen, and why it cannot be exact.", "model")

    steps = [
        ("It learns from past salaries.", f"The model studied {meta['trained_on_rows']:,} unique salary records "
         "(exact duplicates removed) and learned how much each factor tends to add or subtract."),
        ("It looks at seven facts about a job.", "Job title, experience level, company country, company size, "
         "work mode, employment type and year. Nothing about the person themselves."),
        ("It gives a typical salary and a likely range.", "The range covers where most people with the same profile "
         "fall, because identical profiles are paid very differently."),
    ]
    st.html("".join(f"<div class='step'><div class='step-n'>{i}</div><div><strong>{h}</strong> {b}</div></div>"
                    for i, (h, b) in enumerate(steps, 1)))

    m = st.columns(4)
    if tm:
        m[0].metric("Typical error", esc(money(tm["MAE"])), border=True,
                    help="Mean absolute error on 1,719 test salaries the model never saw.")
        m[1].metric("Better than guessing", f"{1 - tm['MAE'] / tm['baseline_MAE']:.0%}", border=True,
                    help="Compared with always guessing the median salary.")
        m[2].metric("Within 20% of the real salary", f"{tm['within_20pct']:.0%}", border=True)
        m[3].metric("Real salary inside the range", f"{tm['range_coverage']:.0%}", border=True,
                    help="Share of test salaries that fell inside the predicted 10th to 90th percentile range.")
    if status == "retrained":
        st.info("The saved model file could not be loaded in this environment, so the same model was trained again "
                "from the data when the app started. The results are the same.")

    tabs = st.tabs(["Which model", "Accuracy", "What matters", "Same profile, different pay", "As classification",
                    "Technical details"])

    with tabs[0]:
        comp = art["comparison"]
        if comp is not None:
            comp = comp.copy()
            order = comp.groupby("model")["CV MAE"].min().sort_values(ascending=False).index.tolist()
            fig = go.Figure()
            for target, color, name in [("salary", t["blue_soft"], "Trained on salary"),
                                        ("log(salary)", t["blue"], "Trained on log of salary")]:
                sub = comp[comp.target == target].set_index("model").loc[order]
                fig.add_trace(go.Bar(
                    y=order, x=to_unit(sub["CV MAE"]), orientation="h", name=name, marker_color=color,
                    error_x=dict(type="data", array=to_unit(sub["CV MAE sd"]), color=t["muted"], thickness=1.2),
                    customdata=np.stack([[money(v) for v in sub["CV MAE"]], [money(v) for v in sub["CV MAE sd"]]],
                                        axis=1),
                    hovertemplate="<b>%{y}</b><br>Average error %{customdata[0]}<br>Varies by about "
                                  "%{customdata[1]} between folds<extra></extra>"))
            if tm:
                fig.add_vline(x=to_unit(tm["baseline_MAE"]), line_color=t["ink"], line_width=1.5,
                              annotation_text="Always guessing the median", annotation_position="top left",
                              annotation_font=dict(color=t["ink"]))
            style_fig(fig, height=360, legend=True, grid="x")
            money_axis(fig, "x")
            fig.update_xaxes(title_text=f"Average error ({unit_words()}), lower is better")
            fig.update_layout(barmode="group", bargap=0.3)
            show(fig, key="mo_comp")
            how_to_read("Four models were each tested five times on different slices of the data (cross-validation). "
                        "The thin whiskers show how much the result moved between slices.")
            insight("all four models land within a few hundred dollars of each other, less than the normal variation "
                    "between slices. The limit is the information in the data, not the algorithm, so the app uses the "
                    "simplest one: linear regression with a small penalty (Ridge), trained on the log of salary.")

    with tabs[1]:
        test = art["test"]
        if test is not None:
            fig = go.Figure(go.Scattergl(
                x=to_unit(test.actual), y=to_unit(test.predicted), mode="markers",
                marker=dict(color=t["blue"], size=6, opacity=0.35),
                customdata=np.stack([[money(v) for v in test.actual], [money(v) for v in test.predicted],
                                     [money(v) for v in test.low], [money(v) for v in test.high]], axis=1),
                hovertemplate="Actual %{customdata[0]}<br>Predicted %{customdata[1]}<br>"
                              "Range %{customdata[2]} to %{customdata[3]}<extra></extra>"))
            lim = to_unit(np.percentile(test.actual, 99.5))
            fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", line=dict(color=t["ink"], width=1.2),
                                     hoverinfo="skip"))
            style_fig(fig, height=460, grid="both")
            money_axis(fig, "x")
            money_axis(fig, "y")
            fig.update_xaxes(range=[0, lim], title_text=f"Actual salary ({unit_words()})")
            fig.update_yaxes(range=[0, lim], title_text=f"Predicted salary ({unit_words()})")
            show(fig, key="mo_scatter")
            how_to_read("Each dot is one test salary. Dots on the line are perfect predictions.")
            insight(f"the model gets the general level right but not each person: R² is {tm.get('R2', 0):.2f}, so "
                    "it explains about a third of the differences in pay. It rarely predicts very high salaries, "
                    "because the inputs cannot tell a $150K and a $400K senior apart.")

    with tabs[2]:
        imp = art["importance"]
        if imp is not None:
            imp = imp.sort_values("MAE increase")
            fig = go.Figure(go.Bar(
                y=imp.input, x=to_unit(imp["MAE increase"]), orientation="h", marker_color=t["blue"],
                text=[money(v, True) for v in imp["MAE increase"]], textposition="outside", cliponaxis=False,
                textfont=dict(color=t["ink"]),
                hovertemplate="<b>%{y}</b><br>Error grows by %{text} when this input is shuffled<extra></extra>"))
            style_fig(fig, height=330, grid="x")
            money_axis(fig, "x")
            fig.update_xaxes(title_text=f"Extra error when the input is scrambled ({unit_words()})",
                             range=[0, to_unit(imp["MAE increase"].max()) * 1.3])
            show(fig, key="mo_imp")
            how_to_read("To see what the model relies on, each input was scrambled in turn and the extra error was "
                        "measured. Bigger bars mean the model leans on that input more.")
            insight("company country, job title and experience level drive the estimate. Company size adds almost "
                    "nothing once the country is known, because small companies in this data are mostly outside "
                    "the US.")

    with tabs[3]:
        mf = F.model_frame(df)
        top = mf.groupby(F.MODEL_INPUTS).size().sort_values(ascending=False).index[0]
        mask = np.logical_and.reduce([mf[c] == v for c, v in zip(F.MODEL_INPUTS, top)])
        same = mf[mask]
        fig = go.Figure(go.Box(x=to_unit(same.salary_in_usd), boxpoints="all", jitter=0.6, pointpos=0,
                               marker=dict(color=t["blue"], size=6, opacity=0.5), line=dict(color=t["blue"]),
                               fillcolor="rgba(42,120,214,0.10)", name="",
                               hovertemplate="%{x}<extra></extra>"))
        style_fig(fig, height=260, grid="x")
        money_axis(fig, "x")
        show(fig, key="mo_same")
        labels = dict(zip(F.MODEL_INPUTS, top))
        st.markdown(f"These are **{len(same)} salaries** with exactly the same seven inputs: "
                    f"{labels['job_title']}, {F.EXPERIENCE_LABELS[labels['experience_level']]}, "
                    f"{F.COUNTRY_NAMES[labels['company_location']]}, {F.COMPANY_SIZE_LABELS[labels['company_size']]} "
                    f"company, {F.WORK_MODE_LABELS[labels['remote_ratio']].lower()}, "
                    f"{F.EMPLOYMENT_LABELS[labels['employment_type']].lower()}, {labels['work_year']}.")
        insight(f"they range from {money(same.salary_in_usd.min())} to {money(same.salary_in_usd.max())}. To the "
                "model these people look identical, so no algorithm could tell them apart. The missing information "
                "(company, city, skills, education, bonuses) is not in the data.")

    with tabs[4]:
        clf = art["classification"]
        st.markdown("The same question can be asked as a **classification**: is a salary Low, Medium or High (each a "
                    "third of the training data)? Random guessing would be right a third of the time.")
        if clf is not None:
            table(clf.round(3))
            insight(f"the best classifier is right {clf.Accuracy.max():.0%} of the time, well above 33% by chance but "
                    "far from perfect. It is the same message as the salary estimate: the data supports rough levels, "
                    "not exact pay.")

    with tabs[5]:
        st.markdown(
            f"* **Model:** {meta['model_name']}, trained on the log of salary (penalty strength "
            f"{meta.get('best_params', art['meta'].get('best_params', {})).get('alpha', 'n/a')}).\n"
            "* **Inputs:** job title (titles with 30+ records kept, rarer ones grouped by job family), job family, "
            "seniority words in the title, company country (countries with 20+ records kept, others grouped by "
            "region), region, experience (1 to 4), company size (1 to 3), work mode, employment type, year.\n"
            "* **Encoding:** one-hot for categories without order, ranks for ordered ones, scaling for numbers.\n"
            "* **Range:** two quantile gradient boosting models give the 10th and 90th percentiles.\n"
            "* **Left out (data leakage):** salary and salary currency, which reveal the answer.\n"
            f"* **Evaluation:** 80/20 train/test split of unique rows and 5-fold cross-validation. The deployed model "
            f"was then refitted on all {meta['trained_on_rows']:,} unique rows.\n"
            f"* **Versions:** scikit-learn {meta.get('sklearn_version', 'n/a')}, trained on "
            f"{meta.get('trained_on', 'n/a')}. Model status in this session: {status}.")


# ================================================================= estimate
def page_estimate() -> None:
    df = load_data()
    bench = load_benchmark()
    bundle, _ = load_model()
    t = tokens()
    page_header("Estimate a salary", "Describe a job and the model returns a typical salary and a likely range, "
                "based on salaries from 2020 to 2024. It is an estimate to orient a conversation, not an offer.",
                "estimate")

    titles = df.job_title.value_counts().index.tolist()
    countries = sorted(df.company_country.unique())
    name_to_code = {v: k for k, v in F.COUNTRY_NAMES.items()}

    left, right = st.columns([1, 1.35], gap="large")
    with left:
        with st.container(border=True):
            title = st.selectbox("Job title", titles, index=titles.index("Data Scientist"),
                                 help="Sorted from most to least common. Type to search.", key="es_title")
            level = st.segmented_control("Experience level", F.EXPERIENCE_ORDER, default="Senior",
                                         key="es_level") or "Senior"
            country = st.selectbox("Company country", countries, index=countries.index("United States"),
                                   key="es_country")
            size = st.segmented_control("Company size", F.COMPANY_SIZE_ORDER, default="Medium",
                                        key="es_size") or "Medium"
            mode = st.segmented_control("Work mode", F.WORK_MODE_ORDER, default="On-site", key="es_mode") or "On-site"
            emp = st.selectbox("Employment type", list(F.EMPLOYMENT_LABELS.values()), key="es_emp")
            year = st.select_slider("Year", options=[2020, 2021, 2022, 2023, 2024], value=2024, key="es_year",
                                    help="The data ends in 2024, so later years cannot be estimated.")

    code_of = lambda mapping, label: {v: k for k, v in mapping.items()}[label]
    row = {"job_title": title, "experience_level": code_of(F.EXPERIENCE_LABELS, level),
           "company_location": name_to_code[country], "company_size": code_of(F.COMPANY_SIZE_LABELS, size),
           "remote_ratio": code_of(F.WORK_MODE_LABELS, mode), "employment_type": code_of(F.EMPLOYMENT_LABELS, emp),
           "work_year": year}
    est = M.predict_salary(bundle, pd.DataFrame([row])).iloc[0]

    with right:
        st.markdown(f"**Estimated salary for a {level.lower()} {title}, {country}**")
        st.html(f"<div class='big-estimate'>{money(est.predicted)}</div>")
        other = (f"{est.predicted * F.USD_TO_SAR / 12:,.0f} SAR a month" if unit().startswith("USD")
                 else f"${est.predicted:,.0f} a year")
        st.html(f"<div class='estimate-sub'>Shown in {unit_words()}, which is about {other}. Most people with "
                f"this profile earn between <strong>{money(est.low)}</strong> and <strong>{money(est.high)}</strong>."
                "</div>")

        similar = df[(df.job_title == title) & (df.experience_level == row["experience_level"])
                     & (df.company_location == row["company_location"])]
        scope, similar_label = f"{level} {title}s in {country}", "Similar records"
        if len(similar) < 5:
            similar = df[(df.job_title == title) & (df.experience_level == row["experience_level"])]
            scope, similar_label = f"{level} {title}s in all countries", "Same job, all countries"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[to_unit(est.low), to_unit(est.high)], y=["Estimate"] * 2, mode="lines",
                                 line=dict(color=t["blue_soft"], width=14), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=[to_unit(est.predicted)], y=["Estimate"], mode="markers", showlegend=False,
                                 marker=dict(color=t["blue"], size=16, line=dict(color=t["surface"], width=2)),
                                 hovertemplate=f"Estimate {money(est.predicted)}<br>Range {money(est.low)} to "
                                               f"{money(est.high)}<extra></extra>"))
        if len(similar) >= 5:
            q1, q2, q3 = similar.salary_in_usd.quantile([0.25, 0.5, 0.75])
            fig.add_trace(go.Scatter(x=[to_unit(q1), to_unit(q3)], y=[similar_label] * 2, mode="lines",
                                     line=dict(color=t["axis"], width=14), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(x=[to_unit(q2)], y=[similar_label], mode="markers", showlegend=False,
                                     marker=dict(color=t["muted"], size=14, line=dict(color=t["surface"], width=2)),
                                     hovertemplate=f"{scope}: median {money(q2)}<br>Middle half {money(q1)} to "
                                                   f"{money(q3)}<br>{len(similar)} salaries<extra></extra>"))
        style_fig(fig, height=170, grid="x")
        money_axis(fig, "x")
        x_max = max(est.high, similar.salary_in_usd.quantile(0.75) if len(similar) >= 5 else 0)
        x_min = min(est.low, similar.salary_in_usd.quantile(0.25) if len(similar) >= 5 else est.low)
        fig.update_xaxes(title_text="", range=[to_unit(x_min) * 0.9, to_unit(x_max) * 1.06])
        fig.update_yaxes(categoryorder="array", categoryarray=[similar_label, "Estimate"])
        show(fig, key="es_range")
        if len(similar) >= 5:
            st.caption(f"Grey: the middle half and median of {len(similar):,} real salaries for {scope}.")
        else:
            st.caption("There are fewer than 5 real salaries for this title and level, so no comparison is shown.")

    n_country = int((df.company_location == row["company_location"]).sum())
    if row["company_location"] == "SA":
        role_bench = bench[bench.role == title]
        text = (f"The dataset has only {n_country} salaries from Saudi companies, so this estimate leans on the "
                "Middle East average. ")
        mids = role_bench.mid_sar_month.dropna()
        if not mids.empty:
            text += (f"Published Saudi figures for a {title} have middle values from {mids.min():,.0f} to "
                     f"{mids.max():,.0f} SAR a month. The Saudi Arabia page shows each source.")
        else:
            text += "The Saudi Arabia page compares published Saudi salaries for several roles."
        st.warning(text)
        st.page_link(PAGES["saudi"], icon=PAGES["saudi"].icon)
    elif n_country < 20:
        st.warning(f"Only {n_country} salaries come from companies in {country}, so the estimate leans on the "
                   f"{F.REGION_OF.get(row['company_location'], 'regional')} average.")
    if F.job_family(title) and df.job_title.value_counts().get(title, 0) < 30:
        st.info(f"{title} has fewer than 30 salaries in the data, so the model treats it like other "
                f"{F.job_family(title)} roles.")

    st.subheader("How experience changes this estimate")
    ladder = pd.DataFrame([{**row, "experience_level": code_of(F.EXPERIENCE_LABELS, lv)} for lv in F.EXPERIENCE_ORDER])
    lp = M.predict_salary(bundle, ladder)
    fig = go.Figure(go.Bar(
        x=F.EXPERIENCE_ORDER, y=to_unit(lp.predicted),
        marker_color=[t["blue"] if lv == level else t["blue_soft"] for lv in F.EXPERIENCE_ORDER],
        text=[money(v, True) for v in lp.predicted], textposition="outside", cliponaxis=False,
        textfont=dict(color=t["ink"]),
        customdata=np.stack([[money(v) for v in lp.low], [money(v) for v in lp.high]], axis=1),
        hovertemplate="<b>%{x}</b><br>Estimate %{text}<br>Range %{customdata[0]} to %{customdata[1]}<extra></extra>"))
    style_fig(fig, height=300)
    money_axis(fig)
    fig.update_yaxes(range=[0, to_unit(lp.predicted.max()) * 1.25], title_text="")
    show(fig, key="es_ladder")
    how_to_read("Same job and company, only the experience level changes. The highlighted bar is your selection.")
    with st.expander("How sure is this estimate?"):
        tm = bundle["meta"].get("test_metrics") or {}
        if tm:
            st.markdown(esc(
                f"On {tm.get('test_rows', 0):,} salaries the model had never seen, the typical error was "
                f"{money(tm['MAE'])}, and {tm['within_20pct']:.0%} of estimates were within 20% of the real salary. "
                f"The range contained the real salary {tm['range_coverage']:.0%} of the time. The data does not "
                "include the company, city, skills or bonuses, which explain much of the rest."))


# ================================================================ navigation
PAGES: dict = {}


def build_pages() -> dict:
    return {
        "overview": st.Page(page_overview, title="Overview", icon=":material/home:", default=True),
        "data": st.Page(page_data, title="The data", icon=":material/table_chart:", url_path="data"),
        "explore": st.Page(page_explore, title="Explore salaries", icon=":material/insights:", url_path="explore"),
        "saudi": st.Page(page_saudi, title="Saudi Arabia vs the world", icon=":material/public:", url_path="saudi"),
        "model": st.Page(page_model, title="How the model works", icon=":material/model_training:",
                         url_path="model"),
        "estimate": st.Page(page_estimate, title="Estimate a salary", icon=":material/calculate:",
                            url_path="estimate"),
    }


def main() -> None:
    st.set_page_config(page_title="Data & AI Salaries", page_icon=":material/payments:", layout="wide")
    PAGES.update(build_pages())
    st.navigation(list(PAGES.values()), position="top").run()


if __name__ == "__main__":
    main()
