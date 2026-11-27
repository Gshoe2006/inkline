"""Memory cards: pairs of cards to cut out, mix up and lay face down, then turn over two at a time to find the pairs.

- Pictures: two of each picture (a house, a star, a cat... from inkengine/pictures.py).
- Words and pictures: a picture, and its word in the current language on the other card.
- Numbers and dots: a number, and that many dots to count on the other card.
- Your own pairs: typed as "cat: chat; dog: chien" (a word on its own makes two cards the same).

Complexity sets how many cards a page holds: 2 x 4 at 1-2, then 3 x 4, 4 x 4, 4 x 5 and 4 x 6 at 9-10 (turned
round on a sideways page); fewer of your own pairs take a smaller grid with bigger cards. The seed shuffles where
each card goes. Dashed lines show where to cut.

Card backs: a page of backs to print on the other side of the sheet, double-sided, flipping on the long edge. A
card's back is printed where the sheet puts it: upright pages flip side to side, so the backs' columns are mirrored;
sideways pages flip top to bottom, so their rows are. page.py places the backs page's grid where the front's falls
once flipped (draw_page, kind "backs"). There's nothing to solve, so no answer page.
"""

import math
import re

from .. import i18n, pictures
from ..i18n import tr
from ..rng import pick

KINDS = {"pictures": "Pictures", "words": "Words and pictures", "dots": "Numbers and dots", "custom": "Your own pairs"}
GRIDS = [(2, 4), (3, 4), (4, 4), (4, 5), (4, 6)]   # columns, rows on an upright page
MAX_TEXT = 600


