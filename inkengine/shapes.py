"""Outlines shared by dot-to-dots and shaped mazes, ported from index.html's DOT_SHAPES.

Shapes live in unit space (about -1..1, y down). Each point is (x, y, corner): corners keep sharp
angles, smooth points are rounded with Catmull-Rom by dense_outline(). Only the outlines are here so
far; the dot-to-dot details (an eye, a door) come with the dot-to-dot port.
"""

import math

from .rng import pick


def star(rnd):
    n = 5 + pick(rnd, 3)
    pts = []
    for i in range(2 * n):
        a = -math.pi / 2 + i * math.pi / n
        r = 0.42 if i % 2 else 1
        pts.append((r * math.cos(a), r * math.sin(a), True))
    return pts


def heart(rnd):
    pts = []
    for i in range(64):
        t = i / 64 * 2 * math.pi
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16
        pts.append((math.sin(t) ** 3, y, i in (0, 32)))
    return pts


def fish(rnd):
    P = lambda x, y, c=False: (x, y, c)
    return [P(-1, 0, True), P(-0.55, -0.48), P(0, -0.55), P(0.45, -0.3), P(0.62, -0.08, True), P(1, -0.48, True),
            P(0.86, 0, True), P(1, 0.48, True), P(0.62, 0.08, True), P(0.45, 0.3), P(0, 0.55), P(-0.55, 0.48)]


def house(rnd):
    pts = [(-0.75, 1), (-0.75, -0.05), (-0.95, -0.05), (0, -0.95), (0.45, -0.524), (0.45, -0.85), (0.65, -0.85),
           (0.65, -0.334), (0.95, -0.05), (0.75, -0.05), (0.75, 1)]
    return [(x, y, True) for x, y in pts]


OUTLINES = {"star": star, "heart": heart, "fish": fish, "house": house}


def dense_outline(pts):
    """A dense closed outline: straight between corners, Catmull-Rom elsewhere."""
    n, out = len(pts), []
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        out.append(p1)
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
