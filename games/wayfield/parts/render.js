// ===================== rendering =====================
const canvas = document.getElementById('view');
const ctx = canvas.getContext('2d');
const shadowCanvas = document.createElement('canvas');
const sctx = shadowCanvas.getContext('2d');
const TILT = 0.78, ZS = 0.92;
const cam = { x: 0, y: 0, zoom: 1.2, rot: -0.35, tx: 0, ty: 0, tzoom: 1.2, trot: -0.35 };
let DPR = 1, VW = 0, VH = 0, cosR = 1, sinR = 0, ccx = 0, ccy = 0;
let overlay = 'none', nightK = 0, frameT = 0, optNight = true;

const ICONS = {
  road: 'M8 21 10.5 3M16 21 13.5 3M12 6v2M12 11v2M12 16v2',
  zone: 'M3 7.5 10 4l2.5 7.5-7 2.8zM13.5 10.5 20.5 8l.5 9-6.5 2.5zM4 16l6.5-1.6L12 21l-7-.5z',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7z',
  drop: 'M12 2.5c-3.5 5-6.5 8.4-6.5 12A6.5 6.5 0 0 0 12 21a6.5 6.5 0 0 0 6.5-6.5c0-3.6-3-7-6.5-12z',
  shield: 'M12 2.5 4.5 5.5v5.5c0 4.8 3.2 8.8 7.5 10.5 4.3-1.7 7.5-5.7 7.5-10.5V5.5z',
  flame: 'M12 2.5c1 4 5.5 6 5.5 11.5a5.5 5.5 0 0 1-11 0c0-2.8 1.3-4.2 2.4-5.5.3 2.2 1.4 3.3 2.5 3.3 0-3.3-1-6.3.6-9.3z',
  cross: 'M9.5 3.5h5v6h6v5h-6v6h-5v-6h-6v-5h6z',
  book: 'M3.5 5h6a2.5 2.5 0 0 1 2.5 2.5V20a2 2 0 0 0-2-2H3.5zM20.5 5h-6A2.5 2.5 0 0 0 12 7.5V20a2 2 0 0 1 2-2h6.5z',
  tree: 'M12 2.5 5.5 12h3.5L6 17h5v4.5h2V17h5l-3-5h3.5z',
  wind: 'M12 11v10.5M12 11 12.8 2.8M12 11l6.8 4.2M12 11l-7.4 3.4M9 21.5h6',
  doze: 'M3.5 20.5h17M6 20.5V10l6-5 6 5v10.5M9.5 13.5l5 5M14.5 13.5l-5 5',
  layers: 'M12 3.5 2.5 8.5l9.5 5 9.5-5zM2.5 12.5l9.5 5 9.5-5M2.5 16.5l9.5 5 9.5-5',
  pointer: 'M5 3.5l13 7.5-6 1.5-2.5 6z',
  straight: 'M4.5 19.5 19.5 4.5M4.5 19.5h0M19.5 4.5h0',
  curve: 'M4.5 19.5C4.5 10 13 4.5 19.5 4.5',
  house: 'M3.5 11.5 12 4.5l8.5 7M5.5 10v10h13V10',
  apt: 'M6 21V3.5h12V21M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2M4 21h16',
  shop: 'M3.5 9.5l2-5h13l2 5M4.5 9.5V20h15V9.5M3.5 9.5h17M9.5 20v-5h5v5',
  office: 'M7 21V3.5h10V21M4 21h16M9.5 7h5M9.5 10.5h5M9.5 14h5',
  factory: 'M3.5 20.5V11l5.5 3.5V11l5.5 3.5V6l6-2.5v17zM3 20.5h18',
  erase: 'M4.5 4.5l15 15M19.5 4.5l-15 15',
  info: 'M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17zM12 10.5v6M12 7.5v.5',
};
const ICON_PATHS = {};
for (const k in ICONS) ICON_PATHS[k] = new Path2D(ICONS[k]);
const svgIcon = (k) => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[k]}"/></svg>`;

