// ===================== simulation =====================
const TICKS_PER_DAY = 24, DAYS_PER_MONTH = 30, TPM = TICKS_PER_DAY * DAYS_PER_MONTH;
const TICK_SEC = 0.1; // real seconds per tick at speed 1
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const LV_TH = [0, 0, 32, 46, 60, 74]; // land value needed to reach level n
const SPEEDS = [0, 1, 3, 8];

let S = null;
let covDirty = true, cars = [];
let carCap = 320;

function freshState(seed, name) {
  return {
    seed, name: name || 'New settlement', money: 70000, tick: 0, speed: 1,
    taxes: { res: 10, com: 10, ind: 10, off: 10 },
    demand: { res: 50, com: 0, ind: 35, off: 0 },
    pop: 0, jobs: { com: 0, ind: 0, off: 0 }, workers: 0, employed: 0, happy: 50,
    milestone: 0, history: [], income: 0, expense: 0, lastNet: 0, tod: 0.35,
    stats: { power: [0, 0], water: [0, 0] }, warned: {},
  };
}

// ---------- coverage, land value, happiness ----------
function evalLot(l) {
  const cov = { police: 0, fire: 0, clinic: 0, school: 0, park: 0 };
  for (const sv of svcGrid.query(l.cx - 500, l.cy - 500, l.cx + 500, l.cy + 500)) {
    const D = SERVICES[sv.type];
    if (D.radius) {
      const d = Math.hypot(sv.cx - l.cx, sv.cy - l.cy);
      if (d < D.radius) { const key = D.cat === 'park' ? 'park' : sv.type; cov[key] = Math.max(cov[key], 1 - (d / D.radius) * 0.6); }
    }
    if (D.pollution) { const d = Math.hypot(sv.cx - l.cx, sv.cy - l.cy); if (d < D.pollution) l._p = (l._p || 0) + (1 - d / D.pollution) * 1.2; }
  }
  let poll = l._p || 0; l._p = 0;
  if (l.zone !== 'ind') {
    for (const o of lotGrid.query(l.cx - 200, l.cy - 200, l.cx + 200, l.cy + 200)) {
      if (o.zone === 'ind' && o.b && !o.b.aband) { const d = Math.hypot(o.cx - l.cx, o.cy - l.cy); if (d < 200) poll += (1 - d / 200) * (0.18 + o.b.lv * 0.06); }
    }
  }
  poll = Math.min(1.5, poll);
  const e = edges.get(l.edge);
  const noise = e ? clamp(e.load, 0, 1) * (e.type === 'avenue' ? 0.8 : 0.5) : 0;
  let lv = 22 + 13 * cov.police + 10 * cov.fire + 13 * cov.clinic + 15 * cov.school + 18 * cov.park - 42 * Math.min(1, poll) - 9 * noise;
  if (e && e.type === 'avenue' && (l.zone === 'com' || l.zone === 'off')) lv += 8;
  if (l.zone === 'ind') lv = 30 + 10 * cov.fire + 8 * cov.police + 6 * cov.clinic + (e && e.type !== 'street' ? 10 : 0) + Math.min(20, S.pop / 300);
  if (nearWater(l.cx, l.cy, 60)) lv += 6;
  l.lv = clamp(lv, 0, 100);
  l.cov = cov; l.poll = poll;
  const unemp = S.workers > 0 ? 1 - S.employed / S.workers : 0;
  let h = 60 + 10 * cov.police + 6 * cov.fire + 12 * cov.clinic + 10 * cov.school + 10 * cov.park - 30 * Math.min(1, poll) - (S.taxes.res - 10) * 2.5 - unemp * 30 - noise * 6;
  if (l.b) { if (!l.b.power) h -= 28; if (!l.b.water) h -= 28; }
  l.happy = clamp(h, 0, 100);
}

