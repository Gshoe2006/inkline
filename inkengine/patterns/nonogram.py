"""Nonograms: shade squares so each row and column has the runs its clue lists, and a picture appears.

Ported line for line from index.html (makeNonogram, nonoLine, solveNonogram, drawNonogram), so a
seed gives the same puzzle as Inkline 2.x. tests/test_nonogram.py checks this against recordings
of the JavaScript.

Pictures are random, mirrored left to right and smoothed once, so they read as shapes rather than
static. One is kept only if line-by-line logic alone solves it completely, which also proves it has
exactly one solution: no guessing is ever needed. Complexity sets the size, 5x5 at 1 up to 20x20 at
10. draw_nonogram also takes squares printed already shaded (givens), for photo nonograms later.
"""

import math
from ..i18n import tr

SLOT = 0.7   # a clue number takes 0.7 of a square


def runs(line):
    """The lengths of the shaded runs in a line, in order."""
    out, k = [], 0
    for x in line:
        if x:
            k += 1
        elif k:
            out.append(k)
            k = 0
    if k:
        out.append(k)
    return out


def size_for(c):
    return 5 + int(math.floor((c - 1) * 15 / 9 + 0.5))


def solve_line(clue, line):
    """Everything one line's clue forces, given what's known (1 shaded, 0 blank, -1 unknown); None if
    impossible. can[j][i]: runs j.. fit in cells i..; every reachable placement then marks which cells
    could be shaded and which could be blank."""
    n, m = len(line), len(clue)
    can = [[False] * (n + 1) for _ in range(m + 1)]
    can[m][n] = True
    for i in range(n - 1, -1, -1):
        can[m][i] = can[m][i + 1] and line[i] != 1

    def fits(i, L):
        return i + L <= n and 0 not in line[i:i + L]

    def after(j, i, L):
        if j == m - 1:
            return can[m][i + L]
        return i + L < n and line[i + L] != 1 and can[j + 1][i + L + 1]

    for j in range(m - 1, -1, -1):
        L, row = clue[j], can[j]
        for i in range(n - 1, -1, -1):
            row[i] = (line[i] != 1 and row[i + 1]) or (fits(i, L) and after(j, i, L))
    if not can[0][0]:
        return None
    shade, blank = [False] * n, [False] * n
    seen, todo = set(), [(0, 0)]
    while todo:
        j, i = todo.pop()
        if (j, i) in seen:
            continue
        seen.add((j, i))
        if j == m:
            for k in range(i, n):
                blank[k] = True
            continue
        if i >= n:
            continue
        if line[i] != 1 and can[j][i + 1]:
            blank[i] = True
            todo.append((j, i + 1))
        L = clue[j]
        if fits(i, L) and after(j, i, L):
            for k in range(i, i + L):
                shade[k] = True
            if j == m - 1:
                todo.append((m, i + L))
            else:
                blank[i + L] = True
                todo.append((j + 1, i + L + 1))
    return [-1 if shade[k] and blank[k] else 1 if shade[k] else 0 for k in range(n)]


def solve(rows, cols, start=None):
    """Apply every row and column until nothing changes. The grid (-1 where logic can't decide), or None.
    start: squares already known, -1 elsewhere."""
    h, w = len(rows), len(cols)
    g = list(start) if start is not None else [-1] * (w * h)
    changed = True
    while changed:
        changed = False
        for r in range(h):
            line = g[r * w:r * w + w]
            out = solve_line(rows[r], line)
            if out is None:
                return None
            if out != line:
                g[r * w:r * w + w] = out
                changed = True
        for c in range(w):
            line = g[c::w]
            out = solve_line(cols[c], line)
            if out is None:
                return None
            if out != line:
                g[c::w] = out
                changed = True
    return g


def clues(pic, w, h=None):
    h = w if h is None else h
    return ([runs(pic[r * w:r * w + w]) for r in range(h)], [runs(pic[c::w][:h]) for c in range(w)])


