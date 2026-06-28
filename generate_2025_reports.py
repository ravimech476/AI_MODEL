"""
Generate TWO 2025-only HTML reports for NEW_SC_Mean (stroma count):
  Report A: WITH Fungi      -> Training_Report_2025_WITH_Fungi.html
  Report B: WITHOUT Fungi   -> Training_Report_2025_WITHOUT_Fungi.html

Both reports:
  - exclude SOIL and DAP as inputs (everywhere)
  - target = NEW_SC_Mean, 5-fold cross-validation, all variants x XGBoost + RF
  - feature importance charts, LMM table + chart, field map
The only difference is Fungi (kept in A, dropped in B), in BOTH prediction and LMM.

Run:  python generate_2025_reports.py
"""
import io, base64
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
import statsmodels.formula.api as smf

FILE = r"C:\Users\USER\Downloads\2025_Wallpe_New_model_FINAL_MERGED_TARSPOT_UAV.xlsx"
TARGET = "NEW_SC_Mean"
LMM_FIXED = ["NDVI_MEAN", "NDRE_MEAN", "OSAVI_MEAN", "PSRI_MEAN",
             "RDVI_MEAN", "MCARI2_MEAN", "EXG_MEAN", "CANOPY_COVER"]
VARIANTS = [("Combined (all data)", None, None),
            ("whole · soil=NO", "whole", "NO"),
            ("whole · soil=YES", "whole", "YES"),
            ("orthorectified · soil=NO", "orthorectified", "NO"),
            ("orthorectified · soil=YES", "orthorectified", "YES")]
# columns excluded from prediction features (SOIL & DAP always; Fungi conditionally)
BASE_EXCLUDE = [TARGET, "DATE", "POINT", "LATITUDE", "LONGITUDE", "EvalPoint",
                "TarSpotBin_Mean", "NEW_SEV_Mean", "NEW_AP_Mean", "SOIL", "DAP"]


def features(df, drop):
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


def variant_scores(df, drop):
    d = df[pd.to_numeric(df[TARGET], errors="coerce").notna()].reset_index(drop=True)
    d[TARGET] = pd.to_numeric(d[TARGET], errors="coerce")
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
            X = features(sub, drop); y = sub[TARGET]; g = sub["POINT"]
            k = min(5, g.nunique()); gkf = GroupKFold(n_splits=k); r2s, rms, mae = [], [], []
            for tr, te in gkf.split(X, y, g):
                m = make(algo); m.fit(X.iloc[tr], y.iloc[tr]); p = m.predict(X.iloc[te])
                r2s.append(r2_score(y.iloc[te], p)); rms.append(np.sqrt(mean_squared_error(y.iloc[te], p)))
                mae.append(mean_absolute_error(y.iloc[te], p))
            rows.append({"algo": algo, "variant": name, "rows": len(sub),
                         "R2": np.mean(r2s), "RMSE": np.mean(rms), "MAE": np.mean(mae),
                         "folds": str([round(v, 2) for v in r2s])})
    order = {"XGBoost": 0, "Random Forest": 1}
    return sorted(rows, key=lambda r: (order[r["algo"]], -r["R2"]))


def importance_chart(df, drop, algo, color):
    d = df[pd.to_numeric(df[TARGET], errors="coerce").notna()].reset_index(drop=True)
    d[TARGET] = pd.to_numeric(d[TARGET], errors="coerce")
    X = features(d, drop); y = d[TARGET]; m = make(algo); m.fit(X, y)
    imp = pd.Series(m.feature_importances_, index=X.columns).sort_values(ascending=False).head(12)[::-1]
    fig, ax = plt.subplots(figsize=(6.2, 4.2)); ax.barh(imp.index, imp.values, color=color)
    ax.set_title(f"{algo} — Top Features", fontsize=11); ax.set_xlabel("Importance", fontsize=9); ax.tick_params(labelsize=8)
    fig.tight_layout(); buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def lmm_run(df, with_fungi):
    fixed = [c for c in LMM_FIXED if c in df.columns] + (["Fungi"] if with_fungi and "Fungi" in df.columns else [])
    d = df.copy(); d[TARGET] = pd.to_numeric(d[TARGET], errors="coerce")
    for c in fixed:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["POINT"] = d["POINT"].astype(str)
    d = d.dropna(subset=[TARGET, "POINT"] + fixed).reset_index(drop=True)
    res = smf.mixedlm(f"{TARGET} ~ " + " + ".join(fixed), data=d, groups=d["POINT"]).fit()
    rows = []
    for f in fixed:
        c, p = res.params[f], res.pvalues[f]
        sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        rows.append((f, round(c, 3), f"{p:.4f}", sig, "raises" if c > 0 else "lowers"))
    return sorted(rows, key=lambda r: float(r[2])), len(d), d["POINT"].nunique()


