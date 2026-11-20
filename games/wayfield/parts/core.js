// ===================== core: maths, geometry, spatial index, terrain =====================
const TAU = Math.PI * 2;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function hash2(a, b) {
  let h = Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
const pick = (r, arr) => arr[Math.floor(r() * arr.length) % arr.length];

function makeNoise(seed) {
  const r = mulberry32(seed);
  const perm = new Uint8Array(256), val = new Float32Array(256);
  for (let i = 0; i < 256; i++) { perm[i] = i; val[i] = r(); }
  for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
  const h = (i, j) => val[perm[(perm[i & 255] + j) & 255]];
  function n2(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    return lerp(lerp(h(xi, yi), h(xi + 1, yi), u), lerp(h(xi, yi + 1), h(xi + 1, yi + 1), u), v);
  }
  return (x, y, oct = 4) => {
    let s = 0, a = 1, f = 1, t = 0;
    for (let o = 0; o < oct; o++) { s += a * n2(x * f + o * 17.3, y * f - o * 9.1); t += a; a *= 0.5; f *= 2; }
    return s / t;
  };
}

// ---------- geometry ----------
function segInter(ax, ay, bx, by, cx, cy, dx, dy) {
  const rX = bx - ax, rY = by - ay, sX = dx - cx, sY = dy - cy;
  const den = rX * sY - rY * sX;
  if (Math.abs(den) < 1e-9) return null;
  const t = ((cx - ax) * sY - (cy - ay) * sX) / den;
  const u = ((cx - ax) * rY - (cy - ay) * rX) / den;
  return (t >= 0 && t <= 1 && u >= 0 && u <= 1) ? [t, u] : null;
}
function distPtSeg(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
  let t = L ? ((px - ax) * dx + (py - ay) * dy) / L : 0;
  t = clamp(t, 0, 1);
  const x = ax + dx * t - px, y = ay + dy * t - py;
  return Math.sqrt(x * x + y * y);
}
function segSegDist(ax, ay, bx, by, cx, cy, dx, dy) {
  if (segInter(ax, ay, bx, by, cx, cy, dx, dy)) return 0;
  return Math.min(distPtSeg(ax, ay, cx, cy, dx, dy), distPtSeg(bx, by, cx, cy, dx, dy),
    distPtSeg(cx, cy, ax, ay, bx, by), distPtSeg(dx, dy, ax, ay, bx, by));
}
function pointInPoly(x, y, P) {
  let c = false;
  for (let i = 0, j = P.length - 1; i < P.length; j = i++) {
    const xi = P[i][0], yi = P[i][1], xj = P[j][0], yj = P[j][1];
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) c = !c;
  }
  return c;
}
function polyArea(P) { let a = 0; for (let i = 0, j = P.length - 1; i < P.length; j = i++) a += (P[j][0] * P[i][1] - P[i][0] * P[j][1]); return a / 2; }
function polyCentroid(P) { let x = 0, y = 0; for (const p of P) { x += p[0]; y += p[1]; } return [x / P.length, y / P.length]; }
function polyConvex(P) {
  let sign = 0;
  for (let i = 0; i < P.length; i++) {
    const a = P[i], b = P[(i + 1) % P.length], c = P[(i + 2) % P.length];
    const cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
    if (Math.abs(cr) < 1e-6) continue;
    const s = cr > 0 ? 1 : -1;
    if (!sign) sign = s; else if (s !== sign) return false;
  }
  return true;
}
function polysOverlap(A, B, pad = 0) { // SAT, convex polygons
  for (const P of [A, B]) {
    for (let i = 0; i < P.length; i++) {
      const a = P[i], b = P[(i + 1) % P.length];
      let nx = b[1] - a[1], ny = a[0] - b[0];
      const L = Math.hypot(nx, ny) || 1; nx /= L; ny /= L;
      let amin = Infinity, amax = -Infinity, bmin = Infinity, bmax = -Infinity;
      for (const p of A) { const d = p[0] * nx + p[1] * ny; if (d < amin) amin = d; if (d > amax) amax = d; }
      for (const p of B) { const d = p[0] * nx + p[1] * ny; if (d < bmin) bmin = d; if (d > bmax) bmax = d; }
      if (amax - pad <= bmin || bmax - pad <= amin) return false;
    }
  }
  return true;
}
function segPolyDist(ax, ay, bx, by, P) {
  if (pointInPoly(ax, ay, P) || pointInPoly(bx, by, P)) return 0;
  let d = Infinity;
  for (let i = 0, j = P.length - 1; i < P.length; j = i++) {
    d = Math.min(d, segSegDist(ax, ay, bx, by, P[j][0], P[j][1], P[i][0], P[i][1]));
    if (d === 0) return 0;
  }
  return d;
}
function polyBBox(P) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of P) { if (p[0] < x0) x0 = p[0]; if (p[0] > x1) x1 = p[0]; if (p[1] < y0) y0 = p[1]; if (p[1] > y1) y1 = p[1]; }
  return [x0, y0, x1, y1];
}
function convexHull(pts) {
  const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (p.length < 3) return p;
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const q of p) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
  up.pop(); lo.pop();
  return lo.concat(up);
}
// bilinear point inside a quad [f0, f1, b1, b0]: a along the front, b into the depth
function quadAt(Q, a, b) {
  const fx = lerp(Q[0][0], Q[1][0], a), fy = lerp(Q[0][1], Q[1][1], a);
  const bx = lerp(Q[3][0], Q[2][0], a), by = lerp(Q[3][1], Q[2][1], a);
  return [lerp(fx, bx, b), lerp(fy, by, b)];
}
function quadRect(Q, a0, a1, b0, b1) { return [quadAt(Q, a0, b0), quadAt(Q, a1, b0), quadAt(Q, a1, b1), quadAt(Q, a0, b1)]; }
function insetPoly(P, d) { // shrink toward centroid by roughly d metres (convex)
  const [cx, cy] = polyCentroid(P);
  return P.map(p => { const dx = p[0] - cx, dy = p[1] - cy, L = Math.hypot(dx, dy) || 1; const k = Math.max(0.1, (L - d) / L); return [cx + dx * k, cy + dy * k]; });
}
function circlePoly(x, y, r, n = 12) { const P = []; for (let i = 0; i < n; i++) { const a = i / n * TAU; P.push([x + Math.cos(a) * r, y + Math.sin(a) * r]); } return P; }

