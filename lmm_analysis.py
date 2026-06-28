"""
==========================================================================
  LINEAR MIXED MODEL (LMM) — Corn Disease Severity
==========================================================================
Purpose: EXPLAIN which vegetation indices significantly affect disease,
while correctly handling repeated measurements of the same grid (POINT).

This is NOT for best prediction (XGBoost does that). It is for STATISTICS:
coefficients + p-values you can put in a report.

  Outcome (1):        SEVERITY
  Fixed effects (8):  index MEANs + CANOPY_COVER  (clean, non-redundant)
  Random effect (1):  POINT  (each grid gets its own offset)

Run:  python lmm_analysis.py
==========================================================================
"""
import pandas as pd
import statsmodels.formula.api as smf

FILE = r"C:\Users\USER\Downloads\combined_vi_stats_with_disease_PPAC-B3.xlsx"

# The 8 clean predictors (fixed effects)
FIXED = ["NDVI_MEAN", "NDRE_MEAN", "OSAVI_MEAN", "PSRI_MEAN",
         "RDVI_MEAN", "MCARI2_MEAN", "EXG_MEAN", "CANOPY_COVER"]
GROUP = "POINT"          # random effect (grouping variable)
OUTCOME = "SEVERITY"

# 1. load + clean
df = pd.read_excel(FILE).dropna(subset=[OUTCOME] + FIXED + [GROUP]).reset_index(drop=True)
print(f"Rows used: {len(df)} | Grids (random-effect groups): {df[GROUP].nunique()}")

# 2. build the formula:  SEVERITY ~ NDVI_MEAN + NDRE_MEAN + ...
formula = f"{OUTCOME} ~ " + " + ".join(FIXED)
print("Formula:", formula)
print("Random effect (groups):", GROUP)

# 3. fit the Linear Mixed Model
model = smf.mixedlm(formula, data=df, groups=df[GROUP])
result = model.fit()

# 4. full statistical summary
print("\n" + "=" * 70)
print(result.summary())

# 5. tidy coefficient + p-value table (the part you report)
print("\n" + "=" * 70)
print("SIGNIFICANT DISEASE DRIVERS (sorted by p-value):")
coef = result.params
pval = result.pvalues
tbl = (pd.DataFrame({"Coefficient": coef, "p_value": pval})
         .drop(index=[i for i in ["Intercept", "Group Var"] if i in coef.index],
               errors="ignore")
         .sort_values("p_value"))
tbl["Significant?"] = tbl["p_value"].apply(
    lambda p: "*** yes (p<0.001)" if p < 0.001 else
              ("** yes (p<0.01)" if p < 0.01 else
               ("* yes (p<0.05)" if p < 0.05 else "no")))
print(tbl.round(4).to_string())

# 6. save the table
tbl.round(5).to_csv("lmm_results.csv")
print("\nSaved -> lmm_results.csv")