function resize() {
  DPR = Math.min(window.devicePixelRatio || 1, 2);
  VW = window.innerWidth; VH = window.innerHeight;
  canvas.width = VW * DPR; canvas.height = VH * DPR;
  shadowCanvas.width = canvas.width; shadowCanvas.height = canvas.height;
  const tb = document.getElementById('topbar');
  document.documentElement.style.setProperty('--top-h', (tb ? tb.offsetHeight : 56) + 'px');
}
function updCam() { cosR = Math.cos(cam.rot); sinR = Math.sin(cam.rot); ccx = VW / 2; ccy = VH / 2 + 20; }
function proj(x, y, z) {
  const dx = x - cam.x, dy = y - cam.y;
  return [ccx + (dx * cosR - dy * sinR) * cam.zoom, ccy + (dx * sinR + dy * cosR) * cam.zoom * TILT - z * cam.zoom * ZS];
}
function unproj(sx, sy) {
  const rx = (sx - ccx) / cam.zoom, ry = (sy - ccy) / (cam.zoom * TILT);
  return [cam.x + rx * cosR + ry * sinR, cam.y - rx * sinR + ry * cosR];
}
function groundTransform(c) {
  c.setTransform(cam.zoom * DPR, 0, 0, cam.zoom * TILT * DPR, ccx * DPR, ccy * DPR);
  c.rotate(cam.rot);
  c.translate(-cam.x, -cam.y);
}
function screenTransform(c) { c.setTransform(DPR, 0, 0, DPR, 0, 0); }
function viewBounds() {
  const extra = 120 * cam.zoom * ZS;
  const cs = [unproj(0, 0), unproj(VW, 0), unproj(0, VH + extra), unproj(VW, VH + extra)];
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of cs) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
  return [x0 - 20, y0 - 20, x1 + 20, y1 + 20];
}
const depthOf = (x, y) => (x - cam.x) * sinR + (y - cam.y) * cosR;

// colour helpers (with night tint)
let NT = [1, 1, 1];
function rgb(c, k = 1) { return `rgb(${c[0] * k * NT[0] | 0},${c[1] * k * NT[1] | 0},${c[2] * k * NT[2] | 0})`; }
function rgbMix(c, k, t, m) { // mix toward overlay colour t by m
  return `rgb(${lerp(c[0] * k, t[0], m) * NT[0] | 0},${lerp(c[1] * k, t[1], m) * NT[1] | 0},${lerp(c[2] * k, t[2], m) * NT[2] | 0})`;
}
function wallLight(nx, ny) { return 0.72 + 0.28 * Math.max(0, -(nx * SUN[0] + ny * SUN[1])) + 0.06 * (nx * -SUN[1] + ny * SUN[0]); }

// ---------- overlay colours ----------
function heat(v) { // 0..1 -> red..yellow..green
  v = clamp(v, 0, 1);
  return v < 0.5 ? [214, lerp(64, 196, v * 2), 52] : [lerp(214, 64, (v - 0.5) * 2), lerp(196, 170, (v - 0.5) * 2), lerp(52, 84, (v - 0.5) * 2)];
}
function lotOverlayColour(l) {
  switch (overlay) {
    case 'value': return heat(l.lv / 85);
    case 'pollution': return heat(1 - l.poll);
    case 'happy': return heat(l.happy / 90);
    case 'util': return !l.b ? null : (l.b.power && l.b.water ? [70, 170, 90] : !l.b.power && !l.b.water ? [200, 50, 40] : !l.b.power ? [222, 170, 40] : [60, 120, 210]);
    case 'services': { const c = l.cov || {}; const v = ((c.police || 0) + (c.fire || 0) + (c.clinic || 0) + (c.school || 0)) / 4; return heat(v * 1.3); }
  }
  return null;
}

