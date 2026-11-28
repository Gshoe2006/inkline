"""Worksheets: maths drills and handwriting (tracing)."""

import re
from dataclasses import replace

import pytest
from PySide6.QtWidgets import QApplication

from inkengine.canvas import RecordingCanvas
from inkengine.box import Box
from inkengine.page import PageSpec, Settings, draw_page, geometry, has_answer, single_page
from inkengine.patterns import GENERATORS, HAS_ANSWER, maths, trace
from inkengine.rng import mulberry32


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


def _sheet(c, kind, seed=1):
    return maths.make_sheet(mulberry32(seed), c, kind)


@pytest.mark.parametrize("c", range(1, 11))
def test_maths_sums_are_right_in_range_and_never_repeat(c):
    lv = maths.level(c)
    for kind in ("add", "sub", "addsub", "times", "bonds", "mixed"):   # (sharing and missing numbers: test_clock_scramble)
        sums = _sheet(c, kind, seed=c * 7)
        assert len(sums) == lv["count"] and len({(s[0], s[1], s[2], s[4]) for s in sums}) == len(sums)
        for a, sign, b, answer, missing in sums:
            if sign == "+" and missing == "result":
                assert a + b == answer and answer <= lv["top"] and a >= 1 and b >= 1
            elif sign == "−":
                assert a - b == answer >= 0                                   # never below zero
            elif sign == "×":
                assert a * b == answer and (a in lv["tables"] or b in lv["tables"])
            else:                                                             # a number bond: a + _ (or _ + b) = total
                assert missing in ("right", "left") and a + b == answer == lv["bond"]
        if kind in ("add", "sub", "addsub"):
            assert {s[1] for s in sums} <= {"+", "−"} and all(s[4] == "result" for s in sums)


def test_maths_gets_harder_and_each_design_differs():
    assert maths.level(1)["top"] == 10 and maths.level(10)["top"] == 1000
    assert maths.level(1)["tables"] == [2, 5, 10] and max(maths.level(10)["tables"]) == 12
    assert maths.level(1)["count"] < maths.level(10)["count"]
    assert _sheet(5, "add", 1) != _sheet(5, "add", 2) and _sheet(5, "add", 3) == _sheet(5, "add", 3)


def test_a_maths_sheet_has_an_answer_page_that_fills_in_the_blanks():
    assert "maths" in HAS_ANSWER and has_answer("maths", Settings())
    s = Settings(gen="maths", seed=9, dpi=72, maths_kind="bonds")
    puzzle = RecordingCanvas()
    out = draw_page(puzzle, geometry(s), single_page(s), s)
    sums = out["sums"]
    answers = RecordingCanvas()
    draw_page(answers, geometry(s), PageSpec(kind="answers", header=True, title="Answers",
                                              items=[PageSpec(gen="maths", seed=9, c=s.complexity, label="Maths")]), s)
    written = [op[1] for op in answers.ops if op[0] == "text"]
    missing = [str(a if m == "left" else b) for a, _s, b, _ans, m in sums]
    assert all(x in written for x in missing)                                # each missing number, filled in
    puzzle_text = [op[1] for op in puzzle.ops if op[0] == "text"]
    assert not any(t in missing for t in puzzle_text)                        # the puzzle leaves them blank


def test_maths_text_fits_its_columns():
    """Every sum stays inside its column, at the hardest level (the widest sums)."""
    s = Settings(gen="maths", seed=3, dpi=72, complexity=10, maths_kind="mixed")
    c = RecordingCanvas()
    g = geometry(s)
    draw_page(c, g, single_page(s), s)
    from inkengine.page import design_box
    box = design_box(g, single_page(s), s)
    texts = [op for op in c.ops if op[0] == "text"]
    assert all(op[2] <= box.x + box.w for op in texts)


def test_tracing_rows_letters_numbers_words_and_names():
    s = Settings(gen="trace", trace_source="upper")
    rows = trace.lines_to_trace(mulberry32(1), 1, s)
    assert len(rows) == trace.rows_for(1) and all(r in trace.UPPER for r in rows)
    start = trace.UPPER.index(rows[0])
    assert rows == [trace.UPPER[(start + k) % 26] for k in range(len(rows))]   # consecutive letters
    assert trace.lines_to_trace(mulberry32(1), 1, s) != trace.lines_to_trace(mulberry32(2), 1, s)   # copies differ
    assert all(r in trace.DIGITS for r in trace.lines_to_trace(mulberry32(1), 5, replace(s, trace_source="numbers")))
    words = trace.lines_to_trace(mulberry32(1), 3, replace(s, trace_source="words", trace_text="cat, dog;sun\nMaya"))
    assert set(words) <= {"cat", "dog", "sun", "Maya"}
    named = replace(s, trace_source="name", name_text="Leo")
    assert set(trace.lines_to_trace(mulberry32(1), 3, named)) == {"Leo"}
    assert set(trace.lines_to_trace(mulberry32(1), 3, named, name="Ana")) == {"Ana"}   # a class set's name first