// ---------- utilities ----------
function updateUtilities() {
  for (const c of comps.values()) { c.power = 0; c.water = 0; c.pDem = 0; c.wDem = 0; }
  for (const sv of services.values()) {
    const c = compOf(sv.edge); const D = SERVICES[sv.type];
    if (!c) continue;
    if (D.power) c.power += D.power;
    if (D.water) c.water += D.water;
  }
  const blds = [];
  for (const l of lots.values()) if (l.b && !l.b.aband) {
    const c = compOf(l.edge); if (!c) { l.b.power = l.b.water = false; continue; }
    const ppl = l.b.res + l.b.jobs;
    l.b.pNeed = ppl * 0.01; l.b.wNeed = ppl * 0.02;
    c.pDem += l.b.pNeed; c.wDem += l.b.wNeed;
    blds.push([l, c]);
  }
  let tp = 0, tpd = 0, tw = 0, twd = 0;
  for (const c of comps.values()) { tp += c.power; tpd += c.pDem; tw += c.water; twd += c.wDem; }
  S.stats.power = [tp, tpd]; S.stats.water = [tw, twd];
  for (const [l, c] of blds) {
    const fp = c.pDem > 0 ? c.power / c.pDem : 1, fw = c.wDem > 0 ? c.water / c.wDem : 1;
    const hsh = hash2(l.id, 3);
    l.b.power = hsh < fp; l.b.water = hash2(l.id, 5) < fw;
  }
}

// ---------- demand ----------
function updateDemand() {
  let R = 0, Jc = 0, Ji = 0, Jo = 0, hs = 0, hw = 0;
  for (const l of lots.values()) {
    const b = l.b; if (!b || b.aband || b.prog < 1) continue;
    if (b.zone === 'resL' || b.zone === 'resH') { R += b.res; hs += l.happy * b.res; hw += b.res; }
    else if (b.zone === 'com') Jc += b.jobs; else if (b.zone === 'ind') Ji += b.jobs; else if (b.zone === 'off') Jo += b.jobs;
  }
  S.pop = R; S.jobs = { com: Jc, ind: Ji, off: Jo };
  const J = Jc + Ji + Jo, W = R * 0.52;
  S.workers = W; S.employed = Math.min(W, J);
  S.happy = hw ? hs / hw : 50;
  const t = S.taxes;
  const target = {
    res: clamp(38 + (J - W) / Math.max(60, W) * 60 - (t.res - 10) * 5 + (S.happy - 50) * 0.5, -100, 100),
    com: clamp((R * 0.13 - Jc) / Math.max(25, R * 0.13) * 100 - (t.com - 10) * 5, -100, 100),
    ind: clamp(22 + (W - J) / Math.max(40, W) * 80 - (t.ind - 10) * 5 - (S.milestone >= 2 ? 12 : 0), -100, 100),
    off: S.milestone >= 2 ? clamp((W * 0.2 - Jo) / Math.max(30, W * 0.2) * 100 - (t.off - 10) * 5, -100, 100) : 0,
  };
  for (const k in target) S.demand[k] = lerp(S.demand[k], target[k], 0.08);
}

// ---------- growth ----------
let candidates = [];
function refreshCandidates() {
  candidates = [];
  for (const l of lots.values()) {
    if (!l.zone || l.b) continue;
    const c = compOf(l.edge);
    if (!c || !c.outside || c.power <= 0 || c.water <= 0) continue;
    candidates.push(l);
  }
}
function demandFor(zone) { return S.demand[ZONES[zone].key]; }
function spawnBuilding(l, zone, lv) {
  const seed = Math.floor(Math.random() * 1e9);
  const g = genBuilding(l, zone, lv, seed);
  l.b = { zone, lv, seed, prog: 0, aband: 0, noUtil: 0, power: true, water: true, res: g.res, jobs: g.jobs, parts: g.parts, maxH: g.maxH, shadow: g.shadow, floors: g.floors, age: 0 };
}
function regen(l) { const b = l.b, g = genBuilding(l, b.zone, b.lv, b.seed); Object.assign(b, { res: g.res, jobs: g.jobs, parts: g.parts, maxH: g.maxH, shadow: g.shadow, floors: g.floors }); }
function growth() {
  if (S.tick % 12 === 0) refreshCandidates();
  const tries = 2 + Math.floor(Math.min(10, candidates.length / 40));
  for (let k = 0; k < tries && candidates.length; k++) {
    const i = Math.floor(Math.random() * candidates.length), l = candidates[i];
    if (!l.zone || l.b) { candidates.splice(i, 1); continue; }
    const d = demandFor(l.zone);
    if (d > 0 && Math.random() * 100 < d * 0.5) { spawnBuilding(l, l.zone, 1); candidates.splice(i, 1); }
  }
}

