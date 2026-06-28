const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber } = require("docx");

const CW = 9360;
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const GREEN = "1F5C2E";

function P(t, o = {}) {
  return new Paragraph({ spacing: { after: o.after ?? 120, before: o.before ?? 0 },
    children: [new TextRun({ text: t, bold: o.bold, italics: o.italics,
      size: o.size ?? 22, color: o.color })] });
}
const SP = () => new Paragraph({ children: [], spacing: { after: 60 } });

// a Question block (green bar) + Answer
function QA(q, answerParas) {
  const out = [];
  out.push(new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    rows: [new TableRow({ children: [new TableCell({ borders,
      width: { size: CW, type: WidthType.DXA },
      shading: { fill: GREEN, type: ShadingType.CLEAR },
      margins: { top: 90, bottom: 90, left: 140, right: 140 },
      children: [new Paragraph({ children: [new TextRun({ text: "Q:  " + q, bold: true,
        color: "FFFFFF", size: 23 })] })] })] })] }));
  answerParas.forEach(p => out.push(p));
  out.push(SP());
  return out;
}
function A(t, o = {}) {       // answer line
  return new Paragraph({ spacing: { after: o.after ?? 100, before: o.before ?? 60 },
    indent: { left: 200 },
    children: [new TextRun({ text: t, size: o.size ?? 22, bold: o.bold, italics: o.italics,
      color: o.color })] });
}
function bullet(t) {
  return new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 70 },
    indent: { left: 560, hanging: 280 },
    children: [new TextRun({ text: t, size: 22 })] });
}

const ch = [];

// Title
ch.push(
  new Paragraph({ spacing: { before: 200, after: 60 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Linear Mixed Model (LMM)", bold: true, size: 40, color: GREEN })] }),
  new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Team Discussion — Questions & Answers", size: 26, color: "555555" })] }),
  new Paragraph({ spacing: { after: 200 },
    children: [new TextRun({ text: "Topic: Why can't we use the LMM for predictions?",
      bold: true, size: 24 })] }),
);

// Main answer up front
ch.push(P("THE SHORT ANSWER", { bold: true, color: GREEN, size: 24 }));
ch.push(P("The LMM can make predictions, but they are not accurate enough. It is built to EXPLAIN which signals matter, not to PREDICT disease. So we use XGBoost for prediction and the LMM only for explanation.", { italics: true }));
ch.push(SP());

ch.push(P("THE PROOF (the key numbers)", { bold: true, color: GREEN, size: 24 }));
ch.push(P("We tested both models on new fields they had never seen before:"));
ch.push(bullet("LMM accuracy:     67%   (R2 = 0.669)"));
ch.push(bullet("XGBoost accuracy: 96%   (R2 = 0.958)"));
ch.push(P("XGBoost is far better at predicting, so that is what we use for the disease maps."));
ch.push(SP());

// Q&A section
ch.push(P("QUESTIONS YOUR TEAM MAY ASK", { bold: true, color: GREEN, size: 24 }));
ch.push(SP());

QA("Why can't we use the LMM for predictions?", [
  A("Two simple reasons:"),
  A("1) The LMM can only draw straight lines. Real disease does not grow in a straight line - it speeds up over time. The LMM misses that curve; XGBoost can bend to follow it.", { }),
  A("Easy picture: tracing a curved road with a ruler - you are always a bit off. XGBoost uses a flexible pen.", { italics: true }),
  A("2) The LMM only knows the fields it has already seen. Its power comes from giving each grid its own personal adjustment. For a brand-new field it never measured, it has no adjustment, so it falls back to a basic average and loses its strength - and predicting new fields is the whole point.", { }),
  A("Easy picture: a doctor who is great with regular patients he knows well, but a brand-new patient walks in with no history. XGBoost is trained to handle any new patient.", { italics: true }),
]).forEach(x => ch.push(x));

QA("If XGBoost is better, why keep the LMM at all?", [
  A("Because XGBoost cannot give us p-values. The LMM proves - with statistics - that EXG, NDVI, NDRE and MCARI2 really affect disease. That is the scientific evidence for our report."),
]).forEach(x => ch.push(x));

QA("Can't we just improve the LMM to predict better?", [
  A("Not really. The straight-line limit is built into what an LMM is. To predict well you need a flexible model - which is exactly XGBoost."),
]).forEach(x => ch.push(x));

QA("So is the LMM useless for new fields?", [
  A("No. It still explains the overall relationships between signals and disease. It just should not be the model we predict with. For prediction, XGBoost wins clearly."),
]).forEach(x => ch.push(x));

QA("Do the two models agree with each other?", [
  A("Yes - and that is reassuring. EXG, NDVI, NDRE and MCARI2 rank as top drivers in BOTH the LMM and XGBoost. A statistics model and a machine-learning model pointing to the same signals is strong, trustworthy evidence."),
]).forEach(x => ch.push(x));

// Closing
ch.push(P("HOW TO CLOSE THE DISCUSSION (3 sentences)", { bold: true, color: GREEN, size: 24 }));
ch.push(P("The LMM predicts at 67% accuracy; XGBoost predicts at 96%. The LMM is limited because it only draws straight lines and cannot handle brand-new fields it has not seen. So we use XGBoost to predict the disease maps, and the LMM to explain which signals matter - each doing the job it is best at.", { italics: true }));
ch.push(SP());

// Quick summary table
ch.push(P("ONE-LOOK SUMMARY", { bold: true, color: GREEN, size: 24 }));
ch.push(new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [3120, 3120, 3120],
  rows: [
    new TableRow({ tableHeader: true, children: ["Model", "Best at", "We use it for"].map(h =>
      new TableCell({ borders, width: { size: 3120, type: WidthType.DXA },
        shading: { fill: GREEN, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 20 })] })] })) }),
    ...[["XGBoost / Random Forest", "Predicting (96%)", "Disease maps, spraying"],
        ["Linear Mixed Model", "Explaining (p-values)", "Which signals matter (report)"]].map((r, ri) =>
      new TableRow({ children: r.map(c =>
        new TableCell({ borders, width: { size: 3120, type: WidthType.DXA },
          shading: { fill: ri % 2 ? "FFFFFF" : "EAF3EC", type: ShadingType.CLEAR },
          margins: { top: 70, bottom: 70, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun({ text: c, size: 20 })] })] })) })),
  ] }));

const doc = new Document({
  styles: { default: { document: { run: { font: "Calibri", size: 22 } } } },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET,
    text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "LMM Team Q&A   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: ch,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("LMM_Team_QA.docx", b); console.log("Created LMM_Team_QA.docx"); });
