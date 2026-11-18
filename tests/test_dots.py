"""The Python dot-to-dot against recordings of index.html's genDots (tests/fixtures/dots_js.json.gz).

Number placement depends on text width, so the recordings and these tests use the same stand-in
width (0.55 font sizes per character); with that, every step must match.
"""

import pytest
from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.patterns import dots
from inkengine.rng import mulberry32
from inkengine.shapes import DOT_SHAPES

CASES = load_fixture("dots")


def draw(k):
    ctx = RecordingCanvas(em_per_char=0.55)
    ctx.line_width = k["lw"]
    info = dots.draw(ctx, Box(**k["box"]), mulberry32(k["seed"]), k["c"], lw=k["lw"], dpi=300, connect=k["connect"])
    return ctx, info


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"{k['info']['shape']}-seed{k['seed']}-c{k['c']}{'-answer' if k['connect'] else ''}")
def test_matches_javascript(k):
    ctx, info = draw(k)
    assert (info["shape"], info["dots"], info["overlaps"]) == (k["info"]["shape"], k["info"]["dots"], k["info"]["overlaps"])
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_every_shape_and_answers():
    assert {k["info"]["shape"] for k in CASES} == set(DOT_SHAPES)
    assert {k["connect"] for k in CASES} == {True, False}


@pytest.mark.parametrize("seed", range(1, 25))
def test_numbers_find_free_spots_with_real_fonts(seed):
    """With the real font measured, every number still gets a spot clear of dots and other numbers."""
    for c in (1, 5, 10):
        info = dots.draw(RecordingCanvas(), Box(150, 150, 2250, 3000), mulberry32(seed), c, lw=8, dpi=300)
        # about 10 + 8c dots: every corner gets one and the rest are rounded per stretch, so a few either way
        assert abs(info["dots"] - (10 + c * 8)) <= 6 or info["shape"] == "flower"
        assert info["overlaps"] == 0, f"{info['shape']} complexity {c}: {info['overlaps']} numbers overlap"


def test_answer_draws_the_same_dots():
    k = next(k for k in CASES if not k["connect"])
    puzzle = draw(k)[1]
    answer = dots.draw(RecordingCanvas(), Box(**k["box"]), mulberry32(k["seed"]), k["c"], lw=8, dpi=300, connect=True)
    assert (answer["shape"], answer["dots"]) == (puzzle["shape"], puzzle["dots"])
