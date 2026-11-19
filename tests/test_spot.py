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


@pytest.mark.parametrize("base", list(spot.BASES))
@pytest.mark.parametrize("c", [1, 10])
@pytest.mark.parametrize("orient", ["portrait", "landscape"])
def test_every_puzzle_gets_all_its_changes_and_few_fills(base, c, orient):
    from inkengine.page import line_width
    for seed in (3, 7, 8):   # seeds that once came up short (3 of 10 on a dense mandala)
        s = Settings(gen="spot", spot_base=base, complexity=c, seed=seed, orient=orient, dpi=150)
        g = geometry(s)
        a, _b, _c = spot.layout(design_box(g, single_page(s), s))
        kinds = [k for k, *_ in spot.changes(a, base, seed, c, s, line_width(s, g), g.dpi)]
        assert len(kinds) == spot.count(c)
        assert kinds.count("fill") <= math.ceil(spot.count(c) / 3)   # the easiest kind to see stays a minority


def test_mandala_changes_stay_inside_the_picture():
    for seed in (1, 77, 4242, 9):
        s = Settings(gen="spot", spot_base="mandala", complexity=4, seed=seed, dpi=150)
        g = geometry(s)
        a, _b, _c = spot.layout(design_box(g, single_page(s), s))
        cx, cy, radius = a.w / 2, a.h / 2, min(a.w, a.h) / 2
        for _k, x, y, _r, _e in spot.changes(a, "mandala", seed, 4, s, 2.0, g.dpi):
            assert math.hypot(x - cx, y - cy) < radius               # no added shape out in the margin


def test_the_answer_page_circles_the_same_changes(monkeypatch):
    from inkengine import patterns
    s = Settings(gen="spot", spot_base="truchet", complexity=6, seed=31, dpi=150, booklet=True)
    g = geometry(s)
    page = replace(single_page(s), label="Spot the difference", page_no=2)
    found = draw_page(RecordingCanvas(), g, page, s)
    seen = []
    monkeypatch.setitem(patterns.GENERATORS, "spot", lambda *a, **k: seen.append(spot.draw(*a, **k)) or seen[-1])
    rec = RecordingCanvas()
    draw_page(rec, g, answer_page([page]), s)
    assert len(found) == spot.count(6)
    assert [q[:4] for q in seen[0]] == [q[:4] for q in found]          # the very same changes, in the same places
    assert not [op for op in rec.ops if op[0] == "text" and "differences" in str(op)]   # no caption repeated


def test_svg_stays_vector():
    s = Settings(gen="spot", spot_base="contour", complexity=7, seed=5, dpi=150)
    g = geometry(s)
    svg = SvgCanvas(g.W, g.H, g.w, g.h)
    draw_page(svg, g, single_page(s), s)
    out = str(svg)
    assert "<image" not in out and out.count("<path") > 10


# pages where the circles used to touch: close changes on busy pictures at the highest complexity
@pytest.mark.parametrize("base, orient, seed, dpi", [("contour", "landscape", 5, 150), ("mandala", "landscape", 3, 150),
                                                     ("mandala", "portrait", 8, 300)])
def test_answer_circles_never_overlap(base, orient, seed, dpi):
    from inkengine.page import line_width
    s = Settings(gen="spot", spot_base=base, complexity=10, seed=seed, orient=orient, dpi=dpi, booklet=True)
    g = geometry(s)
    lw = line_width(s, g)
    box = design_box(g, single_page(s), s)
    plain, rec = RecordingCanvas(), RecordingCanvas()
    found = spot.draw(plain, box, None, 10, s, lw=lw, seed=seed, dpi=g.dpi)
    spot.draw(rec, box, None, 10, s, lw=lw, seed=seed, dpi=g.dpi, solve=True)
    arcs = lambda c: [op for op in c.ops if op[0] == "A"]
    rings = arcs(rec)[len(arcs(plain)):]           # what solve adds: a circle per change in each copy
    assert len(rings) == 2 * len(found)
    first = rings[::2]
    for i, p in enumerate(first):
        for q in first[i + 1:]:
            assert math.hypot(p[1] - q[1], p[2] - q[2]) >= p[3] + q[3]
