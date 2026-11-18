"""Shapes shared by dot-to-dots and shaped mazes, ported from index.html's DOT_SHAPES.

Shapes live in unit space (about -1..1, y down). Each outline point is (x, y, corner): corners always
get a dot, so a house keeps its square corners; smooth points are rounded with Catmull-Rom by
dense_outline(). extras are fixed details (an eye, a door) drawn as lines, so the finished picture
reads clearly. min_dots is the fewest dots that still draw the shape recognisably.
"""

import math
from dataclasses import dataclass, field

from .rng import pick


@dataclass
class Shape:
    pts: list
    extras: list = field(default_factory=list)   # {"circle": (x, y, r)} or {"line": [(x, y), ...]}
    min_dots: int = 0


def star(rnd):
    n = 5 + pick(rnd, 3)
    pts = []
    for i in range(2 * n):
        a = -math.pi / 2 + i * math.pi / n
        r = 0.42 if i % 2 else 1
        pts.append((r * math.cos(a), r * math.sin(a), True))
    return Shape(pts)


def heart(rnd):
    pts = []
    for i in range(64):
        t = i / 64 * 2 * math.pi
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16
        pts.append((math.sin(t) ** 3, y, i in (0, 32)))
    return Shape(pts)


def fish(rnd):
    P = lambda x, y, c=False: (x, y, c)
    return Shape(
        [P(-1, 0, True), P(-0.55, -0.48), P(0, -0.55), P(0.45, -0.3), P(0.62, -0.08, True), P(1, -0.48, True),
         P(0.86, 0, True), P(1, 0.48, True), P(0.62, 0.08, True), P(0.45, 0.3), P(0, 0.55), P(-0.55, 0.48)],
        [{"circle": (-0.58, -0.12, 0.08)}, {"line": [(-0.3, -0.38), (-0.22, 0), (-0.3, 0.38)]}])


def house(rnd):
    pts = [(-0.75, 1), (-0.75, -0.05), (-0.95, -0.05), (0, -0.95), (0.45, -0.524), (0.45, -0.85), (0.65, -0.85),
           (0.65, -0.334), (0.95, -0.05), (0.75, -0.05), (0.75, 1)]
    return Shape([(x, y, True) for x, y in pts],
                 [{"line": [(-0.15, 1), (-0.15, 0.45), (0.15, 0.45), (0.15, 1)]},
                  {"line": [(0.32, 0.2), (0.58, 0.2), (0.58, 0.46), (0.32, 0.46), (0.32, 0.2)]}])


def flower(rnd):
    n, per = 5 + pick(rnd, 3), 16
    pts = []
    for i in range(n * per):
        t = i / (n * per) * 2 * math.pi
        r = 0.42 + 0.58 * abs(math.sin(n * t / 2))
        # valleys and petal tips always get a dot, so even a few dots trace petals, not a cog
        pts.append((r * math.cos(t - math.pi / 2), r * math.sin(t - math.pi / 2), i % per == 0 or i % per == per / 2))
    # 4 dots per petal can only draw a pointed box; 6 is the fewest that reads as a round petal
    return Shape(pts, [{"circle": (0, 0, 0.24)}], n * 6)


def blob(rnd):
    k = []
    for f in (2, 3, 4):
        a = 0.05 + rnd() * 0.1
        k.append((f, a, rnd() * 6.3))
    pts = []
    for i in range(72):
        t = i / 72 * 2 * math.pi
        r = 0.75
        for f, a, p in k:
            r += a * math.cos(f * t + p)
        pts.append((r * math.cos(t), r * math.sin(t), False))
    return Shape(pts)


# In index.html's order: a seed picks shape number int(rnd() * 6) from this list.
DOT_SHAPES = {"star": star, "heart": heart, "fish": fish, "house": house, "flower": flower, "blob": blob}

# The outlines shaped mazes can use.
OUTLINES = {name: (lambda rnd, f=DOT_SHAPES[name]: f(rnd).pts) for name in ("star", "heart", "fish", "house")}


def dense_outline(pts):
    """A dense closed outline: straight between corners, Catmull-Rom elsewhere."""
    n, out = len(pts), []
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        out.append(tuple(p1))
        if p1[2] and p2[2]:
            continue
        p0 = p1 if p1[2] else pts[(i - 1) % n]   # a corner is its own tangent neighbour
        p3 = p2 if p2[2] else pts[(i + 2) % n]
        for s in range(1, 10):
            t = s / 10
            t2, t3 = t * t, t * t * t
            f = lambda k: 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)
            out.append((f(0), f(1), False))
    return out
