"""Mandalas: rings of repeating motifs around a centre, for colouring.

Ported line for line from index.html (genMandala), so a seed draws the same mandala as Inkline 2.x.
tests/test_mandala.py checks this against recordings of the JavaScript. Booklet covers use it too.

Complexity sets the number of rings (3 at 1, 14 at 10). Each ring picks a motif different from the
ring inside it, repeated a multiple of the base symmetry (6, 8, 10 or 12) times.
"""

import math

from ..rng import pick

MOTIFS = ["petal", "circle", "scallop", "zigzag", "dots", "spokes", "teardrop"]


def _js_round(x):
    return int(math.floor(x + 0.5))


def draw(ctx, box, rnd, c, settings=None, lw=1.0, **_opts):
    cx, cy = box.x + box.w / 2, box.y + box.h / 2
    R = min(box.w, box.h) / 2 - lw

    def P(r, a):
        return cx + r * math.cos(a), cy + r * math.sin(a)

    rings, r0 = 3 + _js_round(c * 1.1), R * 0.09
    ws = [0.6 + rnd() * 0.8 for _ in range(rings)]
    tot = sum(ws)
    base = [6, 8, 10, 12][pick(rnd, 4)]

    # centre: two circles and a ring of small leaves
    ctx.circle(cx, cy, r0)
    ctx.circle(cx, cy, r0 * 0.35)
    for k in range(base):
        a, h = k * 2 * math.pi / base, math.pi / base
        ctx.begin_path()
        ctx.move_to(*P(r0 * 0.35, a - h))
        ctx.quadratic_curve_to(*P(r0 * 1.15, a), *P(r0 * 0.35, a + h))
        ctx.stroke()

    r1, last = r0, ""
    used = []
    for i in range(rings):
        r2 = r1 + (R - r0) * ws[i] / tot
        rm, d = (r1 + r2) / 2, r2 - r1
        while True:                       # never the same motif twice in a row
            m = MOTIFS[pick(rnd, len(MOTIFS))]
            if m != last:
                break
        last = m
        used.append(m)
        target = 2 * math.pi * rm / d * (0.8 + rnd() * 0.8)
        n = max(base, _js_round(target / base) * base)
        h = math.pi / n
        for k in range(n):
            a = k * 2 * h
            ctx.begin_path()
            _MOTIF_DRAW[m](ctx, P, a, h, r1, r2, rm, d, lw)
        ctx.circle(cx, cy, r2)
        if rnd() < 0.35 and d > lw * 8:   # sometimes a second line just inside the ring
            ctx.circle(cx, cy, r2 - lw * 3)
        r1 = r2
    return {"rings": rings, "base": base, "motifs": used}


# Each motif draws one repeat at angle a (half-width h) between radii r1 and r2. A fresh path is begun.

def _petal(ctx, P, a, h, r1, r2, rm, d, lw):
    ctx.move_to(*P(r1, a - h * 0.95))
    ctx.bezier_curve_to(*P(r1 + d * 0.5, a - h * 1.05), *P(r2, a - h * 0.35), *P(r2, a))
    ctx.bezier_curve_to(*P(r2, a + h * 0.35), *P(r1 + d * 0.5, a + h * 1.05), *P(r1, a + h * 0.95))
    ctx.move_to(*P(r1, a - h * 0.45))
    ctx.quadratic_curve_to(*P(r1 + d * 0.55, a - h * 0.4), *P(r1 + d * 0.72, a))
    ctx.quadratic_curve_to(*P(r1 + d * 0.55, a + h * 0.4), *P(r1, a + h * 0.45))
    ctx.stroke()


def _circle(ctx, P, a, h, r1, r2, rm, d, lw):
    rad = min(d / 2, rm * math.sin(h)) * 0.82
    ctx.circle(*P(rm, a), rad)
    ctx.circle(*P(rm, a), rad * 0.45)


def _scallop(ctx, P, a, h, r1, r2, rm, d, lw):
    ctx.move_to(*P(r1, a - h))
    ctx.quadratic_curve_to(*P(2 * r2 - r1, a), *P(r1, a + h))
    ctx.move_to(*P(r1, a - h * 0.6))
    ctx.quadratic_curve_to(*P(r1 + d * 1.1, a), *P(r1, a + h * 0.6))
    ctx.stroke()


def _zigzag(ctx, P, a, h, r1, r2, rm, d, lw):
    ctx.move_to(*P(r1, a - h))
    ctx.line_to(*P(r2, a))
    ctx.line_to(*P(r1, a + h))
    ctx.stroke()
    ctx.circle(*P(r1 + d * 0.32, a), min(d * 0.12, rm * h * 0.3))


def _dots(ctx, P, a, h, r1, r2, rm, d, lw):
    ctx.circle(*P(rm, a), min(d / 2, rm * math.sin(h)) * 0.55)
    ctx.circle(*P(r1 + d * 0.22, a + h), min(d, rm * h) * 0.12)
    ctx.circle(*P(r2 - d * 0.22, a + h), min(d, rm * h) * 0.12)


def _spokes(ctx, P, a, h, r1, r2, rm, d, lw):
    ctx.move_to(*P(r1, a))
    ctx.line_to(*P(r2, a))
    ctx.move_to(*P(r1 + d * 0.3, a + h * 0.35))
    ctx.line_to(*P(r1 + d * 0.3, a + h * 1.65))
    ctx.stroke()
    ctx.circle(*P(r1 + d * 0.65, a + h), min(d * 0.18, rm * h * 0.45))


def _teardrop(ctx, P, a, h, r1, r2, rm, d, lw):
    tip = P(r2 - lw, a)
    ctx.move_to(*tip)
    ctx.bezier_curve_to(*P(rm, a - h * 0.25), *P(r1, a - h * 0.95), *P(r1 + d * 0.1, a))
    ctx.bezier_curve_to(*P(r1, a + h * 0.95), *P(rm, a + h * 0.25), *tip)
    ctx.stroke()


_MOTIF_DRAW = {"petal": _petal, "circle": _circle, "scallop": _scallop, "zigzag": _zigzag,
               "dots": _dots, "spokes": _spokes, "teardrop": _teardrop}
