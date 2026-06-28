"""
==========================================================================
  HOW TO USE THE MODELS WITH DIFFERENT INPUTS  —  Team Tutorial
==========================================================================
This script shows, step by step, how to use the three models
(XGBoost, Random Forest, Linear Mixed Model) with DIFFERENT inputs:
  - different Excel files
  - different target columns
  - different feature sets (include / exclude columns)
  - predicting on new data

Everything goes through ml_core.py (the engine). Run any example below.

Run:  python use_models_examples.py
==========================================================================
"""
import pandas as pd
import ml_core as ml          # <-- the engine: all model functions live here


# =========================================================================
# EXAMPLE 1 — Train on ANY file, with ANY target
# =========================================================================
def example_1_train():
    print("\n--- EXAMPLE 1: Train models on a chosen file + target ---")

    # STEP 1: load any Excel into a table
    df = pd.read_excel(
        r"C:\Users\USER\Downloads\Wallpe_2025_combined_vi_stats_filtered_May15_2026.xlsx",
        sheet_name="python")

    # STEP 2: choose the target column (what to predict) — CHANGE THIS to try others
    target = "SEV_Mean"        # try: "NEW_SC_Mean", "TarSpotBin_Mean", etc.

    # STEP 3: choose which columns to EXCLUDE from the inputs
    #   (other disease columns = leakage, must be dropped)
    leakage = ml.suggest_leakage_columns(df.columns, target)   # auto-detects them
    extra_drop = leakage + ["Fungi", "DAP"]    # also drop these (or leave them in)

    # STEP 4: train both algorithms across all variants, cross-validated
    results = ml.train_all_variants(
        df,
        algorithms=["XGBoost", "Random Forest"],   # choose which models
        target=target,
        extra_drop=extra_drop,
        cv=True)                                    # 5-fold cross-validation

    # STEP 5: see the comparison
    print(ml.comparison_table(results).to_string(index=False))
    return results


# =========================================================================
# EXAMPLE 2 — Save the chosen model, then PREDICT on new input
# =========================================================================
def example_2_predict(results):
    print("\n--- EXAMPLE 2: Use a trained model to predict on new data ---")

    # STEP 1: pick a model from the results (here: the best by R2)
    table = ml.comparison_table(results)
    best_label = f"{table.iloc[0]['Algorithm']} · {table.iloc[0]['Variant']}"
    chosen = results[best_label]

    # STEP 2: wrap it as a "bundle" (model + its feature list + target)
    bundle = {"model": chosen["model"],
              "features": chosen["features"],
              "target": chosen["target"]}
    ml.save_active(bundle)              # optional: save to disk for later

    # STEP 3: load NEW data to predict on (disease unknown).
    #   It just needs the same feature columns — predict() aligns them automatically.
    new_data = pd.read_excel(
        r"C:\Users\USER\Downloads\Wallpe_2025_combined_vi_stats_filtered_May15_2026.xlsx",
        sheet_name="python")

    # STEP 4: predict — adds a PREDICTED_SEVERITY column
    out = ml.predict(bundle, new_data)
    print(out[["POINT", "PREDICTED_SEVERITY"]].head(8).to_string(index=False))


# =========================================================================
# EXAMPLE 3 — Try DIFFERENT feature sets (include / exclude columns)
# =========================================================================
def example_3_different_features():
    print("\n--- EXAMPLE 3: Same data, DIFFERENT feature sets ---")
    df = pd.read_excel(
        r"C:\Users\USER\Downloads\Wallpe_2025_combined_vi_stats_filtered_May15_2026.xlsx",
        sheet_name="python")
    target = "SEV_Mean"
    leak = ml.suggest_leakage_columns(df.columns, target)

    # Set A: WITH Fungi & DAP
    rA = ml.train_all_variants(df, ["Random Forest"], target, extra_drop=leak, cv=True)
    # Set B: WITHOUT Fungi & DAP (drone-only)
    rB = ml.train_all_variants(df, ["Random Forest"], target,
                               extra_drop=leak + ["Fungi", "DAP"], cv=True)

    print("WITH Fungi/DAP    -> Combined R2 =",
          ml.comparison_table(rA).query("Variant=='Combined (all data)'")["R2"].values)
    print("WITHOUT Fungi/DAP -> Combined R2 =",
          ml.comparison_table(rB).query("Variant=='Combined (all data)'")["R2"].values)


# =========================================================================
# EXAMPLE 4 — Run the Linear Mixed Model (explanation)
# =========================================================================
def example_4_lmm():
    print("\n--- EXAMPLE 4: Linear Mixed Model (which signals matter) ---")
    df = pd.read_excel(
        r"C:\Users\USER\Downloads\Wallpe_2025_combined_vi_stats_filtered_May15_2026.xlsx",
        sheet_name="python")

    # choose predictors (fixed effects) and the target
    predictors = ml.LMM_FIXED + ["Fungi"]      # clean index means + Fungi
    table, summary, info = ml.fit_lmm(df, fixed=predictors, target="SEV_Mean")

    print(f"Fitted on {info['rows']} rows / {info['groups']} grids")
    print(table.to_string(index=False))


# =========================================================================
if __name__ == "__main__":
    res = example_1_train()
    example_2_predict(res)
    example_3_different_features()
    example_4_lmm()
    print("\nDone. Edit the target / file / extra_drop in each example to try your own inputs.")
