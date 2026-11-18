"""One drawing API for every output.

Patterns draw on a Canvas with the same calls index.html made on an HTML canvas (move_to, line_to,
arc, stroke, fill_text...), so porting a generator is mostly a matter of renaming. The same drawing
then goes to:

- QtCanvas   a QPainter: the on-screen preview, PNG (QImage), vector PDF (QPdfWriter) and printing
- SvgCanvas  a standalone SVG document at true paper size, for Inkscape, cutting machines and lasers

Coordinates are page pixels at the page's dpi, y down, angles in radians clockwise, as on a canvas.
"""

import math
from dataclasses import dataclass, replace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen

from .qt import FONT_FAMILIES, make_font

TAU = 2 * math.pi


@dataclass
class State:
    """What save() and restore() keep, as on an HTML canvas."""
    line_width: float = 1.0
    stroke_style: str = "#000"
    fill_style: str = "#000"
    line_cap: str = "butt"         # butt | round | square
    line_join: str = "miter"       # miter | round | bevel
    font_size: float = 10.0
    font_weight: int = 400
    text_align: str = "start"      # start | left | center | right | end
    text_baseline: str = "alphabetic"   # alphabetic | middle | top


class Canvas:
    """The shared part: state stack and the current path. Back ends draw finished paths."""

    def __init__(self, width, height):
        self.width, self.height = width, height
        self.st = State()
        self._stack = []
        self.path = []          # ("M", x, y) ("L", x, y) ("Q", cx, cy, x, y) ("C", ...6) ("A", cx, cy, r, a0, sweep) ("Z",)
        self._cur = None
        self._start = None

    # --- state ----------------------------------------------------------------------------------
    def __getattr__(self, name):        # ctx.line_width etc. read the current state
        st = self.__dict__.get("st")
        if st is not None and name in State.__dataclass_fields__:
            return getattr(st, name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in State.__dataclass_fields__:
            setattr(self.st, name, value)
        else:
            super().__setattr__(name, value)

    def set_font(self, size, weight=400):
        self.st.font_size, self.st.font_weight = size, weight

    def save(self):
        self._stack.append(self.st)
        self.st = replace(self.st)
        self._on_save()

    def restore(self):
        if self._stack:
            self._on_restore()
            self.st = self._stack.pop()

    # --- path -----------------------------------------------------------------------------------
    def begin_path(self):
        self.path, self._cur, self._start = [], None, None

    # The public calls are what a pattern asks for; _move and _line are the moves and lines the canvas
    # rules add by themselves (e.g. arc's line to its start), which a RecordingCanvas doesn't log.
    def _move(self, x, y):
        self.path.append(("M", x, y))
        self._cur = self._start = (x, y)

    def _line(self, x, y):
        if self._cur is None:
            return self._move(x, y)
        self.path.append(("L", x, y))
        self._cur = (x, y)

    def move_to(self, x, y):
        self._move(x, y)

    def line_to(self, x, y):
        self._line(x, y)

    def quadratic_curve_to(self, cx, cy, x, y):
        if self._cur is None:
            self._move(cx, cy)
        self.path.append(("Q", cx, cy, x, y))
        self._cur = (x, y)

    def bezier_curve_to(self, c1x, c1y, c2x, c2y, x, y):
        if self._cur is None:
            self._move(c1x, c1y)
        self.path.append(("C", c1x, c1y, c2x, c2y, x, y))
        self._cur = (x, y)

    def close_path(self):
        self.path.append(("Z",))
        if self._start is not None:
            self._cur = self._start

    def rect(self, x, y, w, h):
        self._move(x, y)
        self._line(x + w, y)
        self._line(x + w, y + h)
        self._line(x, y + h)
        self.path.append(("Z",))
        self._cur = (x, y)

    def arc(self, cx, cy, r, a0, a1, ccw=False):
        """Canvas arc rules: a line from the current point to the start, and a turn of at least
        one full circle draws the whole circle."""
        sx, sy = cx + r * math.cos(a0), cy + r * math.sin(a0)
        if self._cur is None:
            self._move(sx, sy)
        elif abs(self._cur[0] - sx) > 0.005 or abs(self._cur[1] - sy) > 0.005:
            self._line(sx, sy)
        delta = a0 - a1 if ccw else a1 - a0
        if delta >= TAU - 1e-9:
            sweep = TAU
        else:
            sweep = delta % TAU
        if ccw:
            sweep = -sweep
        self.path.append(("A", cx, cy, r, a0, sweep))
        end = a0 + sweep
        self._cur = (cx + r * math.cos(end), cy + r * math.sin(end))

    def circle(self, x, y, r):
        """Stroke a whole circle in a fresh path (index.html's circle() helper)."""
        self.begin_path()
        self.arc(x, y, r, 0, TAU)
        self.stroke()

    # --- drawing (back ends) ----------------------------------------------------------------------
    def stroke(self):
        raise NotImplementedError

    def fill(self):
        raise NotImplementedError

    def fill_rect(self, x, y, w, h):
        raise NotImplementedError

    def stroke_rect(self, x, y, w, h):
        raise NotImplementedError

    def fill_text(self, text, x, y, max_width=None):
        raise NotImplementedError

    def clip(self):
        raise NotImplementedError

    def measure_text(self, text):
        """Width of text in the current font, in page pixels."""
        return QFontMetricsF(make_font(self.st.font_size, self.st.font_weight)).horizontalAdvance(text)

    def _on_save(self):
        pass

    def _on_restore(self):
        pass

    # shared by the back ends: where text starts once alignment and baseline are applied
    def _text_origin(self, text, x, y, max_width):
        width = self.measure_text(text)
        scale = max_width / width if max_width and width > max_width else 1.0
        drawn = width * scale
        align = self.st.text_align
        if align == "center":
            x -= drawn / 2
        elif align in ("right", "end"):
            x -= drawn
        fm = QFontMetricsF(make_font(self.st.font_size, self.st.font_weight))
        if self.st.text_baseline == "middle":
            y += (fm.ascent() - fm.descent()) / 2
        elif self.st.text_baseline == "top":
            y += fm.ascent()
        return x, y, scale


# --- QPainter ----------------------------------------------------------------------------------------

_CAPS = {"butt": Qt.PenCapStyle.FlatCap, "round": Qt.PenCapStyle.RoundCap, "square": Qt.PenCapStyle.SquareCap}
_JOINS = {"miter": Qt.PenJoinStyle.MiterJoin, "round": Qt.PenJoinStyle.RoundJoin, "bevel": Qt.PenJoinStyle.BevelJoin}


def to_qpath(cmds):
    """The recorded path as a QPainterPath (nonzero fill, like a canvas)."""
    p = QPainterPath()
    p.setFillRule(Qt.FillRule.WindingFill)
    for c in cmds:
        k = c[0]
        if k == "M":
            p.moveTo(c[1], c[2])
        elif k == "L":
            p.lineTo(c[1], c[2])
        elif k == "Q":
            p.quadTo(c[1], c[2], c[3], c[4])
        elif k == "C":
            p.cubicTo(c[1], c[2], c[3], c[4], c[5], c[6])
        elif k == "A":
            _, cx, cy, r, a0, sweep = c
            # Qt measures angles in degrees counter-clockwise; the canvas measures them clockwise.
            p.arcTo(QRectF(cx - r, cy - r, 2 * r, 2 * r), -math.degrees(a0), -math.degrees(sweep))
        elif k == "Z":
            p.closeSubpath()
    return p


class QtCanvas(Canvas):
    """Draws with a QPainter that the caller owns (begin/end are the caller's job)."""

    def __init__(self, painter, width, height):
        super().__init__(width, height)
        self.p = painter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    def _pen(self):
        pen = QPen(QColor(self.st.stroke_style))
        pen.setWidthF(self.st.line_width)
        pen.setCapStyle(_CAPS[self.st.line_cap])
        pen.setJoinStyle(_JOINS[self.st.line_join])
        pen.setMiterLimit(5)   # the canvas default limit of 10 line widths, in Qt's half-width units
        return pen

    def _draw_stroke(self, path):
        # setPen + drawPath, not strokePath: in a PDF, strokePath fills the outline of the stroke, and
        # where a long line overlaps itself (a maze's answer route) that outline shows holes.
        self.p.save()
        self.p.setPen(self._pen())
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        self.p.drawPath(path)
        self.p.restore()

    def stroke(self):
        if self.path:
            self._draw_stroke(to_qpath(self.path))

    def fill(self):
        if self.path:
            self.p.fillPath(to_qpath(self.path), QColor(self.st.fill_style))

    def fill_rect(self, x, y, w, h):
        self.p.fillRect(QRectF(x, y, w, h), QColor(self.st.fill_style))

    def stroke_rect(self, x, y, w, h):
        path = QPainterPath()
        path.addRect(QRectF(x, y, w, h))
        self._draw_stroke(path)

    def clip(self):
        self.p.setClipPath(to_qpath(self.path), Qt.ClipOperation.IntersectClip)

    def fill_text(self, text, x, y, max_width=None):
        x, y, scale = self._text_origin(text, x, y, max_width)
        self.p.save()
        self.p.setFont(make_font(self.st.font_size, self.st.font_weight))
        self.p.setPen(QColor(self.st.fill_style))
        self.p.translate(x, y)
        self.p.scale(scale, 1)
        self.p.drawText(QPointF(0, 0), text)
        self.p.restore()

    def _on_save(self):
        self.p.save()

    def _on_restore(self):
        self.p.restore()


# --- SVG ---------------------------------------------------------------------------------------------

def fx(n):
    """A number with at most two decimals and no trailing zeros, like JS +n.toFixed(2)."""
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _is_white(c):
    return str(c).strip().lower() in ("#fff", "#ffffff", "white")


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


class SvgCanvas(Canvas):
    """Builds an SVG document; str(canvas) gives the finished file."""

    def __init__(self, width, height, width_in, height_in):
        super().__init__(width, height)
        self.head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fx(width_in)}in" height="{fx(height_in)}in" '
                     f'viewBox="0 0 {width} {height}">')
        self.out, self.defs, self._groups, self._clip_n = [], [], [0], 0

    def _d(self):
        parts = []
        for c in self.path:
            k = c[0]
            if k in ("M", "L"):
                parts.append(f"{k}{fx(c[1])} {fx(c[2])}")
            elif k == "Q":
                parts.append(f"Q{fx(c[1])} {fx(c[2])} {fx(c[3])} {fx(c[4])}")
            elif k == "C":
                parts.append("C" + " ".join(fx(v) for v in c[1:]))
            elif k == "Z":
                parts.append("Z")
            elif k == "A":
                _, cx, cy, r, a0, sweep = c
                flag = 1 if sweep > 0 else 0
                pt = lambda a: (fx(cx + r * math.cos(a)), fx(cy + r * math.sin(a)))
                if abs(sweep) >= TAU - 1e-9:   # SVG can't draw a whole circle in one arc: two halves
                    mx, my = pt(a0 + math.copysign(math.pi, sweep))
                    sx, sy = pt(a0)
                    parts.append(f"A{fx(r)} {fx(r)} 0 1 {flag} {mx} {my}A{fx(r)} {fx(r)} 0 1 {flag} {sx} {sy}")
                elif sweep:
                    ex, ey = pt(a0 + sweep)
                    parts.append(f"A{fx(r)} {fx(r)} 0 {1 if abs(sweep) > math.pi else 0} {flag} {ex} {ey}")
        return "".join(parts)

    def _stroke_attrs(self):
        s = self.st
        return (f'fill="none" stroke="{s.stroke_style}" stroke-width="{fx(s.line_width)}" '
                f'stroke-linecap="{s.line_cap}" stroke-linejoin="{s.line_join}"')

    def stroke(self):
        if self.path:
            self.out.append(f'<path d="{self._d()}" {self._stroke_attrs()}/>')

    def fill(self):
        if self.path and not _is_white(self.st.fill_style):
            self.out.append(f'<path d="{self._d()}" fill="{self.st.fill_style}"/>')

    def fill_rect(self, x, y, w, h):
        if not _is_white(self.st.fill_style):   # the white page is the paper itself
            self.out.append(f'<rect x="{fx(x)}" y="{fx(y)}" width="{fx(w)}" height="{fx(h)}" fill="{self.st.fill_style}"/>')

    def stroke_rect(self, x, y, w, h):
        self.out.append(f'<rect x="{fx(x)}" y="{fx(y)}" width="{fx(w)}" height="{fx(h)}" {self._stroke_attrs()}/>')

    def clip(self):
        cid = f"clip{self._clip_n}"
        self._clip_n += 1
        self.defs.append(f'<clipPath id="{cid}"><path d="{self._d()}"/></clipPath>')
        self.out.append(f'<g clip-path="url(#{cid})">')
        self._groups[-1] += 1

    def fill_text(self, text, x, y, max_width=None):
        s = self.st
        anchor = {"center": "middle", "right": "end", "end": "end"}.get(s.text_align, "start")
        baseline = {"middle": ' dominant-baseline="middle"', "top": ' dominant-baseline="text-before-edge"'}.get(s.text_baseline, "")
        squeeze = ""
        if max_width and self.measure_text(text) > max_width:
            squeeze = f' textLength="{fx(max_width)}" lengthAdjust="spacingAndGlyphs"'
        family = ", ".join(f"'{f}'" if " " in f else f for f in FONT_FAMILIES)
        self.out.append(f'<text x="{fx(x)}" y="{fx(y)}" font-family="{family}" font-size="{fx(s.font_size)}" '
                        f'font-weight="{s.font_weight}" fill="{s.fill_style}" text-anchor="{anchor}"{baseline}{squeeze}>'
                        f"{_esc(text)}</text>")

    def _on_save(self):
        self._groups.append(0)

    def _on_restore(self):
        self.out.extend(["</g>"] * self._groups.pop())

    def __str__(self):
        close = "</g>" * sum(self._groups)
        defs = f"<defs>{''.join(self.defs)}</defs>\n" if self.defs else ""
        return f"{self.head}\n<title>Inkline</title>\n{defs}" + "\n".join(self.out) + f"{close}\n</svg>\n"


