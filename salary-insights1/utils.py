"""Shared helpers for the Streamlit app: data loading, currency, chart style."""
import json
from pathlib import Path

import joblib
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ROOT = Path(__file__).parent
USD_TO_SAR = 3.75
EXP_ORDER = ["Entry", "Mid", "Senior", "Executive"]
SETTING_ORDER = ["On-site", "Hybrid", "Remote"]
SIZE_ORDER = ["Small", "Medium", "Large"]

# Calm palette: one accent, one secondary, neutrals
ACCENT = "#6FB8A6"
SECOND = "#8FA9C9"
WARM = "#D9A86C"
MUTED = "#5B6672"
GRID = "#26303A"
TEXT = "#E3E8EC"
SEQ = ["#1E3B3A", "#2C5D57", "#3F8277", "#6FB8A6", "#A8DCCD"]

pio.templates["calm"] = go.layout.Template(
    layout=dict(
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[ACCENT, SECOND, WARM, "#B48EAD", "#88C0D0", "#A3BE8C"],
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        margin=dict(l=10, r=10, t=40, b=10),
        hoverlabel=dict(bgcolor="#1A2129", font_color=TEXT),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
)
pio.templates.default = "plotly_dark+calm"


@st.cache_data
def load_salaries():
    return pd.read_csv(ROOT / "data" / "salaries_clean.csv")


@st.cache_data
def load_benchmark():
    return pd.read_csv(ROOT / "data" / "saudi_benchmark_clean.csv")


@st.cache_data
def load_test_predictions():
    return pd.read_csv(ROOT / "data" / "test_predictions.csv")


@st.cache_data
def load_metadata():
    with open(ROOT / "models" / "model_metadata.json") as f:
        return json.load(f)


@st.cache_resource
def load_model():
    return joblib.load(ROOT / "models" / "salary_model.pkl")


# ---------- Currency ----------
CURRENCIES = ["USD per year", "SAR per month"]


def currency():
    return st.session_state.get("currency", CURRENCIES[0])


def is_sar():
    return currency() == "SAR per month"


def convert(usd_year):
    """Convert yearly USD (number or Series) to the selected currency."""
    return usd_year * USD_TO_SAR / 12 if is_sar() else usd_year


def unit():
    return "SAR / month" if is_sar() else "USD / year"


def money(usd_year, short=True):
    v = convert(usd_year)
    if is_sar():
        return f"{v / 1000:,.1f}K SAR" if short else f"{v:,.0f} SAR"
    return f"${v / 1000:,.0f}K" if short else f"${v:,.0f}"


def both(usd_year):
    """Show a yearly USD value in both currencies."""
    return f"${usd_year:,.0f} per year  |  {usd_year * USD_TO_SAR / 12:,.0f} SAR per month"


# ---------- Small UI helpers ----------
def page_header(title, subtitle):
    st.title(title)
    st.markdown(f"<p style='color:#9AA6B2;font-size:1.05rem;margin-top:-0.6rem'>{subtitle}</p>",
                unsafe_allow_html=True)


def note(text):
    """Short explanation under a chart."""
    st.markdown(f"<p style='color:#9AA6B2;font-size:0.92rem;margin-top:-0.5rem'>{text}</p>",
                unsafe_allow_html=True)


def median_by(df, col, min_count=1):
    g = df.groupby(col)["salary_in_usd"].agg(["median", "count"])
    return g[g["count"] >= min_count].sort_values("median")


# ---------- Saudi comparison ----------
INDIVIDUAL_ROLES = ["Data Analyst", "Data Scientist", "Data Engineer"]


def global_group(df, role):
    """Rows in the global data that match a Saudi benchmark role."""
    if role in INDIVIDUAL_ROLES:
        return df[df["job_title"] == role]
    return df[(df["job_family"] == "Leadership & Management") & (df["experience"].isin(["Senior", "Executive"]))]


def closest_benchmark_role(title, family):
    """Pick the closest benchmark role for a job title from the global data."""
    if title in ["Data Analyst", "Data Scientist", "Data Engineer", "Head of Data Analytics",
                 "Head of Machine Learning", "Head of AI", "Chief Data Officer"]:
        return [title]
    if family == "Leadership & Management":
        t = title.lower()
        if "machine learning" in t:
            return ["Head of Machine Learning"]
        if " ai" in f" {t}":
            return ["Head of AI"]
        if "analytic" in t:
            return ["Head of Data Analytics"]
        if "chief" in t:
            return ["Chief Data Officer"]
        return ["Head of Data Analytics", "Chief Data Officer"]
    return {
        "Analytics & BI": ["Data Analyst"],
        "Data Management & Strategy": ["Data Analyst"],
        "Data Engineering": ["Data Engineer"],
    }.get(family, ["Data Scientist"])


def pad_x(fig, max_value, factor=1.18):
    """Leave room on the right for bar labels."""
    fig.update_xaxes(range=[0, max_value * factor])
    return fig


def pad_y(fig, max_value, factor=1.15):
    """Leave room on top for bar labels."""
    fig.update_yaxes(range=[0, max_value * factor])
    return fig


def money_range(low_usd, high_usd):
    """Short range text that fits in a metric, e.g. '$100K to $246K' or '18.7K to 57.9K SAR'."""
    if is_sar():
        return f"{convert(low_usd) / 1000:,.1f}K to {convert(high_usd) / 1000:,.1f}K SAR"
    return f"\\${low_usd / 1000:,.0f}K to \\${high_usd / 1000:,.0f}K"


# ISO alpha-2 -> alpha-3 codes for the world map (all company countries in the data)
ISO3 = {'AD': 'AND', 'AE': 'ARE', 'AM': 'ARM', 'AR': 'ARG', 'AS': 'ASM', 'AT': 'AUT', 'AU': 'AUS', 'BA': 'BIH',
        'BE': 'BEL', 'BR': 'BRA', 'BS': 'BHS', 'CA': 'CAN', 'CF': 'CAF', 'CH': 'CHE', 'CL': 'CHL', 'CN': 'CHN',
        'CO': 'COL', 'CZ': 'CZE', 'DE': 'DEU', 'DK': 'DNK', 'DZ': 'DZA', 'EC': 'ECU', 'EE': 'EST', 'EG': 'EGY',
        'ES': 'ESP', 'FI': 'FIN', 'FR': 'FRA', 'GB': 'GBR', 'GH': 'GHA', 'GI': 'GIB', 'GR': 'GRC', 'HK': 'HKG',
        'HN': 'HND', 'HR': 'HRV', 'HU': 'HUN', 'ID': 'IDN', 'IE': 'IRL', 'IL': 'ISR', 'IN': 'IND', 'IQ': 'IRQ',
        'IR': 'IRN', 'IT': 'ITA', 'JP': 'JPN', 'KE': 'KEN', 'KR': 'KOR', 'LB': 'LBN', 'LT': 'LTU', 'LU': 'LUX',
        'LV': 'LVA', 'MD': 'MDA', 'MT': 'MLT', 'MU': 'MUS', 'MX': 'MEX', 'MY': 'MYS', 'NG': 'NGA', 'NL': 'NLD',
        'NO': 'NOR', 'NZ': 'NZL', 'OM': 'OMN', 'PH': 'PHL', 'PK': 'PAK', 'PL': 'POL', 'PR': 'PRI', 'PT': 'PRT',
        'QA': 'QAT', 'RO': 'ROU', 'RU': 'RUS', 'SA': 'SAU', 'SE': 'SWE', 'SG': 'SGP', 'SI': 'SVN', 'TH': 'THA',
        'TR': 'TUR', 'UA': 'UKR', 'US': 'USA', 'VN': 'VNM', 'ZA': 'ZAF'}
