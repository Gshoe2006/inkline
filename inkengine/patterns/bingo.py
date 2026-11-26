"""Bingo: a card to mark as things are called, a different one for every child, and the caller's sheet.

- Numbers: 1-20 on a 3 x 3 card, 1-40 on 4 x 4, and the classic 1-75 on 5 x 5 under B I N G O (each column
  from its own fifteen, a free square in the middle).
- Words: from a theme (the word search's, sight words and seasons among them) or your own list.
- Sums: the card has answers, the caller reads out the sums (adding within 20 for the youngest, adding and
  taking away within 30, then times tables).

Complexity sets the card: 3 x 3 at 1-3, 4 x 4 at 4-7, 5 x 5 at 8-10. The seed picks and places what's on the
card, so copies (Paper → Copies, or Names for a class set) each get their own; what can be called depends only
on the kind, the complexity and the words, so one caller's sheet serves every card. The caller's sheet is the
answer page: everything that can be called, in boxes to tick off or cut out and draw from a hat.
"""

import re

from .. import i18n
from ..i18n import tr
from ..rng import mulberry32
from . import words

KINDS = {"numbers": "Numbers", "words": "Words", "sums": "Sums (the caller reads them out)"}
COLUMNS = "BINGO"
MAX_POOL = 40   # words or sums that can be called: enough for every card to differ, few enough for a caller


def size_for(c):
    return 3 if c <= 3 else 4 if c <= 7 else 5


