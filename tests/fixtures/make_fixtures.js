// Records what the 2.5 JavaScript patterns draw, so the Python ports can be checked against them step for step.
// Needs Node and Playwright (with Chromium) and the 2.5 index.html:
//   node tests/fixtures/make_fixtures.js [maze] [mandala] [truchet] [contour] [flow] [dots] [sudoku] [words]     (default: all)
// Writes tests/fixtures/<pattern>_js.json.gz. Only re-run it if the reference changes; the tests read the JSON.
// INDEX_HTML=path/to/index.html points it at another copy (e.g. one checked out from the v2.5.0 tag).
const path = require("path"), fs = require("fs"), zlib = require("zlib");
const { chromium } = require("playwright");

const BOX = { x: 150, y: 150, w: 2250, h: 3000 };   // Letter, 300 dpi, ½ in margins
const LW = 8;                                       // line weight 4 at 300 dpi

const PATTERNS = {
  maze() {
    const cases = [];
    for (const [seed, c] of [[1, 1], [20261117, 5], [42, 3]]) for (const solve of [false, true])
      cases.push({ shape: "rect", word: "", seed, c, solve });
    cases.push({ shape: "rect", word: "", seed: 987654321, c: 10, solve: true });   // the biggest grid, once
    for (const shape of ["heart", "star", "fish", "house"]) for (const solve of [false, true])
      cases.push({ shape, word: "", seed: 20261117, c: 4, solve });
    cases.push({ shape: "word", word: "Maya", seed: 7, c: 4, solve: true });
    return cases;
  },
  mandala() {
    // between them: every motif, the fewest rings (complexity 1) and the most (10)
    return [[1, 1], [2, 3], [3, 5], [20261117, 5], [5, 10]].map(([seed, c]) => ({ seed, c }));
  },
  contour() {
    // small boxes recorded in full (8 + 3c levels; every fifth is drawn twice as thick), one full page as a summary
    const small = { x: 40, y: 60, w: 400, h: 520 };
    return [[1, 1, 300], [42, 10, 300], [7, 4, 150]].map(([seed, c, dpi]) => ({ seed, c, dpi, box: small }))
      .concat([{ seed: 20261117, c: 6, dpi: 300, summary: true }]);
  },
  flow() {
    const small = { x: 40, y: 60, w: 400, h: 520 };
    return [[1, 1], [20261117, 5], [42, 10]].map(([seed, c]) => ({ seed, c, box: small }))
      .concat([{ seed: 20261117, c: 6, summary: true }]);
  },
  dots() {
    // every shape (seed picks it: star 7, heart 9, fish 14, house 1, flower 2, blob 4), complexity 1 to 10,
    // and answer pages (connect) for a few
    const cases = [[7, 1], [9, 3], [14, 5], [1, 7], [2, 10], [4, 6], [8, 9], [3, 2]].map(([seed, c]) => ({ seed, c, connect: false }));
    return cases.concat([[7, 4], [2, 6], [1, 10]].map(([seed, c]) => ({ seed, c, connect: true })));
  },
  sudoku() {
    // complexity 1 (48 givens) to 10 (~25: the hardest also remove single cells), puzzles and answer pages
    return [[1, 1], [20261117, 3], [42, 5], [7, 8], [5, 10], [6, 10]].map(([seed, c]) => ({ seed, c, solve: false }))
      .concat([[42, 5], [5, 10]].map(([seed, c]) => ({ seed, c, solve: true })));
  },
  words() {
    // every theme, complexity 1 to 10 (8x8 across and down only, up to 16x16 in all eight directions),
    // a custom list with a word too long for the grid and one hidden inside another, and answer pages
    const custom = "mum, dad; grandma pizza  pizza Pizza x Ann-Marie supercalifragilistic sun venus";
    return [["animals", "", 1, 1], ["ocean", "", 20261117, 3], ["space", "", 42, 5], ["food", "", 7, 7], ["weather", "", 5, 9],
            ["sports", "", 6, 10], ["custom", custom, 3, 4], ["custom", "", 8, 2]]
      .map(([theme, list, seed, c]) => ({ theme, list, seed, c, solve: false }))
      .concat([["animals", "", 42, 6], ["custom", custom, 3, 10]].map(([theme, list, seed, c]) => ({ theme, list, seed, c, solve: true })));
  },
  truchet() {
    // complexity 1-3 draws one arc per corner, 4 and up three; 10 is the finest grid
    return [[1, 1], [20261117, 3], [7, 4], [42, 7], [5, 10]].map(([seed, c]) => ({ seed, c }));
  },
};

