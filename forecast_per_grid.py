"""
==========================================================================
  HYBRID FORECAST — PER GRID  (2025 Wallpe Tar Spot)
==========================================================================
Each grid (POINT) is forecast SEPARATELY:
   - Growth model (logistic + exponential) -> future severity NUMBER
   - Markov chain                          -> future state ODDS
   - Combined                              -> a RISK LEVEL per grid

Time axis = DAP (Days After Planting): 86, 102, 121, 128.
Output: a per-grid forecast table -> forecast_per_grid.xlsx

Run:  python forecast_per_grid.py
==========================================================================
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

FILE = r"C:\Users\USER\Downloads\2025_Wallpe_New_model_FINAL_MERGED_TARSPOT_UAV.xlsx"
SEV = "NEW_SEV_Mean"
TIME = "DAP"
HORIZON = 14          # forecast this many days ahead

# ---------- load + one time series per grid ----------
df = pd.read_excel(FILE)
df[SEV] = pd.to_numeric(df[SEV], errors="coerce")
df[TIME] = pd.to_numeric(df[TIME], errors="coerce")
df = df.dropna(subset=[SEV, TIME, "POINT"])
ts = (df.drop_duplicates(["POINT", TIME]).sort_values(["POINT", TIME])
        [["POINT", TIME, SEV]].reset_index(drop=True))


# ---------- growth curves ----------
def exp_growth(t, y0, r):
    return y0 * np.exp(r * t)

def logistic(t, K, r, t_mid):
    return K / (1 + np.exp(-r * (t - t_mid)))

def forecast_grid(days, sev, horizon):
    """Return (forecast_value, growth_rate, model_used)."""
    days = np.asarray(days, float)
    sev = np.clip(np.asarray(sev, float), 1e-6, None)
    t0 = days.min()
    x = days - t0
    future = days.max() + horizon - t0
    # try logistic first (levels off -> realistic); fall back to exponential
    try:
        K0 = max(sev.max() * 1.5, 0.3)
        p, _ = curve_fit(logistic, x, sev, p0=[K0, 0.2, x.mean()],
                         maxfev=8000, bounds=([sev.max(), 0, -50], [1.0, 2, 200]))
        val = float(logistic(future, *p))
        return min(val, 1.0), float(p[1]), "logistic"
    except Exception:
        try:
            p, _ = curve_fit(exp_growth, x, sev, p0=[sev[0], 0.1], maxfev=5000)
            val = float(exp_growth(future, *p))
            return min(val, 1.0), float(p[1]), "exponential"
        except Exception:
            return float(sev[-1]), 0.0, "flat"


# ---------- Markov states ----------
def to_state(s):
    if s < 0.01:  return 0
    if s < 0.05:  return 1
    if s < 0.15:  return 2
    return 3
STATE_NAMES = ["Healthy", "Low", "Moderate", "Severe"]

# build transition matrix from all grids
counts = np.zeros((4, 4))
for g, sub in ts.groupby("POINT"):
    seq = [to_state(s) for s in sub.sort_values(TIME)[SEV]]
    for a, b in zip(seq[:-1], seq[1:]):
        counts[a][b] += 1
P = np.divide(counts, counts.sum(axis=1, keepdims=True),
              out=np.zeros_like(counts), where=counts.sum(axis=1, keepdims=True) > 0)


# ---------- per-grid forecast table ----------
def risk_level(cur_state, forecast_val, growth_rate):
    """Combine current state + forecast into a simple risk flag."""
    if cur_state >= 3 or forecast_val >= 0.15:
        return "RED — severe / heading severe"
    if cur_state == 2 or forecast_val >= 0.05 or growth_rate > 0.15:
        return "ORANGE — rising"
    if growth_rate > 0.05:
        return "YELLOW — watch"
    return "GREEN — stable"

rows = []
for g, sub in ts.groupby("POINT"):
    sub = sub.sort_values(TIME)
    cur = float(sub[SEV].iloc[-1])
    cur_state = to_state(cur)
    fval, rate, model = forecast_grid(sub[TIME].values, sub[SEV].values, HORIZON)
    # Markov: probability the grid worsens next flight
    nxt = P[cur_state]
    p_worse = float(nxt[cur_state + 1:].sum()) if cur_state < 3 else 0.0
    rows.append({
        "POINT": g,
        "current_severity": round(cur, 3),
        "current_state": STATE_NAMES[cur_state],
        "growth_rate_per_day": round(rate, 3),
        f"forecast_+{HORIZON}d": round(fval, 3),
        "curve": model,
        "prob_worse_next_flight": f"{p_worse*100:.0f}%",
        "RISK": risk_level(cur_state, fval, rate),
    })

out = pd.DataFrame(rows).sort_values(f"forecast_+{HORIZON}d", ascending=False).reset_index(drop=True)
out.to_excel("forecast_per_grid.xlsx", index=False)

print(f"Per-grid forecast for {len(out)} grids (sorted by forecast severity):\n")
print(out.to_string(index=False))
print("\nRisk summary:")
print(out["RISK"].value_counts().to_string())
print("\nSaved -> forecast_per_grid.xlsx")
