"""Colour by number, for photos and patterns, ported from index.html (cbnLab ... drawCbnAnswer).

Regions, each outlined with a number in it, and a key under the picture saying which crayon each
number means. Where the regions are is worked out on a coarse grid (150 dpi for photos, 100 for
patterns), the same in the preview and in print; numbers and the key are drawn at full resolution.

- Photos: soften the photo, pick the crayons that match it best, give each cell the nearest, smooth
  the edges, then merge regions too narrow to hold a number. The borders are traced as smooth
  vector lines, so the page prints crisp and saves as SVG.
- Patterns (mandalas, woven tiles, contours, name pages): the design is drawn again on the coarse
  grid and its enclosed white spaces become the regions. Spaces with the same shape the same
  distance from the middle (a mandala's repeated petals) share a number; neighbouring groups get
  different colours where the palette allows.

Ported line for line, so the regions match 2.x exactly from the same grid (tests/test_cbn.py). It
runs in plain Python: a photo page takes several seconds to work out, a pattern page about two.
numpy does the steps where it gives identical numbers (smoothing, nearest crayon, the palette).
"""

import math
from array import array

import numpy as np
from PySide6.QtGui import QColor, QImage, QPainter

from .box import Box

CBN_DPI, CBN_PAT_DPI = 150, 100
CRAYONS = [("White", 255, 255, 255), ("Light grey", 200, 200, 200), ("Grey", 128, 128, 128), ("Black", 30, 30, 30),
           ("Red", 210, 40, 45), ("Pink", 245, 160, 190), ("Orange", 245, 135, 40), ("Peach", 250, 205, 160),
           ("Yellow", 250, 220, 60), ("Light green", 160, 210, 110), ("Green", 50, 150, 70), ("Dark green", 30, 85, 50),
           ("Sky blue", 120, 180, 230), ("Cornflower", 95, 130, 200), ("Blue", 40, 90, 190), ("Navy", 30, 40, 90),
           ("Purple", 120, 70, 160), ("Lavender", 190, 170, 220), ("Brown", 125, 75, 40), ("Tan", 205, 170, 120),
           ("Dark brown", 70, 45, 30)]
PATTERN_COLOURS = ["Yellow", "Sky blue", "Pink", "Light green", "Orange", "Purple", "Red", "Blue", "Peach", "Green",
                   "Lavender", "Brown"]
CBN_GENS = {"mandala", "truchet", "contour", "name"}   # patterns made of closed spaces
SQRT2 = math.sqrt(2)


def _js_round(x):
    return int(math.floor(x + 0.5))


# --- colour --------------------------------------------------------------------------------------------

def lab(r, g, b):
    """sRGB 0..255 to CIE Lab, where straight-line distance roughly matches how different colours look."""
    def lin(c):
        c /= 255
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92

    def f(t):
        return math.cbrt(t) if t > 0.008856 else 7.787 * t + 16 / 116

    R, G, B = lin(r), lin(g), lin(b)
    x = f((0.4124 * R + 0.3576 * G + 0.1805 * B) / 0.9505)
    y = f(0.2126 * R + 0.7152 * G + 0.0722 * B)
    z = f((0.0193 * R + 0.1192 * G + 0.9505 * B) / 1.089)
    return (116 * y - 16, 500 * (x - y), 200 * (y - z))


def _lab_np(r, g, b):
    def lin(c):
        c = c / 255
        return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)

    def f(t):
        return np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)

    R, G, B = lin(r), lin(g), lin(b)
    x = f((0.4124 * R + 0.3576 * G + 0.1805 * B) / 0.9505)
    y = f(0.2126 * R + 0.7152 * G + 0.0722 * B)
    z = f((0.0193 * R + 0.1192 * G + 0.9505 * B) / 1.089)
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)


