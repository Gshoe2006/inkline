"""Photo dot-to-dot: the main outline of a photo as numbered dots, to join up in order.

From the photo's tones (photo.py's work image), with numpy only:

1. Blur a little, and mark what's darker than Threshold (lighter, with Invert) as the subject.
2. Keep the biggest patch of it, preferring one that doesn't run along the edges of the picture (that's usually
   the background), and fill in its holes, so only its outside edge is left.
3. Trace that edge with marching squares on a blurred copy (so it's smooth, not stepped pixel by pixel), joining
   the little pieces into closed loops and keeping the longest.
4. Simplify it with Ramer-Douglas-Peucker towards the number of dots chosen (Dots, 20-150): the corners stay, the
   straight stretches lose their points. Then the longest stretches between dots are halved until the number is
   exact, so the dots are spread out enough to number.
5. Number the dots clockwise from the top, and draw them with the dot-to-dot pattern's own numbering
   (patterns/dots.py), which puts each number outside the outline where it doesn't land on another.

The answer joins the dots (Show the answer, as the photo nonogram has).
"""

import math
from collections import deque

import numpy as np

from .box import Box


def _blur(img, sigma):
    """A separable Gaussian blur with clamped edges."""
    r = max(1, math.ceil(sigma * 3))
    k = np.exp(-(np.arange(-r, r + 1) ** 2) / (2 * sigma * sigma))
    k /= k.sum()
    h, w = img.shape
    a = np.pad(img, ((0, 0), (r, r)), mode="edge")
    out = sum(a[:, i:i + w] * k[i] for i in range(2 * r + 1))
    a = np.pad(out, ((r, r), (0, 0)), mode="edge")
    return sum(a[i:i + h, :] * k[i] for i in range(2 * r + 1))


def frame(mask, w, h):
    """The photo's own rectangle in the work image, (x0, y0, x1, y1): fitted inside the page, a photo leaves empty
    space round it, and its edges are where the picture stops, not the work image's."""
    ys, xs = np.nonzero(mask.reshape(h, w))
    if not len(xs):
        return 0, 0, w - 1, h - 1
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _patches(on, box=None):
    """Each 4-connected patch of True pixels: a list of (size, how many of its pixels are on the edge of box (the
    photo's rectangle, x0, y0, x1, y1), how many of its four sides it touches, label), and the label image."""
    h, w = on.shape
    x0, y0, x1, y1 = box or (0, 0, w - 1, h - 1)
    label = np.zeros((h, w), np.int32)
    flat_on = on.reshape(-1)
    flat = label.reshape(-1)
    out = []
    n = 0
    for start in np.flatnonzero(flat_on):
        if flat[start]:
            continue
        n += 1
        flat[start] = n
        todo, size, edge, sides = deque([start]), 0, 0, set()
        while todo:
            i = todo.popleft()
            size += 1
            y, x = divmod(int(i), w)
            if x <= x0 or y <= y0 or x >= x1 or y >= y1:
                edge += 1
                sides.update(k for k, on_side in enumerate((x <= x0, y <= y0, x >= x1, y >= y1)) if on_side)
            for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1), (i - w, y > 0), (i + w, y < h - 1)):
                if ok and flat_on[j] and not flat[j]:
                    flat[j] = n
                    todo.append(j)
        out.append((size, edge, len(sides), n))
    return out, label


