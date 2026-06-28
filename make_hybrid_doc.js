const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, TableOfContents } = require("docx");

const CW = 9360;
const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const PURPLE = "5B2A86", ALT = "F0E9F6";

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
      shading: { fill: PURPLE, type: ShadingType.CLEAR },
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
    children: [new TextRun({ text: "The Hybrid Forecasting Approach", bold: true, size: 46, color: PURPLE })] }),
  new Paragraph({ spacing: { before: 120 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Predicting Where Corn Disease Is Going", size: 28, color: "555555" })] }),
  new Paragraph({ spacing: { before: 500 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "A Simple Explanation for the Team", italics: true, size: 24 })] }),
  new Paragraph({ children: [new PageBreak()] }),
);

// 1
ch.push(H1("1. Two Different Questions"));
ch.push(P("Our current models answer 'how sick is the field RIGHT NOW?'. Forecasting answers a different question: 'where is the disease GOING?'"));
ch.push(tbl(["", "NOWCASTING (current models)", "FORECASTING (the goal)"],
  [["Question", "How sick is it today?", "How sick will it be in 2 weeks?"],
   ["Input", "Drone data today", "Severity history so far"],
   ["Use", "Today's disease map", "Early warning before disease spreads"]],
  [1600, 3880, 3880]));
ch.push(P("Forecasting lets growers spray BEFORE the disease explodes, not after.", { italics: true }));
ch.push(SP());

// 2
ch.push(H1("2. The Three Pieces of the Hybrid"));
ch.push(P("The hybrid combines three tools, each doing one job:"));
ch.push(code([
  "1. DRONE-ML       -> 'How sick is each grid RIGHT NOW?'   (the eyes)",
  "2. GROWTH MODEL   -> 'How fast is it growing?'            (the speed)",
  "3. MARKOV CHAIN   -> 'What is the chance it gets worse?'  (the odds)",
]));
ch.push(P("You already have piece 1 (XGBoost / Random Forest). The next two add the forecasting power."));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// 3 growth model
ch.push(H1("3. Engine 1 - The Growth Model"));
ch.push(P("Tar spot does not grow in a straight line - it accelerates, like a snowball rolling downhill. A little disease makes more disease, which makes even more. This is called exponential growth."));
ch.push(H2("Simple formula"));
ch.push(code([
  "future severity = current severity x (growth factor) ^ (days)",
  "The research paper measured the speed: about 0.20 per day.",
]));
ch.push(H2("Example - a grid at 1% growing at 0.20/day"));
ch.push(tbl(["Day", "Severity"],
  [["Today", "1%"], ["+5 days", "~2.7%"], ["+10 days", "~7%"],
   ["+15 days", "~20%"], ["+20 days", "~50%"]],
  [4680, 4680]));
ch.push(P("It starts slow then explodes - exactly what the paper observed (up to ~50% in three weeks).", { italics: true }));
ch.push(H2("Easy analogy"));
ch.push(P("Like compound interest in a bank: money grows on the new total each day, so it snowballs. Disease spreads the same way (each spot makes new spots).", { italics: true }));
ch.push(H2("How you forecast with it"));
ch.push(bullet("Look at a grid's past severity readings (e.g. 0.5% -> 0.9% -> 1.6%)."));
ch.push(bullet("Fit the curve to measure ITS growth speed."));
ch.push(bullet("Extend the curve forward: 'in 10 days this grid will be ~8%'."));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// 4 markov
ch.push(H1("4. Engine 2 - The Markov Chain"));
ch.push(P("Instead of an exact number, this thinks in STATES and the CHANCE of moving between them."));
ch.push(H2("The states"));
ch.push(code(["Healthy  ->  Low  ->  Moderate  ->  Severe"]));
ch.push(H2("Transition probabilities (learned from past data)"));
ch.push(P("From history, we learn what happens next. For example, if a grid is 'Low' today:"));
ch.push(tbl(["From 'Low', next flight it becomes...", "Probability"],
  [["Stays Low", "30%"], ["Moves to Moderate", "55%"], ["Jumps to Severe", "15%"]],
  [6360, 3000]));
ch.push(H2("How it forecasts"));
ch.push(P("Chain the probabilities forward: 'Low today -> 55% Moderate next flight -> then likely Severe' = this grid has a high chance of being Severe in 2 flights."));
ch.push(H2("Easy analogy"));
ch.push(P("Like a weather forecast: 'if it is cloudy today, there is a 70% chance of rain tomorrow.' You predict the CHANCE of each state, not exact raindrops.", { italics: true }));
ch.push(P("Key rule (why it is 'Markov'): the future depends only on the CURRENT state, not the whole history.", { italics: true }));
ch.push(SP());

// 5 compare
ch.push(H1("5. Growth Model vs Markov Chain"));
ch.push(tbl(["", "Growth Model", "Markov Chain"],
  [["Output", "An exact future number (8%)", "A probability of each state (70% Severe)"],
   ["Thinks in", "A continuous curve", "Discrete states"],
   ["Analogy", "Compound interest", "Weather forecast"],
   ["Answers", "How much?", "How likely?"]],
  [1600, 3880, 3880]));
