// ===================== interface & input =====================
const $ = (s) => document.querySelector(s);
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const money = (n) => (Math.round(n) < 0 ? '−$' : '$') + fmt(Math.abs(n));
const cost = (n) => Math.round(n) > 0 ? '−$' + fmt(n) : '$0';

const CATS = [
  { id: 'none', name: 'Inspect', icon: 'pointer', key: 'Escape' },
  { id: 'road', name: 'Roads', icon: 'road' },
  { id: 'zone', name: 'Zoning', icon: 'zone' },
  { id: 'util', name: 'Utilities', icon: 'bolt' },
  { id: 'svc', name: 'Services', icon: 'shield' },
  { id: 'park', name: 'Parks', icon: 'tree' },
  { id: 'doze', name: 'Bulldoze', icon: 'doze' },
  { id: 'view', name: 'Data views', icon: 'layers' },
];
const ZONE_ICONS = { resL: 'house', resH: 'apt', com: 'shop', off: 'office', ind: 'factory' };
const VIEWS = [
  { id: 'none', name: 'Plain map' }, { id: 'value', name: 'Land value' }, { id: 'traffic', name: 'Traffic' },
  { id: 'util', name: 'Power & water' }, { id: 'happy', name: 'Happiness' }, { id: 'pollution', name: 'Pollution' }, { id: 'services', name: 'Service cover' },
];

const tool = { cat: 'none', id: null, mode: 'straight', brush: 36 };
const road = { p0: null, c: null, an: null };
let hover = { x: 0, y: 0, sx: -1, sy: -1, snap: null, target: null, place: null };
let selected = null;

// ---------- palette ----------
function buildCats() {
  $('#cats').innerHTML = CATS.map(c => `<button class="cat" data-cat="${c.id}" aria-pressed="${tool.cat === c.id}" title="${c.name}">${svgIcon(c.icon)}<span>${c.name}</span></button>`).join('');
  $('#cats').querySelectorAll('.cat').forEach(b => b.onclick = () => setCat(b.dataset.cat));
}
function setCat(id) {
  if (tool.cat === id && id !== 'none') id = 'none';
  tool.cat = id; road.p0 = null; road.c = null;
  if (id === 'road') tool.id = tool.id && ROADS[tool.id] ? tool.id : 'street';
  else if (id === 'zone') tool.id = tool.id && (ZONES[tool.id] || tool.id === 'erase') ? tool.id : 'resL';
  else if (id === 'util') tool.id = tool.id && SERVICES[tool.id] && SERVICES[tool.id].cat === 'util' ? tool.id : 'wind';
  else if (id === 'svc') tool.id = tool.id && SERVICES[tool.id] && SERVICES[tool.id].cat === 'svc' ? tool.id : 'police';
  else if (id === 'park') tool.id = tool.id && SERVICES[tool.id] && SERVICES[tool.id].cat === 'park' ? tool.id : 'park';
  else tool.id = null;
  if (['road', 'zone', 'util', 'svc', 'park'].includes(id)) { const it = paletteItems(id).find(i => i.id === tool.id); if (it && it.locked) tool.id = (paletteItems(id).find(i => !i.locked) || {}).id || null; }
  buildCats(); buildPalette(); updateHint();
  canvas.classList.toggle('grab', id === 'none' || id === 'view');
}
function paletteItems(cat) {
  const m = S ? S.milestone : 0;
  if (cat === 'road') return Object.entries(ROADS).map(([id, R]) => ({ id, name: R.name, cost: `$${R.cost}/m`, icon: 'road', locked: R.unlock > m, unlock: R.unlock, title: R.desc }));
  if (cat === 'zone') return [...Object.entries(ZONES).map(([id, Z]) => ({ id, name: Z.short, cost: 'free', icon: ZONE_ICONS[id], color: Z.css, locked: Z.unlock > m, unlock: Z.unlock, title: Z.name })), { id: 'erase', name: 'Dezone', cost: 'free', icon: 'erase', title: 'Remove zoning' }];
  if (cat === 'util' || cat === 'svc' || cat === 'park') return Object.entries(SERVICES).filter(([, D]) => D.cat === cat).map(([id, D]) => ({ id, name: D.name, cost: '$' + fmt(D.cost), icon: D.icon, locked: D.unlock > m, unlock: D.unlock, title: `${D.desc}. Upkeep $${D.upkeep}/month` }));
  return [];
}
function buildPalette() {
  const P = $('#palette');
  if (!S) { P.innerHTML = ''; return; }
  const cat = tool.cat;
  let html = '';
  if (cat === 'view') {
    html = VIEWS.map(v => `<button class="tool" data-view="${v.id}" aria-pressed="${overlay === v.id}"><span class="tname">${v.name}</span></button>`).join('');
  } else {
    html = paletteItems(cat).map(it => {
      const lock = it.locked ? `Unlocks at ${MILESTONES[it.unlock].name} (${fmt(MILESTONES[it.unlock].pop)} people)` : it.title;
      const ic = it.color ? `<span style="color:${it.color}">${svgIcon(it.icon)}</span>` : svgIcon(it.icon);
      return `<button class="tool" data-id="${it.id}" aria-pressed="${tool.id === it.id}" ${it.locked ? 'disabled' : ''} title="${lock}">${ic}<span class="tname">${it.name}</span><span class="tcost">${it.locked ? 'Locked' : it.cost}</span></button>`;
    }).join('');
    if (cat === 'road') html += `<span class="sep"></span><button class="tool" data-mode="straight" aria-pressed="${tool.mode === 'straight'}" title="Straight roads (C)">${svgIcon('straight')}<span class="tname">Straight</span></button><button class="tool" data-mode="curve" aria-pressed="${tool.mode === 'curve'}" title="Curved roads: click start, bend point, end (C)">${svgIcon('curve')}<span class="tname">Curved</span></button>`;
    if (cat === 'zone') html += `<span class="sep"></span><div class="optgroup"><label for="brush">Brush ${tool.brush} m</label><input type="range" id="brush" min="12" max="120" step="4" value="${tool.brush}"></div>`;
  }
  P.innerHTML = html;
  P.querySelectorAll('[data-id]').forEach(b => b.onclick = () => { tool.id = b.dataset.id; road.p0 = null; buildPalette(); updateHint(); });
  P.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { tool.mode = b.dataset.mode; road.c = null; buildPalette(); updateHint(); });
  P.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { overlay = b.dataset.view; buildPalette(); });
  placeHint();
  const br = $('#brush'); if (br) br.oninput = () => { tool.brush = +br.value; br.previousElementSibling.textContent = `Brush ${tool.brush} m`; };
}
function updateHint() {
  const h = $('#hint');
  const msg = {
    none: 'Drag to pan · click a building or road to inspect it',
    road: tool.mode === 'curve'
      ? (road.p0 ? (road.c ? 'Click to place the end · <kbd>Esc</kbd> stop' : 'Click to set where the road bends') : 'Click to start a curved road · <kbd>C</kbd> straight')
      : (road.p0 ? 'Click to place the end · keeps chaining · <kbd>Esc</kbd> stop · <kbd>Shift</kbd> snaps the angle' : 'Click to start a road, on a junction or anywhere · <kbd>C</kbd> curved'),
    zone: tool.id === 'erase' ? 'Drag over parcels to remove zoning' : 'Drag over parcels to zone them · changing a zone replaces its building',
    util: 'Click beside a road. Power and water flow to every building on connected roads',
    svc: 'Click beside a road. The circle shows who it covers',
    park: 'Click beside a road. Parks raise land value nearby',
    doze: 'Click a building, service or road to remove it',
    view: 'Pick a data view to colour the map',
  }[tool.cat];
  h.innerHTML = msg || ''; h.hidden = !msg;
  placeHint();
}
function placeHint() { const d = $('#dock'); if (d) $('#hint').style.bottom = `calc(${d.offsetHeight + 22}px + env(safe-area-inset-bottom, 0px))`; }

