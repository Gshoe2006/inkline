"""The Python sudoku against recordings of index.html's genSudoku (tests/fixtures/sudoku_js.json.gz)."""

import time

import pytest
from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.patterns import sudoku
from inkengine.rng import mulberry32

CASES = load_fixture("sudoku")


def draw(k):
    ctx = RecordingCanvas()
    ctx.line_width = k["lw"]
    info = sudoku.draw(ctx, Box(**k["box"]), mulberry32(k["seed"]), k["c"], lw=k["lw"], dpi=300, solve=k["solve"])
    return ctx, info


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"seed{k['seed']}-c{k['c']}{'-answer' if k['solve'] else ''}")
def test_matches_javascript(k):
    ctx, info = draw(k)
    assert (info["clues"], info["level"]) == (k["info"]["clues"], k["info"]["level"])
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_every_level():
    assert {k["info"]["level"] for k in CASES} == {"Easy", "Medium", "Hard", "Expert"}


def valid_solution(g):
    groups = [[r * 9 + c for c in range(9)] for r in range(9)] + [[r * 9 + c for r in range(9)] for c in range(9)]
    groups += [[(br + r) * 9 + bc + c for r in range(3) for c in range(3)] for br in (0, 3, 6) for bc in (0, 3, 6)]
    return all(sorted(g[i] for i in grp) == list(range(1, 10)) for grp in groups)


@pytest.mark.parametrize("c", [1, 4, 7, 10])
def test_every_puzzle_is_fair(c):
    """A full valid solution, givens that agree with it, exactly one solution, and the clues the slider asks for."""
    for seed in range(1, 6):
        puzzle, solution, clues = sudoku.make_sudoku(mulberry32(seed * 101 + c), c)
        assert valid_solution(solution)
        assert all(p in (0, s) for p, s in zip(puzzle, solution))
        assert clues == sum(1 for p in puzzle if p)
        assert sudoku.count_solutions(puzzle) == 1
        assert clues <= int(48 - (c - 1) * 2.6 + 0.5) + 2


def test_counter_sees_more_than_one_solution():
    puzzle, solution, _ = sudoku.make_sudoku(mulberry32(3), 5)
    assert sudoku.count_solutions([0] * 81) == 2           # an empty grid: many, counted no further than 2
    emptied = [0 if i < 27 else d for i, d in enumerate(solution)]
    assert sudoku.count_solutions(emptied, limit=10) >= 1


def test_hardest_puzzle_is_quick():
    t = time.perf_counter()
    for seed in range(1, 4):
        sudoku.make_sudoku(mulberry32(seed), 10)
    assert time.perf_counter() - t < 6