// ---------- the frame ----------
function render() {
  updCam();
  const bnd = viewBounds();
  // day/night
  nightK = optNight ? clamp((Math.cos(S.tod * TAU) + 0.25) / 1.0, 0, 1) * 0.85 : 0;
  NT = [1 - 0.62 * nightK, 1 - 0.56 * nightK, 1 - 0.38 * nightK];

  screenTransform(ctx);
  ctx.fillStyle = '#2b3c3a'; ctx.fillRect(0, 0, VW, VH);
  groundTransform(ctx);
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(terrainCanvas, 0, 0, WORLD, WORLD);

  // lots (ground)
  const visLots = [...lotGrid.query(bnd[0], bnd[1], bnd[2], bnd[3])];
  const zoningTool = tool.cat === 'zone';
  for (const l of visLots) {
    const oc = overlay !== 'none' ? lotOverlayColour(l) : null;
    if (l.b) {
      const g = GROUND[l.b.zone];
      ctx.fillStyle = oc ? `rgba(${oc[0]},${oc[1]},${oc[2]},0.75)` : rgb(g);
    } else if (l.zone) {
      const c = ZONES[l.zone].color;
      ctx.fillStyle = oc ? `rgba(${oc[0]},${oc[1]},${oc[2]},0.6)` : `rgba(${c[0]},${c[1]},${c[2]},${zoningTool ? 0.55 : 0.38})`;
    } else if (zoningTool || overlay !== 'none') {
      ctx.fillStyle = oc ? `rgba(${oc[0]},${oc[1]},${oc[2]},0.3)` : 'rgba(255,255,255,0.16)';
    } else continue;
    pathPoly(ctx, l.poly); ctx.fill();
    if (zoningTool) { ctx.strokeStyle = 'rgba(255,255,255,0.55)'; ctx.lineWidth = 0.5; ctx.stroke(); }
    else if (l.b && cam.zoom > 0.8) { ctx.strokeStyle = 'rgba(0,0,0,0.12)'; ctx.lineWidth = 0.4; ctx.stroke(); }
  }
  // service grounds
  const visSvc = [...svcGrid.query(bnd[0], bnd[1], bnd[2], bnd[3])];
  for (const sv of visSvc) {
    ctx.fillStyle = rgb(sv.ground || [176, 178, 172]); pathPoly(ctx, sv.poly); ctx.fill();
    if (sv.type === 'park' || sv.type === 'plaza') { // gravel paths and a hedge line
      const Q = sv.poly, a = quadAt(Q, 0.5, 0), b = quadAt(Q, 0.5, 1), c = quadAt(Q, 0, 0.55), d = quadAt(Q, 1, 0.55);
      ctx.strokeStyle = rgb([214, 202, 168]); ctx.lineWidth = sv.type === 'plaza' ? 2.4 : 1.6; ctx.lineCap = 'butt';
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.moveTo(c[0], c[1]); ctx.lineTo(d[0], d[1]); ctx.stroke();
      ctx.strokeStyle = rgb([84, 128, 66]); ctx.lineWidth = 1; pathPoly(ctx, Q); ctx.stroke();
    }
  }

  drawRoads(bnd);
  if (overlay === 'services' || (tool.cat === 'svc' || tool.cat === 'park')) drawCoverage(visSvc);

  // shadows into an offscreen layer
  sctx.setTransform(1, 0, 0, 1, 0, 0); sctx.clearRect(0, 0, shadowCanvas.width, shadowCanvas.height);
  groundTransform(sctx); sctx.fillStyle = '#000';
  for (const l of visLots) if (l.b) { const k = l.b.prog; for (const hpoly of l.b.shadow) { if (k >= 1) pathPoly(sctx, hpoly); else continue; sctx.fill(); } }
  for (const sv of visSvc) for (const hpoly of sv.shadow) { pathPoly(sctx, hpoly); sctx.fill(); }
  const visTrees = [];
  for (const t of treeGrid.query(bnd[0], bnd[1], bnd[2], bnd[3])) { visTrees.push(t); sctx.beginPath(); sctx.ellipse(t.x + SUN[0] * t.h * SHADOW_K * 0.8, t.y + SUN[1] * t.h * SHADOW_K * 0.8, t.r * 1.05, t.r * 1.05, 0, 0, TAU); sctx.fill(); }
  for (const l of visLots) if (l.b) for (const p of l.b.parts) if (p.kind === 'tree') { sctx.beginPath(); sctx.arc(p.x + SUN[0] * p.h * SHADOW_K * 0.8, p.y + SUN[1] * p.h * SHADOW_K * 0.8, p.r, 0, TAU); sctx.fill(); }
  for (const sv of visSvc) for (const p of sv.parts) if (p.kind === 'tree') { sctx.beginPath(); sctx.arc(p.x + SUN[0] * p.h * SHADOW_K * 0.8, p.y + SUN[1] * p.h * SHADOW_K * 0.8, p.r, 0, TAU); sctx.fill(); }
  screenTransform(ctx); ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 0.2 * (1 - nightK * 0.7); ctx.drawImage(shadowCanvas, 0, 0); ctx.globalAlpha = 1;

  drawCars(bnd);

  // night over the ground
  if (nightK > 0) { screenTransform(ctx); ctx.fillStyle = `rgba(14,24,52,${0.5 * nightK})`; ctx.fillRect(0, 0, VW, VH); }

  // standing objects, back to front
  screenTransform(ctx);
  const items = [];
  for (const t of visTrees) items.push([depthOf(t.x, t.y), 0, t]);
  for (const l of visLots) if (l.b) for (const p of l.b.parts) items.push([depthOf(p.cx, p.cy) + p.z0 * 0.01, 1, p, l]);
  for (const sv of visSvc) for (const p of sv.parts) items.push([depthOf(p.cx, p.cy) + p.z0 * 0.01, 2, p, sv]);
  items.sort((a, b) => a[0] - b[0]);
  const showWin = cam.zoom > 0.55;
  for (const it of items) {
    if (it[1] === 0) drawTree(it[2].x, it[2].y, it[2].r, it[2].h, PAL.tree[it[2].c]);
    else if (it[2].kind === 'tree') drawTree(it[2].x, it[2].y, it[2].r, it[2].h, it[2].col);
    else if (it[1] === 1) {
      const l = it[3], b = l.b;
      const oc = overlay !== 'none' ? lotOverlayColour(l) : null;
      drawPart(it[2], { prog: b.prog, aband: b.aband, dark: !b.power, tint: oc, seed: b.seed, showWin, sel: selected && selected.lot === l });
    } else {
      drawPart(it[2], { prog: 1, seed: it[3].seed, showWin, tint: null, sel: selected && selected.svc === it[3] });
    }
  }
  // problem markers
  if (cam.zoom > 0.45) for (const l of visLots) {
    const b = l.b; if (!b || b.prog < 1) continue;
    let ic = null, col = null;
    if (b.aband) { if (cam.zoom < 0.9) continue; ic = 'doze'; col = '#6b6f73'; } else if (!b.power) { ic = 'bolt'; col = '#d8452f'; } else if (!b.water) { ic = 'drop'; col = '#2f77d8'; }
    if (ic) drawBadge(l.cx, l.cy, b.maxH + 6, ic, col, 0.9);
  }
  drawToolPreview();
}