// ---------- monthly economy ----------
function monthlyBudget() {
  const t = S.taxes, j = S.jobs;
  const inc = {
    res: S.pop * 0.19 * t.res, com: j.com * 0.23 * t.com, ind: j.ind * 0.21 * t.ind, off: j.off * 0.27 * t.off,
  };
  let roadM = 0; for (const e of edges.values()) if (!e.outsideHwy) roadM += e.len * ROADS[e.type].upkeep;
  const svc = {}; for (const sv of services.values()) { const D = SERVICES[sv.type]; svc[D.cat] = (svc[D.cat] || 0) + D.upkeep; }
  const exp = { roads: roadM, util: svc.util || 0, svc: svc.svc || 0, park: svc.park || 0 };
  const I = inc.res + inc.com + inc.ind + inc.off, E = exp.roads + exp.util + exp.svc + exp.park;
  return { inc, exp, I, E, net: I - E };
}

// ---------- traffic ----------
function heapPush(h, item) { h.push(item); let i = h.length - 1; while (i > 0) { const p = (i - 1) >> 1; if (h[p][0] <= h[i][0]) break; [h[p], h[i]] = [h[i], h[p]]; i = p; } }
function heapPop(h) { const top = h[0], last = h.pop(); if (h.length) { h[0] = last; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i; if (l < h.length && h[l][0] < h[m][0]) m = l; if (r < h.length && h[r][0] < h[m][0]) m = r; if (m === i) break; [h[m], h[i]] = [h[i], h[m]]; i = m; } } return top; }
function edgeCost(e) { const R = ROADS[e.type]; return e.len / (R.speed * clamp(1.15 - e.load, 0.25, 1)); }