# --- recording (tests) -----------------------------------------------------------------------------

class RecordingCanvas(Canvas):
    """Writes down every path command and each stroke's style; used to compare with index.html."""

    def __init__(self, width=0, height=0):
        super().__init__(width, height)
        self.ops = []

    def save(self):
        super().save()
        self.ops.append(("save",))

    def restore(self):
        super().restore()
        self.ops.append(("restore",))

    def begin_path(self):
        super().begin_path()
        self.ops.append(("begin",))

    def move_to(self, x, y):
        super().move_to(x, y)
        self.ops.append(("M", x, y))

    def line_to(self, x, y):
        super().line_to(x, y)
        self.ops.append(("L", x, y))

    def quadratic_curve_to(self, cx, cy, x, y):
        super().quadratic_curve_to(cx, cy, x, y)
        self.ops.append(("Q", cx, cy, x, y))

    def bezier_curve_to(self, c1x, c1y, c2x, c2y, x, y):
        super().bezier_curve_to(c1x, c1y, c2x, c2y, x, y)
        self.ops.append(("C", c1x, c1y, c2x, c2y, x, y))

    def arc(self, cx, cy, r, a0, a1, ccw=False):
        super().arc(cx, cy, r, a0, a1, ccw)
        self.ops.append(("A", cx, cy, r, a0, a1, bool(ccw)))   # as called, before the canvas rules apply

    def rect(self, x, y, w, h):
        super().rect(x, y, w, h)
        self.ops.append(("rect", x, y, w, h))

    def close_path(self):
        super().close_path()
        self.ops.append(("Z",))

    def stroke(self):
        s = self.st
        self.ops.append(("stroke", s.line_width, s.stroke_style, s.line_cap, s.line_join))

    def fill(self):
        self.ops.append(("fill", self.st.fill_style))

    def fill_rect(self, x, y, w, h):
        self.ops.append(("fill_rect", x, y, w, h))

    def stroke_rect(self, x, y, w, h):
        self.ops.append(("stroke_rect", x, y, w, h))

    def fill_text(self, text, x, y, max_width=None):
        self.ops.append(("text", text, x, y))

    def clip(self):
        self.ops.append(("clip",))