def grid_for(c, landscape=False, cards=None):
    """(columns, rows) at complexity c; with cards, the smallest grid that holds them, if smaller."""
    g = GRIDS[min(len(GRIDS) - 1, (max(1, c) - 1) // 2)]
    if cards is not None:
        g = next((x for x in GRIDS if x[0] * x[1] >= cards and x[0] * x[1] <= g[0] * g[1]), g)
    return (g[1], g[0]) if landscape else g


def own_pairs(text):
    """Your own pairs, as typed: [(left, right)], a word alone making two cards the same; empty bits left out."""
    out = []
    for part in re.split(r"[;\n]+", text or ""):
        if not part.strip():
            continue
        bits = re.split(r"\s*[:=]\s*", part.strip(), maxsplit=1)
        a = bits[0].strip()
        b = bits[1].strip() if len(bits) > 1 and bits[1].strip() else a
        if a:
            out.append((a, b))
    return out


def note(settings):
    """What the sidebar says about your own pairs: none typed, or more than a page holds; else ""."""
    if getattr(settings, "memory_kind", "pictures") != "custom":
        return ""
    pairs = own_pairs(getattr(settings, "memory_words", ""))
    most = max(a * b for a, b in GRIDS) // 2
    if not pairs:
        return tr("Type your pairs, such as cat: chat; dog: chien.")
    if len(pairs) > most:
        return tr("A page holds {n} pairs: the first {n} are used.").format(n=most)
    return ""


def make_cards(rnd, c, settings=None, landscape=False):
    """((columns, rows), cards in their places): each card is ("picture", name), ("word", text), ("number", n) or
    ("dots", n), and its pair's number."""
    kind = getattr(settings, "memory_kind", "pictures")
    kind = kind if kind in KINDS else "pictures"
    if kind == "custom":
        pairs = own_pairs(getattr(settings, "memory_words", ""))[:max(a * b for a, b in GRIDS) // 2]
        if not pairs:
            kind = "pictures"
    if kind == "custom":
        cols, rows = grid_for(c, landscape, 2 * len(pairs))
        n = min(len(pairs), cols * rows // 2)
        cards = [card for k, (a, b) in enumerate(pairs[:n]) for card in ((("word", a), k), (("word", b), k))]
    else:
        cols, rows = grid_for(c, landscape)
        n = cols * rows // 2
        if kind == "dots":
            top = max(6 if c <= 2 else 10, n)
            pool = list(range(1, top + 1))
        else:
            pool = sorted(pictures.PICTURES)
        for i in range(len(pool) - 1, 0, -1):
            j = pick(rnd, i + 1)
            pool[i], pool[j] = pool[j], pool[i]
        chosen = pool[:n]
        cards = []
        for k, v in enumerate(chosen):
            if kind == "dots":
                cards += [(("number", v), k), (("dots", v), k)]
            elif kind == "words":
                cards += [(("picture", v), k), (("word", pictures.word(v, i18n.LANG)), k)]
            else:
                cards += [(("picture", v), k), (("picture", v), k)]
    for i in range(len(cards) - 1, 0, -1):   # where each card goes
        j = pick(rnd, i + 1)
        cards[i], cards[j] = cards[j], cards[i]
    return (cols, rows), cards


def back_place(k, cols, rows, flip):
    """Where card k's back is printed on the backs page: its column mirrored when the sheet flips side to side
    ("cols", an upright page on the long edge), its row when it flips top to bottom ("rows", a sideways one)."""
    r, c = divmod(k, cols)
    return r * cols + (cols - 1 - c) if flip == "cols" else (rows - 1 - r) * cols + c


def _fit_lines(ctx, text, w, h, weight=600):
    """The text in as few lines as reads biggest inside w x h: (lines, font size)."""
    words = text.split()
    best = ([text], 1.0)
    for n in range(1, min(3, len(words)) + 1):
        per = math.ceil(len(words) / n)
        lines = [" ".join(words[i:i + per]) for i in range(0, len(words), per)]
        ctx.set_font(100, weight)
        widest = max(ctx.measure_text(line) for line in lines) / 100
        fs = min(w / max(widest, 0.01), h / (len(lines) * 1.25))
        if fs > best[1]:
            best = (lines, fs)
    return best


def _dots(ctx, n, x, y, w, h):
    """n dots as a dice face up to six, else in rows of three (or four, past nine), centred in w x h."""
    faces = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)], 4: [(0, 0), (2, 0), (0, 2), (2, 2)],
             5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)], 6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)]}
    if n in faces:
        s = min(w, h) / 3
        ox, oy = x + (w - 3 * s) / 2, y + (h - 3 * s) / 2
        spots = [(ox + (i + 0.5) * s, oy + (j + 0.5) * s) for i, j in faces[n]]
        r = s * 0.32
    else:   # 7-9 in threes, 10-12 in fours, three rows, the last row centred
        per = 3 if n <= 9 else 4
        rows = math.ceil(n / per)
        s = min(w / per, h / rows)
        oy = y + (h - rows * s) / 2
        spots = []
        for k in range(n):
            row, col = divmod(k, per)
            in_row = min(per, n - row * per)
            ox = x + (w - in_row * s) / 2
            spots.append((ox + (col + 0.5) * s, oy + (row + 0.5) * s))
        r = s * 0.3
    for cx, cy in spots:
        ctx.begin_path()
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
    return len(spots)


def _cut_lines(ctx, x, y, cw, ch, cols, rows, lw):
    ctx.save()
    ctx.stroke_style = "#000"
    ctx.line_width = max(1.0, lw * 0.5)
    ctx.line_dash = (lw * 6, lw * 4)
    ctx.begin_path()
    for i in range(cols + 1):
        ctx.move_to(x + i * cw, y)
        ctx.line_to(x + i * cw, y + rows * ch)
    for j in range(rows + 1):
        ctx.move_to(x, y + j * ch)
        ctx.line_to(x + cols * cw, y + j * ch)
    ctx.stroke()
    ctx.line_dash = ()
    ctx.restore()


