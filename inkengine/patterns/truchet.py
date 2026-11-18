"""Woven tiles: a grid of square tiles, each with quarter circles in two opposite corners.

Ported line for line from index.html (genTruchet), so a seed draws the same tiles as Inkline 2.x.
tests/test_truchet.py checks this against recordings of the JavaScript.

Each tile is flipped at random, so the arcs join across tiles into one woven pattern of loops and
paths. Complexity sets the tile size (about 4 tiles across at 1, 18 at 10); from complexity 4 up,
each corner has three arcs instead of one, which makes bands. Tiles at the right and bottom edge
are cut off by clipping to the box.
"""

import math


def draw(ctx, box, rnd, c, settings=None, lw=None, **_opts):
    s = box.w / (3 + c * 1.5)
    cols, rows = math.ceil(box.w / s), math.ceil(box.h / s)
    ctx.save()
    ctx.begin_path()
    ctx.rect(box.x, box.y, box.w, box.h)
    ctx.clip()
    radii = [0.3, 0.5, 0.7] if c > 3 else [0.5]
    ctx.begin_path()
    flips = 0
    for y in range(rows):
        for x in range(cols):
            X, Y = box.x + x * s, box.y + y * s
            flip = rnd() < 0.5
            flips += flip
            for k in radii:
                r = k * s
                if flip:      # arcs round the top-left and bottom-right corners
                    ctx.move_to(X + r, Y)
                    ctx.arc(X, Y, r, 0, math.pi / 2)
                    ctx.move_to(X + s - r, Y + s)
                    ctx.arc(X + s, Y + s, r, math.pi, math.pi * 1.5)
                else:         # arcs round the top-right and bottom-left corners
                    ctx.move_to(X + s, Y + r)
                    ctx.arc(X + s, Y, r, math.pi / 2, math.pi)
                    ctx.move_to(X + r, Y + s)
                    ctx.arc(X, Y + s, r, 0, -math.pi / 2, True)
    ctx.stroke()
    ctx.restore()
    return {"cols": cols, "rows": rows, "tile": s, "arcs_per_corner": len(radii), "flipped": flips}
