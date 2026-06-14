const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, TableOfContents
} = require("docx");

// ---------- helpers ----------
const CW = 9360; // content width US Letter, 1" margins
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const HEADER_FILL = "2E5A1C";   // corn green
const ALT_FILL = "EEF4E8";

function P(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 120, before: opts.before ?? 0 },
    alignment: opts.align,
    children: [new TextRun({ text, bold: opts.bold, italics: opts.italics,
      size: opts.size ?? 22, color: opts.color, font: opts.mono ? "Consolas" : undefined })],
  });
}
function H1(t) { return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] }); }
function H2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] }); }
function bullet(text, bold) {
  return new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 80 },
    children: [ typeof text === "string"
      ? new TextRun({ text, size: 22 })
      : text ] });
}
function kv(label, val) {
  return new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 80 },
    children: [ new TextRun({ text: label + ": ", bold: true, size: 22 }),
                new TextRun({ text: val, size: 22 }) ] });
}
function code(lines) {
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    rows: [ new TableRow({ children: [ new TableCell({
      borders, width: { size: CW, type: WidthType.DXA },
      shading: { fill: "1E1E1E", type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 140, right: 140 },
      children: lines.map(l => new Paragraph({ spacing: { after: 20 },
        children: [new TextRun({ text: l || " ", font: "Consolas", size: 18, color: "D4D4D4" })] })),
    }) ] }) ],
  });
}
function tbl(headers, rows, widths) {
  const headRow = new TableRow({ tableHeader: true, children: headers.map((h, i) =>
    new TableCell({ borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: HEADER_FILL, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 20 })] })] })) });
  const bodyRows = rows.map((r, ri) => new TableRow({ children: r.map((c, i) =>
    new TableCell({ borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: ri % 2 ? "FFFFFF" : ALT_FILL, type: ShadingType.CLEAR },
      margins: { top: 70, bottom: 70, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: String(c), size: 20 })] })] })) }));
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: widths, rows: [headRow, ...bodyRows] });
}
const SP = () => new Paragraph({ children: [], spacing: { after: 80 } });

// ---------- document ----------
const children = [];