def test_tracing_draws_a_model_then_dotted_copies_to_trace():
    s = Settings(gen="trace", seed=4, dpi=72, complexity=3, trace_source="words", trace_text="cat, sunshine")
    c = RecordingCanvas()
    out = draw_page(c, geometry(s), single_page(s), s)
    for text in set(out["rows"]):
        models = [op for op in c.ops if op[0] == "text" and op[1] == text]
        traced = [op for op in c.ops if op[0] == "stroke_text" and op[1] == text]
        assert models and traced                                               # each in ink, and dotted to trace


def test_a_class_set_traces_each_childs_name():
    from inkapp import jobs
    from inkapp.state import State
    s = Settings(gen="trace", seed=4, dpi=36, trace_source="name", name_line=True)
    j = jobs.job(State(s), names=["Ana", "Ben"])
    for i, who in enumerate(("Ana", "Ben")):
        c = RecordingCanvas()
        j.draw(c, i)
        assert any(op[0] == "stroke_text" and op[1] == who for op in c.ops)


def test_worksheet_settings_from_a_file_are_checked():
    s = Settings.from_dict({"gen": "maths", "mathsKind": "calculus", "traceSource": "upper", "traceText": "x" * 900})
    assert s.gen == "maths" and s.maths_kind == "add" and s.trace_source == "upper" and s.trace_text == "x" * 300
    assert set(GENERATORS) >= {"maths", "trace"}


def test_a_handwriting_booklet_has_a_picture_on_its_cover():
    from inkengine import book
    s = Settings(gen="trace", booklet=True, pages=2, cover=True, dpi=36)
    pages = book.book_pages(s)
    c = RecordingCanvas()
    draw_page(c, geometry(s), pages[0], s)
    assert not any(op[0] == "stroke_text" for op in c.ops)                 # a mandala, not letters to trace


def _runs(grid):
    """Every run of two or more letters across and down: what a solver would read as words."""
    out = []
    for across in (True, False):
        for (r, c), (ch, _d) in grid.items():
            before = (r, c - 1) if across else (r - 1, c)
            if before in grid:
                continue
            word, k = "", 0
            while ((r, c + k) if across else (r + k, c)) in grid:
                word += grid[(r, c + k) if across else (r + k, c)][0]
                k += 1
            if len(word) > 1:
                out.append((word, r, c, across))
    return out


@pytest.mark.parametrize("seed", range(12))
def test_a_crossword_has_only_its_words_and_each_one_crosses(seed):
    from inkengine.patterns import crossword
    for theme in ("animals", "food", "space"):
        c = 1 + seed % 10
        grid, clues, left = crossword.make_crossword(mulberry32(seed), c, Settings(cross_theme=theme))
        placed = {(w, r, cc, a) for _n, w, _cl, r, cc, a in clues}
        assert set(_runs(grid)) == placed                                      # no stray words anywhere
        assert len(clues) == crossword.count_for(c) and left == []            # a theme always fills the sheet
        if len(clues) > 1:
            assert all(sum(1 for k in range(len(w)) if grid[(r, cc + k) if a else (r + k, cc)][1] == 3) >= 1
                       for _n, w, _cl, r, cc, a in clues)                     # each word crosses another


def test_crossword_numbers_go_in_reading_order():
    from inkengine.patterns import crossword
    _g, clues, _l = crossword.make_crossword(mulberry32(5), 8, Settings(cross_theme="animals"))
    starts = sorted({(r, c) for _n, _w, _cl, r, c, _a in clues})
    assert {(r, c): n for n, _w, _cl, r, c, _a in clues} == {rc: i + 1 for i, rc in enumerate(starts)}
    assert [e[5] for e in clues] == sorted((e[5] for e in clues), reverse=True)   # Across first, then Down


