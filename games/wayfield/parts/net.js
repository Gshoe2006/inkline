// ===================== network: roads, parcels, service buildings =====================
const ROADS = {
  street:  { name: 'Street',  w: 10, speed: 13, cost: 5,  upkeep: 0.3, lanes: 1, lots: true,  unlock: 0, desc: 'Two lanes, lined with parcels' },
  avenue:  { name: 'Avenue',  w: 18, speed: 19, cost: 12, upkeep: 0.6, lanes: 2, lots: true,  unlock: 1, desc: 'Four lanes with a median, deeper parcels' },
  highway: { name: 'Highway', w: 24, speed: 30, cost: 24, upkeep: 1.0, lanes: 2, lots: false, unlock: 3, desc: 'Fast, no parcels alongside' },
};

const ZONES = {
  resL: { name: 'Low-density housing',  short: 'Houses',     key: 'res', color: [79, 174, 88],  css: 'var(--z-res)', unlock: 0 },
  resH: { name: 'High-density housing', short: 'Apartments', key: 'res', color: [40, 130, 62],  css: '#2c8a45', unlock: 1 },
  com:  { name: 'Commercial',           short: 'Shops',      key: 'com', color: [63, 132, 214], css: 'var(--z-com)', unlock: 0 },
  off:  { name: 'Office',               short: 'Offices',    key: 'off', color: [139, 103, 212], css: 'var(--z-off)', unlock: 2 },
  ind:  { name: 'Industrial',           short: 'Industry',   key: 'ind', color: [210, 154, 47], css: 'var(--z-ind)', unlock: 0 },
};

const SERVICES = {
  wind:   { name: 'Wind turbine',      cat: 'util', icon: 'wind',   cost: 3500,  upkeep: 110, power: 5,  size: [14, 14], unlock: 0, desc: '5 MW, clean' },
  coal:   { name: 'Coal power plant',  cat: 'util', icon: 'bolt',   cost: 16000, upkeep: 520, power: 40, size: [48, 34], unlock: 0, pollution: 380, desc: '40 MW, pollutes' },
  tower:  { name: 'Water tower',       cat: 'util', icon: 'drop',   cost: 2500,  upkeep: 80,  water: 9,  size: [12, 12], unlock: 0, desc: '9 m³/h' },
  pump:   { name: 'Water pump',        cat: 'util', icon: 'drop',   cost: 7000,  upkeep: 290, water: 48, size: [22, 18], unlock: 0, needsWater: true, desc: '48 m³/h, on a shore' },
  police: { name: 'Police station',    cat: 'svc',  icon: 'shield', cost: 6000,  upkeep: 260, radius: 400, size: [24, 18], unlock: 1, desc: 'Safety, 400 m' },
  fire:   { name: 'Fire station',      cat: 'svc',  icon: 'flame',  cost: 6000,  upkeep: 260, radius: 400, size: [24, 20], unlock: 1, desc: 'Fire cover, 400 m' },
  clinic: { name: 'Clinic',            cat: 'svc',  icon: 'cross',  cost: 7500,  upkeep: 300, radius: 420, size: [24, 20], unlock: 1, desc: 'Health, 420 m' },
  school: { name: 'School',            cat: 'svc',  icon: 'book',   cost: 9000,  upkeep: 340, radius: 480, size: [34, 26], unlock: 2, desc: 'Education, 480 m' },
  park:   { name: 'Pocket park',       cat: 'park', icon: 'tree',   cost: 1200,  upkeep: 40,  radius: 200, size: [26, 20], unlock: 0, desc: 'Leisure, 200 m' },
  plaza:  { name: 'Town green',        cat: 'park', icon: 'tree',   cost: 5200,  upkeep: 150, radius: 340, size: [54, 38], unlock: 2, desc: 'Leisure, 340 m' },
};

const MILESTONES = [
  { pop: 0,     name: 'Crossroads', reward: 0 },
  { pop: 250,   name: 'Hamlet',     reward: 10000, unlocks: 'Avenues, apartments, police, fire and clinics' },
  { pop: 900,   name: 'Village',    reward: 20000, unlocks: 'Offices, schools and the town green' },
  { pop: 2400,  name: 'Town',       reward: 35000, unlocks: 'Highways' },
  { pop: 6000,  name: 'City',       reward: 60000 },
  { pop: 12000, name: 'Metropolis', reward: 100000 },
];