function pathPoly(c, P) { c.beginPath(); c.moveTo(P[0][0], P[0][1]); for (let i = 1; i < P.length; i++) c.lineTo(P[i][0], P[i][1]); c.closePath(); }

// ---------- roads ----------
function strokeEdge(c, e) { c.beginPath(); c.moveTo(e.pts[0][0], e.pts[0][1]); for (let i = 1; i <= e.n; i++) c.lineTo(e.pts[i][0], e.pts[i][1]); }
function strokeRoad(e) { ctx.stroke(e.path); }
function drawRoads(bnd) {
  const vis = [...edgeGrid.query(bnd[0], bnd[1], bnd[2], bnd[3])];
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  // bridges: piers & deck shadow
  for (const e of vis) if (e.wetLen > 0) {
    ctx.strokeStyle = 'rgba(20,40,60,0.35)'; ctx.lineWidth = ROADS[e.type].w + 6;
    ctx.beginPath();
    for (let i = 0; i < e.n; i++) if (e.wet[i] || e.wet[i + 1]) { ctx.moveTo(e.pts[i][0] + 3, e.pts[i][1] + 5); ctx.lineTo(e.pts[i + 1][0] + 3, e.pts[i + 1][1] + 5); }
    ctx.stroke();
  }
  // sidewalk / curb
  for (const e of vis) { ctx.strokeStyle = rgb(e.type === 'highway' ? [150, 150, 146] : [196, 194, 186]); ctx.lineWidth = ROADS[e.type].w + (e.type === 'highway' ? 2 : 3.2); strokeRoad(e); }
  // asphalt
  for (const e of vis) {
    let col = e.type === 'highway' ? [74, 78, 84] : e.type === 'avenue' ? [84, 88, 92] : [94, 98, 102];
    ctx.strokeStyle = rgb(col); ctx.lineWidth = ROADS[e.type].w; strokeRoad(e);
  }
  // node caps so junctions read as one surface
  for (const e of vis) for (const id of [e.a, e.b]) {
    const n = nodes.get(id); if (!n || n.edges.size < 3) continue;
    let w = 0; for (const eid of n.edges) { const o = edges.get(eid); if (o) w = Math.max(w, ROADS[o.type].w); }
    ctx.fillStyle = rgb([92, 96, 100]); ctx.beginPath(); ctx.arc(n.x, n.y, w / 2 + 0.6, 0, TAU); ctx.fill();
  }
  // traffic overlay replaces markings
  if (overlay === 'traffic') {
    for (const e of vis) { const c = heat(1 - e.load); ctx.strokeStyle = `rgb(${c[0]},${c[1]},${c[2]})`; ctx.lineWidth = ROADS[e.type].w * 0.6; strokeEdge(ctx, e); ctx.stroke(); }
    return;
  }
  if (cam.zoom < 0.35) return;
  // markings (trimmed at the junctions), cached per edge until its junctions change
  for (const e of vis) {
    const m = roadMarks(e); if (!m) continue;
    if (e.type === 'street') {
      ctx.setLineDash([3, 4]); ctx.strokeStyle = rgb([236, 236, 228], 0.95); ctx.lineWidth = 0.35; ctx.stroke(m[0]); ctx.setLineDash([]);
    } else if (e.type === 'avenue') {
      ctx.strokeStyle = rgb([128, 162, 96]); ctx.lineWidth = 2.2; ctx.stroke(m[0]);
      ctx.setLineDash([3, 5]); ctx.strokeStyle = rgb([236, 236, 228], 0.9); ctx.lineWidth = 0.3; ctx.stroke(m[1]); ctx.stroke(m[2]); ctx.setLineDash([]);
    } else {
      ctx.strokeStyle = rgb([226, 190, 70]); ctx.lineWidth = 0.4; ctx.stroke(m[3]); ctx.stroke(m[4]);
      ctx.setLineDash([4, 6]); ctx.strokeStyle = rgb([236, 236, 228], 0.9); ctx.lineWidth = 0.3; ctx.stroke(m[5]); ctx.stroke(m[6]); ctx.setLineDash([]);
    }
  }
}
function roadMarks(e) {
  const A = nodes.get(e.a), B = nodes.get(e.b);
  const key = (A ? A.edges.size : 0) + ':' + (B ? B.edges.size : 0);
  if (e.markKey === key) return e.marks;
  e.markKey = key; e.marks = null;
  const trim = (n) => n && n.edges.size > 2 ? 9 : 0;
  const s0 = trim(A), s1 = e.len - trim(B);
  if (s1 - s0 < 4) return null;
  const line = (off) => {
    const P = new Path2D(); let first = true;
    for (let s = s0; s <= s1 + 0.01; s += 4) {
      const p = edgePoint(e, Math.min(s, s1)); const x = p[0] - p[3] * off, y = p[1] + p[2] * off;
      if (first) { P.moveTo(x, y); first = false; } else P.lineTo(x, y);
    }
    return P;
  };
  e.marks = e.type === 'street' ? [line(0)] : e.type === 'avenue' ? [line(0), line(4.4), line(-4.4)] : [null, null, null, line(0.8), line(-0.8), line(6), line(-6)];
  return e.marks;
}

