"""Photo dot-to-dot: the photo's main outline as numbered dots, found with numpy alone."""

import math

import numpy as np
import pytest
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from inkengine import photodots
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings, draw_page, geometry, single_page
from inkengine.photo import STYLES, VECTOR_STYLES, Photo


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


def _disc(w=200, h=150, cx=90, cy=70, r=50, dark=30, light=230):
    yy, xx = np.mgrid[0:h, 0:w]
    lum = np.where((xx - cx) ** 2 + (yy - cy) ** 2 < r * r, dark, light).astype(np.float32).reshape(-1)
    return lum, np.ones(w * h, np.uint8)


@pytest.mark.parametrize("n", [20, 60, 150])
def test_a_filled_circle_gives_dots_round_the_circle(n):
    lum, mask = _disc()
    pts = photodots.outline(lum, mask, 200, 150, 128, False, n)
    assert n * 0.9 <= len(pts) <= n   # (a dot too close to the one before is left out)
    assert all(abs(math.hypot(x - 90, y - 70) - 50) < 1.5 for x, y in pts)
    angles = sorted(math.atan2(y - 70, x - 90) for x, y in pts)   # spread all the way round
    assert max(b - a for a, b in zip(angles, angles[1:] + [angles[0] + 2 * math.pi])) < 2 * math.pi / n * 3
    # numbered clockwise on the page from the top
    assert min(pts, key=lambda p: (p[1], p[0])) == pts[0]
    area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
    assert area > 0


def test_holes_are_filled_and_a_light_subject_on_dark_is_found():
    yy, xx = np.mgrid[0:150, 0:200]
    d = (xx - 100) ** 2 + (yy - 75) ** 2
    ring = np.where((d < 60 ** 2) & (d > 25 ** 2), 20, 240).astype(np.float32).reshape(-1)
    pts = photodots.outline(ring, np.ones(200 * 150, np.uint8), 200, 150, 128, False, 40)
    assert all(abs(math.hypot(x - 100, y - 75) - 60) < 1.5 for x, y in pts)   # the outside edge only
    square = np.where((abs(xx - 100) < 40) & (abs(yy - 75) < 40), 230, 30).astype(np.float32).reshape(-1)
    pts = photodots.outline(square, np.ones(200 * 150, np.uint8), 200, 150, 128, False, 20)
    assert pts and all(58 <= x <= 142 and 33 <= y <= 117 for x, y in pts)    # the light square, not the frame
    blank = np.full(200 * 150, 230, np.float32)
    assert photodots.outline(blank, np.ones(200 * 150, np.uint8), 200, 150, 128, False, 20) == []


def test_invert_follows_the_light_shape():
    lum, mask = _disc(dark=230, light=30)
    pts = photodots.outline(lum, mask, 200, 150, 128, True, 30)
    assert len(pts) == 30 and all(abs(math.hypot(x - 90, y - 70) - 50) < 1.5 for x, y in pts)


def test_simplifying_keeps_the_corners():
    square = [(float(x), 0.0) for x in range(100)] + [(100.0, float(y)) for y in range(100)] + \
             [(float(100 - x), 100.0) for x in range(100)] + [(0.0, float(100 - y)) for y in range(100)]
    four = photodots.simplify(square, 4)
    assert sorted(four) == [(0.0, 0.0), (0.0, 100.0), (100.0, 0.0), (100.0, 100.0)]
    assert len(photodots.simplify(square, 37)) == 37


def _photo():
    img = QImage(400, 300, QImage.Format.Format_ARGB32)
    img.fill(QColor("#ffffff"))
    p = QPainter(img)
    p.setBrush(QColor("#202020"))
    p.drawEllipse(120, 70, 160, 160)
    p.end()
    return Photo(img, name="disc.png")


def test_the_page_draws_numbered_dots_and_the_answer_joins_them():
    assert "dots" in STYLES and "dots" in VECTOR_STYLES
    pic = _photo()
    s = Settings(mode="convert", style="dots", dpi=72, pdots_n=40)
    ctx = RecordingCanvas()
    draw_page(ctx, geometry(s), single_page(s, pic), s)
    numbers = [op[1] for op in ctx.ops if op[0] == "text"]
    assert numbers == [str(k) for k in range(1, 41)]
    solved = Settings(mode="convert", style="dots", dpi=72, pdots_n=40, pdots_answer=True)
    ctx = RecordingCanvas()
    draw_page(ctx, geometry(solved), single_page(solved, pic), solved)
    assert not any(op[0] == "text" for op in ctx.ops) and sum(op[0] == "L" for op in ctx.ops) == 39


def test_a_photo_with_no_outline_says_so():
    img = QImage(100, 80, QImage.Format.Format_ARGB32)
    img.fill(QColor("#ffffff"))
    s = Settings(mode="convert", style="dots", dpi=72)
    ctx = RecordingCanvas()
    draw_page(ctx, geometry(s), single_page(s, Photo(img, name="white.png")), s)
    assert any("Threshold" in op[1] for op in ctx.ops if op[0] == "text")


def test_no_dots_along_the_pictures_edge():
    """Dark hills along the bottom of a landscape, in a photo fitted inside the page (empty space round it): the dots
    follow the hills' tops, not the photo's frame."""
    w, h = 240, 320
    yy, xx = np.mgrid[0:h, 0:w]
    mask = ((yy >= 80) & (yy < 240)).astype(np.uint8).reshape(-1)        # the photo: a band across the middle
    ridge = 170 + 12 * np.sin(xx / 15.0)
    lum = np.where(yy > ridge, 40, 220).astype(np.float32).reshape(-1)
    x0, y0, x1, y1 = photodots.frame(mask, w, h)
    assert (x0, y0, x1, y1) == (0, 80, 239, 239)
    pts = photodots.outline(lum, mask, w, h, 128, False, 40)
    assert len(pts) >= 20
    assert all(x0 + 2 < x < x1 - 2 and y0 + 2 < y < y1 - 2 for x, y in pts)   # none on the frame
    assert all(abs(y - (170 + 12 * math.sin(x / 15.0))) < 3 for x, y in pts)    # all on the ridge


def test_dots_keep_their_distance_and_dot_one_has_room():
    lum, mask = _disc()
    pts = photodots.outline(lum, mask, 200, 150, 128, False, 150)
    step = sum(math.dist(p, q) for p, q in zip(pts, pts[1:] + pts[:1])) / len(pts)
    assert min(math.dist(p, q) for p, q in zip(pts, pts[1:] + pts[:1])) >= step * 0.45
    assert math.dist(pts[0], pts[1]) >= step * 0.9 and math.dist(pts[0], pts[-1]) >= step * 0.9


def test_the_self_tests_photo_makes_a_real_outline():
    from inkapp.selftest import _silhouette
    s = Settings(mode="convert", style="dots", dpi=72, pdots_n=60)
    out = draw_page(RecordingCanvas(), geometry(s), single_page(s, _silhouette()), s)
    pts = out.outlines[60]
    assert 50 <= len(pts) <= 60
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0, x1, y1 = photodots.frame(out.mask, out.ww, out.wh)
    assert min(xs) > x0 + 5 and max(xs) < x1 - 5 and min(ys) > y0 + 5 and max(ys) < y1 - 5
