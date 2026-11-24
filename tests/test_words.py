"""The Python word search against recordings of index.html's genWords (tests/fixtures/words_js.json.gz)."""

import pytest
from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings
from inkengine.patterns import words
from inkengine.rng import mulberry32

CASES = load_fixture("words")


def draw(k):
    ctx = RecordingCanvas()
    ctx.line_width = k["lw"]
    s = Settings(gen="words", ws_theme=k["theme"], ws_words=k["list"])
    ws = words.draw(ctx, Box(**k["box"]), mulberry32(k["seed"]), k["c"], s, lw=k["lw"], dpi=300, solve=k["solve"])
    return ctx, ws


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"{k['theme']}-seed{k['seed']}-c{k['c']}{'-answer' if k['solve'] else ''}")
def test_matches_javascript(k):
    ctx, ws = draw(k)
    assert ws["size"] == k["info"]["size"]
    assert [p["word"] for p in ws["placed"]] == k["info"]["words"]
    assert ws["skipped"] == k["info"]["skipped"]
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_every_theme_and_all_eight_directions():
    themes_2x = {"animals", "ocean", "space", "food", "weather", "sports", "custom"}   # 2.x's (the seasons came later)
    assert {k["theme"] for k in CASES} == themes_2x and themes_2x <= set(words.THEME_NAMES)
    assert len(words.level(max(k["c"] for k in CASES))["dirs"]) == 8


@pytest.mark.parametrize("theme", sorted(words.THEMES))
def test_every_word_appears_exactly_once(theme):
    for c in (1, 4, 7, 10):
        rnd = mulberry32(c * 7 + len(theme))
        ws = words.make_word_search(rnd, c, words.word_pool(rnd, c, theme))
        assert ws and len(ws["placed"]) >= 5
        assert all(ch.isalpha() and len(ch) == 1 for ch in ws["grid"])
        for p in ws["placed"]:
            assert words.find_word(ws["grid"], ws["size"], p["word"]) == 1


def test_own_list_cleaning_and_what_gets_left_out():
    rnd = mulberry32(1)
    pool = words.word_pool(rnd, 4, "custom", "Mum, dad;; Ann-Marie  mum x rainbow rain")
    assert pool == ["MUM", "DAD", "ANNMARIE", "RAINBOW", "RAIN"]
    ws = words.make_word_search(rnd, 1, pool)          # 8 x 8: ANNMARIE fits, RAINBOW too
    assert "RAIN (it's inside RAINBOW)" in ws["skipped"]
    assert words.note(ws).startswith("Left out: RAIN")
    assert words.word_pool(mulberry32(1), 4, "custom", " , ") == words.word_pool(mulberry32(1), 4, "animals")


def test_find_word_counts_palindromes_once():
    grid = list("ABBA" + "XXXX" + "XXXX" + "XXXX")
    assert words.find_word(grid, 4, "ABBA") == 1
