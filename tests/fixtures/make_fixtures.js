// Records what the 2.5 JavaScript patterns draw, so the Python ports can be checked against them step for step.
// Needs Node and Playwright (with Chromium) and the 2.5 index.html:
//   node tests/fixtures/make_fixtures.js [maze] [mandala] [truchet] [contour] [flow]     (default: all)
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
        const ops = [], st = { lineWidth: 1, strokeStyle: "#000", lineCap: "butt", lineJoin: "miter" }, stack = [];
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
          stroke() { ops.push(["stroke", st.lineWidth, st.strokeStyle, st.lineCap, st.lineJoin]); },
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
