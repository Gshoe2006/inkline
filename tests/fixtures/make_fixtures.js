// Records what the 2.5 JavaScript patterns draw, so the Python ports can be checked against them step for step.
// Needs Node and Playwright (with Chromium) and the 2.5 index.html:
//   node tests/fixtures/make_fixtures.js [maze] [mandala] [truchet] [contour] [flow] [dots] [sudoku] [words] [nonogram] [name] [booklet]     (default: all)
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
  nonogram() {
    // complexity 1 (5x5) to 10 (20x20), puzzles and answer pages
    return [[1, 1], [20261117, 3], [42, 5], [7, 7], [5, 10], [9, 8]].map(([seed, c]) => ({ seed, c, solve: false }))
      .concat([[42, 5], [5, 10]].map(([seed, c]) => ({ seed, c, solve: true })));
  },
  name() {
    // one to four lines, each background (drawn from the same seed first), and a single long word
    return [["Hello", "none", 1, 3], ["Maya", "flow", 20261117, 3], ["Happy Birthday Maya", "contour", 42, 2],
            ["Alexandrina Rose Montgomery Smith", "truchet", 7, 4], ["  Sam   and  Alex ", "none", 5, 5],
            ["Supercalifragilistic", "none", 6, 1], ["", "none", 8, 3]]
      .map(([text, bg, seed, c]) => ({ text, bg, seed, c }));
  },
  booklet() {
    // the page list, the cover and first answer page as drawn, and the fold-and-staple order
    const base = { gen: "maze", c: 5, pages: 10, ramp: true, mix: false, cover: true, pageNums: true, key: true, title: "", nameLine: false, seed: 20261117, pageSeeds: {} };
    return [
      {},
      { gen: "sudoku", pages: 6, title: "Rainy Day Puzzles", nameLine: true },
      { mix: true, pages: 12, c: 7 },
      { gen: "mandala", pages: 3, ramp: false, cover: false, pageNums: false },
      { gen: "words", pages: 2, key: false, c: 1, title: "Word fun" },
      { gen: "dots", pages: 5, c: 9, pageSeeds: { 2: 12345, cover: 777 } },
      { mix: true, pages: 40, c: 10, title: "Big book" },
    ].map(o => ({ ...base, ...o }));
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
          strokeText(t, x, y) {
            const m = /^(?:(\d+)\s+)?([\d.]+)px/.exec(st.font);
            ops.push(["stroke_text", t, x, y, st.lineWidth, st.strokeStyle, m[1] ? +m[1] : 400, +m[2]]);
          },
          fillRect(x, y, w, h) { ops.push(["fill_rect", x, y, w, h, st.fillStyle]); },
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
        if (name === "booklet") {
          const set = (id, v) => { const e = document.getElementById(id); if (e.type === "checkbox") e.checked = v; else e.value = v; };
          set("booklet", true); set("poster", false); set("cbn", false); set("frame", false); set("weight", 4);
          for (const id of ["gen", "pages", "ramp", "mix", "cover", "pageNums", "key", "title", "nameLine"]) set(id, k[id]);
          set("complexity", k.c); S.mode = "make"; S.seed = k.seed; S.pageSeeds = k.pageSeeds;
          const pages = bookPages(), g = geometry();
          const draw = p => { const r = recorder(); r.setTransform = () => {}; r.fillRect = function (x, y, w, h) { this.ops.push(["fill_rect", x, y, w, h, this.fillStyle]); };
            r.ops.length = 0; drawPage(r, g, p); return r.ops; };
          const strip = p => ({ kind: p.kind, gen: p.gen ?? null, seed: p.seed ?? null, c: p.c ?? null, title: p.title ?? "", name: !!p.name,
                                header: !!p.header, label: p.label ?? "", pageNo: p.pageNo ?? 0, artSeed: p.artSeed ?? null,
                                items: p.items ? p.items.map(d => d.idx) : null, idx: p.idx ?? null });
          const cover = pages.find(p => p.kind === "cover"), answers = pages.find(p => p.kind === "answers");
          const n = pages.length + ((4 - pages.length % 4) % 4);
          return { ...k, pages: pages.map(strip), coverOps: cover ? draw(cover) : null, answersOps: answers ? draw(answers) : null,
                   foldOrder: foldOrder(n) };
        }
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
        if (name === "nonogram") {
          const n = genNonogram(ctx, box, mulberry32(k.seed), k.c, LW, { dpi: 300 }, { solve: k.solve });
          k.info = { size: n.size, attempts: n.attempts, pic: n.pic.join(""), rows: n.rows, cols: n.cols };
        }
        if (name === "name") {
          document.getElementById("nameText").value = k.text;
          document.getElementById("nameBg").value = k.bg;
          k.info = genName(ctx, { dpi: 300 }, box, k.c, LW, k.seed);
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
