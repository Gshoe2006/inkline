"""The printer test page, ported from index.html (drawTestPage).

Printed once at actual size to check the printer: true-size squares and rulers (is it scaling?),
corner marks at known distances from the paper edge (how close can it print?), grey ramps in every
dither style and dot size (which looks best on this printer?) and every line weight. Always
portrait, with its own 0.75 in margin so the corner marks never touch the content.
"""

from dataclasses import replace

from .box import Box
from .page import geometry
from .photo import convert, grey_ramp
from .i18n import tr

_ramp = None


def _grey_ramp():
    global _ramp
    if _ramp is None:
        _ramp = grey_ramp()
    return _ramp


def _num(x):
    """A number as JavaScript prints it: 11, 8.5, 11.69."""
    return f"{x:g}"


def draw_test_page(ctx, s, version=""):
    s = replace(s, orient="portrait")
    g = geometry(s)
    I = g.dpi
    CM, M = I / 2.54, 0.75 * I
    b = Box(M, M, g.W - 2 * M, g.H - 2 * M)
    hair = max(1, I / 300)
    ctx.fill_style = "#fff"
    ctx.fill_rect(0, 0, g.W, g.H)
    ctx.stroke_style = ctx.fill_style = "#000"
    ctx.line_cap, ctx.text_baseline = "butt", "alphabetic"

    def text(t, x, y, size, weight=400, align="left", color="#000"):
        ctx.set_font(size, weight)
        ctx.text_align, ctx.fill_style = align, color
        ctx.fill_text(t, x, y)

    def line(x1, y1, x2, y2, w):
        ctx.line_width = w
        ctx.begin_path()
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()

    # corner marks: nested L shapes at known distances from each paper edge
    marks, arm = [(1 / 8, "1/8"), (3 / 16, "3/16"), (1 / 4, "1/4"), (3 / 8, "3/8"), (1 / 2, "1/2")], 0.16 * I
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        ox, oy = (0 if sx > 0 else g.W), (0 if sy > 0 else g.H)
        for d, label in marks:
            x, y = ox + sx * d * I, oy + sy * d * I
            line(x, y, x + sx * arm, y, hair)
            line(x, y, x, y + sy * arm, hair)
            if d >= 1 / 4:
                text(label, x + sx * (arm + 0.02 * I), y + 0.03 * I, 0.06 * I, 400, "left" if sx > 0 else "right", "#444")

    y = b.y
    paper = "A4" if s.paper == "a4" else tr("Letter")
    text(tr("Printer test page"), b.x, y + 0.26 * I, 0.26 * I, 700)
    text(tr("{paper} {w} × {h} in · {dpi} dpi").format(paper=paper, w=_num(g.w), h=_num(g.h), dpi=g.dpi)
         + (f" · Inkline {version}" if version else ""),
         b.x + b.w, y + 0.26 * I, 0.1 * I, 400, "right", "#444")
    y += 0.55 * I

    def ruler(y0, length, n, sub, unit):   # 6 inches in 1/8 in, and 15 cm in mm
        line(b.x, y0, b.x + length, y0, hair * 1.5)
        for i in range(n * sub + 1):
            x, whole = b.x + length * i / (n * sub), i % sub == 0
            if whole:
                h = 0.2 * I
            elif sub % 2 == 0 and i % (sub // 2) == 0:
                h = 0.13 * I
            elif sub == 8 and i % 2 == 0:
                h = 0.09 * I
            else:
                h = 0.06 * I
            line(x, y0, x, y0 + h, hair)
            if whole:
                text(str(i // sub), x + 0.02 * I, y0 + 0.32 * I, 0.09 * I, 600)
        text(tr(unit), b.x + length + 0.1 * I, y0 + 0.12 * I, 0.1 * I, 600)

    ruler(y, 6 * I, 6, 8, "inches")
    y += 0.5 * I
    ruler(y, 15 * CM, 15, 10, "cm")
    y += 0.6 * I

    def square(x, side, label, note):   # true-size squares
        ctx.line_width = hair * 2
        ctx.stroke_rect(x, y, side, side)
        text(tr(label), x + side / 2, y + side / 2 + 0.08 * I, 0.22 * I, 700, "center")
        text(tr(note), x + side / 2, y + side / 2 + 0.3 * I, 0.08 * I, 400, "center", "#444")

    square(b.x, 2 * I, "2 in", "= 5.08 cm on each side")
    square(b.x + 2.6 * I, 5 * CM, "5 cm", "= 1.97 in on each side")
    tx = b.x + 4.8 * I
    for dy, t, wt in ((0.3, "If these squares measure smaller, your", 600), (0.46, "printer is shrinking the page. Print at", 400),
                      (0.62, "100% / “Actual size”, not “Fit to page”.", 400), (0.94, "The innermost corner mark you can", 600),
                      (1.1, "see shows how close to the paper", 400), (1.26, "edge your printer can print.", 400)):
        text(tr(t), tx, y + dy * I, 0.1 * I, wt)   # (each line its own key: a translation keeps the breaks)
    y += 2 * I + 0.35 * I

    # grey ramps in each dither style at the current dot size, with neutral settings
    label_w = 1.75 * I
    ramp_w, ramp_h, ramp = b.w - label_w, 0.36 * I, _grey_ramp()
    text(tr("Dither styles at dot size {n} (from white to black)").format(n=s.dot), b.x, y, 0.11 * I, 700)
    y += 0.12 * I
    for style, name in (("fs", "Smooth"), ("atkinson", "Crisp"), ("bayer", "Ordered"), ("halftone", "Halftone"),
                        ("engrave", "Engraving"), ("stipple", "Stippling"), ("threshold", "Solid")):
        text(tr(name), b.x, y + ramp_h * 0.62, 0.1 * I, 600)
        r = Box(b.x + label_w, y, ramp_w, ramp_h)
        convert(ctx, r, g.dpi, s, ramp, style=style)
        ctx.line_width = hair
        ctx.stroke_rect(*r)
        y += ramp_h + 0.09 * I
    for pct in (0, 25, 50, 75, 100):
        text(f"{pct}%", b.x + label_w + ramp_w * pct / 100, y + 0.05 * I, 0.075 * I, 400,
             "left" if pct == 0 else "right" if pct == 100 else "center", "#444")
    y += 0.28 * I

    # smooth dither at dot sizes 1-4: pick the one that stays crisp on this printer
    text(tr("Smooth dither at dot sizes 1 to 4 (pick the smallest that doesn't smudge)"), b.x, y, 0.11 * I, 700)
    y += 0.12 * I
    gap = 0.15 * I
    cell_w = (b.w - 3 * gap) / 4
    for d in range(1, 5):
        r = Box(b.x + (d - 1) * (cell_w + gap), y, cell_w, ramp_h)
        convert(ctx, r, g.dpi, s, ramp, style="fs", dot=d)
        ctx.line_width = hair
        ctx.stroke_rect(*r)
        text(tr("dot {n}").format(n=d), r.x + r.w / 2, y + ramp_h + 0.13 * I, 0.08 * I, 600, "center")
    y += ramp_h + 0.38 * I

    # line weights 1-10, as the Line weight slider draws them
    text(tr("Line weights (the Line weight slider)"), b.x, y, 0.11 * I, 700)
    y += 0.14 * I
    col_w, row_h = b.w / 2, 0.19 * I
    for wgt in range(1, 11):
        col, row = (wgt - 1) // 5, (wgt - 1) % 5
        x0, yy = b.x + col * col_w, y + row * row_h + row_h / 2
        line(x0, yy, x0 + col_w * 0.55, yy, wgt * I / 150)
        text(f"{wgt}  ·  {wgt / 150 * 25.4:.2f} mm", x0 + col_w * 0.6, yy + 0.035 * I, 0.085 * I, 400)
    return {"bottom": y + 5 * row_h, "limit": b.y + b.h}
