"""
Generate a self-contained HTML training-results report.

Per dataset:
  - ALL 5 variants x XGBoost + Random Forest (full comparison)
  - 2024 PPAC  -> SINGLE-SPLIT (large data, already reliable)
  - 2025 Wallpe -> CROSS-VALIDATED (small data, honest); DRONE-ONLY prediction
  - Feature importance charts, LMM table+chart (Fungi kept), field map

Run:  python generate_report.py   ->  Training_Results_Report.html
"""
import io, base64
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
import statsmodels.formula.api as smf

PPAC = r"C:\Users\USER\Downloads\combined_vi_stats_with_disease_PPAC-B3.xlsx"
WALLPE = r"C:\Users\USER\Downloads\2025_Wallpe_New_model_FINAL_MERGED_TARSPOT_UAV.xlsx"
LMM_FIXED = ["NDVI_MEAN", "NDRE_MEAN", "OSAVI_MEAN", "PSRI_MEAN",
             "RDVI_MEAN", "MCARI2_MEAN", "EXG_MEAN", "CANOPY_COVER"]
VARIANTS = [("Combined (all data)", None, None),
            ("whole · soil=NO", "whole", "NO"),
            ("whole · soil=YES", "whole", "YES"),
            ("orthorectified · soil=NO", "orthorectified", "NO"),
            ("orthorectified · soil=YES", "orthorectified", "YES")]


def features(df, target, drop):
    X = df.drop(columns=[c for c in drop if c in df.columns]).copy()
    for c in X.columns:
        if X[c].dtype == object:
            X[c] = X[c].astype("category").cat.codes
    return X.apply(pd.to_numeric, errors="coerce").fillna(0)


def make(algo):
    if algo == "XGBoost":
        return XGBRegressor(n_estimators=600, learning_rate=0.03, max_depth=5, subsample=0.8,
                            colsample_bytree=0.8, min_child_weight=3, random_state=42, n_jobs=-1)
    return RandomForestRegressor(n_estimators=300, min_samples_leaf=2, max_features="sqrt",
                                 random_state=42, n_jobs=-1)


def variant_scores(df, target, drop, cv):
    """All variants x both algorithms. cv=True -> 5-fold CV; else single 80/20 grid split."""
    d = df[pd.to_numeric(df[target], errors="coerce").notna()].reset_index(drop=True)
    d[target] = pd.to_numeric(d[target], errors="coerce")
    rows = []
    for algo in ["XGBoost", "Random Forest"]:
        for name, method, soil in VARIANTS:
            sub = d
            if method is not None and "METHOD" in d.columns:
                sub = sub[sub["METHOD"] == method]
            if soil is not None and "SOIL" in d.columns:
                sub = sub[sub["SOIL"] == soil]
            sub = sub.reset_index(drop=True)
            if len(sub) < 20:
                continue
            X = features(sub, target, drop); y = sub[target]; g = sub["POINT"]
            if cv:
                k = min(5, g.nunique())
                gkf = GroupKFold(n_splits=k); r2s, rms, mae = [], [], []
                for tr, te in gkf.split(X, y, g):
                    m = make(algo); m.fit(X.iloc[tr], y.iloc[tr]); p = m.predict(X.iloc[te])
                    r2s.append(r2_score(y.iloc[te], p)); rms.append(np.sqrt(mean_squared_error(y.iloc[te], p)))
                    mae.append(mean_absolute_error(y.iloc[te], p))
                rows.append({"algo": algo, "variant": name, "rows": len(sub),
                             "R2": np.mean(r2s), "RMSE": np.mean(rms), "MAE": np.mean(mae),
                             "folds": str([round(v, 2) for v in r2s])})
            else:
                gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
                tr, te = next(gss.split(X, y, g))
                m = make(algo); m.fit(X.iloc[tr], y.iloc[tr]); p = m.predict(X.iloc[te])
                rows.append({"algo": algo, "variant": name, "rows": len(sub),
                             "R2": r2_score(y.iloc[te], p),
                             "RMSE": np.sqrt(mean_squared_error(y.iloc[te], p)),
                             "MAE": mean_absolute_error(y.iloc[te], p), "folds": "single split"})
    # XGBoost block first, then Random Forest; within each, best R2 first
    algo_order = {"XGBoost": 0, "Random Forest": 1}
    return sorted(rows, key=lambda r: (algo_order[r["algo"]], -r["R2"]))


