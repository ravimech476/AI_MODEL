"""
==========================================================================
  🔮 DISEASE FORECAST DASHBOARD  (separate hybrid-forecast app)
==========================================================================
Upload a labeled time-series Excel  ->  per-grid future forecast:
   Drone-ML (XGBoost/RF) predicts severity  ->  Growth model + Markov chain
   ->  per-grid table: predicted severity -> state -> forecast -> RISK

RUN:  streamlit run forecast_app.py
==========================================================================
"""
import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from scipy.optimize import curve_fit
import ml_core as ml

st.set_page_config(page_title="Disease Forecast", page_icon="🔮", layout="wide")
st.title("🔮 Corn Disease Forecast Dashboard")
st.caption("Hybrid forecast: Drone-ML (current) + Growth model (future number) + Markov chain (future odds)")

STATE_NAMES = ["Healthy", "Low", "Moderate", "Severe"]


# ---------------- growth + markov helpers ----------------
def exp_growth(t, y0, r): return y0 * np.exp(r * t)
def logistic(t, K, r, m): return K / (1 + np.exp(-r * (t - m)))

def forecast_grid(days, sev, horizons):
    days = np.asarray(days, float); sev = np.clip(np.asarray(sev, float), 1e-6, None)
    t0 = days.min(); x = days - t0; last = days.max()
    def at(fn, p): return {h: min(float(fn(last + h - t0, *p)), 1.0) for h in horizons}
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

def to_state(s, c1, c2, c3):
    if s < c1: return 0
    if s < c2: return 1
    if s < c3: return 2
    return 3

def risk_level(cs, fval, rate, c3):
    if cs >= 3 or fval >= c3:        return "🔴 RED — severe / heading severe"
    if cs == 2 or fval >= 0.05 or rate > 0.15: return "🟠 ORANGE — rising"
    if rate > 0.05:                  return "🟡 YELLOW — watch"
    return "🟢 GREEN — stable"


# ---------------- sidebar settings ----------------
st.sidebar.header("⚙️ Settings")
algo = st.sidebar.radio("Drone-ML model", ["Random Forest", "XGBoost"],
                        help="Which model predicts the current severity from drone data.")
horizons_txt = st.sidebar.text_input("Forecast horizons (days, comma-separated)", "7, 14, 21")
HORIZONS = [int(x) for x in horizons_txt.replace(" ", "").split(",") if x]
risk_h = st.sidebar.selectbox("Risk based on horizon (days)", HORIZONS,
                              index=min(1, len(HORIZONS)-1))
st.sidebar.markdown("**State cutoffs (severity)**")
c1 = st.sidebar.number_input("Healthy below", value=0.01, step=0.01, format="%.3f")
c2 = st.sidebar.number_input("Low below", value=0.05, step=0.01, format="%.3f")
c3 = st.sidebar.number_input("Severe at/above", value=0.15, step=0.01, format="%.3f")

# ---------------- upload ----------------
up = st.file_uploader("📤 Upload labeled time-series Excel (needs POINT, a time column, severity)",
                      type=["xlsx"])
if up is None:
    st.info("👈 Upload a file to forecast. It must have grids (POINT), a time column "
            "(DAP or DATE), and a severity column.")
    st.stop()

xls = pd.ExcelFile(up)
sheet = st.selectbox("Sheet", xls.sheet_names) if len(xls.sheet_names) > 1 else xls.sheet_names[0]
df = pd.read_excel(up, sheet_name=sheet)

c1c, c2c, c3c = st.columns(3)
numcols = ml.numeric_columns(df)
sev_col = c1c.selectbox("🎯 Severity column", numcols,
                        index=numcols.index("NEW_SEV_Mean") if "NEW_SEV_Mean" in numcols
                        else (numcols.index("SEVERITY") if "SEVERITY" in numcols else 0))
time_opts = [c for c in ["DAP", "DATE", "DATE1"] if c in df.columns] or list(df.columns)
time_col = c2c.selectbox("⏱️ Time column", time_opts)
c3c.metric("Grids", df["POINT"].nunique() if "POINT" in df.columns else "—")

# If the file already has PREDICTED_SEVERITY, use it directly (uploaded prediction file)
already_predicted = "PREDICTED_SEVERITY" in df.columns
if already_predicted:
    st.success("✅ This file already has a **PREDICTED_SEVERITY** column — the forecast will "
               "use it directly (no re-training needed).")
else:
    st.info("This file has no PREDICTED_SEVERITY — the forecast will train the drone-ML and "
            "predict internally.")

