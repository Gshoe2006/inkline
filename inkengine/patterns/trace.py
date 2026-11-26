"""Handwriting and tracing: rows of writing lines, each with a letter, number, word or name written once in
solid and then in dotted outline to trace over, with room at the end to write it unaided.

What's traced is a setting: capital or small letters, numbers, your own words, or a name (a class set's name
for each copy, else the name page's text). Letters and numbers start at a different place on each design, so
copies of a sheet practise different ones. Complexity sets the size: 4 big rows at 1, 11 smaller ones at 10.

Each row has the four lines handwriting is taught on: the top line, a dashed middle line, the base line
(darker) and a light line below for tails.
"""

import re

from ..rng import pick
from .. import i18n
from ..i18n import tr

SOURCES = {"upper": "Capital letters", "lower": "Small letters", "numbers": "Numbers", "words": "Your own words",
           "name": "A name"}
LETTERS = {"print": "Print letters", "joined": "Joined-up (cursive)"}
# joined-up styles (inkengine/fonts, Playwrite): "auto" is the school style of Inkline's language
HANDS = {"auto": "Your language's school style", "gb": "England", "us-trad": "United States (traditional cursive)",
         "us-modern": "United States (modern cursive)", "au": "Australia (New South Wales)", "nz": "New Zealand",
         "ie": "Ireland", "ca": "Canada", "es": "Spain", "mx": "Mexico", "fr": "France", "br": "Brazil",
         "pt": "Portugal", "de": "Germany", "it": "Italy", "nl": "Netherlands"}
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = UPPER.lower()
DIGITS = "0123456789"
DEFAULT_WORDS = {"en": ["cat", "dog", "sun", "tree"], "es": ["gato", "perro", "sol", "árbol"],
                 "fr": ["chat", "chien", "soleil", "arbre"], "pt": ["gato", "bola", "sol", "árvore"],
                 "de": ["Katze", "Hund", "Sonne", "Baum"], "it": ["gatto", "cane", "sole", "albero"],
                 "nl": ["kat", "hond", "zon", "boom"]}   # Your own words, empty


def rows_for(c):
    """How many rows of writing at complexity c (1..10)."""
    return [4, 5, 5, 6, 7, 7, 8, 9, 10, 11][c - 1]


def words_from(text):
    return [w for w in (x.strip() for x in re.split(r"[,;\n]+", text or "")) if w][:40]


def lines_to_trace(rnd, c, settings, name=""):
    """The text of each row."""
    n = rows_for(c)
    source = getattr(settings, "trace_source", "upper")
    if source == "name":
        who = name or (getattr(settings, "name_text", "") or "").strip() or tr("Your name")
        return [who] * n
    if source == "words":
        words = words_from(getattr(settings, "trace_text", "")) or DEFAULT_WORDS.get(i18n.LANG, DEFAULT_WORDS["en"])
        start = pick(rnd, len(words))
        return [words[(start + k) % len(words)] for k in range(n)]
    upper = i18n.alphabet() if i18n.LANG in i18n.ALPHABETS else UPPER   # the Spanish alphabet has Ñ
    chars = DIGITS if source == "numbers" else upper.lower() if source == "lower" else upper
    start = pick(rnd, len(chars))
    return [chars[(start + k) % len(chars)] for k in range(n)]


def font_for(settings):
    """(family, weight) the sheet is written in: Inkline's print letters, or the language's joined-up
    handwriting font (Playwrite), which has one weight."""
    if getattr(settings, "trace_style", "print") == "joined":
        from ..qt import joined_family
        family = joined_family(i18n.LANG, getattr(settings, "trace_hand", "auto"))
        if family:
            return family, 400
    return "", 500


PRINT_LINES = (0.72, 0.52, 0.2)   # print letters: ascender line, x-height and descender line, in font sizes