function drawCoverage(visSvc) {
  for (const sv of services.values()) {
    const D = SERVICES[sv.type]; if (!D.radius) continue;
    if (tool.cat === 'svc' || tool.cat === 'park') { if (!tool.id || D.cat !== SERVICES[tool.id].cat) continue; }
    ctx.fillStyle = 'rgba(255,255,255,0.10)'; ctx.strokeStyle = 'rgba(255,255,255,0.55)'; ctx.lineWidth = 1.2 / cam.zoom;
    ctx.beginPath(); ctx.arc(sv.cx, sv.cy, D.radius, 0, TAU); ctx.fill(); ctx.stroke();
  }
  void visSvc;
}

// ---------- cars ----------
function drawCars(bnd) {
  if (cam.zoom < 0.22) return;
  groundTransform(ctx);
  const big = cam.zoom > 0.7;
  for (const c of cars) {
    const sg = c.route[c.ri], e = sg && edges.get(sg.e); if (!e) continue;
    const p = edgePoint(e, c.s); const dir = sg.s1 >= sg.s0 ? 1 : -1;
    const tx = p[2] * dir, ty = p[3] * dir;
    const R = ROADS[e.type];
    const off = R.lanes === 1 ? R.w * 0.22 : (c.lane ? R.w * 0.36 : R.w * 0.16) + (e.type === 'avenue' ? 0.6 : 0);
    const x = p[0] - ty * off, y = p[1] + tx * off;
    if (x < bnd[0] || x > bnd[2] || y < bnd[1] || y > bnd[3]) continue;
    const L = c.truck ? 3.6 : 2.2, W = c.truck ? 1.25 : 1;
    ctx.fillStyle = c.col;
    if (!big) { ctx.fillRect(x - 1.3, y - 1.3, 2.6, 2.6); continue; }
    ctx.beginPath();
    ctx.moveTo(x + tx * L - ty * W, y + ty * L + tx * W); ctx.lineTo(x + tx * L + ty * W, y + ty * L - tx * W);
    ctx.lineTo(x - tx * L + ty * W, y - ty * L - tx * W); ctx.lineTo(x - tx * L - ty * W, y - ty * L + tx * W); ctx.closePath(); ctx.fill();
    if (nightK > 0.4) { ctx.fillStyle = 'rgba(255,236,170,0.9)'; ctx.beginPath(); ctx.arc(x + tx * L, y + ty * L, 0.7, 0, TAU); ctx.fill(); }
    else { ctx.fillStyle = 'rgba(30,40,50,0.45)'; ctx.fillRect(x - 0.7, y - 0.7, 1.4, 1.4); }
  }
  screenTransform(ctx);
}