let nodes = new Map(), edges = new Map(), lots = new Map(), services = new Map();
let nextId = 1;
const edgeGrid = new Grid(64), lotGrid = new Grid(64), svcGrid = new Grid(96);
let netDirty = true;

// ---------- nodes & edges ----------
function addNode(x, y, id) {
  const n = { id: id || nextId++, x, y, edges: new Set(), outside: false };
  nodes.set(n.id, n); return n;
}
function bez(ax, ay, cx, cy, bx, by, t) { const m = 1 - t; return [m * m * ax + 2 * m * t * cx + t * t * bx, m * m * ay + 2 * m * t * cy + t * t * by]; }
function edgeGeom(e) {
  const A = nodes.get(e.a), B = nodes.get(e.b);
  const approx = Math.hypot(e.cx - A.x, e.cy - A.y) + Math.hypot(B.x - e.cx, B.y - e.cy);
  const n = Math.max(2, Math.ceil(approx / 4));
  const pts = [], cum = [0];
  for (let i = 0; i <= n; i++) pts.push(bez(A.x, A.y, e.cx, e.cy, B.x, B.y, i / n));
  for (let i = 1; i <= n; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  e.pts = pts; e.cum = cum; e.n = n; e.len = cum[n];
  e.bbox = polyBBox(pts);
  e.wet = pts.map(p => isWater(p[0], p[1]));
  e.wetLen = 0; for (let i = 1; i <= n; i++) if (e.wet[i] || e.wet[i - 1]) e.wetLen += cum[i] - cum[i - 1];
  const path = new Path2D(); path.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i <= n; i++) path.lineTo(pts[i][0], pts[i][1]);
  e.path = path; e.markKey = null;
}
function addEdge(a, b, cx, cy, type, id) {
  const e = { id: id || nextId++, a: a.id, b: b.id, cx, cy, type, cars: 0, load: 0, comp: 0 };
  edgeGeom(e);
  edges.set(e.id, e); a.edges.add(e.id); b.edges.add(e.id);
  const w = ROADS[type].w;
  edgeGrid.add(e, e.bbox[0] - w, e.bbox[1] - w, e.bbox[2] + w, e.bbox[3] + w);
  netDirty = true;
  return e;
}
function removeEdgeRaw(e) {
  edges.delete(e.id); edgeGrid.remove(e);
  const A = nodes.get(e.a), B = nodes.get(e.b);
  if (A) A.edges.delete(e.id); if (B) B.edges.delete(e.id);
  netDirty = true;
}
function otherNode(e, nid) { return e.a === nid ? e.b : e.a; }
function edgePoint(e, s) { // [x, y, tx, ty]
  s = clamp(s, 0, e.len);
  let lo = 0, hi = e.n;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (e.cum[mid] <= s) lo = mid; else hi = mid; }
  const L = e.cum[hi] - e.cum[lo] || 1, f = (s - e.cum[lo]) / L;
  const p = e.pts[lo], q = e.pts[hi];
  const tx = (q[0] - p[0]) / L, ty = (q[1] - p[1]) / L;
  return [lerp(p[0], q[0], f), lerp(p[1], q[1], f), tx, ty];
}
function nearestOnEdge(e, x, y) {
  let best = Infinity, bi = 0, bf = 0;
  for (let i = 0; i < e.n; i++) {
    const p = e.pts[i], q = e.pts[i + 1];
    const dx = q[0] - p[0], dy = q[1] - p[1], L = dx * dx + dy * dy;
    let f = L ? ((x - p[0]) * dx + (y - p[1]) * dy) / L : 0; f = clamp(f, 0, 1);
    const d = Math.hypot(p[0] + dx * f - x, p[1] + dy * f - y);
    if (d < best) { best = d; bi = i; bf = f; }
  }
  const s = lerp(e.cum[bi], e.cum[bi + 1], bf);
  const p = e.pts[bi], q = e.pts[bi + 1];
  return { d: best, s, t: (bi + bf) / e.n, x: lerp(p[0], q[0], bf), y: lerp(p[1], q[1], bf) };
}
function nearestEdge(x, y, r, filter) {
  let best = null;
  for (const e of edgeGrid.query(x - r, y - r, x + r, y + r)) {
    if (filter && !filter(e)) continue;
    const h = nearestOnEdge(e, x, y);
    const d = h.d - ROADS[e.type].w / 2;
    if (d < r && (!best || d < best.dd)) best = { e, ...h, dd: d };
  }
  return best;
}
function nearestNode(x, y, r) {
  let best = null, bd = r;
  for (const n of nodes.values()) { const d = Math.hypot(n.x - x, n.y - y); if (d < bd) { bd = d; best = n; } }
  return best;
}