def test_your_own_crossword_words_and_clues():
    from inkengine.patterns import crossword
    assert crossword.parse_entries("cat: Says miaow; Dog:Barks\nsun\n x : too short; cat: again") == \
        [("CAT", "Says miaow"), ("DOG", "Barks"), ("SUN", "?")]
    s = Settings(cross_theme="custom", cross_words="cat: Says miaow; act: To perform; tack: A small nail; zzz: none")
    grid, clues, left = crossword.make_crossword(mulberry32(1), 1, s)
    assert {e[1] for e in clues} | set(left) == {"CAT", "ACT", "TACK", "ZZZ"}
    assert left == ["ZZZ"]                                                     # it shares no letter: left out
    assert crossword.note({"left": left}) == "Left out (no place to cross): zzz."


def test_a_crossword_draws_its_clues_and_its_answer_page_fills_the_grid():
    s = Settings(gen="crossword", seed=7, dpi=72, complexity=4)
    c = RecordingCanvas()
    out = draw_page(c, geometry(s), single_page(s), s)
    texts = [op[1] for op in c.ops if op[0] == "text"]
    assert "Across" in texts and "Down" in texts
    assert all(any(t.startswith(f"{n}. {cl}") for t in texts) for n, _w, cl, _r, _c, _a in out["clues"])
    assert not any(len(t) == 1 and t.isalpha() and t.isupper() for t in texts)   # no answers on the puzzle
    a = RecordingCanvas()
    draw_page(a, geometry(s), PageSpec(kind="answers", header=True, title="Answers",
                                        items=[PageSpec(gen="crossword", seed=7, c=4, label="Crossword")]), s)
    from inkengine.patterns import crossword
    grid = crossword.make_crossword(mulberry32(7), 4, s)[0]
    letters = [op[1] for op in a.ops if op[0] == "text" and len(op[1]) == 1 and op[1].isalpha()]
    assert sorted(letters) == sorted(ch for ch, _d in grid.values())          # every square filled in


def _value(text):
    a, op, b = re.match(r"(\d+)([+−])(\d+)$", text).groups()
    return int(a) + int(b) if op == "+" else int(a) - int(b)


def test_colour_by_maths_sums_give_each_spaces_number():
    from inkengine import cbn
    for n in range(1, 13):
        for region in range(30):
            text = cbn.sum_for(n, 77, region)
            assert _value(text) == n and cbn.sum_for(n, 77, region) == text   # the same sum every time
            assert "−" not in text or int(text.split("−")[1]) >= 1


def test_a_colour_by_maths_page_writes_sums_and_says_to_work_them_out():
    from inkengine import cbn
    s = Settings(gen="mandala", seed=12, dpi=72, cbn=True, cbn_maths=True, cbn_colours=5)
    c = RecordingCanvas()
    r = draw_page(c, geometry(s), single_page(s), s)
    texts = [op[1] for op in c.ops if op[0] == "text"]
    sums = [t for t in texts if re.match(r"\d+[+−]\d+$", t)]
    assert len(sums) == len(r["spots"])                                        # a sum in every numbered space
    assert sorted(_value(t) for t in sums) == sorted(q[0] for q in r["spots"])
    assert "Work out each sum, then colour:" in texts
    plain = RecordingCanvas()
    draw_page(plain, geometry(s), single_page(s), replace(s, cbn_maths=False))
    assert "Colour key" in [op[1] for op in plain.ops if op[0] == "text"]


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("5.0.0", remember=False)
    w.show()
    yield w
    w.close()
    w.deleteLater()


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_the_sidebar_offers_each_worksheets_options(win):
    sb = win.sidebar
    assert [v for v, _t in __import__("inkapp.sidebar", fromlist=["x"]).GEN_OPTIONS][-22:-5] == ["maths", "trace", "crossword", "clock",
                                                                                            "scramble", "spelltest", "fractions", "symmetry",
                                                                                            "ruled", "reward", "reading", "bingo", "early",
                                                                                            "logic", "cryptogram", "ladder", "calendar"]
    _set(win, gen="maths")
    assert sb.shown(sb.maths_opts) and not sb.shown(sb.trace_opts) and not sb.shown(sb.cross_opts)
    sb.maths_kind.set_value("times")
    assert win.state.settings.maths_kind == "times"
    _set(win, gen="trace")
    assert sb.shown(sb.trace_opts) and not sb.shown(sb.trace_text_row)
    _set(win, trace_source="words")
    assert sb.shown(sb.trace_text_row)
    _set(win, trace_source="name")
    assert sb.shown(sb.trace_hint) and "Print → Copies and names" in sb.trace_hint.text()
    _set(win, gen="crossword")
    assert sb.shown(sb.cross_opts) and not sb.shown(sb.cross_words_row)
    _set(win, cross_theme="custom")
    assert sb.shown(sb.cross_words_row) and sb.shown(sb.cross_words_hint)
    _set(win, gen="mandala", cbn=True)
    maths_switch = next(w for w in sb.cbn_opts.findChildren(type(sb.copies_vary)) if "Colour by maths" in w.text.text())
    assert sb.shown(maths_switch)
    maths_switch.setChecked(True)
    assert win.state.settings.cbn_maths