// ---------- trees ----------
function drawTree(x, y, r, h, col) {
  const p = proj(x, y, h * 0.62), z = cam.zoom;
  const rr = r * z;
  if (rr < 0.6) return;
  if (z > 0.5) { const b = proj(x, y, 0); ctx.strokeStyle = rgb([96, 74, 56]); ctx.lineWidth = Math.max(1, 0.5 * z); ctx.beginPath(); ctx.moveTo(b[0], b[1]); ctx.lineTo(p[0], p[1]); ctx.stroke(); }
  ctx.fillStyle = rgb(col, 0.82);
  ctx.beginPath(); ctx.ellipse(p[0], p[1], rr, rr * 0.92, 0, 0, TAU); ctx.fill();
  if (z > 0.35) {
    ctx.fillStyle = rgb(col, 1.08);
    ctx.beginPath(); ctx.ellipse(p[0] - rr * 0.28, p[1] - rr * 0.3, rr * 0.62, rr * 0.55, 0, 0, TAU); ctx.fill();
  }
}

// ---------- buildings ----------
const WIN_LIT = [255, 214, 140];
function drawPart(p, o) {
  const prog = o.prog;
  const building = prog < 1;
  const h = p.h * (building ? Math.max(0.08, prog) : 1);
  const P = p.poly, m = P.length, z0 = p.z0 * (building ? prog : 1);
  const base = new Array(m), top = new Array(m);
  for (let i = 0; i < m; i++) { base[i] = proj(P[i][0], P[i][1], z0); top[i] = proj(P[i][0], P[i][1], z0 + h); }
  const tint = o.tint, aband = o.aband;
  const colOf = (c, k) => {
    if (building) return rgb([210, 204, 192], k);
    if (aband) { const g = (c[0] + c[1] + c[2]) / 3 * 0.75; return rgb([g, g * 0.97, g * 0.94], k); }
    return tint ? rgbMix(c, k, tint, 0.65) : rgb(c, k);
  };
  const zv = cam.zoom * ZS;
  // walls
  for (let i = 0; i < m; i++) {
    const [nx, ny, len] = p.nrm[i];
    const vy = nx * sinR + ny * cosR;
    if (vy <= 0.001) continue;
    const j = (i + 1) % m, k = wallLight(nx, ny);
    ctx.fillStyle = colOf(p.col, k);
    ctx.beginPath(); ctx.moveTo(base[i][0], base[i][1]); ctx.lineTo(base[j][0], base[j][1]); ctx.lineTo(top[j][0], top[j][1]); ctx.lineTo(top[i][0], top[i][1]); ctx.closePath(); ctx.fill();
    if (p.stripe && !building) { // red/white chimney band
      const zz = h * 0.82;
      ctx.fillStyle = colOf([236, 232, 226], k);
      ctx.beginPath(); ctx.moveTo(base[i][0], base[i][1] - zz * zv); ctx.lineTo(base[j][0], base[j][1] - zz * zv); ctx.lineTo(base[j][0], base[j][1] - (zz + h * 0.08) * zv); ctx.lineTo(base[i][0], base[i][1] - (zz + h * 0.08) * zv); ctx.fill();
    }
    if (p.band && !building) {
      ctx.fillStyle = colOf(p.band.col, k);
      ctx.beginPath(); ctx.moveTo(base[i][0], base[i][1] - p.band.z0 * zv); ctx.lineTo(base[j][0], base[j][1] - p.band.z0 * zv); ctx.lineTo(base[j][0], base[j][1] - p.band.z1 * zv); ctx.lineTo(base[i][0], base[i][1] - p.band.z1 * zv); ctx.fill();
    }
    if (building) { // scaffold lines
      ctx.strokeStyle = rgb([150, 120, 80], 0.9); ctx.lineWidth = 0.6;
      ctx.beginPath();
      for (let z = 3; z < h; z += 3) { ctx.moveTo(base[i][0], base[i][1] - z * zv); ctx.lineTo(base[j][0], base[j][1] - z * zv); }
      ctx.stroke();
      continue;
    }
    if (p.win && o.showWin && len > 2.5) drawWindows(p, base[i], base[j], len, h, z0, zv, o, i, k);
  }
  // gable end triangles are walls too
  const R = p.roof;
  if (building) { ctx.fillStyle = 'rgba(120,100,70,0.35)'; pathScreen(top); ctx.fill(); if (o.sel) outline(top); return; }
  if (!R || R.type === 'flat' || R.type === 'saw' || m !== 4 || !R.rh) {
    ctx.fillStyle = colOf(R ? R.col : p.col, 1.0);
    pathScreen(top); ctx.fill();
    if (R && R.type === 'saw' && cam.zoom > 0.4) drawSaw(p, z0 + h, colOf);
    if (p.turbine) drawRotor(p, z0 + h);
    if (p.smoke && !aband) drawSmoke(p, z0 + h);
    if (p.badge && cam.zoom > 0.35) { const c = polyCentroid(P); drawBadge(c[0], c[1], z0 + h + 0.2, p.badge, '#ffffff', 0.7, true); }
    if (o.sel) outline(top);
    return;
  }
  // pitched roofs on quads
  const ax = R.axis || 0;
  const Q = ax === 0 ? P : [P[1], P[2], P[3], P[0]];
  const zt = z0 + h, zr = zt + R.rh;
  const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  let R0 = mid(Q[0], Q[3]), R1 = mid(Q[1], Q[2]);
  if (R.type === 'hip') { const k = 0.28; const a = [lerp(R0[0], R1[0], k), lerp(R0[1], R1[1], k)], b = [lerp(R1[0], R0[0], k), lerp(R1[1], R0[1], k)]; R0 = a; R1 = b; }
  const faces = [
    { pts: [Q[0], Q[1], R1, R0], z: [zt, zt, zr, zr], e: [Q[0], Q[1]] },
    { pts: [Q[2], Q[3], R0, R1], z: [zt, zt, zr, zr], e: [Q[2], Q[3]] },
    { pts: [Q[1], Q[2], R1], z: [zt, zt, zr], e: [Q[1], Q[2]], end: true },
    { pts: [Q[3], Q[0], R0], z: [zt, zt, zr], e: [Q[3], Q[0]], end: true },
  ];
  const [pcx, pcy] = polyCentroid(P);
  for (const f of faces) {
    const a = f.e[0], b = f.e[1];
    let nx = b[1] - a[1], ny = a[0] - b[0]; const L = Math.hypot(nx, ny) || 1; nx /= L; ny /= L;
    if (nx * ((a[0] + b[0]) / 2 - pcx) + ny * ((a[1] + b[1]) / 2 - pcy) < 0) { nx = -nx; ny = -ny; }
    f.nx = nx; f.ny = ny; f.vy = nx * sinR + ny * cosR;
  }
  faces.sort((a, b) => a.vy - b.vy);
  for (const f of faces) {
    const sp = f.pts.map((q, i) => proj(q[0], q[1], f.z[i]));
    const gableWall = f.end && R.type === 'gable';
    if (gableWall && f.vy <= 0) continue;
    const k = gableWall ? wallLight(f.nx, f.ny) : 0.8 + 0.3 * Math.max(0, -(f.nx * SUN[0] + f.ny * SUN[1]));
    ctx.fillStyle = colOf(gableWall ? p.col : R.col, k);
    pathScreen(sp); ctx.fill();
    if (!gableWall && cam.zoom > 1.1) { ctx.strokeStyle = colOf(R.col, k * 0.85); ctx.lineWidth = 0.5; ctx.stroke(); }
  }
  if (o.sel) outline(top);
}
function pathScreen(sp) { ctx.beginPath(); ctx.moveTo(sp[0][0], sp[0][1]); for (let i = 1; i < sp.length; i++) ctx.lineTo(sp[i][0], sp[i][1]); ctx.closePath(); }
function outline(sp) { ctx.strokeStyle = '#f0ad35'; ctx.lineWidth = 2; pathScreen(sp); ctx.stroke(); }

