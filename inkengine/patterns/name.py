"""Name pages: a name or word in big bubble letters to colour, optionally over a pattern.

Ported line for line from index.html (balanceLines, genName). tests/test_name.py checks this
against recordings of the JavaScript.

Each line is outlined wide in black, then a little narrower in white, then filled white. Where
neighbouring letters' outlines overlap, the white pass erases the black between them, so the word
becomes one puffy, connected outline. Words are split over one to four lines, whichever gives the
biggest letters, with the widest line as narrow as possible.

The letters are drawn in the installed font, so (like word mazes) they look exactly like 2.x only
where 2.x's fonts are installed; the line breaks follow the font's widths too.
"""

from ..rng import mulberry32
from ..i18n import tr

BACKGROUNDS = {"none": "Plain", "flow": "Flow lines", "contour": "Contours", "truchet": "Woven tiles"}
PUFF = 0.035   # bubble size in ems: bubbly and joined, while the openings in a, e and g stay open
REF = 100      # font size for measuring


def balance_lines(words, n, width):
    """Split words into n lines so the widest line is as narrow as possible (a small dynamic programme)."""
    W, memo = len(words), {}

    def line_w(a, b):
        return width(" ".join(words[a:b]))

    def best(i, k):
        if (i, k) in memo:
            return memo[(i, k)]
        if k == 1:
            res = (line_w(i, W), [" ".join(words[i:])])
        else:
            res = (float("inf"), [])
            for j in range(i + 1, W - k + 2):
                rest = best(j, k - 1)
                cost = max(line_w(i, j), rest[0])
                if cost < res[0]:
                    res = (cost, [" ".join(words[i:j])] + rest[1])
        memo[(i, k)] = res
        return res

    return best(0, n)[1]


def clean_text(text):
    return " ".join((text or "").split()) or tr("Your name")


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, seed=0, **_opts):
    text = clean_text(getattr(settings, "name_text", "Hello"))
    bg = getattr(settings, "name_bg", "none")
    if bg != "none":   # the pattern goes underneath, from the same seed
        from . import GENERATORS
        GENERATORS[bg](ctx, box, mulberry32(seed), c, settings, lw=lw, seed=seed, dpi=dpi)
    ctx.save()
    ctx.set_font(REF, 900)
    width = lambda s: ctx.measure_text(s) / REF
    words = text.split(" ")
    # try 1-4 lines; keep the layout with the biggest letters (the bubble adds 2 x puff, plus a little)
    pick = None
    for n in range(1, min(4, len(words)) + 1):
        lines = balance_lines(words, n, width)
        max_w = max(width(t) for t in lines)
        fs = min(box.w * 0.9 / (max_w + 2 * PUFF + 0.01), box.h * 0.84 / (n * 1.18))
        if pick is None or fs > pick[1]:
            pick = (lines, fs)
    lines, fs = pick
    e, lh = fs * PUFF, fs * 1.18
    cx, top = box.x + box.w / 2, box.y + (box.h - len(lines) * lh) / 2

    def base(i):
        return top + (i + 0.5) * lh + fs * 0.36

    ctx.set_font(fs, 900)
    ctx.text_align, ctx.text_baseline = "center", "alphabetic"
    ctx.line_join = ctx.line_cap = "round"
    ctx.stroke_style, ctx.line_width = "#000", 2 * e + lw
    for i, t in enumerate(lines):
        ctx.stroke_text(t, cx, base(i))
    ctx.stroke_style, ctx.line_width = "#fff", max(1, 2 * e - lw)
    for i, t in enumerate(lines):
        ctx.stroke_text(t, cx, base(i))
    ctx.fill_style = "#fff"
    for i, t in enumerate(lines):
        ctx.fill_text(t, cx, base(i))
    ctx.restore()
    return {"lines": lines, "fs": fs / dpi}