// split edge e at bezier parameter t -> returns new middle node
function splitEdge(e, t) {
  const A = nodes.get(e.a), B = nodes.get(e.b);
  const P = bez(A.x, A.y, e.cx, e.cy, B.x, B.y, t);
  const mid = addNode(P[0], P[1]);
  removeEdgeRaw(e);
  const e1 = addEdge(A, mid, lerp(A.x, e.cx, t), lerp(A.y, e.cy, t), e.type);
  const e2 = addEdge(mid, B, lerp(e.cx, B.x, t), lerp(e.cy, B.y, t), e.type);
  reattach([e1, e2], e.id);
  return mid;
}
// lots/services that referenced an edge that was replaced find their nearest new piece
function reattach(pieces, oldId) {
  const fix = (o) => {
    let best = null, bd = Infinity;
    for (const p of pieces) { const h = nearestOnEdge(p, o.ax, o.ay); if (h.d < bd) { bd = h.d; best = { p, h }; } }
    o.edge = best.p.id; o.s = best.h.s;
  };
  for (const l of lots.values()) if (l.edge === oldId) fix(l);
  for (const sv of services.values()) if (sv.edge === oldId) fix(sv);
}

// ---------- road placement ----------
// A point from the snapping step: {x, y, node?, edge?}
function resolvePoint(p) {
  const n = nearestNode(p.x, p.y, 3);
  if (n) return n;
  const h = nearestEdge(p.x, p.y, 1.5);
  if (h && h.d < ROADS[h.e.type].w / 2 + 1.5) {
    const e = h.e, A = nodes.get(e.a), B = nodes.get(e.b);
    if (h.s < 6) return A;
    if (h.s > e.len - 6) return B;
    return splitEdge(e, h.t);
  }
  return addNode(p.x, p.y);
}

