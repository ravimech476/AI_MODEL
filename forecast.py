"""
==========================================================================
  HYBRID FORECAST — Growth Model + Markov Chain  (2025 Wallpe Tar Spot)
==========================================================================
Forecasts FUTURE disease from the severity time series per grid.

Pipeline:
   severity per grid per flight (DAP)  ->  reshape to time series
        ->  GROWTH MODEL  (forecasts the future NUMBER)
        ->  MARKOV CHAIN  (forecasts the future ODDS / state)

Time axis = DAP (Days After Planting): 86, 102, 121, 128.

Run:  python forecast.py
==========================================================================
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

FILE = r"C:\Users\USER\Downloads\2025_Wallpe_New_model_FINAL_MERGED_TARSPOT_UAV.xlsx"
SEV = "NEW_SEV_Mean"          # severity (% leaf area) — best for growth curves
TIME = "DAP"                  # days after planting (the time axis)


# ----------------------------------------------------------------------
# 1. LOAD + reshape into one time series per grid
# ----------------------------------------------------------------------
df = pd.read_excel(FILE)
df[SEV] = pd.to_numeric(df[SEV], errors="coerce")
df[TIME] = pd.to_numeric(df[TIME], errors="coerce")
df = df.dropna(subset=[SEV, TIME, "POINT"])

# severity is identical across method/soil variants -> keep one row per grid+DAP
ts = (df.drop_duplicates(["POINT", TIME])
        .sort_values(["POINT", TIME])[["POINT", TIME, SEV]]
        .reset_index(drop=True))
print(f"Grids: {ts['POINT'].nunique()} | time points (DAP): {sorted(ts[TIME].unique())}")


# ======================================================================
# 2. GROWTH MODEL  — fit an exponential curve per grid, forecast forward
# ======================================================================
def exp_growth(t, y0, r):
    return y0 * np.exp(r * t)        # y0 = level, r = growth rate per day

def fit_growth(days, sev):
    """Fit exponential growth; return (y0, r) or None if it fails."""
    days = np.asarray(days, float)
    sev = np.clip(np.asarray(sev, float), 1e-6, None)   # avoid log(0)
    t0 = days.min()
    try:
        p, _ = curve_fit(exp_growth, days - t0, sev,
                         p0=[sev[0], 0.1], maxfev=5000)
        return p[0], p[1], t0
    except Exception:
        return None

print("\n===== GROWTH MODEL (exponential) =====")
rates = []
for g, sub in ts.groupby("POINT"):
    fit = fit_growth(sub[TIME].values, sub[SEV].values)
    if fit is None:
        continue
    y0, r, t0 = fit
    rates.append(r)
    last_day = sub[TIME].max()
    f1 = exp_growth(last_day + 7 - t0, y0, r)     # forecast +7 days
    f2 = exp_growth(last_day + 14 - t0, y0, r)    # forecast +14 days
    if g in list(ts["POINT"].unique())[:3]:       # show first 3 grids
        cur = sub[SEV].iloc[-1]
        print(f"Grid {g}: now={cur:.3f}  rate r={r:.3f}/day  ->  +7d≈{f1:.3f}  +14d≈{f2:.3f}")
print(f"\nAverage growth rate r = {np.mean(rates):.3f}/day  "
      f"(paper reported ~0.20/day for tar spot)")

# ---- VALIDATE: fit on first 3 flights, predict the 4th ----
print("\n----- Growth-model validation (fit first 3, predict 4th) -----")
errs, n = [], 0
for g, sub in ts.groupby("POINT"):
    sub = sub.sort_values(TIME)
    if len(sub) < 4:
        continue
    train, test = sub.iloc[:3], sub.iloc[3]
    fit = fit_growth(train[TIME].values, train[SEV].values)
    if fit is None:
        continue
    y0, r, t0 = fit
    pred = exp_growth(test[TIME] - t0, y0, r)
    errs.append(abs(pred - test[SEV])); n += 1
print(f"Validated on {n} grids | mean abs error on the 4th flight = {np.mean(errs):.3f}")


# ======================================================================
# 3. MARKOV CHAIN  — states + transition probabilities, forecast the odds
# ======================================================================
def to_state(s):
    if s < 0.01:  return 0     # Healthy
    if s < 0.05:  return 1     # Low
    if s < 0.15:  return 2     # Moderate
    return 3                   # Severe
STATE_NAMES = ["Healthy", "Low", "Moderate", "Severe"]

print("\n\n===== MARKOV CHAIN =====")
# build a 4x4 count matrix of transitions (state at t -> state at t+1)
counts = np.zeros((4, 4))
for g, sub in ts.groupby("POINT"):
    seq = [to_state(s) for s in sub.sort_values(TIME)[SEV]]
    for a, b in zip(seq[:-1], seq[1:]):
        counts[a][b] += 1

# normalize each row to probabilities
P = np.divide(counts, counts.sum(axis=1, keepdims=True),
              out=np.zeros_like(counts), where=counts.sum(axis=1, keepdims=True) > 0)

print("Transition matrix  (rows = now, columns = next flight):")
header = "from->to".rjust(10)
print(header + " " + " ".join(f"{n:>9}" for n in STATE_NAMES))
for i, name in enumerate(STATE_NAMES):
    print(f"{name:>10} " + " ".join(f"{P[i][j]:>9.2f}" for j in range(4)))

print("\nReading example: from 'Low' the next-flight probabilities are:")
for j in range(4):
    if P[1][j] > 0:
        print(f"   -> {STATE_NAMES[j]}: {P[1][j]*100:.0f}%")

# ---- forecast 2 flights ahead from each current state ----
print("\n----- 2-flight-ahead state probabilities (chain forward) -----")
P2 = P @ P                                  # two-step transition matrix
for i, name in enumerate(STATE_NAMES):
    if counts[i].sum() == 0:
        continue
    probs = ", ".join(f"{STATE_NAMES[j]} {P2[i][j]*100:.0f}%" for j in range(4) if P2[i][j] > 0.05)
    print(f"If '{name}' now -> in 2 flights: {probs}")

print("\nDone.  Growth model = future NUMBER ; Markov chain = future ODDS.")
