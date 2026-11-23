"""Telling the time: a sheet of clock faces, each with a time to read (write it under the clock) or to show (draw
the hands for the time written under it), and an answer page with every time read and every clock's hands drawn.

Complexity sets how many clocks and how exact the times are: o'clock at 1-2, half past at 3-4, quarters at 5-6,
five minutes at 7-8, any minute at 9-10; six clocks at first, then nine, then twelve. Faces have the numbers 1 to
12, an hour mark at each, and from five minutes on a mark for every minute. Times are written as on a digital
clock ("3:30"), which reads the same in every language. No time appears twice on a sheet.
"""

import math

from ..rng import pick

TASKS = {"read": "Read the clock", "draw": "Draw the hands", "mixed": "Both, mixed"}


def level(c):
    step = 60 if c <= 2 else 30 if c <= 4 else 15 if c <= 6 else 5 if c <= 8 else 1
    count = 6 if c <= 3 else 9 if c <= 7 else 12
    return {"step": step, "count": count, "minute_marks": c >= 7}


def make_times(rnd, c, task):
    """The clocks for one sheet: [(hour 1-12, minute, "read" or "draw")], no time twice."""
    lv = level(c)
    slots = 60 // lv["step"]
    out, seen, tries = [], set(), 0
    while len(out) < lv["count"] and tries < 1000:
        tries += 1
        h, m = 1 + pick(rnd, 12), pick(rnd, slots) * lv["step"]
        if (h, m) in seen:
            continue
        seen.add((h, m))
        kind = task if task in ("read", "draw") else ("read" if pick(rnd, 2) else "draw")
        out.append((h, m, kind))
    return out


def time_text(h, m):
    return f"{h}:{m:02d}"


def _hands(ctx, cx, cy, r, h, m, lw, colour="#000"):
    ctx.stroke_style = colour
    ctx.line_cap = "round"
    for frac, length, width in (((h % 12 + m / 60) / 12, 0.5, 2.6), (m / 60, 0.78, 1.6)):
        a = frac * 2 * math.pi
        ctx.line_width = max(1.0, lw * width)
        ctx.begin_path()
        ctx.move_to(cx, cy)
        ctx.line_to(cx + math.sin(a) * r * length, cy - math.cos(a) * r * length)
        ctx.stroke()
    ctx.stroke_style = "#000"


def _face(ctx, cx, cy, r, lw, minute_marks):
    ctx.line_width = max(1.0, lw * 1.2)
    ctx.begin_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.stroke()
    for k in range(60 if minute_marks else 12):
        hour = k % (5 if minute_marks else 1) == 0
        a = k / (60 if minute_marks else 12) * 2 * math.pi
        inner = r * (0.86 if hour else 0.93)
        ctx.line_width = max(1.0, lw * (0.9 if hour else 0.45))
        ctx.begin_path()
        ctx.move_to(cx + math.sin(a) * inner, cy - math.cos(a) * inner)
        ctx.line_to(cx + math.sin(a) * r * 0.97, cy - math.cos(a) * r * 0.97)
        ctx.stroke()
    ctx.set_font(r * 0.2, 600)
    ctx.text_align, ctx.text_baseline = "center", "middle"
    for n in range(1, 13):
        a = n / 12 * 2 * math.pi
        ctx.fill_text(str(n), cx + math.sin(a) * r * 0.7, cy - math.cos(a) * r * 0.7)
    ctx.begin_path()
    ctx.arc(cx, cy, max(1.5, r * 0.035), 0, 2 * math.pi)
    ctx.fill()


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The sheet of clocks (or, with solve=True, every time written and every clock's hands drawn)."""
    task = getattr(settings, "clock_task", "read")
    task = task if task in TASKS else "read"
    clocks = make_times(rnd, c, task)
    lv = level(c)
    cols = 3
    rows = -(-len(clocks) // cols)
    cw, rh = box.w / cols, box.h / rows
    r = min(cw * 0.36, rh / 2.9)   # the face and, under it, the time or a line to write it on
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    for k, (h, m, kind) in enumerate(clocks):
        col, row = k % cols, k // cols
        cx = box.x + (col + 0.5) * cw
        cy = box.y + row * rh + (rh - r * 2.6) / 2 + r   # the clock and its time, in the middle of the row
        _face(ctx, cx, cy, r, lw, lv["minute_marks"])
        if kind == "read" or solve:   # the hands: given to read, or the answer to one to draw
            _hands(ctx, cx, cy, r, h, m, lw, "#000" if kind == "read" else "#666")
        ty = cy + r * 1.5   # under the clock: the time, or a line to write it on
        ctx.text_align, ctx.text_baseline = "center", "alphabetic"
        if kind == "draw":
            ctx.set_font(r * 0.32, 700)
            ctx.fill_style = "#000"
            ctx.fill_text(time_text(h, m), cx, ty)
        else:
            ctx.line_width = max(1.0, lw * 0.6)
            ctx.begin_path()
            ctx.move_to(cx - r * 0.7, ty + r * 0.04)
            ctx.line_to(cx + r * 0.7, ty + r * 0.04)
            ctx.stroke()
            if solve:
                ctx.set_font(r * 0.32, 600)
                ctx.fill_style = "#666"
                ctx.fill_text(time_text(h, m), cx, ty - r * 0.04)
                ctx.fill_style = "#000"
    ctx.restore()
    return {"clocks": clocks, "task": task}
