import math
import xml.etree.ElementTree as ET

from PySide6.QtGui import QImage, QPainter

from inkengine.canvas import QtCanvas, SvgCanvas, fx
from inkengine.qt import ensure_app


def draw_quarter(ctx):
    """A quarter circle clockwise from 3 o'clock: on a canvas (y down) that's the lower-right quarter."""
    ctx.line_width = 6
    ctx.begin_path()
    ctx.arc(50, 50, 40, 0, math.pi / 2)
    ctx.stroke()


def test_qt_arc_turns_the_canvas_way():
    ensure_app()
    img = QImage(100, 100, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFFFF)
    p = QPainter(img)
    draw_quarter(QtCanvas(p, 100, 100))
    p.end()
    d = 40 / math.sqrt(2)
    assert img.pixelColor(round(50 + d), round(50 + d)).lightness() < 100   # lower right: drawn
    assert img.pixelColor(round(50 + d), round(50 - d)).lightness() > 200   # upper right: blank


def test_svg_arc_and_full_circle():
    ctx = SvgCanvas(100, 100, 1, 1)
    draw_quarter(ctx)
    ctx.circle(50, 50, 10)
    svg = str(ctx)
    root = ET.fromstring(svg)
    paths = [e.get("d") for e in root.iter("{http://www.w3.org/2000/svg}path")]
    assert paths[0] == "M90 50A40 40 0 0 1 50 90"
    assert paths[1].count("A") == 2            # a whole circle is two half arcs
    assert root.get("width") == "1in"


def test_svg_save_restore_closes_clip_groups():
    ctx = SvgCanvas(10, 10, 1, 1)
    ctx.save()
    ctx.rect(0, 0, 5, 5)
    ctx.clip()
    ctx.save()
    ctx.rect(1, 1, 2, 2)
    ctx.clip()
    svg = str(ctx)                 # still open: closed at the end
    ET.fromstring(svg)
    ctx.restore()
    ctx.restore()
    assert str(ctx).count("<g ") == str(ctx).count("</g>") == 2


def test_white_fills_are_left_out_of_svg():
    ctx = SvgCanvas(10, 10, 1, 1)
    ctx.fill_style = "#fff"
    ctx.fill_rect(0, 0, 10, 10)
    assert "<rect" not in str(ctx)


def test_number_format_matches_js_tofixed():
    assert [fx(1.0), fx(2.345), fx(-0.001), fx(10.5)] == ["1", "2.35", "0", "10.5"]