def make_nonogram(rnd, c):
    n = size_for(c)
    half = math.ceil(n / 2)
    for attempt in range(2000):
        noise = [0] * (n * n)
        for r in range(n):
            for col in range(half):
                noise[r * n + col] = noise[r * n + n - 1 - col] = 1 if rnd() < 0.5 else 0
        # shaded where most of the 3x3 round it is (the rule is symmetric, so the mirror holds)
        pic = []
        for i in range(n * n):
            r, col, k = i // n, i % n, 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, col + dc
                    if 0 <= rr < n and 0 <= cc < n:
                        k += noise[rr * n + cc]
            pic.append(1 if k >= 5 else 0)
        ink = sum(pic) / (n * n)
        if ink < 0.4 or ink > 0.65:   # too empty is dull, too full is just a block
            continue
        rows, cols = clues(pic, n)
        solved = solve(rows, cols)
        if solved is not None and solved == pic:
            return {"size": n, "w": n, "h": n, "pic": pic, "rows": rows, "cols": cols, "givens": None,
                    "attempts": attempt + 1}
    return None   # practically never: about half of all in-range pictures solve on their own


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    nono = make_nonogram(rnd, c)
    if nono:
        draw_nonogram(ctx, box, dpi, lw, nono, solve)
    return nono


def draw_nonogram(ctx, box, dpi, lw, nono, solve=False):
    """A w x h nonogram: clues, grid and caption, or (solve=True) the finished picture."""
    w, h, pic, rows, cols, givens = nono["w"], nono["h"], nono["pic"], nono["rows"], nono["cols"], nono.get("givens")
    cap = 0 if solve else min(box.h * 0.1, dpi * 0.45)
    across = 0 if solve else max(max(1, len(r)) for r in rows) * SLOT + 0.3
    down = 0 if solve else max(max(1, len(r)) for r in cols) * SLOT + 0.3
    cs = min(box.w / (w + across), (box.h - cap) / (h + down)) * 0.96
    x0 = box.x + (box.w - (w + across) * cs) / 2 + across * cs
    y0 = box.y + (box.h - cap - (h + down) * cs) / 2 + down * cs
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.line_cap = "square"
    for i in range(w * h):
        if (pic[i] if solve else givens and givens[i]):
            ctx.fill_rect(x0 + (i % w) * cs, y0 + (i // w) * cs, cs, cs)
    for k in range(max(w, h) + 1):   # thin square lines, a thicker line every 5, thickest border
        ctx.begin_path()
        if k <= w:
            ctx.line_width = lw * 1.3 if k in (0, w) else lw * 0.35 if k % 5 else lw
            ctx.move_to(x0 + k * cs, y0)
            ctx.line_to(x0 + k * cs, y0 + h * cs)
            ctx.stroke()
            ctx.begin_path()
        if k <= h:
            ctx.line_width = lw * 1.3 if k in (0, h) else lw * 0.35 if k % 5 else lw
            ctx.move_to(x0, y0 + k * cs)
            ctx.line_to(x0 + w * cs, y0 + k * cs)
            ctx.stroke()
    side = h * cs
    if not solve:
        fs, gap = cs * 0.5, cs * 0.3
        ctx.set_font(fs, 600)
        ctx.text_baseline = "alphabetic"
        ctx.text_align = "right"    # row clues read left to right, ending beside the grid
        for r, clue in enumerate(rows):
            t = clue or [0]
            for k, x in enumerate(t):
                ctx.fill_text(str(x), x0 - gap - (len(t) - 1 - k) * SLOT * cs, y0 + (r + 0.5) * cs + fs * 0.36)
        ctx.text_align = "center"   # column clues read top to bottom, ending above the grid
        for col, clue in enumerate(cols):
            t = clue or [0]
            for k, x in enumerate(t):
                ctx.fill_text(str(x), x0 + (col + 0.5) * cs, y0 - gap - (len(t) - 1 - k) * SLOT * cs)
        fc, mid = min(dpi * 0.13, cap * 0.32), box.x + box.w / 2
        ctx.set_font(fc, 400)
        ctx.fill_style = "#555"
        n_given = sum(givens) if givens else 0
        if n_given:
            line = (tr("{w} × {h} · shade squares to find the picture · {n} squares shaded to start you off") if n_given > 1
                    else tr("{w} × {h} · shade squares to find the picture · 1 square shaded to start you off"))
        else:
            line = tr("{w} × {h} · shade squares to find the picture")
        ctx.fill_text(line.format(w=w, h=h, n=n_given), mid, y0 + side + cap * 0.42, box.w)
        ctx.fill_text(tr("Each number is a run of shaded squares, in order, with at least one gap between runs."),
                      mid, y0 + side + cap * 0.42 + fc * 1.5, box.w)
    ctx.restore()
