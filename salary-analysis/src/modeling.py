"""Model building, evaluation, training and prediction helpers."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from .features import (MODEL_CATEGORICAL, MODEL_INPUTS, MODEL_NUMERIC, ROOT, TARGET,
                       SalaryFeatureBuilder)

MODEL_DIR = ROOT / "models"
BUNDLE_PATH = MODEL_DIR / "salary_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
RANDOM_STATE = 42
LOW_Q, HIGH_Q = 0.10, 0.90  # The predicted range covers the middle 80% of salaries.


def make_preprocessor(scale_numeric: bool) -> ColumnTransformer:
    numeric = StandardScaler() if scale_numeric else "passthrough"
    return ColumnTransformer([
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), MODEL_CATEGORICAL),
        ("numeric", numeric, MODEL_NUMERIC),
    ])


def make_pipeline(estimator, scale_numeric: bool = False, log_target: bool = False):
    pipe = Pipeline([
        ("features", SalaryFeatureBuilder()),
        ("prep", make_preprocessor(scale_numeric)),
        ("model", clone(estimator)),
    ])
    if log_target:
        return TransformedTargetRegressor(regressor=pipe, func=np.log, inverse_func=np.exp)
    return pipe


def candidate_models() -> dict:
    """The four models compared in the notebook. Linear Regression is the only
    one that needs scaled inputs; tree-based models do not."""
    return {
        "Linear Regression": (LinearRegression(), True),
        "Decision Tree": (DecisionTreeRegressor(max_depth=8, min_samples_leaf=20,
                                                random_state=RANDOM_STATE), False),
        "Random Forest": (RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                                                n_jobs=-1, random_state=RANDOM_STATE), False),
        "Gradient Boosting": (HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                                            random_state=RANDOM_STATE), False),
    }


def regression_metrics(y_true, y_pred) -> dict:
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "MSE": mse,
        "RMSE": float(np.sqrt(mse)),
        "R2": float(r2_score(y_true, y_pred)),
    }


def quantile_model(q: float):
    return make_pipeline(HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300,
                                                       learning_rate=0.05,
                                                       random_state=RANDOM_STATE))


def train_bundle(train_df: pd.DataFrame, model_name: str, estimator, scale_numeric: bool,
                 log_target: bool, test_metrics: dict | None = None, extra: dict | None = None) -> dict:
    """Fit the point model and the two range models on `train_df`."""
    X, y = train_df[MODEL_INPUTS], train_df[TARGET]
    point = make_pipeline(estimator, scale_numeric, log_target).fit(X, y)
    low = quantile_model(LOW_Q).fit(X, y)
    high = quantile_model(HIGH_Q).fit(X, y)
    meta = {
        "model_name": model_name,
        "log_target": log_target,
        "trained_on_rows": int(len(train_df)),
        "trained_on": date.today().isoformat(),
        "sklearn_version": sklearn.__version__,
        "inputs": MODEL_INPUTS,
        "range_quantiles": [LOW_Q, HIGH_Q],
        "test_metrics": test_metrics or {},
    }
    if extra:
        meta.update(extra)
    return {"model": point, "low": low, "high": high, "meta": meta}


def save_bundle(bundle: dict, path: Path = BUNDLE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path, compress=3)
    METRICS_PATH.write_text(json.dumps(bundle["meta"], indent=2))


def load_bundle(path: Path = BUNDLE_PATH) -> dict:
    return joblib.load(path)


def predict_salary(bundle: dict, inputs: pd.DataFrame) -> pd.DataFrame:
    """Point prediction plus a low/high range, in USD per year."""
    X = inputs[MODEL_INPUTS]
    point = bundle["model"].predict(X)
    low = bundle["low"].predict(X)
    high = bundle["high"].predict(X)
    # Quantile models are fitted separately, so keep low <= point <= high.
    low = np.minimum(low, point)
    high = np.maximum(high, point)
    return pd.DataFrame({"predicted": point, "low": low, "high": high}, index=inputs.index)