// ---------- snapping ----------
function snapPoint(wx, wy, from) {
  const r = 14 / cam.zoom;
  const n = nearestNode(wx, wy, Math.max(r, 6));
  if (n) return { x: n.x, y: n.y, node: n.id };
  const h = nearestEdge(wx, wy, 10 / cam.zoom);
  if (h && h.dd < 10 / cam.zoom) return { x: h.x, y: h.y, edge: h.e.id };
  if (from && keys.Shift) {
    const dx = wx - from.x, dy = wy - from.y, L = Math.hypot(dx, dy);
    const a = Math.round(Math.atan2(dy, dx) / (Math.PI / 12)) * (Math.PI / 12);
    return { x: from.x + Math.cos(a) * L, y: from.y + Math.sin(a) * L };
  }
  return { x: wx, y: wy };
}
function roadControl(p1) {
  if (tool.mode === 'curve' && road.c) return road.c;
  if (tool.mode === 'curve' && !road.c) return [(road.p0.x + p1.x) / 2, (road.p0.y + p1.y) / 2];
  return [(road.p0.x + p1.x) / 2, (road.p0.y + p1.y) / 2];
}

// ---------- hover & preview ----------
function updateHover() {
  if (hover.sx < 0) return;
  const [wx, wy] = unproj(hover.sx, hover.sy);
  hover.x = wx; hover.y = wy; hover.target = null; hover.place = null; hover.snap = null;
  if (tool.cat === 'road') {
    hover.snap = snapPoint(wx, wy, road.p0);
    if (road.p0 && (tool.mode === 'straight' || road.c)) road.an = analyseRoad(road.p0, roadControl(hover.snap), hover.snap, tool.id);
    else road.an = null;
  } else if ((tool.cat === 'util' || tool.cat === 'svc' || tool.cat === 'park') && tool.id) {
    hover.place = servicePlacement(tool.id, wx, wy);
  } else if (tool.cat === 'doze' || tool.cat === 'none') {
    hover.target = pickTarget(wx, wy);
  }
}
function pickTarget(wx, wy) {
  for (const sv of svcGrid.query(wx - 1, wy - 1, wx + 1, wy + 1)) if (pointInPoly(wx, wy, sv.poly)) return { svc: sv };
  // buildings rise up the screen: also test the ground point a little "behind" the cursor
  for (const dz of [0, 4, 9, 16]) {
    const [qx, qy] = unproj(hover.sx, hover.sy + dz * cam.zoom * ZS);
    for (const l of lotGrid.query(qx - 1, qy - 1, qx + 1, qy + 1)) if (pointInPoly(qx, qy, l.poly) && (l.b || dz === 0)) return { lot: l };
  }
  const h = nearestEdge(wx, wy, 6 / cam.zoom);
  if (h && h.dd < 6 / cam.zoom) return { edge: h.e };
  return null;
}
function drawToolPreview() {
  if (hover.sx < 0) return;
  if (tool.cat === 'zone') {
    groundTransform(ctx);
    ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 1.5 / cam.zoom; ctx.setLineDash([6 / cam.zoom, 4 / cam.zoom]);
    ctx.beginPath(); ctx.arc(hover.x, hover.y, tool.brush, 0, TAU); ctx.stroke(); ctx.setLineDash([]);
    screenTransform(ctx); return;
  }
  if (tool.cat === 'road') {
    groundTransform(ctx);
    const sn = hover.snap;
    if (sn) { ctx.fillStyle = sn.node ? '#f0ad35' : sn.edge ? '#ffd27a' : 'rgba(255,255,255,0.85)'; ctx.beginPath(); ctx.arc(sn.x, sn.y, Math.max(2.5, 5 / cam.zoom), 0, TAU); ctx.fill(); }
    if (road.p0) {
      const R = ROADS[tool.id];
      if (tool.mode === 'curve' && !road.c) {
        ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 1.5 / cam.zoom; ctx.setLineDash([5 / cam.zoom, 4 / cam.zoom]);
        ctx.beginPath(); ctx.moveTo(road.p0.x, road.p0.y); ctx.lineTo(sn.x, sn.y); ctx.stroke(); ctx.setLineDash([]);
      } else if (road.an) {
        const ok = road.an.ok;
        ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        ctx.strokeStyle = ok ? 'rgba(240,173,53,0.55)' : 'rgba(214,64,48,0.6)'; ctx.lineWidth = R.w + 3;
        ctx.beginPath(); road.an.pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.stroke();
        ctx.strokeStyle = ok ? 'rgba(255,255,255,0.9)' : 'rgba(255,220,210,0.9)'; ctx.lineWidth = 1 / cam.zoom; ctx.stroke();
        if (road.c) { ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(road.c[0], road.c[1], 3 / cam.zoom, 0, TAU); ctx.fill(); }
        screenTransform(ctx);
        const lbl = ok ? `${fmt(road.an.len)} m · ${money(road.an.cost)}${road.an.wet > 0 ? ' · bridge' : ''}` : road.an.reason;
        label(hover.sx + 16, hover.sy + 18, lbl, ok);
        return;
      }
    }
    screenTransform(ctx); return;
  }
  if (hover.place) {
    const pl = hover.place;
    groundTransform(ctx);
    if (pl.poly) { ctx.fillStyle = pl.ok ? 'rgba(240,173,53,0.45)' : 'rgba(214,64,48,0.45)'; pathPoly(ctx, pl.poly); ctx.fill(); ctx.strokeStyle = '#fff'; ctx.lineWidth = 1 / cam.zoom; ctx.stroke(); }
    const D = SERVICES[tool.id];
    if (D.radius && pl.poly) { const c = polyCentroid(pl.poly); ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.setLineDash([8 / cam.zoom, 6 / cam.zoom]); ctx.beginPath(); ctx.arc(c[0], c[1], D.radius, 0, TAU); ctx.stroke(); ctx.setLineDash([]); }
    screenTransform(ctx);
    label(hover.sx + 16, hover.sy + 18, pl.ok ? `${D.name} · ${money(D.cost)}` : pl.reason, pl.ok);
    return;
  }
  if (hover.target && (tool.cat === 'doze' || tool.cat === 'none')) {
    const t = hover.target, red = tool.cat === 'doze';
    groundTransform(ctx);
    ctx.strokeStyle = red ? '#ec6a55' : 'rgba(255,255,255,0.9)'; ctx.fillStyle = red ? 'rgba(214,64,48,0.3)' : 'rgba(255,255,255,0.12)'; ctx.lineWidth = 2 / cam.zoom;
    if (t.edge) { ctx.lineWidth = ROADS[t.edge.type].w + 2; ctx.strokeStyle = red ? 'rgba(214,64,48,0.55)' : 'rgba(255,255,255,0.3)'; strokeEdge(ctx, t.edge); ctx.stroke(); }
    else { pathPoly(ctx, (t.lot || t.svc).poly); ctx.fill(); ctx.stroke(); }
    screenTransform(ctx);
    if (red) {
      const name = t.svc ? SERVICES[t.svc.type].name : t.lot ? (t.lot.b ? 'Building' : 'Parcel (only its building can go)') : ROADS[t.edge.type].name;
      label(hover.sx + 16, hover.sy + 18, (t.lot && !t.lot.b) ? 'Nothing to remove' : 'Remove ' + name.toLowerCase(), !(t.lot && !t.lot.b));
    }
  }
}
function label(x, y, text, ok) {
  ctx.font = '500 12px "IBM Plex Sans", sans-serif';
  const w = ctx.measureText(text).width + 14;
  x = Math.min(x, VW - w - 8);
  ctx.fillStyle = ok ? 'rgba(20,43,42,0.92)' : 'rgba(150,36,24,0.94)';
  ctx.beginPath(); ctx.roundRect ? ctx.roundRect(x, y, w, 22, 4) : ctx.rect(x, y, w, 22); ctx.fill();
  ctx.fillStyle = '#fff'; ctx.fillText(text, x + 7, y + 15);
}

