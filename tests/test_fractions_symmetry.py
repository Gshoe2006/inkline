"""Fractions, number lines, times grids and symmetry: what each sheet asks, and that the answers are right."""

import pytest

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings, draw_page, geometry, single_page
from inkengine.patterns import fractions, symmetry
from inkengine.rng import mulberry32


def _texts(ctx):
    return [op[1] for op in ctx.ops if op[0] == "text"]


@pytest.mark.parametrize("c, top", [(1, 4), (3, 4), (5, 8), (7, 12), (10, 12)])
def test_fractions_are_proper_and_grow_with_complexity(c, top):
    for seed in range(10):
        items = fractions.make_fractions(mulberry32(seed), c)
        assert len(items) == (6 if c <= 3 else 9)
        assert len({(n, k, task) for _s, n, k, task in items}) == len(items)
        for shape, n, k, task in items:
            assert 2 <= n <= top and 1 <= k < n and task in ("name", "shade")
            assert shape in ("circle", "bar") or (shape == "square" and n in (4, 9))
            if c < 5:
                assert task == "name"


def test_a_fraction_sheet_hides_its_answers_and_the_answers_name_them():
    s = Settings(gen="fractions", frac_kind="fractions", complexity=7)
    plain, solved = RecordingCanvas(), RecordingCanvas()
    out = fractions.draw(plain, Box(0, 0, 900, 1200), mulberry32(3), 7, s, dpi=100)
    fractions.draw(solved, Box(0, 0, 900, 1200), mulberry32(3), 7, s, dpi=100, solve=True)
    named = [f"{k}/{n}" for _s, n, k, task in out["fractions"] if task == "name"]
    assert named and not set(named) & set(_texts(plain)) and set(named) <= set(_texts(solved))
    shade = [f"Shade {k}/{n}" for _s, n, k, task in out["fractions"] if task == "shade"]
    assert set(shade) <= set(_texts(plain))
    assert sum(op[0] == "fill" for op in solved.ops) > sum(op[0] == "fill" for op in plain.ops)


def test_the_parts_of_a_shape_are_equal():
    for shape, n in (("bar", 5), ("square", 9), ("circle", 7)):
        parts = fractions._parts(shape, n, 0, 0, 100, 100)
        assert len(parts) == n

        def area(pts):
            return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2
        areas = [area(p) for p in parts]
        assert max(areas) - min(areas) < 1e-6 * max(areas) + 1e-6


@pytest.mark.parametrize("c", range(1, 11))
def test_number_lines_count_evenly_and_hide_some_marks(c):
    for start, step, marks, shown, tenths in fractions.make_lines(mulberry32(c), c):
        assert marks == (9 if c <= 4 else 11) and shown[0] and shown.count(False) == (2 if c <= 2 else 3 if c <= 6 else 4)
        assert tenths == (c >= 9)
        if 7 <= c <= 8:
            assert start < 0
        assert step in {1: (1,), 2: (1,), 3: (2, 5, 10), 4: (2, 5, 10), 5: (10, 25, 100), 6: (10, 25, 100)}.get(c, (1, 2, 5))


def test_tenths_use_the_languages_decimal_mark():
    from inkengine import i18n
    assert fractions.decimal(1.2) == "1.2" and fractions.decimal(2.0) == "2"
    i18n.set_language("de")
    try:
        assert fractions.decimal(1.2) == "1,2"
    finally:
        i18n.set_language("en")


@pytest.mark.parametrize("c, n", [(1, 5), (4, 8), (7, 10), (10, 12)])
def test_a_times_grid_has_its_size_and_answers_every_blank(c, n):
    across, down, blanks = fractions.make_grid(mulberry32(c), c)
    assert sorted(across) == sorted(down) == list(range(1, n + 1)) and blanks
    assert (across == list(range(1, n + 1))) == (c < 5)
    solved = RecordingCanvas()
    fractions.draw(solved, Box(0, 0, 900, 900), mulberry32(c), c, Settings(frac_kind="timesgrid"), dpi=100, solve=True)
    numbers = _texts(solved)
    for r, k in blanks:
        assert str(down[r] * across[k]) in numbers


@pytest.mark.parametrize("c", [1, 4, 7, 10])
def test_symmetry_gives_one_part_touching_the_mirror_and_the_answer_mirrors_it(c):
    for seed in range(8):
        cols, rows, quarters, shaded = symmetry.make_picture(mulberry32(seed), c)
        assert cols % 2 == rows % 2 == 0 and quarters == (c >= 7)
        assert all(k < cols // 2 and (r < rows // 2 or not quarters) for r, k in shaded)
        assert any(k == cols // 2 - 1 for _r, k in shaded)                 # touches the mirror line
        full = symmetry.whole(cols, rows, quarters, shaded)
        assert all((r, cols - 1 - k) in full for r, k in full)              # mirrored left to right
        if quarters:
            assert all((rows - 1 - r, k) in full for r, k in full)          # and top to bottom
        # one shape: every square reachable from the first
        seen, todo = set(), [next(iter(shaded))]
        while todo:
            r, k = todo.pop()
            if (r, k) in seen or (r, k) not in shaded:
                continue
            seen.add((r, k))
            todo += [(r + 1, k), (r - 1, k), (r, k + 1), (r, k - 1)]
        assert seen == shaded


@pytest.mark.parametrize("gen", ["fractions", "symmetry"])
def test_the_new_pages_draw_and_have_answers_in_a_booklet(gen):
    s = Settings(gen=gen, dpi=40)
    draw_page(RecordingCanvas(), geometry(s), single_page(s), s)
    from inkengine import book
    kinds = [p.kind for p in book.book_pages(Settings(gen=gen, dpi=40, booklet=True, pages=2, key=True))]
    assert kinds.count("design") == 2 and "answers" in kinds


def test_seasonal_themes_in_every_puzzle_and_language():
    from inkengine import i18n, pack
    from inkengine.patterns import crossword, words
    for season in ("autumn", "halloween", "winter", "spring", "summer"):
        assert season in words.THEME_NAMES and season in crossword.THEME_NAMES and season in pack.THEME_NAMES
        for code in i18n.LANGUAGES:
            ws = words.THEMES_BY_LANGUAGE.get(code, words.THEMES)[season].split()
            cw = crossword.parse_entries(crossword.THEMES_BY_LANGUAGE.get(code, crossword.THEMES)[season])
            assert len(ws) >= 18 and len(cw) >= 14, (season, code)
