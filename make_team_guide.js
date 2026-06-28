const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber } = require("docx");

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
  new Paragraph({ spacing: { before: 300, after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "How to Use the Models", bold: true, size: 44, color: BLUE })] }),
  new Paragraph({ spacing: { after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "with Different Inputs", bold: true, size: 36, color: BLUE })] }),
  new Paragraph({ spacing: { after: 240 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "A Simple Team Guide — Corn Disease AI", size: 24, color: "555555" })] }),
);

ch.push(H1("1. Think of the Model Like a Juice Machine"));
ch.push(P("A juice machine: you put in fruit, it gives you juice."));
ch.push(code(["You put in FRUIT  ->  machine works  ->  JUICE comes out"]));
ch.push(P("Our model works the same way:"));
ch.push(code(["You put in DRONE DATA  ->  model works  ->  DISEASE PREDICTION"]));
ch.push(P("\"Using the model with different inputs\" simply means putting in different data.", { bold: true }));
ch.push(SP());

ch.push(H1("2. The 4 Things You Can Change"));
ch.push(P("To try different inputs, you change one (or more) of these:"));
ch.push(tbl(["Change this", "Example", "Like..."],
  [["1. The file", "Use a different Excel", "different fruit"],
   ["2. The target", "Predict severity OR stroma count", "what juice you want"],
   ["3. The columns", "Include or exclude Fungi / DAP", "which ingredients"],
   ["4. The model", "XGBoost or Random Forest", "which machine"]],
  [2600, 4160, 2600]));
ch.push(SP());

ch.push(H1("3. Where Everything Lives"));
ch.push(P("All the model code is in ONE file: ml_core.py", { bold: true }));
ch.push(P("Think of ml_core.py as the juice machine's motor. You do not rebuild the motor - you just press buttons (call its functions)."));
ch.push(SP());

ch.push(H1("4. The 3 Buttons (Functions) You Use"));
ch.push(H2("Button 1 - TRAIN (teach the model)"));
ch.push(code(["results = ml.train_all_variants(df, target=\"SEV_Mean\")"]));
ch.push(P("In plain words: \"Learn from this data, predict this column.\"", { italics: true }));
ch.push(H2("Button 2 - PREDICT (use the model)"));
ch.push(code(["predictions = ml.predict(model, new_data)"]));
ch.push(P("In plain words: \"Look at this new data, tell me the disease.\"", { italics: true }));
ch.push(H2("Button 3 - EXPLAIN (statistics / LMM)"));
ch.push(code(["table = ml.fit_lmm(df, target=\"SEV_Mean\")"]));
ch.push(P("In plain words: \"Tell me which signals matter, with proof.\"", { italics: true }));
ch.push(SP());

ch.push(H1("5. A Super-Simple Example (the whole thing)"));
ch.push(code([
  "import ml_core as ml          # turn on the machine",
  "import pandas as pd",
  "",
  "# 1. Put in the data (INPUT)",
  "df = pd.read_excel(\"my_file.xlsx\")",
  "",
  "# 2. Press the TRAIN button - tell it what to predict",
  "results = ml.train_all_variants(df, target=\"SEV_Mean\")",
  "",
  "# 3. See the result",
  "print(ml.comparison_table(results))",
]));
ch.push(P("To try a DIFFERENT input, change just ONE line:"));
ch.push(code([
  "df = pd.read_excel(\"DIFFERENT_file.xlsx\")        # different file",
  "# OR",
  "results = ml.train_all_variants(df, target=\"NEW_SC_Mean\")  # different target",
]));
ch.push(SP());

ch.push(H1("6. The Key Message"));
ch.push(P("You do NOT write new code. You change the INPUT (file, target, columns) and press the same buttons (functions). The machine handles the rest.", { bold: true }));
ch.push(SP());

ch.push(H1("7. How to Learn It"));
ch.push(P("Open the file use_models_examples.py. It has ready examples. Learn by doing:"));
ch.push(bullet("RUN it once - see it work."));
ch.push(bullet("CHANGE one thing - e.g. the target column."));
ch.push(bullet("RUN it again - see what changes."));
ch.push(bullet("Repeat: change the file, the columns, the model."));
ch.push(SP());

ch.push(H1("8. Summary"));
ch.push(P("All model logic is in ml_core.py. You use 3 functions - train_all_variants(), predict(), fit_lmm() - and change the file, target, columns, or model to try different inputs. You never rewrite the model; you just feed it different data. The tutorial file use_models_examples.py lets you learn by editing and re-running.", { bold: true }));
ch.push(SP());
ch.push(P("One-line takeaway: Same machine, different fruit. Change the input, press the same buttons.", { italics: true, color: BLUE }));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: BLUE, font: "Calibri" },
        paragraph: { spacing: { before: 260, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "2E6CA4", font: "Calibri" },
        paragraph: { spacing: { before: 150, after: 80 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "How to Use the Models — Team Guide   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: ch,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("How_To_Use_The_Models_Team_Guide.docx", b); console.log("Created How_To_Use_The_Models_Team_Guide.docx"); });
