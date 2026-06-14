"""
UAV Disease Severity Prediction — XGBoost Regressor
Dataset: combined_vi_stats_with_disease_PPAC-B3.xlsx
Target : SEVERITY (continuous 0..6) -> regression

Run:  python train_xgboost.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor

# ----------------------------------------------------------------------
# 1. LOAD
# ----------------------------------------------------------------------
FILE = r"C:\Users\USER\Downloads\combined_vi_stats_with_disease_PPAC-B3.xlsx"
df = pd.read_excel(FILE)
print(f"Loaded: {df.shape[0]} rows, {df.shape[1]} columns")

# ----------------------------------------------------------------------
# 2. CLEAN  — we can only train on rows that HAVE a severity value
# ----------------------------------------------------------------------
df = df.dropna(subset=["SEVERITY"]).reset_index(drop=True)
print(f"After dropping rows with no SEVERITY: {df.shape[0]} rows")

# ----------------------------------------------------------------------
# 3. SELECT FEATURES
#    Drop pure identifiers (they cause location memorization / leakage).
#    Encode the two text columns (METHOD, SOIL) into numbers.
# ----------------------------------------------------------------------
DROP_COLS = ["SEVERITY", "DATE", "POINT", "LATITUDE", "LONGITUDE"]

X = df.drop(columns=DROP_COLS)
y = df["SEVERITY"]

# Encode categorical text columns
for col in ["METHOD", "SOIL"]:
    if col in X.columns:
        X[col] = X[col].astype("category").cat.codes   # whole/orthorectified, NO/YES -> 0/1

print(f"Using {X.shape[1]} features")

# ----------------------------------------------------------------------
# 4. TRAIN / TEST SPLIT  -- BY GRID (POINT)
#    Each grid (12 m, 6 corn plants) is stored 4x (whole/ortho x soil yes/no)
#    and across 8 dates. We must keep ALL rows of a grid on the SAME side,
#    otherwise the model sees the test plants during training (data leakage).
# ----------------------------------------------------------------------
groups = df["POINT"]                       # the grid id = the unit to keep together
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups))
X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
print(f"Train grids: {groups.iloc[train_idx].nunique()} | "
      f"Test grids: {groups.iloc[test_idx].nunique()} (never seen in training)")

# ----------------------------------------------------------------------
# 5. TRAIN XGBOOST REGRESSOR
# ----------------------------------------------------------------------
model = XGBRegressor(
    n_estimators=600,
    learning_rate=0.03,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train, y_train)

# ----------------------------------------------------------------------
# 6. EVALUATE
# ----------------------------------------------------------------------
pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, pred))
mae  = mean_absolute_error(y_test, pred)
r2   = r2_score(y_test, pred)

print("\n================ RESULTS ================")
print(f"RMSE : {rmse:.4f}   (avg error, same units as SEVERITY)")
print(f"MAE  : {mae:.4f}")
print(f"R^2  : {r2:.4f}   (1.0 = perfect, 0 = no better than the mean)")
print("=========================================")

# ----------------------------------------------------------------------
# 7. FEATURE IMPORTANCE  -> which indices drive disease severity
# ----------------------------------------------------------------------
imp = (pd.Series(model.feature_importances_, index=X.columns)
         .sort_values(ascending=False))
print("\nTop 15 most important features:")
print(imp.head(15).to_string())

imp.head(20).iloc[::-1].plot(kind="barh", figsize=(8, 7))
plt.title("XGBoost Feature Importance — Disease Severity")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=120)
print("\nSaved chart -> feature_importance.png")

# ----------------------------------------------------------------------
# 8. SAVE MODEL for reuse / dashboard
# ----------------------------------------------------------------------
model.save_model("xgb_severity_model.json")
print("Saved model -> xgb_severity_model.json")