// sample a candidate road; returns analysis without changing anything
function analyseRoad(p0, c, p1, type) {
  const n = Math.max(2, Math.ceil((Math.hypot(c[0] - p0.x, c[1] - p0.y) + Math.hypot(p1.x - c[0], p1.y - c[1])) / 4));
  const pts = [];
  for (let i = 0; i <= n; i++) pts.push(bez(p0.x, p0.y, c[0], c[1], p1.x, p1.y, i / n));
  let len = 0, wet = 0;
  for (let i = 1; i <= n; i++) {
    const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    len += d; if (isWater(pts[i][0], pts[i][1])) wet += d;
  }
  const R = ROADS[type];
  const res = { pts, len, wet, cost: Math.round((len - wet) * R.cost + wet * R.cost * 4), ok: true, reason: '' };
  if (len < 12) { res.ok = false; res.reason = 'Too short'; return res; }
  for (const p of pts) if (p[0] < 10 || p[1] < 10 || p[0] > WORLD - 10 || p[1] > WORLD - 10) {
    const outsideOk = false; if (!outsideOk) { res.ok = false; res.reason = 'Outside the map'; return res; }
  }
  if (isWater(p0.x, p0.y) || isWater(p1.x, p1.y)) { res.ok = false; res.reason = 'Ends must be on land'; return res; }
  // turning radius: reject hairpins
  for (let i = 1; i < n; i++) {
    const a = pts[i - 1], b = pts[i], d = pts[i + 1];
    const ang = Math.abs(Math.atan2((b[0] - a[0]) * (d[1] - b[1]) - (b[1] - a[1]) * (d[0] - b[0]), (b[0] - a[0]) * (d[0] - b[0]) + (b[1] - a[1]) * (d[1] - b[1])));
    if (ang > 0.75) { res.ok = false; res.reason = 'Curve is too tight'; return res; }
  }
  // service buildings block roads
  const hw = R.w / 2;
  const bb = polyBBox(pts);
  for (const sv of svcGrid.query(bb[0] - hw, bb[1] - hw, bb[2] + hw, bb[3] + hw)) {
    for (let i = 0; i < n; i++) if (segPolyDist(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], sv.poly) < hw) {
      res.ok = false; res.reason = SERVICES[sv.type].name + ' is in the way'; return res;
    }
  }
  // parallel overlap with existing roads (shallow crossings)
  for (const e of edgeGrid.query(bb[0] - 20, bb[1] - 20, bb[2] + 20, bb[3] + 20)) {
    // a crossing stays close for ~2*lim metres; running alongside stays close much longer
    const lim = (ROADS[e.type].w + R.w) / 4;
    let run = 0;
    for (let i = 1; i < n; i++) {
      const h = nearestOnEdge(e, pts[i][0], pts[i][1]);
      const step = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      const nearEnd = Math.hypot(pts[i][0] - p0.x, pts[i][1] - p0.y) < lim * 3 || Math.hypot(pts[i][0] - p1.x, pts[i][1] - p1.y) < lim * 3;
      if (h.d < lim && !nearEnd) run += step; else run = 0;
      if (run > lim * 5) { res.ok = false; res.reason = 'Overlaps a road'; return res; }
    }
  }
  if (S.money < res.cost) { res.ok = false; res.reason = 'Not enough funds'; }
  return res;
}

function buildRoad(p0, c, p1, type) {
  const an = analyseRoad(p0, c, p1, type);
  if (!an.ok) return { ok: false, reason: an.reason };
  const A = resolvePoint(p0), B = resolvePoint(p1);
  if (A === B) return { ok: false, reason: 'Too short' };
  // intersections with existing edges
  const pts = an.pts, n = pts.length - 1, hits = [];
  const bb = polyBBox(pts);
  for (const e of edgeGrid.query(bb[0], bb[1], bb[2], bb[3])) {
    for (let i = 0; i < n; i++) for (let j = 0; j < e.n; j++) {
      const r = segInter(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], e.pts[j][0], e.pts[j][1], e.pts[j + 1][0], e.pts[j + 1][1]);
      if (!r) continue;
      const tn = (i + r[0]) / n;
      const x = lerp(pts[i][0], pts[i + 1][0], r[0]), y = lerp(pts[i][1], pts[i + 1][1], r[0]);
      if (Math.hypot(x - A.x, y - A.y) < 8 || Math.hypot(x - B.x, y - B.y) < 8) continue;
      hits.push({ tn, x, y });
    }
  }
  hits.sort((a, b) => a.tn - b.tn);
  const chain = [{ node: A, t: 0 }];
  for (const h of hits) {
    if (h.tn - chain[chain.length - 1].t < 0.01) continue;
    let node = nearestNode(h.x, h.y, 7);
    if (!node) {
      const ne = nearestEdge(h.x, h.y, 2);
      if (!ne) continue;
      if (ne.s < 7) node = nodes.get(ne.e.a);
      else if (ne.s > ne.e.len - 7) node = nodes.get(ne.e.b);
      else node = splitEdge(ne.e, ne.t);
    }
    if (node === A || node === B || node === chain[chain.length - 1].node) continue;
    chain.push({ node, t: h.tn });
  }
  chain.push({ node: B, t: 1 });
  // split the new bezier into pieces
  let ax = p0.x, ay = p0.y, cx = c[0], cy = c[1], bx = p1.x, by = p1.y, tPrev = 0;
  const made = [];
  for (let k = 1; k < chain.length; k++) {
    const from = chain[k - 1].node, to = chain[k].node;
    let pcx, pcy;
    if (k < chain.length - 1) {
      const t = (chain[k].t - tPrev) / (1 - tPrev);
      pcx = lerp(ax, cx, t); pcy = lerp(ay, cy, t);
      const P = bez(ax, ay, cx, cy, bx, by, t);
      const ncx = lerp(cx, bx, t), ncy = lerp(cy, by, t);
      ax = P[0]; ay = P[1]; cx = ncx; cy = ncy; tPrev = chain[k].t;
    } else { pcx = cx; pcy = cy; }
    // nudge control so the piece meets the snapped node positions
    const dup = [...from.edges].some(id => { const e = edges.get(id); return e && otherNode(e, from.id) === to.id; });
    if (dup || Math.hypot(from.x - to.x, from.y - to.y) < 3) continue;
    const e = addEdge(from, to, pcx, pcy, type);
    made.push(e);
  }
  S.money -= an.cost;
  // clear the corridor of parcels & trees, then cut new parcels
  for (const e of made) clearCorridor(e);
  for (const e of made) if (ROADS[type].lots) { genLots(e, 1); genLots(e, -1); }
  netDirty = true;
  return { ok: true, cost: an.cost, end: B, edges: made };
}