// from/to: {edge, s}; to may be {node}
function findRoute(from, to) {
  const fe = edges.get(from.edge); if (!fe) return null;
  const dist = new Map(), prev = new Map(), h = [];
  const vf = ROADS[fe.type].speed;
  dist.set(fe.a, from.s / vf); heapPush(h, [from.s / vf, fe.a]); prev.set(fe.a, null);
  const cb = (fe.len - from.s) / vf;
  if (!dist.has(fe.b) || cb < dist.get(fe.b)) { dist.set(fe.b, cb); heapPush(h, [cb, fe.b]); prev.set(fe.b, null); }
  let te = null, goals;
  if (to.node) goals = new Set([to.node]);
  else { te = edges.get(to.edge); if (!te) return null; goals = new Set([te.a, te.b]); }
  if (te && te.id === fe.id) return [{ e: fe.id, s0: from.s, s1: to.s }];
  const done = new Set(); let found = 0, iter = 0;
  while (h.length && iter++ < 6000) {
    const [d, n] = heapPop(h);
    if (done.has(n)) continue; done.add(n);
    if (goals.has(n)) { found++; if (found >= goals.size) break; }
    const nd = nodes.get(n); if (!nd) continue;
    for (const eid of nd.edges) {
      const e = edges.get(eid); if (!e) continue;
      const o = otherNode(e, n), nd2 = d + edgeCost(e);
      if (!dist.has(o) || nd2 < dist.get(o)) { dist.set(o, nd2); prev.set(o, [n, eid]); heapPush(h, [nd2, o]); }
    }
  }
  let goal, last = null;
  if (to.node) { if (!dist.has(to.node)) return null; goal = to.node; }
  else {
    const vt = ROADS[te.type].speed;
    const ca = dist.has(te.a) ? dist.get(te.a) + to.s / vt : Infinity, cbb = dist.has(te.b) ? dist.get(te.b) + (te.len - to.s) / vt : Infinity;
    if (ca === Infinity && cbb === Infinity) return null;
    goal = ca <= cbb ? te.a : te.b;
    last = { e: te.id, s0: goal === te.a ? 0 : te.len, s1: to.s };
  }
  const segs = [];
  let n = goal;
  while (prev.get(n)) { const [p, eid] = prev.get(n); const e = edges.get(eid); segs.push({ e: eid, s0: e.a === p ? 0 : e.len, s1: e.a === p ? e.len : 0 }); n = p; }
  segs.reverse();
  segs.unshift({ e: fe.id, s0: from.s, s1: n === fe.a ? 0 : fe.len });
  if (last) segs.push(last);
  return segs.filter(sg => Math.abs(sg.s1 - sg.s0) > 0.01);
}
const CAR_COLS = ['#d8d8d4', '#2d3a46', '#b4352c', '#e3b23c', '#3f6fb0', '#f2f2ee', '#5c6d4c', '#7a7f86', '#1d1d1f', '#9a4a8c'];
function spawnTraffic() {
  const target = Math.min(carCap, Math.floor(S.pop / 5 + (S.jobs.com + S.jobs.ind + S.jobs.off) / 8));
  if (cars.length >= target) return;
  const homes = [], work = [];
  for (const l of lots.values()) { const b = l.b; if (!b || b.aband || b.prog < 1) continue; if (b.res) homes.push(l); else if (b.jobs) work.push(l); }
  let outsideNode = null; for (const n of nodes.values()) if (n.outside) { outsideNode = n; break; }
  for (let k = 0; k < 3 && cars.length < target; k++) {
    let from, to;
    const r = Math.random();
    if (homes.length && work.length && r < 0.7) { from = pick(Math.random, homes); to = pick(Math.random, work); }
    else if (homes.length && outsideNode && r < 0.85) { from = pick(Math.random, homes); to = { node: outsideNode.id }; }
    else if ((homes.length || work.length) && outsideNode) {
      const dest = pick(Math.random, work.length && Math.random() < 0.5 ? work : (homes.length ? homes : work));
      const oe = edges.get([...outsideNode.edges][0]); if (!oe) continue;
      from = { edge: oe.id, s: oe.a === outsideNode.id ? 0 : oe.len }; to = dest;
    } else continue;
    const route = findRoute(from.edge ? from : { edge: from.edge, s: from.s }, to.node ? to : { edge: to.edge, s: to.s });
    if (!route || !route.length) continue;
    const s0 = route[0].s0;
    cars.push({ route, ri: 0, s: s0, col: CAR_COLS[Math.floor(Math.random() * CAR_COLS.length)], lane: Math.random() < 0.5 ? 0 : 1, truck: from.b && from.b.zone === 'ind' || to.b && to.b.zone === 'ind' ? Math.random() < 0.5 : false });
  }
}
function moveCars(dt) {
  for (const e of edges.values()) e.cars = 0;
  for (const c of cars) { const sg = c.route[c.ri]; const e = sg && edges.get(sg.e); if (e) e.cars++; }
  for (const e of edges.values()) {
    const cap = Math.max(1, ROADS[e.type].lanes * 2 * e.len / 16);
    e.load = lerp(e.load, e.cars / cap * 4, 0.05);
  }
  const keep = [];
  for (const c of cars) {
    const sg = c.route[c.ri], e = sg && edges.get(sg.e);
    if (!e) continue;
    const v = ROADS[e.type].speed * clamp(1.15 - e.load, 0.18, 1) * (c.truck ? 0.8 : 1);
    const dir = sg.s1 >= sg.s0 ? 1 : -1;
    c.s += dir * v * dt;
    if ((dir > 0 && c.s >= sg.s1) || (dir < 0 && c.s <= sg.s1)) {
      c.ri++;
      if (c.ri >= c.route.length) continue;
      c.s = c.route[c.ri].s0;
    }
    keep.push(c);
  }
  cars = keep;
}