// ---------- actions ----------
function roadClick() {
  const sn = hover.snap || snapPoint(hover.x, hover.y);
  if (!road.p0) { road.p0 = sn; road.c = null; updateHint(); return; }
  if (tool.mode === 'curve' && !road.c) { road.c = [sn.x, sn.y]; updateHint(); return; }
  const res = buildRoad(road.p0, roadControl(sn), sn, tool.id);
  if (!res.ok) { toast(res.reason, 'bad', 2500); return; }
  // continue from the end; in curve mode, carry the tangent so chains stay smooth
  const end = res.end;
  if (tool.mode === 'curve') {
    const c = road.c || [sn.x, sn.y];
    const dx = end.x - c[0], dy = end.y - c[1], L = Math.hypot(dx, dy) || 1;
    road.c = null; road.lastTan = [dx / L, dy / L];
  }
  road.p0 = { x: end.x, y: end.y, node: end.id };
  updateHover(); updateHint();
}
function paintZone(wx, wy) {
  const r = tool.brush;
  for (const l of lotGrid.query(wx - r, wy - r, wx + r, wy + r)) {
    if (Math.hypot(l.cx - wx, l.cy - wy) > r) continue;
    const z = tool.id === 'erase' ? null : tool.id;
    if (l.zone === z) continue;
    if (l.b && l.b.zone !== z) l.b = null;
    l.zone = z;
  }
}
function bulldoze() {
  const t = hover.target; if (!t) return;
  if (t.svc) { removeService(t.svc); toast(`${SERVICES[t.svc.type].name} removed.`); }
  else if (t.lot) { if (t.lot.b) { t.lot.b = null; covDirty = true; } }
  else if (t.edge) {
    if (t.edge.outsideHwy) { toast('This highway links you to the region. It stays.', 'bad'); return; }
    removeRoad(t.edge);
  }
  if (selected && (selected.svc === t.svc || selected.lot === t.lot || selected.edge === t.edge)) closePanel();
  updateHover();
}
function placeSvc() {
  const res = placeService(tool.id, hover.x, hover.y);
  if (!res.ok) toast(res.reason, 'bad', 2500);
  updateHover();
}

