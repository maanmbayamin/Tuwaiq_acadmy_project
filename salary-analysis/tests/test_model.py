"""Checks that the saved model loads and behaves sensibly (src/modeling.py)."""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from src import features as F
from src import modeling as M


@pytest.fixture(scope="module")
def bundle():
    return M.load_bundle()


def profile(**changes):
    base = {"job_title": "Data Scientist", "experience_level": "SE", "company_location": "US",
            "company_size": "M", "remote_ratio": 0, "employment_type": "FT", "work_year": 2024}
    return {**base, **changes}


def test_saved_files_exist():
    for name in ["salary_model.joblib", "metrics.json", "model_comparison.csv", "test_predictions.csv",
                 "feature_importance.csv", "duplicates_experiment.csv", "classification_comparison.csv"]:
        assert (M.MODEL_DIR / name).exists(), name


def test_metrics_are_recorded_and_beat_the_baseline():
    meta = json.loads(M.METRICS_PATH.read_text())
    tm = meta["test_metrics"]
    assert {"MAE", "MSE", "RMSE", "R2", "baseline_MAE", "range_coverage"} <= set(tm)
    assert tm["MAE"] < 0.85 * tm["baseline_MAE"]
    assert 0.2 < tm["R2"] < 0.5
    assert meta["duplicates_dropped_for_model"] is True


def test_predictions_are_positive_and_ranges_are_ordered(bundle):
    df = F.load_clean().sample(500, random_state=0)
    pred = M.predict_salary(bundle, df)
    assert (pred.predicted > 0).all()
    assert ((pred.low <= pred.predicted) & (pred.predicted <= pred.high)).all()


def test_more_experience_means_higher_estimate(bundle):
    rows = pd.DataFrame([profile(experience_level=e) for e in ["EN", "MI", "SE", "EX"]])
    p = M.predict_salary(bundle, rows).predicted.values
    assert np.all(np.diff(p) > 0)


def test_us_estimate_is_above_uk_and_india(bundle):
    rows = pd.DataFrame([profile(company_location=c) for c in ["US", "GB", "IN"]])
    us, gb, india = M.predict_salary(bundle, rows).predicted.values
    assert us > gb > india


def test_saudi_estimate_is_within_published_range(bundle):
    est = M.predict_salary(bundle, pd.DataFrame([profile(company_location="SA")])).predicted.iloc[0]
    monthly_sar = est * F.USD_TO_SAR / 12
    bench = F.load_saudi_benchmark()
    ds = bench[bench.role == "Data Scientist"]
    assert ds.min_sar_month.min() <= monthly_sar <= ds.max_sar_month.max()


def test_retraining_gives_a_working_model():
    df = F.load_clean()
    small = F.model_frame(df).sample(2000, random_state=1)
    fresh = M.train_bundle(small, "test", Ridge(alpha=10.0), True, True)
    p = M.predict_salary(fresh, pd.DataFrame([profile()]))
    assert np.isfinite(p.values).all()


def test_saudi_benchmark_file_is_complete():
    bench = F.load_saudi_benchmark()
    assert len(bench) == 11
    assert bench.url.str.startswith("https://").all()
    assert (bench.min_sar_month.dropna() <= bench.max_sar_month.dropna()).all()