def lmm_chart(rows):
    rows = sorted(rows, key=lambda r: r[1]); names = [r[0] for r in rows]; coefs = [r[1] for r in rows]
    colors = ["#27ae60" if c < 0 else "#c0392b" for c in coefs]
    fig, ax = plt.subplots(figsize=(6.4, 4.2)); ax.barh(names, coefs, color=colors); ax.axvline(0, color="#444", linewidth=0.8)
    ax.set_title("LMM coefficients (red = raises, green = lowers)", fontsize=10)
    ax.set_xlabel("Coefficient", fontsize=9); ax.tick_params(labelsize=8); fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def field_map(df):
    d = df.copy(); d[TARGET] = pd.to_numeric(d[TARGET], errors="coerce")
    g = (d.dropna(subset=[TARGET, "LATITUDE", "LONGITUDE"])
           .groupby("POINT").agg(LAT=("LATITUDE", "mean"), LON=("LONGITUDE", "mean"), SEV=(TARGET, "mean")).reset_index())
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    sc = ax.scatter(g["LON"], g["LAT"], c=g["SEV"], cmap="RdYlGn_r", s=70, edgecolor="#333", linewidth=0.3)
    fig.colorbar(sc, ax=ax, label="mean stroma count")
    ax.set_title("2025 Wallpe - mean stroma count by grid", fontsize=10)
    ax.set_xlabel("Longitude", fontsize=9); ax.set_ylabel("Latitude", fontsize=9); ax.tick_params(labelsize=7); fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def pred_rows_html(rows):
    best = max(range(len(rows)), key=lambda i: rows[i]["R2"]) if rows else -1
    out = ""
    for i, r in enumerate(rows):
        cls = " class='best'" if i == best else ""
        out += (f"<tr{cls}><td>{r['algo']}</td><td>{r['variant']}</td><td class='num'>{r['rows']:,}</td>"
                f"<td class='num'>{r['R2']:.3f}</td><td class='num'>{r['RMSE']:.3f}</td>"
                f"<td class='num'>{r['MAE']:.3f}</td><td class='folds'>{r['folds']}</td></tr>")
    return out


def lmm_rows_html(rows):
    out = ""
    for f, c, p, sig, d in rows:
        cls = "sig" if sig != "ns" else "nsig"; dc = "up" if d == "raises" else "down"
        out += (f"<tr class='{cls}'><td>{f}</td><td class='num'>{c}</td><td class='num'>{p}</td>"
                f"<td class='{dc}'>{d} disease</td><td class='star'>{sig}</td></tr>")
    return out