// ---------- input ----------
const keys = {};
const pointers = new Map();
let drag = null, gesture = null;
canvas.addEventListener('contextmenu', e => e.preventDefault());
canvas.addEventListener('pointerdown', e => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  hover.sx = e.clientX; hover.sy = e.clientY; updateHover();
  if (pointers.size === 2) { // start a two-finger gesture
    drag = null;
    const [a, b] = [...pointers.values()];
    gesture = { d: Math.hypot(a.x - b.x, a.y - b.y), ang: Math.atan2(b.y - a.y, b.x - a.x), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, zoom: cam.zoom, rot: cam.rot };
    return;
  }
  const panBtn = e.button === 1 || e.button === 2;
  drag = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, pan: panBtn, btn: e.button, moved: 0, rotate: e.button === 2 && e.ctrlKey };
  if (!panBtn && tool.cat === 'zone') { drag.paint = true; paintZone(hover.x, hover.y); }
});
canvas.addEventListener('pointermove', e => {
  if (pointers.has(e.pointerId)) pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (gesture && pointers.size >= 2) {
    const [a, b] = [...pointers.values()];
    const d = Math.hypot(a.x - b.x, a.y - b.y), ang = Math.atan2(b.y - a.y, b.x - a.x), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    panBy(mx - gesture.mx, my - gesture.my);
    zoomAt(mx, my, clamp(gesture.zoom * d / gesture.d, 0.15, 4) / cam.zoom);
    cam.rot = gesture.rot + (ang - gesture.ang); cam.trot = cam.rot;
    gesture.mx = mx; gesture.my = my;
    return;
  }
  hover.sx = e.clientX; hover.sy = e.clientY;
  if (drag) {
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    drag.x = e.clientX; drag.y = e.clientY;
    if (drag.paint) { updateHover(); paintZone(hover.x, hover.y); return; }
    if (drag.rotate) { cam.rot += dx * 0.006; cam.trot = cam.rot; return; }
    if (drag.pan || drag.moved > 6) { panBy(dx, dy); canvas.classList.add('grabbing'); return; }
  }
  updateHover();
});
function endPointer(e) {
  pointers.delete(e.pointerId);
  if (gesture) { if (pointers.size < 2) gesture = null; drag = null; return; }
  if (!drag) return;
  const d = drag; drag = null; canvas.classList.remove('grabbing');
  if (e.type === 'pointercancel') return;
  const click = d.moved <= 6;
  if (d.btn === 2 && click) { // right click cancels
    if (tool.cat === 'road' && road.p0) { road.p0 = null; road.c = null; updateHint(); }
    else setCat('none');
    return;
  }
  if (d.pan || !click || d.paint) return;
  hover.sx = e.clientX; hover.sy = e.clientY; updateHover();
  switch (tool.cat) {
    case 'road': roadClick(); break;
    case 'util': case 'svc': case 'park': placeSvc(); break;
    case 'doze': bulldoze(); break;
    case 'none': case 'view': select(pickTarget(hover.x, hover.y)); break;
  }
}
canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);
canvas.addEventListener('pointerleave', () => { if (!drag) hover.sx = -1; });
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  if (e.shiftKey) { cam.trot += (e.deltaY || e.deltaX) * 0.003; return; }
  zoomAt(e.clientX, e.clientY, Math.exp(-e.deltaY * 0.0016));
  updateHover();
}, { passive: false });
function panBy(dx, dy) {
  updCam();
  const a = unproj(0, 0), b = unproj(dx, dy);
  cam.x = clamp(cam.x - (b[0] - a[0]), 0, WORLD); cam.y = clamp(cam.y - (b[1] - a[1]), 0, WORLD);
  cam.tx = cam.x; cam.ty = cam.y;
}
function zoomAt(sx, sy, f) {
  updCam();
  const before = unproj(sx, sy);
  cam.zoom = clamp(cam.zoom * f, 0.15, 4); cam.tzoom = cam.zoom;
  updCam();
  const after = unproj(sx, sy);
  cam.x = clamp(cam.x + before[0] - after[0], 0, WORLD); cam.y = clamp(cam.y + before[1] - after[1], 0, WORLD);
  cam.tx = cam.x; cam.ty = cam.y;
}
window.addEventListener('keydown', e => {
  if (e.target.matches('input[type=text]')) return;
  keys[e.key.length === 1 ? e.key.toLowerCase() : e.key] = true;
  if (e.key === 'Shift') { keys.Shift = true; updateHover(); }
  if (!$('#menu').hidden || !$('#help').hidden) { if (e.key === 'Escape') { $('#menu').hidden = true; $('#help').hidden = true; } return; }
  const k = e.key.toLowerCase();
  if (e.key === 'Escape') { if (tool.cat === 'road' && road.p0) { road.p0 = null; road.c = null; updateHint(); } else if (tool.cat !== 'none') setCat('none'); else closePanel(); }
  else if (k === ' ') { e.preventDefault(); setSpeed(S.speed === 0 ? (S.prevSpeed || 1) : 0); }
  else if (k === '1' || k === '2' || k === '3') setSpeed(+k);
  else if (k === 'c' && tool.cat === 'road') { tool.mode = tool.mode === 'curve' ? 'straight' : 'curve'; road.c = null; buildPalette(); updateHint(); }
  else if (k === 'b') setCat('doze');
  else if (k === 'r' && !e.ctrlKey && !e.metaKey) setCat('road');
  else if (k === 'z' && !e.ctrlKey && !e.metaKey) setCat('zone');
  else if (k === '+' || k === '=') zoomAt(VW / 2, VH / 2, 1.25);
  else if (k === '-') zoomAt(VW / 2, VH / 2, 0.8);
});
window.addEventListener('keyup', e => { keys[e.key.length === 1 ? e.key.toLowerCase() : e.key] = false; if (e.key === 'Shift') { keys.Shift = false; updateHover(); } });
window.addEventListener('blur', () => { for (const k in keys) keys[k] = false; });