def importance_chart_b64(df, target, drop, algo, color):
    d = df[pd.to_numeric(df[target], errors="coerce").notna()].reset_index(drop=True)
    d[target] = pd.to_numeric(d[target], errors="coerce")
    X = features(d, target, drop); y = d[target]
    m = make(algo); m.fit(X, y)
    imp = pd.Series(m.feature_importances_, index=X.columns).sort_values(ascending=False).head(12)[::-1]
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.barh(imp.index, imp.values, color=color)
    ax.set_title(f"{algo} — Top Features", fontsize=11)
    ax.set_xlabel("Importance", fontsize=9); ax.tick_params(labelsize=8)
    fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def lmm_chart_b64(rows):
    rows = sorted(rows, key=lambda r: r[1])
    names = [r[0] for r in rows]; coefs = [r[1] for r in rows]
    colors = ["#27ae60" if c < 0 else "#c0392b" for c in coefs]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.barh(names, coefs, color=colors); ax.axvline(0, color="#444", linewidth=0.8)
    ax.set_title("LMM coefficients (red = raises, green = lowers)", fontsize=10)
    ax.set_xlabel("Coefficient", fontsize=9); ax.tick_params(labelsize=8)
    fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def field_map_b64(df, target, title):
    d = df.copy(); d[target] = pd.to_numeric(d[target], errors="coerce")
    g = (d.dropna(subset=[target, "LATITUDE", "LONGITUDE"])
           .groupby("POINT").agg(LAT=("LATITUDE", "mean"), LON=("LONGITUDE", "mean"),
                                 SEV=(target, "mean")).reset_index())
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    sc = ax.scatter(g["LON"], g["LAT"], c=g["SEV"], cmap="RdYlGn_r", s=70, edgecolor="#333", linewidth=0.3)
    fig.colorbar(sc, ax=ax, label="mean severity")
    ax.set_title(title, fontsize=10); ax.set_xlabel("Longitude", fontsize=9); ax.set_ylabel("Latitude", fontsize=9)
    ax.tick_params(labelsize=7); fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def lmm_table(df, target, extra=None):
    d = df.copy(); d[target] = pd.to_numeric(d[target], errors="coerce")
    fixed = [c for c in LMM_FIXED if c in d.columns] + (extra or [])
    for c in fixed:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["POINT"] = d["POINT"].astype(str)
    d = d.dropna(subset=[target, "POINT"] + fixed).reset_index(drop=True)
    res = smf.mixedlm(f"{target} ~ " + " + ".join(fixed), data=d, groups=d["POINT"]).fit()
    rows = []
    for f in fixed:
        c, p = res.params[f], res.pvalues[f]
        sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        rows.append((f, round(c, 3), f"{p:.4f}", sig, "raises" if c > 0 else "lowers"))
    return sorted(rows, key=lambda r: float(r[2])), len(d), d["POINT"].nunique()


# ============================ compute ============================
print("Computing 2024 PPAC (single-split, all variants)...")
ppac = pd.read_excel(PPAC)
DROP24 = ["SEVERITY", "DATE", "POINT", "LATITUDE", "LONGITUDE"]
v24 = variant_scores(ppac, "SEVERITY", DROP24, cv=False)
img24_xgb = importance_chart_b64(ppac, "SEVERITY", DROP24, "XGBoost", "#1f5c2e")
img24_rf = importance_chart_b64(ppac, "SEVERITY", DROP24, "Random Forest", "#3c7a4a")
lmm24, n24, g24 = lmm_table(ppac, "SEVERITY")
lmmimg24 = lmm_chart_b64(lmm24)
map24 = field_map_b64(ppac, "SEVERITY", "2024 PPAC - mean tar spot severity by grid")

print("Computing 2025 Wallpe (cross-validated, WITH Fungi/DAP, target NEW_SC_Mean)...")
wal = pd.read_excel(WALLPE)                       # new merged file, single sheet
T25 = "NEW_SC_Mean"                               # target = stroma count
DROP25 = [T25, "DATE", "POINT", "LATITUDE", "LONGITUDE", "EvalPoint",
          "TarSpotBin_Mean", "NEW_SEV_Mean", "NEW_AP_Mean",   # other disease cols = leakage
          "DAP"]                                              # DAP dropped (crop age excluded)