(async () => {
  const want = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(PATTERNS);
  const html = path.resolve(process.env.INDEX_HTML || path.join(__dirname, "..", "..", "index.html"));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + html);
  for (const name of want) {
    const out = await page.evaluate(([name, cases, BOX, LW]) => {
      // a canvas stand-in that writes down every path command, as called, and the style each stroke used
      function recorder() {
        const ops = [], stack = [];
        const st = { lineWidth: 1, strokeStyle: "#000", fillStyle: "#000", lineCap: "butt", lineJoin: "miter", font: "10px sans-serif", textAlign: "start", textBaseline: "alphabetic" };
        const ctx = {
          ops,
          save() { stack.push({ ...st }); ops.push(["save"]); },
          restore() { Object.assign(st, stack.pop()); ops.push(["restore"]); },
          beginPath() { ops.push(["begin"]); },
          moveTo(x, y) { ops.push(["M", x, y]); },
          lineTo(x, y) { ops.push(["L", x, y]); },
          quadraticCurveTo(a, b, x, y) { ops.push(["Q", a, b, x, y]); },
          bezierCurveTo(a, b, c, d, x, y) { ops.push(["C", a, b, c, d, x, y]); },
          arc(x, y, r, a0, a1, ccw = false) { ops.push(["A", x, y, r, a0, a1, !!ccw]); },
          rect(x, y, w, h) { ops.push(["rect", x, y, w, h]); },
          clip() { ops.push(["clip"]); },
          closePath() { ops.push(["Z"]); },
          strokeRect(x, y, w, h) { ops.push(["stroke_rect", x, y, w, h, st.lineWidth, st.strokeStyle]); },
          stroke() { ops.push(["stroke", st.lineWidth, st.strokeStyle, st.lineCap, st.lineJoin]); },
          fill() { ops.push(["fill", st.fillStyle]); },
          fillText(t, x, y) {   // text, position, colour, weight and size
            const m = /^(?:(\d+)\s+)?([\d.]+)px/.exec(st.font);
            ops.push(["text", t, x, y, st.fillStyle, m[1] ? +m[1] : 400, +m[2]]);
          },
          // text widths depend on the fonts installed, so recordings use a stand-in: 0.55 em per character
          // (the Python test's RecordingCanvas does the same); real pages measure the real font
          measureText(t) { return { width: +/([\d.]+)px/.exec(st.font)[1] * 0.55 * t.length }; },
        };
        for (const k of Object.keys(st)) Object.defineProperty(ctx, k, { get: () => st[k], set: v => { st[k] = v; } });
        ctx.lineWidth = LW;
        return ctx;
      }
      return cases.map(k => {
        const ctx = recorder(), box = { ...(k.box || BOX) };
        if (name === "maze") {
          document.getElementById("mazeShape").value = k.shape;
          document.getElementById("mazeWord").value = k.word;
          const grid = mazeGrid(box, k.c), mask = mazeMask(k.shape, grid.cols, grid.rows, k.word);
          ctx.ops.length = 0;
          genMaze(ctx, box, mulberry32(k.seed), k.c, { grid, solve: k.solve });
          return { ...k, box, lw: LW, grid, mask: mask ? Array.from(mask).join("") : null, ops: ctx.ops };
        }
        if (name === "mandala") genMandala(ctx, box, mulberry32(k.seed), k.c, LW);
        if (name === "truchet") genTruchet(ctx, box, mulberry32(k.seed), k.c);
        if (name === "contour") genContour(ctx, box, mulberry32(k.seed), k.c, LW, k.dpi, k.seed);
        if (name === "flow") genFlow(ctx, box, mulberry32(k.seed), k.c, k.seed);
        if (name === "words") {
          document.getElementById("wsTheme").value = k.theme;
          document.getElementById("wsWords").value = k.list;
          const ws = genWords(ctx, box, mulberry32(k.seed), k.c, LW, { dpi: 300 }, { solve: k.solve });
          k.info = { size: ws.size, words: ws.placed.map(p => p.word), skipped: ws.skipped };
        }
        if (name === "sudoku") k.info = genSudoku(ctx, box, mulberry32(k.seed), k.c, LW, { dpi: 300 }, { solve: k.solve });
        if (name === "dots") k.info = genDots(ctx, box, mulberry32(k.seed), k.c, LW, { dpi: 300 }, { connect: k.connect });
        if (k.summary) {   // a full page is too many steps to keep: counts per kind, and sums of the coordinates
          const kinds = {}, sums = {};
          for (const o of ctx.ops) {
            kinds[o[0]] = (kinds[o[0]] || 0) + 1;
            if (o[0] === "M" || o[0] === "L") sums[o[0]] = (sums[o[0]] || 0) + o[1] + o[2];
          }
          return { ...k, box, lw: LW, kinds, sums, first: ctx.ops.slice(0, 200), last: ctx.ops.slice(-200) };
        }
        return { ...k, box, lw: LW, ops: ctx.ops };
      });
    }, [name, PATTERNS[name](), BOX, LW]);
    // coordinates to 1/10000 of a pixel keeps the files small; the tests compare to 1/1000
    const round = (k, v) => (typeof v === "number" && !Number.isInteger(v) ? Math.round(v * 1e4) / 1e4 : v);
    fs.writeFileSync(path.join(__dirname, `${name}_js.json.gz`), zlib.gzipSync(JSON.stringify(out, round), { level: 9 }));
    console.log(`${name}: wrote ${out.length} cases`);
  }
  await browser.close();
})();