function setSpeed(v) {
  if (v === 0 && S.speed) S.prevSpeed = S.speed;
  S.speed = v;
  document.querySelectorAll('[data-speed]').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.speed === v)));
}
document.querySelectorAll('[data-speed]').forEach(b => b.onclick = () => setSpeed(+b.dataset.speed));

// ---------- panels ----------
function closePanel() { selected = null; $('#panel').hidden = true; }
function select(t) {
  if (!t || (t.lot && !t.lot.b && !t.lot.zone)) { closePanel(); return; }
  selected = t; renderPanel();
}
function meter(v, col) { return `<div class="meter"><i style="width:${clamp(v, 0, 100)}%;background:${col}"></i></div>`; }
function yesNo(ok, y = 'Yes', n = 'No') { return `<span class="pill ${ok ? 'ok' : 'no'}">${ok ? y : n}</span>`; }
function panelShell(sub, title, body) {
  return `<header><div><div class="sub">${sub}</div><h2>${title}</h2></div><button class="ibtn" id="pClose" aria-label="Close">${svgIcon('erase')}</button></header><div class="body">${body}</div>`;
}
function renderPanel() {
  const P = $('#panel');
  if (!selected) { P.hidden = true; return; }
  let html = '';
  if (selected.budget) html = budgetHtml();
  else if (selected.lot) {
    const l = selected.lot, b = l.b, Z = ZONES[b ? b.zone : l.zone];
    const covRow = (k, n) => `<dt>${n}</dt><dd>${Math.round((l.cov[k] || 0) * 100)}%</dd>`;
    if (!b) html = panelShell('Zoned parcel', Z.name, `<dl class="kv"><dt>Frontage</dt><dd>${l.front.toFixed(0)} m</dd><dt>Depth</dt><dd>${l.depth.toFixed(0)} m</dd><dt>Area</dt><dd>${fmt(l.area)} m²</dd><dt>Demand</dt><dd>${Math.round(demandFor(l.zone))}</dd></dl><p style="margin:0;font-size:13px;color:var(--ink-soft)">Something will be built here once there is demand, a road link to the region, power and water.</p>`);
    else {
      const isRes = b.zone === 'resL' || b.zone === 'resH';
      const status = b.prog < 1 ? '<span class="pill warn">Under construction</span>' : b.aband ? '<span class="pill no">Abandoned</span>' : '<span class="pill ok">Occupied</span>';
      html = panelShell(Z.name, `${Z.short} · level ${b.lv}`, `
        <div>${status}</div>
        <dl class="kv">
          <dt>${isRes ? 'Residents' : 'Jobs'}</dt><dd>${fmt(isRes ? b.res : b.jobs)}</dd>
          <dt>Floors</dt><dd>${b.floors}</dd>
          <dt>Parcel</dt><dd>${l.front.toFixed(0)} × ${l.depth.toFixed(0)} m</dd>
          <dt>Power</dt><dd>${yesNo(b.power)}</dd>
          <dt>Water</dt><dd>${yesNo(b.water)}</dd>
        </dl>
        <div class="sect">Land value ${Math.round(l.lv)}${b.lv < 5 ? ` · level ${b.lv + 1} needs ${LV_TH[b.lv + 1]}` : ' · top level'}</div>${meter(l.lv, 'var(--accent)')}
        ${isRes ? `<div class="sect">Happiness ${Math.round(l.happy)}</div>${meter(l.happy, 'var(--good)')}` : ''}
        <div class="sect">Nearby services</div>
        <dl class="kv">${covRow('police', 'Police')}${covRow('fire', 'Fire')}${covRow('clinic', 'Health')}${covRow('school', 'Education')}${covRow('park', 'Parks')}<dt>Pollution</dt><dd>${Math.round(l.poll * 100)}%</dd></dl>
        <div class="row-btns"><button class="btn danger" id="pDoze">Bulldoze building</button></div>`);
    }
  } else if (selected.svc) {
    const sv = selected.svc, D = SERVICES[sv.type], c = compOf(sv.edge);
    html = panelShell('Service building', D.name, `
      <dl class="kv">
        ${D.power ? `<dt>Supplies</dt><dd>${D.power} MW</dd>` : ''}${D.water ? `<dt>Supplies</dt><dd>${D.water} m³/h</dd>` : ''}
        ${D.radius ? `<dt>Covers</dt><dd>${D.radius} m</dd>` : ''}
        <dt>Upkeep</dt><dd>${money(D.upkeep)}/mo</dd>
        <dt>Road network</dt><dd>${c ? (c.outside ? yesNo(true, 'Linked to region') : yesNo(false, '', 'Not linked to region')) : yesNo(false, '', 'No road')}</dd>
      </dl>
      ${c && (D.power || D.water) ? `<div class="sect">This network</div><dl class="kv"><dt>Power</dt><dd>${c.pDem.toFixed(1)} / ${c.power} MW</dd><dt>Water</dt><dd>${c.wDem.toFixed(1)} / ${c.water} m³/h</dd></dl>` : ''}
      <div class="row-btns"><button class="btn danger" id="pDoze">Demolish</button></div>`);
  } else if (selected.edge) {
    const e = selected.edge; if (!edges.has(e.id)) { closePanel(); return; }
    const R = ROADS[e.type];
    const flow = e.load < 0.35 ? ['Free-flowing', 'ok'] : e.load < 0.7 ? ['Busy', 'warn'] : ['Congested', 'no'];
    html = panelShell('Road', R.name, `
      <dl class="kv"><dt>Length</dt><dd>${fmt(e.len)} m</dd><dt>Speed</dt><dd>${Math.round(R.speed * 3.6)} km/h</dd><dt>Vehicles now</dt><dd>${e.cars}</dd><dt>Traffic</dt><dd><span class="pill ${flow[1]}">${flow[0]}</span></dd><dt>Upkeep</dt><dd>${money(e.len * R.upkeep)}/mo</dd>${e.wetLen ? `<dt>Bridge</dt><dd>${fmt(e.wetLen)} m</dd>` : ''}</dl>
      ${e.outsideHwy ? '<p style="margin:0;font-size:13px;color:var(--ink-soft)">Your link to the region. New residents and goods arrive this way.</p>' : '<div class="row-btns"><button class="btn danger" id="pDoze">Remove road</button></div>'}`);
  }
  P.innerHTML = html; P.hidden = false;
  const close = $('#pClose'); if (close) close.onclick = closePanel;
  const dz = $('#pDoze'); if (dz) dz.onclick = () => { hover.target = selected; bulldoze(); closePanel(); };
  if (selected.budget) wireBudget();
}
function budgetHtml() {
  const b = monthlyBudget();
  const row = (k, n) => `<div class="tax"><label for="tax-${k}">${n}</label><input type="range" id="tax-${k}" min="0" max="25" step="1" value="${S.taxes[k]}"><span class="num" id="tv-${k}">${S.taxes[k]}%</span></div>`;
  return panelShell('City finances', 'Budget', `
    <div class="sect">Tax rates</div>
    ${row('res', 'Residential')}${row('com', 'Commercial')}${row('ind', 'Industrial')}${S.milestone >= 2 ? row('off', 'Office') : ''}
    <div class="sect">Monthly</div>
    <dl class="kv" id="budKv">${budgetRows(b)}</dl>
    <div class="sect">${S.history.length > 1 ? `Funds, last ${S.history.length} months` : 'Funds this month'}</div>
    <canvas id="spark" aria-label="Funds over time"></canvas>
    <div class="sect">Utilities</div>
    <dl class="kv" id="utilKv">${utilRows()}</dl>`);
}
function budgetRows(b) {
  return `<dt>Residential taxes</dt><dd>${money(b.inc.res)}</dd><dt>Business taxes</dt><dd>${money(b.inc.com + b.inc.ind + b.inc.off)}</dd>
    <dt>Road upkeep</dt><dd>${cost(b.exp.roads)}</dd><dt>Utilities</dt><dd>${cost(b.exp.util)}</dd><dt>Services</dt><dd>${cost(b.exp.svc)}</dd><dt>Parks</dt><dd>${cost(b.exp.park)}</dd>
    <dt><b>Net</b></dt><dd style="color:${b.net >= 0 ? 'var(--good)' : 'var(--bad)'}"><b>${b.net >= 0 ? '+' : ''}${money(b.net)}</b></dd>`;
}
function utilRows() {
  const [p, pd] = S.stats.power, [w, wd] = S.stats.water;
  return `<dt>Power</dt><dd style="color:${pd > p ? 'var(--bad)' : 'inherit'}">${pd.toFixed(1)} / ${p} MW</dd><dt>Water</dt><dd style="color:${wd > w ? 'var(--bad)' : 'inherit'}">${wd.toFixed(1)} / ${w} m³/h</dd>`;
}
function wireBudget() {
  for (const k of ['res', 'com', 'ind', 'off']) {
    const i = $('#tax-' + k); if (!i) continue;
    i.oninput = () => { S.taxes[k] = +i.value; $('#tv-' + k).textContent = i.value + '%'; $('#budKv').innerHTML = budgetRows(monthlyBudget()); };
  }
  drawSpark();
}
function drawSpark() {
  const c = $('#spark'); if (!c) return;
  const w = c.clientWidth, h = c.clientHeight, d = Math.min(2, window.devicePixelRatio || 1);
  c.width = w * d; c.height = h * d;
  const g = c.getContext('2d'); g.scale(d, d);
  const css = getComputedStyle(document.documentElement);
  const data = S.history.length ? S.history.map(x => x.money).concat([S.money]) : [S.money, S.money];
  let lo = Math.min(...data, 0), hi = Math.max(...data, 1);
  const X = i => 2 + i / (data.length - 1) * (w - 4), Y = v => h - 4 - (v - lo) / (hi - lo || 1) * (h - 10);
  g.strokeStyle = css.getPropertyValue('--rule'); g.lineWidth = 1; g.beginPath(); g.moveTo(0, Y(0)); g.lineTo(w, Y(0)); g.stroke();
  g.beginPath(); data.forEach((v, i) => i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)));
  g.strokeStyle = css.getPropertyValue('--accent'); g.lineWidth = 2; g.stroke();
  g.lineTo(X(data.length - 1), Y(lo)); g.lineTo(X(0), Y(lo)); g.closePath();
  g.globalAlpha = 0.15; g.fillStyle = css.getPropertyValue('--accent'); g.fill(); g.globalAlpha = 1;
  g.fillStyle = css.getPropertyValue('--accent'); g.beginPath(); g.arc(X(data.length - 1), Y(data[data.length - 1]), 3, 0, TAU); g.fill();
}
$('#budgetBtn').onclick = () => { if (selected && selected.budget) closePanel(); else { selected = { budget: true }; renderPanel(); } };

