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
ss.setdefault("lmm_table", None)                 # LMM coefficient/p-value table
ss.setdefault("lmm_summary", None)               # LMM full text summary
ss.setdefault("lmm_info", None)                  # LMM rows/groups info
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
                "all_results", "selected_variant",
                "lmm_table", "lmm_summary", "lmm_info",
                "train_up", "pred_up", "lmm_up", "rst_del", "rst_confirm"]:
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

c1, c2, c3, c4 = st.columns(4)
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
with c4:
    st.button("④ Statistics (LMM)", use_container_width=True,
              type="primary" if ss.step == 4 else "secondary",
              on_click=lambda: ss.update(step=4))

st.markdown("---")


# ======================================================================
#  STEP 1 — TRAIN MODEL
# ======================================================================
if ss.step == 1:
    st.header("Step 1 — Train & Compare Models")
    st.write("Upload a labeled Excel file. Pick the **target column** and the **algorithm(s)**. "
             "We train each across data variants (Combined + processing variants), then you "
             "pick the best model to use. Works for **any** dataset (PPAC `SEVERITY` or "
             "Wallpe `SEV_Mean`).")

    if trained:
        st.success("✅ A trained model already exists. You can re-train below, "
                   "or skip to **Step 2 — Predict**.")

    # algorithm selector
    algo_choice = st.radio(
        "Algorithm to train",
        ["XGBoost only", "Random Forest only", "Both (compare)"],
        index=2, horizontal=True,
        help="XGBoost = primary model. Random Forest = simpler baseline. "
             "Both = train each and compare side by side.")
    ALGO_MAP = {"XGBoost only": ["XGBoost"],
                "Random Forest only": ["Random Forest"],
                "Both (compare)": ["XGBoost", "Random Forest"]}
    algos = ALGO_MAP[algo_choice]

    use_cv = st.checkbox(
        "🔁 Use 5-fold cross-validation (reliable scores — recommended for small data)",
        value=False,
        help="Tests each model 5 times on different grid folds and averages — so a single "
             "lucky split can't fool you. Slower, but the scores are trustworthy. "
             "Essential for small datasets like the 2025 Wallpe data.")

    train_file = st.file_uploader("📤 Upload TRAINING Excel", type=["xlsx"], key="train_up")

    if train_file is not None:
        # pick sheet if several (Wallpe file has sas/python/Sheet1/Sheet2)
        xls = pd.ExcelFile(train_file)
        sheet = (st.selectbox("Sheet", xls.sheet_names) if len(xls.sheet_names) > 1
                 else xls.sheet_names[0])
        df = pd.read_excel(train_file, sheet_name=sheet)
        st.write(f"Preview — {df.shape[0]} rows, {df.shape[1]} columns:")
        st.dataframe(df.head(5), height=170)

        # --- target column ---
        numcols = ml.numeric_columns(df)
        default_t = ("SEVERITY" if "SEVERITY" in numcols else
                     ("SEV_Mean" if "SEV_Mean" in numcols else (numcols[-1] if numcols else None)))
        target = st.selectbox("🎯 Target column (what to predict)", numcols,
                              index=numcols.index(default_t) if default_t in numcols else 0)

        # --- farm-record columns: exclude each one independently ---
        nondrone = [c for c in ["Fungi", "DAP"] if c in df.columns]
        excl_nondrone = []
        if nondrone:
            st.caption("Farm-record columns (not from the drone) — exclude any you won't "
                       "have at prediction time:")
            ncols = st.columns(len(nondrone))
            for i, col in enumerate(nondrone):
                if ncols[i].checkbox(f"Exclude {col}", value=(col == "DAP"),
                                     key=f"excl_{col}",
                                     help=f"Check to exclude {col} from the features. "
                                          f"Exclude it if your prediction files won't have {col}."):
                    excl_nondrone.append(col)

        # --- leakage exclusion ---
        suggested = ml.suggest_leakage_columns(df.columns, target)
        exclude = st.multiselect(
            "🚫 Columns to EXCLUDE from features (leakage protection)",
            options=[c for c in df.columns if c != target],
            default=suggested,
            help="Other disease/answer columns must be excluded so the model can't cheat. "
                 "Pre-filled with detected disease columns.")
        if excl_nondrone:                    # add the farm-record exclusions
            exclude = list(set(exclude) | set(excl_nondrone))
            st.caption(f"Also excluding: {', '.join(excl_nondrone)}.")

        # --- transparency: show exactly what is used vs excluded ---
        used_cols = list(ml.prepare_features(df, target=target, extra_drop=exclude).columns)
        excluded_ids = [c for c in ml.BASE_DROP if c in df.columns]
        excluded_user = [c for c in exclude if c in df.columns and c not in excluded_ids]
        with st.expander(f"🔎 Columns: {len(used_cols)} used as features  ·  "
                         f"{len(set(excluded_ids) | set(excluded_user)) + 1} excluded  (click to view)"):
            c_used, c_excl = st.columns(2)
            with c_used:
                st.markdown(f"**✅ Features used ({len(used_cols)})**")
                st.caption(", ".join(used_cols))
            with c_excl:
                st.markdown("**❌ Excluded**")
                st.caption(f"🎯 **Target:** {target}")
                if excluded_user:
                    st.caption(f"🚫 **Leakage / your choice:** {', '.join(excluded_user)}")
                st.caption(f"🆔 **ID columns (auto):** {', '.join(excluded_ids)}")

        n_models = len(algos) * len(ml.VARIANTS)
        if st.button(f"🚀 Train & Compare (up to {n_models} models)", type="primary"):
            spin = ("Cross-validating models (5 folds each)... this takes longer"
                    if use_cv else f"Training models ({' + '.join(algos)})... a few seconds")
            with st.spinner(spin):
                try:
                    ss.all_results = ml.train_all_variants(
                        df, algorithms=algos, target=target, extra_drop=exclude, cv=use_cv)
                    if not ss.all_results:
                        st.error("No models could be trained — check target/columns.")
                    else:
                        best = ml.comparison_table(ss.all_results)
                        best_label = f"{best.iloc[0]['Algorithm']} · {best.iloc[0]['Variant']}"
                        ss.selected_variant = best_label
                        st.success(f"🎉 Trained {len(ss.all_results)} models on target "
                                   f"'{target}'. Best by R²: **{best_label}**")
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
            use_container_width=True, height=min(420, 80 + 35 * len(table)))
        _kind = next(iter(ss.all_results.values()))["metrics"].get("split_kind", "")
        st.caption(f"Higher R² = better. Lower RMSE / MAE = better. "
                   f"Validation: **{_kind}**. "
                   + ("Cross-validated scores are reliable even on small data."
                      if "CV" in _kind else
                      "Single-split — reliable for large data, but can be lucky on small data "
                      "(enable cross-validation above for small datasets)."))

        # download the training comparison report
        _csv = table.to_csv(index=False).encode()
        st.download_button("📥 Download Training Report (CSV)", _csv,
                           "training_results_report.csv", "text/csv",
                           help="The model comparison table (R²/RMSE/MAE for each model).")

        st.subheader("✅ Choose the model to use for prediction")
        # labels match the result dict keys: 'Algorithm · Variant'
        names = [f"{r['Algorithm']} · {r['Variant']}" for _, r in table.iterrows()]
        choice = st.selectbox("Selected model", names,
                              index=names.index(ss.selected_variant)
                              if ss.selected_variant in names else 0)

        if st.button(f"Use “{choice}” for prediction", type="primary"):
            chosen = ss.all_results[choice]
            # store the full bundle so prediction aligns features correctly
            ss.model = {"model": chosen["model"], "features": chosen["features"],
                        "target": chosen["target"]}
            ss.metrics = chosen["metrics"]
            ss.importance = chosen["importance"]
            ss.selected_variant = choice
            ml.save_active(ss.model)             # persist the chosen bundle to disk
            st.success(f"Active model set to **{choice}** (target: {chosen['target']}) "
                       "and saved. ➡️ Go to **② Predict**.")

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
        xls = pd.ExcelFile(pred_file)
        psheet = (st.selectbox("Sheet", xls.sheet_names, key="pred_sheet")
                  if len(xls.sheet_names) > 1 else xls.sheet_names[0])
        new = pd.read_excel(pred_file, sheet_name=psheet)
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

    # ---- AUTO thresholds: adapt to THIS dataset's prediction scale ----
    pv = df["PREDICTED_SEVERITY"].astype(float)
    lo, hi = float(pv.min()), float(pv.max())
    if hi <= lo:                       # all predictions identical
        hi = lo + max(lo, 0.01)
    smax = round(hi * 1.25 + 1e-9, 4)  # slider top a bit above the max prediction
    step = max(round(smax / 100, 4), 0.0001)
    mod_def = round(float(pv.quantile(0.70)), 4)   # ~top 30% -> Moderate+
    sev_def = round(float(pv.quantile(0.90)), 4)   # ~top 10% -> Severe
    mod_def = min(max(mod_def, 0.0), smax)
    sev_def = min(max(sev_def, mod_def), smax)

    st.caption(f"🎯 Thresholds auto-suggested from the predictions "
               f"(range {lo:.3f}–{hi:.3f}). Adjust the sliders if needed.")
    s1, s2 = st.columns(2)
    mod = s1.slider("Moderate starts at severity ≥", 0.0, smax, mod_def, step)
    sev = s2.slider("Severe starts at severity ≥", 0.0, smax, sev_def, step)
    df["HEALTH_STATUS"] = df["PREDICTED_SEVERITY"].apply(lambda v: status_label(v, mod, sev))

    # KPI cards
    n_h = int((df.HEALTH_STATUS == "Healthy").sum())
    n_m = int((df.HEALTH_STATUS == "Moderate").sum())
    n_s = int((df.HEALTH_STATUS == "Severe").sum())
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total grids", f"{len(df):,}")
    k2.metric("🟢 Healthy", f"{n_h:,}")
    k3.metric("🟡 Moderate", f"{n_m:,}")
    k4.metric("🔴 Severe", f"{n_s:,}")

    # ---- Download KPI Report (share instead of screenshots) ----
    rep = io.BytesIO()
    with pd.ExcelWriter(rep, engine="openpyxl") as xw:
        summary = pd.DataFrame({
            "Metric": ["Total grids", "Healthy", "Moderate", "Severe",
                       "Healthy %", "Moderate %", "Severe %",
                       "Moderate threshold (>=)", "Severe threshold (>=)",
                       "Predicted severity min", "Predicted severity max",
                       "Predicted severity mean"],
            "Value": [len(df), n_h, n_m, n_s,
                      f"{n_h/len(df)*100:.1f}%", f"{n_m/len(df)*100:.1f}%", f"{n_s/len(df)*100:.1f}%",
                      round(mod, 4), round(sev, 4),
                      round(float(df.PREDICTED_SEVERITY.min()), 4),
                      round(float(df.PREDICTED_SEVERITY.max()), 4),
                      round(float(df.PREDICTED_SEVERITY.mean()), 4)],
        })
        summary.to_excel(xw, sheet_name="KPI Summary", index=False)
        if "DATE" in df.columns:                      # health counts per flight date
            by_date = (df.groupby(["DATE", "HEALTH_STATUS"]).size()
                         .unstack(fill_value=0).reset_index())
            by_date.to_excel(xw, sheet_name="By Flight Date", index=False)
        show = [c for c in ["POINT", "DATE", "LATITUDE", "LONGITUDE",
                            "PREDICTED_SEVERITY", "HEALTH_STATUS"] if c in df.columns]
        df[show].to_excel(xw, sheet_name="Predictions", index=False)
    st.download_button("📥 Download KPI Report (Excel)", rep.getvalue(),
                       "corn_disease_KPI_report.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       help="A shareable report: KPI summary, per-flight counts, and all "
                            "predictions — send this instead of screenshots.")
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


