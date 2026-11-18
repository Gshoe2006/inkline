"""The Python nonogram against recordings of index.html's genNonogram (tests/fixtures/nonogram_js.json.gz)."""

import time

import pytest
from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.patterns import nonogram
from inkengine.rng import mulberry32

CASES = load_fixture("nonogram")


def draw(k):
    ctx = RecordingCanvas()
    ctx.line_width = k["lw"]
    nono = nonogram.draw(ctx, Box(**k["box"]), mulberry32(k["seed"]), k["c"], lw=k["lw"], dpi=300, solve=k["solve"])
    return ctx, nono


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"seed{k['seed']}-c{k['c']}{'-answer' if k['solve'] else ''}")
def test_matches_javascript(k):
    ctx, nono = draw(k)
    i = k["info"]
    assert (nono["size"], nono["attempts"]) == (i["size"], i["attempts"])
    assert "".join(map(str, nono["pic"])) == i["pic"]
    assert (nono["rows"], nono["cols"]) == (i["rows"], i["cols"])
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_smallest_and_largest():
    assert {k["info"]["size"] for k in CASES} >= {5, 20}


@pytest.mark.parametrize("c", [1, 4, 7, 10])
def test_every_puzzle_solves_by_logic_alone(c):
    """Line-by-line logic finishes the picture from the clues alone, so it has exactly one solution."""
    for seed in range(1, 6):
        nono = nonogram.make_nonogram(mulberry32(seed * 13 + c), c)
        n = nono["size"]
        assert n == nonogram.size_for(c)
        assert 0.4 <= sum(nono["pic"]) / (n * n) <= 0.65
        assert nonogram.solve(nono["rows"], nono["cols"]) == nono["pic"]
        for r in range(n):     # mirrored left to right
            row = nono["pic"][r * n:r * n + n]
            assert row == row[::-1]


def test_line_solver():
    assert nonogram.solve_line([3], [-1] * 5) == [-1, -1, 1, -1, -1]        # the middle square is forced
    assert nonogram.solve_line([2, 2], [-1] * 5) == [1, 1, 0, 1, 1]
    assert nonogram.solve_line([], [-1, -1]) == [0, 0]
    assert nonogram.solve_line([3], [-1, 0, -1, -1, 0]) is None             # no room for a run of 3
    assert nonogram.runs([1, 1, 0, 1, 0, 0, 1, 1, 1]) == [2, 1, 3]


def test_ambiguous_puzzle_is_left_undecided():
    """Two diagonals give the same clues: logic can't choose, so those squares stay -1."""
    rows, cols = nonogram.clues([1, 0, 0, 1], 2)
    assert nonogram.solve(rows, cols) == [-1, -1, -1, -1]


def test_largest_puzzle_is_quick():
    t = time.perf_counter()
    for seed in range(1, 4):
        nonogram.make_nonogram(mulberry32(seed), 10)
    assert time.perf_counter() - t < 8
