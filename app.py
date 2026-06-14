"""
==========================================================================
  CORN DISEASE AI — GUIDED WORKFLOW DASHBOARD
==========================================================================
A step-by-step web app:
   STEP 1  Train Model   -> upload labeled Excel, click Train
   STEP 2  Predict       -> upload new Excel, get severity predictions
   STEP 3  Dashboard     -> map, trends, feature importance, download

RUN:  streamlit run app.py   (or double-click run_dashboard.bat)
==========================================================================
"""

import io
import pandas as pd
import streamlit as st
import plotly.express as px

import importlib
import ml_core as ml
importlib.reload(ml)   # ensure the latest ml_core is used after edits (no stale cache)

st.set_page_config(page_title="Corn Disease AI", page_icon="🌽", layout="wide")

# ---------- session memory (persists while the app is open) ----------
ss = st.session_state
ss.setdefault("model", ml.load_saved_model())   # auto-load if already trained before
ss.setdefault("metrics", None)
ss.setdefault("importance", None)
ss.setdefault("predictions", None)
ss.setdefault("all_results", None)               # all 5 trained variant models
ss.setdefault("selected_variant", None)          # which one the user chose
ss.setdefault("step", 1)

COLORS = {"Healthy": "#2ecc71", "Moderate": "#f1c40f", "Severe": "#e74c3c"}


def status_label(v, mod, sev):
    return "Healthy" if v < mod else ("Moderate" if v < sev else "Severe")


def reset_all(delete_model_file: bool):
    """Clear all in-memory state and return to Step 1.
    Optionally also delete the saved model file from disk."""
    import os
    if delete_model_file and os.path.exists(ml.MODEL_PATH):
        try:
            os.remove(ml.MODEL_PATH)
        except OSError:
            pass
    # clear workflow state + the uploader and reset-checkbox widgets
    for key in ["model", "metrics", "importance", "predictions",
                "all_results", "selected_variant", "train_up", "pred_up",
                "rst_del", "rst_confirm"]:
        ss.pop(key, None)
    ss.step = 1
    # If the model file was kept, reload it so Step 2 stays available;
    # if it was deleted, model becomes None and the user must re-train.
    ss.model = None if delete_model_file else ml.load_saved_model()


# ---------- sidebar: Reset / Start Over ----------
with st.sidebar:
    st.header("🔄 Reset")
    st.caption("Clear the current session and start the workflow again.")
    also_delete = st.checkbox("Also delete the trained model file from disk",
                              value=False, key="rst_del",
                              help="If unchecked, the saved model stays and will "
                                   "auto-load next time. If checked, you must "
                                   "re-train in Step 1.")
    confirm = st.checkbox("Yes, I'm sure", key="rst_confirm")
    if st.button("🗑️ Reset / Start Over", type="primary",
                 disabled=not confirm, use_container_width=True):
        reset_all(also_delete)
        st.success("Reset done — back to Step 1.")
        st.rerun()      # force an immediate redraw so no manual refresh is needed


# ======================================================================
#  HEADER + STEP NAVIGATION
# ======================================================================
st.title("🌽 Corn Disease AI — Guided Workflow")

c1, c2, c3 = st.columns(3)
trained = ss.model is not None
predicted = ss.predictions is not None
with c1:
    st.button("① Train Model", use_container_width=True,
              type="primary" if ss.step == 1 else "secondary",
              on_click=lambda: ss.update(step=1))
with c2:
    st.button("② Predict" + (" ✅" if trained else " 🔒"), use_container_width=True,
              type="primary" if ss.step == 2 else "secondary",
              on_click=lambda: ss.update(step=2))
with c3:
    st.button("③ Dashboard" + (" ✅" if predicted else " 🔒"), use_container_width=True,
              type="primary" if ss.step == 3 else "secondary",
              on_click=lambda: ss.update(step=3))

st.markdown("---")