# ======================================================================
#  STEP 4 — STATISTICAL ANALYSIS (LINEAR MIXED MODEL)
# ======================================================================
elif ss.step == 4:
    st.header("Step 4 — Statistical Analysis (Linear Mixed Model)")
    st.write("Unlike XGBoost (best **prediction**), the LMM gives **explanation**: which "
             "vegetation indices have a *statistically significant* effect on disease, "
             "while correctly handling repeated measurements of each grid (`POINT` = random "
             "effect). It uses a clean, non-redundant set of predictors.")

    lmm_file = st.file_uploader("📤 Upload labeled Excel (must include the target & POINT)",
                               type=["xlsx"], key="lmm_up")

    if lmm_file is not None:
        xls = pd.ExcelFile(lmm_file)
        lsheet = (st.selectbox("Sheet", xls.sheet_names, key="lmm_sheet")
                  if len(xls.sheet_names) > 1 else xls.sheet_names[0])
        ldf = pd.read_excel(lmm_file, sheet_name=lsheet)
        st.caption(f"Loaded {ldf.shape[0]} rows.")

        lnum = ml.numeric_columns(ldf)
        ldef = ("SEVERITY" if "SEVERITY" in lnum else
                ("SEV_Mean" if "SEV_Mean" in lnum else (lnum[-1] if lnum else None)))
        ltarget = st.selectbox("🎯 Target column", lnum,
                               index=lnum.index(ldef) if ldef in lnum else 0)

        # predictors: the clean index means present in this file (+ optional extras)
        cand = [c for c in ml.LMM_FIXED if c in ldf.columns]
        for opt in ["Fungi", "DAP"]:           # offer the Wallpe experimental factors
            if opt in ldf.columns:
                cand.append(opt)

        advanced = st.checkbox(
            "➕ Advanced: choose predictors from ALL columns",
            value=False,
            help="By default the LMM offers only clean, non-duplicate predictors. Check this "
                 "to pick from every numeric column — but adding duplicates (STD/MIN/MAX, bands) "
                 "can make the p-values unreliable.")
        if advanced:
            # all numeric columns except the target, IDs and other disease columns
            skip = set(ml.BASE_DROP) | {ltarget} | set(ml.suggest_leakage_columns(ldf.columns, ltarget))
            options = [c for c in ml.numeric_columns(ldf) if c not in skip]
            st.warning("⚠️ Advanced mode: adding correlated columns (STD/MIN/MAX, raw bands) "
                       "can distort the coefficients and p-values. Use with care.")
        else:
            options = cand
        fixed = st.multiselect(
            "Predictors (fixed effects) — deselect any to EXCLUDE it",
            options=options, default=[c for c in cand if c in options],
            help="Deselect a predictor to exclude it. In advanced mode you can also add other columns.")

        # --- transparency: what the LMM uses vs excludes ---
        with st.expander(f"🔎 Columns the LMM uses ({len(fixed)} predictors) vs excluded  (click to view)"):
            st.markdown("**✅ Used by the LMM**")
            st.caption(f"🎯 Outcome: **{ltarget}**  ·  🎲 Random effect: **POINT** (grid)")
            st.caption(f"📊 Fixed effects ({len(fixed)}): {', '.join(fixed) if fixed else '(none selected)'}")
            st.markdown("**❌ Excluded on purpose**")
            st.caption("STD / MIN / MAX columns, raw spectral bands, and LATITUDE/LONGITUDE — "
                       "they are near-duplicates of the index means (correlation 0.9–1.0). "
                       "Feeding duplicates to a linear model makes its coefficients and p-values "
                       "unreliable, so the LMM keeps only one clean signal per index.")
            st.info("Why fewer columns than XGBoost? XGBoost can use all 50+ features because trees "
                    "ignore duplicates. The LMM must give trustworthy p-values, so it needs clean, "
                    "non-redundant predictors — hence this focused set.")

        if st.button("📈 Run Linear Mixed Model", type="primary"):
            with st.spinner("Fitting the Linear Mixed Model..."):
                try:
                    tbl, summary, info = ml.fit_lmm(ldf, fixed=fixed, target=ltarget)
                    ss.lmm_table, ss.lmm_summary, ss.lmm_info = tbl, summary, info
                    st.success(f"✅ Fitted on {info['rows']:,} rows across "
                               f"{info['groups']} grids (target: {ltarget}).")
                except Exception as e:
                    st.error(f"LMM failed: {e}")

    # results
    if ss.lmm_table is not None:
        info = ss.lmm_info
        st.caption(f"Model: {info['formula']}  ·  random effect: POINT  ·  "
                   f"{info['rows']:,} rows / {info['groups']} grids")

        st.subheader("📋 Disease drivers — coefficients & significance")
        tbl = ss.lmm_table.copy()
        st.dataframe(
            tbl.style.format({"Coefficient": "{:.3f}", "p_value": "{:.4f}"})
               .background_gradient(subset=["p_value"], cmap="Greens_r"),
            use_container_width=True, height=min(420, 80 + 35 * len(tbl)))
        st.caption("Lower p-value = more statistically significant. "
                   "*** p<0.001, ** p<0.01, * p<0.05. "
                   "Positive coefficient = raises severity; negative = lowers it.")

        # download the LMM report
        _lcsv = tbl.to_csv(index=False).encode()
        st.download_button("📥 Download LMM Report (CSV)", _lcsv,
                           "lmm_results_report.csv", "text/csv",
                           help="The LMM coefficients, p-values, and significance.")

        st.subheader("📊 Effect direction & size (significant drivers)")
        sig = tbl[tbl["Significant"] != "not significant"].copy()
        if len(sig):
            sig = sig.sort_values("Coefficient")
            sig["dir"] = sig["Coefficient"].apply(lambda v: "raises severity" if v > 0
                                                  else "lowers severity")
            fig = px.bar(sig, x="Coefficient", y="Feature", orientation="h",
                         color="dir", color_discrete_map={"raises severity": "#e74c3c",
                                                          "lowers severity": "#2ecc71"},
                         height=420)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No significant predictors at p<0.05 with the current selection.")

        with st.expander("🔬 Full statistical summary (advanced)"):
            st.text(ss.lmm_summary)

        st.info("Note: the LMM is for **explanation/reporting**, not the prediction maps. "
                "Use Steps ①–③ for prediction.")
