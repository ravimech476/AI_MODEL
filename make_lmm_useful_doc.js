const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber } = require("docx");

const CW = 9360;
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const GREEN = "1F5C2E", ALT = "EAF3EC";

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
      shading: { fill: GREEN, type: ShadingType.CLEAR },
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
  new Paragraph({ spacing: { before: 300, after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "How Is the LMM Useful?", bold: true, size: 42, color: GREEN })] }),
  new Paragraph({ spacing: { after: 220 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Linear Mixed Model - A Simple Explanation", size: 26, color: "555555" })] }),
);

ch.push(H1("1. XGBoost Answers 'WHAT', the LMM Answers 'WHY'"));
ch.push(P("The two models have completely different jobs:"));
ch.push(code([
  "XGBoost:  'This grid's severity will be 4.3%'      -> ACTION (spray maps)",
  "LMM:      'PSRI significantly increases disease,   -> UNDERSTANDING (why)",
  "           and fungicide significantly reduces it'",
]));
ch.push(P("XGBoost is the DOER (predicts, makes maps). The LMM is the EXPLAINER (proves what matters). You need both, for different reasons.", { italics: true }));
ch.push(SP());

ch.push(H1("2. The Four Useful Things the LMM Gives You"));

ch.push(H2("1) PROOF of which signals matter (p-values)"));
ch.push(P("XGBoost says 'PSRI is important' - but how sure are we? It cannot tell you. The LMM gives statistical PROOF:"));
ch.push(P("\"EXG, NDVI, NDRE, MCARI2 significantly affect disease (p < 0.001).\"", { italics: true }));
ch.push(P("That word 'significant' with a p-value is something you can defend in a report. XGBoost importance cannot do that."));

ch.push(H2("2) DIRECTION and SIZE of each effect"));
ch.push(P("The LMM tells you which way each signal pushes disease:"));
ch.push(bullet("NDRE up -> disease DOWN (coefficient -30)"));
ch.push(bullet("EXG up  -> disease UP (coefficient +120)"));
ch.push(P("XGBoost importance only says 'this matters' - not the direction or size. The LMM does."));

ch.push(H2("3) It PROVED fungicide works (a real finding)"));
ch.push(P("On the 2025 data, the LMM showed:"));
ch.push(P("Fungicide coefficient = -0.044, p < 0.01  ->  'Fungicide significantly reduces tar spot.'", { bold: true }));
ch.push(P("This is a real, defensible conclusion - exactly what a researcher or agronomist wants. XGBoost could never give this with statistical confidence."));

ch.push(H2("4) It handles repeated-grid data correctly"));
ch.push(P("Our grids are measured over many flights (repeated measurements). The LMM is the statistically correct model for that structure, and the standard method in agricultural science."));
ch.push(SP());

ch.push(H1("3. When You Would Actually USE the LMM"));
ch.push(tbl(["Situation", "How the LMM helps"],
  [["Writing a report / paper", "\"X, Y, Z significantly affect disease (p<0.001)\" - defensible"],
   ["Choosing which indices to collect", "Focus on the proven-significant ones; drop the rest"],
   ["Proving a treatment works", "\"Fungicide significantly reduced severity (p<0.01)\""],
   ["Building trust in XGBoost", "LMM + XGBoost agreeing on top drivers = strong evidence"],
   ["Explaining to non-technical people", "\"Higher PSRI means more disease\" - clear & directional"]],
  [3400, 5960]));
ch.push(SP());

ch.push(H1("4. The Teamwork Between the Two Models"));
ch.push(code([
  "XGBoost  ->  'WHERE is disease and how much?'  ->  spray maps, predictions",
  "LMM      ->  'WHICH signals cause it, proven?' ->  science, reports, decisions",
  "              |",
  "   When BOTH agree (e.g. EXG, NDVI top in both) -> trust the conclusion strongly",
]));
ch.push(P("A machine-learning model and a statistical model pointing to the same drivers is far more convincing than either alone.", { italics: true }));
ch.push(SP());

ch.push(H1("5. A Concrete Example for the Team"));
ch.push(P("If the team asks:"));
ch.push(bullet("\"Does our drone data actually relate to real disease, or is it coincidence?\"  ->  LMM gives p-values that prove it is real."));
ch.push(bullet("\"Did the fungicide trial work?\"  ->  LMM: yes, significant (p<0.01)."));
ch.push(bullet("\"Which 3 indices should we always measure?\"  ->  LMM: the significant ones (PSRI, EXG, NDRE)."));
ch.push(P("XGBoost cannot answer any of those with statistical confidence. The LMM can."));
ch.push(SP());

ch.push(H1("6. Important: Use REAL Severity, Not Predicted"));
ch.push(P("The LMM must use REAL measured severity as its target - never the PREDICTED output from XGBoost. The predicted severity was made FROM the vegetation indices, so feeding it back into the LMM is circular and gives fake p-values. Always run the LMM on the labeled data (real SEV_Mean)."));
ch.push(SP());

ch.push(H1("7. Summary"));
ch.push(P("The LMM is useful for EXPLANATION and PROOF, not prediction. It tells you - with statistical confidence (p-values) - WHICH vegetation indices truly affect disease, in WHICH direction, and by HOW MUCH, while correctly handling repeated-grid data. It even proved the fungicide significantly reduces tar spot. That is its value: defensible scientific conclusions for reports, decisions, and validating the XGBoost predictions - things prediction models cannot give.", { bold: true }));
ch.push(SP());
ch.push(P("One-line takeaway: XGBoost predicts the future; the LMM proves the science.", { italics: true, color: GREEN }));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: GREEN, font: "Calibri" },
        paragraph: { spacing: { before: 260, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "3C7A4A", font: "Calibri" },
        paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "How Is the LMM Useful   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: ch,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("LMM_How_It_Is_Useful.docx", b); console.log("Created LMM_How_It_Is_Useful.docx"); });
