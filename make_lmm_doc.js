const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, TableOfContents
} = require("docx");

const CW = 9360;
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const HEAD = "1F5C2E", ALT = "EAF3EC";

function P(t, o = {}) {
  return new Paragraph({ spacing: { after: o.after ?? 120, before: o.before ?? 0 },
    alignment: o.align,
    children: [new TextRun({ text: t, bold: o.bold, italics: o.italics,
      size: o.size ?? 22, color: o.color })] });
}
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const SP = () => new Paragraph({ children: [], spacing: { after: 80 } });
function bullet(t) {
  return new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 80 },
    children: [new TextRun({ text: t, size: 22 })] });
}
function code(lines) {
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    rows: [new TableRow({ children: [new TableCell({ borders,
      width: { size: CW, type: WidthType.DXA },
      shading: { fill: "1E1E1E", type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 140, right: 140 },
      children: lines.map(l => new Paragraph({ spacing: { after: 20 },
        children: [new TextRun({ text: l || " ", font: "Consolas", size: 18, color: "D4D4D4" })] })) })] })] });
}
function tbl(headers, rows, widths) {
  const head = new TableRow({ tableHeader: true, children: headers.map((h, i) =>
    new TableCell({ borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: HEAD, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 20 })] })] })) });
  const body = rows.map((r, ri) => new TableRow({ children: r.map((c, i) =>
    new TableCell({ borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: ri % 2 ? "FFFFFF" : ALT, type: ShadingType.CLEAR },
      margins: { top: 70, bottom: 70, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: String(c), size: 20 })] })] })) }));
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: widths, rows: [head, ...body] });
}

const ch = [];