# ======================================================================
#  STEP 1 — TRAIN MODEL
# ======================================================================
if ss.step == 1:
    st.header("Step 1 — Train & Compare Models")
    st.write("Upload an Excel file that **contains a `SEVERITY` column**. We train **five "
             "models** — one **Combined** (all data) plus four **processing variants** "
             "(whole / orthorectified × soil YES / NO) — then you pick the best one to use "
             "for prediction.")

    if trained:
        st.success("✅ A trained model already exists. You can re-train below, "
                   "or skip to **Step 2 — Predict**.")

    train_file = st.file_uploader("📤 Upload TRAINING Excel (must include SEVERITY)",
                                  type=["xlsx"], key="train_up")

    if train_file is not None:
        df = pd.read_excel(train_file)
        st.write(f"Preview — {df.shape[0]} rows, {df.shape[1]} columns:")
        st.dataframe(df.head(5), height=180)

        if "SEVERITY" not in df.columns:
            st.error("❌ This file has no `SEVERITY` column, so it cannot be used for "
                     "training. Use a labeled file, or go to Step 2 to predict.")
        elif st.button("🚀 Train & Compare All 5 Models", type="primary"):
            with st.spinner("Training 5 XGBoost models... this takes a few seconds"):
                try:
                    ss.all_results = ml.train_all_variants(df)
                    # default selection = best by R2
                    best = ml.comparison_table(ss.all_results).iloc[0]["Variant"]
                    ss.selected_variant = best
                    st.success(f"🎉 Trained {len(ss.all_results)} models. "
                               f"Best by R²: **{best}**")
                except Exception as e:
                    st.error(f"Training failed: {e}")

    # ---- show comparison + let user choose ----
    if ss.all_results:
        st.subheader("📊 Model comparison")
        table = ml.comparison_table(ss.all_results)
        st.dataframe(
            table.style.format({"R2": "{:.3f}", "RMSE": "{:.3f}", "MAE": "{:.3f}"})
                 .background_gradient(subset=["R2"], cmap="Greens")
                 .background_gradient(subset=["RMSE", "MAE"], cmap="Reds_r"),
            use_container_width=True, height=240)
        st.caption("Higher R² = better. Lower RMSE / MAE = better. "
                   "Each model uses an honest grid-grouped split.")

        st.subheader("✅ Choose the model to use for prediction")
        names = table["Variant"].tolist()
        choice = st.selectbox("Selected model", names,
                              index=names.index(ss.selected_variant)
                              if ss.selected_variant in names else 0)

        if st.button(f"Use “{choice}” for prediction", type="primary"):
            chosen = ss.all_results[choice]
            ss.model = chosen["model"]
            ss.metrics = chosen["metrics"]
            ss.importance = chosen["importance"]
            ss.selected_variant = choice
            ml.save_active(chosen["model"])      # persist the chosen model to disk
            st.success(f"Active model set to **{choice}** and saved. "
                       "➡️ Go to **② Predict**.")

        # details of the chosen model
        if ss.metrics and ss.selected_variant:
            m = ss.metrics
            st.markdown(f"**Active model:** {ss.selected_variant}")
            a, b, c, d = st.columns(4)
            a.metric("R² (accuracy)", f"{m['R2']:.3f}", help="1.0 = perfect")
            b.metric("RMSE", f"{m['RMSE']:.3f}", help="lower is better")
            c.metric("MAE", f"{m['MAE']:.3f}", help="typical error")
            d.metric("Rows trained on", f"{m['rows_used']:,}")
            st.subheader("What drives this model (top features)")
            imp = ss.importance.head(15).reset_index()
            imp.columns = ["Feature", "Importance"]
            st.plotly_chart(px.bar(imp.iloc[::-1], x="Importance", y="Feature",
                                   orientation="h", height=420), use_container_width=True)


