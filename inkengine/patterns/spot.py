"""Spot the difference: two copies of a picture, the second with a few changes to find.

The picture is one of the colouring patterns, drawn twice from the same seed. Where to change it comes
from where its ink is: a small patch drawn on a coarse grid tells busy places (a piece can be taken
away, whited out) from empty ones (a small star, heart, flower or ring can be added). Complexity sets
how many changes (5 to 10) and how small they are. solve=True circles every change in both copies.
"""

import math

import numpy as np

from ..box import Box
from ..rng import mulberry32, pick
from ..shapes import dense_outline, flower, heart, star

# Flow lines are left out: their lines are open and far apart, so a missing piece barely shows.
BASES = {"mandala": "Mandala", "truchet": "Woven tiles", "contour": "Contours"}
MAP_DPI = 100        # the ink map's resolution: fine enough to find the small enclosed spaces
SALT = 0x5D1FF       # the changes' own random sequence, apart from the picture's
KINDS = ("fill", "dot", "gap")


def count(c):
    """How many differences: 5 at complexity 1, 10 at complexity 10."""
    return 5 + round((max(1, min(10, c)) - 1) * 5 / 9)


def layout(box):
    """(first copy, second copy, caption line): stacked on a tall box, side by side on a wide one."""
    fs = min(box.w, box.h) * 0.035
    art = Box(box.x, box.y, box.w, box.h - fs * 2.2)
    gap = min(art.w, art.h) * 0.06
    if art.h >= art.w:
        h = (art.h - gap) / 2
        a, b = Box(art.x, art.y, art.w, h), Box(art.x, art.y + h + gap, art.w, h)
    else:
        w = (art.w - gap) / 2
        a, b = Box(art.x, art.y, w, art.h), Box(art.x + w + gap, art.y, w, art.h)
    return a, b, (box.x + box.w / 2, box.y + box.h - fs * 0.6, fs)


def _draw_base(ctx, half, base, seed, c, s, lw, dpi):
    from . import GENERATORS
    GENERATORS[base](ctx, half, mulberry32(seed), c, s, lw=lw, seed=seed, dpi=dpi)