def dist2(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2


def palette(R, G, B, mask, k):
    """Which k crayons best match the photo: start from all of them and drop the least missed, one at a time."""
    idx = np.nonzero(mask)[0]
    r, g, b = R[idx].astype(np.float64), G[idx].astype(np.float64), B[idx].astype(np.float64)
    keys = ((r.astype(np.int64) >> 4) << 8) | ((g.astype(np.int64) >> 4) << 4) | (b.astype(np.int64) >> 4)
    uniq, first, inv = np.unique(keys, return_index=True, return_inverse=True)
    order = np.argsort(first, kind="stable")          # bins in the order they first appear, as a Map keeps them
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    binid = rank[inv]
    n = len(uniq)
    count = np.bincount(binid, minlength=n).astype(np.float64)
    sr = np.bincount(binid, weights=r, minlength=n)   # bincount adds in pixel order, as the JavaScript does
    sg = np.bincount(binid, weights=g, minlength=n)
    sb = np.bincount(binid, weights=b, minlength=n)
    labs = [lab(c[1], c[2], c[3]) for c in CRAYONS]
    dist = np.empty((n, len(CRAYONS)))
    for i in range(n):
        lb = lab(sr[i] / count[i], sg[i] / count[i], sb[i] / count[i])
        dist[i] = [dist2(lb, q) * count[i] for q in labs]
    keep = list(range(len(CRAYONS)))
    while len(keep) > max(2, k):
        drop, least = 0, math.inf
        cols = dist[:, keep]
        for a in range(len(keep)):
            m = np.min(np.delete(cols, a, axis=1), axis=1) if len(keep) > 1 else np.full(n, math.inf)
            err = float(np.cumsum(m)[-1]) if n else 0.0   # cumsum adds in order, like the JavaScript's loop
            if err < least:
                least, drop = err, a
        keep.pop(drop)
    return keep


def mode_filter(val, w, h, k):
    """Majority of the 3x3 round each cell (ties keep their own value): smooths ragged region edges."""
    V = np.asarray(val, np.int64).reshape(h, w)
    out = V.copy()
    if h < 3 or w < 3:
        return out.reshape(-1)
    inner = V[1:-1, 1:-1]
    cnt = np.empty((k,) + inner.shape, np.uint8)
    for c in range(k):                               # votes for c in each 3x3: a row sum, then a column sum
        b = (V == c).view(np.uint8)
        row = b[:, :-2] + b[:, 1:-1] + b[:, 2:]
        cnt[c] = row[:-2] + row[1:-1] + row[2:]
    top = cnt.max(axis=0)
    first = cnt.argmax(axis=0)                       # the first crayon with the most votes
    own = np.take_along_axis(cnt, np.clip(inner, 0, k - 1)[None], axis=0)[0]
    best = np.where(own == top, inner, first)
    out[1:-1, 1:-1] = np.where(inner < 0, inner, best)
    return out.reshape(-1)


# --- regions -------------------------------------------------------------------------------------------
#
# These work on whole numpy arrays but give exactly what index.html's pixel-by-pixel loops gave: the same
# region numbers, the same 32-bit distances (so the same ties), the same choices in the same order.

def components(val, w, h):
    """Regions: 4-connected cells of equal value (-1 is nothing). (label, count); label -1 for nothing.
    Regions are numbered in the order their first cell comes in a row-by-row scan, as the flood fill did."""
    V = np.asarray(val, np.int64).reshape(h, w)
    # runs: stretches of one value along a row, numbered in scan order
    start = np.ones((h, w), bool)
    start[:, 1:] = V[:, 1:] != V[:, :-1]
    run = np.cumsum(start.reshape(-1)) - 1
    nrun = int(run[-1]) + 1 if run.size else 0
    runval = V.reshape(-1)[start.reshape(-1)]
    R = run.reshape(h, w)
    # runs that touch the run below with the same value are one region
    same = (V[:-1] == V[1:]) & (V[:-1] >= 0)
    pair = np.unique(R[:-1][same] * nrun + R[1:][same])
    a, b = pair // nrun, pair % nrun
    parent = np.arange(nrun)
    while a.size:                                    # union-find: hook each root onto the smaller one
        ra, rb = parent[a], parent[b]
        keep = ra != rb
        a, b, ra, rb = a[keep], b[keep], ra[keep], rb[keep]
        if not a.size:
            break
        np.minimum.at(parent, np.maximum(ra, rb), np.minimum(ra, rb))
        while True:                                  # point every run straight at its root
            nxt = parent[parent]
            if np.array_equal(nxt, parent):
                break
            parent = nxt
    valid = runval >= 0
    roots = np.unique(parent[valid])                 # each root is its region's first run, so its first cell
    runlabel = np.full(nrun, -1, np.int64)
    runlabel[valid] = np.searchsorted(roots, parent[valid])
    return runlabel[run], len(roots)


def _waves(rows, cols, w, key):
    """The cells (rows x cols) grouped by key(y, x), in key order: cells with the same key don't depend on
    each other in a chamfer pass, so each group is done at once."""
    ys, xs = np.meshgrid(rows, cols, indexing="ij")
    k = key(ys, xs).reshape(-1)
    flat = (ys * w + xs).reshape(-1)
    order = np.argsort(k, kind="stable")
    k, flat = k[order], flat[order]
    cuts = np.flatnonzero(np.diff(k)) + 1
    return np.split(flat, cuts)


_wave_cache = {}


def distance(label, w, h):
    """Distance from each region cell to the nearest cell outside its region (two chamfer passes),
    in 32-bit floats as index.html's Float32Array: each cell is the smallest of its neighbours plus 1 or
    sqrt 2, worked out in 64 bits and stored in 32, in the same order as the JavaScript's loops."""
    L = np.asarray(label, np.int64).reshape(h, w)
    inside = L >= 0
    edge = np.zeros((h, w), bool)
    edge[0, :] = edge[-1, :] = True
    edge[:, 0] = edge[:, -1] = True
    edge[:, 1:] |= L[:, 1:] != L[:, :-1]
    edge[:, :-1] |= L[:, :-1] != L[:, 1:]
    edge[1:, :] |= L[1:, :] != L[:-1, :]
    edge[:-1, :] |= L[:-1, :] != L[1:, :]
    d = np.where(inside, np.where(edge, 1, 1e9), 0).astype(np.float32).reshape(-1)
    if h < 2 or w < 3:
        return d
    key = (w, h)
    if key not in _wave_cache:
        # forward: (y, x) needs (y, x-1) and the row above at x-1, x, x+1, all with a smaller 2y + x
        fwd = _waves(np.arange(1, h), np.arange(1, w - 1), w, lambda y, x: 2 * y + x)
        # backward: the mirror image
        bwd = _waves(np.arange(h - 2, -1, -1), np.arange(w - 2, 0, -1), w, lambda y, x: 2 * (h - 1 - y) + (w - 1 - x))
        if len(_wave_cache) > 4:
            _wave_cache.clear()
        _wave_cache[key] = (fwd, bwd)
    fwd, bwd = _wave_cache[key]
    step = np.array([1.0, 1.0, SQRT2, SQRT2])[:, None]
    for waves, offs in ((fwd, np.array([-1, -w, -w - 1, -w + 1])), (bwd, np.array([1, w, w + 1, w - 1]))):
        offs = offs[:, None]
        for i in waves:
            cur = d[i]
            todo = cur > 1
            if not todo.any():
                continue
            i, cur = i[todo], cur[todo]
            near = (d[i[None, :] + offs].astype(np.float64) + step).min(axis=0)
            d[i] = np.minimum(cur.astype(np.float64), near).astype(np.float32)
    return d


def region_info(label, n, val, w, h, d=None):
    """Per region: value c, area, coordinate sums, deepest point (x, y) and its depth r, and whether it
    touches the edge. The deepest point is the first cell, row by row, at the region's greatest depth."""
    if d is None:
        d = distance(label, w, h)
    L = np.asarray(label, np.int64).reshape(-1)
    V = np.asarray(val, np.int64).reshape(-1)
    cells = np.flatnonzero(L >= 0)
    lab = L[cells]
    xs, ys = cells % w, cells // w
    area = np.bincount(lab, minlength=n)
    sx = np.bincount(lab, weights=xs, minlength=n)
    sy = np.bincount(lab, weights=ys, minlength=n)
    border = (xs == 0) | (ys == 0) | (xs == w - 1) | (ys == h - 1)
    edge = np.bincount(lab[border], minlength=n) > 0
    c = np.full(n, -1, np.int64)
    c[lab] = V[cells]
    dc = d[cells]
    top = np.zeros(n, np.float32)
    np.maximum.at(top, lab, dc)
    deep = dc == top[lab]
    regions, first = np.unique(lab[deep], return_index=True)
    at = np.zeros(n, np.int64)
    at[regions] = cells[np.flatnonzero(deep)[first]]
    info = []
    for l, (cl, ar, x_, y_, e, r, i) in enumerate(zip(c.tolist(), area.tolist(), sx.tolist(), sy.tolist(), edge.tolist(),
                                                       top.tolist(), at.tolist())):
        info.append({"c": cl, "area": ar, "sx": int(x_), "sy": int(y_), "x": i % w if r > 0 else 0,
                     "y": i // w if r > 0 else 0, "r": r, "edge": e})
    return info


def merge(val, w, h, min_r):
    """Each region too narrow for its number joins the neighbour it shares the most border with, until none
    are left. (label, info, d): d is the distance map of the final regions, for spots()."""
    V = np.array(val, np.int64).reshape(-1)
    N = w * h
    pos = np.arange(N)
    x = pos % w
    for pas in range(13):
        label, n = components(V, w, h)
        d = distance(label, w, h)
        info = region_info(label, n, V, w, h, d)
        small = np.array([o["r"] < min_r for o in info], bool)
        if pas == 12 or not small.any():
            return label, info, d
        # every (small region, neighbour) cell edge, with where it was first met in the JavaScript's scan
        ls, ms, firsts = [], [], []
        src = (label >= 0) & small[np.maximum(label, 0)]
        for k, (off, ok) in enumerate(((-1, x > 0), (1, x < w - 1), (-w, pos >= w), (w, pos < N - w))):
            i = np.flatnonzero(src & ok)
            m = label[i + off]
            keep = (m >= 0) & (m != label[i])
            ls.append(label[i][keep])
            ms.append(m[keep])
            firsts.append(i[keep] * 4 + k)
        l, m, first = np.concatenate(ls), np.concatenate(ms), np.concatenate(firsts)
        to = np.full(n, -1, np.int64)
        if l.size:
            order = np.argsort(first, kind="stable")
            l, m, first = l[order], m[order], first[order]
            pair, at, cnt = np.unique(l * n + m, return_index=True, return_counts=True)
            pl, pm, pf = pair // n, pair % n, first[at]
            score = cnt * np.where(small[pm], 0.3, 1.0)   # prefer a big neighbour, so two small ones don't just swap colours
            best = np.lexsort((pf, -score, pl))            # per region: highest score, then first met
            pl, pm = pl[best], pm[best]
            lead = np.ones(len(pl), bool)
            lead[1:] = pl[1:] != pl[:-1]
            cs = np.array([o["c"] for o in info], np.int64)
            to[pl[lead]] = cs[pm[lead]]
        t = np.where(label >= 0, to[np.maximum(label, 0)], -1)
        change = (t >= 0) & (t != V)
        if not change.any():
            return label, info, d
        V[change] = t[change]


def spots(label, info, w, h, min_r, gap, d=None):
    """Where numbers go: each region's deepest point, then more wherever it's still wide enough (ridge
    points of the distance map) and at least gap from its other numbers. [(region, x, y, depth)]."""
    if d is None:
        d = distance(label, w, h)
    L = np.asarray(label, np.int64).reshape(h, w)
    D = d.reshape(h, w).astype(np.float64)          # 64-bit, so min_r is compared as the JavaScript did
    out = [[(rid, o["x"], o["y"], o["r"])] for rid, o in enumerate(info)]
    c = D[1:-1, 1:-1]
    ridge = ((L[1:-1, 1:-1] >= 0) & (c >= min_r) & (c >= D[1:-1, :-2]) & (c >= D[1:-1, 2:])
             & (c >= D[:-2, 1:-1]) & (c >= D[2:, 1:-1]))
    yy, xx = np.nonzero(ridge)
    yy, xx = yy + 1, xx + 1                          # row by row, as the JavaScript's loops
    depth = D[yy, xx]
    order = np.argsort(-depth, kind="stable")        # stable, as JavaScript's sort
    g2 = gap * gap
    for l, x, y, r in zip(L[yy, xx][order].tolist(), xx[order].tolist(), yy[order].tolist(), depth[order].tolist()):
        lst = out[l]
        if all((q[1] - x) ** 2 + (q[2] - y) ** 2 >= g2 for q in lst):
            lst.append((l, x, y, r))
    return [q for lst in out for q in lst]


def trace(label, w, h):
    """Borders between regions as smooth vector lines. Every cell edge with a different region on each
    side is a border edge; edges chain into lines that end where three or more borders meet, so smoothing
    never pulls lines apart at a junction. Each line is simplified (Douglas-Peucker) and rounded (Chaikin
    twice). Lines are flat [x0, y0, x1, y1, ...] lists in grid-corner units, rounded to 32-bit floats."""
    W = w + 1
    P = np.full((h + 2, w + 2), -1, np.int64)        # the labels with a ring of nothing round them
    P[1:-1, 1:-1] = np.asarray(label, np.int64).reshape(h, w)
    # vertical edges row by row, then horizontal ones row by row, as the JavaScript listed them
    vy, vx = np.nonzero(P[1:-1, :-1] != P[1:-1, 1:])  # x = 0..w: between cell x-1 and cell x
    hy, hx = np.nonzero(P[:-1, 1:-1] != P[1:, 1:-1])  # y = 0..h: between cell y-1 and cell y
    ev0 = np.concatenate([vy * W + vx, hy * W + hx]).tolist()
    ev1 = np.concatenate([(vy + 1) * W + vx, hy * W + hx + 1]).tolist()
    deg, adj = {}, {}
    for e, a in enumerate(ev0):
        for v in (a, ev1[e]):
            deg[v] = deg.get(v, 0) + 1
            adj.setdefault(v, []).append(e)
    used = bytearray(len(ev0))
    lines = []

    def walk(v, e):   # follow edges from v through vertices of degree 2
        pts = [v]
        while True:
            used[e] = 1
            v = ev1[e] if ev0[e] == v else ev0[e]
            pts.append(v)
            if deg[v] != 2:
                break
            nxt = next((f for f in adj[v] if not used[f]), None)
            if nxt is None:
                break
            e = nxt
        return [(q % W, q // W) for q in pts]

    def dp(pts, tol):   # Douglas-Peucker
        if len(pts) < 3:
            return pts
        keep = bytearray(len(pts))
        keep[0] = keep[-1] = 1
        stack = [(0, len(pts) - 1)]
        while stack:
            a, b = stack.pop()
            (ax, ay), (bx, by) = pts[a], pts[b]
            L = math.hypot(bx - ax, by - ay) or 1
            worst, far = -1, 0
            for i in range(a + 1, b):
                d = abs((bx - ax) * (ay - pts[i][1]) - (ax - pts[i][0]) * (by - ay)) / L
                if d > far:
                    far, worst = d, i
            if far > tol:
                keep[worst] = 1
                stack.append((a, worst))
                stack.append((worst, b))
        return [p for i, p in enumerate(pts) if keep[i]]

    def chaikin(pts, closed):
        n = len(pts)
        out = [] if closed else [pts[0]]
        for i in range(n if closed else n - 1):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            out.append((ax * 0.75 + bx * 0.25, ay * 0.75 + by * 0.25))
            out.append((ax * 0.25 + bx * 0.75, ay * 0.25 + by * 0.75))
        out.append(out[0] if closed else pts[n - 1])
        return out

    def emit(pts, closed):
        q = dp(pts, 0.8)
        if closed:
            q = q[:-1]
        if len(q) >= (3 if closed else 2):
            q = chaikin(q, closed)
            q = chaikin(q[:-1] if closed else q, closed)
        elif closed:
            return
        lines.append(array("f", [c for p in q for c in p]).tolist())

    for v, dg in deg.items():
        if dg != 2:
            for e in adj[v]:
                if not used[e]:
                    emit(walk(v, e), False)
    for e in range(len(ev0)):
        if not used[e]:
            emit(walk(ev0[e], e), True)   # loops with no junction on them
    return lines


# --- photos --------------------------------------------------------------------------------------------

def process_photo(D, mask, ww, wh, p):
    """The colour-by-number half of processPixels: (label, cbn) where cbn has pal (crayon indexes), colour
    (per region, an index into pal), spots and lines."""
    from .photo import gauss_blur
    N = ww * wh
    D = np.asarray(D, np.uint8).reshape(N, 4).astype(np.float64)
    al = D[:, 3] / 255
    ch = []
    for c in range(3):
        a = np.minimum(255, np.maximum(0, ((D[:, c] * al + 255 * (1 - al)) - 128) * p["ct"] + 128 + p["br"]))
        ch.append(gauss_blur(a.astype(np.float32), ww, wh, 2.4))
    R, G, B = ch
    pal = palette(R, G, B, mask, p["k"])
    pal_lab = [lab(*CRAYONS[c][1:]) for c in pal]
    L, A, Bb = _lab_np(R.astype(np.float64), G.astype(np.float64), B.astype(np.float64))
    dists = np.stack([(L - q[0]) ** 2 + (A - q[1]) ** 2 + (Bb - q[2]) ** 2 for q in pal_lab])
    val = np.where(np.asarray(mask) == 1, np.argmin(dists, axis=0), -1)   # the first nearest, as the JavaScript's loop
    for _ in range(3):
        val = mode_filter(val, ww, wh, len(pal))
    min_r = 7 + (254 - p["t"]) / 254 * 8   # narrowest region, in 1/150 in: 7 (most detail) to 15
    label, info, d = merge(val, ww, wh, min_r)
    used = sorted({o["c"] for o in info})
    renum = {c: j for j, c in enumerate(used)}   # crayons merged away leave the key
    cbn = {"pal": [pal[j] for j in used], "colour": [renum[o["c"]] for o in info],
           "spots": spots(label, info, ww, wh, min_r, 2 * 150, d), "lines": trace(label, ww, wh)}
    return label.tolist(), cbn


# --- drawing -------------------------------------------------------------------------------------------

def key_cols(w, dpi):
    return 4 if w > dpi * 5 else 3


def key_height(box, dpi, n):
    return min(box.h * 0.22, dpi * (0.42 + math.ceil(n / key_cols(box.w, dpi)) * 0.24))


def draw_numbers(ctx, pts, dpi):
    """Numbers, each centred on its region's deepest point: pts are (n, x, y, r) in page pixels, n from 1."""
    ctx.save()
    ctx.fill_style, ctx.text_align, ctx.text_baseline = "#666", "center", "alphabetic"
    for n, x, y, r in pts:
        fs = max(dpi * 0.06, min(dpi * 0.15, r * 1.2))
        ctx.set_font(fs, 500)
        ctx.fill_text(str(n), x, y + fs * 0.36)
    ctx.restore()


def draw_key(ctx, kb, names, dpi):
    """The key: a ring with each number, and the crayon it means, to try the colour in before starting."""
    cols = key_cols(kb.w, dpi)
    rows = math.ceil(len(names) / cols)
    fs = min(dpi * 0.11, kb.h / (rows * 2.2 + 2))
    r, col_w, top = fs * 0.8, kb.w / cols, kb.y + fs * 1.6
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_baseline, ctx.text_align = "alphabetic", "left"
    ctx.set_font(fs, 700)
    ctx.fill_text("Colour key", kb.x, top)
    ctx.line_width = max(1, dpi / 150)
    for i, name in enumerate(names):
        cx = kb.x + (i % cols) * col_w + r + ctx.line_width
        cy = top + fs * 0.9 + r + (i // cols) * fs * 2.2
        ctx.begin_path()
        ctx.arc(cx, cy, r, 0, math.pi * 2)
        ctx.stroke()
        ctx.text_align = "center"
        ctx.set_font(fs * 0.85, 600)
        ctx.fill_text(str(i + 1), cx, cy + fs * 0.3)
        ctx.text_align = "left"
        ctx.set_font(fs, 400)
        ctx.fill_text(name, cx + r + fs * 0.5, cy + fs * 0.35, col_w - 2 * r - fs * 1.2)
    ctx.restore()


def draw_photo(ctx, box, key_box, dpi, entry):
    """A colour-by-number photo: the traced borders, the numbers and the key."""
    cbn = entry.cbn
    if not cbn:
        return
    sx, sy = box.w / entry.ww, box.h / entry.wh
    ctx.save()
    ctx.stroke_style, ctx.line_width = "#000", 2 * sx
    ctx.line_join = ctx.line_cap = "round"
    ctx.begin_path()
    for l in cbn["lines"]:
        ctx.move_to(box.x + l[0] * sx, box.y + l[1] * sy)
        for k in range(2, len(l), 2):
            ctx.line_to(box.x + l[k] * sx, box.y + l[k + 1] * sy)
    ctx.stroke()
    ctx.restore()
    draw_numbers(ctx, [(cbn["colour"][l] + 1, box.x + (x + 0.5) * sx, box.y + (y + 0.5) * sy, r * sx)
                       for l, x, y, r in cbn["spots"]], dpi)
    draw_key(ctx, key_box, [CRAYONS[i][0] for i in cbn["pal"]], dpi)


# --- patterns ------------------------------------------------------------------------------------------

def pattern_raster(g, box, spec, lw, s):
    """The design drawn again on a 100 dpi grid: ink -1, white space 0. (val, w, h, scale)."""
    from .canvas import QtCanvas
    from .page import draw_design
    from .qt import ensure_app
    ensure_app()
    sc = CBN_PAT_DPI / g.dpi
    w, h = max(1, math.ceil(box.w * sc)), max(1, math.ceil(box.h * sc))
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(QColor("#fff"))
    p = QPainter(img)
    p.scale(sc, sc)
    p.translate(-box.x, -box.y)
    ctx = QtCanvas(p, w, h)
    ctx.stroke_style = ctx.fill_style = "#000"
    ctx.line_cap = ctx.line_join = "round"
    ctx.line_width = lw
    draw_design(ctx, g, box, spec.gen, spec.seed, spec.c, s, lw)
    p.end()
    red = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).reshape(h, img.bytesPerLine())[:, 2:w * 4:4]
    return np.where(red > 160, 0, -1).reshape(-1).tolist(), w, h, sc


_pattern_cache = {}


def pattern(g, box, spec, lw, s, raster=None):
    """Numbered spaces for a colour-by-number design: {spots: [(n, x, y, r, region)], names, label, w, h, s}."""
    k = s.cbn_colours
    key = (spec.gen, spec.seed, spec.c, lw, tuple(box), g.dpi, k, s.name_text, s.name_bg)
    if raster is None and key in _pattern_cache:
        return _pattern_cache[key]
    val, w, h, _sc = raster or pattern_raster(g, box, spec, lw, s)
    sc = CBN_PAT_DPI / g.dpi
    label, n = components(val, w, h)
    info = region_info(label, n, val, w, h)
    min_r = 0.05 * CBN_PAT_DPI   # narrower spaces get no number (and are left blank)
    for o in info:   # the big space round the design is background
        o["keep"] = o["r"] >= min_r and not (o["edge"] and o["area"] > 0.25 * w * h)
    # group repeated spaces: the same size (within 20%) and distance from the middle (within 1.2% of the diagonal)
    diag, groups, grp = math.hypot(w, h), [], [-1] * n
    for rid, o in enumerate(info):
        if not o["keep"]:
            continue
        d = math.hypot(o["sx"] / o["area"] - w / 2, o["sy"] / o["area"] - h / 2)
        gi = next((j for j, G in enumerate(groups) if abs(G["d"] - d) < diag * 0.012 and abs(math.log(o["area"] / G["a"])) < 0.2), -1)
        if gi < 0:
            gi = len(groups)
            groups.append({"d": d, "a": o["area"], "total": 0, "near": set(), "c": -1})
        grp[rid] = gi
        groups[gi]["total"] += o["area"]
    # neighbouring groups: spaces facing each other across a line
    step = math.ceil(lw * sc) + 3
    G = np.array(grp + [-1], np.int64)[label.reshape(h, w)]   # each cell's group (-1 for none; label -1 → -1)
    for a, b in ((G[:, :-step], G[:, step:]), (G[:-step], G[step:])):
        near = (a >= 0) & (b >= 0) & (a != b)
        for ga, gb in set(zip(a[near].tolist(), b[near].tolist())):
            groups[ga]["near"].add(gb)
            groups[gb]["near"].add(ga)
    use = [0.0] * k   # biggest groups first; each takes the least-used colour its neighbours don't have
    for G in sorted(groups, key=lambda G: -G["total"]):
        taken = {groups[j]["c"] for j in G["near"]}
        best = -1
        for c in range(k):
            if c not in taken and (best < 0 or use[c] < use[best]):
                best = c
        if best < 0:
            for c in range(k):
                if best < 0 or use[c] < use[best]:
                    best = c
        G["c"] = best
        use[best] += G["total"]
    used = sorted({G["c"] for G in groups})
    renum = {c: j for j, c in enumerate(used)}
    pts = [(renum[groups[grp[rid]]["c"]] + 1, box.x + (o["x"] + 0.5) / sc, box.y + (o["y"] + 0.5) / sc, o["r"] / sc, rid)
           for rid, o in enumerate(info) if o["keep"]]
    r = {"spots": pts, "names": [PATTERN_COLOURS[c] for c in used], "label": label.tolist(), "w": w, "h": h, "s": sc}
    if raster is None:
        if len(_pattern_cache) > 20:
            del _pattern_cache[next(iter(_pattern_cache))]
        _pattern_cache[key] = r
    return r


def is_cbn_design(gen, s):
    return s.cbn and gen in CBN_GENS


def art_box(box, dpi, k):
    """The design's part of a colour-by-number page: the key takes a band under it."""
    kh = key_height(box, dpi, k)
    return Box(box.x, box.y, box.w, box.h - kh - dpi * 0.12), Box(box.x, box.y + box.h - kh, box.w, kh)


def draw_design_page(ctx, g, box, spec, s, lw, raster=None):
    """A colour-by-number design page: the design, its numbers and the key."""
    from .page import draw_design
    art, kb = art_box(box, g.dpi, s.cbn_colours)
    draw_design(ctx, g, art, spec.gen, spec.seed, spec.c, s, lw)
    r = pattern(g, art, spec, lw, s, raster)
    draw_numbers(ctx, [q[:4] for q in r["spots"]], g.dpi)
    draw_key(ctx, kb, r["names"], g.dpi)
    return r


def draw_answer(ctx, g, slot, d, s, lw, raster=None):
    """Answer page cell for a colour-by-number design: the design shrunk into the slot, each numbered space
    shaded grey by its number (1 lightest), to check a finished page against."""
    from .page import design_box, draw_design
    art, _kb = art_box(design_box(g, d, s), g.dpi, s.cbn_colours)
    r = pattern(g, art, d, lw, s, raster)
    num = {q[4]: q[0] for q in r["spots"]}
    top = max(1, len(r["names"]))
    W, H = r["w"], r["h"]
    shade = np.full(W * H, 255, np.uint8)
    for i, l in enumerate(r["label"]):
        n = num.get(l)
        if n:
            shade[i] = _js_round(255 * (1 - (0.12 + 0.6 * (n - 1) / max(1, top - 1))))
    img = QImage(shade.tobytes(), W, H, W, QImage.Format.Format_Grayscale8).copy()
    fs = g.dpi * 0.1
    area = Box(slot.x, slot.y, slot.w, slot.h - fs * 1.6)
    k = min(area.w / art.w, area.h / art.h)
    ox, oy = area.x + (area.w - art.w * k) / 2, area.y + (area.h - art.h * k) / 2
    ctx.save()
    ctx.draw_image(img, ox, oy, art.w * k, art.h * k, smooth=True)
    ctx.transform(k, 0, 0, k, ox - art.x * k, oy - art.y * k)   # the page's design, drawn exactly as on its page
    ctx.stroke_style = ctx.fill_style = "#000"
    ctx.line_width = lw
    draw_design(ctx, g, art, d.gen, d.seed, d.c, s, lw)
    ctx.restore()
    ctx.save()
    ctx.set_font(fs, 400)
    ctx.fill_style, ctx.text_align = "#555", "center"
    ctx.fill_text(f"Shaded by number: 1 lightest to {top} darkest", slot.x + slot.w / 2, slot.y + slot.h - fs * 0.3, slot.w)
    ctx.restore()
