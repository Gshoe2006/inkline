"""Look, say, cover, write, check: the way spelling words are learnt, as a sheet.

Each word is printed in the first column. The child looks at it and says it, folds the page along the dashed line to
cover it, writes it from memory, then unfolds the page and checks, ticking the box if it's right; three times across.

The words come from the same place as the word search's, unscramble's and spelling test's: this week's spelling words
(your own list, all of it, up to 20) or a theme (a seeded pick, 6 at complexity 1 up to 12 at 10). Words are printed
as they're written in the list. The words are on the sheet, so there's no answer page.
"""

import re

from .. import i18n
from ..i18n import tr
from ..rng import pick
from .words import THEMES, THEMES_BY_LANGUAGE

MAX_OWN = 20
HEADINGS = ("Look and say", "Cover and write", "Write again", "Write again")


def sheet_words(rnd, c, theme="animals", own=""):
    """The words in the order they're printed: your own list as typed (without repeats), else a theme's pick."""
    if theme == "custom":
        mine = []
        for w in re.split(r"[\s,;]+", own or ""):
            if w and any(ch.isalpha() for ch in w) and w.lower() not in (x.lower() for x in mine):
                mine.append(w)
        if mine:
            return mine[:MAX_OWN]
    themes = THEMES_BY_LANGUAGE.get(i18n.LANG, THEMES)
    pool = [w for w in themes.get(theme, themes["animals"]).split() if w]
    for i in range(len(pool) - 1, 0, -1):
        j = pick(rnd, i + 1)
        pool[i], pool[j] = pool[j], pool[i]
    return pool[:6 + (max(1, c) - 1) * 6 // 9]


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    words = sheet_words(rnd, c, getattr(settings, "ws_theme", "animals"), getattr(settings, "ws_words", ""))
    if not words:
        return None
    fs = min(dpi * 0.15, box.h / 40)
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    # the instructions, wrapped across the top
    ctx.set_font(fs, 400)
    lines, line = [], ""
    for w in tr("Look at the word and say it. Fold along the dashed line to cover it and write it. Unfold and check: "
                "tick the box if it's right.").split():
        trial = f"{line} {w}".strip()
        if line and ctx.measure_text(trial) > box.w:
            lines.append(line)
            line = w
        else:
            line = trial
    lines.append(line)
    y = box.y
    for t in lines:
        y += fs * 1.3
        ctx.fill_text(t, box.x, y)
    y += fs * 0.9
    # the columns: the word, then three times a line to write on and a box to tick
    tick = min(box.w * 0.06, dpi * 0.42)
    word_w = box.w * 0.27
    write_w = (box.w - word_w - 3 * tick) / 3
    xs = [box.x, box.x + word_w]
    for k in range(3):
        xs.append(xs[-1] + write_w)
        xs.append(xs[-1] + tick)
    head_h = fs * 2.2
    ctx.set_font(fs * 0.95, 700)
    heads = [tr(HEADINGS[0])] + [h for k in range(3) for h in (tr(HEADINGS[1 + k]), "✓")]
    for k, h in enumerate(heads):
        left, right = xs[k], xs[k + 1]
        ctx.text_align = "center"
        ctx.fill_text(h, (left + right) / 2, y + head_h * 0.62, (right - left) * 0.95)
    y += head_h
    rows = len(words)
    rh = min((box.y + box.h - y - fs * 0.6) / rows, dpi * 1.1)   # the rows fill the page, but no taller than a hand needs
    # the word column's writing: as big as the longest word allows
    ctx.set_font(100, 600)
    widest = max(ctx.measure_text(w) for w in words) / 100
    wfs = min(rh * 0.55, (word_w * 0.86) / max(widest, 0.01))
    ctx.line_width = max(1.0, lw * 0.9)
    ctx.stroke_rect(box.x, y - head_h, box.w, head_h + rows * rh)
    ctx.line_width = max(1.0, lw * 0.5)
    ctx.begin_path()
    for r in range(rows + 1):
        ctx.move_to(box.x, y + r * rh)
        ctx.line_to(box.x + box.w, y + r * rh)
    for k in range(2, len(xs) - 1):
        ctx.move_to(xs[k], y - head_h)
        ctx.line_to(xs[k], y + rows * rh)
    ctx.stroke()
    ctx.line_dash = (lw * 5, lw * 4)   # fold here to cover the words
    ctx.line_width = max(1.0, lw * 0.9)
    ctx.begin_path()
    ctx.move_to(xs[1], y - head_h - fs * 0.6)
    ctx.line_to(xs[1], y + rows * rh + fs * 0.6)
    ctx.stroke()
    ctx.line_dash = ()
    ctx.text_align = "left"
    for r, word in enumerate(words):
        base = y + r * rh + rh * 0.68
        ctx.set_font(wfs, 600)
        ctx.fill_text(word, box.x + word_w * 0.07, base)
        ctx.line_width = max(1.0, lw * 0.4)   # a line to write on in each writing box
        ctx.stroke_style = "#999"
        ctx.begin_path()
        for k in range(3):
            left = xs[2 + 2 * k - 1]
            ctx.move_to(left + write_w * 0.08, base + rh * 0.08)
            ctx.line_to(left + write_w * 0.92, base + rh * 0.08)
        ctx.stroke()
        ctx.stroke_style = "#000"
    ctx.restore()
    return {"words": words, "rows": rows}
