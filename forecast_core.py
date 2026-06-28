"""
forecast_core.py — reusable hybrid-forecast engine (growth model + Markov chain).
Used by both forecast_app.py and the main dashboard's Step 5.
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import ml_core as ml

STATE_NAMES = ["Healthy", "Low", "Moderate", "Severe"]


def exp_growth(t, y0, r):
    return y0 * np.exp(r * t)


def logistic(t, K, r, m):
    return K / (1 + np.exp(-r * (t - m)))


def forecast_grid(days, sev, horizons, cap):
    """Fit a curve once, forecast at each horizon. cap = max severity (scale-aware ceiling)."""
    days = np.asarray(days, float)
    sev = np.clip(np.asarray(sev, float), 1e-6, None)
    t0 = days.min(); x = days - t0; last = days.max()
    def at(fn, p):
        return {h: min(float(fn(last + h - t0, *p)), cap) for h in horizons}
    try:   # logistic K is bounded to the data's own scale (not a fixed 1.0)
        p, _ = curve_fit(logistic, x, sev, p0=[max(sev.max() * 1.5, cap * 0.5), .2, x.mean()],
                         maxfev=8000, bounds=([sev.max(), 0, -50], [cap * 1.2, 2, 200]))
        return at(logistic, p), float(p[1]), "logistic"
    except Exception:
        try:
            p, _ = curve_fit(exp_growth, x, sev, p0=[sev[0], .1], maxfev=5000)
            return at(exp_growth, p), float(p[1]), "exponential"
        except Exception:
            return {h: float(sev[-1]) for h in horizons}, 0.0, "flat"


def to_days(series):
    """Convert a time column to real day-numbers.
    Handles DAP (already days) AND date-codes like 6242021 / 8062025 (M[M]DDYYYY)."""
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return s.astype(float)
    if s.dropna().max() > 1_000_000:           # looks like a date-code -> parse to dates
        def parse(v):
            try:
                t = str(int(v)).zfill(8)        # MMDDYYYY
                return pd.Timestamp(year=int(t[4:]), month=int(t[:2]), day=int(t[2:4]))
            except Exception:
                return pd.NaT
        dates = series.apply(parse)
        return (dates - dates.min()).dt.days.astype(float)
    return s.astype(float)                       # already a day count (e.g. DAP)


def to_state(s, c1, c2, c3):
    if s < c1: return 0
    if s < c2: return 1
    if s < c3: return 2
    return 3


def risk_level(cs, fval, rate, c2, c3):
    if cs >= 3 or fval >= c3:                 # already severe OR forecast crosses severe
        return "🔴 RED — severe / heading severe"
    if cs == 2 or fval >= c2 or rate > 0.15:  # moderate OR forecast crosses moderate OR fast
        return "🟠 ORANGE — rising"
    if rate > 0.05:
        return "🟡 YELLOW — watch"
    return "🟢 GREEN — stable"


def run_forecast(df, sev_col, time_col, algo="Random Forest",
                 horizons=(7, 14, 21), risk_h=14, cutoffs=None):
    """Full hybrid forecast. Returns (per_grid_table, transition_matrix, ts, info).
    cutoffs=None -> auto-scaled to the data (works for 0-1 or 0-100 severity)."""
    horizons = list(horizons)

    # 1. get the predicted-severity series (use existing PREDICTED_SEVERITY if present)
    already = "PREDICTED_SEVERITY" in df.columns
    if already:
        pred = df.copy()
        pred["PREDICTED_SEVERITY"] = pd.to_numeric(pred["PREDICTED_SEVERITY"], errors="coerce")
    else:
        leak = ml.suggest_leakage_columns(df.columns, sev_col)
        drop = leak + ([time_col] if time_col == "DAP" else [])
        res = ml.train_all_variants(df, algorithms=[algo], target=sev_col,
                                    extra_drop=drop, cv=False)
        ch = res[f"{algo} · Combined (all data)"]
        bundle = {"model": ch["model"], "features": ch["features"], "target": sev_col}
        pred = ml.predict(bundle, df)

    pred[time_col] = to_days(pred[time_col])     # parse dates/DAP into real day-numbers
    pred = pred.dropna(subset=[time_col, "POINT", "PREDICTED_SEVERITY"])
    keep = ["POINT", time_col, "PREDICTED_SEVERITY"]
    if {"LATITUDE", "LONGITUDE"}.issubset(pred.columns):
        keep += ["LATITUDE", "LONGITUDE"]
    ts = (pred.drop_duplicates(["POINT", time_col]).sort_values(["POINT", time_col])
            [keep].reset_index(drop=True))

    # ---- SCALE-AWARE cutoffs & cap (works for 0-1 OR 0-100 severity) ----
    smax = float(ts["PREDICTED_SEVERITY"].max())
    cap = max(smax * 1.5, 1.0)                       # forecast ceiling matches the data scale
    if cutoffs is None:
        c1, c2, c3 = smax * 0.05, smax * 0.20, smax * 0.50   # 5% / 20% / 50% of the max
    else:
        c1, c2, c3 = cutoffs

    # 2. Markov transition matrix (from all grids)
    counts = np.zeros((4, 4))
    for g, sub in ts.groupby("POINT"):
        seq = [to_state(s, c1, c2, c3) for s in sub.sort_values(time_col)["PREDICTED_SEVERITY"]]
        for a, b in zip(seq[:-1], seq[1:]):
            counts[a][b] += 1
    P = np.divide(counts, counts.sum(axis=1, keepdims=True),
                  out=np.zeros_like(counts), where=counts.sum(axis=1, keepdims=True) > 0)

    # 3. per-grid forecast
    rows = []
    for g, sub in ts.groupby("POINT"):
        sub = sub.sort_values(time_col)
        cur = float(sub["PREDICTED_SEVERITY"].iloc[-1]); cs = to_state(cur, c1, c2, c3)
        fdict, rate, model = forecast_grid(sub[time_col].values,
                                           sub["PREDICTED_SEVERITY"].values, horizons, cap)
        p_worse = float(P[cs][cs + 1:].sum()) if cs < 3 else 0.0
        row = {"POINT": g, "predicted_severity_now": round(cur, 3),
               "state": STATE_NAMES[cs], "growth_rate/day": round(rate, 3)}
        for h in horizons:
            row[f"forecast_+{h}d"] = round(fdict[h], 3)
        row["prob_worse_next"] = round(p_worse, 2)
        row["RISK"] = risk_level(cs, fdict[risk_h], rate, c2, c3)
        if "LATITUDE" in sub.columns:
            row["LAT"] = sub["LATITUDE"].iloc[-1]; row["LON"] = sub["LONGITUDE"].iloc[-1]
        rows.append(row)

    out = (pd.DataFrame(rows).sort_values(f"forecast_+{risk_h}d", ascending=False)
             .reset_index(drop=True))
    info = {"grids": ts["POINT"].nunique(), "used_existing_predictions": already,
            "time_col": time_col, "horizons": horizons}
    # ts (the per-grid time series) is returned too, for per-grid curve plots
    return out, P, ts, info


def grid_curve(ts, time_col, point, horizons):
    """Return (history_days, history_sev, curve_days, curve_sev) for one grid — for plotting."""
    cap = max(float(ts["PREDICTED_SEVERITY"].max()) * 1.5, 1.0)   # scale-aware ceiling
    sub = ts[ts["POINT"] == point].sort_values(time_col)
    days = sub[time_col].values.astype(float)
    sev = sub["PREDICTED_SEVERITY"].values.astype(float)
    fdict, rate, model = forecast_grid(days, sev, horizons, cap)
    # smooth curve from first day to the furthest horizon
    t0 = days.min(); last = days.max()
    span = np.linspace(0, (last - t0) + max(horizons), 60)
    sv = np.clip(np.asarray(sev, float), 1e-6, None)
    try:
        if model == "logistic":
            p, _ = curve_fit(logistic, days - t0, sv, p0=[max(sv.max()*1.5, cap*0.5), .2, (days-t0).mean()],
                             maxfev=8000, bounds=([sv.max(), 0, -50], [cap*1.2, 2, 200]))
            cy = [min(float(logistic(t, *p)), cap) for t in span]
        else:
            p, _ = curve_fit(exp_growth, days - t0, sv, p0=[sv[0], .1], maxfev=5000)
            cy = [min(float(exp_growth(t, *p)), cap) for t in span]
    except Exception:
        cy = [float(sev[-1])] * len(span)
    return days, sev, (span + t0), np.array(cy), fdict, rate, model
