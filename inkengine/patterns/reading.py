"""Reading comprehension: a short passage for the age, with questions to answer about it.

Passages live in inkengine/reading/<language>.json (English when a language has none): original texts at three
levels, 40-70 words for ages 5-7, 90-140 for 7-9 and 160-220 for 9-11. Complexity picks the level (1-3, 4-7,
8-10) and the seed picks a passage from it. Multiple-choice questions have a circle to tick by each answer;
written questions have lines to write on. The answer page ticks the right circles and writes a model answer
on the lines.
"""

import json
import os

from .. import i18n

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reading")
_cache = {}


def passages(lang=None):
    """Every passage for a language (English's when it has no file)."""
    lang = lang or i18n.LANG
    if lang not in _cache:
        path = os.path.join(HERE, f"{lang}.json")
        if not os.path.exists(path):
            return passages("en") if lang != "en" else []
        with open(path, encoding="utf-8") as f:
            _cache[lang] = json.load(f)
    return _cache[lang]


def level_for(c):
    return 1 if c <= 3 else 2 if c <= 7 else 3


def choose(rnd, c):
    """The passage for complexity c, picked by the seed."""
    pool = [p for p in passages() if p["level"] == level_for(c)]
    return pool[int(rnd() * len(pool)) % len(pool)] if pool else None


def _wrap(ctx, text, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and ctx.measure_text(trial) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def _layout(ctx, p, box, fs, letters):
    """The page at text size fs: [(kind, x, y, text or data)] and the height it takes."""
    items, y = [], box.y
    lh = fs * 1.45
    ctx.set_font(fs * 1.5, 700)
    y += fs * 1.5
    items.append(("title", box.x, y, p["title"]))
    y += fs * 0.9
    ctx.set_font(fs, 400)
    for para in p["text"].split("\n\n"):
        for line in _wrap(ctx, para, box.w):
            y += lh
            items.append(("text", box.x, y, line))
        y += fs * 0.5
    y += fs * 0.8
    for n, q in enumerate(p["questions"]):
        ctx.set_font(fs, 600)
        for k, line in enumerate(_wrap(ctx, f"{n + 1}. {q['q']}", box.w)):
            y += lh
            items.append(("q", box.x, y, line))
        if "choices" in q:
            ctx.set_font(fs, 400)
            for i, choice in enumerate(q["choices"]):
                y += lh
                items.append(("choice", box.x + fs * 1.2, y, (letters[i], choice, i == q["answer"])))
        else:
            for k in range(2):   # two lines to write on; the model answer on the first
                y += lh * 1.25
                items.append(("line", box.x + fs * 1.2, y, q["answer"] if k == 0 else ""))
        y += fs * 0.7
    return items, y - box.y


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    p = choose(rnd, c)
    if p is None:
        return None
    letters = "ABCD"
    ctx.save()
    fs = min(dpi * (0.27 if level_for(c) == 1 else 0.21 if level_for(c) == 2 else 0.17), box.h / 16)
    items, height = _layout(ctx, p, box, fs, letters)
    while height > box.h and fs > dpi * 0.08:   # smaller until it all fits on the page
        fs *= 0.94
        items, height = _layout(ctx, p, box, fs, letters)
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    for kind, x, y, data in items:
        if kind == "title":
            ctx.set_font(fs * 1.5, 700)
            ctx.fill_text(data, x, y)
        elif kind == "text":
            ctx.set_font(fs, 400)
            ctx.fill_text(data, x, y)
        elif kind == "q":
            ctx.set_font(fs, 600)
            ctx.fill_text(data, x, y)
        elif kind == "choice":
            letter, text, right = data
            r = fs * 0.36
            ctx.line_width = max(1.0, lw * 0.7)
            ctx.begin_path()
            ctx.arc(x + r, y - fs * 0.32, r, 0, 6.2832)
            if solve and right:
                ctx.fill_style = "#666"
                ctx.fill()
                ctx.fill_style = "#000"
            ctx.stroke()
            ctx.set_font(fs, 400)
            ctx.fill_text(f"{letter}  {text}", x + r * 2 + fs * 0.4, y)
        elif kind == "line":
            ctx.line_width = max(1.0, lw * 0.5)
            ctx.begin_path()
            ctx.move_to(x, y + fs * 0.15)
            ctx.line_to(box.x + box.w, y + fs * 0.15)
            ctx.stroke()
            if solve and data:
                ctx.set_font(fs, 500)
                ctx.fill_style = "#666"
                ctx.fill_text(data, x + fs * 0.2, y - fs * 0.05)
                ctx.fill_style = "#000"
    ctx.restore()
    return {"title": p["title"], "level": p["level"], "size": fs}
