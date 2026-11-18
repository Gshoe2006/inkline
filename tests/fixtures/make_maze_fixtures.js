// Records what the 2.5 JavaScript maze draws, so the Python port can be checked against it line for line.
// Needs Node and Playwright (with Chromium) and the 2.5 index.html:
//   node tests/fixtures/make_maze_fixtures.js [path/to/index.html]
// Writes tests/fixtures/maze_js.json. Only re-run it if the reference changes; the tests read the JSON.
const path = require("path"), fs = require("fs");
const { chromium } = require("playwright");

const CASES = [];
for (const [seed, c] of [[1, 1], [20261117, 5], [42, 3]]) for (const solve of [false, true])
  CASES.push({ shape: "rect", word: "", seed, c, solve });
CASES.push({ shape: "rect", word: "", seed: 987654321, c: 10, solve: true });   // the biggest grid, once
for (const shape of ["heart", "star", "fish", "house"]) for (const solve of [false, true])
  CASES.push({ shape, word: "", seed: 20261117, c: 4, solve });
CASES.push({ shape: "word", word: "Maya", seed: 7, c: 4, solve: true });

(async () => {
  const html = path.resolve(process.argv[2] || path.join(__dirname, "..", "..", "index.html"));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + html);
  const out = await page.evaluate(cases => {
    // a canvas stand-in that writes down every path command and the style each stroke used
    function recorder() {
      const ops = [], st = { lineWidth: 1, strokeStyle: "#000", lineCap: "butt", lineJoin: "miter" }, stack = [];
      const ctx = {
        ops,
        save() { stack.push({ ...st }); ops.push(["save"]); },
        restore() { Object.assign(st, stack.pop()); ops.push(["restore"]); },
        beginPath() { ops.push(["begin"]); },
        moveTo(x, y) { ops.push(["M", x, y]); },
        lineTo(x, y) { ops.push(["L", x, y]); },
        stroke() { ops.push(["stroke", st.lineWidth, st.strokeStyle, st.lineCap, st.lineJoin]); },
      };
      for (const k of Object.keys(st)) Object.defineProperty(ctx, k, { get: () => st[k], set: v => { st[k] = v; } });
      return ctx;
    }
    const box = { x: 150, y: 150, w: 2250, h: 3000 };   // Letter, 300 dpi, ½ in margins
    return cases.map(k => {
      document.getElementById("mazeShape").value = k.shape;
      document.getElementById("mazeWord").value = k.word;
      const grid = mazeGrid(box, k.c), ctx = recorder();
      const mask = mazeMask(k.shape, grid.cols, grid.rows, k.word);
      genMaze(ctx, box, mulberry32(k.seed), k.c, { grid, solve: k.solve });
      return { ...k, box, grid, mask: mask ? Array.from(mask).join("") : null, ops: ctx.ops };
    });
  }, CASES);
  await browser.close();
  // coordinates to 1/10000 of a pixel keeps the file small; the tests compare to 1/1000
  const round = (k, v) => (typeof v === "number" && !Number.isInteger(v) ? Math.round(v * 1e4) / 1e4 : v);
  fs.writeFileSync(path.join(__dirname, "maze_js.json"), JSON.stringify(out, round));
  console.log(`wrote ${out.length} cases`);
})();
