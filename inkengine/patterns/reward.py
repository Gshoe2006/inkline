"""Reward charts and certificates, with each child's name when Paper → Names lists the class.

- Sticker chart: a title, the child's name (or a line to write it on), what the stickers are for, and a grid of
  circles to fill with stickers or ticks, numbered, the last one a star. Complexity sets how many: 10 at 1, up
  to 40 at 10.
- Certificate: a double border with a band of mandala-like rosettes in the corners, "Well done!", the child's
  name, what it's for, and lines for the date and a signature.

What it's for comes from "For" (reward_text); left empty, there's a line to write it on.
"""

import math

from ..i18n import tr

KINDS = {"chart": "Sticker chart", "certificate": "Certificate"}


def count_for(c):
    """How many stickers: 10 at 1, 40 at 10, in fives."""
    return 10 + int(round((c - 1) * 30 / 9 / 5)) * 5


def _star(ctx, cx, cy, r):
    ctx.begin_path()
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        (ctx.move_to if k == 0 else ctx.line_to)(cx + rr * math.cos(a), cy + rr * math.sin(a))
    ctx.line_to(cx, cy - r)
    ctx.stroke()


def _rosette(ctx, cx, cy, r, lw):
    ctx.line_width = max(1.0, lw * 0.6)
    for ring in (1.0, 0.7, 0.4):
        ctx.begin_path()
        ctx.arc(cx, cy, r * ring, 0, 2 * math.pi)
        ctx.stroke()
    for k in range(12):
        a = k * math.pi / 6
        ctx.begin_path()
        ctx.arc(cx + r * 0.85 * math.cos(a), cy + r * 0.85 * math.sin(a), r * 0.15, 0, 2 * math.pi)
        ctx.stroke()


def _line_with(ctx, label, value, x, y, w, fs, lw):
    """A label, then the value written on a line, or an empty line to write it on."""
    ctx.set_font(fs, 500)
    ctx.text_align = "left"
    ctx.fill_text(label, x, y)
    lx = x + ctx.measure_text(label) + fs * 0.4
    ctx.line_width = max(1.0, lw * 0.6)
    ctx.begin_path()
    ctx.move_to(lx, y + fs * 0.15)
    ctx.line_to(x + w, y + fs * 0.15)
    ctx.stroke()
    if value:
        ctx.set_font(fs * 1.1, 600)
        ctx.text_align = "center"
        ctx.fill_text(value, (lx + x + w) / 2, y - fs * 0.05, x + w - lx)


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, filled_name="", **_opts):
    kind = getattr(settings, "reward_kind", "chart")
    reason = (getattr(settings, "reward_text", "") or "").strip()
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_baseline = "alphabetic"
    if kind == "certificate":
        m = min(box.w, box.h) * 0.03
        ctx.line_width = max(1.5, lw * 2.2)
        ctx.stroke_rect(box.x + m, box.y + m, box.w - 2 * m, box.h - 2 * m)
        ctx.line_width = max(1.0, lw * 0.8)
        ctx.stroke_rect(box.x + 2.2 * m, box.y + 2.2 * m, box.w - 4.4 * m, box.h - 4.4 * m)
        r = min(box.w, box.h) * 0.07
        for cx, cy in ((box.x + 2.2 * m + r * 1.3, box.y + 2.2 * m + r * 1.3),
                       (box.x + box.w - 2.2 * m - r * 1.3, box.y + 2.2 * m + r * 1.3),
                       (box.x + 2.2 * m + r * 1.3, box.y + box.h - 2.2 * m - r * 1.3),
                       (box.x + box.w - 2.2 * m - r * 1.3, box.y + box.h - 2.2 * m - r * 1.3)):
            _rosette(ctx, cx, cy, r, lw)
        cx, w = box.x + box.w / 2, box.w * 0.62
        fs = min(box.h * 0.035, box.w * 0.05)
        ctx.text_align = "center"
        ctx.set_font(fs * 1.1, 500)
        ctx.fill_text(tr("Certificate").upper(), cx, box.y + box.h * 0.22)
        ctx.set_font(fs * 2.6, 800)
        ctx.fill_text(tr("Well done!"), cx, box.y + box.h * 0.36, w * 1.2)
        _line_with(ctx, tr("This certificate is for"), filled_name, cx - w / 2, box.y + box.h * 0.52, w, fs, lw)
        _line_with(ctx, tr("For"), reason, cx - w / 2, box.y + box.h * 0.63, w, fs, lw)
        half = w * 0.46
        _line_with(ctx, tr("Date"), "", cx - w / 2, box.y + box.h * 0.8, half, fs * 0.85, lw)
        _line_with(ctx, tr("Signed"), "", cx + w / 2 - half, box.y + box.h * 0.8, half, fs * 0.85, lw)
        out = {"kind": "certificate"}
    else:
        n = count_for(c)
        fs = min(box.h * 0.04, box.w * 0.06)
        ctx.text_align = "center"
        ctx.set_font(fs * 1.6, 800)
        ctx.fill_text(tr("Sticker chart"), box.x + box.w / 2, box.y + fs * 1.6)
        top = box.y + fs * 2.8
        _line_with(ctx, tr("Name"), filled_name, box.x + box.w * 0.1, top + fs * 1.2, box.w * 0.8, fs * 0.8, lw)
        _line_with(ctx, tr("For"), reason, box.x + box.w * 0.1, top + fs * 2.8, box.w * 0.8, fs * 0.8, lw)
        grid_top = top + fs * 4.2
        cols = 5
        rows = -(-n // cols)
        cell = min(box.w / cols, (box.y + box.h - grid_top) / rows)
        r = cell * 0.4
        x0 = box.x + (box.w - cell * cols) / 2
        for k in range(n):
            cx = x0 + (k % cols + 0.5) * cell
            cy = grid_top + (k // cols + 0.5) * cell
            ctx.line_width = max(1.0, lw * 0.9)
            if k == n - 1:   # the goal
                _star(ctx, cx, cy, r * 1.05)
            else:
                ctx.begin_path()
                ctx.arc(cx, cy, r, 0, 2 * math.pi)
                ctx.stroke()
                ctx.set_font(r * 0.45, 500)
                ctx.fill_style = "#999"
                ctx.text_align = "center"
                ctx.fill_text(str(k + 1), cx, cy + r * 0.16)
                ctx.fill_style = "#000"
        out = {"kind": "chart", "count": n}
    ctx.restore()
    return out
