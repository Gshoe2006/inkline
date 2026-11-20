// ===================== procedural buildings =====================
const PAL = {
  houseWall: [[236, 228, 214], [214, 196, 170], [196, 212, 214], [232, 214, 188], [208, 178, 158], [246, 242, 232], [188, 202, 182], [222, 204, 210]],
  houseRoof: [[168, 80, 62], [118, 74, 62], [92, 98, 108], [152, 112, 78], [72, 84, 98], [140, 64, 58]],
  aptWall: [[216, 208, 196], [186, 148, 126], [170, 176, 182], [228, 224, 216], [160, 118, 98], [204, 192, 170], [146, 156, 160]],
  comWall: [[234, 228, 218], [200, 212, 222], [242, 238, 230], [216, 192, 172], [182, 192, 202], [226, 214, 196]],
  awning: [[196, 72, 60], [58, 118, 188], [226, 168, 52], [68, 148, 98], [176, 88, 158], [40, 130, 140]],
  glass: [[106, 146, 178], [88, 118, 148], [138, 168, 188], [98, 128, 128], [158, 174, 190], [74, 100, 124]],
  indWall: [[192, 188, 178], [172, 162, 142], [150, 160, 166], [202, 192, 162], [176, 170, 160]],
  indRoof: [[128, 130, 126], [108, 118, 124], [150, 140, 120]],
  tree: [[86, 130, 62], [70, 116, 58], [104, 142, 70], [78, 124, 80]],
};
const GROUND = {
  resL: [124, 162, 88], resH: [176, 174, 168], com: [188, 184, 178], off: [166, 172, 176], ind: [164, 158, 144],
};

function mkPart(poly, z0, h, col, roof, extra) {
  const p = Object.assign({ kind: 'box', poly, z0, h, col, roof: roof || { type: 'flat', col: shadeArr(col, 0.92) } }, extra || {});
  finishPart(p);
  return p;
}
function finishPart(p) {
  const P = p.poly, [cx, cy] = polyCentroid(P);
  p.cx = cx; p.cy = cy;
  p.nrm = P.map((a, i) => {
    const b = P[(i + 1) % P.length];
    let nx = b[1] - a[1], ny = a[0] - b[0];
    const L = Math.hypot(nx, ny) || 1; nx /= L; ny /= L;
    const mx = (a[0] + b[0]) / 2 - cx, my = (a[1] + b[1]) / 2 - cy;
    if (nx * mx + ny * my < 0) { nx = -nx; ny = -ny; }
    return [nx, ny, Math.hypot(b[0] - a[0], b[1] - a[1])];
  });
}
const shadeArr = (c, k) => [c[0] * k, c[1] * k, c[2] * k];
function treePart(x, y, r, col) { return { kind: 'tree', x, y, r, h: r * 2 + 2.5, col, cx: x, cy: y, z0: 0 }; }

// footprint of a lot in its own (front, depth) frame -> world quad
function foot(lot, a0, a1, b0, b1) { return quadRect(lot.poly, a0, a1, b0, b1); }

