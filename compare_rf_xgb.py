"""
Head-to-head: Random Forest (baseline) vs XGBoost (primary).
Same data, same honest grid-grouped split, same metrics.
"""
import time
import numpy as np, pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

df = pd.read_excel(r"C:\Users\USER\Downloads\combined_vi_stats_with_disease_PPAC-B3.xlsx")
df = df.dropna(subset=["SEVERITY"]).reset_index(drop=True)
DROP = ["SEVERITY", "DATE", "POINT", "LATITUDE", "LONGITUDE"]

X = df.drop(columns=[c for c in DROP if c in df.columns]).copy()
for c in ["METHOD", "SOIL"]:
    X[c] = X[c].astype("category").cat.codes
y = df["SEVERITY"]

# identical honest split for both models
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr, te = next(gss.split(X, y, df["POINT"]))
Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]

models = {
    "Random Forest (baseline)": RandomForestRegressor(
        n_estimators=300, max_depth=None, min_samples_leaf=2,
        max_features="sqrt", random_state=42, n_jobs=-1),
    "XGBoost (primary)": XGBRegressor(
        n_estimators=600, learning_rate=0.03, max_depth=5, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=3, random_state=42, n_jobs=-1),
}

rows = []
for name, m in models.items():
    t0 = time.time()
    m.fit(Xtr, ytr)
    train_s = time.time() - t0
    p = m.predict(Xte)
    rows.append({
        "Model": name,
        "R2": round(r2_score(yte, p), 4),
        "RMSE": round(np.sqrt(mean_squared_error(yte, p)), 4),
        "MAE": round(mean_absolute_error(yte, p), 4),
        "Train time (s)": round(train_s, 2),
    })

out = pd.DataFrame(rows)
print(out.to_string(index=False))
best = out.loc[out.R2.idxmax(), "Model"]
print(f"\nHighest R2: {best}")
print(f"Train rows: {len(tr)} | Test rows: {len(te)} | Features: {X.shape[1]}")
