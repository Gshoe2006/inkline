"""Early maths with pictures: ten frames, number bonds, place value and counting."""

import pytest
from PySide6.QtWidgets import QApplication

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings
from inkengine.patterns import early
from inkengine.rng import mulberry32


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


@pytest.mark.parametrize("kind", list(early.KINDS))
@pytest.mark.parametrize("c", [1, 5, 10])
def test_items_are_in_range_and_never_twice_in_a_row(kind, c):
    items = early.make_items(mulberry32(c * 7), c, kind)
    cols, rows = early.GRID[kind]
    assert len(items) == cols * rows
    hi = early.top(kind, c)
    for (a, d), (b, _e) in zip(items, items[1:]):
        assert a != b or kind == "bonds"
    for answer, d in items:
        if kind == "bonds":
            whole, x, y = d["parts"]
            assert x + y == whole and x >= 1 and y >= 1 and 3 <= whole <= hi and answer == d["parts"][d["blank"]]
        elif kind == "placevalue":
            assert 11 <= answer <= hi
        else:
            assert (2 if kind == "counting" else 1) <= answer <= hi
    assert early.top("placevalue", 1) == 30 and early.top("placevalue", 10) == 99 and early.top("tenframe", 9) == 20


def _ops(ctx, kind):
    return [op for op in ctx.ops if op[0] == kind]


@pytest.mark.parametrize("kind", list(early.KINDS))
def test_the_sheet_and_its_answers_are_drawn(kind):
    box = Box(0, 0, 800, 1000)
    sheet, key = RecordingCanvas(), RecordingCanvas()
    out = early.draw(sheet, box, mulberry32(3), 6, Settings(early_kind=kind), dpi=100)
    again = early.draw(key, box, mulberry32(3), 6, Settings(early_kind=kind), dpi=100, solve=True)
    assert out["answers"] == again["answers"]                 # the answer page is the same sheet
    texts = [op[1] for op in _ops(key, "text")]
    for a in out["answers"]:
        assert str(a) in texts                                 # each answer written in
    assert len(_ops(key, "text")) > len(_ops(sheet, "text"))


def test_ten_frames_fill_the_right_number_of_spaces():
    ctx = RecordingCanvas()
    early._ten_frame(ctx, 0, 0, 100, 7, 1.0)
    assert len([op for op in ctx.ops if op[0] == "fill"]) == 7 and len([op for op in ctx.ops if op[0] == "stroke_rect"]) == 10


def test_counting_shapes_stay_apart_and_inside():
    spots = early._scatter(12, 99, 300, 200, 10)
    assert len(spots) == 12 and all(10 <= x <= 290 and 10 <= y <= 190 for x, y in spots)
    import math
    assert min(math.dist(p, q) for i, p in enumerate(spots) for q in spots[i + 1:]) > 10
