"""Fractions, number lines and times grids: the maths worksheets that are pictures rather than sums.

- Fractions: shapes cut into equal parts (a circle, a bar or a square), some shaded. "What fraction is
  shaded?" with a line to write it, and from complexity 5 also "Shade 3/4" on an empty shape. Halves, thirds
  and quarters at 1-3, up to eighths by 6, up to twelfths at 7-10. The answer page writes each fraction and
  shades the shapes to shade.
- Number lines: lines with evenly spaced marks, some numbered and some left blank to fill in. Counting in ones
  within 20 at 1-2, in twos, fives and tens at 3-4, in tens, twenty-fives and hundreds at 5-6, across zero
  into negative numbers at 7-8, and in tenths at 9-10 (written with the language's decimal comma or point).
- Times grid: a multiplication square with some answers missing: 5 × 5 at 1-3, 8 × 8 at 4-6, 10 × 10 at 7-8,
  12 × 12 at 9-10; more blanks as complexity grows, and from 5 the numbers along the edges are mixed up.
"""

import math

from .. import i18n
from ..i18n import tr
from ..rng import pick

KINDS = {"fractions": "Fractions of shapes", "numberline": "Number lines", "timesgrid": "Times grid"}


def _between(rnd, lo, hi):
    return lo + pick(rnd, hi - lo + 1)


