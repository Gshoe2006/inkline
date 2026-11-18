"""Dot-to-dot: numbered dots round a shape's outline; joining them in order draws the picture.

Ported line for line from index.html (genDots), so a seed draws the same shape and dots as
Inkline 2.x. tests/test_dots.py checks this against recordings of the JavaScript.

The seed picks one of six shapes (star, heart, fish, house, flower, blob). The outline runs
clockwise from its top-most corner; every corner gets a dot and the rest are spread along each
stretch in proportion to its length (18 dots at complexity 1, 90 at 10). Each number is placed
outside the outline, trying a few angles and distances so it doesn't land on another number, a dot
or a detail. A ring marks dot 1. The answer page (connect=True) draws the finished picture.

Where a number lands depends on how wide the font draws it, so with fonts other than 2.x's a
number can sit in a different free spot; the dots themselves are always the same.
"""

import math

from ..rng import pick
from ..shapes import DOT_SHAPES, dense_outline


def _js_round(x):
    return int(math.floor(x + 0.5))


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, connect=False, **_opts):
    names = list(DOT_SHAPES)
    shape_name = names[pick(rnd, len(names))]
    shape = DOT_SHAPES[shape_name](rnd)
    line = dense_outline(shape.pts)
    # clockwise on screen (positive shoelace area with y down), starting from the top-most corner or point
    n = len(line)
    area = 0.0
    for i, p in enumerate(line):
        q = line[(i + 1) % n]
        area = area + p[0] * q[1] - q[0] * p[1]
    if area < 0:
        line.reverse()
    cand = [(p, i) for i, p in enumerate(line) if p[2]] if any(p[2] for p in line) else [(p, i) for i, p in enumerate(line)]
    best = cand[0]
    for x in cand[1:]:
        if x[0][1] < best[0][1] - 1e-9 or (abs(x[0][1] - best[0][1]) < 1e-9 and x[0][0] < best[0][0]):
            best = x
    s0 = best[1]
    line = line[s0:] + line[:s0]

    # fit to the box, leaving room for numbers round the outside
    xs, ys = [p[0] for p in line], [p[1] for p in line]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    sc = min(box.w * 0.8 / bw, box.h * 0.8 / bh)
    ox = box.x + box.w / 2 - (min(xs) + bw / 2) * sc
    oy = box.y + box.h / 2 - (min(ys) + bh / 2) * sc

    def T(p):
        return ox + p[0] * sc, oy + p[1] * sc

    P = [(*T(p), p[2]) for p in line]
    M = len(P)

    # dots: every corner, then the rest spread along each stretch in proportion to its length
    N = max(10 + c * 8, shape.min_dots)
    anchors = [i for i, p in enumerate(P) if p[2]] or [0]

    def seg_len(a, b):   # outline length from a forward to b; a == b (no corners) is all the way round
        L, i = 0.0, a
        while True:
            j = (i + 1) % M
            L += math.hypot(P[j][0] - P[i][0], P[j][1] - P[i][1])
            i = j
            if i == b:
                return L

    spans = [(a, anchors[(k + 1) % len(anchors)]) for k, a in enumerate(anchors)]
    lens = [seg_len(a, b) for a, b in spans]
    total = sum(lens)
    spare = max(0, N - len(anchors))
    dots = []
    for k, (a, b) in enumerate(spans):
        dots.append((P[a][0], P[a][1]))
        m = _js_round(spare * lens[k] / total)
        if not m:
            continue
        step = lens[k] / (m + 1)
        need, i, acc = step, a, 0.0
        while len(dots) < 10000 and need < lens[k] - 1e-6:
            j = (i + 1) % M
            d = math.hypot(P[j][0] - P[i][0], P[j][1] - P[i][1])
            if acc + d >= need:
                t = (need - acc) / d
                dots.append((P[i][0] + (P[j][0] - P[i][0]) * t, P[i][1] + (P[j][1] - P[i][1]) * t))
                need += step
                continue
            acc += d
            i = j
            if i == b:
                break

    ctx.save()
    ctx.line_width, ctx.stroke_style, ctx.fill_style = lw, "#000", "#000"
    ctx.line_cap = ctx.line_join = "round"
    for e in shape.extras:   # fixed details, drawn in both the puzzle and the answer
        if "circle" in e:
            x, y = T(e["circle"])
            ctx.begin_path()
            ctx.arc(x, y, e["circle"][2] * sc, 0, math.pi * 2)
            ctx.stroke()
        if "line" in e:
            ctx.begin_path()
            for i, p in enumerate(e["line"]):
                (ctx.line_to if i else ctx.move_to)(*T(p))
            ctx.stroke()
    rd = max(lw * 0.9, dpi * 0.016)

    if connect:   # answer page: the finished picture
        ctx.begin_path()
        for i, d in enumerate(dots):
            (ctx.line_to if i else ctx.move_to)(*d)
        ctx.close_path()
        ctx.stroke()
        for d in dots:
            ctx.begin_path()
            ctx.arc(d[0], d[1], rd * 0.8, 0, math.pi * 2)
            ctx.fill()
        ctx.restore()
        return {"shape": shape_name, "dots": len(dots), "overlaps": 0}

    # numbers sit outside the outline; try a few angles so they don't land on other numbers or dots
    nd = len(dots)
    spacing = math.inf
    for i in range(nd):
        q = dots[(i + 1) % nd]
        spacing = min(spacing, math.hypot(q[0] - dots[i][0], q[1] - dots[i][1]))
    fs = max(dpi * 0.085, min(dpi * 0.17, spacing * 0.6))
    cx, cy = box.x + box.w / 2, box.y + box.h / 2
    placed = []
    ctx.set_font(fs, 600)
    ctx.text_align, ctx.text_baseline = "center", "alphabetic"
    # the fixed details (eye, door, flower centre) are obstacles too: sample points along them
    detail = []
    for e in shape.extras:
        if "circle" in e:
            ex, ey, er = e["circle"]
            for k in range(32):
                a = k / 32 * 2 * math.pi
                detail.append(T((ex + er * math.cos(a), ey + er * math.sin(a))))
        if "line" in e:
            pts = e["line"]
            for k in range(1, len(pts)):
                a, b = pts[k - 1], pts[k]
                t = 0.0
                while t <= 1:          # the same float steps as the JavaScript's t += 1 / 8
                    detail.append(T((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)))
                    t += 1 / 8

    def in_box(r):
        return r[0] >= box.x and r[1] >= box.y and r[0] + r[2] <= box.x + box.w and r[1] + r[3] <= box.y + box.h

    def near(pts, r, pad):
        return any(r[0] - pad < d[0] < r[0] + r[2] + pad and r[1] - pad < d[1] < r[1] + r[3] + pad for d in pts)

    def hits(r):
        return (not in_box(r) or any(r[0] < q[0] + q[2] and q[0] < r[0] + r[2] and r[1] < q[1] + q[3] and q[1] < r[1] + r[3]
                                     for q in placed)
                or near(dots, r, rd) or near(detail, r, lw))

    overlaps = 0
    for i, d in enumerate(dots):
        a, b = dots[(i - 1) % nd], dots[(i + 1) % nd]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        nl = math.hypot(nx, ny) or 1
        nx, ny = nx / nl, ny / nl
        if nx * (d[0] - cx) + ny * (d[1] - cy) < 0:   # point away from the middle
            nx, ny = -nx, -ny
        label = str(i + 1)
        w, h = ctx.measure_text(label), fs * 0.8
        # outward first, then turned, then farther out, then pointing inward as a last resort
        best, clear = None, False
        for far in (1, 1.9):
            for turn in (0, 0.5, -0.5, 1, -1, 1.5, -1.5, math.pi):
                ca, sa = math.cos(turn), math.sin(turn)
                ux, uy = nx * ca - ny * sa, nx * sa + ny * ca
                off = (rd + fs * 0.35) * far + abs(ux) * w / 2 + abs(uy) * h / 2
                r = (d[0] + ux * off - w / 2, d[1] + uy * off - h / 2, w, h)
                if best is None:
                    best = r
                if not hits(r):
                    best, clear = r, True
                    break
            if clear:
                break
        if not clear:
            overlaps += 1
        placed.append(best)
        ctx.fill_text(label, best[0] + w / 2, best[1] + h * 0.9)
    for d in dots:
        ctx.begin_path()
        ctx.arc(d[0], d[1], rd, 0, math.pi * 2)
        ctx.fill()
    ctx.line_width = max(1, lw * 0.6)
    ctx.begin_path()
    ctx.arc(dots[0][0], dots[0][1], rd * 2.4, 0, math.pi * 2)   # a ring marks where to start
    ctx.stroke()
    ctx.restore()
    return {"shape": shape_name, "dots": nd, "overlaps": overlaps, "fs": fs / dpi, "labels": placed}
