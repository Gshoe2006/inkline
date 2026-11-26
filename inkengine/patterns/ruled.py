"""Graph and lined paper: squared, dotted and isometric grids, music staves, handwriting lines and lined paper,
filling the page. Complexity sets how close the lines are: wide for small hands at 1 (an inch apart), down to
5 mm squares and narrow lines at 10. Nothing to solve, so no answer page.
"""

import math

KINDS = {"squared": "Squared (graph) paper", "dotted": "Dot grid", "isometric": "Isometric dots",
         "lined": "Lined paper", "handwriting": "Handwriting lines", "staff": "Music staves"}
MM = 1 / 25.4   # inches


def spacing(c):
    """The grid's spacing in inches at complexity c: 1 in at 1, 5 mm at 10."""
    return 1.0 - (c - 1) * (1.0 - 5 * MM) / 9


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, **_opts):
    kind = getattr(settings, "ruled_kind", "squared")
    step = spacing(c) * dpi
    ctx.save()
    ctx.stroke_style, ctx.fill_style = "#000", "#000"
    if kind == "squared":
        cols, rows = int(box.w // step), int(box.h // step)
        x0, y0 = box.x + (box.w - cols * step) / 2, box.y + (box.h - rows * step) / 2
        for i in range(cols + 1):
            ctx.line_width = max(1.0, lw * (0.9 if i % 5 == 0 else 0.4))   # every fifth line darker
            ctx.stroke_style = "#555" if i % 5 == 0 else "#999"
            ctx.begin_path()
            ctx.move_to(x0 + i * step, y0)
            ctx.line_to(x0 + i * step, y0 + rows * step)
            ctx.stroke()
        for i in range(rows + 1):
            ctx.line_width = max(1.0, lw * (0.9 if i % 5 == 0 else 0.4))
            ctx.stroke_style = "#555" if i % 5 == 0 else "#999"
            ctx.begin_path()
            ctx.move_to(x0, y0 + i * step)
            ctx.line_to(x0 + cols * step, y0 + i * step)
            ctx.stroke()
        out = {"cols": cols, "rows": rows}
    elif kind in ("dotted", "isometric"):
        r = max(1.0, step * 0.04, lw * 0.7)
        dy = step * (math.sqrt(3) / 2 if kind == "isometric" else 1)
        rows = int(box.h // dy) + 1
        cols = int(box.w // step) + 1
        x0 = box.x + (box.w - (cols - 1) * step) / 2
        y0 = box.y + (box.h - (rows - 1) * dy) / 2
        n = 0
        for j in range(rows):
            shift = step / 2 if kind == "isometric" and j % 2 else 0
            for i in range(cols - (1 if shift else 0)):
                ctx.begin_path()
                ctx.arc(x0 + i * step + shift, y0 + j * dy, r, 0, 2 * math.pi)
                ctx.fill()
                n += 1
        out = {"dots": n}
    elif kind == "staff":
        gap = step * 0.25                 # between a staff's five lines
        pitch = gap * 4 + step * 0.9      # staff to staff
        staves = max(1, int((box.h + step * 0.9) // pitch))
        y0 = box.y + (box.h - (staves * pitch - step * 0.9)) / 2
        ctx.line_width = max(1.0, lw * 0.6)
        for s in range(staves):
            for k in range(5):
                y = y0 + s * pitch + k * gap
                ctx.begin_path()
                ctx.move_to(box.x, y)
                ctx.line_to(box.x + box.w, y)
                ctx.stroke()
            for x in (box.x, box.x + box.w):   # the bar lines at each end
                ctx.begin_path()
                ctx.move_to(x, y0 + s * pitch)
                ctx.line_to(x, y0 + s * pitch + 4 * gap)
                ctx.stroke()
        out = {"staves": staves}
    else:   # lined, or handwriting lines (a dashed middle line and a dotted line below, as Handwriting draws)
        hand = kind == "handwriting"
        pitch = step * (1.6 if hand else 0.7)
        rows = max(1, int(box.h // pitch))
        y0 = box.y + (box.h - rows * pitch) / 2
        for r in range(rows):
            base = y0 + r * pitch + pitch * (0.75 if hand else 1.0)
            if hand:
                body = pitch * 0.32
                for y, width, dash, colour in ((base - body * 2, 0.5, (), "#999"),
                                               (base - body, 0.5, (body * 0.12, body * 0.12), "#aaa"),
                                               (base, 0.9, (), "#555"),
                                               (base + body * 0.7, 0.4, (body * 0.06, body * 0.16), "#bbb")):
                    ctx.line_width, ctx.line_dash, ctx.stroke_style = max(1.0, lw * width), dash, colour
                    ctx.begin_path()
                    ctx.move_to(box.x, y)
                    ctx.line_to(box.x + box.w, y)
                    ctx.stroke()
                ctx.line_dash = ()
            else:
                ctx.line_width, ctx.stroke_style = max(1.0, lw * 0.5), "#777"
                ctx.begin_path()
                ctx.move_to(box.x, base)
                ctx.line_to(box.x + box.w, base)
                ctx.stroke()
        out = {"rows": rows}
    ctx.restore()
    return out