// ---------- toasts ----------
function toast(html, kind = '', ms = 4000) {
  const box = $('#toasts');
  while (box.children.length > 3) box.firstChild.remove();
  const t = document.createElement('div'); t.className = 'toast ' + kind; t.innerHTML = html;
  box.appendChild(t); setTimeout(() => t.remove(), ms);
}

// ---------- HUD ----------
function updateHud() {
  $('#sPop').textContent = fmt(S.pop);
  $('#sMoney').textContent = money(S.money);
  const net = $('#sNet'); net.textContent = (S.lastNet >= 0 ? '+' : '−') + fmt(Math.abs(S.lastNet)) + '/mo'; net.className = 'delta ' + (S.lastNet >= 0 ? 'pos' : 'neg');
  const J = S.jobs.com + S.jobs.ind + S.jobs.off;
  $('#sJobs').textContent = `${fmt(S.employed)} / ${fmt(J)}`;
  $('#sHappy').textContent = S.pop ? Math.round(S.happy) + '%' : '–';
  const m = Math.floor(S.tick / TPM), day = Math.floor((S.tick % TPM) / TICKS_PER_DAY) + 1;
  $('#sDate').textContent = `${day} ${MONTHS[m % 12]} Y${Math.floor(m / 12) + 1}`;
  const dset = (id, v) => { const el = $(id); const h = Math.abs(v) / 2; el.style.height = h + '%'; el.style.bottom = v >= 0 ? '50%' : (50 - h) + '%'; el.style.opacity = v >= 0 ? 1 : 0.45; };
  dset('#dRes', S.demand.res); dset('#dCom', S.demand.com); dset('#dInd', S.demand.ind); dset('#dOff', S.demand.off);
  const cur = MILESTONES[S.milestone], nx = MILESTONES[S.milestone + 1];
  $('#msName').textContent = cur.name;
  $('#msNext').textContent = nx ? `${fmt(Math.max(0, nx.pop - S.pop))} to ${nx.name}` : 'Every milestone reached';
  $('#msBar').style.width = nx ? clamp((S.pop - cur.pop) / (nx.pop - cur.pop) * 100, 0, 100) + '%' : '100%';
  $('#cityName').textContent = S.name;
  if (selected && selected.budget) { const kv = $('#budKv'); if (kv) kv.innerHTML = budgetRows(monthlyBudget()); const u = $('#utilKv'); if (u) u.innerHTML = utilRows(); }
  else if (selected && !document.activeElement.closest('#panel')) renderPanel();
}

