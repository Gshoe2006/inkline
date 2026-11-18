"""The Python woven tiles against recordings of index.html's genTruchet (tests/fixtures/truchet_js.json)."""

import json
import math
import os

import pytest
from recording import same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.patterns import truchet
from inkengine.rng import mulberry32

with open(os.path.join(os.path.dirname(__file__), "fixtures", "truchet_js.json")) as f:
    CASES = json.load(f)


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"seed{k['seed']}-c{k['c']}")
def test_matches_javascript(k):
    ctx = RecordingCanvas()
    ctx.line_width = k["lw"]
    truchet.draw(ctx, Box(**k["box"]), mulberry32(k["seed"]), k["c"])
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_one_and_three_arcs():
    assert {1 if k["c"] <= 3 else 3 for k in CASES} == {1, 3}


def test_tiles_cover_the_box_and_flip_about_half():
    box = Box(0, 0, 1000, 1400)
    for c in (1, 5, 10):
        info = truchet.draw(RecordingCanvas(), box, mulberry32(c), c)
        assert info["cols"] * info["tile"] >= box.w and info["rows"] * info["tile"] >= box.h
        n = info["cols"] * info["rows"]
        assert 0.25 * n <= info["flipped"] <= 0.75 * n
        assert info["arcs_per_corner"] == (3 if c > 3 else 1)


def test_arcs_start_where_the_move_left_off():
    """Each move_to sits on its arc's start, so no stray joining lines are drawn."""
    ctx = RecordingCanvas()
    truchet.draw(ctx, Box(0, 0, 500, 500), mulberry32(3), 5)
    ops = ctx.ops
    for prev, op in zip(ops, ops[1:]):
        if op[0] == "A":
            _, cx, cy, r, a0, *_ = op
            assert prev[0] == "M"
            assert prev[1] == pytest.approx(cx + r * math.cos(a0)) and prev[2] == pytest.approx(cy + r * math.sin(a0))
