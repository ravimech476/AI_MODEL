"""
ml_core.py  — shared Machine-Learning engine for the dashboard.
Keeps the training/prediction logic in ONE place so the UI stays clean.
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor

MODEL_PATH = "xgb_severity_model.json"     # the ACTIVE model used for prediction
TARGET = "SEVERITY"
DROP_COLS = ["SEVERITY", "DATE", "POINT", "LATITUDE", "LONGITUDE"]
TEXT_COLS = ["METHOD", "SOIL"]

# The five models we offer: (display name, METHOD filter, SOIL filter)
# None = no filter on that column.
VARIANTS = [
    ("Combined (all data)",        None,             None),
    ("whole · soil=NO",            "whole",          "NO"),
    ("whole · soil=YES",           "whole",          "YES"),
    ("orthorectified · soil=NO",   "orthorectified", "NO"),
    ("orthorectified · soil=YES",  "orthorectified", "YES"),
]


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Drop identifier columns and encode text columns to numbers.
    Used identically for training AND prediction (train/serve consistency).
    Note: within a single variant, METHOD/SOIL are constant, so the model
    simply ignores them — the feature schema stays the same for every model."""
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns]).copy()
    for col in TEXT_COLS:
        if col in X.columns:
            X[col] = X[col].astype("category").cat.codes
    return X


def _train_core(data: pd.DataFrame):
    """Train one XGBoost on the given (already-cleaned) rows.
    Returns (model, metrics_dict, importance_series). Does NOT save to disk."""
    X = prepare_features(data)
    y = data[TARGET]

    if "POINT" in data.columns and data["POINT"].nunique() >= 5:
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        tr, te = next(gss.split(X, y, data["POINT"]))
        split_kind = "grid-grouped (honest)"
    else:
        from sklearn.model_selection import train_test_split
        tr, te = train_test_split(np.arange(len(X)), test_size=0.2, random_state=42)
        split_kind = "random"

    model = XGBRegressor(
        n_estimators=600, learning_rate=0.03, max_depth=5,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        reg_lambda=1.0, random_state=42, n_jobs=-1,
    )
    model.fit(X.iloc[tr], y.iloc[tr])
    pred = model.predict(X.iloc[te])

    metrics = {
        "R2": round(float(r2_score(y.iloc[te], pred)), 3),
        "RMSE": round(float(np.sqrt(mean_squared_error(y.iloc[te], pred))), 3),
        "MAE": round(float(mean_absolute_error(y.iloc[te], pred)), 3),
        "rows_used": len(data),
        "train_rows": len(tr),
        "test_rows": len(te),
        "split_kind": split_kind,
        "n_features": X.shape[1],
    }
    importance = (pd.Series(model.feature_importances_, index=X.columns)
                    .sort_values(ascending=False))
    return model, metrics, importance


def train_model(df: pd.DataFrame):
    """Backward-compatible: train ONE combined model and save it as active."""
    if TARGET not in df.columns:
        raise ValueError(f"Training file must contain a '{TARGET}' column.")
    data = df.dropna(subset=[TARGET]).reset_index(drop=True)
    model, metrics, importance = _train_core(data)
    metrics["rows_dropped"] = int(len(df) - len(data))
    save_active(model)
    return model, metrics, importance


def train_all_variants(df: pd.DataFrame):
    """Train ALL five models (combined + 4 processing variants).
    Returns dict: name -> {model, metrics, importance}.
    Skips a variant if its METHOD/SOIL columns are missing or too few rows."""
    if TARGET not in df.columns:
        raise ValueError(f"Training file must contain a '{TARGET}' column.")
    base = df.dropna(subset=[TARGET]).reset_index(drop=True)

    results = {}
    for name, method, soil in VARIANTS:
        sub = base
        if method is not None:
            if "METHOD" not in base.columns:
                continue
            sub = sub[sub["METHOD"] == method]
        if soil is not None:
            if "SOIL" not in base.columns:
                continue
            sub = sub[sub["SOIL"] == soil]
        sub = sub.reset_index(drop=True)
        if len(sub) < 20:           # not enough rows to train/test meaningfully
            continue
        model, metrics, importance = _train_core(sub)
        metrics["Variant"] = name
        results[name] = {"model": model, "metrics": metrics, "importance": importance}
    return results


def comparison_table(results: dict) -> pd.DataFrame:
    """Build a tidy comparison DataFrame from train_all_variants() output,
    sorted best-first by R2."""
    rows = [{"Variant": r["metrics"]["Variant"],
             "Rows": r["metrics"]["rows_used"],
             "R2": r["metrics"]["R2"],
             "RMSE": r["metrics"]["RMSE"],
             "MAE": r["metrics"]["MAE"]} for r in results.values()]
    return (pd.DataFrame(rows)
              .sort_values("R2", ascending=False)
              .reset_index(drop=True))


def save_active(model):
    """Save the chosen model to disk as the ACTIVE model used for prediction."""
    model.save_model(MODEL_PATH)


def predict(model, df: pd.DataFrame) -> pd.DataFrame:
    """Add PREDICTED_SEVERITY column to a copy of df (no negatives)."""
    out = df.copy()
    X = prepare_features(out)
    out["PREDICTED_SEVERITY"] = np.clip(model.predict(X), 0, None)
    return out


def load_saved_model():
    """Load the active model from disk, or None if none exists yet."""
    if not os.path.exists(MODEL_PATH):
        return None
    m = XGBRegressor()
    m.load_model(MODEL_PATH)
    return m