def test_long_handwriting_stays_big_enough_to_trace():
    """A long name or word isn't shrunk to a few millimetres: it gets rows of its own, in ink then dotted, and
    a full name is traced word by word."""
    s = Settings(gen="trace", seed=3, dpi=72, complexity=4, trace_source="name",
                 name_text="Maximilian-Alexander Featherstonehaugh")
    c = RecordingCanvas()
    out = draw_page(c, geometry(s), single_page(s), s)
    assert set(out["rows"]) == {"Maximilian-Alexander", "Featherstonehaugh"}
    sizes = {op[6] for op in c.ops if op[0] in ("text", "stroke_text") and op[1] in out["rows"]}
    assert min(sizes) >= 72 * 0.3                                              # never below about 8 mm
    for word in set(out["rows"]):
        assert any(op[0] == "text" and op[1] == word for op in c.ops)
        assert any(op[0] == "stroke_text" and op[1] == word for op in c.ops)


def test_crossword_letters_lose_their_accents_not_themselves():
    from inkengine.patterns import crossword
    assert [w for w, _c in crossword.parse_entries("café: a shop; naïve: x; über: y; École: z")] == \
        ["CAFE", "NAIVE", "UBER", "ECOLE"]


def test_your_own_crossword_words_cross_words_placed_after_them():
    from inkengine.patterns import crossword
    s = Settings(cross_theme="custom", cross_words="elephant: big; buzzy: like a bee; zen: calm")
    for seed in range(6):
        _g, clues, left = crossword.make_crossword(mulberry32(seed), 1, s)
        assert sorted(e[1] for e in clues) == ["BUZZY", "ELEPHANT", "ZEN"] and left == []


def test_own_crossword_lists_are_capped_and_an_unusable_one_says_so():
    from inkengine.patterns import crossword
    many = "; ".join(f"{w}: clue" for w in ["cat", "act", "tac", "tic", "tock", "clock", "lock", "rock", "sock",
                                             "dock", "duck", "luck", "tuck", "muck", "pick", "kick", "lick", "tick",
                                             "sick", "nick", "rick", "wick", "chick", "brick", "trick", "stick",
                                             "slick", "flick", "click", "thick", "quick", "prick"])
    assert crossword.own_note(Settings(cross_theme="custom", cross_words=many)) == "Only the first 30 of your words are used."
    entries, own = crossword.entries_for(mulberry32(1), Settings(cross_theme="custom", cross_words=many))
    assert own and len(entries) == 30
    assert "can be used" in crossword.own_note(Settings(cross_theme="custom", cross_words="1234; !!"))


def test_long_crossword_clues_wrap_instead_of_squashing():
    s = Settings(gen="crossword", seed=1, dpi=72, cross_theme="custom",
                 cross_words="cat: " + "a very long clue about a small animal that likes milk and sleeping " * 2
                 + "; act: to perform")
    c = RecordingCanvas()
    draw_page(c, geometry(s), single_page(s), s)
    from inkengine.page import design_box
    box = design_box(geometry(s), single_page(s), s)
    lines = [op for op in c.ops if op[0] == "text" and ("clue" in op[1] or "sleeping" in op[1] or "milk" in op[1])]
    assert len(lines) >= 3                                                     # wrapped onto several lines
    ctx = RecordingCanvas()
    for op in lines:
        ctx.set_font(op[6], op[5])
        assert ctx.measure_text(op[1]) <= box.w / 2 + 1                         # each one fits its column


def test_colour_by_maths_small_spaces_get_short_sums():
    from inkengine import cbn
    for n in range(2, 13):
        assert "+" in cbn.sum_for(n, 5, 3, small=True)
    assert cbn.sum_for(1, 5, 3, small=True).endswith(tuple("123456789"))       # 1 can only be taken away


def test_harder_maths_has_no_tiny_numbers_and_the_blank_fits_the_answer():
    sums = _sheet(10, "addsub", 4)
    assert all(min(a, b) >= 50 for a, sign, b, _ans, _m in sums)              # sums to 1000: no "5 − 3"
    assert not any(1 in (a, b) for a, sign, b, _ans, _m in _sheet(3, "addsub", 4))   # "+ 1" only within 10