function corridorPoly(e, i, pad) {
  const p = e.pts[i], q = e.pts[i + 1];
  const dx = q[0] - p[0], dy = q[1] - p[1], L = Math.hypot(dx, dy) || 1;
  const w = ROADS[e.type].w / 2 + pad, nx = -dy / L * w, ny = dx / L * w;
  const ex = dx / L * 2, ey = dy / L * 2;
  return [[p[0] + nx - ex, p[1] + ny - ey], [q[0] + nx + ex, q[1] + ny + ey], [q[0] - nx + ex, q[1] - ny + ey], [p[0] - nx - ex, p[1] - ny - ey]];
}
function clearCorridor(e) {
  const w = ROADS[e.type].w / 2;
  for (const l of lotGrid.query(e.bbox[0] - w, e.bbox[1] - w, e.bbox[2] + w, e.bbox[3] + w)) {
    for (let i = 0; i < e.n; i++) if (segPolyDist(e.pts[i][0], e.pts[i][1], e.pts[i + 1][0], e.pts[i + 1][1], l.poly) < w + 0.6) { removeLot(l); break; }
  }
  for (let i = 0; i < e.n; i++) clearTreesInPoly(corridorPoly(e, i, 2), 0);
}

// ---------- parcels (gridless lots) ----------
function lotFits(Q, ownEdge) {
  if (!polyConvex(Q)) return false;
  const area = Math.abs(polyArea(Q));
  if (area < 90) return false;
  for (const p of Q) if (isWater(p[0], p[1])) return false;
  const [cx, cy] = polyCentroid(Q);
  if (isWater(cx, cy)) return false;
  const bb = polyBBox(Q);
  if (bb[0] < 4 || bb[1] < 4 || bb[2] > WORLD - 4 || bb[3] > WORLD - 4) return false;
  for (const l of lotGrid.query(bb[0], bb[1], bb[2], bb[3])) if (polysOverlap(Q, l.poly, 0.05)) return false;
  for (const sv of svcGrid.query(bb[0], bb[1], bb[2], bb[3])) if (polysOverlap(Q, sv.poly, 0.05)) return false;
  for (const e of edgeGrid.query(bb[0] - 14, bb[1] - 14, bb[2] + 14, bb[3] + 14)) {
    const w = ROADS[e.type].w / 2 + (e === ownEdge ? 0.4 : 1.2);
    for (let i = 0; i < e.n; i++) {
      const p = e.pts[i], q = e.pts[i + 1];
      if (Math.max(p[0], q[0]) < bb[0] - w || Math.min(p[0], q[0]) > bb[2] + w || Math.max(p[1], q[1]) < bb[1] - w || Math.min(p[1], q[1]) > bb[3] + w) continue;
      if (segPolyDist(p[0], p[1], q[0], q[1], Q) < w) return false;
    }
  }
  return true;
}
function genLots(e, side) {
  const R = ROADS[e.type];
  const rnd = mulberry32(e.id * 7 + (side > 0 ? 1 : 2));
  const A = nodes.get(e.a), B = nodes.get(e.b);
  const clearOf = (n) => n.edges.size > 1 ? Math.max(...[...n.edges].map(id => edges.get(id) ? ROADS[edges.get(id).type].w / 2 : 0)) + 3 : 1;
  let s = clearOf(A);
  const end = e.len - clearOf(B);
  const off = R.w / 2 + 0.8;
  const depths = e.type === 'avenue' ? [38, 30, 22, 15] : [30, 24, 17, 12];
  while (s < end - 8) {
    const front = Math.min(10 + rnd() * 8 + (e.type === 'avenue' ? 4 : 0), end - s);
    if (front < 8) break;
    const P0 = edgePoint(e, s), P1 = edgePoint(e, s + front);
    const n0 = [-P0[3] * side, P0[2] * side], n1 = [-P1[3] * side, P1[2] * side];
    let placed = false;
    for (const d of depths) {
      const Q = [
        [P0[0] + n0[0] * off, P0[1] + n0[1] * off],
        [P1[0] + n1[0] * off, P1[1] + n1[1] * off],
        [P1[0] + n1[0] * (off + d), P1[1] + n1[1] * (off + d)],
        [P0[0] + n0[0] * (off + d), P0[1] + n0[1] * (off + d)],
      ];
      if (lotFits(Q, e)) { addLot(Q, e, s + front / 2); placed = true; break; }
    }
    s += placed ? front : 3;
  }
}
function addLot(Q, e, s, id) {
  const [cx, cy] = polyCentroid(Q);
  const fx = (Q[0][0] + Q[1][0]) / 2, fy = (Q[0][1] + Q[1][1]) / 2;
  const l = {
    id: id || nextId++, poly: Q, edge: e.id, s, cx, cy, ax: fx, ay: fy,
    area: Math.abs(polyArea(Q)), front: Math.hypot(Q[1][0] - Q[0][0], Q[1][1] - Q[0][1]),
    depth: Math.hypot((Q[3][0] + Q[2][0]) / 2 - fx, (Q[3][1] + Q[2][1]) / 2 - fy),
    zone: null, b: null, lv: 30, cov: {}, poll: 0, happy: 50,
  };
  lots.set(l.id, l);
  const bb = polyBBox(Q); lotGrid.add(l, bb[0], bb[1], bb[2], bb[3]);
  clearTreesInPoly(Q, 0.5);
  return l;
}
function removeLot(l) { lots.delete(l.id); lotGrid.remove(l); }

