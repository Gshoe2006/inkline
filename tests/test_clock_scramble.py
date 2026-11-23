"""Telling the time, unscramble, and the newer kinds of sum: what each sheet asks, and its answers."""

import math

import pytest

from inkengine.canvas import RecordingCanvas
from inkengine.box import Box
from inkengine.page import Settings, geometry, draw_page, single_page
from inkengine.patterns import clock, maths, scramble
from inkengine.rng import mulberry32


@pytest.mark.parametrize("c, step, count", [(1, 60, 6), (3, 30, 6), (5, 15, 9), (7, 5, 9), (10, 1, 12)])
def test_clock_times_get_more_exact_and_never_repeat(c, step, count):
    for seed in range(20):
        times = clock.make_times(mulberry32(seed), c, "mixed")
        assert len(times) == count and len({(h, m) for h, m, _k in times}) == count
        assert all(1 <= h <= 12 and m % step == 0 and 0 <= m < 60 for h, m, _k in times)
        assert {k for _h, _m, k in times} <= {"read", "draw"}
    assert {k for _h, _m, k in clock.make_times(mulberry32(1), 5, "read")} == {"read"}
    assert clock.time_text(3, 5) == "3:05" and clock.time_text(12, 0) == "12:00"


def _texts(ctx):
    return [op[1] for op in ctx.ops if op[0] == "text"]


def test_a_clock_to_read_has_hands_and_a_line_and_its_answer_writes_the_time():
    s = Settings(gen="clock", clock_task="read", complexity=4)
    ctx = RecordingCanvas()
    out = clock.draw(ctx, Box(0, 0, 900, 1200), mulberry32(7), 4, s, dpi=100)
    shown = [clock.time_text(h, m) for h, m, _k in out["clocks"]]
    assert not set(shown) & set(_texts(ctx))   # the times aren't given away
    solved = RecordingCanvas()
    clock.draw(solved, Box(0, 0, 900, 1200), mulberry32(7), 4, s, dpi=100, solve=True)
    assert set(shown) <= set(_texts(solved))


def test_a_clock_to_draw_gives_the_time_and_its_answer_draws_the_hands():
    s = Settings(gen="clock", clock_task="draw", complexity=6)
    plain, solved = RecordingCanvas(), RecordingCanvas()
    out = clock.draw(plain, Box(0, 0, 900, 1200), mulberry32(3), 6, s, dpi=100)
    clock.draw(solved, Box(0, 0, 900, 1200), mulberry32(3), 6, s, dpi=100, solve=True)
    assert {clock.time_text(h, m) for h, m, _k in out["clocks"]} <= set(_texts(plain))
    assert sum(op[0] == "stroke" for op in solved.ops) == sum(op[0] == "stroke" for op in plain.ops) + 2 * len(out["clocks"])


def test_hands_point_the_right_way():
    ctx = RecordingCanvas()
    clock._hands(ctx, 0, 0, 100, 3, 0, 1)
    lines = [op for op in ctx.ops if op[0] == "L"]
    (hx, hy), (mx, my) = lines[0][1:3], lines[1][1:3]
    assert hx == pytest.approx(50) and hy == pytest.approx(0, abs=1e-6)    # the hour hand at 3
    assert mx == pytest.approx(0, abs=1e-6) and my == pytest.approx(-78)   # the minute hand at 12


def test_unscramble_mixes_every_word_and_answers_with_it():
    for seed in range(30):
        items = scramble.make_sheet(mulberry32(seed), 5)
        assert len(items) == 10
        for word, mixed in items:
            assert sorted(word) == sorted(mixed) and mixed != word
    own = scramble.make_sheet(mulberry32(1), 1, "custom", "because, friend, said, aa")
    assert [w for w, _m in own] == ["BECAUSE", "FRIEND", "SAID", "AA"]
    assert dict(own)["AA"] == "AA"   # every letter the same: there's no other order
    s = Settings(gen="scramble", ws_theme="custom", ws_words="because, friend")
    solved = RecordingCanvas()
    scramble.draw(solved, Box(0, 0, 900, 1200), mulberry32(2), 5, s, dpi=100, solve=True)
    assert {"BECAUSE", "FRIEND"} <= set(_texts(solved))


@pytest.mark.parametrize("kind", ["divide", "missing"])
def test_sharing_and_missing_numbers_are_true_whole_number_sums(kind):
    for c in range(1, 11):
        for s in maths.make_sheet(mulberry32(c), c, kind):
            a, sign, b, answer, blank = s
            assert {"+": a + b, "−": a - b, "×": a * b, "÷": a / b}[sign] == answer and answer >= 0
            if kind == "divide":
                assert sign == "÷" and blank == "result" and b >= 2 and answer >= 2
            else:
                assert sign in "+−×" and blank in ("left", "right")


def test_mixed_sums_are_as_5_0_made_them():
    """Projects saved with 5.0's "All of them, mixed" open with the same sums."""
    sheet = maths.make_sheet(mulberry32(42), 6, "mixed")
    assert {s[1] for s in sheet} <= {"+", "−", "×"} and len(sheet) == 24


@pytest.mark.parametrize("gen", ["clock", "scramble", "spelltest"])
def test_the_new_pages_draw_on_a_page_and_in_a_booklet_with_answers(gen):
    s = Settings(gen=gen, dpi=40)
    draw_page(RecordingCanvas(), geometry(s), single_page(s), s)
    from inkengine import book
    b = Settings(gen=gen, dpi=40, booklet=True, pages=2, key=True)
    kinds = [p.kind for p in book.book_pages(b)]
    assert kinds.count("design") == 2 and "answers" in kinds


