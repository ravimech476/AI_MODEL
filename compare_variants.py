"""
Experiment: which drone-processing variant predicts disease best?
Train a SEPARATE XGBoost for each combination of:
   METHOD = whole / orthorectified
   SOIL   = YES / NO
...plus the COMBINED model (all data together).
Each uses an honest grid-grouped split. Compare R2 / RMSE / MAE.
"""
import numpy as np, pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor

df = pd.read_excel(r"C:\Users\USER\Downloads\combined_vi_stats_with_disease_PPAC-B3.xlsx")
df = df.dropna(subset=["SEVERITY"]).reset_index(drop=True)
DROP = ["SEVERITY", "DATE", "POINT", "LATITUDE", "LONGITUDE", "METHOD", "SOIL"]

def run(data, name):
    X = data.drop(columns=[c for c in DROP if c in data.columns]).copy()
    y = data["SEVERITY"]
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y, data["POINT"]))
    m = XGBRegressor(n_estimators=600, learning_rate=0.03, max_depth=5,
                     subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
                     random_state=42, n_jobs=-1).fit(X.iloc[tr], y.iloc[tr])
    p = m.predict(X.iloc[te])
    return {"Variant": name, "Rows": len(data),
            "R2": round(r2_score(y.iloc[te], p), 3),
            "RMSE": round(np.sqrt(mean_squared_error(y.iloc[te], p)), 3),
            "MAE": round(mean_absolute_error(y.iloc[te], p), 3)}

results = []
for method in ["whole", "orthorectified"]:
    for soil in ["NO", "YES"]:
        sub = df[(df.METHOD == method) & (df.SOIL == soil)]
        results.append(run(sub, f"{method} | soil={soil}"))
results.append(run(df, "COMBINED (all 4 variants)"))

out = pd.DataFrame(results)
print(out.to_string(index=False))
print("\nBest by R2:", out.loc[out.R2.idxmax(), "Variant"], "->", out.R2.max())
