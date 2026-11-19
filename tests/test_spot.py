"""Spot the difference: two copies of a picture with a few changes, the same changes on the answer page."""

import math
from dataclasses import replace

import pytest

from inkengine.canvas import RecordingCanvas, SvgCanvas
from inkengine.page import PageSpec, Settings, answer_page, design_box, draw_page, geometry, single_page
from inkengine.patterns import HAS_ANSWER, NAMES, spot


def test_how_many_differences():
    assert [spot.count(c) for c in (1, 5, 10)] == [5, 7, 10]
    assert "spot" in HAS_ANSWER and NAMES["spot"] == "Spot the difference"


@pytest.mark.parametrize("base", list(spot.BASES))
@pytest.mark.parametrize("seed", [1, 77, 4242])
def test_changes_are_all_there_spread_out_and_repeatable(base, seed):
    s = Settings(gen="spot", spot_base=base, complexity=5, seed=seed, dpi=150)
    g = geometry(s)
    a, b, _cap = spot.layout(design_box(g, single_page(s), s))
    found = spot.changes(a, base, seed, 5, s, 2.0, g.dpi)
    assert len(found) == spot.count(5)
    assert [(k, round(x, 3), round(y, 3)) for k, x, y, *_ in found] == \
        [(k, round(x, 3), round(y, 3)) for k, x, y, *_ in spot.changes(a, base, seed, 5, s, 2.0, g.dpi)]
    for i, (_k, x, y, r, _e) in enumerate(found):
        assert r < x < a.w - r and r < y < a.h - r            # inside the copy
        for _k2, x2, y2, r2, _e2 in found[i + 1:]:
            assert math.hypot(x - x2, y - y2) >= r + r2       # never on top of each other


def test_mandala_changes_stay_inside_the_picture():
    for seed in (1, 77, 4242, 9):
        s = Settings(gen="spot", spot_base="mandala", complexity=4, seed=seed, dpi=150)
        g = geometry(s)
        a, _b, _c = spot.layout(design_box(g, single_page(s), s))
        cx, cy, radius = a.w / 2, a.h / 2, min(a.w, a.h) / 2
        for _k, x, y, _r, _e in spot.changes(a, "mandala", seed, 4, s, 2.0, g.dpi):
            assert math.hypot(x - cx, y - cy) < radius               # no added shape out in the margin


def test_the_answer_page_circles_the_same_changes():
    s = Settings(gen="spot", spot_base="truchet", complexity=6, seed=31, dpi=150, booklet=True)
    g = geometry(s)
    page = replace(single_page(s), label="Spot the difference", page_no=2)
    found = draw_page(RecordingCanvas(), g, page, s)
    rec = RecordingCanvas()
    draw_page(rec, g, answer_page([page]), s)
    assert len(found) == spot.count(6)
    caption = [op for op in rec.ops if op[0] == "text" and "differences" in str(op)]
    assert caption and f"Find the {len(found)} differences" in str(caption[0])


def test_svg_stays_vector():
    s = Settings(gen="spot", spot_base="contour", complexity=7, seed=5, dpi=150)
    g = geometry(s)
    svg = SvgCanvas(g.W, g.H, g.w, g.h)
    draw_page(svg, g, single_page(s), s)
    out = str(svg)
    assert "<image" not in out and out.count("<path") > 10