# ======================================================================
#  STEP 2 — PREDICT
# ======================================================================
elif ss.step == 2:
    st.header("Step 2 — Predict on New Data")

    if not trained:
        st.warning("🔒 No trained model yet. Please complete **Step 1 — Train Model** first.")
        st.stop()

    st.write("Upload a **new** drone-data Excel (the disease is unknown). It must have the "
             "same vegetation-index / band columns as the training data. A `SEVERITY` column "
             "is **not** required here.")

    pred_file = st.file_uploader("📤 Upload NEW data Excel to predict", type=["xlsx"],
                                 key="pred_up")

    if pred_file is not None:
        new = pd.read_excel(pred_file)
        st.write(f"Loaded {new.shape[0]} grids.")
        if st.button("🔮 Run Prediction", type="primary"):
            try:
                result = ml.predict(ss.model, new)
                ss.predictions = result
                st.success(f"✅ Predicted severity for {len(result):,} grids.")
            except Exception as e:
                st.error(f"Prediction failed — check the columns match training. {e}")

    if ss.predictions is not None:
        df = ss.predictions
        st.subheader("Predictions")
        show = [c for c in ["POINT", "DATE", "PREDICTED_SEVERITY"] if c in df.columns]
        st.dataframe(df[show + [c for c in df.columns if c not in show]], height=350)

        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        st.download_button("⬇️ Download predictions (Excel)", buf.getvalue(),
                           "corn_disease_predictions.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.info("➡️ Click **③ Dashboard** at the top to visualize these results.")


# ======================================================================
#  STEP 3 — DASHBOARD
# ======================================================================
elif ss.step == 3:
    st.header("Step 3 — Dashboard")

    if ss.predictions is None:
        st.warning("🔒 No predictions yet. Please complete **Step 2 — Predict** first.")
        st.stop()

    df = ss.predictions.copy()

    # thresholds
    s1, s2 = st.columns(2)
    mod = s1.slider("Moderate starts at severity ≥", 0.1, 2.0, 0.5, 0.1)
    sev = s2.slider("Severe starts at severity ≥", 1.0, 6.0, 2.0, 0.5)
    df["HEALTH_STATUS"] = df["PREDICTED_SEVERITY"].apply(lambda v: status_label(v, mod, sev))

    # KPI cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total grids", f"{len(df):,}")
    k2.metric("🟢 Healthy", f"{(df.HEALTH_STATUS=='Healthy').sum():,}")
    k3.metric("🟡 Moderate", f"{(df.HEALTH_STATUS=='Moderate').sum():,}")
    k4.metric("🔴 Severe", f"{(df.HEALTH_STATUS=='Severe').sum():,}")
    st.markdown("---")

    tab_map, tab_time, tab_imp = st.tabs(["🗺️ Field Map", "📈 Over Time", "⭐ Feature Importance"])

    with tab_map:
        if {"LATITUDE", "LONGITUDE"}.issubset(df.columns):
            dates = sorted(df["DATE"].unique()) if "DATE" in df.columns else [None]
            pick = st.selectbox("Flight date", dates) if dates[0] is not None else None
            d = df[df["DATE"] == pick] if pick is not None else df
            fig = px.scatter(d, x="LONGITUDE", y="LATITUDE", color="PREDICTED_SEVERITY",
                             color_continuous_scale="RdYlGn_r",
                             hover_data=[c for c in ["POINT", "HEALTH_STATUS"] if c in d.columns],
                             height=560)
            fig.update_traces(marker=dict(size=11))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No LATITUDE/LONGITUDE columns — map needs them.")

    with tab_time:
        if "DATE" in df.columns:
            ts = df.groupby("DATE")["PREDICTED_SEVERITY"].mean().reset_index()
            ts["DATE"] = ts["DATE"].astype(str)
            st.plotly_chart(px.line(ts, x="DATE", y="PREDICTED_SEVERITY", markers=True,
                            title="Average predicted severity per flight"),
                            use_container_width=True)
            cnt = df.groupby(["DATE", "HEALTH_STATUS"]).size().reset_index(name="grids")
            cnt["DATE"] = cnt["DATE"].astype(str)
            st.plotly_chart(px.bar(cnt, x="DATE", y="grids", color="HEALTH_STATUS",
                            color_discrete_map=COLORS, title="Grid health per flight"),
                            use_container_width=True)
        else:
            st.warning("No DATE column — time view needs it.")

    with tab_imp:
        if ss.importance is not None:
            imp = ss.importance.head(15).reset_index()
            imp.columns = ["Feature", "Importance"]
            st.plotly_chart(px.bar(imp.iloc[::-1], x="Importance", y="Feature",
                            orientation="h", height=450), use_container_width=True)
        else:
            st.info("Train a model in Step 1 to see feature importance.")
