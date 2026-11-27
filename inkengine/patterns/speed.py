"""Times-table speed test: a sheet of quick facts to answer against the clock, with a box for the time and the
score, and an answer page.

- How many: 25, 50 or 100 facts.
- Tables: the ones typed (e.g. "3, 4, 8", 1 to 12), else the tables Complexity sets, as the maths drill's times
  tables do (the 2, 5 and 10 at 1, up to the 12 at 9-10).
- Order: mixed (the seed shuffles every fact of the tables, then again when they run out, so none comes twice
  before every one has come once) or in order (1 × 3, 2 × 3 ... 12 × 3, then the next table).
- Facts: times, sharing (the times tables backwards: 24 ÷ 3) or both.
- My progress: a chart to colour a bar in after each try, so a child sees the score climb.

The facts are numbered, as the maths drill's sums are, and laid out in as many columns as give the biggest writing,
each column's facts centred in it. The answer page shows the sheet itself, scaled down, with each answer written in
its blank in grey (page.py draws it from the sheet's own box, so its columns are the sheet's).
"""

import re

from ..i18n import tr
from ..rng import pick
from . import maths

COUNTS = [(25, "25"), (50, "50"), (100, "100")]
ORDERS = {"mixed": "Mixed up", "order": "In order"}
OPS = {"times": "Times (×)", "divide": "Sharing (÷)", "both": "Both"}
MAX_TABLES = 40   # how long the typed list may be
TRIES = 10        # bars on the progress chart


def typed_tables(text):
    """The tables typed: whole numbers 1-12, each once, in the order typed."""
    out = []
    for t in re.findall(r"\d+", text or ""):
        n = int(t)
        if 1 <= n <= 12 and n not in out:
            out.append(n)
    return out


def tables_for(c, text=""):
    """The tables to test: those typed, else Complexity's."""
    return typed_tables(text) or list(maths.level(c)["tables"])


def note(settings):
    """What the sidebar says when the tables typed have none from 1 to 12, or ""."""
    text = getattr(settings, "speed_tables", "") or ""
    if text.strip() and not typed_tables(text):
        return tr("Type tables from 1 to 12, such as 3, 4, 8. Until then, Complexity chooses them.")
    return ""


def _fact(t, n, op, rnd=None):
    """(left, sign, right, answer): n × t (or t × n, mixed up), or (n × t) ÷ t."""
    if op == "divide":
        return n * t, "÷", t, n
    if rnd is not None and pick(rnd, 2):
        return t, "×", n, n * t
    return n, "×", t, n * t


def make_facts(rnd, c, settings=None):
    """The sheet's facts, in order: [(left, sign, right, answer)]."""
    count = int(getattr(settings, "speed_count", 50) or 50)
    count = count if count in dict(COUNTS) else 50
    tables = tables_for(c, getattr(settings, "speed_tables", ""))
    op = getattr(settings, "speed_op", "times")
    op = op if op in OPS else "times"
    order = getattr(settings, "speed_order", "mixed")
    ops = ["times", "divide"] if op == "both" else [op]
    out = []
    if order == "order":
        while len(out) < count:
            for o in ops:
                for t in tables:
                    for n in range(1, 13):
                        out.append(_fact(t, n, o))
        return out[:count]
    # each fact once: 2 × 6 is the same fact from the 2s and the 6s, so overlapping tables don't repeat it
    every, seen = [], set()
    for o in ops:
        for t in tables:
            for n in range(1, 13):
                key = (o, min(t, n), max(t, n)) if o == "times" else (o, t, n)
                if key not in seen:
                    seen.add(key)
                    every.append((t, n, o))
    last = None
    while len(out) < count:
        deck = list(every)
        for i in range(len(deck) - 1, 0, -1):
            j = pick(rnd, i + 1)
            deck[i], deck[j] = deck[j], deck[i]
        if last is not None and len(deck) > 1 and deck[0] == last:   # no fact twice in a row across decks
            deck[0], deck[-1] = deck[-1], deck[0]
        for t, n, o in deck:
            f = _fact(t, n, o, rnd)
            if out and f == out[-1] and f[1] == "×":   # 5 × 7 from the 5s straight after 5 × 7 from the 7s
                f = (f[2], f[1], f[0], f[3])
            out.append(f)
        last = deck[-1]
    return out[:count]


def _number_width(ctx, n, fs):
    """How wide the facts' numbers are ("100."), and the gap after them, at font size fs."""
    ctx.set_font(fs * 0.55, 400)
    return ctx.measure_text(f"{n}.") + fs * 0.35


