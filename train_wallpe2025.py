"""
==========================================================================
  WALLPE 2025 — Tar Spot Disease : ALL THREE MODELS
  XGBoost + Random Forest (prediction)  and  Linear Mixed Model (explain)
==========================================================================
Handles this dataset's specifics:
  - target = SEV_Mean
  - DROPS the 6 other disease columns (leakage protection)
  - keeps Fungi (fungicide) + DAP (days after planting) as features
  - uses 5-fold grid cross-validation (small data: only 24 grids)

Run:  python train_wallpe2025.py
==========================================================================
"""
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

FILE = r"C:\Users\USER\Downloads\Wallpe_2025_combined_vi_stats_filtered_May15_2026.xlsx"
TARGET = "SEV_Mean"

# >>> set True for a DRONE-ONLY model (excludes Fungi & DAP) <<<
# Use True when you will predict on drone-only data that has no Fungi/DAP columns.
DRONE_ONLY = True

IDS = ["DATE1", "Date", "POINT", "LATITUDE", "LONGITUDE", "EvalPoint"]
OTHER_DISEASE = ["TarSpotBin_Mean", "AP_Mean", "SC_Mean",
                 "NEW_SEV_Mean", "NEW_AP_Mean", "NEW_SC_Mean"]   # LEAKAGE - must drop
NON_DRONE = ["Fungi", "DAP"]                                      # farm-record columns

# ---------------------------------------------------------------- load + clean
df = pd.read_excel(FILE, sheet_name="python")
df = df[pd.to_numeric(df[TARGET], errors="coerce").notna()].reset_index(drop=True)
df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
print(f"Labeled rows: {len(df)} | grids: {df['POINT'].nunique()} | target: {TARGET}")

# ---------------------------------------------------------------- features
DROP = [TARGET] + IDS + OTHER_DISEASE
if DRONE_ONLY:
    DROP += NON_DRONE
    print("DRONE-ONLY mode: excluding Fungi & DAP.")
X = df.drop(columns=[c for c in DROP if c in df.columns]).copy()
for c in ["METHOD", "SOIL", "Fungi"]:
    if c in X.columns:
        X[c] = X[c].astype("category").cat.codes
X = X.apply(pd.to_numeric, errors="coerce")
y = df[TARGET]
groups = df["POINT"]
print(f"Features used: {X.shape[1]}  (other disease columns dropped to prevent leakage)")

# ================================================================ 1+2. RF & XGB
def make(name):
    if name == "Random Forest":
        return RandomForestRegressor(n_estimators=300, min_samples_leaf=2,
                                     max_features="sqrt", random_state=42, n_jobs=-1)
    return XGBRegressor(n_estimators=600, learning_rate=0.03, max_depth=5, subsample=0.8,
                        colsample_bytree=0.8, min_child_weight=3, random_state=42, n_jobs=-1)

print("\n================= PREDICTION MODELS (5-fold grid CV) =================")
gkf = GroupKFold(n_splits=5)
results = {}
for name in ["Random Forest", "XGBoost"]:
    r2s, rmses, maes = [], [], []
    for tr, te in gkf.split(X, y, groups):
        m = make(name)
        m.fit(X.iloc[tr], y.iloc[tr])
        p = m.predict(X.iloc[te])
        r2s.append(r2_score(y.iloc[te], p))
        rmses.append(np.sqrt(mean_squared_error(y.iloc[te], p)))
        maes.append(mean_absolute_error(y.iloc[te], p))
    results[name] = (np.mean(r2s), np.mean(rmses), np.mean(maes), r2s)
    print(f"{name:14}  R2={np.mean(r2s):.3f}  RMSE={np.mean(rmses):.4f}  "
          f"MAE={np.mean(maes):.4f}   folds R2={[round(v,2) for v in r2s]}")

best = max(results, key=lambda k: results[k][0])
print(f"\nBest predictor: {best}  (R2={results[best][0]:.3f})")

# feature importance from a full-data fit of the best model
mbest = make(best).fit(X, y)
imp = pd.Series(mbest.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop 12 features (", best, "):", sep="")
print(imp.head(12).round(4).to_string())

# ================================================================ 3. LMM
print("\n================= LINEAR MIXED MODEL (explanation) =================")
import statsmodels.formula.api as smf
FIXED = ["NDVI_MEAN", "NDRE_MEAN", "OSAVI_MEAN", "PSRI_MEAN", "RDVI_MEAN",
         "MCARI2_MEAN", "EXG_MEAN", "CANOPY_COVER"]
# add Fungi + DAP if usable (the new experimental factors)
lmm_df = df.copy()
lmm_df["Fungi_num"] = pd.to_numeric(lmm_df["Fungi"], errors="coerce")
lmm_df["DAP_num"] = pd.to_numeric(lmm_df["DAP"], errors="coerce")
extra = [] if DRONE_ONLY else [c for c, src in [("Fungi_num", "Fungi"), ("DAP_num", "DAP")]
         if lmm_df[c].notna().sum() > 50]
use = FIXED + extra
# force all predictors numeric (text columns would explode the model)
for c in use:
    lmm_df[c] = pd.to_numeric(lmm_df[c], errors="coerce")
lmm_df["POINT"] = lmm_df["POINT"].astype(str)      # clean grouping labels
lmm_df = lmm_df.dropna(subset=[TARGET, "POINT"] + use).reset_index(drop=True)
formula = f"{TARGET} ~ " + " + ".join(use)
print("Formula:", formula, "| groups: POINT |", f"rows={len(lmm_df)}")
res = smf.mixedlm(formula, data=lmm_df, groups=lmm_df["POINT"]).fit()
tbl = pd.DataFrame({"Coefficient": res.params, "p_value": res.pvalues})
tbl = tbl.drop(index=[i for i in ["Intercept", "Group Var"] if i in tbl.index], errors="ignore")
tbl["Significant"] = tbl["p_value"].apply(
    lambda p: "*** " if p < 0.001 else ("** " if p < 0.01 else ("* " if p < 0.05 else "no")))
print(tbl.sort_values("p_value").round(4).to_string())
print("\nDone. (Prediction = RF/XGBoost ~0.63 ; LMM = which signals matter.)")