function genBuilding(lot, zone, lv, seed) {
  const r = mulberry32(seed * 31 + lv * 977 + 7);
  const fr = lot.front, dp = lot.depth;
  const parts = [];
  let res = 0, jobs = 0, floors = 1;
  const am = (m) => clamp(m / fr, 0, 0.45);   // metres -> front fraction
  const bm = (m) => clamp(m / dp, 0, 0.9);    // metres -> depth fraction

  if (zone === 'resL') {
    const wall = pick(r, PAL.houseWall), roofC = pick(r, PAL.houseRoof);
    floors = lv >= 3 ? 2 : (r() < 0.25 + lv * 0.1 ? 2 : 1);
    const side = am(1.6 + r() * 1.5), setback = bm(3 + r() * 3);
    const hd = Math.min(dp * 0.62, 8 + lv * 1.6 + r() * 3);
    const wFrac = 1 - side * 2 - (r() < 0.5 && fr > 13 ? am(3.5) : 0);
    const left = r() < 0.5;
    const a0 = left ? side : 1 - side - wFrac, a1 = a0 + wFrac;
    const Q = foot(lot, a0, a1, setback, setback + bm(hd));
    const wh = floors * 3 + 0.4;
    const ridgeAlongFront = fr * wFrac >= hd;
    parts.push(mkPart(Q, 0, wh, wall, { type: r() < 0.6 ? 'gable' : 'hip', col: roofC, rh: 2.4 + r() * 1.4, axis: ridgeAlongFront ? 0 : 1 }, { win: { fh: 3, sp: 3.2, wc: [70, 86, 104] } }));
    // garage or porch wing
    if (fr * (1 - wFrac) > 4.5) {
      const ga0 = left ? a1 + am(0.3) : side * 0.6, ga1 = left ? 1 - side * 0.6 : a0 - am(0.3);
      if (ga1 - ga0 > 0.08) parts.push(mkPart(foot(lot, ga0, ga1, setback + bm(1.5), setback + bm(Math.min(hd, 6.5))), 0, 2.8, shadeArr(wall, 0.94), { type: 'flat', col: shadeArr(roofC, 0.9) }));
    }
    // chimney
    if (r() < 0.5) { const cq = foot(lot, a0 + wFrac * 0.7, a0 + wFrac * 0.7 + am(0.9), setback + bm(hd * 0.3), setback + bm(hd * 0.3 + 0.9)); parts.push(mkPart(cq, 0, wh + 3.4, [150, 92, 76])); }
    // garden trees
    const nT = 1 + Math.floor(r() * 3);
    for (let k = 0; k < nT; k++) { const p = quadAt(lot.poly, 0.15 + r() * 0.7, Math.min(0.95, setback + bm(hd) + 0.12 + r() * 0.25)); if (pointInPoly(p[0], p[1], lot.poly)) parts.push(treePart(p[0], p[1], 2 + r() * 1.8, pick(r, PAL.tree))); }
    res = Math.max(2, Math.round(fr * wFrac * hd * floors / 42) + lv);
  }
  else if (zone === 'resH') {
    const wall = pick(r, PAL.aptWall);
    floors = 3 + lv * 2 + Math.floor(r() * 3);
    const side = am(1.5), setback = bm(2.5 + r() * 2);
    const Q = foot(lot, side, 1 - side, setback, Math.min(0.92, setback + bm(Math.min(dp * 0.8, 14 + lv * 3))));
    const fh = 3.1, wc = [62, 78, 96];
    if (floors >= 8 && r() < 0.7) {
      const pod = 2;
      parts.push(mkPart(Q, 0, pod * fh + 0.6, shadeArr(wall, 0.9), null, { win: { fh, sp: 3.4, wc } }));
      const T = insetPoly(Q, 2.2 + r() * 1.5);
      parts.push(mkPart(T, pod * fh + 0.6, (floors - pod) * fh, wall, { type: 'flat', col: [128, 128, 126] }, { win: { fh, sp: 3, wc } }));
    } else {
      parts.push(mkPart(Q, 0, floors * fh + 0.6, wall, { type: 'flat', col: [134, 132, 128] }, { win: { fh, sp: 3, wc } }));
    }
    const top = floors * fh + 0.6;
    const sq = insetPoly(Q, Math.max(2, Math.sqrt(Math.abs(polyArea(Q))) * 0.32));
    parts.push(mkPart(sq, top, 2.6, [176, 172, 166]));
    const area = Math.abs(polyArea(Q));
    res = Math.floor(area * floors / 40);
  }
  else if (zone === 'com') {
    const wall = pick(r, PAL.comWall), aw = pick(r, PAL.awning);
    floors = 1 + Math.floor(lv * 0.8) + (r() < 0.4 ? 1 : 0);
    const Q = foot(lot, am(0.6), 1 - am(0.6), bm(1.2), Math.min(0.9, bm(1.2) + bm(Math.min(dp * 0.75, 11 + lv * 2.4))));
    const fh = 3.6, h = floors * fh + 0.8;
    parts.push(mkPart(Q, 0, h, wall, { type: 'flat', col: [150, 148, 144] }, { win: { fh, sp: 2.8, wc: [64, 84, 104], shop: true }, band: { col: aw, z0: 3.0, z1: 3.9 } }));
    // awning along the frontage
    const A = foot(lot, am(1.2), 1 - am(1.2), bm(0.1), bm(1.25));
    parts.push(mkPart(A, 2.7, 0.35, aw, { type: 'flat', col: aw }));
    // rooftop units
    for (let k = 0; k < 1 + Math.floor(r() * 3); k++) {
      const a = 0.2 + r() * 0.5, b = 0.35 + r() * 0.35;
      parts.push(mkPart(foot(lot, a, a + am(2.2), b, b + bm(2)), h, 1.4, [196, 198, 200]));
    }
    jobs = Math.max(2, Math.floor(Math.abs(polyArea(Q)) * floors / 42));
  }
  else if (zone === 'off') {
    const g = pick(r, PAL.glass);
    floors = 5 + lv * 4 + Math.floor(r() * 4);
    const fh = 3.6;
    let Q = foot(lot, am(1.8), 1 - am(1.8), bm(3), Math.min(0.9, bm(3) + bm(Math.min(dp * 0.8, 18 + lv * 2))));
    const tiers = floors > 14 ? 3 : floors > 8 ? 2 : 1;
    let z = 0, left = floors, area = Math.abs(polyArea(Q)), total = 0;
    for (let t = 0; t < tiers; t++) {
      const f = t === tiers - 1 ? left : Math.ceil(left * (0.5 + r() * 0.15));
      left -= f;
      parts.push(mkPart(Q, z, f * fh, g, { type: 'flat', col: shadeArr(g, 0.75) }, { glass: true, win: { fh, sp: 1.8, wc: shadeArr(g, 0.7) } }));
      total += Math.abs(polyArea(Q)) * f;
      z += f * fh;
      Q = insetPoly(Q, 2 + r() * 1.5);
    }
    if (r() < 0.5) { const [cx, cy] = polyCentroid(Q); parts.push(mkPart(circlePoly(cx, cy, 0.6, 6), z, 6 + r() * 8, [190, 196, 200])); }
    jobs = Math.floor(total / 26);
    void area;
  }
  else if (zone === 'ind') {
    const wall = pick(r, PAL.indWall), roofC = pick(r, PAL.indRoof);
    floors = 1;
    const Q = foot(lot, am(1.5), 1 - am(1.5), bm(4 + r() * 3), Math.min(0.9, bm(4) + bm(Math.min(dp * 0.7, 12 + lv * 3 + r() * 4))));
    const h = 6 + lv * 1.2 + r() * 3;
    parts.push(mkPart(Q, 0, h, wall, { type: r() < 0.6 ? 'saw' : 'flat', col: roofC, axis: fr > dp ? 1 : 0 }, { win: { fh: h, sp: 6, wc: [90, 104, 116], high: true } }));
    const [cx, cy] = polyCentroid(Q);
    if (r() < 0.55) { // chimney
      const p = quadAt(lot.poly, 0.75 + r() * 0.12, 0.8);
      parts.push(mkPart(circlePoly(p[0], p[1], 1.3, 10), 0, 18 + lv * 3 + r() * 6, [176, 92, 72], null, { stripe: true, smoke: true }));
    } else { // tanks
      for (let k = 0; k < 2; k++) {
        const p = quadAt(lot.poly, 0.2 + k * 0.45 + r() * 0.1, 0.86);
        if (pointInPoly(p[0], p[1], lot.poly)) parts.push(mkPart(circlePoly(p[0], p[1], 2.2, 12), 0, 7 + r() * 4, [206, 208, 204], { type: 'flat', col: [180, 182, 180] }));
      }
    }
    jobs = Math.max(4, Math.floor(Math.abs(polyArea(Q)) / 26 * (1 + lv * 0.35)));
    void cx; void cy;
  }
  let maxH = 0;
  for (const p of parts) maxH = Math.max(maxH, (p.z0 || 0) + (p.h || 0) + ((p.roof && p.roof.rh) || 0));
  return { parts, res, jobs, floors, maxH, shadow: shadowHull(parts) };
}