def _layout(ctx, box, facts, dpi):
    """(columns, rows, font size) giving the biggest writing that fits."""
    best = None
    numbers = _number_width(ctx, len(facts), 100) / 100
    ctx.set_font(100, 500)
    widest = max(ctx.measure_text(f"{a} {s} {b} = ") for a, s, b, _ans in facts) / 100 + 2.6 + numbers
    for cols in range(1, 7):
        rows = -(-len(facts) // cols)
        cw, rh = box.w / cols, box.h / rows
        fs = min(rh * 0.5, cw * 0.88 / widest, dpi * 0.34)
        if best is None or fs > best[2] * 1.001:
            best = (cols, rows, fs)
    return best


def _chart(ctx, x, y, w, h, count, lw, fs):
    """My progress: a bar for each try, scores up the side."""
    ctx.save()
    ctx.fill_style = "#000"
    ctx.set_font(fs, 700)
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    ctx.fill_text(tr("My progress"), x, y + fs)
    top = y + fs * 2.1   # clear of the title: the top score's number reaches half a line above the top line
    left = x + fs * 2.4
    bottom = y + h - fs * 1.4
    gw, gh = x + w - left, bottom - top
    steps = 5
    ctx.set_font(fs * 0.75, 400)
    for k in range(steps + 1):
        yy = bottom - gh * k / steps
        ctx.stroke_style = "#000" if k == 0 else "#aaa"
        ctx.line_width = max(1.0, lw * (0.9 if k == 0 else 0.4))
        ctx.begin_path()
        ctx.move_to(left, yy)
        ctx.line_to(left + gw, yy)
        ctx.stroke()
        ctx.text_align, ctx.text_baseline = "right", "middle"
        ctx.fill_text(str(round(count * k / steps)), left - fs * 0.3, yy)
    cw = gw / TRIES
    ctx.stroke_style = "#000"
    ctx.line_width = max(1.0, lw * 0.6)
    for k in range(TRIES + 1):
        ctx.begin_path()
        ctx.move_to(left + k * cw, top)
        ctx.line_to(left + k * cw, bottom)
        ctx.stroke()
    ctx.text_align, ctx.text_baseline = "center", "top"
    for k in range(TRIES):
        ctx.fill_text(str(k + 1), left + (k + 0.5) * cw, bottom + fs * 0.25)
    ctx.restore()


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The facts with a blank for each answer (or, with solve=True, the answers in grey), under the time and score
    box."""
    facts = make_facts(rnd, c, settings)
    chart = bool(getattr(settings, "speed_chart", False))
    hfs = min(dpi * 0.22, box.h / 28)
    head_h = hfs * 2.6
    chart_h = min(box.h * 0.24, dpi * 2.4) if chart else 0
    area = type(box)(box.x, box.y + head_h, box.w, box.h - head_h - chart_h - (hfs if chart else 0))
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    # the time and the score, in a box across the top
    ctx.line_width = max(1.0, lw * 0.9)
    ctx.stroke_rect(box.x, box.y, box.w, hfs * 1.9)
    ctx.set_font(hfs, 600)
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    base = box.y + hfs * 1.3
    time_label, score_label = tr("Time:"), tr("Score:")
    out_of = f"/ {len(facts)}"
    x = box.x + hfs * 0.6
    ctx.fill_text(time_label, x, base)
    # a line as long as both halves of the box leave, measured in the font the page uses (wider in some)
    left_room = box.w / 2 - hfs * 1.4 - ctx.measure_text(time_label)
    right_room = box.w / 2 - hfs * 1.6 - ctx.measure_text(score_label) - ctx.measure_text(out_of)
    line_w = max(hfs, min(left_room, right_room))
    lx = x + ctx.measure_text(time_label) + hfs * 0.3
    ctx.line_width = max(1.0, lw * 0.6)
    ctx.begin_path()
    ctx.move_to(lx, base + hfs * 0.1)
    ctx.line_to(lx + line_w, base + hfs * 0.1)
    ctx.stroke()
    sx = box.x + box.w / 2 + hfs * 0.3
    ctx.fill_text(score_label, sx, base)
    lx = sx + ctx.measure_text(score_label) + hfs * 0.3
    ctx.begin_path()
    ctx.move_to(lx, base + hfs * 0.1)
    ctx.line_to(lx + line_w, base + hfs * 0.1)
    ctx.stroke()
    ctx.fill_text(out_of, lx + line_w + hfs * 0.3, base)
    # the facts
    cols, rows, fs = _layout(ctx, area, facts, dpi)
    cw, rh = area.w / cols, area.h / rows
    blank = fs * 2.4
    numbers = _number_width(ctx, len(facts), fs)
    ctx.set_font(fs, 500)
    widest = max(ctx.measure_text(f"{a} {sign} {b} = ") for a, sign, b, _ans in facts)
    spare = max(0.0, cw - (numbers + widest + blank))   # each column's facts centred in it
    for k, (a, sign, b, answer) in enumerate(facts):
        col, row = k // rows, k % rows
        x = area.x + col * cw + spare / 2
        y = area.y + row * rh + rh * 0.68
        ctx.set_font(fs * 0.55, 400)
        ctx.fill_style = "#666"
        ctx.text_align = "left"
        ctx.fill_text(f"{k + 1}.", x, y)
        x += numbers
        ctx.set_font(fs, 500)
        ctx.fill_style = "#000"
        ctx.text_align = "right"   # every blank in a column starts in the same place
        ctx.fill_text(f"{a} {sign} {b} = ", x + widest, y)
        bx = x + widest
        ctx.line_width = max(1.0, lw * 0.6)
        ctx.begin_path()
        ctx.move_to(bx, y + fs * 0.12)
        ctx.line_to(bx + blank, y + fs * 0.12)
        ctx.stroke()
        if solve:
            ctx.fill_style = "#666"
            ctx.text_align = "center"
            ctx.fill_text(str(answer), bx + blank / 2, y - fs * 0.08)
    if chart:
        _chart(ctx, box.x, box.y + box.h - chart_h, box.w, chart_h, len(facts), lw, hfs * 0.8)
    ctx.restore()
    return {"facts": facts, "columns": cols}
