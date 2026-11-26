"""Early maths with pictures, for ages 4-6: things to count or complete, drawn rather than written in numbers.

- Ten frames: a 2 x 5 frame (two of them past 10) with some spaces filled; write how many.
- Number bonds: a whole in the top circle, its two parts below, one of the three left empty to fill in.
- Place value: tens as rods of ten cubes and ones as single cubes; write the number.
- Counting: a few shapes scattered in a box; write how many.

Complexity sets the numbers: up to 10 at 1-3, up to 20 at 4-7, and for place value up to 50 then 99. The seed
picks them, each different from the one before. Every picture has a box to write in; the answer page writes the
answers in them, in grey.
"""

import math

from ..rng import pick

KINDS = {"tenframe": "Ten frames", "bonds": "Number bonds", "placevalue": "Place value (tens and ones)",
         "counting": "Counting"}
GRID = {"tenframe": (2, 4), "bonds": (3, 3), "placevalue": (2, 3), "counting": (2, 4)}   # columns, rows
SHAPES = ("circle", "square", "triangle", "star")


def top(kind, c):
    """The largest number at complexity c."""
    if kind == "placevalue":
        return 30 if c <= 3 else 50 if c <= 6 else 99
    return 10 if c <= 3 else 20


def make_items(rnd, c, kind):
    """The sheet: [(answer, details)], no number twice in a row."""
    cols, rows = GRID[kind]
    hi = top(kind, c)
    lo = {"placevalue": 11, "bonds": 3, "counting": 2}.get(kind, 1)   # no "1 + 1", nothing to count but one
    out, last = [], None
    for _ in range(cols * rows):
        n = last
        while n == last:
            n = lo + pick(rnd, hi - lo + 1)
        last = n
        if kind == "bonds":
            a = 1 + pick(rnd, n - 1)
            blank = pick(rnd, 3)   # 0: the whole, 1: the left part, 2: the right part
            parts = (n, a, n - a)
            out.append((parts[blank], {"parts": parts, "blank": blank}))
        elif kind == "counting":
            out.append((n, {"shape": SHAPES[pick(rnd, len(SHAPES))], "seed": pick(rnd, 1 << 30)}))
        else:
            out.append((n, {}))
    return out


def _answer_box(ctx, x, y, s, lw, text=None):
    ctx.line_width = max(1.0, lw * 0.8)
    ctx.stroke_rect(x, y, s, s)
    if text is not None:
        ctx.fill_style = "#666"
        ctx.set_font(s * 0.55, 600)
        ctx.text_align, ctx.text_baseline = "center", "middle"
        ctx.fill_text(str(text), x + s / 2, y + s / 2)
        ctx.fill_style = "#000"


def _ten_frame(ctx, x, y, w, n, lw):
    """One 2 x 5 frame, w wide, its first n spaces filled (left to right, top row first); returns its height."""
    cell = w / 5
    ctx.line_width = max(1.0, lw * 0.9)
    for r in range(2):
        for k in range(5):
            ctx.stroke_rect(x + k * cell, y + r * cell, cell, cell)
            if r * 5 + k < n:
                ctx.begin_path()
                ctx.arc(x + (k + 0.5) * cell, y + (r + 0.5) * cell, cell * 0.32, 0, 2 * math.pi)
                ctx.fill()
    return cell * 2


def _shape(ctx, kind, cx, cy, r):
    ctx.begin_path()
    if kind == "circle":
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
    elif kind == "square":
        ctx.move_to(cx - r, cy - r)
        for px, py in ((cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)):
            ctx.line_to(px, py)
        ctx.close_path()
    elif kind == "triangle":
        ctx.move_to(cx, cy - r)
        ctx.line_to(cx + r, cy + r * 0.8)
        ctx.line_to(cx - r, cy + r * 0.8)
        ctx.close_path()
    else:
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            (ctx.move_to if k == 0 else ctx.line_to)(cx + rr * math.cos(a), cy + rr * math.sin(a))
        ctx.close_path()
    ctx.stroke()


