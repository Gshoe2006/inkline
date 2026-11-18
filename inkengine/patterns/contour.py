"""Topographic contours: lines of equal height through smooth noise, like a hiking map.

Ported line for line from index.html (genContour), so a seed draws the same map as Inkline 2.x.
tests/test_contour.py checks this against recordings of the JavaScript.

The noise is sampled on a grid (a point every 7 pixels at 300 dpi) and each level is traced with
marching squares. Complexity sets the number of levels (11 at 1, 38 at 10); every fifth line is an
index contour, drawn twice as thick. numpy does the grid work: a page is up to 38 levels x 140,000
squares.
"""

import math

import numpy as np

from ..noise import Noise

# For each corner pattern (top-left, top-right, bottom-right, bottom-left above the level = 8, 4, 2, 1):
# which cell edges the line crosses, as pairs of Top, Right, Bottom, Left.
_SEGMENTS = {1: [("L", "B")], 2: [("B", "R")], 3: [("L", "R")], 4: [("T", "R")], 5: [("T", "R"), ("L", "B")],
             6: [("T", "B")], 7: [("L", "T")], 8: [("L", "T")], 9: [("T", "B")], 10: [("L", "T"), ("B", "R")],
             11: [("T", "R")], 12: [("L", "R")], 13: [("B", "R")], 14: [("L", "B")]}


def _js_round(x):
    return int(math.floor(x + 0.5))


def draw(ctx, box, rnd, c, settings=None, lw=1.0, seed=0, dpi=300, **_opts):
    noise = Noise(seed)
    step = max(3, _js_round(dpi / 45))
    f = 1 / (max(box.w, box.h) * 0.32)
    cols, rows = math.ceil(box.w / step) + 1, math.ceil(box.h / step) + 1
    jj, ii = np.mgrid[0:rows, 0:cols].astype(np.float64)
    Z = noise.grid(ii * step * f, jj * step * f)
    lo, hi = min(1.0, float(Z.min())), max(0.0, float(Z.max()))
    F = Z.astype(np.float32).astype(np.float64)   # index.html keeps the grid in a Float32Array
    levels = 8 + c * 3

    A, B, C, D = F[:-1, :-1], F[:-1, 1:], F[1:, 1:], F[1:, :-1]   # each cell's corners: TL, TR, BR, BL
    ctx.save()
    ctx.begin_path()
    ctx.rect(box.x, box.y, box.w, box.h)
    ctx.clip()
    segments = 0
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(levels):
            L = lo + (hi - lo) * (k + 0.5) / levels
            ctx.line_width = lw * 2 if k % 5 == 4 else lw   # index contours, like a real topo map
            ctx.begin_path()
            idx = (A > L) * 8 | (B > L) * 4 | (C > L) * 2 | (D > L) * 1
            js, is_ = np.nonzero((idx != 0) & (idx != 15))   # row by row, as the JavaScript loops
            if len(js):
                a, b, cc, d = A[js, is_], B[js, is_], C[js, is_], D[js, is_]
                x0, y0 = box.x + is_ * step, box.y + js * step
                edge = {
                    "T": (x0 + step * (L - a) / (b - a), y0),
                    "R": (x0 + step, y0 + step * (L - b) / (cc - b)),
                    "B": (x0 + step * (L - d) / (cc - d), y0 + step),
                    "L": (x0, y0 + step * (L - a) / (d - a)),
                }
                edge = {e: (px.tolist(), py.tolist()) for e, (px, py) in edge.items()}
                for n, cell in enumerate(idx[js, is_].tolist()):
                    for p, q in _SEGMENTS[cell]:
                        ctx.move_to(edge[p][0][n], edge[p][1][n])
                        ctx.line_to(edge[q][0][n], edge[q][1][n])
                        segments += 1
            ctx.stroke()
    ctx.restore()
    return {"levels": levels, "step": step, "segments": segments}