// ---------- spatial hash ----------
class Grid {
  constructor(cell) { this.c = cell; this.m = new Map(); this.k = new Map(); }
  add(item, x0, y0, x1, y1) {
    const c = this.c, keys = [];
    for (let i = Math.floor(x0 / c); i <= Math.floor(x1 / c); i++)
      for (let j = Math.floor(y0 / c); j <= Math.floor(y1 / c); j++) {
        const key = i * 65536 + j;
        let s = this.m.get(key); if (!s) this.m.set(key, s = new Set());
        s.add(item); keys.push(key);
      }
    this.k.set(item, keys);
  }
  remove(item) {
    const keys = this.k.get(item); if (!keys) return;
    for (const key of keys) { const s = this.m.get(key); if (s) { s.delete(item); if (!s.size) this.m.delete(key); } }
    this.k.delete(item);
  }
  query(x0, y0, x1, y1, out = new Set()) {
    const c = this.c;
    for (let i = Math.floor(x0 / c); i <= Math.floor(x1 / c); i++)
      for (let j = Math.floor(y0 / c); j <= Math.floor(y1 / c); j++) {
        const s = this.m.get(i * 65536 + j); if (s) for (const it of s) out.add(it);
      }
    return out;
  }
  clear() { this.m.clear(); this.k.clear(); }
}

// ---------- terrain ----------
const WORLD = 3600, TRES = 4, TN = WORLD / TRES;
let water = null, terrainCanvas = null, shoreD = null;
const HWY_Y = WORLD * 0.52;

function isWater(x, y) {
  if (x < 0 || y < 0 || x >= WORLD || y >= WORLD) return true;
  return water[(y / TRES | 0) * TN + (x / TRES | 0)] === 1;
}
function nearWater(x, y, r) {
  for (let a = 0; a < 8; a++) { const t = a / 8 * TAU; if (isWater(x + Math.cos(t) * r, y + Math.sin(t) * r)) return true; }
  return false;
}