ch.push(P("They are complementary - one gives the trajectory, the other gives the odds.", { italics: true }));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// 6 hybrid
ch.push(H1("6. How the Hybrid Puts It Together"));
ch.push(code([
  "STEP 1 - Drone flies, our ML estimates CURRENT severity per grid",
  "         (replaces manual field scouting)",
  "              |",
  "STEP 2 - Growth model: how FAST each grid is rising",
  "         Markov chain: the CHANCE of getting worse",
  "              |",
  "STEP 3 - Combine into an EARLY-WARNING RISK MAP:",
  "         green = stable | yellow = rising | red = severe soon -> spray now",
]));
ch.push(H2("Why the hybrid is the best choice"));
ch.push(P("The paper's growth/Markov models need severity measurements to forecast - normally collected by hand. Our drone-ML provides those severity estimates automatically, so the forecast runs on every flight with no manual scouting. That is the breakthrough: automatic detection (our AI) + proven spread-modeling (the paper's math)."));
ch.push(new Paragraph({ children: [new PageBreak()] }));

// Worked example tying all models together
ch.push(H1("7. Worked Example - One Grid Through the Season"));
ch.push(P("This shows how the three models work together for a single grid (Grid 47). "
  + "XGBoost gives the CURRENT severity at each flight; the Growth model and Markov chain "
  + "use that history to forecast the FUTURE."));

ch.push(H2("Part A - XGBoost: current severity at each flight"));
ch.push(P("Each time the drone flies, XGBoost reads the vegetation indices and estimates that "
  + "grid's severity TODAY. No manual scouting needed."));
ch.push(tbl(["Flight date", "Drone data in", "XGBoost predicts (current severity)"],
  [["Aug 6", "NDVI, OSAVI, PSRI ...", "0.5%"],
   ["Aug 13", "NDVI, OSAVI, PSRI ...", "0.9%"],
   ["Aug 21", "NDVI, OSAVI, PSRI ...", "1.6%"]],
  [2200, 3400, 3760]));
ch.push(P("So far XGBoost only tells us NOW. It does not say what happens next.", { italics: true }));

ch.push(H2("Part B - Growth Model: forecast the future NUMBER"));
ch.push(P("The growth model fits a curve to those three points (0.5 -> 0.9 -> 1.6), measures the "
  + "speed (about 0.20/day), and extends the curve forward:"));
ch.push(code([
  "Past (from XGBoost):  Aug6=0.5%  Aug13=0.9%  Aug21=1.6%",
  "Growth model fits the curve -> speed ~0.20/day",
  "Forecast forward:",
  "   Aug 30  ->  ~4%",
  "   Sep 6   ->  ~10%",
  "   Sep 13  ->  ~25%   (heading to SEVERE)",
]));
ch.push(P("Now we know the future AMOUNT: this grid is snowballing toward ~25%.", { italics: true }));

ch.push(H2("Part C - Markov Chain: forecast the future ODDS"));
ch.push(P("The Markov chain looks at the grid's current STATE (Low) and the chance of moving up:"));
ch.push(tbl(["Now", "Next flight", "Flight after"],
  [["Low (1.6%)", "55% chance -> Moderate", "then 50% chance -> Severe"]],
  [2600, 3380, 3380]));
ch.push(P("So: 'Grid 47 has a high probability of becoming Severe within 2 flights.'", { italics: true }));

ch.push(H2("Part D - The combined decision"));
ch.push(code([
  "XGBoost   :  current severity = 1.6% (Low)        <- the EYES",
  "Growth    :  forecast ~25% in 3 weeks             <- the SPEED",
  "Markov    :  high chance of SEVERE in 2 flights   <- the ODDS",
  "----------------------------------------------------------",
  "DECISION  :  Grid 47 is green today but heading RED",
  "          -> SPRAY GRID 47 NOW (before it explodes)",
]));
ch.push(P("That is the whole value: XGBoost detects the present, the growth model and Markov "
  + "chain project the future, and together they warn us in time to act.", { bold: true }));
ch.push(SP());

// 7 data + expectation
ch.push(H1("8. What the Data Allows (Honest)"));
ch.push(P("Forecasting needs several time points per grid:"));
ch.push(tbl(["Dataset", "Flights", "Forecasting feasibility"],
  [["2024 PPAC", "8 flights", "Good - enough history to fit growth curves"],
   ["2025 Wallpe", "4 scored dates", "Minimal - short series, directional only"]],
  [2600, 2200, 4560]));
ch.push(P("We start with the 2024 data (more time points), prove the growth-curve forecast, then apply to 2025."));
ch.push(H2("Realistic expectation"));
ch.push(bullet("Forecasting gives a DIRECTION and rough timing ('heading toward severe in ~2 weeks'), not an exact future number."));
ch.push(bullet("That is still very useful - enough to decide WHERE and WHEN to spray before disease explodes."));
ch.push(bullet("The paper's own forecast was validated on 2024, so the approach genuinely works for tar spot."));
ch.push(SP());

// 8 summary
ch.push(H1("9. Summary"));
ch.push(P("The hybrid forecast combines three tools: our DRONE-ML sees where disease is now (the eyes), the GROWTH MODEL projects how fast it snowballs (the speed), and the MARKOV CHAIN gives the odds of getting worse (the odds). Together they produce an EARLY-WARNING RISK MAP so growers can spray BEFORE tar spot explodes - the real-time detection the research paper calls for.", { bold: true }));
ch.push(SP());
ch.push(P("One-line takeaway: Our AI sees where disease is now; the growth model and Markov chain project where it is going.", { italics: true, color: PURPLE }));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 29, bold: true, color: PURPLE, font: "Calibri" },
        paragraph: { spacing: { before: 260, after: 150 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "7B4BA8", font: "Calibri" },
        paragraph: { spacing: { before: 170, after: 90 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Hybrid Forecasting Approach   |   Page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: ch,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync("Hybrid_Forecasting_Approach.docx", b); console.log("Created Hybrid_Forecasting_Approach.docx"); });