// ---------- menu ----------
$('#menuBtn').onclick = () => { $('#cityInput').value = S.name; $('#newConfirm').hidden = true; $('#menu').hidden = false; };
$('#menuClose').onclick = () => { $('#menu').hidden = true; };
$('#cityInput').oninput = (e) => { S.name = e.target.value.trim() || 'New settlement'; };
$('#saveBtn').onclick = () => saveGame(false);
$('#helpBtn').onclick = () => { $('#menu').hidden = true; $('#help').hidden = false; };
$('#helpClose').onclick = () => { $('#help').hidden = true; };
$('#newBtn').onclick = () => { $('#newConfirm').hidden = false; };
$('#newNo').onclick = () => { $('#newConfirm').hidden = true; };
$('#newYes').onclick = () => { newCity(Math.floor(Math.random() * 1e9)); afterLoad(); $('#menu').hidden = true; saveGame(true); toast('A new map. Draw your first streets off the highway.'); };
$('#optNight').onchange = (e) => { optNight = e.target.checked; try { localStorage.setItem('wayfield.night', optNight ? '1' : '0'); } catch (err) { /* storage blocked */ } };
let optEdge = true;
$('#optEdge').onchange = (e) => { optEdge = e.target.checked; };

// ---------- founding village (first launch) ----------
function foundVillage() {
  const [sx, sy] = S.start;
  const keep = S.money; S.money = 1e9;
  const P = (x, y) => ({ x, y });
  const st = snapPoint(sx, sy);
  const mk = (a, c, b, t = 'street') => buildRoad(a, c, b, t);
  // a curving main street and a few side streets
  const r1 = mk(st, [sx + 120, sy - 90], P(sx + 300, sy - 40));
  const r2 = mk(st, [sx + 110, sy + 70], P(sx + 260, sy + 150));
  if (r1.ok && r2.ok) {
    const m1 = edgePoint(r1.edges[0], r1.edges[0].len * 0.5);
    mk({ x: m1[0], y: m1[1], edge: r1.edges[0].id }, [m1[0] + 10, m1[1] + 80], P(m1[0] + 30, m1[1] + 170));
    mk({ x: sx + 300, y: sy - 40, node: r1.end.id }, [sx + 360, sy + 40], P(sx + 330, sy + 140));
    mk(P(sx + 330, sy + 140), [sx + 300, sy + 170], { x: sx + 260, y: sy + 150, node: r2.end.id });
  }
  computeNetworks();
  // zone: housing inside, shops along the main street, industry by the highway
  for (const l of lots.values()) {
    const e = edges.get(l.edge); if (!e) continue;
    const d = Math.hypot(l.cx - sx, l.cy - sy);
    l.zone = d < 70 ? 'ind' : (hash2(l.id, 9) < 0.22 ? 'com' : 'resL');
  }
  // utilities
  const tryPlace = (type) => { for (let k = 0; k < 40; k++) { const a = k * 0.7, rr = 60 + k * 6; if (placeService(type, sx + 140 + Math.cos(a) * rr, sy + Math.sin(a) * rr).ok) return; } };
  tryPlace('wind'); tryPlace('tower'); tryPlace('wind'); tryPlace('tower');
  S.money = keep;
  computeNetworks(); updateUtilities();
  // a few households already living here
  let n = 0;
  for (const l of lots.values()) {
    if (!l.zone || n > 26) continue;
    if (hash2(l.id, 17) < 0.55) { spawnBuilding(l, l.zone, 1); l.b.prog = 1; l.b.age = Math.floor(TPM * 0.4); n++; }
  }
  for (const l of lots.values()) evalLot(l);
  updateDemand(); updateUtilities();
}

