const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, TableOfContents } = require("docx");

const CW = 9360;
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const BLUE = "1F4E79", ALT = "EAF1F8";

function P(t, o = {}) {
  return new Paragraph({ spacing: { after: o.after ?? 120, before: o.before ?? 0 }, alignment: o.align,
    children: [new TextRun({ text: t, bold: o.bold, italics: o.italics, size: o.size ?? 22, color: o.color })] });
}
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const SP = () => new Paragraph({ children: [], spacing: { after: 80 } });
function bullet(t) {
  return new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 70 },
    indent: { left: 560, hanging: 280 }, children: [new TextRun({ text: t, size: 22 })] });
}
function code(lines) {
  return new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    rows: [new TableRow({ children: [new TableCell({ borders, width: { size: CW, type: WidthType.DXA },
      shading: { fill: "1E1E1E", type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 140, right: 140 },
      children: lines.map(l => new Paragraph({ spacing: { after: 20 },
        children: [new TextRun({ text: l || " ", font: "Consolas", size: 18, color: "D4D4D4" })] })) })] })] });
}
function tbl(headers, rows, widths) {
  const head = new TableRow({ tableHeader: true, children: headers.map((h, i) =>
    new TableCell({ borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: BLUE, type: ShadingType.CLEAR },
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
ch.push(
  new Paragraph({ spacing: { before: 2200 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Training the Wallpe 2025 Dataset", bold: true, size: 46, color: BLUE })] }),
  new Paragraph({ spacing: { before: 120 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Two Key Issues: Data Leakage & Small Data", size: 28, color: "555555" })] }),
  new Paragraph({ spacing: { before: 500 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Corn Tar Spot Disease — Beginner Guide", italics: true, size: 24 })] }),
  new Paragraph({ children: [new PageBreak()] }),
  H1("Contents"),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
);

// 0. context
ch.push(H1("1. The Dataset in Brief"));
ch.push(P("The Wallpe 2025 file is a Tar Spot disease trial: 24 grids x 7 flight dates x 6 processing variants = 1,008 rows. Disease was scored on 4 of the 7 dates, giving 576 labeled rows. The target is SEV_Mean (disease severity)."));
ch.push(P("Before training, we found TWO issues that must be handled correctly, or the model will be misleading. This document explains both in simple terms."));
ch.push(tbl(["Quick result", "Value"],
  [["Honest accuracy (5-fold CV)", "R2 ~ 0.63"],
   ["Single-split accuracy (unreliable)", "0.67 - 0.68"],
   ["Best / most stable model", "Random Forest"],
   ["Compared to first dataset", "Lower (first was ~0.96)"]],
  [5360, 4000]));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// Issue 1
ch.push(H1("2. Issue 1 — Data Leakage (the dangerous one)"));
ch.push(H2("What it is"));
ch.push(P("Data leakage is when the model accidentally gets to SEE THE ANSWER through a back door. It then looks brilliant in testing but fails in real life."));
ch.push(H2("Why this dataset causes it"));
ch.push(P("The file has 7 columns that all measure the SAME Tar Spot disease:"));
ch.push(code([
  "SEV_Mean        <- we want to PREDICT this (the answer)",
  "NEW_SEV_Mean    <- the same severity, revised",
  "TarSpotBin_Mean <- tar spot presence",
  "AP_Mean         <- pustule / area count   } all measure",
  "SC_Mean         <- stroma count            } the SAME disease",
  "NEW_AP_Mean, NEW_SC_Mean  <- revised versions",
]));
ch.push(P("If we predict SEV_Mean but leave the other 6 in as INPUTS, the model simply finds that NEW_SEV_Mean is almost identical to SEV_Mean and copies it. It scores ~99% but learns NOTHING about vegetation indices."));
ch.push(H2("Simple analogy"));
ch.push(P("It is like giving a student an exam with the answer key stapled to the back. They score 100% - but they did not learn anything, and they will fail the real test where there is no answer key.", { italics: true }));
ch.push(P("In real use, a new drone flight gives vegetation indices but NOT the disease counts (those require manual field scoring - the very thing we are trying to avoid). So those columns will not even exist at prediction time."));
ch.push(H2("The fix"));
ch.push(P("Remove all 6 other disease columns from the features. Keep only the vegetation indices and bands as inputs. This forces the model to actually learn the drone-to-disease relationship - the whole point."));
ch.push(H2("Why this matters most"));
ch.push(P("Leakage is sneaky because it makes results look BETTER, so people do not question it. A leaky model might show R2 0.99, everyone celebrates, then it fails in the field. Catching leakage is what separates a real model from a fake one."));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// Issue 2
ch.push(H1("3. Issue 2 — Small Data"));
ch.push(H2("The problem"));
ch.push(P("This dataset has only 24 grids. Machine learning learns patterns from examples, and 24 is very few. This causes three problems."));
ch.push(H2("Consequence A: one test split is unreliable"));
ch.push(P("With grid-grouped splitting, the test set is only ~5 grids. If those 5 happen to be easy, the score is high; if hard, low. Pure luck. We saw exactly this - the 5 cross-validation folds gave:"));
ch.push(code([
  "0.45 ... 0.68 ... 0.68 ... 0.80 ... 0.45",
  "   ^                          ^",
  " unlucky fold             lucky fold",
  "A swing from 0.45 to 0.80 just from WHICH grids were tested.",
]));
ch.push(H2("The fix: Cross-Validation"));
ch.push(P("Instead of testing once, test 5 times on 5 different grid groups, then average. That average (~0.63) is the honest number that cannot be fooled by one lucky or unlucky split."));
ch.push(code([
  "Test on grids 1-5   -> 0.55",
  "Test on grids 6-10  -> 0.68",
  "Test on grids 11-15 -> 0.68",
  "Test on grids 16-20 -> 0.80",
  "Test on grids 21-24 -> 0.45",
  "                       ----",
  "            Average  =  0.63   <- trust THIS",
]));
ch.push(H2("Consequence B: overfitting risk"));
ch.push(P("With few examples, a complex model can MEMORIZE the 24 grids instead of learning general rules - like a student who memorizes 24 practice questions but cannot answer a new one. Simpler models (Random Forest) are safer on small data, which is why RF edged out XGBoost here."));
ch.push(H2("Consequence C: lower ceiling"));
ch.push(P("24 grids simply contain less information than 135. Even a perfect method can only learn so much. 0.63 may be close to the best this data allows - to go higher you need more grids/seasons, not a fancier model."));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// Why opposite + comparison
ch.push(H1("4. Why the Two Issues Pull in Opposite Directions"));
ch.push(bullet("Leakage makes scores look TOO GOOD (fake high)."));
ch.push(bullet("Small data makes scores UNSTABLE and lower (honest but noisy)."));
ch.push(P("Handling both correctly is what gives a trustworthy 0.63 instead of a fake 0.99 or a misleading single 0.80."));
ch.push(SP());
ch.push(H2("Compared to the first dataset"));
ch.push(tbl(["Aspect", "First file (PPAC-B3)", "This file (Wallpe 2025)"],
  [["Leakage risk", "Low (1 disease column)", "High (7 disease columns)"],
   ["Data size", "135 grids (plenty)", "24 grids (small)"],
   ["Honest R2", "~0.96", "~0.63"],
   ["Trust level", "High", "Decent - use CV, do not over-promise"]],
  [2400, 3480, 3480]));
ch.push(SP());

ch.push(H1("5. The Bottom Line"));
ch.push(P("This new dataset needs more careful handling than the first: we must STRIP OUT the duplicate disease columns (or the model cheats), and we must judge it with CROSS-VALIDATION (or one lucky split fools us). Done right, it is an honest ~0.63 - a reasonable first model for a hard disease with limited data, not a polished one.", { bold: true }));
ch.push(SP());
ch.push(H2("Recommended setup"));
ch.push(bullet("Target: SEV_Mean (the disease severity)."));
ch.push(bullet("Remove the 6 other disease columns from features (leakage)."));
ch.push(bullet("Keep Fungi (fungicide) and DAP (days after planting) as useful features."));
ch.push(bullet("Judge accuracy with 5-fold grid cross-validation, not a single split."));
ch.push(bullet("Prefer Random Forest (slightly better and more stable on this small data)."));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: BLUE, font: "Calibri" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: "2E6CA4", font: "Calibri" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Wallpe 2025 — Leakage & Small Data   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: ch,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("Wallpe2025_Leakage_and_SmallData.docx", b); console.log("Created Wallpe2025_Leakage_and_SmallData.docx"); });
