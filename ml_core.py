"""
ml_core.py  — shared Machine-Learning engine for the dashboard.
Dataset-flexible: you choose the TARGET column and any columns to EXCLUDE
(e.g. leakage columns). Supports XGBoost, Random Forest, and a Linear Mixed Model.
"""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

MODEL_PATH = "active_model.joblib"     # active model BUNDLE used for prediction
DEFAULT_TARGET = "SEVERITY"

# ID-like columns that are never features (superset covering both datasets)
BASE_DROP = ["DATE", "DATE1", "Date", "POINT", "LATITUDE", "LONGITUDE", "EvalPoint"]

ALGORITHMS = ["XGBoost", "Random Forest"]

# Processing variants: (display name, METHOD filter, SOIL filter). None = no filter.
# Note: 'aoi' variants are intentionally excluded from the comparison.
VARIANTS = [
    ("Combined (all data)",        None,             None),
    ("whole · soil=NO",            "whole",          "NO"),
    ("whole · soil=YES",           "whole",          "YES"),
    ("orthorectified · soil=NO",   "orthorectified", "NO"),
    ("orthorectified · soil=YES",  "orthorectified", "YES"),
]

# tokens used to auto-suggest "other disease" leakage columns
_LEAK_TOKENS = ["SEV", "AP_MEAN", "SC_MEAN", "TARSPOT", "BIN"]


def numeric_columns(df):
    """Columns that are numeric or can be coerced to numeric — candidate targets."""
    out = []
    for c in df.columns:
        if pd.to_numeric(df[c], errors="coerce").notna().sum() > 0:
            out.append(c)
    return out


def suggest_leakage_columns(columns, target):
    """Suggest other disease-measurement columns to exclude (besides the target)."""
    return [c for c in columns
            if c != target and any(tok in c.upper() for tok in _LEAK_TOKENS)]


def make_model(algorithm: str):
    if algorithm == "XGBoost":
        return XGBRegressor(
            n_estimators=600, learning_rate=0.03, max_depth=5,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
            reg_lambda=1.0, random_state=42, n_jobs=-1)
    if algorithm == "Random Forest":
        return RandomForestRegressor(
            n_estimators=300, max_depth=None, min_samples_leaf=2,
            max_features="sqrt", random_state=42, n_jobs=-1)
    raise ValueError(f"Unknown algorithm: {algorithm}")


def prepare_features(df, target=DEFAULT_TARGET, extra_drop=()):
    """Drop ID columns, the target, and any excluded columns; encode text to numbers."""
    drop = set(BASE_DROP) | {target} | set(extra_drop)
    X = df.drop(columns=[c for c in drop if c in df.columns]).copy()
    for c in X.columns:
        if X[c].dtype == object or str(X[c].dtype) == "category":
            X[c] = X[c].astype("category").cat.codes
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)
    return X


def _train_core(data, algorithm, target, extra_drop, cv=False, n_splits=5):
    """Train one model. If cv=True, evaluate with K-fold grid cross-validation
    (reliable for small data) and fit the FINAL model on all rows."""
    from sklearn.model_selection import GroupKFold
    X = prepare_features(data, target, extra_drop)
    y = pd.to_numeric(data[target], errors="coerce")
    n_grids = data["POINT"].nunique() if "POINT" in data.columns else 0

    if cv and n_grids >= 3:
        # ---- cross-validation: average over K folds (honest on small data) ----
        k = min(n_splits, n_grids)
        gkf = GroupKFold(n_splits=k)
        r2s, rmses, maes = [], [], []
        for tr, te in gkf.split(X, y, data["POINT"]):
            m = make_model(algorithm)
            m.fit(X.iloc[tr], y.iloc[tr])
            p = m.predict(X.iloc[te])
            r2s.append(r2_score(y.iloc[te], p))
            rmses.append(np.sqrt(mean_squared_error(y.iloc[te], p)))
            maes.append(mean_absolute_error(y.iloc[te], p))
        model = make_model(algorithm).fit(X, y)      # final model on ALL data
        metrics = {
            "Algorithm": algorithm,
            "R2": round(float(np.mean(r2s)), 3),
            "RMSE": round(float(np.mean(rmses)), 3),
            "MAE": round(float(np.mean(maes)), 3),
            "rows_used": len(data),
            "split_kind": f"{k}-fold grid CV",
            "cv_folds": [round(float(v), 2) for v in r2s],
            "n_features": X.shape[1],
            "train_rows": len(X), "test_rows": len(X),
        }
    else:
        # ---- single honest split (fast; reliable when data is large) ----
        if n_grids >= 5:
            gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            tr, te = next(gss.split(X, y, data["POINT"]))
            split_kind = "grid-grouped (single split)"
        else:
            from sklearn.model_selection import train_test_split
            tr, te = train_test_split(np.arange(len(X)), test_size=0.2, random_state=42)
            split_kind = "random (single split)"
        model = make_model(algorithm)
        model.fit(X.iloc[tr], y.iloc[tr])
        pred = model.predict(X.iloc[te])
        metrics = {
            "Algorithm": algorithm,
            "R2": round(float(r2_score(y.iloc[te], pred)), 3),
            "RMSE": round(float(np.sqrt(mean_squared_error(y.iloc[te], pred))), 3),
            "MAE": round(float(mean_absolute_error(y.iloc[te], pred)), 3),
            "rows_used": len(data),
            "train_rows": len(tr), "test_rows": len(te),
            "split_kind": split_kind,
            "n_features": X.shape[1],
        }

    importance = (pd.Series(model.feature_importances_, index=X.columns)
                    .sort_values(ascending=False))
    return model, metrics, importance, list(X.columns)


