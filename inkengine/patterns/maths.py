"""Maths drills: a sheet of sums to work out, each copy different, with the answers on an answer page.

The kind of sum is a setting (adding, taking away, both, times tables, number bonds, or all of them mixed);
Complexity sets how big the numbers get and how many sums there are:

- adding / taking away: within 10 at 1, within 20 at 2-3, within 100 by 6, up to 1000 at 10. Taking away
  never goes below zero.
- times tables: the 2, 5 and 10 times tables at 1, up to the 12 times table at 10.
- number bonds: "7 + _ = 10" or "_ + 3 = 10", making 10 at 1-3, 20 at 4-6, 100 at 7-10.

Sums are written across ("7 + 5 = ____"), in two or three columns depending on how many there are. The
answer page writes each answer in its blank, in grey.
"""

from ..rng import pick

KINDS = {"add": "Adding", "sub": "Taking away", "addsub": "Adding and taking away", "times": "Times tables",
         "bonds": "Number bonds", "mixed": "All of them, mixed"}


def level(c):
    """How many sums, and the largest number for adding and taking away, at complexity c (1..10)."""
    top = [10, 20, 20, 50, 50, 100, 100, 200, 500, 1000][c - 1]
    return {"count": [12, 15, 18, 20, 21, 24, 24, 27, 30, 30][c - 1], "top": top,
            "tables": [[2, 5, 10], [2, 3, 5, 10], [2, 3, 4, 5, 10], list(range(2, 7)) + [10], list(range(2, 9)) + [10],
                       list(range(2, 11)), list(range(2, 11)), list(range(2, 12)), list(range(2, 13)),
                       list(range(2, 13))][c - 1],
            "bond": 10 if c <= 3 else 20 if c <= 6 else 100}


def _between(rnd, lo, hi):
    return lo + pick(rnd, hi - lo + 1)


def make_sum(rnd, kind, lv):
    """One sum: (left, sign, right, answer, blank) where blank says what the child writes: the "result", or for a
    number bond the missing number on the "right" (7 + _ = 10) or the "left" (_ + 3 = 10)."""
    if kind == "mixed":
        kind = ["add", "sub", "times", "bonds"][pick(rnd, 4)]
    if kind == "addsub":
        kind = "add" if pick(rnd, 2) == 0 else "sub"
    top = lv["top"]
    # the smallest numbers grow with the largest: "+ 1" only within 10, and no "5 − 3" among sums to 1000
    lo = 1 if top <= 10 else max(2, top // 20)
    if kind == "add":
        a = _between(rnd, lo, top - lo)
        b = _between(rnd, lo, top - a)
        return a, "+", b, a + b, "result"
    if kind == "sub":
        a = _between(rnd, 2 * lo, top)
        b = _between(rnd, lo, a - lo) if a - lo >= lo else lo
        return a, "−", b, a - b, "result"
    if kind == "times":
        t = lv["tables"][pick(rnd, len(lv["tables"]))]
        n = _between(rnd, 1, 12)
        return (n, "×", t, n * t, "result") if pick(rnd, 2) else (t, "×", n, n * t, "result")
    total = lv["bond"]   # number bonds: a + _ = total, or _ + b = total
    a = _between(rnd, 1, total - 1)
    return a, "+", total - a, total, "right" if pick(rnd, 2) else "left"


def make_sheet(rnd, c, kind):
    """The sums for one sheet: no sum twice."""
    lv, sums, seen = level(c), [], set()
    tries = 0
    while len(sums) < lv["count"] and tries < 2000:
        tries += 1
        s = make_sum(rnd, kind, lv)
        key = (s[0], s[1], s[2], s[4])   # the numbers, and where the blank is
        if key not in seen:
            seen.add(key)
            sums.append(s)
    return sums


BLANK = 2.4   # the blank to write in, in font sizes


def _pieces(s):
    """Sum s as (text before the blank, text after it, what goes in the blank)."""
    a, sign, b, answer, missing = s
    if missing == "left":
        return "", f" {sign} {b} = {answer}", a
    if missing == "right":
        return f"{a} {sign} ", f" = {answer}", b
    return f"{a} {sign} {b} = ", "", answer


def _width(ctx, n, s, blank=BLANK):
    """How wide sum s is written, at the current font size (its number, the sum, the blank)."""
    before, after, _fill = _pieces(s)
    size = ctx.font_size
    return size * 1.5 + ctx.measure_text(before) + size * blank + ctx.measure_text(after)


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The sheet of sums (or, with solve=True, each answer written in its blank)."""
    kind = getattr(settings, "maths_kind", "add")
    kind = kind if kind in KINDS else "add"
    sums = make_sheet(rnd, c, kind)
    cols = 2 if len(sums) <= 18 else 3
    rows = -(-len(sums) // cols)
    cw, rh = box.w / cols, box.h / rows
    ctx.save()
    # as large as the rows allow, but every sum (number, sum, blank, a bond's "= 10") inside its column
    ctx.set_font(100, 500)
    digits = max(len(str(_pieces(s)[2])) for s in sums)
    blank_fs = max(BLANK, 0.75 * digits + 1.0)   # room for the longest answer in a child's writing
    widest = max(_width(ctx, len(sums), s, blank_fs) for s in sums) / 100
    fs = min(rh * 0.42, cw * 0.9 / widest, dpi * 0.36)
    blank = fs * blank_fs
    ctx.text_baseline, ctx.text_align = "alphabetic", "left"
    for k, s in enumerate(sums):
        before, after, fill = _pieces(s)
        col, row = k // rows, k % rows
        x, y = box.x + col * cw + cw * 0.06, box.y + row * rh + rh * 0.62
        ctx.set_font(fs * 0.55, 400)
        ctx.fill_style = "#666"
        ctx.fill_text(f"{k + 1}.", x, y)
        x += fs * 1.5
        ctx.set_font(fs, 500)
        ctx.fill_style = "#000"
        ctx.fill_text(before, x, y)
        x += ctx.measure_text(before)
        ctx.line_width = max(1.0, lw * 0.6)   # the blank to write in
        ctx.begin_path()
        ctx.move_to(x, y + fs * 0.12)
        ctx.line_to(x + blank, y + fs * 0.12)
        ctx.stroke()
        if solve:
            ctx.fill_style = "#666"
            ctx.text_align = "center"
            ctx.fill_text(str(fill), x + blank / 2, y - fs * 0.08)   # just above the line
            ctx.text_align = "left"
            ctx.fill_style = "#000"
        ctx.fill_text(after, x + blank, y)
    ctx.restore()
    return {"sums": sums, "kind": kind}