def subject(lum, mask, w, h, t, inv=False):
    """The subject as a filled True/False image (h x w), or None when nothing is dark enough."""
    tone = _blur(lum.reshape(h, w).astype(np.float64), 1.0)
    inside = mask.reshape(h, w).astype(bool)
    on = ((tone > t) if inv else (tone < t)) & inside
    box = frame(mask, w, h)
    border, area = 2 * (box[2] - box[0] + box[3] - box[1] + 2), int(inside.sum())
    best, best_score = None, 0.0
    # the dark patches, and the light ones too (a light subject on a dark background), which count for a bit less
    for weight, side in ((1.0, on), (0.9, ~on & inside)):
        patches, label = _patches(side, box)
        for size, edge, sides, n in patches:
            if size > area * 0.6 and edge > border * 0.2:   # most of the picture, round its edges: the background
                continue
            # a patch that runs along the picture's edges is more likely background (or ground, or sky): the more it
            # does, the less it counts, so a shape that stands clear of the edges wins when there's one
            score = size * weight * (0.1 if edge > border * 0.2 else 0.15 if sides >= 2 else 0.3 if sides else 1.0)
            if score > best_score and size >= max(12, w * h // 2000):
                best, best_score = label == n, score
    if best is None:
        return None
    shape = best
    # fill its holes: a patch of the rest that doesn't reach the edge is inside it
    _rest, rest = _patches(~shape)
    edges = set(np.unique(np.concatenate([rest[0], rest[-1], rest[:, 0], rest[:, -1]]).tolist())) - {0}
    fill = shape | ((rest > 0) & ~np.isin(rest, sorted(edges)))
    return fill


# --- marching squares ----------------------------------------------------------------------------------------------

def contours(field, level=0.5):
    """Closed loops where field crosses level, each a list of (x, y) in pixel units (the field is padded with lows,
    so every loop closes)."""
    f = np.pad(field.astype(np.float64), 1, constant_values=level - 1)
    h, w = f.shape
    above = f > level

    def point(edge):
        kind, y, x = edge   # "h": between (y, x) and (y, x + 1); "v": between (y, x) and (y + 1, x)
        a = f[y, x]
        b = f[y, x + 1] if kind == "h" else f[y + 1, x]
        t = (level - a) / (b - a) if b != a else 0.5
        return (float(x + t - 1), float(y - 1)) if kind == "h" else (float(x - 1), float(y + t - 1))

    links = {}

    def link(e1, e2):
        links.setdefault(e1, []).append(e2)
        links.setdefault(e2, []).append(e1)

    codes = above[:-1, :-1] * 8 + above[:-1, 1:] * 4 + above[1:, 1:] * 2 + above[1:, :-1]
    for y, x in zip(*np.nonzero((codes > 0) & (codes < 15))):   # only the squares the line goes through
        y, x = int(y), int(x)
        code = int(codes[y, x])
        top, right, bottom, left = ("h", y, x), ("v", y, x + 1), ("h", y + 1, x), ("v", y, x)
        if code in (5, 10):   # a saddle: the middle of the square decides which corners join
            mid = (f[y, x] + f[y, x + 1] + f[y + 1, x] + f[y + 1, x + 1]) / 4 > level
            if (code == 10) == mid:
                link(top, right)
                link(bottom, left)
            else:
                link(top, left)
                link(bottom, right)
            continue
        tl, tr, br, bl = above[y, x], above[y, x + 1], above[y + 1, x + 1], above[y + 1, x]
        crossed = [e for e, on in ((top, tl != tr), (right, tr != br), (bottom, br != bl), (left, bl != tl)) if on]
        link(crossed[0], crossed[1])
    loops, seen = [], set()
    for start in links:
        if start in seen:
            continue
        loop, prev, cur = [], None, start
        while True:
            seen.add(cur)
            loop.append(point(cur))
            nxt = [e for e in links[cur] if e != prev]
            nxt = [e for e in nxt if e not in seen] or nxt
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur == start:
                break
        if len(loop) > 2:
            loops.append(loop)
    return loops


def _length(loop):
    return sum(math.dist(loop[i], loop[(i + 1) % len(loop)]) for i in range(len(loop)))


# --- simplifying ---------------------------------------------------------------------------------------------------

def _rdp(pts, eps):
    """Ramer-Douglas-Peucker on an open line: the indices kept."""
    keep = {0, len(pts) - 1}
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        (ax, ay), (bx, by) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-9
        best, far = -1.0, a
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > best:
                best, far = d, i
        if best > eps:
            keep.add(far)
            stack += [(a, far), (far, b)]
    return keep


def simplify(loop, n):
    """A closed loop as exactly n points (fewer if it has fewer): RDP picks the corners (up to 60% of them), then the
    longest stretches between points are halved until there are n, so the dots are spread along the straight bits
    too and no two numbers end up far apart."""
    m = len(loop)
    if m <= n:
        return list(loop)
    # split the loop at its two farthest-apart points, so RDP sees two open lines
    a = 0
    b = max(range(m), key=lambda i: math.dist(loop[0], loop[i]))
    a = max(range(m), key=lambda i: math.dist(loop[b], loop[i]))
    order = loop[a:] + loop[:a]
    b = (b - a) % m
    halves = (order[:b + 1], order[b:] + order[:1])

    def kept(eps):
        k1 = _rdp(halves[0], eps)
        k2 = _rdp(halves[1], eps)
        return sorted(k1 | {b + i for i in k2 if b + i < m})

    lo, hi = 0.0, max(1.0, max(math.dist(p, q) for p in loop[::max(1, m // 50)] for q in loop[::max(1, m // 50)]))
    best = kept(lo)
    corners = max(3, round(n * 0.6))
    for _ in range(40):   # the smallest tolerance that keeps at most that many points
        mid = (lo + hi) / 2
        k = kept(mid)
        if len(k) > corners:
            lo = mid
        else:
            hi, best = mid, k
    pts = [order[i] for i in best]
    while len(pts) < n:   # too few: a point in the middle of the longest gap, on the outline
        gaps = [(best[(i + 1) % len(best)] - best[i]) % m for i in range(len(best))]
        i = max(range(len(best)), key=lambda k: gaps[k])
        if gaps[i] < 2:
            break
        best.insert(i + 1, (best[i] + gaps[i] // 2) % m)
        best = sorted(set(best))
        pts = [order[j] for j in best]
    while len(pts) > n:   # too many: drop the point that changes the outline least
        def area(i):
            (x1, y1), (x2, y2), (x3, y3) = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
        pts.pop(min(range(len(pts)), key=area))
    return pts


def roomy_start(pts):
    """Dot 1 (with its ring), the last dot and dot 2 crowd each other where the outline starts at a sharp corner: the
    dots either side of dot 1 that are closer than the usual spacing are left out, so its ring and numbers have room."""
    if len(pts) < 8:
        return pts
    step = sum(math.dist(p, q) for p, q in zip(pts, pts[1:] + pts[:1])) / len(pts)
    while len(pts) > 8 and math.dist(pts[0], pts[1]) < step * 0.9:
        pts = pts[:1] + pts[2:]
    while len(pts) > 8 and math.dist(pts[0], pts[-1]) < step * 0.9:
        pts = pts[:-1]
    return pts


def clockwise_from_top(pts):
    """Clockwise on the page (y down) and starting from the top-most point, as the dot-to-dot pattern numbers."""
    area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    s = min(range(len(pts)), key=lambda i: (pts[i][1], pts[i][0]))
    return pts[s:] + pts[:s]


def outline(lum, mask, w, h, t, inv, n):
    """The photo's main outline as n points in work-image pixels, numbered order; [] when there's none."""
    shape = subject(lum, mask, w, h, t, inv)
    if shape is None:
        return []
    soft = _blur(shape.astype(np.float64), max(1.0, min(w, h) / 160))
    loops = contours(soft, 0.5)
    if not loops:
        return []
    loop = max(loops, key=_length)
    # where the shape runs along the picture's edge, that's the photo's frame, not an outline: no dots there (the
    # line joins straight across)
    x0, y0, x1, y1 = frame(mask, w, h)
    m = 2.5
    kept = [p for p in loop if x0 + m < p[0] < x1 - m and y0 + m < p[1] < y1 - m]
    if len(kept) < max(8, len(loop) // 5):
        return []
    return roomy_start(clockwise_from_top(spaced(simplify(kept, n))))


def spaced(pts):
    """Dots too close to the one before (under half the usual spacing) are left out, so no two sit on top of each
    other and their numbers have room."""
    if len(pts) < 4:
        return pts
    step = sum(math.dist(p, q) for p, q in zip(pts, pts[1:] + pts[:1])) / len(pts)
    out = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, out[-1]) >= step * 0.5:
            out.append(p)
    while len(out) > 3 and math.dist(out[-1], out[0]) < step * 0.5:   # nor the last on top of the first
        out.pop()
    return out


def place(pts, box, share=0.84):
    """Points scaled to fit share of the box, in the middle, keeping their shape."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    bw, bh = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    k = min(box.w * share / bw, box.h * share / bh)
    ox = box.x + box.w / 2 - (min(xs) + bw / 2) * k
    oy = box.y + box.h / 2 - (min(ys) + bh / 2) * k
    return [(ox + x * k, oy + y * k) for x, y in pts]


def work_cell(box):
    """Page pixels per work-image pixel: about 320 across the long side, enough for a smooth outline."""
    return max(1.0, max(box.w, box.h) / 320)


def draw(ctx, box, dpi, s, e, inv):
    """Draw the photo's dots (or, with s.pdots_answer, the joined outline) from its Conversion e."""
    from .i18n import tr
    from .patterns.dots import draw_numbered
    n = max(20, min(150, int(getattr(s, "pdots_n", 60))))
    if n not in e.outlines:   # one outline for each number of dots
        e.outlines[n] = outline(e.lum, e.mask, e.ww, e.wh, s.threshold, inv, n)
    pts = e.outlines[n]
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    if len(pts) < 3:
        ctx.fill_style, ctx.text_align = "#888", "center"
        ctx.set_font(box.w / 32, 400)
        ctx.fill_text(tr("No outline found: try another Threshold, or Invert."), box.x + box.w / 2, box.y + box.h / 2)
        ctx.restore()
        return {"dots": 0}
    lw = s.weight * dpi / 150
    ctx.line_width = lw
    ctx.line_cap = ctx.line_join = "round"
    out = draw_numbered(ctx, Box(*box), place(pts, box), lw, dpi, connect=bool(getattr(s, "pdots_answer", False)))
    ctx.restore()
    return out