def _back(ctx, x, y, w, h, lw):
    """A card's back: a frame round a lattice of light diagonals, a question mark in the middle."""
    pad = min(w, h) * 0.1
    ix, iy, iw, ih = x + pad, y + pad, w - 2 * pad, h - 2 * pad
    ctx.save()
    ctx.stroke_style = "#888"
    ctx.line_width = max(1.0, lw * 0.5)
    step = min(iw, ih) / 5
    ctx.begin_path()
    k = -ih
    while k < iw:   # lines going down-right from (ix + k, iy), and down-left, cut to the frame
        for sign in (1, -1):
            x0 = ix + k if sign == 1 else ix + iw - k
            # the line x = x0 + sign * t, y = iy + t, for t in [0, ih], kept inside ix..ix + iw
            t0 = max(0.0, (ix - x0) * sign) if sign == 1 else max(0.0, (x0 - (ix + iw)))
            t1 = min(ih, (ix + iw - x0) * sign) if sign == 1 else min(ih, x0 - ix)
            if t1 > t0:
                ctx.move_to(x0 + sign * t0, iy + t0)
                ctx.line_to(x0 + sign * t1, iy + t1)
        k += step
    ctx.stroke()
    ctx.stroke_style = "#000"
    ctx.line_width = max(1.0, lw * 0.9)
    ctx.stroke_rect(ix, iy, iw, ih)
    r = min(iw, ih) * 0.24
    ctx.fill_style = "#fff"
    ctx.begin_path()
    ctx.arc(x + w / 2, y + h / 2, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.stroke()
    ctx.fill_style = "#000"
    ctx.set_font(r * 1.3, 700)
    ctx.text_align, ctx.text_baseline = "center", "middle"
    ctx.fill_text("?", x + w / 2, y + h / 2 + r * 0.05)
    ctx.restore()


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, backs=False, flip="cols", **_opts):
    """The cards (or with backs=True, their backs, each where its card's back falls once the sheet flips)."""
    landscape = box.w > box.h
    (cols, rows), cards = make_cards(rnd, c, settings, landscape)
    cw, ch = box.w / cols, box.h / rows   # the cards fill the page, so cutting leaves nothing over
    x0, y0 = box.x + (box.w - cols * cw) / 2, box.y + (box.h - rows * ch) / 2
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    placed = []
    pad = min(cw, ch) * 0.12
    iw, ih = cw - 2 * pad, ch - 2 * pad
    # every word card's writing the same size: the size the hardest one to fit allows
    fits = {k: _fit_lines(ctx, str(v), iw * 0.9, ih * (0.6 if what == "number" else 0.5), 700 if what == "number" else 600)
            for k, ((what, v), _p) in enumerate(cards) if what in ("word", "number")}
    common = {w: min([f[1] for k, f in fits.items() if cards[k][0][0] == w] + [ih * 0.6]) for w in ("word", "number")}
    for k, (card, pair) in enumerate(cards):
        spot = back_place(k, cols, rows, flip) if backs else k
        r, col = divmod(spot, cols)
        x, y = x0 + col * cw, y0 + r * ch
        placed.append(spot)
        if backs:
            _back(ctx, x, y, cw, ch, lw)
            continue
        what, v = card
        if what == "picture":
            side = min(iw, ih)
            pictures.draw(ctx, v, x + (cw - side) / 2, y + (ch - side) / 2, side, max(1.5, lw * 1.3))
        elif what == "dots":
            _dots(ctx, v, x + pad, y + pad, iw, ih)
        else:
            lines, fs = fits[k][0], common[what]
            ctx.set_font(fs, 700 if what == "number" else 600)
            ctx.text_align, ctx.text_baseline = "center", "middle"
            lh = fs * 1.25
            top = y + ch / 2 - lh * (len(lines) - 1) / 2
            for i, line in enumerate(lines):
                ctx.fill_text(line, x + cw / 2, top + i * lh)
    _cut_lines(ctx, x0, y0, cw, ch, cols, rows, lw)
    ctx.restore()
    return {"grid": (cols, rows), "cards": cards, "places": placed, "card_size": (cw, ch), "origin": (x0, y0)}
