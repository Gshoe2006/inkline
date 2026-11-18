"""Flow lines: evenly spaced curves that follow a smooth noise field, like wood grain or wind.

Ported line for line from index.html (genFlow), so a seed draws the same lines as Inkline 2.x.
tests/test_flow.py checks this against recordings of the JavaScript.

Seed points on a jittered grid are visited in random order. From each, a line is traced both ways
along the field until it leaves the box or comes too close to an earlier line (a coarse occupancy
grid keeps them apart). Lines shorter than 10 steps are dropped. Complexity sets the spacing.
"""

import math

from ..noise import Noise
from ..rng import pick


def draw(ctx, box, rnd, c, settings=None, lw=None, seed=0, **_opts):
    noise = Noise(seed)
    f = 1 / (max(box.w, box.h) * 0.45)
    sep = box.w / (16 + c * 5)
    cs = sep * 0.5
    gw, gh = math.ceil(box.w / cs) + 1, math.ceil(box.h / cs) + 1
    occ = [-1] * (gw * gh)
    step_len = sep * 0.25
    bx, by, bx2, by2 = box.x, box.y, box.x + box.w, box.y + box.h

    def cell(x, y):          # JavaScript's "| 0" truncates toward zero, as int() does
        return int((x - bx) / cs), int((y - by) / cs)

    def blocked(x, y, line_id):
        gx, gy = cell(x, y)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                X, Y = gx + dx, gy + dy
                if X < 0 or Y < 0 or X >= gw or Y >= gh:
                    continue
                o = occ[Y * gw + X]
                if o != -1 and o != line_id:
                    return True
        return False

    def inside(x, y):
        return bx <= x <= bx2 and by <= y <= by2

    def trace(x, y, direction, line_id):
        pts = []
        for _ in range(800):
            if not inside(x, y) or blocked(x, y, line_id):
                break
            pts.append((x, y))
            a = noise(x * f, y * f) * math.pi * 4
            x += math.cos(a) * step_len * direction
            y += math.sin(a) * step_len * direction
        return pts

    seeds = []
    y = by + sep / 2
    while y < by2:
        x = bx + sep / 2
        while x < bx2:
            seeds.append((x + (rnd() - 0.5) * sep, y + (rnd() - 0.5) * sep))
            x += sep
        y += sep
    for i in range(len(seeds) - 1, 0, -1):
        j = pick(rnd, i + 1)
        seeds[i], seeds[j] = seeds[j], seeds[i]

    ctx.line_join = ctx.line_cap = "round"
    line_id = 0
    for sx, sy in seeds:
        if not inside(sx, sy) or blocked(sx, sy, line_id):
            continue
        back = trace(sx, sy, -1, line_id)
        back.reverse()
        pts = back + trace(sx, sy, 1, line_id)[1:]
        if len(pts) < 10:
            continue
        for x, y in pts:
            gx, gy = cell(x, y)
            if 0 <= gx < gw and 0 <= gy < gh:
                occ[gy * gw + gx] = line_id
        ctx.begin_path()
        ctx.move_to(*pts[0])
        for p in pts:
            ctx.line_to(*p)
        ctx.stroke()
        line_id += 1
    return {"lines": line_id, "seeds": len(seeds)}
