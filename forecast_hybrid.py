"""
==========================================================================
  FULL HYBRID FORECAST  (2025 Wallpe Tar Spot)
==========================================================================
The COMPLETE pipeline:
   1. Drone-ML (XGBoost OR Random Forest) -> PREDICTS severity per grid/flight
   2. Those predictions form each grid's time series
   3. Growth model  -> future NUMBER
      Markov chain  -> future ODDS
   4. Combined      -> RISK level per grid

>>> CHOOSE the drone model here:  "XGBoost"  or  "Random Forest"  <<<
ALGORITHM = "Random Forest"

Run:  python forecast_hybrid.py
Output: forecast_hybrid.xlsx
==========================================================================
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import ml_core as ml

FILE = r"C:\Users\USER\Downloads\2025_Wallpe_New_model_FINAL_MERGED_TARSPOT_UAV.xlsx"
SEV = "NEW_SEV_Mean"            # the severity we model
TIME = "DAP"
HORIZONS = [7, 14, 21]         # <-- forecast these many days ahead (change freely)
RISK_HORIZON = 14              # which horizon the RISK flag is based on
ALGORITHM = "Random Forest"    # <-- choose "XGBoost" or "Random Forest"

# ----------------------------------------------------------------------
# STEP 1 — Drone-ML: train, then PREDICT severity from drone data
# ----------------------------------------------------------------------
df = pd.read_excel(FILE)
leak = ml.suggest_leakage_columns(df.columns, SEV)        # other disease cols
extra_drop = leak + ["DAP"]                               # drone-focused (drop DAP)

res = ml.train_all_variants(df, algorithms=[ALGORITHM], target=SEV,
                            extra_drop=extra_drop, cv=False)
ch = res[f"{ALGORITHM} · Combined (all data)"]
bundle = {"model": ch["model"], "features": ch["features"], "target": SEV}
print(f"Drone-ML = {ALGORITHM}  (predicts severity from drone indices)")

# predict severity for every row, then keep one value per grid+DAP
pred_df = ml.predict(bundle, df)
pred_df[TIME] = pd.to_numeric(pred_df[TIME], errors="coerce")
pred_df = pred_df.dropna(subset=[TIME, "POINT"])
ts = (pred_df.drop_duplicates(["POINT", TIME]).sort_values(["POINT", TIME])
        [["POINT", TIME, "PREDICTED_SEVERITY"]].reset_index(drop=True))
SEVCOL = "PREDICTED_SEVERITY"        # <-- now using the DRONE-ML prediction!
print(f"Built predicted-severity time series for {ts['POINT'].nunique()} grids.\n")


# ----------------------------------------------------------------------
# STEP 2 — Growth model (logistic + exponential)
# ----------------------------------------------------------------------
def exp_growth(t, y0, r):  return y0 * np.exp(r * t)
def logistic(t, K, r, m):  return K / (1 + np.exp(-r * (t - m)))

def forecast_grid(days, sev, horizons):
    """Fit a curve once, forecast at EACH horizon. Returns (dict_of_forecasts, rate, curve)."""
    days = np.asarray(days, float); sev = np.clip(np.asarray(sev, float), 1e-6, None)
    t0 = days.min(); x = days - t0; last = days.max()
    def at(fn, p):
        return {h: min(float(fn(last + h - t0, *p)), 1.0) for h in horizons}
    try:
        p, _ = curve_fit(logistic, x, sev, p0=[max(sev.max()*1.5, .3), .2, x.mean()],
                         maxfev=8000, bounds=([sev.max(), 0, -50], [1.0, 2, 200]))
        return at(logistic, p), float(p[1]), "logistic"
    except Exception:
        try:
            p, _ = curve_fit(exp_growth, x, sev, p0=[sev[0], .1], maxfev=5000)
            return at(exp_growth, p), float(p[1]), "exponential"
        except Exception:
            return {h: float(sev[-1]) for h in horizons}, 0.0, "flat"


# ----------------------------------------------------------------------
# STEP 3 — Markov chain
# ----------------------------------------------------------------------
def to_state(s):
    if s < 0.01: return 0
    if s < 0.05: return 1
    if s < 0.15: return 2
    return 3
STATE_NAMES = ["Healthy", "Low", "Moderate", "Severe"]

counts = np.zeros((4, 4))
for g, sub in ts.groupby("POINT"):
    seq = [to_state(s) for s in sub.sort_values(TIME)[SEVCOL]]
    for a, b in zip(seq[:-1], seq[1:]):
        counts[a][b] += 1
P = np.divide(counts, counts.sum(axis=1, keepdims=True),
              out=np.zeros_like(counts), where=counts.sum(axis=1, keepdims=True) > 0)


# ----------------------------------------------------------------------
# STEP 4 — per-grid forecast + risk
# ----------------------------------------------------------------------
def risk_level(cs, fval, rate):
    if cs >= 3 or fval >= 0.15:               return "RED — severe / heading severe"
    if cs == 2 or fval >= 0.05 or rate > 0.15: return "ORANGE — rising"
    if rate > 0.05:                            return "YELLOW — watch"
    return "GREEN — stable"

rows = []
for g, sub in ts.groupby("POINT"):
    sub = sub.sort_values(TIME)
    cur = float(sub[SEVCOL].iloc[-1]); cs = to_state(cur)
    fdict, rate, model = forecast_grid(sub[TIME].values, sub[SEVCOL].values, HORIZONS)
    p_worse = float(P[cs][cs+1:].sum()) if cs < 3 else 0.0
    row = {
        "POINT": g,
        "predicted_severity_now": round(cur, 3),     # from the DRONE-ML
        "current_state": STATE_NAMES[cs],
        "growth_rate_per_day": round(rate, 3),
    }
    for h in HORIZONS:                               # one column per horizon
        row[f"forecast_+{h}d"] = round(fdict[h], 3)
    row["prob_worse_next_flight"] = f"{p_worse*100:.0f}%"
    row["RISK"] = risk_level(cs, fdict[RISK_HORIZON], rate)
    rows.append(row)

out = pd.DataFrame(rows).sort_values(f"forecast_+{RISK_HORIZON}d", ascending=False).reset_index(drop=True)
out.to_excel("forecast_hybrid.xlsx", index=False)

print(f"FULL HYBRID forecast ({ALGORITHM} drone-ML + growth + Markov):\n")
print(out.to_string(index=False))
print("\nRisk summary:")
print(out["RISK"].value_counts().to_string())
print("\nSaved -> forecast_hybrid.xlsx")
