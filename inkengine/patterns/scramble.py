"""Unscramble: words with their letters mixed up, each with a line to write the word on, and an answer page.

The words come from the same place as the word search's: a theme (a seeded pick) or your own list, such as
this week's spelling words (all of it, up to 20). Complexity sets how many words from a theme: 6 at 1, 15 at
10. Each word's letters are shuffled by the seed until they no longer spell it (or any other word on the
sheet), and shown in boxes, one letter each. The answer page writes each word on its line.
"""

import math

from ..i18n import tr
from ..rng import pick
from .words import word_pool

MAX_OWN = 20


def shuffle_letters(rnd, word, avoid=()):
    """The word's letters in another order: not the word itself (unless every letter is the same), nor a word in
    avoid."""
    letters = list(word)
    if len(set(letters)) < 2:
        return word
    for _ in range(50):
        for i in range(len(letters) - 1, 0, -1):
            j = pick(rnd, i + 1)
            letters[i], letters[j] = letters[j], letters[i]
        out = "".join(letters)
        if out != word and out not in avoid:
            return out
    return word[1:] + word[0]   # a rotation is never the word itself here (two different letters at least)


def make_sheet(rnd, c, theme="animals", own=""):
    """[(word, scrambled)] for one sheet."""
    pool = word_pool(rnd, c, theme, own)
    if theme == "custom" and own.strip():
        words = pool[:MAX_OWN]
    else:
        words = pool[:5 + c]
    words = [w for w in words if len(w) >= 2]
    return [(w, shuffle_letters(rnd, w, set(words))) for w in words]


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The scrambled words (or, with solve=True, each word written on its line)."""
    items = make_sheet(rnd, c, getattr(settings, "ws_theme", "animals"), getattr(settings, "ws_words", ""))
    if not items:
        return None
    cols = 1 if len(items) <= 10 else 2
    rows = math.ceil(len(items) / cols)
    cw, rh = box.w / cols, box.h / max(rows, 6)
    longest = max(len(s) for _w, s in items)
    # one box per letter, then a line as long as the letters: both inside the column
    cell = min(rh * 0.55, (cw * 0.9 - rh * 0.5) / (longest * 2.15 + 1.5), dpi * 0.4)
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_baseline = "middle"
    for k, (word, mixed) in enumerate(items):
        col, row = k // rows, k % rows
        x = box.x + col * cw + cw * 0.03
        y = box.y + row * rh + rh * 0.5
        ctx.set_font(cell * 0.5, 400)
        ctx.fill_style = "#666"
        ctx.text_align = "left"
        ctx.fill_text(f"{k + 1}.", x, y)
        x += cell * 1.5
        ctx.fill_style = "#000"
        ctx.line_width = max(1.0, lw * 0.7)
        ctx.set_font(cell * 0.62, 600)
        ctx.text_align = "center"
        for i, ch in enumerate(mixed):
            bx = x + i * cell * 1.08
            ctx.stroke_rect(bx, y - cell / 2, cell, cell)
            ctx.fill_text(ch, bx + cell / 2, y + cell * 0.04)
        lx = x + longest * cell * 1.08 + cell * 0.8   # every line starts in the same place
        line = longest * cell * 1.0 + cell
        ctx.line_width = max(1.0, lw * 0.6)
        ctx.begin_path()
        ctx.move_to(lx, y + cell * 0.45)
        ctx.line_to(lx + line, y + cell * 0.45)
        ctx.stroke()
        if solve:
            ctx.fill_style = "#666"
            ctx.text_align = "left"
            ctx.set_font(cell * 0.6, 600)
            ctx.fill_text(word, lx + cell * 0.2, y + cell * 0.08)
            ctx.fill_style = "#000"
    ctx.restore()
    return {"words": items}


def crossword_clues(rnd, words):
    """Crossword entries for words that have no clues (a spelling list): each clue is the word's letters mixed up,
    "Unscramble: T A C", as "word: clue" lines for Crossword → Your own words."""
    return "\n".join(f"{w.lower()}: " + tr("Unscramble: {letters}").format(letters=" ".join(shuffle_letters(rnd, w)))
                     for w in words)
