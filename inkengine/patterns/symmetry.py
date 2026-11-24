"""Symmetry: half a picture of shaded squares on a grid, and a mirror line; the child shades the squares that
make the other half. The answer page shows the whole picture.

The picture is a seeded blob of squares that touches the mirror line, so the halves join up as one shape.
Complexity sets the grid (8 squares across at 1, up to 18 at 10) and, from 7, a second mirror line across the
middle: then one quarter is given and the child completes the other three.
"""

from ..rng import pick

ROWS_FOR_COLS = 1.25   # the grid is a little taller than wide, as a page is


def size_for(c):
    """(columns, rows) of the whole grid: always even, so each half has whole squares."""
    cols = 8 + 2 * ((c - 1) * 5 // 9)
    rows = int(round(cols * ROWS_FOR_COLS / 2)) * 2
    return cols, rows


def make_picture(rnd, c):
    """(cols, rows, quarters, shaded): shaded is the set of (row, col) squares of the given part: the left half,
    or with quarters the top-left quarter, always touching the mirror line(s)."""
    cols, rows = size_for(c)
    quarters = c >= 7
    w, h = cols // 2, rows // 2 if quarters else rows
    target = max(4, int(w * h * (0.32 + 0.02 * pick(rnd, 6))))
    start = (pick(rnd, h), w - 1)   # on the vertical mirror line
    if quarters:
        start = (h - 1, w - 1)      # in the corner where both lines meet
    shaded, edge = {start}, [start]
    tries = 0
    while len(shaded) < target and tries < 5000:
        tries += 1
        r, k = edge[pick(rnd, len(edge))]
        dr, dk = ((0, 1), (1, 0), (0, -1), (-1, 0))[pick(rnd, 4)]
        nr, nk = r + dr, k + dk
        if 0 <= nr < h and 0 <= nk < w and (nr, nk) not in shaded:
            shaded.add((nr, nk))
            edge.append((nr, nk))
    return cols, rows, quarters, shaded


def whole(cols, rows, quarters, shaded):
    """Every square of the finished picture: the given part and its mirror images."""
    out = set()
    for r, k in shaded:
        out |= {(r, k), (r, cols - 1 - k)}
        if quarters:
            out |= {(rows - 1 - r, k), (rows - 1 - r, cols - 1 - k)}
    return out


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    cols, rows, quarters, shaded = make_picture(rnd, c)
    cell = min(box.w / cols, box.h / rows)
    x0 = box.x + (box.w - cell * cols) / 2
    y0 = box.y + (box.h - cell * rows) / 2
    given = shaded
    show = whole(cols, rows, quarters, shaded) if solve else given
    ctx.save()
    for r, k in show:
        ctx.fill_style = "#555" if (r, k) in given else "#aaa"
        ctx.fill_rect(x0 + k * cell, y0 + r * cell, cell, cell)
    ctx.stroke_style, ctx.line_width = "#888", max(1.0, lw * 0.4)
    for i in range(cols + 1):
        ctx.begin_path()
        ctx.move_to(x0 + i * cell, y0)
        ctx.line_to(x0 + i * cell, y0 + rows * cell)
        ctx.stroke()
    for i in range(rows + 1):
        ctx.begin_path()
        ctx.move_to(x0, y0 + i * cell)
        ctx.line_to(x0 + cols * cell, y0 + i * cell)
        ctx.stroke()
    ctx.stroke_style, ctx.line_width = "#000", max(1.5, lw * 1.6)   # the mirror line(s), dashed
    ctx.line_dash = (cell * 0.3, cell * 0.15)
    lines = [((x0 + cols / 2 * cell, y0 - cell * 0.4), (x0 + cols / 2 * cell, y0 + (rows + 0.4) * cell))]
    if quarters:
        lines.append(((x0 - cell * 0.4, y0 + rows / 2 * cell), (x0 + (cols + 0.4) * cell, y0 + rows / 2 * cell)))
    for (ax, ay), (bx, by) in lines:
        ctx.begin_path()
        ctx.move_to(ax, ay)
        ctx.line_to(bx, by)
        ctx.stroke()
    ctx.line_dash = ()
    ctx.stroke_style, ctx.line_width = "#000", max(1.0, lw * 0.9)
    ctx.stroke_rect(x0, y0, cols * cell, rows * cell)
    ctx.restore()
    return {"cols": cols, "rows": rows, "quarters": quarters, "shaded": sorted(shaded)}
