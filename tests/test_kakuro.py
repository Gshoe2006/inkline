"""Kakuro: a valid layout, clues that match the filling, no repeats, and exactly one solution."""

import itertools
import time
from dataclasses import replace

import pytest

from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings, answer_page, draw_page, geometry, single_page
from inkengine.patterns import HAS_ANSWER, NAMES, kakuro
from inkengine.rng import mulberry32


def test_sizes_and_names():
    assert [kakuro.size(c) for c in (1, 5, 10)] == [4, 6, 8]
    assert NAMES["kakuro"] == "Kakuro" and "kakuro" in HAS_ANSWER


@pytest.mark.parametrize("c", [1, 4, 7, 10])
@pytest.mark.parametrize("seed", [1, 2, 3, 99])
def test_puzzles_are_valid_and_come_out_one_way(c, seed):
    white, runs, solution, starters, N = kakuro.make_kakuro(mulberry32(seed), c)
    n = N - 1
    cells = {(r, q) for r in range(N) for q in range(N) if white[r][q]}
    assert set(solution) == cells and all(r > 0 and q > 0 for r, q in cells)    # clue row and column stay clue squares
    assert all(white[r][q] == white[N - r][N - q] for r, q in itertools.product(range(1, N), repeat=2))   # symmetric
    covered = {}
    for across, run, total in runs:
        assert 2 <= len(run) <= 9
        digits = [solution[q] for q in run]
        assert len(set(digits)) == len(digits) and sum(digits) == total and all(1 <= d <= 9 for d in digits)
        for q in run:
            covered.setdefault(q, set()).add(across)
    assert all(covered.get(q) == {True, False} for q in cells)   # every square has an across and a down clue
    assert set(starters) <= cells and all(starters[q] == solution[q] for q in starters)
    assert len(starters) < len(cells) * 0.6
    # exactly one solution, checked again from the printed clues alone
    p = kakuro._Puzzle(white, N)
    sums = {tuple(run): total for _a, run, total in runs}
    assert p.count([sums[tuple(run)] for _a, run in p.runs], limit=2, givens=starters) == 1
    assert {**starters, **p.solutions[0]} == solution
    assert n == kakuro.size(c)


def test_same_seed_same_puzzle_and_quick():
    t = time.time()
    a = kakuro.make_kakuro(mulberry32(5), 10)
    assert time.time() - t < 5
    assert a == kakuro.make_kakuro(mulberry32(5), 10)


def test_the_answer_page_shows_the_same_puzzle_filled_in():
    s = Settings(gen="kakuro", complexity=8, seed=12, dpi=150, booklet=True)
    g = geometry(s)
    page = replace(single_page(s), label="Kakuro", page_no=3)
    puzzle = draw_page(RecordingCanvas(), g, page, s)
    rec = RecordingCanvas()
    draw_page(rec, g, answer_page([page]), s)
    texts = [op[1] for op in rec.ops if op[0] == "text"]
    digits = [t for t in texts if t.isdigit() and len(t) == 1]
    # every square's digit is written on the answer page (single digits; clues of 10+ are two)
    assert len(digits) >= len(puzzle["solution"])
    assert kakuro.INSTRUCTIONS not in texts


def test_no_empty_grey_rows_or_columns_are_drawn():
    from inkengine.box import Box
    trimmed = 0
    for seed in range(1, 40):
        rec = RecordingCanvas()
        r = kakuro.draw(rec, Box(0, 0, 1000, 1200), mulberry32(seed), 6, lw=2, dpi=150, solve=True)
        rows = {q[0] for q in r["solution"]}
        cols = {q[1] for q in r["solution"]}
        nr, nc = max(rows) - min(rows) + 2, max(cols) - min(cols) + 2   # the white squares, plus one clue row and column
        frame = next(op for op in rec.ops if op[0] == "stroke_rect")   # the outer border
        assert frame[3] / frame[4] == pytest.approx(nc / nr)
        trimmed += (nr, nc) != (len(r["white"]), len(r["white"]))
    assert trimmed   # some layouts did leave room to trim