#         Fungi is KEPT as a feature; DAP is dropped.
v25 = variant_scores(wal, T25, DROP25, cv=True)
img25_xgb = importance_chart_b64(wal, T25, DROP25, "XGBoost", "#1f5c2e")
img25_rf = importance_chart_b64(wal, T25, DROP25, "Random Forest", "#3c7a4a")
lmm25, n25, g25 = lmm_table(wal, T25, extra=["Fungi", "DAP"])   # LMM keeps BOTH (explanation)
lmmimg25 = lmm_chart_b64(lmm25)
map25 = field_map_b64(wal, T25, "2025 Wallpe - mean stroma count by grid")


# ============================ HTML ============================
def pred_rows(rows):
    out = ""
    best_idx = max(range(len(rows)), key=lambda i: rows[i]["R2"]) if rows else -1
    for i, r in enumerate(rows):
        cls = " class='best'" if i == best_idx else ""
        out += (f"<tr{cls}><td>{r['algo']}</td><td>{r['variant']}</td><td class='num'>{r['rows']:,}</td>"
                f"<td class='num'>{r['R2']:.3f}</td><td class='num'>{r['RMSE']:.4f}</td>"
                f"<td class='num'>{r['MAE']:.4f}</td><td class='folds'>{r['folds']}</td></tr>")
    return out


def lmm_rows(rows):
    out = ""
    for f, c, p, sig, d in rows:
        cls = "sig" if sig != "ns" else "nsig"
        dircls = "up" if d == "raises" else "down"
        out += (f"<tr class='{cls}'><td>{f}</td><td class='num'>{c}</td><td class='num'>{p}</td>"
                f"<td class='{dircls}'>{d} disease</td><td class='star'>{sig}</td></tr>")
    return out


