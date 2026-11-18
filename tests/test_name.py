"""The Python name page against recordings of index.html's genName (tests/fixtures/name_js.json.gz).

Line breaks and letter size depend on text width, so the recordings and these tests use the same
stand-in width (0.55 font sizes per character); with that, every step must match.
"""

import pytest
from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings
from inkengine.patterns import name
from inkengine.rng import mulberry32

CASES = load_fixture("name")


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"{(k['text'].strip() or 'empty').replace(' ', '_')}-{k['bg']}")
def test_matches_javascript(k):
    ctx = RecordingCanvas(em_per_char=0.55)
    ctx.line_width = k["lw"]
    s = Settings(gen="name", name_text=k["text"], name_bg=k["bg"])
    info = name.draw(ctx, Box(**k["box"]), mulberry32(k["seed"]), k["c"], s, lw=k["lw"], dpi=300, seed=k["seed"])
    assert info["lines"] == k["info"]["lines"]
    assert info["fs"] == pytest.approx(k["info"]["fs"], abs=1e-4)
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_every_background_and_up_to_four_lines():
    assert {k["bg"] for k in CASES} == set(name.BACKGROUNDS)
    assert {len(k["info"]["lines"]) for k in CASES} >= {1, 2, 3, 4}


def test_balance_lines_keeps_the_widest_line_narrow():
    width = len
    assert name.balance_lines(["aaaa", "bb", "cc", "dddddd"], 2, width) == ["aaaa bb", "cc dddddd"]   # widest 9, not 10 or 12
    # a tie (both splits' widest line is 8) keeps the first split found, as index.html does
    assert name.balance_lines(["a", "bb", "ccc", "dddd"], 2, width) == ["a bb", "ccc dddd"]
    assert name.balance_lines(["one", "two", "three"], 3, width) == ["one", "two", "three"]
    assert name.balance_lines(["Happy", "Birthday", "Maya"], 1, width) == ["Happy Birthday Maya"]


def test_text_is_tidied():
    assert name.clean_text("  Sam   and\tAlex ") == "Sam and Alex"
    assert name.clean_text("   ") == "Your name"