// Title page
children.push(
  new Paragraph({ spacing: { before: 2200, after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Corn Disease Severity Prediction", bold: true, size: 52, color: "2E5A1C" })] }),
  new Paragraph({ spacing: { before: 120, after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Using UAV / Drone Data and XGBoost Machine Learning", size: 30, color: "555555" })] }),
  new Paragraph({ spacing: { before: 600, after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "US Corn Farming — AI Crop Health Monitoring", italics: true, size: 24 })] }),
  new Paragraph({ spacing: { before: 2600, after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Project Documentation & Beginner Guide", bold: true, size: 24 })] }),
  new Paragraph({ spacing: { before: 120 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Prepared: 13 June 2026", size: 20, color: "777777" })] }),
  new Paragraph({ children: [new PageBreak()] }),
);

// TOC
children.push(H1("Contents"),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }));

// 1. Overview
children.push(H1("1. Project Overview"));
children.push(P("This project uses Artificial Intelligence (AI) to predict corn disease severity from drone (UAV) imagery. A drone flies over a corn field, captures multispectral images, and software converts them into vegetation indices (numerical health signals). A Machine Learning model — XGBoost — then learns the link between these signals and measured disease, so it can predict disease on new fields automatically."));
children.push(P("UAV = Unmanned Aerial Vehicle (Drone). The goal: replace slow manual field scouting with fast, map-based AI predictions.", { italics: true }));
children.push(H2("The processing pipeline"));
children.push(code([
  "Drone Images  ->  Orthorectification  ->  Orthomosaic",
  "      ->  Vegetation Index Calculation  ->  Excel Dataset",
  "      ->  XGBoost AI Model  ->  Severity Prediction  ->  Dashboard",
]));
children.push(SP());

// 2. Dataset
children.push(H1("2. The Dataset"));
children.push(P("File: combined_vi_stats_with_disease_PPAC-B3.xlsx — 1 sheet, 4,320 rows x 56 columns."));
children.push(H2("What one row means"));
children.push(P("Each grid (POINT) is a 12 m field cell containing 6 corn plants. SEVERITY is the measured disease level of those 6 plants. The data covers 135 grids across 8 flight dates."));
children.push(H2("Column groups"));
children.push(tbl(
  ["Group", "Columns", "Role"],
  [
    ["Identity / Metadata", "DATE, METHOD, SOIL, POINT, LATITUDE, LONGITUDE", "Not predictors"],
    ["Canopy", "CANOPY_COVER", "Feature (input)"],
    ["Vegetation Indices", "NDVI, NDRE, EXG, PSRI, RDVI, MCARI2, OSAVI (each MEAN/STD/MIN/MAX)", "Features (input)"],
    ["Spectral Bands", "RED, GREEN, BLUE, REDEDGE, NIR (each MEAN/STD/MIN/MAX)", "Features (input)"],
    ["Target", "SEVERITY", "What we predict"],
  ],
  [2100, 4760, 2500]));
children.push(SP());
children.push(H2("Important data facts"));
children.push(kv("Problem type", "Regression — SEVERITY is a continuous number (0.0 to 6.02), not categories"));
children.push(kv("Duplication", "Each grid+date is stored 4 times: {whole, orthorectified} x {soil NO, soil YES}"));
children.push(kv("Real observations", "135 grids x 8 dates = 1,080 unique observations (x4 copies = 4,320 rows)"));
children.push(kv("Zero-inflated", "Many grids are perfectly healthy (SEVERITY = 0)"));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 3. Cleaning — the 4320 vs 3780 explanation
children.push(H1("3. Data Cleaning — Why 4,320 becomes 3,780"));
children.push(P("The raw file has 4,320 rows, but we cannot train on all of them. Training needs both an input AND a known answer. 540 rows have a BLANK severity, so they are removed."));
children.push(P("Investigation showed all 540 blank rows belong to ONE flight date (3 Aug 2024) — on that day the drone flew but ground disease was not measured. That whole date is dropped.", { italics: true }));
children.push(tbl(
  ["Stage", "Calculation", "Rows"],
  [
    ["Raw file", "135 grids x 8 dates x 4 copies", "4,320"],
    ["Dropped (blank severity)", "135 grids x 1 date x 4 copies", "540"],
    ["Used for training", "135 grids x 7 dates x 4 copies", "3,780"],
  ],
  [3000, 4360, 2000]));
children.push(SP());
children.push(P("Key point: 4,320 is the count BEFORE cleaning; 3,780 is what the model actually trains on.", { bold: true }));
children.push(SP());

// 4. Why drop columns
children.push(H1("4. Feature Selection — Why We Drop Columns"));
children.push(P("An input column should describe the CAUSE or SYMPTOM of disease (the plant's spectral colors), not an IDENTITY tag (who/where/when). Identity tags make the model memorize instead of learn — called data leakage."));
children.push(tbl(
  ["Column dropped", "Reason"],
  [
    ["SEVERITY", "It is the answer. The model must predict it, not see it — else it just copies it (fake 100%)."],
    ["DATE", "A calendar number, not a plant measurement. Disease comes from spectral colors, not the date."],
    ["POINT", "Just a grid ID. Using it makes the model memorize specific locations, failing on new fields."],
    ["LATITUDE / LONGITUDE", "GPS position = where, not health. Same memorization risk; model should work anywhere."],
  ],
  [2400, 6960]));
children.push(SP());
children.push(P("METHOD and SOIL are text (e.g. 'whole', 'YES'). The model only understands numbers, so they are encoded to 0/1.", { italics: true }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 5. Train/test split
children.push(H1("5. Train / Test Split — The Honest Exam"));
children.push(P("To test if the model truly learned (not memorized), we teach it on some grids and test it on different grids it has never seen — like giving a student practice questions, then testing on hidden ones."));
children.push(H2("The duplication trap"));
children.push(P("Because each grid has 4 identical-answer copies, a RANDOM split could put copy 1 of a grid in training and copy 3 in testing — the model would 'study' then be 'tested' on the same grid. That is cheating, and gave a falsely high score (R2 = 0.972)."));
children.push(H2("The fix: GroupShuffleSplit by grid (POINT)"));
children.push(P("We group by POINT so all 4 copies of any grid stay on the SAME side. Result: 108 grids to train, 27 unseen grids to test — an honest evaluation."));
children.push(code([
  "groups = df['POINT']                    # keep each grid together",
  "gss = GroupShuffleSplit(test_size=0.2, random_state=42)",
  "train_idx, test_idx = next(gss.split(X, y, groups))",
  "# 108 train grids  |  27 test grids (never seen)",
]));
children.push(SP());

// 6. The model
children.push(H1("6. The XGBoost Model"));
children.push(P("XGBoost = Extreme Gradient Boosting. It builds hundreds of small decision trees, where each new tree corrects the mistakes of the previous ones. Adding 600 such trees produces a highly accurate predictor."));
children.push(H2("Key settings (hyperparameters)"));
children.push(tbl(
  ["Setting", "Value", "Meaning"],
  [
    ["n_estimators", "600", "Number of trees (more = more learning)"],
    ["learning_rate", "0.03", "How big each correction is (small = careful)"],
    ["max_depth", "5", "Max questions per tree (limits complexity)"],
    ["subsample", "0.8", "Each tree sees 80% of rows (adds variety)"],
    ["colsample_bytree", "0.8", "Each tree sees 80% of columns"],
    ["random_state", "42", "Makes results reproducible"],
  ],
  [2600, 1400, 5360]));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 7. Results
children.push(H1("7. Results & How to Read Them"));
children.push(P("Honest evaluation on 27 unseen grids:"));
children.push(tbl(
  ["Metric", "Value", "Plain meaning", "Goal"],
  [
    ["R2 (R-squared)", "0.963", "Model captures 96% of the real disease pattern", "Higher (max 1.0)"],
    ["RMSE", "0.27", "Average error, big misses punished more", "Lower"],
    ["MAE", "0.10", "Typical guess is off by only 0.10 severity points", "Lower"],
  ],
  [2200, 1200, 4760, 1200]));
children.push(SP());
children.push(H2("What each metric means"));
children.push(bullet("MAE (Mean Absolute Error): the average size of a mistake. 0.10 is tiny on a 0-6 scale."));
children.push(bullet("RMSE (Root Mean Squared Error): like MAE but punishes large misses more. RMSE > MAE means a few hard grids miss by more."));
children.push(bullet("R2: percentage of the pattern explained. 1.0 = perfect, 0 = no better than guessing the average. 0.963 is excellent."));
children.push(SP());

// feature importance image
if (fs.existsSync("feature_importance.png")) {
  children.push(H2("Most important features"));
  children.push(P("These vegetation indices influence the prediction most. PSRI (a plant-stress index) and OSAVI/NDVI (greenness) ranking high confirms the model learned real biology."));
  children.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [ new ImageRun({
    type: "png", data: fs.readFileSync("feature_importance.png"),
    transformation: { width: 460, height: 400 },
    altText: { title: "Feature importance", description: "XGBoost feature importance chart", name: "FeatureImportance" } }) ] }));
}
children.push(new Paragraph({ children: [new PageBreak()] }));

// 8. Project files
children.push(H1("8. Project Files"));
children.push(tbl(
  ["File", "Purpose", "When to run"],
  [
    ["train_xgboost.py", "Teaches the model from labeled data", "Once (or on new data)"],
    ["xgb_severity_model.json", "The saved trained model (600 trees)", "Created by training"],
    ["predict.py", "Batch predictions: Excel in, Excel out", "Each new flight"],
    ["app.py", "Web dashboard: upload, map, charts, download", "Anytime"],
    ["requirements.txt", "List of required libraries", "When setting up"],
    ["run_dashboard.bat", "Double-click to launch the dashboard", "Anytime"],
    ["train_model.bat", "Double-click to retrain", "On new data"],
  ],
  [2900, 4560, 1900]));
children.push(SP());

// 9. How to run
children.push(H1("9. How to Run (with Virtual Environment)"));
children.push(P("A venv (virtual environment) keeps this project's libraries separate from the rest of the computer, avoiding version conflicts."));
children.push(H2("One-time setup"));
children.push(code([
  "cd D:\\AI_ANALYSIS",
  "python -m venv venv",
  ".\\venv\\Scripts\\Activate.ps1",
  "pip install -r requirements.txt",
]));
children.push(H2("Daily use"));
children.push(code([
  "cd D:\\AI_ANALYSIS",
  ".\\venv\\Scripts\\Activate.ps1     # you should see (venv)",
  "streamlit run app.py               # launch the dashboard",
  "# or just double-click run_dashboard.bat",
]));
children.push(P("Golden rule: always activate the venv (look for '(venv)' in the prompt) before running any project file.", { bold: true }));
children.push(SP());

// 10. Dashboard
children.push(H1("10. The Dashboard"));
children.push(P("Built with Streamlit, the dashboard lets anyone upload a drone Excel and instantly see AI predictions — no coding needed."));
children.push(bullet("KPI cards: total grids and counts of Healthy / Moderate / Severe."));
children.push(bullet("Field Map: each grid plotted by GPS, colored red-to-green by severity."));
children.push(bullet("Over Time: disease progression across the flight dates."));
children.push(bullet("Feature Importance: which indices drive the prediction."));
children.push(bullet("Data + Download: full predictions table and one-click Excel export."));
children.push(SP());

// 11. Workflow & next steps
children.push(H1("11. Real-World Workflow & Next Steps"));
children.push(code([
  "New drone flight -> vegetation-index Excel -> open dashboard",
  "   -> upload -> AI predicts every grid in <1 second",
  "   -> map shows RED zones = diseased corn -> scout/spray there",
  "   -> download report; compare across dates to track spread",
]));
children.push(H2("Recommended improvements"));
children.push(bullet("Recover the missing 3 Aug date's ground measurements to add an 8th training date."));
children.push(bullet("Add a classification view (Healthy / Moderate / Severe) with agronomist-set thresholds."));
children.push(bullet("Use 5-fold grid cross-validation for an even more reliable score."));
children.push(bullet("Add time-series forecasting to predict FUTURE disease from early flights."));
children.push(new Paragraph({ children: [new PageBreak()] }));

// Appendix A — Worked example of the metrics
children.push(H1("Appendix A — How the Metrics Work (Worked Example)"));
children.push(P("To make R2, RMSE and MAE concrete, here is a tiny example using just 5 grids. We know each grid's REAL severity and the model's PREDICTED severity. Every metric is built from the Error column (Real - Predicted)."));
children.push(tbl(
  ["Grid", "Real severity", "Predicted", "Error (Real - Predicted)"],
  [
    ["1", "2.0", "1.8", "+0.2"],
    ["2", "0.0", "0.3", "-0.3"],
    ["3", "4.0", "3.5", "+0.5"],
    ["4", "1.0", "1.2", "-0.2"],
    ["5", "3.0", "3.0", "0.0"],
  ],
  [1400, 2700, 2600, 2660]));
children.push(SP());

children.push(H2("MAE — Mean Absolute Error = 0.24"));
children.push(P("Rule: ignore +/- signs, then average the errors."));
children.push(code([
  "Absolute errors:  0.2, 0.3, 0.5, 0.2, 0.0",
  "Sum            :  0.2 + 0.3 + 0.5 + 0.2 + 0.0 = 1.2",
  "Divide by 5    :  1.2 / 5 = 0.24   -> MAE",
]));
children.push(P("Meaning: on average the model is off by 0.24 severity points (a simple average mistake).", { italics: true }));

children.push(H2("RMSE — Root Mean Squared Error = 0.29"));
children.push(P("Rule: square each error (punishes big misses), average, then take the square root."));
children.push(code([
  "Squared errors:  0.04, 0.09, 0.25, 0.04, 0.00   (0.5 -> 0.25 dominates)",
  "Sum           :  0.42",
  "Divide by 5   :  0.42 / 5 = 0.084   (this is MSE)",
  "Square root   :  sqrt(0.084) = 0.29   -> RMSE",
]));
children.push(P("RMSE (0.29) is bigger than MAE (0.24) because grid 3's larger error got squared. Lesson: RMSE > MAE means a few predictions missed by more than the rest.", { italics: true }));

children.push(H2("R2 — R-squared = 0.958"));
children.push(P("Rule: compare the model's error against a 'lazy guesser' that always predicts the average (here, the average real severity is 2.0)."));
children.push(code([
  "Model error  (SS_res) = sum of squared errors        = 0.42",
  "Lazy error   (SS_tot) = sum of (real - 2.0) squared:",
  "   0 + 4 + 4 + 1 + 1                                 = 10",
  "R2 = 1 - (SS_res / SS_tot) = 1 - (0.42 / 10) = 0.958",
]));
children.push(P("Meaning: the model's error (0.42) is tiny next to the lazy guesser's (10), so it removes 95.8% of the error. R2 = 1.0 is perfect, 0 is no better than guessing the average.", { italics: true }));
children.push(SP());

children.push(H2("Example vs. the real model"));
children.push(tbl(
  ["Metric", "This example (5 grids)", "Real model (27 grids)", "Direction"],
  [
    ["MAE", "0.24", "0.105", "Lower = better"],
    ["RMSE", "0.29", "0.272", "Lower = better"],
    ["R2", "0.958", "0.963", "Higher = better (max 1.0)"],
  ],
  [1800, 2860, 2700, 2000]));
children.push(SP());
children.push(P("Note: these three metrics are standard for ALL regression models (Linear Regression, Random Forest, XGBoost, Neural Networks). They evaluate the predictions, not the algorithm — so the same numbers let you fairly compare different models and pick the best one.", { bold: true }));

// ---------- build ----------
const doc = new Document({
  creator: "Corn Disease AI Project",
  title: "Corn Disease Severity Prediction — Documentation",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: "2E5A1C", font: "Calibri" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: "4A7A2C", font: "Calibri" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [ { level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } } ] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [ new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ text: "Corn Disease AI Project   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" }) ] }) ] }) },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("Corn_Disease_AI_Documentation_v2.docx", buf);
  console.log("Created Corn_Disease_AI_Documentation_v2.docx");
});