def _shuffle(rnd, items):
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = pick(rnd, i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def decimal(value, places=1):
    """A number with the decimal comma in the languages that use one."""
    text = f"{value:.{places}f}" if places else str(int(round(value)))
    if places and text.endswith("0" * places):
        text = text[: -places - 1]
    return text.replace(".", ",") if i18n.LANG in ("es", "fr", "pt", "de") else text


# --- fractions ------------------------------------------------------------------------------------------

def make_fractions(rnd, c):
    """[(shape, parts, shaded, task)]: task "name" (write the fraction) or "shade" (shade it)."""
    tops = 4 if c <= 3 else 8 if c <= 6 else 12
    count = 6 if c <= 3 else 9
    out, seen, tries = [], set(), 0
    while len(out) < count and tries < 500:
        tries += 1
        n = _between(rnd, 2, tops)
        k = _between(rnd, 1, n - 1)
        shape = ("circle", "bar", "square")[pick(rnd, 3)] if n in (4, 9) else ("circle", "bar")[pick(rnd, 2)]
        task = "shade" if c >= 5 and pick(rnd, 2) else "name"
        if (n, k, task) in seen:
            continue
        seen.add((n, k, task))
        out.append((shape, n, k, task))
    return out


def _parts(shape, n, x, y, w, h):
    """The n equal parts of a shape in the box, as polygons (lists of points)."""
    if shape == "circle":
        cx, cy, r = x + w / 2, y + h / 2, min(w, h) / 2
        out = []
        for i in range(n):
            a0, a1 = -math.pi / 2 + i * 2 * math.pi / n, -math.pi / 2 + (i + 1) * 2 * math.pi / n
            steps = max(2, int(24 / n) + 2)
            arc = [(cx + r * math.cos(a0 + (a1 - a0) * t / steps), cy + r * math.sin(a0 + (a1 - a0) * t / steps))
                   for t in range(steps + 1)]
            out.append([(cx, cy)] + arc)
        return out
    if shape == "square":   # a grid: 4 = 2 × 2, 9 = 3 × 3
        side, m = min(w, h), int(round(math.sqrt(n)))
        sx, sy, cell = x + (w - side) / 2, y + (h - side) / 2, side / m
        return [[(sx + c * cell, sy + r * cell), (sx + (c + 1) * cell, sy + r * cell),
                 (sx + (c + 1) * cell, sy + (r + 1) * cell), (sx + c * cell, sy + (r + 1) * cell)]
                for r in range(m) for c in range(m)]
    bh = h * 0.42   # a bar
    by, cell = y + (h - bh) / 2, w / n
    return [[(x + i * cell, by), (x + (i + 1) * cell, by), (x + (i + 1) * cell, by + bh), (x + i * cell, by + bh)]
            for i in range(n)]


def _poly(ctx, pts):
    ctx.begin_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.line_to(*pts[0])


def _draw_fractions(ctx, box, rnd, c, lw, solve):
    items = make_fractions(rnd, c)
    cols = 3
    rows = -(-len(items) // cols)
    cw, rh = box.w / cols, box.h / rows
    size = min(cw * 0.62, rh * 0.55)
    for k, (shape, n, shaded, task) in enumerate(items):
        col, row = k % cols, k // cols
        x, y = box.x + col * cw + (cw - size) / 2, box.y + row * rh + rh * 0.06
        parts = _parts(shape, n, x, y, size, size)
        fill = shaded if task == "name" or solve else 0
        for i, pts in enumerate(parts):
            if i < fill:
                ctx.fill_style = "#bbb" if task == "shade" else "#888"
                _poly(ctx, pts)
                ctx.fill()
            ctx.line_width, ctx.stroke_style = max(1.0, lw * 0.9), "#000"
            _poly(ctx, pts)
            ctx.stroke()
        ty = y + size + rh * 0.16
        ctx.fill_style = "#000"
        ctx.text_align, ctx.text_baseline = "center", "alphabetic"
        if task == "shade":
            ctx.set_font(rh * 0.075, 600)
            ctx.fill_text(tr("Shade {fraction}").format(fraction=f"{shaded}/{n}"), x + size / 2, ty)
        else:
            ctx.line_width = max(1.0, lw * 0.6)
            ctx.begin_path()
            ctx.move_to(x + size * 0.25, ty)
            ctx.line_to(x + size * 0.75, ty)
            ctx.stroke()
            if solve:
                ctx.set_font(rh * 0.08, 600)
                ctx.fill_style = "#666"
                ctx.fill_text(f"{shaded}/{n}", x + size / 2, ty - rh * 0.01)
                ctx.fill_style = "#000"
    return {"fractions": items}


# --- number lines ---------------------------------------------------------------------------------------

def make_lines(rnd, c):
    """[(start, step, marks, shown)]: each line's first number, the step between marks, how many marks, and
    which marks are numbered (the rest are to fill in). Steps in tenths are kept in tenths (integers / 10)."""
    lines = []
    for _ in range(6):
        if c <= 2:
            step, start = 1, _between(rnd, 0, 10)
        elif c <= 4:
            step = (2, 5, 10)[pick(rnd, 3)]
            start = step * _between(rnd, 0, 8)
        elif c <= 6:
            step = (10, 25, 100)[pick(rnd, 3)]
            start = step * _between(rnd, 0, 10)
        elif c <= 8:
            step = (1, 2, 5)[pick(rnd, 3)]
            start = -step * _between(rnd, 3, 7)
        else:
            step, start = 1, _between(rnd, 0, 30)   # tenths: 1 = 0.1
        marks = 9 if c <= 4 else 11
        blanks = 2 if c <= 2 else 3 if c <= 6 else 4
        hidden = set()
        while len(hidden) < blanks:
            hidden.add(_between(rnd, 1, marks - 1))   # the first mark always shows where the line starts
        lines.append((start, step, marks, [i not in hidden for i in range(marks)], c >= 9))
    return lines


def _draw_lines(ctx, box, rnd, c, lw, solve):
    lines = make_lines(rnd, c)
    rh = box.h / len(lines)
    for r, (start, step, marks, shown, tenths) in enumerate(lines):
        y = box.y + r * rh + rh * 0.42
        x0, x1 = box.x + box.w * 0.04, box.x + box.w * 0.96
        gap = (x1 - x0) / (marks - 1)
        ctx.line_width, ctx.stroke_style = max(1.0, lw * 1.0), "#000"
        ctx.begin_path()   # the line, with an arrow at each end
        ctx.move_to(x0 - gap * 0.35, y)
        ctx.line_to(x1 + gap * 0.35, y)
        ctx.stroke()
        for ax, d in ((x0 - gap * 0.35, 1), (x1 + gap * 0.35, -1)):
            ctx.begin_path()
            ctx.move_to(ax + d * rh * 0.06, y - rh * 0.05)
            ctx.line_to(ax, y)
            ctx.line_to(ax + d * rh * 0.06, y + rh * 0.05)
            ctx.stroke()
        fs = min(rh * 0.2, gap * 0.42)
        for i in range(marks):
            x = x0 + i * gap
            ctx.begin_path()
            ctx.move_to(x, y - rh * 0.08)
            ctx.line_to(x, y + rh * 0.08)
            ctx.stroke()
            value = start + i * step
            text = decimal(value / 10) if tenths else str(value).replace("-", "−")
            ctx.text_align, ctx.text_baseline = "center", "alphabetic"
            ty = y + rh * 0.08 + fs * 1.25
            if shown[i]:
                ctx.set_font(fs, 600)
                ctx.fill_style = "#000"
                ctx.fill_text(text, x, ty)
            else:   # a box to write the missing number in
                bw, bh = gap * 0.8, fs * 1.35
                ctx.line_width = max(1.0, lw * 0.6)
                ctx.stroke_rect(x - bw / 2, ty - fs * 1.05, bw, bh)
                ctx.line_width = max(1.0, lw * 1.0)
                if solve:
                    ctx.set_font(fs, 600)
                    ctx.fill_style = "#666"
                    ctx.fill_text(text, x, ty)
                    ctx.fill_style = "#000"
    return {"lines": lines}


# --- times grid -----------------------------------------------------------------------------------------

def make_grid(rnd, c):
    """(across, down, blanks): the numbers along the top and the side, and which cells are left to fill."""
    n = 5 if c <= 3 else 8 if c <= 6 else 10 if c <= 8 else 12
    across, down = list(range(1, n + 1)), list(range(1, n + 1))
    if c >= 5:
        across, down = _shuffle(rnd, across), _shuffle(rnd, down)
    share = [0.35, 0.45, 0.55, 0.5, 0.6, 0.7, 0.65, 0.8, 0.85, 1.0][c - 1]
    cells = [(r, k) for r in range(n) for k in range(n)]
    blanks = set(_shuffle(rnd, cells)[: max(1, round(len(cells) * share))])
    return across, down, blanks


def _draw_grid(ctx, box, rnd, c, lw, solve):
    across, down, blanks = make_grid(rnd, c)
    n = len(across)
    side = min(box.w, box.h)
    cell = side / (n + 1)
    x0, y0 = box.x + (box.w - side) / 2, box.y
    fs = cell * 0.42
    ctx.text_align, ctx.text_baseline = "center", "middle"
    ctx.fill_style = "#ddd"   # the edges, shaded
    ctx.fill_rect(x0, y0, side, cell)
    ctx.fill_rect(x0, y0, cell, side)
    ctx.fill_style = "#000"
    ctx.set_font(fs * 1.1, 700)
    ctx.fill_text("×", x0 + cell / 2, y0 + cell / 2)
    for i in range(n):
        ctx.fill_text(str(across[i]), x0 + (i + 1.5) * cell, y0 + cell / 2)
        ctx.fill_text(str(down[i]), x0 + cell / 2, y0 + (i + 1.5) * cell)
    for r in range(n):
        for k in range(n):
            blank = (r, k) in blanks
            if blank and not solve:
                continue
            ctx.set_font(fs, 600 if not blank else 500)
            ctx.fill_style = "#666" if blank else "#000"
            ctx.fill_text(str(down[r] * across[k]), x0 + (k + 1.5) * cell, y0 + (r + 1.5) * cell)
    ctx.fill_style = "#000"
    ctx.line_width, ctx.stroke_style = max(1.0, lw * 0.6), "#000"
    for i in range(n + 2):
        ctx.begin_path()
        ctx.move_to(x0 + i * cell, y0)
        ctx.line_to(x0 + i * cell, y0 + side)
        ctx.stroke()
        ctx.begin_path()
        ctx.move_to(x0, y0 + i * cell)
        ctx.line_to(x0 + side, y0 + i * cell)
        ctx.stroke()
    return {"across": across, "down": down, "blanks": sorted(blanks)}


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    kind = getattr(settings, "frac_kind", "fractions")
    ctx.save()
    if kind == "numberline":
        out = _draw_lines(ctx, box, rnd, c, lw, solve)
    elif kind == "timesgrid":
        out = _draw_grid(ctx, box, rnd, c, lw, solve)
    else:
        out = _draw_fractions(ctx, box, rnd, c, lw, solve)
    ctx.restore()
    return out
