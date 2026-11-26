"""Bingo cards: a different card for every child, and one caller's sheet for them all."""

import pytest
from PySide6.QtWidgets import QApplication

from inkengine import i18n
from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings
from inkengine.patterns import bingo
from inkengine.rng import mulberry32


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


def _texts(ctx):
    return [op[1] for op in ctx.ops if op[0] == "text"]


def cells(grid):
    return [x for row in grid for x in row]


@pytest.mark.parametrize("kind", list(bingo.KINDS))
@pytest.mark.parametrize("c,n", [(1, 3), (3, 3), (4, 4), (7, 4), (8, 5), (10, 5)])
def test_the_card_grows_with_complexity_and_has_no_repeats(kind, c, n):
    s = Settings(bingo_kind=kind)
    grid = bingo.card(mulberry32(7), c, s)
    assert len(grid) == n and all(len(row) == n for row in grid)
    filled = [x for x in cells(grid) if x is not None]
    assert len(filled) == len(set(filled)) == n * n - (1 if n == 5 else 0)
    assert (grid[2][2] is None) == (n == 5)                    # the free square, in the middle of a 5 x 5
    called = {shown for shown, _said in bingo.pool(c, s)}
    assert set(filled) <= called                               # everything on the card can be called


def test_the_classic_card_takes_each_column_from_its_fifteen():
    for seed in range(20):
        grid = bingo.card(mulberry32(seed), 9, Settings())
        for k in range(5):
            col = [int(row[k]) for row in grid if row[k] is not None]
            assert all(15 * k + 1 <= v <= 15 * k + 15 for v in col) and col == sorted(col)
    assert [said for _shown, said in bingo.pool(9, Settings())][:2] == ["B 1", "B 2"]
    assert len(bingo.pool(9, Settings())) == 75 and len(bingo.pool(1, Settings())) == 20


def test_cards_differ_but_the_caller_doesnt():
    s = Settings(bingo_kind="sums")
    cards = {tuple(cells(bingo.card(mulberry32(seed), 5, s))) for seed in range(30)}
    assert len(cards) == 30
    assert bingo.pool(5, s) == bingo.pool(5, s)                 # what's called depends on nothing seeded
    for c in (2, 5, 9):
        sums = bingo._sums(c)
        assert len({a for a, _ in sums}) == len(sums) <= bingo.MAX_POOL
        for answer, text in sums:                               # each sum is right
            assert eval(text.replace("×", "*").replace("−", "-")) == int(answer)


def test_words_come_from_the_theme_or_your_own_list():
    s = Settings(bingo_kind="words", bingo_theme="sight1")
    assert set(cells(bingo.card(mulberry32(1), 5, s))) <= set(w for w, _ in bingo.pool(5, s))
    own = Settings(bingo_kind="words", bingo_theme="custom", bingo_words="cat, dog, sun, hat, pen, cup, bus, box, "
                                                                          "map, egg, jam")
    assert len(bingo.card(mulberry32(1), 9, own)) == 3          # eleven words: a 3 x 3 card, so cards still differ
    spaced = Settings(bingo_kind="words", bingo_theme="custom", bingo_words="a b c d e f g h i j k l m n o p q r")
    assert len(bingo.card(mulberry32(1), 9, spaced)) == 4
    short = Settings(bingo_kind="words", bingo_theme="custom", bingo_words="cat dog sun")
    assert bingo.card(mulberry32(1), 9, short) is None
    ctx = RecordingCanvas()
    assert bingo.draw(ctx, Box(0, 0, 800, 1000), mulberry32(1), 9, short, dpi=100) is None
    assert any("at least 9" in t for t in _texts(ctx))
    dup = Settings(bingo_kind="words", bingo_theme="custom", bingo_words="Cat, cat, CAT, dog")
    assert [w for w, _ in bingo.pool(1, dup)] == ["Cat", "dog"]


def test_words_follow_the_language():
    try:
        i18n.set_language("es")
        words = [w for w, _ in bingo.pool(5, Settings(bingo_kind="words", bingo_theme="animals"))]
        assert "perro" in [w.lower() for w in words] or "gato" in [w.lower() for w in words]
        ctx = RecordingCanvas()
        bingo.draw(ctx, Box(0, 0, 800, 1000), mulberry32(1), 9, Settings(), dpi=100)
        assert "LIBRE" in _texts(ctx)
    finally:
        i18n.set_language("en")