def train_model(df, algorithm="XGBoost", target=DEFAULT_TARGET, extra_drop=()):
    """Train ONE combined model and save it as the active bundle."""
    if target not in df.columns:
        raise ValueError(f"Training file must contain the target '{target}'.")
    data = df[pd.to_numeric(df[target], errors="coerce").notna()].reset_index(drop=True)
    model, metrics, importance, feats = _train_core(data, algorithm, target, extra_drop)
    metrics["rows_dropped"] = int(len(df) - len(data))
    save_active({"model": model, "features": feats, "target": target})
    return model, metrics, importance


def train_all_variants(df, algorithms=("XGBoost",), target=DEFAULT_TARGET, extra_drop=(),
                       cv=False):
    """Train chosen algorithm(s) across all variants. Returns dict keyed
    'Algorithm · Variant' -> {model, metrics, importance, features, target}.
    cv=True uses 5-fold grid cross-validation (reliable scores for small data)."""
    if target not in df.columns:
        raise ValueError(f"Training file must contain the target '{target}'.")
    base = df[pd.to_numeric(df[target], errors="coerce").notna()].reset_index(drop=True)

    results = {}
    for algo in algorithms:
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
            if len(sub) < 20:
                continue
            model, metrics, importance, feats = _train_core(sub, algo, target, extra_drop, cv=cv)
            metrics["Variant"] = name
            results[f"{algo} · {name}"] = {
                "model": model, "metrics": metrics, "importance": importance,
                "features": feats, "target": target}
    return results


def comparison_table(results: dict) -> pd.DataFrame:
    rows = [{"Algorithm": r["metrics"]["Algorithm"],
             "Variant": r["metrics"]["Variant"],
             "Rows": r["metrics"]["rows_used"],
             "R2": r["metrics"]["R2"],
             "RMSE": r["metrics"]["RMSE"],
             "MAE": r["metrics"]["MAE"]} for r in results.values()]
    return (pd.DataFrame(rows).sort_values("R2", ascending=False).reset_index(drop=True))


def save_active(bundle):
    """Save the chosen model bundle {model, features, target} to disk."""
    joblib.dump(bundle, MODEL_PATH)


def predict(bundle, df: pd.DataFrame) -> pd.DataFrame:
    """Predict using a saved bundle. Aligns new data to the training features."""
    model = bundle["model"] if isinstance(bundle, dict) else bundle
    target = bundle.get("target", DEFAULT_TARGET) if isinstance(bundle, dict) else DEFAULT_TARGET
    feats = bundle.get("features") if isinstance(bundle, dict) else None
    out = df.copy()
    X = prepare_features(out, target)
    if feats is not None:
        X = X.reindex(columns=feats, fill_value=0)   # exact same columns as training
    out["PREDICTED_SEVERITY"] = np.clip(model.predict(X), 0, None)
    return out


def load_saved_model():
    """Load the active bundle from disk, or None if none exists yet."""
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


# ======================================================================
#  LINEAR MIXED MODEL (statistical explanation)
# ======================================================================
LMM_FIXED = ["NDVI_MEAN", "NDRE_MEAN", "OSAVI_MEAN", "PSRI_MEAN",
             "RDVI_MEAN", "MCARI2_MEAN", "EXG_MEAN", "CANOPY_COVER"]
LMM_GROUP = "POINT"


def _sig_label(p):
    if p < 0.001:
        return "*** (p<0.001)"
    if p < 0.01:
        return "** (p<0.01)"
    if p < 0.05:
        return "* (p<0.05)"
    return "not significant"


def fit_lmm(df, fixed=None, group=LMM_GROUP, target=DEFAULT_TARGET):
    """Fit a Linear Mixed Model: target ~ fixed effects, grouped by POINT."""
    import statsmodels.formula.api as smf

    fixed = list(fixed) if fixed else LMM_FIXED
    if target not in df.columns:
        raise ValueError(f"Data must contain target '{target}'.")
    if group not in df.columns:
        raise ValueError(f"Data must contain grouping column '{group}'.")
    fixed = [c for c in fixed if c in df.columns]
    if not fixed:
        raise ValueError("None of the selected predictors exist in this file.")

    data = df.copy()
    data[target] = pd.to_numeric(data[target], errors="coerce")
    for c in fixed:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data[group] = data[group].astype(str)
    data = data.dropna(subset=[target, group] + fixed).reset_index(drop=True)

    formula = f"{target} ~ " + " + ".join(fixed)
    result = smf.mixedlm(formula, data=data, groups=data[group]).fit()

    coef, pval = result.params, result.pvalues
    tbl = pd.DataFrame({"Feature": coef.index, "Coefficient": coef.values,
                        "p_value": pval.values})
    tbl = tbl[~tbl["Feature"].isin(["Intercept", "Group Var"])].copy()
    tbl["Significant"] = tbl["p_value"].apply(_sig_label)
    tbl = tbl.sort_values("p_value").reset_index(drop=True)

    info = {"rows": len(data), "groups": int(data[group].nunique()),
            "formula": formula, "n_fixed": len(fixed)}
    return tbl, result.summary().as_text(), info