// ---------- service buildings ----------
function servicePlacement(type, x, y) {
  const D = SERVICES[type];
  const h = nearestEdge(x, y, 45, e => e.type !== 'highway');
  if (!h) return { ok: false, reason: 'Place it beside a street or avenue' };
  const e = h.e, P = edgePoint(e, h.s);
  const side = ((x - P[0]) * -P[3] + (y - P[1]) * P[2]) >= 0 ? 1 : -1;
  const nx = -P[3] * side, ny = P[2] * side, tx = P[2], ty = P[3];
  const [w, d] = D.size;
  const off = ROADS[e.type].w / 2 + 1.5;
  const f0 = [P[0] + nx * off - tx * w / 2, P[1] + ny * off - ty * w / 2];
  const f1 = [P[0] + nx * off + tx * w / 2, P[1] + ny * off + ty * w / 2];
  const poly = [f0, f1, [f1[0] + nx * d, f1[1] + ny * d], [f0[0] + nx * d, f0[1] + ny * d]];
  const res = { ok: true, poly, edge: e, s: h.s, nx, ny, tx, ty, reason: '' };
  const bb = polyBBox(poly);
  for (const p of poly) if (isWater(p[0], p[1])) { res.ok = false; res.reason = 'Needs dry land'; return res; }
  for (const sv of svcGrid.query(bb[0], bb[1], bb[2], bb[3])) if (polysOverlap(poly, sv.poly, 0.05)) { res.ok = false; res.reason = 'Overlaps another building'; return res; }
  for (const o of edgeGrid.query(bb[0] - 14, bb[1] - 14, bb[2] + 14, bb[3] + 14)) {
    const hw = ROADS[o.type].w / 2 + (o === e ? 0.4 : 1);
    for (let i = 0; i < o.n; i++) if (segPolyDist(o.pts[i][0], o.pts[i][1], o.pts[i + 1][0], o.pts[i + 1][1], poly) < hw) { res.ok = false; res.reason = 'Overlaps a road'; return res; }
  }
  if (D.needsWater) {
    const back = [(poly[2][0] + poly[3][0]) / 2 + nx * 14, (poly[2][1] + poly[3][1]) / 2 + ny * 14];
    if (!nearWater(back[0], back[1], 14) && !isWater(back[0], back[1])) { res.ok = false; res.reason = 'Back it onto a river or lake'; return res; }
  }
  if (S.money < D.cost) { res.ok = false; res.reason = 'Not enough funds'; }
  return res;
}
function placeService(type, x, y) {
  const pl = servicePlacement(type, x, y);
  if (!pl.ok) return pl;
  const bb = polyBBox(pl.poly);
  for (const l of lotGrid.query(bb[0], bb[1], bb[2], bb[3])) if (polysOverlap(pl.poly, l.poly, 0.05)) removeLot(l);
  clearTreesInPoly(pl.poly, 0.5);
  const [cx, cy] = polyCentroid(pl.poly);
  const sv = { id: nextId++, type, poly: pl.poly, cx, cy, edge: pl.edge.id, s: pl.s, ax: (pl.poly[0][0] + pl.poly[1][0]) / 2, ay: (pl.poly[0][1] + pl.poly[1][1]) / 2, seed: Math.floor(Math.random() * 1e9), served: true };
  addServiceRec(sv);
  S.money -= SERVICES[type].cost;
  netDirty = true; covDirty = true;
  return { ok: true, sv };
}
function addServiceRec(sv) {
  services.set(sv.id, sv);
  const bb = polyBBox(sv.poly); svcGrid.add(sv, bb[0], bb[1], bb[2], bb[3]);
  sv.parts = genServiceParts(sv);
}
function removeService(sv) { services.delete(sv.id); svcGrid.remove(sv); netDirty = true; covDirty = true; }