// ---------- the tick ----------
let lvCursor = 0;
function simTick() {
  S.tick++;
  if (netDirty) { computeNetworks(); updateUtilities(); refreshCandidates(); }
  if (S.tick % 6 === 0) updateUtilities();
  if (S.tick % 4 === 0) updateDemand();
  // land value in round-robin batches
  const all = [...lots.values()];
  if (all.length) {
    const batch = covDirty ? all.length : Math.min(all.length, 120);
    for (let k = 0; k < batch; k++) { lvCursor = (lvCursor + 1) % all.length; evalLot(all[lvCursor]); }
    covDirty = false;
  }
  growth();
  // buildings: construction, levels, abandonment
  for (const l of all) {
    const b = l.b; if (!b) continue;
    if (b.prog < 1) { b.prog = Math.min(1, b.prog + 1 / 40); continue; }
    b.age++;
    if (b.aband) { b.aband++; if (b.aband > TPM * 1.5) l.b = null; continue; }
    if (!b.power || !b.water) b.noUtil++; else b.noUtil = Math.max(0, b.noUtil - 2);
    const lowHappy = (b.zone === 'resL' || b.zone === 'resH') && l.happy < 14;
    if (b.noUtil > TPM * 0.6 || (lowHappy && Math.random() < 0.0004)) { b.aband = 1; continue; }
    if (b.lv < 5 && b.power && b.water && l.lv >= LV_TH[b.lv + 1] && b.age > TPM * 0.5 && Math.random() < 0.0025 && demandFor(b.zone) > -40) {
      b.lv++; b.age = 0; regen(l); b.prog = 0.55;
    }
  }
  if (S.tick % 2 === 0) spawnTraffic();
  // money
  const bud = monthlyBudget();
  S.money += bud.net / TPM;
  S.income = bud.I; S.expense = bud.E; S.lastNet = bud.net;
  if (S.tick % TPM === 0) monthly();
}
function monthly() {
  S.history.push({ m: Math.floor(S.tick / TPM), money: Math.round(S.money), pop: S.pop });
  if (S.history.length > 48) S.history.shift();
  // milestones
  while (S.milestone < MILESTONES.length - 1 && S.pop >= MILESTONES[S.milestone + 1].pop) {
    S.milestone++;
    const M = MILESTONES[S.milestone];
    S.money += M.reward;
    toast(`<b>${M.name} reached.</b> $${M.reward.toLocaleString()} grant.${M.unlocks ? ' Unlocked: ' + M.unlocks + '.' : ''}`, 'good', 7000);
    buildPalette();
  }
  advise();
  saveGame(true);
}
function advise() {
  const [p, pd] = S.stats.power, [w, wd] = S.stats.water;
  const zoned = [...lots.values()].some(l => l.zone);
  let anyB = false; for (const l of lots.values()) if (l.b) { anyB = true; break; }
  if (zoned && p <= 0) note('power0', 'Nobody will move in without power. Build a wind turbine beside a connected road.');
  else if (zoned && w <= 0) note('water0', 'Nobody will move in without water. Build a water tower beside a connected road.');
  else if (pd > p * 1.02) note('powerLow', `Power shortage: ${pd.toFixed(1)} MW needed, ${p.toFixed(0)} MW supplied. Some buildings are going dark.`);
  else if (wd > w * 1.02) note('waterLow', `Water shortage: ${wd.toFixed(1)} m³/h needed, ${w.toFixed(0)} supplied.`);
  else if (anyB && S.demand.com > 60 && ![...lots.values()].some(l => l.zone === 'com')) note('com', 'Residents want shops. Zone some commercial parcels.');
  else if (S.money < 0) note('debt', 'The city is in debt. Raise taxes a little or cut services.');
}
function note(key, msg) { const last = S.warned[key] || -99; const m = Math.floor(S.tick / TPM); if (m - last >= 3) { S.warned[key] = m; toast(msg, 'bad', 7000); } }