// title
ch.push(
  new Paragraph({ spacing: { before: 2400 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Linear Mixed Model (LMM)", bold: true, size: 50, color: "1F5C2E" })] }),
  new Paragraph({ spacing: { before: 120 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "How It Works, How to Read the Report, and What You Get", size: 28, color: "555555" })] }),
  new Paragraph({ spacing: { before: 500 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Corn Disease Severity Project — Beginner Guide", italics: true, size: 24 })] }),
  new Paragraph({ children: [new PageBreak()] }),
  H1("Contents"),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
);

// 1. What is LMM
ch.push(H1("1. What Is a Linear Mixed Model?"));
ch.push(P("A Linear Mixed Model (LMM) is a statistical model that answers one question for your corn data:"));
ch.push(P("“Which drone measurements actually affect corn disease — and can we trust it?”", { italics: true, bold: true }));
ch.push(P("It is NOT used to predict disease on new fields (XGBoost does that). Its job is EXPLANATION: it tells you which vegetation indices have a real, statistically proven effect on disease, and in which direction."));
ch.push(H2("The name explained"));
ch.push(bullet("Linear = it assumes straight-line relationships (more of an index -> proportionally more/less disease)."));
ch.push(bullet("Mixed = it mixes two kinds of effects: fixed effects (shared pattern) + random effects (per-group adjustment)."));
ch.push(SP());

// 2. How it works
ch.push(H1("2. How the LMM Works"));
ch.push(H2("Fixed effects vs random effects"));
ch.push(P("Every prediction is split into two parts:"));
ch.push(tbl(["Effect", "Meaning", "In your data"],
  [["Fixed effects", "The overall pattern shared by ALL grids", "“Higher EXG -> more disease”"],
   ["Random effects", "A personal offset for each group", "Each GRID (POINT) gets its own baseline"]],
  [2200, 3760, 3400]));
ch.push(SP());
ch.push(P("The model equation looks like this:"));
ch.push(code([
  "SEVERITY = b0 + b1*NDVI + b2*NDRE + ... + b8*CANOPY   <- fixed effects",
  "         + (this GRID's own offset)                    <- random effect",
  "         + error",
]));
ch.push(H2("Why random effects matter for your data"));
ch.push(P("Your 135 grids are each measured across multiple flight dates. Measurements from the SAME grid are related (a sick grid stays sick). Ordinary models assume every row is independent — yours are not. The random effect on POINT handles this correctly. This is the special power of a mixed model."));
ch.push(SP());
ch.push(H2("How it is trained (fitted)"));
ch.push(P("Unlike XGBoost (which builds 600 trees), the LMM estimates the NUMBERS in one equation. It uses a method called REML (Restricted Maximum Likelihood):"));
ch.push(code([
  "Guess the coefficients & variances",
  "   -> measure how LIKELY they make the observed data",
  "   -> adjust   -> repeat ...",
  "   -> stop when it no longer improves  ('Converged: Yes')",
]));
ch.push(P("In code, the whole training is two lines:"));
ch.push(code([
  "model  = smf.mixedlm(formula, data=df, groups=df['POINT'])",
  "result = model.fit()      # estimates all coefficients & p-values",
]));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// 3. Columns used
ch.push(H1("3. Which Columns the LMM Uses (and Why So Few)"));
ch.push(P("Of 56 columns, the LMM uses only 10: SEVERITY (outcome) + 8 predictors (fixed effects) + POINT (random effect)."));
ch.push(tbl(["Role", "Count", "Columns"],
  [["Outcome", "1", "SEVERITY"],
   ["Fixed effects", "8", "NDVI/NDRE/OSAVI/PSRI/RDVI/MCARI2/EXG _MEAN + CANOPY_COVER"],
   ["Random effect", "1", "POINT (grid)"]],
  [2200, 1000, 6160]));
ch.push(SP());
ch.push(P("Why not all 51 like XGBoost? Because a linear model breaks when inputs are near-duplicates (called multicollinearity). In your data the STD/MIN/MAX columns and raw bands repeat the same information as the index means (correlations 0.9 to 1.0). Duplicates make the coefficients and p-values unreliable — the very things the LMM exists to provide. So we keep one clean signal per index. (Full detail in LMM_why_we_drop_columns.txt.)"));
ch.push(SP());

// 4. Reading the report
ch.push(H1("4. How to Read the Report"));
ch.push(P("The report gives two main numbers per index: a Coefficient and a p-value."));
ch.push(H2("Coefficient = direction + strength"));
ch.push(bullet("Positive (+) = that index RAISES disease."));
ch.push(bullet("Negative (-) = that index LOWERS disease."));
ch.push(bullet("Bigger number = stronger effect."));
ch.push(H2("p-value = can we trust it (is it just luck)?"));
ch.push(P("The p-value is the chance the result happened by pure luck. Small p = very unlikely to be luck = REAL effect. Big p = could easily be luck = ignore it."));
ch.push(tbl(["p-value", "Stars", "Meaning"],
  [["< 0.001", "***", "Extremely trustworthy"],
   ["< 0.01", "**", "Very trustworthy"],
   ["< 0.05", "*", "Trustworthy"],
   ["> 0.05", "(none)", "Not significant — ignore"]],
  [2200, 1400, 5760]));
ch.push(SP());
ch.push(H2("How the p-value is calculated (the chain)"));
ch.push(P("All these numbers are produced automatically by the model. The chain is:"));
ch.push(code([
  "1. Coefficient   = best-fit slope                 (e.g. NDRE = -30.5)",
  "2. Std. Error    = how uncertain that slope is    (e.g. 1.5)",
  "3. z  = Coef / Std.Error                          (-30.5 / 1.5 = -20.2)",
  "4. p-value = tail area of the bell curve beyond z (= 0.0000)",
  "   big z -> tiny p -> real ;  small z -> big p -> luck",
]));
ch.push(P("Key idea: a big coefficient is not enough — it must be large RELATIVE to its uncertainty. That is what the p-value measures.", { italics: true }));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// 5. Results
ch.push(H1("5. The Results on Your Data"));
ch.push(P("Fitted on 3,780 rows across 135 grids (Converged: Yes). Statistically significant drivers (p < 0.001):"));
ch.push(tbl(["Index", "Coefficient", "Effect", "Trust"],
  [["EXG_MEAN", "+120.3", "Raises disease", "*** yes"],
   ["MCARI2_MEAN", "-98.4", "Lowers disease", "*** yes"],
   ["RDVI_MEAN", "+60.6", "Raises disease", "*** yes"],
   ["NDRE_MEAN", "-30.5", "Lowers disease", "*** yes"],
   ["NDVI_MEAN", "+22.9", "Raises disease", "*** yes"],
   ["CANOPY_COVER", "+2.29", "Raises disease", "*** yes"],
   ["OSAVI_MEAN", "+5.20", "—", "not significant"],
   ["PSRI_MEAN", "+2.14", "—", "not significant"]],
  [2400, 1900, 2860, 2200]));
ch.push(SP());
ch.push(P("Plain English: 6 vegetation indices have a proven effect on corn disease. EXG, RDVI, NDVI and canopy cover increase with disease; NDRE and MCARI2 decrease with it. OSAVI and PSRI showed no reliable effect (their p-values were too large, partly because they overlap with NDVI/RDVI)."));
ch.push(SP());

// 6. What you get / use
ch.push(H1("6. What You Get From the LMM (Its Use)"));
ch.push(P("From your data, the LMM gives five kinds of information:"));
ch.push(bullet("1. Direction of each index (coefficient): which signals rise or fall with disease."));
ch.push(bullet("2. Trust level (p-value): which signals are real vs noise."));
ch.push(bullet("3. Confidence range (standard error / intervals): how precise each effect is."));
ch.push(bullet("4. Grid variation (random-effect variance): how much grids differ on their own — unique to mixed models."));
ch.push(bullet("5. Model health (converged, observations, groups): the analysis is valid."));
ch.push(SP());
ch.push(H2("Its role vs the prediction models"));
ch.push(tbl(["Model", "What it gives", "Use"],
  [["XGBoost / Random Forest", "Accurate predictions", "Disease maps, spraying decisions"],
   ["Linear Mixed Model", "Coefficients + p-values", "Understanding & reporting which signals matter"]],
  [2900, 3260, 3200]));
ch.push(SP());
ch.push(H2("Why the LMM is not used for prediction"));
ch.push(P("The LMM can predict, but poorly. On unseen grids it scored R2 = 0.669 versus XGBoost's R2 = 0.958. Two reasons: (1) it is linear (cannot fit curves), and (2) for a NEW grid it never saw, it cannot apply that grid's random-effect offset, so it loses its main advantage. Therefore: use XGBoost/RF for prediction, and the LMM only for explanation."));
ch.push(SP());
ch.push(H1("7. One-Line Takeaway"));
ch.push(P("From your data, the LMM produces a “report card” for each vegetation index — its direction (+/-), strength (coefficient), and trustworthiness (p-value) — plus how much grids vary on their own. It explains WHICH drone signals truly drive corn disease, while XGBoost handles the actual predictions.", { bold: true }));

// build
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: "1F5C2E", font: "Calibri" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: "3C7A4A", font: "Calibri" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET,
    text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Linear Mixed Model Guide   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: ch,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("LMM_Guide.docx", b); console.log("Created LMM_Guide.docx"); });
