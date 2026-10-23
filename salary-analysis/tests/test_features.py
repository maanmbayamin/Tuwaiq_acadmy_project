"""Checks for data loading, cleaning and feature engineering (src/features.py)."""

import numpy as np
import pandas as pd

from src import features as F


def test_raw_data_shape_and_no_missing():
    raw = F.load_raw()
    assert raw.shape == (13972, 11)
    assert raw.isna().sum().sum() == 0


def test_strip_finds_no_hidden_spaces_and_duplicates_are_real():
    original = pd.read_csv(F.DATA_PATH)
    stripped = F.load_raw()
    assert (original.select_dtypes(exclude="number") == stripped.select_dtypes(exclude="number")).all().all()
    assert original.duplicated().sum() == stripped.duplicated().sum() == 5378


def test_every_title_gets_one_of_seven_families():
    df = F.load_clean()
    assert set(df.job_family) <= set(F.JOB_FAMILY_ORDER)
    assert df.job_family.nunique() == 7


def test_family_and_seniority_examples():
    assert F.job_family("ML Engineer") == "Machine Learning & AI"
    assert F.job_family("Business Intelligence Developer") == "Analytics & BI"
    assert F.job_family("Applied Scientist") == "Research"
    assert F.job_family("Data Modeler") == "Data Architecture"
    assert F.title_seniority("Head of Data") == "Leadership"
    assert F.title_seniority("Principal Data Scientist") == "Principal / Staff"
    assert F.title_seniority("Data Analyst") == "Individual contributor"


def test_every_country_has_a_name_region_and_iso3_code():
    raw = F.load_raw()
    codes = set(raw.company_location) | set(raw.employee_residence)
    assert codes <= set(F.COUNTRY_NAMES)
    assert codes <= set(F.COUNTRY_ISO3)
    assert set(raw.company_location) <= set(F.REGION_OF)


def test_new_columns_are_consistent():
    df = F.load_clean()
    assert np.allclose(df.salary_sar, df.salary_in_usd * 3.75)
    assert np.allclose(df.monthly_sar, df.salary_sar / 12)
    assert df.experience_rank.between(1, 4).all()
    assert set(df.work_mode.astype(str)) == {"On-site", "Hybrid", "Remote"}
    assert df.salary_band.isna().sum() == 0
    assert df.is_outlier.sum() == 253


def test_iqr_bounds_follow_the_course_formula():
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8])
    q1, q3 = s.quantile([0.25, 0.75])
    assert F.iqr_bounds(s) == (q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1))


def test_model_frame_drops_only_exact_duplicates():
    df = F.load_clean()
    assert len(F.model_frame(df)) == 8594
    assert len(F.model_frame(df, drop_duplicates=False)) == len(df)


def test_feature_builder_handles_unseen_values():
    df = F.load_clean()
    builder = F.SalaryFeatureBuilder().fit(df[F.MODEL_INPUTS])
    new = pd.DataFrame([{"job_title": "Brand New Title", "experience_level": "SE", "company_location": "ZZ",
                         "company_size": "M", "remote_ratio": 100, "employment_type": "FT", "work_year": 2024}])
    out = builder.transform(new)
    assert out.title_group.iloc[0].startswith("Other ")
    assert out.location_group.iloc[0] == "Other Other"
    assert out.isna().sum().sum() == 0
