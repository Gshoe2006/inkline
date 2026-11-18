"""Posters: one big design printed across several sheets, ported from index.html (posterGeom,
sheetRect, drawSheet).

The poster is laid out as one large page (the design scaled up, line weights and title with it)
and each sheet prints a window onto it. Neighbouring sheets share an overlap strip so they can be
lined up and glued; each sheet has trim marks at its printable corners, dashed ticks where the
overlap starts, and a label (A1, A2... rows down, columns across) saying where it goes.
"""

from .box import Box
from .page import Geometry, draw_page, geometry, js_round

GRIDS = ["2x2", "3x3", "4x4", "2x1", "3x2", "1x2", "2x3"]
GRID_NAMES = {"2x2": "2 × 2", "3x3": "3 × 3", "4x4": "4 × 4", "2x1": "2 across × 1", "3x2": "3 across × 2",
              "1x2": "1 across × 2", "2x3": "2 across × 3"}


def row_name(r):
    return chr(65 + r)    # A, B, C... down; 1, 2, 3... across


class PosterGeometry(Geometry):
    """The whole poster as one page, plus how it's cut into sheets."""

    def __init__(self, s, dpi):
        base = geometry(s)
        cols, rows = (int(n) for n in s.grid.split("x"))
        o, m = float(s.overlap), float(s.margin)
        pw, ph = base.w - 2 * m, base.h - 2 * m          # printable area of one sheet, inches
        w, h = cols * pw - (cols - 1) * o, rows * ph - (rows - 1) * o
        W, H, mm = js_round(w * dpi), js_round(h * dpi), m * dpi
        box = Box(mm, mm, W - 2 * mm, H - 2 * mm)
        r = dpi / base.dpi                                # scale against a single page
        scale = min(box.w / (base.box.w * r), box.h / (base.box.h * r))
        super().__init__(round(w, 2), round(h, 2), dpi, W, H, box, scale)
        self.cols, self.rows, self.pw, self.ph, self.o, self.m = cols, rows, pw, ph, o, m

    @property
    def sheets(self):
        return self.cols * self.rows


def poster_geometry(s, dpi=None):
    return PosterGeometry(s, s.dpi if dpi is None else dpi)


def sheet_rect(P, i):
    """(column, row, Box) of the part of the poster sheet i prints, in poster pixels."""
    c, r = i % P.cols, i // P.cols
    return c, r, Box(c * (P.pw - P.o) * P.dpi, r * (P.ph - P.o) * P.dpi, P.pw * P.dpi, P.ph * P.dpi)


def sheet_label(P, i):
    c, r, _ = sheet_rect(P, i)
    text = f"Sheet {row_name(r)}{c + 1}  ·  row {r + 1} of {P.rows}, column {c + 1} of {P.cols}"
    if P.o > 0:
        text += f"  ·  dashed ticks mark the {'½' if P.o == 0.5 else '¼'} in overlap"
    return text


def draw_sheet(ctx, s, P, spec, i):
    """Sheet i of the poster on a page: its window onto the design, trim marks, overlap ticks and label."""
    g = geometry(s)
    c, r, t = sheet_rect(P, i)
    m, k = g.box.x, g.dpi / 150
    ctx.fill_style = "#fff"
    ctx.fill_rect(0, 0, g.W, g.H)
    ctx.save()
    ctx.begin_path()
    ctx.rect(m, m, g.box.w, g.box.h)
    ctx.clip()
    ctx.translate(m - t.x, m - t.y)
    P.view = t   # the dot and line photo styles skip what's off this sheet
    draw_page(ctx, P, spec, s, keep=True)
    P.view = None
    ctx.restore()
    # trim marks at the printable corners, in the margin
    L, gap = min(m * 0.7, g.dpi * 0.3), g.dpi * 0.04
    x0, y0, x1, y1 = m, m, m + g.box.w, m + g.box.h
    ctx.save()
    ctx.stroke_style, ctx.line_width, ctx.line_cap = "#000", k, "butt"
    ctx.begin_path()
    for x, y, sx, sy in ((x0, y0, -1, -1), (x1, y0, 1, -1), (x0, y1, -1, 1), (x1, y1, 1, 1)):
        ctx.move_to(x + sx * gap, y)
        ctx.line_to(x + sx * (gap + L), y)
        ctx.move_to(x, y + sy * gap)
        ctx.line_to(x, y + sy * (gap + L))
    ctx.stroke()
    if P.o > 0:   # ticks where the overlap strip with the next sheet starts
        ctx.line_dash = (k * 4, k * 3)
        ctx.begin_path()
        if c < P.cols - 1:
            x = x1 - P.o * g.dpi
            ctx.move_to(x, y0 - gap)
            ctx.line_to(x, y0 - gap - L)
            ctx.move_to(x, y1 + gap)
            ctx.line_to(x, y1 + gap + L)
        if r < P.rows - 1:
            y = y1 - P.o * g.dpi
            ctx.move_to(x0 - gap, y)
            ctx.line_to(x0 - gap - L, y)
            ctx.move_to(x1 + gap, y)
            ctx.line_to(x1 + gap + L, y)
        ctx.stroke()
        ctx.line_dash = ()
    fs = g.dpi * 0.11
    ctx.set_font(fs, 600)
    ctx.fill_style, ctx.text_align = "#000", "center"
    ctx.fill_text(sheet_label(P, i), g.W / 2, g.H - m / 2 + fs / 3, g.box.w)
    ctx.restore()


def size_note(s):
    """e.g. "Finished poster: 14.75 × 19.75 in, from 4 Letter sheets." """
    P = poster_geometry(s, 1)
    paper = "A4" if s.paper == "a4" else "Letter"
    return f"Finished poster: {_num(P.w)} × {_num(P.h)} in, from {P.sheets} {paper} sheets."


def _num(x):
    return f"{x:g}"