// ---------- save / load ----------
const SAVE_KEY = 'wayfield.save.v1';
function serialize() {
  return {
    v: 1, S, nextId,
    nodes: [...nodes.values()].map(n => [n.id, +n.x.toFixed(2), +n.y.toFixed(2), n.outside ? 1 : 0]),
    edges: [...edges.values()].map(e => [e.id, e.a, e.b, +e.cx.toFixed(2), +e.cy.toFixed(2), e.type, e.outsideHwy ? 1 : 0]),
    lots: [...lots.values()].map(l => [l.id, l.poly.map(p => [+p[0].toFixed(2), +p[1].toFixed(2)]), l.edge, +l.s.toFixed(1), l.zone, l.b ? [l.b.zone, l.b.lv, l.b.seed, +l.b.prog.toFixed(2), l.b.aband, l.b.age] : null]),
    services: [...services.values()].map(s => [s.id, s.type, s.poly, s.edge, s.s, s.seed]),
  };
}
function deserialize(d) {
  nodes = new Map(); edges = new Map(); lots = new Map(); services = new Map();
  edgeGrid.clear(); lotGrid.clear(); svcGrid.clear(); cars = [];
  S = Object.assign(freshState(d.S.seed), d.S);
  genTerrain(S.seed); genTrees(S.seed);
  for (const [id, x, y, o] of d.nodes) { const n = addNode(x, y, id); n.outside = !!o; }
  for (const [id, a, b, cx, cy, type, oh] of d.edges) { const e = addEdge(nodes.get(a), nodes.get(b), cx, cy, type, id); e.outsideHwy = !!oh; for (let i = 0; i < e.n; i++) clearTreesInPoly(corridorPoly(e, i, 2), 0); }
  for (const [id, poly, edge, s, zone, b] of d.lots) {
    const e = edges.get(edge); if (!e) continue;
    const l = addLot(poly, e, s, id); l.zone = zone;
    if (b) { spawnBuilding(l, b[0], b[1]); l.b.seed = b[2]; regen(l); l.b.prog = b[3]; l.b.aband = b[4]; l.b.age = b[5] || 0; }
  }
  for (const [id, type, poly, edge, s, seed] of d.services) {
    const [cx, cy] = polyCentroid(poly);
    addServiceRec({ id, type, poly, cx, cy, edge, s, seed, ax: (poly[0][0] + poly[1][0]) / 2, ay: (poly[0][1] + poly[1][1]) / 2 });
    clearTreesInPoly(poly, 0.5);
  }
  nextId = d.nextId;
  netDirty = true; covDirty = true;
}
function saveGame(silent) {
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(serialize())); if (!silent) toast('City saved in this browser.', 'good'); }
  catch (err) { if (!silent) toast('This browser blocked saving. Your city stays open until you close the tab.', 'bad'); }
}
function loadSaved() {
  try { const raw = localStorage.getItem(SAVE_KEY); return raw ? JSON.parse(raw) : null; } catch (err) { return null; }
}

// ---------- a new map ----------
function newCity(seed, name) {
  nodes = new Map(); edges = new Map(); lots = new Map(); services = new Map();
  edgeGrid.clear(); lotGrid.clear(); svcGrid.clear(); cars = []; nextId = 1;
  S = freshState(seed, name);
  genTerrain(seed); genTrees(seed);
  // regional highway link from the west edge
  const r = mulberry32(seed + 5);
  const pts = [[0, HWY_Y + (r() - 0.5) * 80], [WORLD * 0.14, HWY_Y + (r() - 0.5) * 120], [WORLD * 0.27, HWY_Y + (r() - 0.5) * 60]];
  const n0 = addNode(pts[0][0], pts[0][1]); n0.outside = true;
  let prev = n0;
  for (let i = 1; i < pts.length; i++) {
    const n = addNode(pts[i][0], pts[i][1]);
    const mx = (prev.x + n.x) / 2, my = (prev.y + n.y) / 2 + (r() - 0.5) * 70;
    const e = addEdge(prev, n, mx, my, 'highway'); e.outsideHwy = true;
    for (let k = 0; k < e.n; k++) clearTreesInPoly(corridorPoly(e, k, 3), 0);
    prev = n;
  }
  S.start = [prev.x, prev.y];
  netDirty = true; covDirty = true;
}