function genTerrain(seed) {
  const nz = makeNoise(seed), nz2 = makeNoise(seed + 7), nz3 = makeNoise(seed + 13);
  const r = mulberry32(seed);
  water = new Uint8Array(TN * TN);
  shoreD = new Float32Array(TN * TN);
  const riverX0 = WORLD * (0.63 + r() * 0.1), ph = r() * 10;
  for (let j = 0; j < TN; j++) {
    const y = j * TRES + TRES / 2;
    const rx = riverX0 + Math.sin(y / 560 + ph) * 190 + Math.sin(y / 210 + ph * 2) * 60 + (nz(3, y / 420) - 0.5) * 240;
    const rw = 42 + nz(7, y / 300) * 55;
    for (let i = 0; i < TN; i++) {
      const x = i * TRES + TRES / 2;
      const dr = Math.abs(x - rx) - rw;
      let lk = (nz2(x / 760, y / 760, 4) - 0.64) * 1100;
      // keep the founding area along the highway dry
      const dh = Math.max(0, 520 - Math.hypot(Math.max(0, x - WORLD * 0.42), y - HWY_Y));
      if (x < WORLD * 0.5) lk -= dh * 3;
      const d = Math.min(dr, -lk);
      water[j * TN + i] = d < 0 ? 1 : 0;
      shoreD[j * TN + i] = d;
    }
  }
  terrainCanvas = document.createElement('canvas');
  terrainCanvas.width = TN; terrainCanvas.height = TN;
  const g = terrainCanvas.getContext('2d');
  const img = g.createImageData(TN, TN), D = img.data;
  for (let j = 0; j < TN; j++) for (let i = 0; i < TN; i++) {
    const k = j * TN + i, x = i * TRES, y = j * TRES, d = shoreD[k];
    let R, G, B;
    if (d < 0) {
      const t = smooth(0, 60, -d);
      R = lerp(96, 52, t); G = lerp(158, 104, t); B = lerp(182, 146, t);
    } else if (d < 9) {
      R = 212; G = 200; B = 150;
    } else {
      const n = nz3(x / 340, y / 340, 4), m = nz(x / 90 + 50, y / 90, 2);
      const t = clamp(n * 1.2 - 0.1, 0, 1);
      R = lerp(146, 104, t) + (m - 0.5) * 14; G = lerp(176, 146, t) + (m - 0.5) * 16; B = lerp(98, 78, t) + (m - 0.5) * 8;
      const wet = 1 - smooth(9, 40, d); R -= wet * 14; G -= wet * 4; B -= wet * 6;
    }
    const grain = (hash2(i, j) - 0.5) * 6;
    D[k * 4] = R + grain; D[k * 4 + 1] = G + grain; D[k * 4 + 2] = B + grain; D[k * 4 + 3] = 255;
  }
  g.putImageData(img, 0, 0);
}

// ---------- trees ----------
let trees = [];
const treeGrid = new Grid(48);
function genTrees(seed) {
  trees = []; treeGrid.clear();
  const r = mulberry32(seed + 99), nz = makeNoise(seed + 31);
  for (let k = 0; k < 26000; k++) {
    const x = r() * WORLD, y = r() * WORLD;
    const f = nz(x / 520, y / 520, 3);
    const dens = smooth(0.48, 0.7, f) * 0.9 + 0.03;
    if (r() > dens) continue;
    if (isWater(x, y) || nearWater(x, y, 6)) continue;
    if (x < WORLD * 0.42 && Math.abs(y - HWY_Y) < 40) continue;
    addTree(x, y, 3 + r() * 3.2, r);
  }
}
function addTree(x, y, rad, r) {
  const t = { x, y, r: rad, h: rad * 2.1 + 2, c: Math.floor(r() * 4), dead: false };
  trees.push(t); treeGrid.add(t, x - rad, y - rad, x + rad, y + rad);
  return t;
}
function clearTreesInPoly(P, pad = 1) {
  const [x0, y0, x1, y1] = polyBBox(P);
  for (const t of treeGrid.query(x0 - 8, y0 - 8, x1 + 8, y1 + 8)) {
    if (pointInPoly(t.x, t.y, P) || minDistToPoly(t.x, t.y, P) < t.r * 0.6 + pad) { t.dead = true; treeGrid.remove(t); }
  }
}
function minDistToPoly(x, y, P) {
  let d = Infinity;
  for (let i = 0, j = P.length - 1; i < P.length; j = i++) d = Math.min(d, distPtSeg(x, y, P[j][0], P[j][1], P[i][0], P[i][1]));
  return d;
}