def build(df, with_fungi, outfile):
    drop = list(BASE_EXCLUDE) + ([] if with_fungi else ["Fungi"])
    fungi_txt = "WITH Fungi" if with_fungi else "WITHOUT Fungi"
    feat_note = "with Fungi" if with_fungi else "without Fungi (pure drone signals)"
    v = variant_scores(df, drop)
    ixgb = importance_chart(df, drop, "XGBoost", "#1f5c2e")
    irf = importance_chart(df, drop, "Random Forest", "#3c7a4a")
    lrows, lr_rows, lr_grids = lmm_run(df, with_fungi)
    lchart = lmm_chart(lrows); fmap = field_map(df)
    grids = df["POINT"].nunique()
    nfeat = features(df[df[TARGET].notna()] if df[TARGET].dtype != object else df, drop).shape[1]

    # build the excluded-columns block (grouped by reason)
    disease = [c for c in ["TarSpotBin_Mean", "NEW_SEV_Mean", "NEW_AP_Mean"] if c in df.columns]
    ids = [c for c in ["DATE", "POINT", "LATITUDE", "LONGITUDE", "EvalPoint"] if c in df.columns]
    choice = ["SOIL", "DAP"] + ([] if with_fungi else ["Fungi"])
    choice = [c for c in choice if c in df.columns]
    excl_html = (
        "<div class='excl'><b>Excluded columns (NOT used as model inputs):</b><ul>"
        f"<li><b>Target (the answer):</b> {TARGET}</li>"
        f"<li><b>Other disease measures (leakage):</b> {', '.join(disease)}</li>"
        f"<li><b>ID columns:</b> {', '.join(ids)}</li>"
        f"<li><b>Excluded by choice:</b> {', '.join(choice)}</li>"
        "</ul></div>"
        "<div class='explain'><b>Note &mdash; excluding SOIL as an input does NOT affect the variants.</b> "
        "The variants (whole&middot;soil=YES, orthorectified&middot;soil=NO, &hellip;) are data <b>FILTERS</b> "
        "that split the rows by soil &mdash; they are separate from which <i>columns</i> the model uses. "
        "So removing SOIL from the inputs leaves the variant comparison unchanged (and inside each soil variant "
        "SOIL is constant anyway, so it was already ignored).</div>")

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>2025 Report - {fungi_txt}</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f7f4;color:#222}}
.wrap{{max-width:1000px;margin:0 auto;padding:30px}}
h1{{color:#1f5c2e;border-bottom:3px solid #1f5c2e;padding-bottom:10px}}
h2{{color:#1f5c2e;margin-top:30px;background:#e7f0e7;padding:10px 14px;border-radius:6px}}
h3{{color:#3c7a4a;margin-top:22px}}
table{{border-collapse:collapse;width:100%;margin:12px 0;background:#fff;box-shadow:0 1px 3px #0001}}
th{{background:#1f5c2e;color:#fff;padding:9px 12px;text-align:left;font-size:14px}}
td{{padding:8px 12px;border-bottom:1px solid #eee;font-size:14px}}
.num{{text-align:right;font-variant-numeric:tabular-nums}} .folds{{color:#888;font-size:12px}}
tr.sig{{background:#f3faf3}} .star{{font-weight:bold;color:#1f5c2e;text-align:center}}
.up{{color:#c0392b}} .down{{color:#27ae60}} .nsig td{{color:#999}} .best{{background:#d5f0d5;font-weight:bold}}
.note{{background:#fff8e1;border-left:4px solid #f0c000;padding:10px 14px;margin:14px 0;font-size:14px}}
.explain{{background:#eef4fb;border-left:4px solid #2e6ca4;padding:12px 16px;margin:16px 0;font-size:14px;border-radius:4px}}
.explain ul{{margin:8px 0 0 0;padding-left:20px}} .explain li{{margin:5px 0}}
.excl{{background:#fdeeee;border-left:4px solid #c0392b;padding:12px 16px;margin:16px 0;font-size:14px;border-radius:4px}}
.excl ul{{margin:8px 0 0 0;padding-left:20px}} .excl li{{margin:5px 0}}
.charts{{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0}}
.charts figure{{margin:0;flex:1;min-width:320px;background:#fff;padding:8px;border-radius:6px;box-shadow:0 1px 3px #0001}}
.charts img{{width:100%;height:auto;display:block}}
.foot{{color:#888;font-size:12px;margin-top:26px;border-top:1px solid #ddd;padding-top:12px}}
</style></head><body><div class="wrap">
<h1>&#127809; 2025 Wallpe Tar Spot &mdash; Training Report ({fungi_txt})</h1>
<p>Target = <b>NEW_SC_Mean</b> (stroma count). <b>SOIL and DAP excluded</b> from inputs.
This report is <b>{fungi_txt}</b> as a feature. Validation: <b>5-fold cross-validation</b> (small data).</p>
<div class="explain"><b>How accuracy is measured:</b> 5-fold cross-validation splits the {grids} grids into 5 groups,
tests 5 times (each time holding out a different 20%), and averages &mdash; so a single lucky split can't mislead.
Grids never appear in both train and test (no data leakage). RMSE/MAE are large because the target is a
<b>count</b> (0&ndash;1,715), which is normal.</div>

<h2>Prediction models &mdash; all variants ({feat_note})</h2>
<p>{grids} grids &middot; {nfeat} features &middot; SOIL &amp; DAP excluded{'' if with_fungi else ' &middot; Fungi excluded'}</p>
{excl_html}
<table><tr><th>Algorithm</th><th>Variant</th><th>Rows</th><th>R&sup2;</th><th>RMSE</th><th>MAE</th><th>Fold R&sup2;</th></tr>{pred_rows_html(v)}</table>
<div class="note">Random Forest is usually the more stable choice on this small data. The 96-row variants are noisier
than the 576-row Combined.</div>

<h3>Feature importance ({feat_note})</h3>
<div class="charts"><figure><img src="{ixgb}"></figure><figure><img src="{irf}"></figure></div>

<h2>Linear Mixed Model &mdash; significant disease drivers ({fungi_txt})</h2>
<p>Predictors: clean index means{' + Fungi' if with_fungi else ''} &middot; no DAP &middot; no SOIL &middot;
random effect = POINT &middot; {lr_rows:,} rows / {lr_grids} grids</p>
<table><tr><th>Factor</th><th>Coefficient</th><th>p-value</th><th>Effect</th><th>Sig.</th></tr>{lmm_rows_html(lrows)}</table>
<div class="charts"><figure><img src="{lchart}"></figure><figure><img src="{fmap}"></figure></div>

<h3>How to read the numbers</h3>
<table><tr><th>Metric</th><th>Meaning</th><th>Goal</th></tr>
<tr><td>R&sup2;</td><td>% of disease pattern captured</td><td>Higher (max 1.0)</td></tr>
<tr><td>RMSE</td><td>Average error (large here = count scale)</td><td>Lower</td></tr>
<tr><td>MAE</td><td>Typical error</td><td>Lower</td></tr>
<tr><td>p-value</td><td>Chance the effect is just luck</td><td>&lt; 0.05 = real (*** strongest)</td></tr></table>
<p class="foot">Target NEW_SC_Mean &middot; SOIL &amp; DAP excluded &middot; {fungi_txt} &middot;
5-fold grid cross-validation &middot; LMM uses real measured stroma count with a random effect on grid.
Generated by generate_2025_reports.py.</p>
</div></body></html>"""
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(html)
    best = max(v, key=lambda r: r["R2"])
    print(f"Saved {outfile}  | best: {best['algo']} {best['variant']} R2={best['R2']:.3f}")


df = pd.read_excel(FILE)
print("Building report A (WITH Fungi)...")
build(df, True, "Training_Report_2025_WITH_Fungi.html")
print("Building report B (WITHOUT Fungi)...")
build(df, False, "Training_Report_2025_WITHOUT_Fungi.html")
print("Done.")
