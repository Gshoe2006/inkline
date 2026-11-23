"""Spelling test: a numbered line for each word the teacher reads aloud, and an answer page with the words.

The words come from the same place as the word search's: this week's spelling words (your own list, all of
it, up to 20) or a theme (a seeded pick, as many as Complexity sets: 6 at 1, 15 at 10). The sheet shows only
the numbers and the lines, never the words; the teacher reads them in the order of the answer page.
"""

from ..rng import pick
from .words import word_pool

MAX_OWN = 20


def test_words(rnd, c, theme="animals", own=""):
    """The words in the order they're read: your own list mixed up by the seed (so last week's order isn't
    remembered), or a theme's pick."""
    pool = word_pool(rnd, c, theme, own)
    if theme == "custom" and own.strip():
        out = list(pool[:MAX_OWN])
        for i in range(len(out) - 1, 0, -1):
            j = pick(rnd, i + 1)
            out[i], out[j] = out[j], out[i]
        return out
    return pool[:5 + c]


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The numbered lines (or, with solve=True, each word written on its line)."""
    words = test_words(rnd, c, getattr(settings, "ws_theme", "animals"), getattr(settings, "ws_words", ""))
    if not words:
        return None
    cols = 1 if len(words) <= 12 else 2
    rows = -(-len(words) // cols)
    cw, rh = box.w / cols, box.h / max(rows, 8)
    fs = min(rh * 0.42, dpi * 0.3)
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_baseline, ctx.text_align = "alphabetic", "left"
    for k, word in enumerate(words):
        col, row = k // rows, k % rows
        x = box.x + col * cw + cw * 0.04
        y = box.y + row * rh + rh * 0.7
        ctx.set_font(fs * 0.7, 400)
        ctx.fill_style = "#666"
        ctx.fill_text(f"{k + 1}.", x, y)
        lx, rx = x + fs * 1.8, box.x + (col + 1) * cw - cw * 0.06
        ctx.line_width = max(1.0, lw * 0.6)
        ctx.begin_path()
        ctx.move_to(lx, y + fs * 0.1)
        ctx.line_to(rx, y + fs * 0.1)
        ctx.stroke()
        if solve:
            ctx.set_font(fs, 600)
            ctx.fill_text(word.lower(), lx + fs * 0.3, y - fs * 0.08)
        ctx.fill_style = "#000"
    ctx.restore()
    return {"words": words}