def _shuffle(items, rnd):
    for i in range(len(items) - 1, 0, -1):
        j = int(rnd() * (i + 1)) % (i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def _sums(c):
    """[(answer, sum)] to call: one sum for each answer, the same every time for this complexity."""
    rnd = mulberry32(0xB1260 + c)
    out = []
    if c <= 3:
        for ans in range(2, 21):
            a = 1 + int(rnd() * (ans - 1))
            out.append((str(ans), f"{a} + {ans - a}"))
    elif c <= 7:
        for ans in range(0, 31):
            if rnd() < 0.5 and ans <= 25:
                b = 1 + int(rnd() * 9)
                out.append((str(ans), f"{ans + b} − {b}"))
            else:
                a = int(rnd() * (ans + 1))
                out.append((str(ans), f"{a} + {ans - a}"))
    else:
        seen = {}
        for a in range(2, 11):
            for b in range(a, 11):
                seen.setdefault(a * b, (a, b))
        for prod in sorted(seen):
            a, b = seen[prod]
            if rnd() < 0.5:
                a, b = b, a
            out.append((str(prod), f"{a} × {b}"))
    if len(out) > MAX_POOL:   # a caller's sheet that fits: a seeded pick, in order
        keep = set(_shuffle(list(range(len(out))), rnd)[:MAX_POOL])
        out = [x for i, x in enumerate(out) if i in keep]
    return out


def _words(settings):
    """The words to call: your own list, or the theme's, in the current language, without repeats."""
    theme = getattr(settings, "bingo_theme", "animals") or "animals"
    raw = []
    if theme == "custom":
        raw = [w.strip() for w in re.split(r"[\n,;]+", getattr(settings, "bingo_words", "") or "") if w.strip()]
        if len(raw) <= 1:   # one line of words separated by spaces
            raw = (getattr(settings, "bingo_words", "") or "").split()
    if not raw:
        themes = words.THEMES_BY_LANGUAGE.get(i18n.LANG, words.THEMES)
        raw = themes.get(theme if theme in themes else "animals", themes["animals"]).split()
    out = []
    for w in raw:
        if w.lower() not in (x.lower() for x in out):
            out.append(w)
    return out[:MAX_POOL]


def pool(c, settings=None):
    """Everything that can be called: [(what's on the card, what the caller says)]."""
    kind = getattr(settings, "bingo_kind", "numbers")
    n = size_for(c)
    if kind == "sums":
        return _sums(c)
    if kind == "words":
        return [(w, w) for w in _words(settings)]
    top = {3: 20, 4: 40, 5: 75}[n]
    return [(str(k), (f"{COLUMNS[(k - 1) // 15]} {k}" if n == 5 else str(k))) for k in range(1, top + 1)]


def card(rnd, c, settings=None):
    """The card: rows of what's in each square (None for the free square), or None if there's too little to
    call for a card this size (a short list of your own makes a smaller card)."""
    kind = getattr(settings, "bingo_kind", "numbers")
    items = [shown for shown, _ in pool(c, settings)]
    n = size_for(c)
    squares = lambda k: k * k - (1 if k == 5 else 0)
    while n > 3 and len(items) < squares(n) + 2:   # a short list: a smaller card, so cards still differ
        n -= 1
    free, need = n == 5, squares(n)
    if len(items) < need:
        return None
    if kind == "numbers" and n == 5:   # each column from its own fifteen, in order down the column
        cols = []
        for k in range(5):
            col = sorted(_shuffle(list(range(15 * k + 1, 15 * k + 16)), rnd)[:5 if k != 2 else 4])
            if k == 2:
                col.insert(2, None)
            cols.append([None if v is None else str(v) for v in col])
        return [[cols[k][r] for k in range(5)] for r in range(5)]
    picked = _shuffle(items[:], rnd)[:need]
    if free:
        picked.insert(need // 2, None)
    return [picked[r * n:(r + 1) * n] for r in range(n)]


def _fit(ctx, text, w, fs, weight=600):
    """The font size (at most fs) at which text fits in w."""
    ctx.set_font(fs, weight)
    wide = ctx.measure_text(text)
    return fs if wide <= w else max(fs * 0.35, fs * w / wide)


def _draw_card(ctx, box, grid, lw, kind):
    n = len(grid)
    classic = kind == "numbers" and n == 5
    head = min(box.w, box.h) * (0.12 if classic else 0.1)
    cell = min(box.w / n, (box.h - head * 1.2) / n)
    x0 = box.x + (box.w - cell * n) / 2
    y0 = box.y + (box.h - cell * n - head * 1.2) / 2 + head * 1.2
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_align, ctx.text_baseline = "center", "middle"
    if classic:
        ctx.set_font(head * 0.85, 800)
        for k, letter in enumerate(COLUMNS):
            ctx.fill_text(letter, x0 + (k + 0.5) * cell, y0 - head * 0.6)
    else:
        ctx.set_font(head * 0.8, 800)
        ctx.fill_text(tr("Bingo").upper(), box.x + box.w / 2, y0 - head * 0.6)
    ctx.line_width = max(1.5, lw * 1.6)
    ctx.stroke_rect(x0, y0, cell * n, cell * n)
    ctx.line_width = max(1.0, lw * 0.9)
    for k in range(1, n):
        ctx.begin_path()
        ctx.move_to(x0 + k * cell, y0)
        ctx.line_to(x0 + k * cell, y0 + n * cell)
        ctx.move_to(x0, y0 + k * cell)
        ctx.line_to(x0 + n * cell, y0 + k * cell)
        ctx.stroke()
    base = cell * (0.42 if kind != "words" else 0.3)
    longest = max((t for row in grid for t in row if t), key=lambda t: len(t), default="")
    fs = _fit(ctx, longest, cell * 0.86, base)   # one size for the whole card
    for r, row in enumerate(grid):
        for k, text in enumerate(row):
            cx, cy = x0 + (k + 0.5) * cell, y0 + (r + 0.5) * cell
            if text is None:
                ctx.set_font(_fit(ctx, tr("FREE"), cell * 0.8, cell * 0.24, 800), 800)
                ctx.fill_text(tr("FREE"), cx, cy)
                ctx.begin_path()
                ctx.arc(cx, cy, cell * 0.42, 0, 6.2832)
                ctx.stroke()
            else:
                ctx.set_font(fs, 600)
                ctx.fill_text(text, cx, cy)


def _draw_caller(ctx, box, items, lw, kind, c):
    """Everything that can be called, in boxes: the classic card's under B I N G O, the rest in rows."""
    title = min(box.w, box.h) * 0.06
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_align, ctx.text_baseline = "center", "middle"
    ctx.set_font(title * 0.8, 800)
    ctx.fill_text(tr("Caller's sheet"), box.x + box.w / 2, box.y + title * 0.6)
    top = box.y + title * 1.4
    count = len(items)
    if kind == "numbers" and size_for(c) == 5:
        cols, rows = 5, 15
        order = [items[k * 15 + r] if k * 15 + r < count else None for r in range(rows) for k in range(cols)]
    else:
        cols = 4 if kind != "numbers" else 5
        rows = -(-count // cols)
        order = items + [None] * (rows * cols - count)
    cw, ch = box.w / cols, (box.y + box.h - top) / rows
    longest = max((s for x in items for s in ((x[1] + " = " + x[0]) if kind == "sums" else x[1],)), key=len,
                  default="")
    fs = _fit(ctx, longest, cw * 0.84, min(ch * 0.5, cw * 0.22), 500)
    ctx.line_width = max(1.0, lw * 0.6)
    for i, item in enumerate(order):
        if item is None:
            continue
        x, y = box.x + (i % cols) * cw, top + (i // cols) * ch
        ctx.stroke_rect(x + cw * 0.04, y + ch * 0.08, cw * 0.92, ch * 0.84)
        shown, said = item
        ctx.set_font(fs, 500)
        ctx.fill_text(f"{said} = {shown}" if kind == "sums" else said, x + cw / 2, y + ch / 2)


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    kind = getattr(settings, "bingo_kind", "numbers")
    ctx.save()
    if solve:
        items = pool(c, settings)
        _draw_caller(ctx, box, items, lw, kind, c)
        ctx.restore()
        return {"kind": kind, "called": len(items)}
    grid = card(rnd, c, settings)
    if grid is None:
        ctx.fill_style = "#000"
        ctx.text_align, ctx.text_baseline = "center", "middle"
        ctx.set_font(min(box.w, box.h) * 0.04, 500)
        ctx.fill_text(tr("Add more words for a bingo card (at least 9)."), box.x + box.w / 2, box.y + box.h / 2,
                      box.w * 0.9)
        ctx.restore()
        return None
    _draw_card(ctx, box, grid, lw, kind)
    ctx.restore()
    return {"kind": kind, "size": len(grid), "card": grid}
