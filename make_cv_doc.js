const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber } = require("docx");

const CW = 9360;
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const TEAL = "0F6E6E", ALT = "E6F2F2";

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
      shading: { fill: TEAL, type: ShadingType.CLEAR },
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
    children: [new TextRun({ text: "What Is Cross-Validation?", bold: true, size: 42, color: TEAL })] }),
  new Paragraph({ spacing: { after: 220 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "A Simple Explanation with One Example", size: 26, color: "555555" })] }),
);

ch.push(H1("1. The Problem It Solves"));
ch.push(P("To check how good a model is, we train it on some grids and test it on other grids it has never seen. But if we test only ONCE, the result depends on WHICH grids we happened to hold out:"));
ch.push(bullet("Easy test grids  -> high score (lucky)"));
ch.push(bullet("Hard test grids  -> low score (unlucky)"));
ch.push(P("So a single test can fool us. Cross-validation fixes this."));
ch.push(SP());

ch.push(H1("2. What Cross-Validation Is"));
ch.push(P("Cross-validation = test many times on different splits, then average. Luck cancels out.", { bold: true }));
ch.push(SP());

ch.push(H1("3. One Simple Example (10 grids, 5 folds)"));
ch.push(H2("Step 1 - split 10 grids into 5 equal groups (folds)"));
ch.push(code([
  "Fold 1:  grids 1, 2",
  "Fold 2:  grids 3, 4",
  "Fold 3:  grids 5, 6",
  "Fold 4:  grids 7, 8",
  "Fold 5:  grids 9, 10",
]));
ch.push(H2("Step 2 - test 5 times, each time hold out ONE fold"));
ch.push(P("Each round: 1 fold is the TEST (hidden), the other 4 folds TRAIN the model."));
ch.push(tbl(["Round", "TEST on", "TRAIN on", "Score"],
  [["1", "grids 1,2", "folds 2,3,4,5", "0.60"],
   ["2", "grids 3,4", "folds 1,3,4,5", "0.55"],
   ["3", "grids 5,6", "folds 1,2,4,5", "0.70"],
   ["4", "grids 7,8", "folds 1,2,3,5", "0.50"],
   ["5", "grids 9,10", "folds 1,2,3,4", "0.65"]],
  [1200, 2200, 3360, 2600]));
ch.push(P("Every grid is tested exactly once, and every grid helps train in the other rounds. Nothing is wasted.", { italics: true }));
ch.push(H2("Step 3 - average the 5 scores"));
ch.push(code([
  "(0.60 + 0.55 + 0.70 + 0.50 + 0.65) / 5  =  0.60",
  "",
  "Honest accuracy = 0.60",
]));
ch.push(SP());

ch.push(H1("4. Why This Beats Testing Once"));
ch.push(P("If we tested only once and happened to pick Round 3, we would see 0.70 (\"great model!\") - but that was a LUCKY test. If we picked Round 4, we would see 0.50 (\"bad model!\") - an UNLUCKY test."));
ch.push(P("One test could mislead us (0.50 or 0.70). The average (0.60) is the truth.", { bold: true }));
ch.push(SP());

ch.push(H1("5. The Picture"));
ch.push(code([
  "Grids:  [1,2] [3,4] [5,6] [7,8] [9,10]",
  "        -------------------------------",
  "Round1: TEST  train train train train  -> 0.60",
  "Round2: train TEST  train train train  -> 0.55",
  "Round3: train train TEST  train train  -> 0.70",
  "Round4: train train train TEST  train  -> 0.50",
  "Round5: train train train train TEST   -> 0.65",
  "        -------------------------------",
  "                         Average = 0.60",
]));
ch.push(P("The test fold 'slides' across all the data, one position at a time.", { italics: true }));
ch.push(SP());

ch.push(H1("6. Easy Analogy"));
ch.push(P("A student takes 5 different exams instead of 1. Maybe they got lucky on one and unlucky on another - but the AVERAGE of 5 exams is a fair, true picture of how good they really are.", { italics: true }));
ch.push(SP());

ch.push(H1("7. On Our Real Data"));
ch.push(P("This is exactly what happened with the 2025 grids:"));
ch.push(tbl(["Test method", "Score", "Meaning"],
  [["One lucky split", "0.629", "Like seeing only Round 3 (0.70)"],
   ["5-fold average", "0.568", "The honest truth"]],
  [3000, 1800, 4560]));
ch.push(P("Cross-validation averaged away the luck and gave the real number."));
ch.push(SP());

ch.push(H1("8. Summary"));
ch.push(P("Cross-validation: split the grids into 5 groups, test the model 5 times (each time holding out a different group), then average the 5 scores. Every grid is tested once, no grid is wasted, and averaging removes the luck of any single test. 5 exams averaged > 1 exam. That average is the accuracy you can trust.", { bold: true }));
ch.push(SP());
ch.push(P("One-line takeaway: Test 5 times on 5 different slices, then average - so luck cannot fool you.", { italics: true, color: TEAL }));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: TEAL, font: "Calibri" },
        paragraph: { spacing: { before: 260, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "2E8B8B", font: "Calibri" },
        paragraph: { spacing: { before: 160, after: 90 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Cross-Validation Explained   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: ch,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("Cross_Validation_Explained.docx", b); console.log("Created Cross_Validation_Explained.docx"); });