def _scatter(n, seed, w, h, r):
    """n spots in a w x h box, at least 2.4 r apart where there's room (seeded, so the same sheet again)."""
    from ..rng import mulberry32
    rnd = mulberry32(seed)
    spots = []
    for _ in range(n):
        best = None
        for _try in range(40):
            p = (r + rnd() * (w - 2 * r), r + rnd() * (h - 2 * r))
            gap = min((math.dist(p, q) for q in spots), default=1e9)
            if best is None or gap > best[0]:
                best = (gap, p)
            if gap >= r * 2.4:
                break
        spots.append(best[1])
    return spots


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    kind = getattr(settings, "early_kind", "tenframe")
    kind = kind if kind in KINDS else "tenframe"
    items = make_items(rnd, c, kind)
    cols, rows = GRID[kind]
    cw, ch = box.w / cols, box.h / rows
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    for k, (answer, d) in enumerate(items):
        cx0, cy0 = box.x + (k % cols) * cw, box.y + (k // cols) * ch
        pad = min(cw, ch) * 0.08
        x, y, w, h = cx0 + pad, cy0 + pad, cw - 2 * pad, ch - 2 * pad
        ctx.set_font(min(w, h) * 0.09, 400)
        ctx.fill_style = "#666"
        ctx.text_align, ctx.text_baseline = "left", "top"
        ctx.fill_text(f"{k + 1}.", x, y)
        ctx.fill_style = "#000"
        box_s = min(w, h) * 0.26
        fill = answer if solve else None
        if kind == "tenframe":
            fw = min(w * 0.62, (h - box_s) * 1.1)
            n = answer
            fy = y + h * 0.12
            fh = _ten_frame(ctx, x + w * 0.04, fy, fw, min(n, 10), lw)
            if n > 10 or top(kind, c) > 10:
                _ten_frame(ctx, x + w * 0.04, fy + fh + fw * 0.08, fw, max(0, n - 10), lw)
            _answer_box(ctx, x + w - box_s, y + h / 2 - box_s / 2, box_s, lw, fill)
        elif kind == "bonds":
            whole, a, b = d["parts"]
            r = min(w * 0.17, h * 0.17)
            spots = [(x + w / 2, y + r + h * 0.08), (x + w * 0.25, y + h - r - h * 0.06),
                     (x + w * 0.75, y + h - r - h * 0.06)]
            ctx.line_width = max(1.0, lw * 0.9)
            for sx, sy in spots[1:]:
                ctx.begin_path()
                ctx.move_to(*spots[0])
                ctx.line_to(sx, sy)
                ctx.stroke()
            for i, ((sx, sy), v) in enumerate(zip(spots, (whole, a, b))):
                ctx.fill_style = "#fff"
                ctx.begin_path()
                ctx.arc(sx, sy, r, 0, 2 * math.pi)
                ctx.fill()
                ctx.fill_style = "#000"
                ctx.stroke()
                ctx.text_align, ctx.text_baseline = "center", "middle"
                if i != d["blank"]:
                    ctx.set_font(r * 0.9, 600)
                    ctx.fill_text(str(v), sx, sy)
                elif solve:
                    ctx.set_font(r * 0.9, 600)
                    ctx.fill_style = "#666"
                    ctx.fill_text(str(v), sx, sy)
                    ctx.fill_style = "#000"
        elif kind == "placevalue":
            tens, ones = divmod(answer, 10)
            most = top(kind, c) // 10   # the same cube size on every picture: room for the most tens there can be
            room = w - box_s - w * 0.1
            cube = min(room / (most * 1.4 + 3.4), h * 0.7 / 10)
            px, py = x + w * 0.03, y + h * 0.15
            ctx.line_width = max(1.0, lw * 0.7)
            for t in range(tens):   # a rod: ten cubes in a column
                for q in range(10):
                    ctx.stroke_rect(px + t * cube * 1.4, py + q * cube, cube, cube)
            ox = px + tens * cube * 1.4 + cube * 0.8
            for o in range(ones):   # ones: single cubes, in twos up the page
                ctx.stroke_rect(ox + (o % 2) * cube * 1.3, py + 10 * cube - (o // 2 + 1) * cube * 1.3, cube, cube)
            _answer_box(ctx, x + w - box_s, y + h / 2 - box_s / 2, box_s, lw, fill)
        else:   # counting
            aw, ah = w - box_s - w * 0.08, h * 0.82
            r = min(aw, ah) * (0.075 if answer <= 10 else 0.06)
            ctx.line_width = max(1.0, lw * 0.6)
            ctx.stroke_rect(x, y + h * 0.12, aw, ah - h * 0.04)
            ctx.line_width = max(1.0, lw * 0.9)
            for sx, sy in _scatter(answer, d["seed"], aw - r, ah - h * 0.08 - r, r):
                _shape(ctx, d["shape"], x + r * 0.5 + sx, y + h * 0.12 + r * 0.5 + sy, r)
            _answer_box(ctx, x + w - box_s, y + h / 2 - box_s / 2, box_s, lw, fill)
    ctx.restore()
    return {"kind": kind, "answers": [a for a, _d in items]}

