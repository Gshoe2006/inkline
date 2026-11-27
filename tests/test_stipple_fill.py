"""Rows of stipple dots are filled a few dots at a time on the raster painter (much faster in Qt), and that must give
exactly the pixels one path per row gives. PDFs, and anything that isn't a plain row of whole circles, keep the one
path."""

import math

import numpy as np
import pytest
from PySide6.QtGui import QImage, QPainter, QPdfWriter

from inkengine import canvas, photo
from inkengine.box import Box
from inkengine.canvas import QtCanvas
from inkengine.qt import ensure_app


def _conversion(seed, ww, wh):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:wh, 0:ww]
    lum = np.clip(x / ww * 255 + rng.normal(0, 30, (wh, ww)), 0, 255).astype(np.float32).ravel()
    mask = np.ones(ww * wh, np.uint8)
    return photo.Conversion(ww, wh, lum, mask)


def _render(monkeypatch, grouped, e, box, inv, size, setup=None):
    ensure_app()
    img = QImage(size[0], size[1], QImage.Format.Format_RGB32)
    img.fill(0xFFFFFF)
    p = QPainter(img)
    if setup:
        setup(p)
    with monkeypatch.context() as m:
        if not grouped:
            m.setattr(canvas, "_dot_groups", lambda cmds, painter: None)
        photo._draw_stipple(QtCanvas(p, *size), box, e, inv, None)
    p.end()
    return np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).copy()


@pytest.mark.parametrize("seed,ww,wh,scale", [(1, 120, 90, 1.0), (2, 61, 140, 0.37), (3, 200, 40, 2.5)])
@pytest.mark.parametrize("inv", [False, True])
def test_dots_a_few_at_a_time_give_the_same_pixels(monkeypatch, seed, ww, wh, scale, inv):
    e = _conversion(seed, ww, wh)
    box = Box(13.3, 21.7, ww * 4.1, wh * 3.9)
    size = (int((box.x + box.w) * scale) + 20, int((box.y + box.h) * scale) + 20)
    setup = (lambda p: p.scale(scale, scale)) if scale != 1 else None
    calls = []
    real = canvas._dot_groups
    monkeypatch.setattr(canvas, "_dot_groups", lambda cmds, painter: calls.append(1) or real(cmds, painter))
    fast = _render(monkeypatch, True, e, box, inv, size, setup)
    assert calls   # it was asked
    slow = _render(monkeypatch, False, e, box, inv, size, setup)
    assert np.array_equal(fast, slow)
    assert (fast < 128).sum() > 1000


def _dots(n, gap):
    cmds = []
    for k in range(n):
        cx, cy, r = 10 + k * gap, 20 + (k % 3) * 0.4, 1.5
        cmds += [("M", cx + r, cy), ("A", cx, cy, r, 0, math.tau)]
    return cmds


def test_groups_only_split_where_a_pixel_column_is_free():
    ensure_app()
    img = QImage(400, 100, QImage.Format.Format_RGB32)
    p = QPainter(img)
    try:
        apart = canvas._dot_groups(_dots(20, 6.0), p)      # 3 px dots 6 px apart: a free column between each
        assert apart is not None and len(apart) == 20
        touching = canvas._dot_groups(_dots(20, 3.2), p)   # a hair apart: they share pixel columns
        assert touching is None
        assert canvas._dot_groups(_dots(20, 6.0)[:-1], p) is None                         # a move without its arc
        assert canvas._dot_groups(_dots(19, 6.0) + [("M", 0, 0), ("L", 5, 5)], p) is None  # not just circles
        half = [("A",) + c[1:5] + (math.pi,) if c[0] == "A" else c for c in _dots(20, 6.0)]
        assert canvas._dot_groups(half, p) is None                                          # half circles
        p.rotate(10)
        assert canvas._dot_groups(_dots(20, 6.0), p) is None                                # a turned page
    finally:
        p.end()


def test_pdf_keeps_one_path_per_row(tmp_path):
    ensure_app()
    w = QPdfWriter(str(tmp_path / "x.pdf"))
    p = QPainter(w)
    try:
        assert canvas._dot_groups(_dots(20, 6.0), p) is None
    finally:
        p.end()


def test_whole_stipple_page_png_unchanged(monkeypatch):
    from inkapp.benchmark import made_up_photo
    from inkengine import output
    from inkengine.page import Settings, single_page
    pic = made_up_photo(400, 300, seed=4)
    s = Settings(mode="convert", style="stipple", paper="letter", dpi=100)

    def png(grouped):
        photo.clear_cache()
        with monkeypatch.context() as m:
            if not grouped:
                m.setattr(canvas, "_dot_groups", lambda cmds, painter: None)
            img = output.render_image(s, single_page(s, pic))
        return np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).copy()
    assert np.array_equal(png(True), png(False))
    photo.clear_cache()