def ink_map(half, base, seed, c, s, lw, dpi):
    """The picture drawn on a coarse grid: (True where there's ink, grid cells per page pixel)."""
    from PySide6.QtGui import QColor, QImage, QPainter
    from ..canvas import QtCanvas
    from ..qt import ensure_app
    ensure_app()
    sc = MAP_DPI / dpi
    w, h = max(1, math.ceil(half.w * sc)), max(1, math.ceil(half.h * sc))
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(QColor("#fff"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.scale(sc, sc)
    p.translate(-half.x, -half.y)
    ctx = QtCanvas(p, w, h)
    ctx.stroke_style = ctx.fill_style = "#000"
    ctx.line_cap = ctx.line_join = "round"
    ctx.line_width = lw
    _draw_base(ctx, half, base, seed, c, s, lw, dpi)
    p.end()
    grey = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).reshape(h, img.bytesPerLine())[:, 1:w * 4:4]
    return grey < 160, sc


def changes(half, base, seed, c, s, lw, dpi):
    """The differences, in page pixels relative to a copy's corner: [(kind, x, y, r, extra)].
    fill: an enclosed space filled black (extra: its rows of grid runs and the grid scale); dot: a
    dot or small shape in an enclosed space (extra: the shape); gap: a short piece of line missing."""
    from ..cbn import components, distance, region_info
    ink, sc = ink_map(half, base, seed, c, s, lw, dpi)
    gh, gw = ink.shape
    label, nreg = components(np.where(ink, -1, 0).reshape(-1), gw, gh)   # the white spaces
    d = distance(label, gw, gh)
    info = region_info(label, nreg, np.zeros(gw * gh, np.int64), gw, gh, d)
    rnd = mulberry32((seed ^ SALT) & 0xFFFFFFFF)
    n = count(c)
    size = min(gw, gh) * (0.06 - 0.003 * c)       # grid cells: changes get smaller as complexity goes up
    # enclosed spaces only: one touching the edge is the background round the picture
    inner = [(rid, o) for rid, o in enumerate(info) if not o["edge"] and o["area"] > 4]
    # a filled space is the easiest change to see, so only modest ones, and at most a third of the changes
    fills = [(rid, o) for rid, o in inner if 0.4 * size ** 2 <= o["area"] <= 1.6 * size ** 2 and o["r"] >= 1.5]
    most_fills = math.ceil(n / 3)
    S = np.pad(np.cumsum(np.cumsum(ink, 0), 1), ((1, 0), (1, 0)))
    g = max(1.5, size * 0.28)                     # a gap's radius, in grid cells

    def density(x, y, rad):
        x0, y0, x1, y1 = max(0, int(x - rad)), max(0, int(y - rad)), min(gw, int(x + rad) + 1), min(gh, int(y + rad) + 1)
        return (S[y1, x1] - S[y0, x1] - S[y1, x0] + S[y0, x0]) / max(1, (x1 - x0) * (y1 - y0))

    # dots go where there's room: an enclosed space, or open space with ink close by, so never out in
    # the empty margin round a mandala
    D = d.reshape(gh, gw)
    L = label.reshape(gh, gw)
    edge_region = np.array([o["edge"] for o in info] + [False], bool)[L]
    dys, dxs = np.nonzero(D >= max(2.0, size * 0.45))   # room for a dot big enough to see
    ok = (dxs > 2 * size) & (dxs < gw - 2 * size) & (dys > 2 * size) & (dys < gh - 2 * size)
    dys, dxs = dys[ok], dxs[ok]
    ys, xs = np.nonzero(ink)
    ok = (xs > 3 * g) & (xs < gw - 3 * g) & (ys > 3 * g) & (ys < gh - 3 * g)
    xs, ys = xs[ok], ys[ok]
    out, used = [], set()

    spacing = [size]   # room kept between changes; given up only if the picture can't fit them all otherwise

    def clear(x, y, rad):
        return all(math.hypot(x - q[1], y - q[2]) >= rad + q[3] + spacing[0] for q in out)

    def try_fill():
        rid, o = fills[pick(rnd, len(fills))]
        rad = max(o["r"] * 1.6, math.sqrt(o["area"] / math.pi))
        if rid in used or not clear(o["x"], o["y"], rad):
            return None
        rows = np.nonzero(L == rid)
        if rows[0].min() < 2 or rows[1].min() < 2 or rows[0].max() >= gh - 2 or rows[1].max() >= gw - 2:
            return None   # keep clear of the copy's edges, where the picture is cut off
        used.add(rid)
        return ("fill", o["x"], o["y"], rad, rows)

    def surrounded(x, y, reach):   # ink close by to the left, right, above and below: inside the picture
        return (ink[y, max(0, x - reach):x].any() and ink[y, x + 1:x + 1 + reach].any()
                and ink[max(0, y - reach):y, x].any() and ink[y + 1:y + 1 + reach, x].any())

    def try_dot():
        k = pick(rnd, len(dxs))
        x, y = int(dxs[k]), int(dys[k])
        rad = min(float(D[y, x]) * 0.55, size * 0.6)
        if L[y, x] in used or not clear(x, y, rad):
            return None
        if edge_region[y, x] and not surrounded(x, y, int(size * 3)):
            return None
        used.add(int(L[y, x]))   # one change per space
        motif = "dot" if rad < size * 0.45 else ("star", "heart", "flower", "ring")[pick(rnd, 4)]
        return ("dot", x, y, rad, motif)

    def try_gap():
        k = pick(rnd, len(xs))
        x, y = int(xs[k]), int(ys[k])
        if 0.08 <= density(x, y, g) <= 0.6 and clear(x, y, g):
            return ("gap", x, y, g, None)

    tries = {"fill": try_fill if fills else None, "dot": try_dot if len(dxs) else None, "gap": try_gap if len(xs) else None}
    misses = dict.fromkeys(KINDS, 0)
    turn = 0
    while len(out) < n:
        if sum(1 for q in out if q[0] == "fill") >= most_fills:
            tries["fill"] = None
        kinds = [k for k in KINDS if tries[k] and misses[k] < 400]
        if not kinds:
            if spacing[0] == 0:
                break
            spacing[0] = 0                         # last resort: closer together, but never touching
            misses = dict.fromkeys(KINDS, 0)
            continue
        kind = kinds[turn % len(kinds)]           # take turns among the kinds the picture still allows
        got = tries[kind]()
        if got:
            out.append(got)
            turn += 1
        else:
            misses[kind] += 1
    # back to page pixels, relative to the copy's corner
    return [(kind, (x + 0.5) / sc, (y + 0.5) / sc, r / sc, (extra, sc) if kind == "fill" else extra)
            for kind, x, y, r, extra in out]


def _motif(ctx, motif, x, y, r, lw):
    ctx.save()
    ctx.line_width = lw
    ctx.stroke_style = "#000"
    if motif == "ring":
        ctx.begin_path()
        ctx.arc(x, y, r * 0.55, 0, 2 * math.pi)
        ctx.stroke()
        ctx.begin_path()
        ctx.arc(x, y, r * 0.18, 0, 2 * math.pi)
        ctx.fill_style = "#000"
        ctx.fill()
    else:
        shape = {"star": star, "heart": heart, "flower": flower}[motif](mulberry32(1))
        pts = dense_outline(shape.pts)
        ctx.begin_path()
        for i, (px, py, *_rest) in enumerate(pts):
            (ctx.move_to if i == 0 else ctx.line_to)(x + px * r * 0.6, y + py * r * 0.6)
        ctx.close_path()
        ctx.stroke()
    ctx.restore()


def draw(ctx, box, rnd, c, settings=None, lw=1.0, seed=0, dpi=300, solve=False, line=None, **_opts):
    """line: the width to draw with, when it isn't lw (an answer page draws thinner, but the changes are
    worked out with the page's own lw, so they're the same changes)."""
    s = settings
    base = getattr(s, "spot_base", "mandala")
    if base not in BASES:
        base = "mandala"
    a, b, (tx, ty, fs) = layout(box)
    found = changes(a, base, seed, c, s, lw, dpi)
    lw = line or lw
    for half in (a, b):
        ctx.save()
        ctx.stroke_style = ctx.fill_style = "#000"
        ctx.line_width = lw
        _draw_base(ctx, half, base, seed, c, s, lw, dpi)
        ctx.restore()
    for kind, x, y, r, extra in found:   # the second copy's changes
        ctx.save()
        if kind == "fill":   # the space's grid cells, a row of runs at a time, as one black shape
            (ys, xs), sc = extra
            ctx.fill_style = "#000"
            ctx.begin_path()
            for row in np.unique(ys):
                cols = xs[ys == row]
                starts = cols[np.r_[True, np.diff(cols) > 1]]
                ends = cols[np.r_[np.diff(cols) > 1, True]]
                for x0, x1 in zip(starts.tolist(), ends.tolist()):   # a run, grown half a cell to tuck under the lines
                    ctx.rect(b.x + (x0 - 0.5) / sc, b.y + (row - 0.5) / sc, (x1 - x0 + 2) / sc, 2 / sc)
            ctx.fill()
        elif kind == "dot":
            if extra == "dot":
                ctx.fill_style = "#000"
                ctx.begin_path()
                ctx.arc(b.x + x, b.y + y, r, 0, 2 * math.pi)
                ctx.fill()
            else:
                _motif(ctx, extra, b.x + x, b.y + y, r / 0.6, lw)
        else:                # a short piece of line taken away
            ctx.fill_style = "#fff"
            ctx.begin_path()
            ctx.arc(b.x + x, b.y + y, r, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()
    if solve:
        ctx.save()
        ctx.line_width = lw * 2.5
        ctx.stroke_style = "#000"
        for _kind, x, y, r, _extra in found:
            ring = max(r * 1.5, min(a.w, a.h) * 0.03)   # big enough to see round a small dot or gap
            for half in (a, b):
                ctx.begin_path()
                ctx.arc(half.x + x, half.y + y, ring, 0, 2 * math.pi)
                ctx.stroke()
        ctx.restore()
    if not solve:   # an answer page names the puzzle already
        ctx.save()
        ctx.set_font(fs, 600)
        ctx.fill_style, ctx.text_align = "#000", "center"
        ctx.fill_text(f"Find the {len(found)} differences", tx, ty)
        ctx.restore()
    return found