html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Corn Disease AI - Training Results</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f7f4;color:#222}}
.wrap{{max-width:1040px;margin:0 auto;padding:30px}}
h1{{color:#1f5c2e;border-bottom:3px solid #1f5c2e;padding-bottom:10px}}
h2{{color:#1f5c2e;margin-top:36px;background:#e7f0e7;padding:10px 14px;border-radius:6px}}
h3{{color:#3c7a4a;margin-top:24px}}
table{{border-collapse:collapse;width:100%;margin:12px 0;background:#fff;box-shadow:0 1px 3px #0001}}
th{{background:#1f5c2e;color:#fff;padding:9px 12px;text-align:left;font-size:14px}}
td{{padding:8px 12px;border-bottom:1px solid #eee;font-size:14px}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.folds{{color:#888;font-size:12px}}
tr.sig{{background:#f3faf3}} .star{{font-weight:bold;color:#1f5c2e;text-align:center}}
.up{{color:#c0392b}} .down{{color:#27ae60}} .nsig td{{color:#999}}
.best{{background:#d5f0d5;font-weight:bold}}
.note{{background:#fff8e1;border-left:4px solid #f0c000;padding:10px 14px;margin:14px 0;font-size:14px}}
.explain{{background:#eef4fb;border-left:4px solid #2e6ca4;padding:12px 16px;margin:16px 0;font-size:14px;border-radius:4px}}
.explain ul{{margin:8px 0 0 0;padding-left:20px}} .explain li{{margin:6px 0}}
.foot{{color:#888;font-size:12px;margin-top:30px;border-top:1px solid #ddd;padding-top:12px}}
.charts{{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0}}
.charts figure{{margin:0;flex:1;min-width:320px;background:#fff;padding:8px;border-radius:6px;box-shadow:0 1px 3px #0001}}
.charts img{{width:100%;height:auto;display:block}}
</style></head><body><div class="wrap">
<h1>&#127809; Corn Disease AI &mdash; Training Results Report</h1>
<p>Models: <b>XGBoost</b> &amp; <b>Random Forest</b> (prediction) and <b>Linear Mixed Model</b> (explanation).
Each table shows <b>all 5 data variants</b> for both algorithms. Validation: <b>2024 = single-split</b>
(large data, already reliable); <b>2025 = 5-fold cross-validation</b> (small data, honest).</p>

<div class="explain">
<b>How we measured accuracy (single-split vs cross-validation):</b>
<ul>
<li><b>Single split</b> &mdash; train the model on 80% of the grids and test on the other 20% <i>once</i>.
Fast, and reliable when there is <b>lots of data</b> (like 2024, 135 grids).</li>
<li><b>5-fold cross-validation</b> &mdash; split the grids into 5 groups, test 5 times (each time holding out a
different 20%), then <i>average</i> the 5 scores. This removes the luck of any single split, so it is essential for
<b>small data</b> (like 2025, only 24 grids, where one lucky split can look falsely high).</li>
<li><b>The rule:</b> big data &rarr; single split is enough; small data &rarr; cross-validation gives the honest number.
Grids never appear in both train and test, so there is no cheating (no data leakage).</li>
</ul>
</div>

<h2>Dataset 1 &mdash; 2024 PPAC (field B3)</h2>
<p>{g24} grids &middot; target = SEVERITY (0&ndash;6 scale) &middot; single-split validation</p>
<h3>Prediction models &mdash; all variants (single-split)</h3>
<table><tr><th>Algorithm</th><th>Variant</th><th>Rows</th><th>R&sup2;</th><th>RMSE</th><th>MAE</th><th>Validation</th></tr>{pred_rows(v24)}</table>
<div class="note">2024 disease developed strongly (up to 6.0); single-split is reliable here (best ~0.96). Best row highlighted.</div>
<h3>Feature importance</h3>
<div class="charts"><figure><img src="{img24_xgb}"></figure><figure><img src="{img24_rf}"></figure></div>
<h3>Linear Mixed Model &mdash; significant disease drivers</h3>
<table><tr><th>Index</th><th>Coefficient</th><th>p-value</th><th>Effect</th><th>Sig.</th></tr>{lmm_rows(lmm24)}</table>
<div class="charts"><figure><img src="{lmmimg24}"></figure><figure><img src="{map24}"></figure></div>

<h2>Dataset 2 &mdash; 2025 Wallpe (Tar Spot &mdash; target: Stroma Count)</h2>
<p>{g25} grids &middot; target = <b>NEW_SC_Mean</b> (stroma count, 0&ndash;1,715 scale) &middot;
<b>with Fungi</b> as a feature (<b>DAP dropped</b>) &middot; 5-fold cross-validation</p>
<h3>Prediction models &mdash; all variants (cross-validated)</h3>
<table><tr><th>Algorithm</th><th>Variant</th><th>Rows</th><th>R&sup2;</th><th>RMSE</th><th>MAE</th><th>Fold R&sup2;</th></tr>{pred_rows(v25)}</table>
<div class="note">Target is <b>stroma count</b> (number of black tar-spot spots), so RMSE/MAE are large numbers
(on a 0&ndash;1,715 scale) &mdash; this is normal, not an error. 2025 is small ({g25} grids), so cross-validation
gives the honest score; the 96-row variants are noisier than the 576-row Combined. Random Forest is usually the
more stable choice on this small data.</div>
<h3>Feature importance (with Fungi, DAP dropped)</h3>
<div class="charts"><figure><img src="{img25_xgb}"></figure><figure><img src="{img25_rf}"></figure></div>
<h3>Linear Mixed Model &mdash; significant disease drivers (Fungi &amp; DAP kept)</h3>
<table><tr><th>Factor</th><th>Coefficient</th><th>p-value</th><th>Effect</th><th>Sig.</th></tr>{lmm_rows(lmm25)}</table>
<div class="charts"><figure><img src="{lmmimg25}"></figure><figure><img src="{map25}"></figure></div>
<div class="note"><b>Note 1:</b> the prediction models drop DAP (crop age), but the <b>LMM keeps both Fungi and DAP</b> &mdash;
the LMM is for <i>explanation</i> (not prediction), so including all meaningful factors gives a complete picture.<br>
<b>Note 2:</b> NEW_SEV (severity), NEW_AP (pustules) and NEW_SC (stroma count) are ~0.99 correlated &mdash;
they measure the same disease amount in different units. NEW_SC_Mean was chosen as the reporting unit here.</div>

<h3>How to read the numbers</h3>
<table><tr><th>Metric</th><th>Meaning</th><th>Goal</th></tr>
<tr><td>R&sup2;</td><td>% of disease pattern captured</td><td>Higher (max 1.0)</td></tr>
<tr><td>RMSE</td><td>Average error (punishes big misses)</td><td>Lower</td></tr>
<tr><td>MAE</td><td>Typical error</td><td>Lower</td></tr>
<tr><td>p-value</td><td>Chance the effect is just luck</td><td>&lt; 0.05 = real (*** strongest)</td></tr></table>
<p class="foot">Methodology: honest grid-grouped validation (2024 single-split, 2025 5-fold CV); no data leakage;
LMM uses real measured severity with a random effect on grid (POINT). Generated by generate_report.py.</p>
</div></body></html>"""

with open("Training_Results_Report.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Saved -> Training_Results_Report.html")