def test_the_card_and_the_callers_sheet_are_drawn():
    box = Box(0, 0, 800, 1000)
    ctx = RecordingCanvas()
    out = bingo.draw(ctx, box, mulberry32(3), 9, Settings(), dpi=100)
    texts = _texts(ctx)
    assert out["size"] == 5 and list("BINGO") == texts[:5] and "FREE" in texts
    assert set(t for t in cells(out["card"]) if t) <= set(texts)
    key = RecordingCanvas()
    called = bingo.draw(key, box, mulberry32(3), 9, Settings(), dpi=100, solve=True)
    assert called["called"] == 75 and "Caller's sheet" in _texts(key) and "O 75" in _texts(key)
    sums = RecordingCanvas()
    bingo.draw(sums, box, mulberry32(3), 2, Settings(bingo_kind="sums"), dpi=100, solve=True)
    assert any(t.endswith(" = 20") for t in _texts(sums))     # the caller sees each sum's answer


# --- copies: every child a different card; one caller's sheet ---------------------------------------------------
def _cards(**kw):
    from inkapp import jobs
    from inkapp.state import State
    from inkengine import patterns
    seen, keys = [], []
    real = bingo.draw

    def spy(*a, **k):
        out = real(*a, **k)
        (keys if k.get("solve") else seen).append(out)
        return out
    patterns.GENERATORS["bingo"] = spy
    try:
        j = jobs.job(State(Settings(gen="bingo", dpi=30, complexity=5, name_line=True)), **kw)
        for i in range(j.count):
            j.draw(RecordingCanvas(), i)
    finally:
        patterns.GENERATORS["bingo"] = real
    return j, seen, keys


def test_copies_are_all_different_cards_even_without_asking():
    j, seen, keys = _cards(copies=4, vary=False)
    assert len(seen) == 4 and len({tuple(cells(o["card"])) for o in seen}) == 4
    _j, named, _ = _cards(names=["Ana", "Ben", "Cy"])
    assert len({tuple(cells(o["card"])) for o in named}) == 3


def test_answer_pages_are_one_callers_sheet_for_every_card():
    j, seen, keys = _cards(copies=6, answers=True)
    assert len(seen) == 6 and len(keys) == 1 and j.answers == 1 and keys[0]["called"] == 40


def test_always_vary_only_for_bingo():
    from inkapp.classset import always_vary
    assert always_vary(Settings(gen="bingo")) and not always_vary(Settings(gen="maze"))
    assert not always_vary(Settings(gen="bingo", mode="convert"))
    assert always_vary(Settings(gen="maze", booklet=True, page_list=[{"gen": "maze"}, {"gen": "bingo"}]))
    assert always_vary(Settings(gen="maze", sheet="halves", panel_gens="bingo"))


# --- the sidebar ------------------------------------------------------------------------------------------------
@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("5.7.0", remember=False)
    w.show()
    yield w


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_the_sidebar_shows_bingos_options(win):
    sb = win.sidebar
    _set(win, gen="bingo")
    assert sb.bingo_opts.isVisibleTo(sb) and not sb.bingo_theme_row.isVisibleTo(sb)
    sb.bingo_kind.set_value("words")
    assert win.state.settings.bingo_kind == "words"
    _set(win, bingo_kind="words")
    assert sb.bingo_theme_row.isVisibleTo(sb) and not sb.bingo_words_row.isVisibleTo(sb)
    _set(win, bingo_theme="custom")
    assert sb.bingo_words_row.isVisibleTo(sb)
    _set(win, gen="maze")
    assert not sb.bingo_opts.isVisibleTo(sb)


def test_copies_of_bingo_dont_offer_alike_cards(win):
    sb = win.sidebar
    sb.copies.setText("3")
    _set(win, gen="maze")
    maze_offers = sb.copies_vary.isVisibleTo(sb)
    _set(win, gen="bingo")
    assert maze_offers and not sb.copies_vary.isVisibleTo(sb)
    assert "its own design" in sb.copies_hint.text() or "own designs" in sb.copies_hint.text()