if st.button("🔮 Run Forecast", type="primary"):
    with st.spinner(f"Forecasting ({'using uploaded predictions' if already_predicted else algo + ' drone-ML'} "
                    "+ growth + Markov)..."):
        if already_predicted:
            # use the predictions already in the file
            pred = df.copy()
            pred["PREDICTED_SEVERITY"] = pd.to_numeric(pred["PREDICTED_SEVERITY"], errors="coerce")
        else:
            # train the drone-ML and predict internally
            leak = ml.suggest_leakage_columns(df.columns, sev_col)
            res = ml.train_all_variants(df, algorithms=[algo], target=sev_col,
                                        extra_drop=leak + ([time_col] if time_col in ("DAP",) else []),
                                        cv=False)
            ch = res[f"{algo} · Combined (all data)"]
            bundle = {"model": ch["model"], "features": ch["features"], "target": sev_col}
            pred = ml.predict(bundle, df)
        pred[time_col] = pd.to_numeric(pred[time_col], errors="coerce")
        pred = pred.dropna(subset=[time_col, "POINT"])
        ts = (pred.drop_duplicates(["POINT", time_col]).sort_values(["POINT", time_col])
                [["POINT", time_col, "PREDICTED_SEVERITY", "LATITUDE", "LONGITUDE"]
                 if {"LATITUDE", "LONGITUDE"}.issubset(pred.columns)
                 else ["POINT", time_col, "PREDICTED_SEVERITY"]].reset_index(drop=True))

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
                                               sub["PREDICTED_SEVERITY"].values, HORIZONS)
            p_worse = float(P[cs][cs+1:].sum()) if cs < 3 else 0.0
            row = {"POINT": g, "predicted_severity_now": round(cur, 3),
                   "state": STATE_NAMES[cs], "growth_rate/day": round(rate, 3)}
            for h in HORIZONS:
                row[f"forecast_+{h}d"] = round(fdict[h], 3)
            row["prob_worse_next"] = round(p_worse, 2)
            row["RISK"] = risk_level(cs, fdict[risk_h], rate, c3)
            if "LATITUDE" in sub.columns:
                row["LAT"] = sub["LATITUDE"].iloc[-1]; row["LON"] = sub["LONGITUDE"].iloc[-1]
            rows.append(row)
        out = pd.DataFrame(rows).sort_values(f"forecast_+{risk_h}d", ascending=False).reset_index(drop=True)
        st.session_state["fc"] = out
        st.session_state["P"] = P

# ---------------- results ----------------
if "fc" in st.session_state:
    out = st.session_state["fc"]; P = st.session_state["P"]
    st.success(f"Forecast ready for {len(out)} grids.")

    # KPI risk counts
    def cnt(key): return int(out["RISK"].str.contains(key).sum())
    k = st.columns(4)
    k[0].metric("🔴 Severe-risk", cnt("RED"))
    k[1].metric("🟠 Rising", cnt("ORANGE"))
    k[2].metric("🟡 Watch", cnt("YELLOW"))
    k[3].metric("🟢 Stable", cnt("GREEN"))
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 Per-grid forecast", "🗺️ Risk map", "🎲 Markov rules"])

    with tab1:
        st.subheader("Per-grid forecast (predicted severity → state → forecast → risk)")
        st.dataframe(out, use_container_width=True, height=560)
        buf = io.BytesIO(); out.to_excel(buf, index=False)
        st.download_button("⬇️ Download forecast (Excel)", buf.getvalue(),
                           "disease_forecast.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab2:
        if {"LAT", "LON"}.issubset(out.columns):
            m = out.copy()
            def _rcat(r):
                if "RED" in r: return "🔴 Severe risk"
                if "ORANGE" in r: return "🟠 Rising"
                if "YELLOW" in r: return "🟡 Watch"
                return "🟢 Stable"
            m["Risk"] = m["RISK"].apply(_rcat)
            cmap = {"🔴 Severe risk": "#e74c3c", "🟠 Rising": "#e67e22",
                    "🟡 Watch": "#f1c40f", "🟢 Stable": "#2ecc71"}
            order = ["🔴 Severe risk", "🟠 Rising", "🟡 Watch", "🟢 Stable"]
            fcols = [c for c in m.columns if c.startswith("forecast_")]
            fig = px.scatter(m, x="LON", y="LAT", color="Risk",
                             color_discrete_map=cmap, category_orders={"Risk": order},
                             hover_data=["POINT", "state"] + fcols, height=560,
                             title="Grids colored by combined RISK (growth model + Markov chain)")
            fig.update_traces(marker=dict(size=14, line=dict(width=0.5, color="#333")))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Color = combined RISK (both models). 🔴 spray now · 🟠 plan · 🟡 watch · 🟢 stable.")
        else:
            st.warning("No LATITUDE/LONGITUDE columns — map needs them.")

    with tab3:
        st.subheader("Markov transition matrix (chance of moving between states)")
        mat = pd.DataFrame(np.round(P, 2), index=STATE_NAMES, columns=STATE_NAMES)
        st.dataframe(mat.style.background_gradient(cmap="Reds"), use_container_width=True)
        st.caption("Read a row: 'if a grid is in this state now, here are the % chances for next flight'. "
                   "Zeros below the diagonal = disease only worsens, never improves.")