function drawWindows(p, A, B, len, h, z0, zv, o, wi, k) {
  const W = p.win, fh = W.fh;
  const floors = Math.max(1, Math.floor(h / fh + 0.01));
  const cols = Math.max(1, Math.floor(len / W.sp));
  const ux = (B[0] - A[0]), uy = (B[1] - A[1]);
  const lit = nightK > 0.35 && !o.aband && !o.dark;
  const dayC = rgb(W.wc, k * (p.glass ? 1.1 : 1));
  const litPath = lit ? new Path2D() : null, dayPath = new Path2D();
  const glass = p.glass;
  for (let f = 0; f < floors; f++) {
    let zA, zB;
    if (W.high) { zA = h * 0.62; zB = h * 0.85; }
    else if (W.shop && f === 0) { zA = 0.5; zB = 2.6; }
    else { zA = f * fh + fh * (glass ? 0.12 : 0.3); zB = f * fh + fh * (glass ? 0.92 : 0.78); }
    if (zB > h) break;
    for (let c = 0; c < cols; c++) {
      const t0 = (c + (glass ? 0.06 : 0.22)) / cols, t1 = (c + (glass ? 0.94 : 0.78)) / cols;
      const x0 = A[0] + ux * t0, y0 = A[1] + uy * t0, x1 = A[0] + ux * t1, y1 = A[1] + uy * t1;
      const isLit = lit && hash2(o.seed + wi * 131 + f * 17, c) < 0.55;
      const path = isLit ? litPath : dayPath;
      path.moveTo(x0, y0 - zA * zv); path.lineTo(x1, y1 - zA * zv); path.lineTo(x1, y1 - zB * zv); path.lineTo(x0, y0 - zB * zv); path.closePath();
    }
    if (W.high) break;
  }
  ctx.fillStyle = dayC; ctx.fill(dayPath);
  if (lit) { ctx.fillStyle = `rgb(${WIN_LIT[0]},${WIN_LIT[1]},${WIN_LIT[2]})`; ctx.fill(litPath); }
  void z0;
}
function drawSaw(p, zt, colOf) {
  const P = p.poly; if (P.length !== 4) return;
  const ax = p.roof.axis || 0;
  const Q = ax === 0 ? P : [P[1], P[2], P[3], P[0]];
  const n = 5;
  ctx.fillStyle = colOf([170, 196, 210], 0.9);
  for (let i = 0; i < n; i++) {
    const t0 = (i + 0.55) / n, t1 = (i + 0.85) / n;
    const a = [lerp(Q[0][0], Q[3][0], t0), lerp(Q[0][1], Q[3][1], t0)], b = [lerp(Q[1][0], Q[2][0], t0), lerp(Q[1][1], Q[2][1], t0)];
    const c = [lerp(Q[1][0], Q[2][0], t1), lerp(Q[1][1], Q[2][1], t1)], d = [lerp(Q[0][0], Q[3][0], t1), lerp(Q[0][1], Q[3][1], t1)];
    const sp = [proj(a[0], a[1], zt + 1.2), proj(b[0], b[1], zt + 1.2), proj(c[0], c[1], zt), proj(d[0], d[1], zt)];
    pathScreen(sp); ctx.fill();
  }
}
function drawRotor(p, zt) {
  const c = proj(p.cx, p.cy, zt);
  const a0 = frameT * 1.6 + p.cx;
  ctx.strokeStyle = rgb([244, 244, 244]); ctx.lineWidth = Math.max(1, 0.7 * cam.zoom);
  ctx.beginPath();
  for (let k = 0; k < 3; k++) {
    const a = a0 + k * TAU / 3, L = 14 * cam.zoom;
    ctx.moveTo(c[0], c[1]); ctx.lineTo(c[0] + Math.cos(a) * L * 0.35, c[1] + Math.sin(a) * L);
  }
  ctx.stroke();
  ctx.fillStyle = rgb([220, 222, 224]); ctx.beginPath(); ctx.arc(c[0], c[1], Math.max(1.2, cam.zoom * 1.2), 0, TAU); ctx.fill();
}
function drawSmoke(p, zt) {
  if (cam.zoom < 0.3) return;
  for (let k = 0; k < 5; k++) {
    const t = ((frameT * 0.25 + k / 5 + p.cx * 0.01) % 1);
    const q = proj(p.cx + SUN[0] * t * 30, p.cy + SUN[1] * t * 30, zt + t * 16);
    ctx.fillStyle = `rgba(${200 * NT[0] | 0},${200 * NT[1] | 0},${200 * NT[2] | 0},${0.45 * (1 - t)})`;
    ctx.beginPath(); ctx.arc(q[0], q[1], (2 + t * 6) * cam.zoom, 0, TAU); ctx.fill();
  }
}
function drawBadge(x, y, z, icon, col, scale = 1, flat) {
  const p = proj(x, y, z), r = clamp(8 * cam.zoom, 4.5, 11) * scale;
  ctx.save();
  ctx.translate(p[0], p[1] - (flat ? 0 : r));
  ctx.fillStyle = flat ? 'rgba(20,40,40,0.72)' : col;
  ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill();
  if (!flat) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.stroke(); }
  const s = r * 1.15 / 12; ctx.scale(s, s); ctx.translate(-12, -12);
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.stroke(ICON_PATHS[icon]);
  ctx.restore();
}