// ---------- removal ----------
function removeRoad(e) {
  for (const l of [...lots.values()]) if (l.edge === e.id) removeLot(l);
  const orphans = [];
  for (const sv of services.values()) if (sv.edge === e.id) orphans.push(sv);
  removeEdgeRaw(e);
  for (const sv of orphans) { const h = nearestEdge(sv.ax, sv.ay, 30); if (h) { sv.edge = h.e.id; sv.s = h.s; } else sv.edge = 0; }
  for (const id of [e.a, e.b]) { const n = nodes.get(id); if (n && n.edges.size === 0 && !n.outside) nodes.delete(id); }
  cars = cars.filter(c => !c.route.some(seg => seg.e === e.id));
}

// ---------- connectivity (utilities flow along roads) ----------
let comps = new Map();
function computeNetworks() {
  netDirty = false;
  let cid = 0; comps = new Map();
  const seen = new Set();
  for (const n of nodes.values()) {
    if (seen.has(n.id)) continue;
    cid++;
    const comp = { id: cid, outside: false, power: 0, water: 0, pDem: 0, wDem: 0, nodes: 0 };
    comps.set(cid, comp);
    const stack = [n.id]; seen.add(n.id);
    while (stack.length) {
      const id = stack.pop(), nd = nodes.get(id); comp.nodes++;
      if (nd.outside) comp.outside = true;
      for (const eid of nd.edges) {
        const e = edges.get(eid); if (!e) continue;
        e.comp = cid;
        const o = otherNode(e, id);
        if (!seen.has(o)) { seen.add(o); stack.push(o); }
      }
    }
  }
}
function compOf(edgeId) { const e = edges.get(edgeId); return e ? comps.get(e.comp) : null; }
