"""
USE the trained model — predict disease severity for NEW drone data.
You do NOT train again. You just load the saved model and feed it new grids.

Run:  python predict.py
Output: a new Excel file with a PREDICTED_SEVERITY column added.
"""

import pandas as pd
from xgboost import XGBRegressor

# ----------------------------------------------------------------------
# 1. LOAD THE TRAINED MODEL  (the "brain" we saved during training)
# ----------------------------------------------------------------------
model = XGBRegressor()
model.load_model("xgb_severity_model.json")
print("Model loaded.")

# ----------------------------------------------------------------------
# 2. LOAD NEW DATA
#    This must have the SAME feature columns the model was trained on.
#    (a new drone flight, same vegetation-index/band columns)
#    Here we reuse the original file as an example.
# ----------------------------------------------------------------------
NEW_FILE = r"C:\Users\USER\Downloads\combined_vi_stats_with_disease_PPAC-B3.xlsx"
new = pd.read_excel(NEW_FILE)
print(f"New data: {new.shape[0]} grids to predict")

# ----------------------------------------------------------------------
# 3. PREPARE FEATURES  -- EXACTLY the same steps as training
#    Drop the same ID columns, encode the same text columns.
# ----------------------------------------------------------------------
DROP = ["SEVERITY", "DATE", "POINT", "LATITUDE", "LONGITUDE"]
X = new.drop(columns=[c for c in DROP if c in new.columns]).copy()
for col in ["METHOD", "SOIL"]:
    if col in X.columns:
        X[col] = X[col].astype("category").cat.codes

# ----------------------------------------------------------------------
# 4. PREDICT  -- this is the actual "use the model" line
# ----------------------------------------------------------------------
new["PREDICTED_SEVERITY"] = model.predict(X)

# Optional: turn the number into an easy label
def label(v):
    if v < 0.5:  return "Healthy"
    if v < 2.0:  return "Moderate"
    return "Severe"
new["HEALTH_STATUS"] = new["PREDICTED_SEVERITY"].apply(label)

# ----------------------------------------------------------------------
# 5. SAVE RESULTS
# ----------------------------------------------------------------------
OUT = r"C:\Users\USER\Downloads\predictions_output.xlsx"
cols = ["POINT", "DATE", "PREDICTED_SEVERITY", "HEALTH_STATUS"]
new[cols + [c for c in new.columns if c not in cols]].to_excel(OUT, index=False)
print(f"Saved predictions -> {OUT}")

print("\nSample predictions:")
print(new[["POINT", "DATE", "PREDICTED_SEVERITY", "HEALTH_STATUS"]].head(10).to_string(index=False))
print("\nHealth status counts:")
print(new["HEALTH_STATUS"].value_counts())