// shadow of all parts on the ground, cast away from the sun
const SUN = (() => { const x = 0.55, y = 0.75, L = Math.hypot(x, y); return [x / L, y / L]; })(); // shadow direction (world)
const SHADOW_K = 0.55;
function shadowHull(parts) {
  const out = [];
  for (const p of parts) {
    if (p.kind === 'tree') continue;
    const top = p.z0 + p.h + ((p.roof && p.roof.rh) || 0);
    const pts = [];
    for (const q of p.poly) { pts.push([q[0] + SUN[0] * p.z0 * SHADOW_K, q[1] + SUN[1] * p.z0 * SHADOW_K]); pts.push([q[0] + SUN[0] * top * SHADOW_K, q[1] + SUN[1] * top * SHADOW_K]); }
    out.push(convexHull(pts));
  }
  return out;
}

// ---------- service building looks ----------
function genServiceParts(sv) {
  const D = SERVICES[sv.type], r = mulberry32(sv.seed);
  const Q = sv.poly, parts = [];
  const L = { poly: Q, front: D.size[0], depth: D.size[1] };
  const f = (a0, a1, b0, b1) => quadRect(Q, a0, a1, b0, b1);
  let ground = [176, 178, 172];
  switch (sv.type) {
    case 'wind': {
      ground = [150, 176, 110];
      const [cx, cy] = polyCentroid(Q);
      parts.push(mkPart(circlePoly(cx, cy, 2.2, 8), 0, 0.8, [190, 190, 186]));
      parts.push(mkPart(circlePoly(cx, cy, 0.9, 8), 0, 34, [236, 238, 240], null, { turbine: true }));
      break;
    }
    case 'coal': {
      ground = [150, 146, 136];
      parts.push(mkPart(f(0.05, 0.6, 0.12, 0.8), 0, 14, [156, 150, 140], { type: 'saw', col: [112, 110, 106], axis: 0 }, { win: { fh: 14, sp: 5, wc: [80, 90, 100], high: true } }));
      parts.push(mkPart(f(0.62, 0.95, 0.12, 0.5), 0, 9, [140, 128, 112], null));
      const c1 = quadAt(Q, 0.75, 0.72), c2 = quadAt(Q, 0.9, 0.72);
      parts.push(mkPart(circlePoly(c1[0], c1[1], 2, 12), 0, 42, [182, 96, 76], null, { stripe: true, smoke: true }));
      parts.push(mkPart(circlePoly(c2[0], c2[1], 2, 12), 0, 38, [182, 96, 76], null, { stripe: true, smoke: true }));
      break;
    }
    case 'tower': {
      ground = [150, 176, 110];
      const [cx, cy] = polyCentroid(Q);
      parts.push(mkPart(circlePoly(cx, cy, 1.4, 10), 0, 16, [196, 196, 192]));
      parts.push(mkPart(circlePoly(cx, cy, 4.6, 14), 16, 7, [120, 160, 196], { type: 'flat', col: [150, 184, 210] }, { badge: 'drop' }));
      break;
    }
    case 'pump': {
      parts.push(mkPart(f(0.1, 0.9, 0.12, 0.62), 0, 6, [196, 206, 214], { type: 'gable', col: [70, 110, 150], rh: 2, axis: 0 }, { badge: 'drop', win: { fh: 6, sp: 4, wc: [80, 96, 112], high: true } }));
      parts.push(mkPart(f(0.4, 0.6, 0.62, 1.0), 0, 1.4, [96, 120, 140]));
      break;
    }
    case 'police': case 'fire': case 'clinic': {
      const C = { police: [[150, 168, 196], [52, 72, 120]], fire: [[214, 196, 182], [178, 52, 44]], clinic: [[242, 242, 238], [92, 168, 160]] }[sv.type];
      parts.push(mkPart(f(0.08, 0.92, 0.15, 0.72), 0, sv.type === 'clinic' ? 9.6 : 7, C[0], { type: 'flat', col: C[1] }, { badge: D.icon, win: { fh: sv.type === 'fire' ? 7 : 3.2, sp: sv.type === 'fire' ? 5 : 3, wc: [70, 86, 104] } }));
      if (sv.type === 'fire') parts.push(mkPart(f(0.75, 0.92, 0.72, 0.95), 0, 14, C[0], { type: 'flat', col: C[1] }));
      break;
    }
    case 'school': {
      ground = [146, 172, 104];
      parts.push(mkPart(f(0.05, 0.6, 0.1, 0.55), 0, 7.4, [214, 176, 136], { type: 'hip', col: [124, 70, 58], rh: 2.4, axis: 0 }, { badge: 'book', win: { fh: 3.6, sp: 3, wc: [70, 86, 104] } }));
      parts.push(mkPart(f(0.05, 0.25, 0.55, 0.92), 0, 7.4, [214, 176, 136], { type: 'flat', col: [124, 70, 58] }, { win: { fh: 3.6, sp: 3, wc: [70, 86, 104] } }));
      break;
    }
    case 'park': case 'plaza': {
      ground = [112, 166, 80];
      const n = sv.type === 'plaza' ? 18 : 7;
      for (let k = 0; k < n; k++) {
        const a = 0.08 + r() * 0.84, b = 0.12 + r() * 0.8;
        if (Math.abs(a - 0.5) < 0.1 && b < 0.7) continue;
        const p = quadAt(Q, a, b); parts.push(treePart(p[0], p[1], 2.5 + r() * 2.5, pick(r, PAL.tree)));
      }
      const c = quadAt(Q, 0.5, 0.55);
      parts.push(mkPart(circlePoly(c[0], c[1], sv.type === 'plaza' ? 4 : 2.4, 12), 0, 0.7, [200, 198, 190], { type: 'flat', col: [120, 170, 206] }));
      if (sv.type === 'plaza') parts.push(mkPart(f(0.42, 0.58, 0.05, 0.2), 0, 4, [222, 214, 196], { type: 'hip', col: [100, 120, 90], rh: 2, axis: 0 }));
      break;
    }
  }
  sv.ground = ground;
  sv.shadow = shadowHull(parts);
  void L;
  return parts;
}