// ---------- loop ----------
let last = performance.now(), acc = 0, hudT = 0;
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now; frameT += dt;
  // keyboard pan & rotate
  const sp = 600 * dt / cam.zoom;
  let kx = 0, ky = 0;
  if (keys.w || keys.ArrowUp) ky -= 1; if (keys.s || keys.ArrowDown) ky += 1;
  if (keys.a || keys.ArrowLeft) kx -= 1; if (keys.d || keys.ArrowRight) kx += 1;
  if (optEdge && hover.sx >= 0 && !drag && document.hasFocus()) {
    if (hover.sx < 6) kx -= 1; if (hover.sx > VW - 6) kx += 1; if (hover.sy > VH - 6) ky += 1;
  }
  if (kx || ky) { panBy(-kx * sp * cam.zoom, -ky * sp * cam.zoom * TILT); updateHover(); }
  if (keys.q) cam.trot -= 1.6 * dt; if (keys.e) cam.trot += 1.6 * dt;
  cam.rot = lerp(cam.rot, cam.trot, Math.min(1, dt * 10));
  if (Math.abs(cam.rot - cam.trot) > 1e-4) updateHover();
  // simulation
  const mult = SPEEDS[S.speed];
  acc += dt * mult;
  let steps = 0;
  while (acc >= TICK_SEC && steps < 40) { simTick(); acc -= TICK_SEC; steps++; }
  if (steps >= 40) acc = 0;
  moveCars(dt * mult);
  S.tod = (S.tod + dt * mult / 240) % 1;
  render();
  hudT += dt; if (hudT > 0.25) { hudT = 0; updateHud(); }
  requestAnimationFrame(frame);
}

function afterLoad() {
  computeNetworks(); updateUtilities(); updateDemand();
  for (const l of lots.values()) evalLot(l);
  const c = S.cam || { x: S.start ? S.start[0] + 150 : WORLD / 3, y: S.start ? S.start[1] : WORLD / 2, zoom: 2.0, rot: -0.35 };
  Object.assign(cam, { x: c.x, y: c.y, tx: c.x, ty: c.y, zoom: c.zoom, tzoom: c.zoom, rot: c.rot, trot: c.rot });
  setSpeed(S.speed ?? 1);
  closePanel(); setCat('none'); buildPalette();
}
function boot(data) {
  try { optNight = localStorage.getItem('wayfield.night') !== '0'; } catch (err) { optNight = true; }
  $('#optNight').checked = optNight;
  resize(); window.addEventListener('resize', () => { resize(); placeHint(); });
  const saved = data && data.nodes ? data : loadSaved();
  let fresh = false;
  if (saved) { try { deserialize(saved); } catch (err) { console.warn('Save could not be read', err); fresh = true; } } else fresh = true;
  if (fresh) { newCity(Math.floor(Math.random() * 1e9), 'Fernmouth'); foundVillage(); }
  afterLoad();
  buildCats(); updateHud(); updateHint();
  if (fresh) $('#help').hidden = false;
  window.claude?.hot?.snapshot?.(() => { S.cam = { x: cam.x, y: cam.y, zoom: cam.zoom, rot: cam.rot }; return serialize(); });
  window.addEventListener('beforeunload', () => { S.cam = { x: cam.x, y: cam.y, zoom: cam.zoom, rot: cam.rot }; saveGame(true); });
  window.__wayfield = { S: () => S, nodes: () => nodes, edges: () => edges, lots: () => lots, services: () => services, cars: () => cars, cam, buildRoad, placeService, paintZone, tool, simTick, setCat, snapPoint };
  requestAnimationFrame(frame);
}
window.claude?.hot?.ready ? window.claude.hot.ready(boot) : boot(window.claude?.hot?.data ?? {});