def guide_lines(family, weight):
    """(ascender, x-height, descender) for the handwriting lines, in font sizes: print letters' own, or measured
    from a joined-up font (whose loops reach much higher and lower: the French school style's twice as far)."""
    if not family:
        return PRINT_LINES
    from PySide6.QtGui import QFontMetricsF
    from ..qt import make_font
    m = QFontMetricsF(make_font(100, weight, family))
    return (-m.tightBoundingRect("bdfhklt").top() / 100, -m.tightBoundingRect("xnmuvw").top() / 100,
            m.tightBoundingRect("gjpqy").bottom() / 100)


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, filled_name="", **_opts):
    texts = lines_to_trace(rnd, c, settings, filled_name)
    family, weight = font_for(settings)
    asc, xh, desc = guide_lines(family, weight)
    span = (asc + desc) / sum(PRINT_LINES[::2])   # how much taller than print letters a row's writing is
    room = box.w * 0.97
    ctx.save()
    # one size for the whole sheet: as big as the rows allow, but the widest text fits four times across (the
    # model, two to trace and a space to write it), so every row has something to trace
    ctx.set_font(100, weight, family)
    widest = max(ctx.measure_text(text) for text in texts) / 100
    if room * 0.98 / (widest * 2 + 0.6) < dpi * 0.45 and any(" " in text for text in texts):
        # too long to trace at a good size (a full name): each word of it on rows of its own
        words = [w for text in texts for w in text.split()]
        texts = [words[k % len(words)] for k in range(len(texts))]
        widest = max(ctx.measure_text(text) for text in texts) / 100
    tall = box.h / len(texts) * 0.66 / span

    def across(n):   # the size at which the widest text fits n times
        return room * 0.98 / (widest * n + max(0.6, widest * 0.35) * (n - 1))
    # four times across if that keeps it big enough, else three (the model, one to trace, the space). Too long
    # even for that at a size a child can trace: rows in pairs, the text in ink on one and dotted on the next
    pairs = across(3) < min(tall, dpi * 0.45)
    if pairs:
        fs = min(tall, across(1), dpi * 0.6)
        texts = [x for text in texts[: max(1, len(texts) // 2)] for x in (text, text)]
    else:
        fs = min(tall, across(4) if across(4) >= tall * 0.6 else across(3))
    rows = max(len(texts), min(2 * len(texts), 16, int(box.h // (fs * 1.6 * span))))   # smaller writing: more rows
    if pairs:
        rows -= rows % 2
    texts = [texts[k % len(texts)] for k in range(rows)]
    rh = box.h / rows
    dot = max(1.0, min(lw * 1.1, fs * 0.03))
    ctx.text_baseline, ctx.text_align = "alphabetic", "left"
    for r, text in enumerate(texts):
        # the writing (ascenders to descenders) in the middle of the row
        base = box.y + r * rh + (rh - fs * (asc + desc)) / 2 + fs * asc
        top, mid, tail = base - fs * asc, base - fs * xh, base + fs * desc
        for y, width, dash, colour in ((top, 0.5, (), "#999"), (mid, 0.5, (fs * 0.06, fs * 0.06), "#aaa"),
                                       (base, 0.9, (), "#555"), (tail, 0.4, (fs * 0.03, fs * 0.08), "#bbb")):
            ctx.line_width, ctx.line_dash, ctx.stroke_style = max(1.0, lw * width), dash, colour
            ctx.begin_path()
            ctx.move_to(box.x, y)
            ctx.line_to(box.x + box.w, y)
            ctx.stroke()
        ctx.line_dash = ()
        ctx.set_font(fs, weight, family)
        unit = ctx.measure_text(text)
        gap = max(fs * 0.6, unit * 0.35)
        width = min(unit, room)
        fits = max(1, int((room + gap) // (width + gap)))
        traced = 1 if pairs else max(1, fits - 1) if fits > 2 else fits   # leave the last place empty
        alone = pairs and r % 2 == 1   # in pairs: the second row of each is the dotted one
        x = box.x + fs * 0.15
        for k in range(traced):
            if k == 0 and not alone:   # the model, in solid ink
                ctx.fill_style = "#000"
                ctx.fill_text(text, x, base, room)
            else:        # then dotted outlines to trace
                ctx.line_width, ctx.stroke_style = dot, "#555"
                ctx.line_dash = (fs * 0.035, fs * 0.04)
                ctx.stroke_text(text, x, base, room)
                ctx.line_dash = ()
            x += width + gap
    ctx.restore()
    return {"rows": texts}
