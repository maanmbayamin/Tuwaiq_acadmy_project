"""Shared data loading, cleaning and feature engineering.

The notebook and the Streamlit app both import from this module, so every
column they show and every feature the model sees is built the same way.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "salaries.csv"
SAUDI_BENCHMARK_PATH = ROOT / "data" / "saudi_benchmark.csv"

TARGET = "salary_in_usd"
USD_TO_SAR = 3.75  # The Saudi riyal is pegged to the US dollar at 3.75.

RAW_COLUMNS = [
    "work_year", "experience_level", "employment_type", "job_title", "salary",
    "salary_currency", "salary_in_usd", "employee_residence", "remote_ratio",
    "company_location", "company_size",
]

# Raw columns the model is allowed to use. `salary` and `salary_currency` are
# excluded on purpose: `salary` is the target in another currency (leakage).
MODEL_INPUTS = [
    "job_title", "experience_level", "company_location", "company_size",
    "remote_ratio", "employment_type", "work_year",
]

# ---------------------------------------------------------------- label maps
EXPERIENCE_LABELS = {"EN": "Entry", "MI": "Mid", "SE": "Senior", "EX": "Executive"}
EXPERIENCE_RANK = {"EN": 1, "MI": 2, "SE": 3, "EX": 4}
EXPERIENCE_ORDER = ["Entry", "Mid", "Senior", "Executive"]

EMPLOYMENT_LABELS = {"FT": "Full-time", "PT": "Part-time", "CT": "Contract", "FL": "Freelance"}

COMPANY_SIZE_LABELS = {"S": "Small", "M": "Medium", "L": "Large"}
COMPANY_SIZE_RANK = {"S": 1, "M": 2, "L": 3}
COMPANY_SIZE_ORDER = ["Small", "Medium", "Large"]

WORK_MODE_LABELS = {0: "On-site", 50: "Hybrid", 100: "Remote"}
WORK_MODE_ORDER = ["On-site", "Hybrid", "Remote"]

SALARY_BAND_ORDER = ["Low", "Medium", "High", "Very high"]

COUNTRY_NAMES = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AM": "Armenia", "AR": "Argentina",
    "AS": "American Samoa", "AT": "Austria", "AU": "Australia", "BA": "Bosnia and Herzegovina",
    "BE": "Belgium", "BG": "Bulgaria", "BO": "Bolivia", "BR": "Brazil", "BS": "Bahamas",
    "CA": "Canada", "CF": "Central African Republic", "CH": "Switzerland", "CL": "Chile",
    "CN": "China", "CO": "Colombia", "CR": "Costa Rica", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "DO": "Dominican Republic", "DZ": "Algeria",
    "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt", "ES": "Spain", "FI": "Finland",
    "FR": "France", "GB": "United Kingdom", "GE": "Georgia", "GH": "Ghana", "GI": "Gibraltar",
    "GR": "Greece", "HK": "Hong Kong", "HN": "Honduras", "HR": "Croatia", "HU": "Hungary",
    "ID": "Indonesia", "IE": "Ireland", "IL": "Israel", "IN": "India", "IQ": "Iraq",
    "IR": "Iran", "IT": "Italy", "JE": "Jersey", "JP": "Japan", "KE": "Kenya",
    "KR": "South Korea", "KW": "Kuwait", "LB": "Lebanon", "LT": "Lithuania",
    "LU": "Luxembourg", "LV": "Latvia", "MD": "Moldova", "MT": "Malta", "MU": "Mauritius",
    "MX": "Mexico", "MY": "Malaysia", "NG": "Nigeria", "NL": "Netherlands", "NO": "Norway",
    "NZ": "New Zealand", "OM": "Oman", "PE": "Peru", "PH": "Philippines", "PK": "Pakistan",
    "PL": "Poland", "PR": "Puerto Rico", "PT": "Portugal", "QA": "Qatar", "RO": "Romania",
    "RS": "Serbia", "RU": "Russia", "SA": "Saudi Arabia", "SE": "Sweden",
    "SG": "Singapore", "SI": "Slovenia", "TH": "Thailand", "TN": "Tunisia", "TR": "Turkey",
    "UA": "Ukraine", "UG": "Uganda", "US": "United States", "UZ": "Uzbekistan",
    "VN": "Vietnam", "ZA": "South Africa",
}

# ISO alpha-3 codes, used by the world map in the app.
COUNTRY_ISO3 = {
    "AD": "AND", "AE": "ARE", "AM": "ARM", "AR": "ARG", "AS": "ASM", "AT": "AUT", "AU": "AUS",
    "BA": "BIH", "BE": "BEL", "BG": "BGR", "BO": "BOL", "BR": "BRA", "BS": "BHS", "CA": "CAN",
    "CF": "CAF", "CH": "CHE", "CL": "CHL", "CN": "CHN", "CO": "COL", "CR": "CRI", "CY": "CYP",
    "CZ": "CZE", "DE": "DEU", "DK": "DNK", "DO": "DOM", "DZ": "DZA", "EC": "ECU", "EE": "EST",
    "EG": "EGY", "ES": "ESP", "FI": "FIN", "FR": "FRA", "GB": "GBR", "GE": "GEO", "GH": "GHA",
    "GI": "GIB", "GR": "GRC", "HK": "HKG", "HN": "HND", "HR": "HRV", "HU": "HUN", "ID": "IDN",
    "IE": "IRL", "IL": "ISR", "IN": "IND", "IQ": "IRQ", "IR": "IRN", "IT": "ITA", "JE": "JEY",
    "JP": "JPN", "KE": "KEN", "KR": "KOR", "KW": "KWT", "LB": "LBN", "LT": "LTU", "LU": "LUX",
    "LV": "LVA", "MD": "MDA", "MT": "MLT", "MU": "MUS", "MX": "MEX", "MY": "MYS", "NG": "NGA",
    "NL": "NLD", "NO": "NOR", "NZ": "NZL", "OM": "OMN", "PE": "PER", "PH": "PHL", "PK": "PAK",
    "PL": "POL", "PR": "PRI", "PT": "PRT", "QA": "QAT", "RO": "ROU", "RS": "SRB", "RU": "RUS",
    "SA": "SAU", "SE": "SWE", "SG": "SGP", "SI": "SVN", "TH": "THA", "TN": "TUN", "TR": "TUR",
    "UA": "UKR", "UG": "UGA", "US": "USA", "UZ": "UZB", "VN": "VNM", "ZA": "ZAF",
}

_REGION_MEMBERS = {
    "North America": ["US", "CA"],
    "Latin America": ["MX", "PR", "BS", "CR", "DO", "HN", "AR", "BO", "BR", "CL", "CO", "EC", "PE"],
    "Europe": ["AD", "AT", "BA", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
               "FR", "GB", "GI", "GR", "HR", "HU", "IE", "IT", "JE", "LT", "LU", "LV", "MD",
               "MT", "NL", "NO", "PL", "PT", "RO", "RS", "RU", "SE", "SI", "UA"],
    "Middle East & North Africa": ["SA", "AE", "QA", "KW", "OM", "IQ", "IR", "IL", "LB",
                                   "TR", "EG", "DZ", "TN"],
    "Asia": ["CN", "HK", "ID", "IN", "JP", "KR", "MY", "PH", "PK", "SG", "TH", "VN", "UZ",
             "AM", "GE"],
    "Sub-Saharan Africa": ["CF", "GH", "KE", "MU", "NG", "ZA", "UG"],
    "Oceania": ["AU", "NZ", "AS"],
}
REGION_OF = {code: region for region, codes in _REGION_MEMBERS.items() for code in codes}
REGION_ORDER = list(_REGION_MEMBERS)

# --------------------------------------------------------------- job families
JOB_FAMILY_ORDER = [
    "Data Engineering", "Data Science", "Machine Learning & AI", "Research",
    "Analytics & BI", "Data Architecture", "Data Management & Strategy",
]

# Exact-title overrides for titles that keyword rules would misplace.
_FAMILY_OVERRIDES = {
    "Research Analyst": "Analytics & BI",
    "Quantitative Research Analyst": "Analytics & BI",
    "Data Specialist": "Data Management & Strategy",
    "Data Manager": "Data Management & Strategy",
    "Head of Data": "Data Management & Strategy",
    "Data Lead": "Data Management & Strategy",
    "Data Product Manager": "Data Management & Strategy",
    "Data Product Owner": "Data Management & Strategy",
    "AI Product Manager": "Data Management & Strategy",
    "Data Developer": "Data Engineering",
    "Analytics Engineer": "Data Engineering",
    "Analytics Engineering Manager": "Data Engineering",
    "Data Analytics Engineer": "Data Engineering",
    "BI Data Engineer": "Data Engineering",
    "Business Intelligence Engineer": "Analytics & BI",
    "Data Visualization Engineer": "Analytics & BI",
    "Data Science Engineer": "Data Science",
    "Autonomous Vehicle Technician": "Machine Learning & AI",
    "Machine Learning Modeler": "Machine Learning & AI",
    "Head of Machine Learning": "Machine Learning & AI",
    "Machine Learning Manager": "Machine Learning & AI",
    "Applied Scientist": "Research",
}

# Ordered keyword rules: the first match wins.
_FAMILY_RULES = [
    ("Data Architecture", ["architect", "modeler", "modeller"]),
    ("Research", ["research scientist", "research engineer", "researcher", "machine learning scientist",
                  "applied machine learning scientist", "ai scientist", "ai research"]),
    ("Machine Learning & AI", ["machine learning", "ml engineer", "ml ops", "mlops", "ai engineer",
                               "ai developer", "ai programmer", "ai software", "computer vision",
                               "nlp", "deep learning", "prompt engineer", "robotics"]),
    ("Data Science", ["data scien", "decision scientist"]),
    ("Analytics & BI", ["analyst", "business intelligence", "bi ", "power bi", "visualization",
                        "insight", "analytics"]),
    ("Data Engineering", ["engineer", "etl", "pipeline", "integration", "big data", "developer"]),
    ("Data Management & Strategy", ["manage", "strateg", "operations", "quality", "lead", "head"]),
]

_LEADERSHIP_WORDS = ["head of", "director", "manager", "lead", "chief", "vp ", "managing"]
_SENIOR_IC_WORDS = ["principal", "staff"]


def job_family(title: str) -> str:
    """Map a raw job title to one of seven job families."""
    if title in _FAMILY_OVERRIDES:
        return _FAMILY_OVERRIDES[title]
    t = f"{title.lower()} "
    for family, words in _FAMILY_RULES:
        if any(w in t for w in words):
            return family
    return "Data Management & Strategy"


def title_seniority(title: str) -> str:
    """Seniority signal carried by the title itself (separate from experience_level)."""
    t = f"{title.lower()} "
    if any(w in t for w in _LEADERSHIP_WORDS):
        return "Leadership"
    if any(w in t for w in _SENIOR_IC_WORDS):
        return "Principal / Staff"
    return "Individual contributor"


# ------------------------------------------------------------------ loading
def load_raw(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Read the CSV and strip whitespace from every text column."""
    df = pd.read_csv(path)
    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    for col in df.select_dtypes(exclude="number").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def iqr_bounds(s: pd.Series, k: float = 1.5) -> tuple[float, float]:
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with readable labels and the engineered analysis columns."""
    out = df.copy()
    out["experience_label"] = pd.Categorical(
        out["experience_level"].map(EXPERIENCE_LABELS), EXPERIENCE_ORDER, ordered=True)
    out["experience_rank"] = out["experience_level"].map(EXPERIENCE_RANK)
    out["employment_label"] = out["employment_type"].map(EMPLOYMENT_LABELS)
    out["company_size_label"] = pd.Categorical(
        out["company_size"].map(COMPANY_SIZE_LABELS), COMPANY_SIZE_ORDER, ordered=True)
    out["company_size_rank"] = out["company_size"].map(COMPANY_SIZE_RANK)
    out["work_mode"] = pd.Categorical(
        out["remote_ratio"].map(WORK_MODE_LABELS), WORK_MODE_ORDER, ordered=True)
    out["job_family"] = out["job_title"].map(job_family)
    out["title_seniority"] = out["job_title"].map(title_seniority)
    out["is_management"] = (out["title_seniority"] == "Leadership").astype(int)
    out["company_country"] = out["company_location"].map(COUNTRY_NAMES).fillna(out["company_location"])
    out["residence_country"] = out["employee_residence"].map(COUNTRY_NAMES).fillna(out["employee_residence"])
    out["region"] = out["company_location"].map(REGION_OF).fillna("Other")
    out["is_us"] = (out["company_location"] == "US").astype(int)
    out["cross_border"] = (out["employee_residence"] != out["company_location"]).astype(int)
    if TARGET in out:
        out["salary_sar"] = out[TARGET] * USD_TO_SAR
        out["monthly_sar"] = out["salary_sar"] / 12
        q1, q2, q3 = out[TARGET].quantile([0.25, 0.5, 0.75])
        out["salary_band"] = pd.cut(out[TARGET], [-np.inf, q1, q2, q3, np.inf],
                                    labels=SALARY_BAND_ORDER)
        low, high = iqr_bounds(out[TARGET])
        out["is_outlier"] = ((out[TARGET] < low) | (out[TARGET] > high)).astype(int)
        out["log_salary"] = np.log(out[TARGET])
    return out


def load_clean(path: Path | str = DATA_PATH) -> pd.DataFrame:
    """Raw data + engineered columns. Duplicates are kept (see the notebook)."""
    return add_features(load_raw(path))


def model_frame(df: pd.DataFrame, drop_duplicates: bool = True) -> pd.DataFrame:
    """Rows used to train the model. Exact duplicates are removed by default
    because the notebook shows unique rows give a slightly better model."""
    base = df[RAW_COLUMNS]
    return df.loc[~base.duplicated()] if drop_duplicates else df


# ------------------------------------------------------ model feature builder
class SalaryFeatureBuilder(BaseEstimator, TransformerMixin):
    """Turns the raw model inputs into model features.

    Rare job titles and countries are folded into a group learned during fit,
    so the saved pipeline accepts raw values and handles unseen ones.
    """

    def __init__(self, min_title_count: int = 30, min_country_count: int = 20):
        self.min_title_count = min_title_count
        self.min_country_count = min_country_count

    def fit(self, X: pd.DataFrame, y=None):
        X = pd.DataFrame(X)
        titles = X["job_title"].value_counts()
        countries = X["company_location"].value_counts()
        self.kept_titles_ = sorted(titles[titles >= self.min_title_count].index)
        self.kept_countries_ = sorted(countries[countries >= self.min_country_count].index)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = pd.DataFrame(X).copy()
        family = X["job_title"].map(job_family)
        region = X["company_location"].map(REGION_OF).fillna("Other")
        out = pd.DataFrame(index=X.index)
        out["title_group"] = np.where(X["job_title"].isin(self.kept_titles_),
                                      X["job_title"], "Other " + family)
        out["job_family"] = family
        out["title_seniority"] = X["job_title"].map(title_seniority)
        out["location_group"] = np.where(X["company_location"].isin(self.kept_countries_),
                                         X["company_location"], "Other " + region)
        out["region"] = region
        out["work_mode"] = X["remote_ratio"].map(WORK_MODE_LABELS).fillna("On-site")
        out["employment_type"] = X["employment_type"].astype(str)
        out["experience_rank"] = X["experience_level"].map(EXPERIENCE_RANK).astype(float)
        out["company_size_rank"] = X["company_size"].map(COMPANY_SIZE_RANK).astype(float)
        out["work_year"] = X["work_year"].astype(float)
        return out


MODEL_CATEGORICAL = ["title_group", "job_family", "title_seniority", "location_group",
                     "region", "work_mode", "employment_type"]
MODEL_NUMERIC = ["experience_rank", "company_size_rank", "work_year"]


def load_saudi_benchmark(path: Path | str = SAUDI_BENCHMARK_PATH) -> pd.DataFrame:
    return pd.read_csv(path)