def test_a_spelling_test_hides_the_words_and_its_answers_give_them_in_order():
    from inkengine.patterns import spelltest
    s = Settings(gen="spelltest", ws_theme="custom", ws_words="because, friend, said, which, there")
    plain, solved = RecordingCanvas(), RecordingCanvas()
    out = spelltest.draw(plain, Box(0, 0, 900, 1200), mulberry32(4), 5, s, dpi=100)
    spelltest.draw(solved, Box(0, 0, 900, 1200), mulberry32(4), 5, s, dpi=100, solve=True)
    words = [w.lower() for w in out["words"]]
    assert sorted(words) == ["because", "friend", "said", "there", "which"]
    assert not set(words) & set(_texts(plain)) and [f"{k}." for k in range(1, 6)] == _texts(plain)
    assert [t for t in _texts(solved) if not t.endswith(".")] == words
    orders = {tuple(spelltest.test_words(mulberry32(k), 5, "custom", "because, friend, said, which, there"))
              for k in range(10)}
    assert len(orders) > 1   # each design reads them in another order
    assert len(spelltest.test_words(mulberry32(1), 3, "animals")) == 8


def test_money_is_written_as_where_it_is_used():
    from inkengine import i18n
    from inkengine.patterns import money
    assert [money.fmt(v, "GBP") for v in (45, 100, 1205)] == ["45p", "£1.00", "£12.05"]
    assert [money.fmt(v, "USD") for v in (45, 1205)] == ["45¢", "$12.05"] and money.fmt(45, "EUR") == "45c"
    assert money.coin_label(200, "GBP") == "£2" and money.coin_label(25, "USD") == "25¢"
    assert money.currency("auto") == "GBP" and money.currency("USD") == "USD"
    i18n.set_language("fr")
    try:
        assert money.currency("auto") == "EUR" and money.fmt(45, "EUR") == "0,45 €" and money.fmt(1205, "EUR") == "12,05 €"
        assert money.coin_label(200, "EUR") == "2 €"
    finally:
        i18n.set_language("en")


def _cents(text):
    import re
    t = text.replace(",", ".")
    if re.fullmatch(r"\d+[pc¢]", t):
        return int(t[:-1])
    return round(float(re.sub(r"[^\d.]", "", t)) * 100)


@pytest.mark.parametrize("cur", ["GBP", "EUR", "USD"])
def test_money_sums_add_up_coins_are_real_and_change_is_from_a_note(cur):
    from inkengine.patterns import money
    for c in range(1, 11):
        sheet = maths.make_sheet(mulberry32(c * 3), c, "money", cur)
        assert len(sheet) == (8 if c <= 4 else min(18, maths.level(c)["count"]))
        for a, sign, b, answer, blank in sheet:
            if sign == "coins":
                assert c <= 4 and set(b) <= set(money.COINS[cur]) and 2 <= len(b) <= 4
                assert _cents(answer) == sum(b) and list(a) == [money.coin_label(v, cur) for v in b]
            else:
                assert c >= 5 and blank == "result"
                got = _cents(a) + _cents(b) if sign == "+" else _cents(a) - _cents(b)
                assert got == _cents(answer) and _cents(answer) >= 0
                if c <= 6:
                    assert _cents(a) % 10 == _cents(b) % 10 == 0 and _cents(answer) <= 500


def test_a_money_sheet_draws_its_coins_and_answers():
    s = Settings(gen="maths", maths_kind="money", money="GBP", complexity=3)
    plain, solved = RecordingCanvas(), RecordingCanvas()
    out = maths.draw(plain, Box(0, 0, 900, 1200), mulberry32(5), 3, s, dpi=100)
    maths.draw(solved, Box(0, 0, 900, 1200), mulberry32(5), 3, s, dpi=100, solve=True)
    labels = {lab for a, sign, *_ in out["sums"] for lab in a}
    assert labels <= set(_texts(plain))
    assert {ans for *_x, ans, _b in out["sums"]} <= set(_texts(solved))


@pytest.mark.parametrize("lang, family", [("en", "Playwrite GB J"), ("es", "Playwrite ES"), ("fr", "Playwrite FR Trad")])
def test_joined_up_handwriting_uses_the_languages_school_font(lang, family):
    from inkengine import i18n
    from inkengine.patterns import trace
    i18n.set_language(lang)
    try:
        s = Settings(gen="trace", trace_style="joined", trace_source="words", trace_text="because, señor")
        assert trace.font_for(s) == (family, 400)
        asc, xh, desc = trace.guide_lines(family, 400)
        assert asc > 0.8 and 0.45 < xh < 0.6 and desc > 0.3   # loops reach far higher and lower than print
        ctx = RecordingCanvas()
        trace.draw(ctx, Box(0, 0, 900, 1200), mulberry32(1), 4, s, dpi=100)
        assert any(op[0] == "text" for op in ctx.ops)
    finally:
        i18n.set_language("en")
    assert trace.font_for(Settings(gen="trace")) == ("", 500)
    assert trace.guide_lines("", 500) == trace.PRINT_LINES


def test_joined_up_writing_stays_inside_its_rows():
    """Each row's writing, ascenders to descenders, fits in the row (the French school style's loops are tall)."""
    from inkengine import i18n
    from inkengine.patterns import trace
    i18n.set_language("fr")
    try:
        s = Settings(gen="trace", trace_style="joined", trace_source="words", trace_text="because, friend, said")
        family, weight = trace.font_for(s)
        asc, _xh, desc = trace.guide_lines(family, weight)
        ctx = RecordingCanvas()
        out = trace.draw(ctx, Box(0, 0, 900, 1200), mulberry32(1), 4, s, dpi=100)
        rh = 1200 / len(out["rows"])
        sizes = {op[6] for op in ctx.ops if op[0] == "text"}
        assert all(size * (asc + desc) <= rh for size in sizes)
    finally:
        i18n.set_language("en")
