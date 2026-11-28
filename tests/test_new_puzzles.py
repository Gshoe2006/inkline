"""Logic puzzles, cryptograms, word ladders and calendars: each made the same way from a seed, right, in every
language, and fitting the page on Letter and A4, upright and sideways."""

import calendar
import datetime
import re
from dataclasses import replace

import pytest
from PySide6.QtWidgets import QApplication

from inkengine import i18n
from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import PageSpec, Settings, answer_page, design_box, draw_page, geometry, single_page
from inkengine.patterns import GENERATORS, HAS_ANSWER, NAMES, cryptogram, ladder, logic, planner
from inkengine.rng import mulberry32

NEW = ("logic", "cryptogram", "ladder", "calendar")
LANGS = ["en", "es", "fr", "pt", "de", "it", "nl"]


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])
    yield
    i18n.set_language("en")


def _texts(ctx):
    return [op[1] for op in ctx.ops if op[0] == "text"]


def test_they_are_patterns():
    for gen in NEW:
        assert gen in GENERATORS and gen in NAMES
    assert {"logic", "cryptogram", "ladder"} <= HAS_ANSWER and "calendar" not in HAS_ANSWER


# --- logic puzzles -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("c,n", [(1, 3), (3, 3), (4, 4), (7, 4), (8, 5), (10, 5)])
def test_a_logic_puzzle_has_one_answer_and_the_solver_finds_it(c, n):
    for seed in range(8):
        p = logic.make_puzzle(mulberry32(seed), c)
        assert len(p["items"]) == 3 and all(len(items) == n for items in p["items"])
        assert logic.count_answers(n, p["clues"]) == 1                 # tried every answer: only one fits
        g = logic.deduce(n, p["clues"])
        assert g is not None and g.solved() and g.answer() == p["answer"]
        for clue in p["clues"]:                                        # and every clue is true of it
            assert logic.deduce(n, [clue]) is not None
            yes, x, i, y, j = clue
            owner = {0: list(range(n)), 1: [a for _c, a, _b in p["answer"]], 2: [b for _c, _a, b in p["answer"]]}
            assert (owner[x].index(i) == owner[y].index(j)) == yes


def test_no_clue_can_be_left_out():
    for seed in range(5):
        p = logic.make_puzzle(mulberry32(seed), 6)
        n = len(p["items"][0])
        for k in range(len(p["clues"])):
            rest = p["clues"][:k] + p["clues"][k + 1:]
            g = logic.deduce(n, rest)
            assert g is None or not g.solved()


def test_the_solver_says_when_clues_disagree():
    assert logic.deduce(3, [(True, 0, 0, 1, 0), (False, 0, 0, 1, 0)]) is None
    assert logic.deduce(3, [(True, 0, 0, 1, 0), (True, 0, 1, 1, 0)]) is None


def test_a_logic_puzzle_is_the_same_for_the_same_seed():
    a = logic.make_puzzle(mulberry32(11), 8)
    assert a == logic.make_puzzle(mulberry32(11), 8) and a != logic.make_puzzle(mulberry32(12), 8)


@pytest.mark.parametrize("lang", LANGS)
def test_logic_clues_are_sentences_in_each_language(lang):
    i18n.set_language(lang)
    words = logic.WORDS[lang]
    assert set(words) == {"child", *logic.THINGS}
    assert len(words["child"].split()) >= 5 and all(len(words[k]) >= 5 for k in logic.THINGS)
    for seed in range(4):
        p = logic.make_puzzle(mulberry32(seed), 9)
        for clue in p["clues"]:
            text = logic.sentence(p, clue)
            assert text[0].isupper() and text.endswith(".") and "{" not in text
            assert p["items"][clue[3]][clue[4]][1] in text
    ctx = RecordingCanvas()
    out = logic.draw(ctx, Box(0, 0, 2400, 3000), mulberry32(3), 5, Settings(), dpi=300)
    assert i18n.tr(logic.INSTRUCTIONS).split()[0] in " ".join(_texts(ctx)) and out["clues"] == len(out["sentences"])


def test_the_logic_answer_ticks_the_grid():
    ctx = RecordingCanvas()
    out = logic.draw(ctx, Box(0, 0, 1200, 1500), mulberry32(5), 5, Settings(), dpi=150, solve=True)
    p = logic.make_puzzle(mulberry32(5), 5)
    rows = [", ".join([p["items"][0][i][0], p["items"][1][a][0], p["items"][2][b][0]]) for i, a, b in p["answer"]]
    assert set(rows) <= set(_texts(ctx)) and out["size"] == 4


# --- cryptograms ---------------------------------------------------------------------------------------------------

def test_a_cryptogram_gives_each_letter_its_own_code():
    for seed in range(10):
        p = cryptogram.make(mulberry32(seed), 5, Settings())
        codes = list(p["code"].values())
        assert sorted(codes) == list(range(26)) and p["text"] in cryptogram.SAYINGS["en"]
        assert 1 <= len(p["given"]) <= 4
        decoded = "".join(letter or shown for letter, shown in p["tokens"])
        assert decoded == p["text"].upper()
    assert cryptogram.make(mulberry32(4), 5, Settings()) == cryptogram.make(mulberry32(4), 5, Settings())


def test_harder_cryptograms_are_longer_and_give_less_away():
    def letters(c):
        return sum(sum(1 for t, _s in cryptogram.make(mulberry32(s), c, Settings())["tokens"] if t) for s in range(12))

    def given(c):
        return sum(len(cryptogram.make(mulberry32(s), c, Settings())["given"]) for s in range(12))
    assert letters(1) < letters(5) < letters(9)
    assert given(1) > given(9)


def test_accents_become_plain_letters_and_spanish_keeps_n_tilde():
    i18n.set_language("fr")
    assert cryptogram.letters_of("é") == "E" and cryptogram.letters_of("œ") == "OE" and cryptogram.letters_of("'") == ""
    i18n.set_language("de")
    assert cryptogram.letters_of("ß") == "SS" and cryptogram.letters_of("ü") == "U"
    i18n.set_language("es")
    assert cryptogram.letters_of("ñ") == "Ñ" and cryptogram.letters_of("á") == "A"
    p = cryptogram.make(mulberry32(1), 5, Settings())
    assert len(p["code"]) == 27                                        # Spanish: 27 letters, 27 codes


@pytest.mark.parametrize("lang", LANGS)
def test_cryptogram_sayings_in_each_language(lang):
    i18n.set_language(lang)
    assert len(cryptogram.SAYINGS[lang]) >= 12
    for saying in cryptogram.SAYINGS[lang]:
        assert all(t in i18n.alphabet() for t, _s in cryptogram.tokens(saying) if t)


def test_your_own_text_goes_in_code():
    s = Settings(crypto_source="custom", crypto_text="Hello, Maya!")
    p = cryptogram.make(mulberry32(2), 5, s)
    assert p["text"] == "Hello, Maya!" and cryptogram.note(s) == ""
    empty = Settings(crypto_source="custom", crypto_text="123 !!")
    assert cryptogram.make(mulberry32(2), 5, empty) is None and cryptogram.note(empty)
    assert cryptogram.draw(RecordingCanvas(), Box(0, 0, 900, 1200), mulberry32(2), 5, empty, dpi=100) is None


def test_the_cryptogram_answer_fills_every_box():
    s = Settings(crypto_source="custom", crypto_text="Zebra crossing")
    puzzle, key = RecordingCanvas(), RecordingCanvas()
    cryptogram.draw(puzzle, Box(0, 0, 1200, 1500), mulberry32(3), 9, s, dpi=150)
    cryptogram.draw(key, Box(0, 0, 1200, 1500), mulberry32(3), 9, s, dpi=150, solve=True)
    letters = [t for t in _texts(key) if len(t) == 1 and t.isalpha()]
    assert "".join(letters).startswith("ZEBRACROSSING")
    assert len([t for t in _texts(puzzle) if len(t) == 1 and t.isalpha()]) < len(letters)


def test_symbols_are_drawn_not_typed():
    s = Settings(crypto_code="symbols")
    ctx = RecordingCanvas()
    cryptogram.draw(ctx, Box(0, 0, 1200, 1500), mulberry32(3), 5, s, dpi=150)
    assert not any(re.fullmatch(r"\d+", t) for t in _texts(ctx))
    for k in range(27):                                               # every shape draws
        c = RecordingCanvas()
        cryptogram.symbol(c, k, 50, 50, 10, 1)
        assert any(op[0] in ("stroke", "fill") for op in c.ops)


# --- word ladders --------------------------------------------------------------------------------------------------

def _one_apart(a, b):
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


@pytest.mark.parametrize("lang", LANGS)
def test_ladders_change_one_letter_at_a_time_through_real_words(lang):
    i18n.set_language(lang)
    for c in range(1, 11):
        letters, steps, count = ladder.plan(c)
        ladders, used = ladder.make_ladders(mulberry32(c * 31), c)
        assert len(ladders) == count and used == lang                  # each language has its own ladders
        for path in ladders:
            words = set(ladder.word_list(used, len(path[0])))
            assert len(path) == steps + 1 and all(w in words for w in path)
            assert all(_one_apart(a, b) for a, b in zip(path, path[1:]))
            # no shorter way: the ladder takes the steps it says
            assert ladder.shortest(ladder.neighbours(used, len(path[0])), path[0])[path[-1]][0] == steps
        assert len({p[0] for p in ladders} | {p[-1] for p in ladders}) == 2 * count


def test_a_language_without_ladders_that_long_uses_english_and_says_so(monkeypatch):
    i18n.set_language("it")
    monkeypatch.setitem(ladder.WORDS, "it", "casa cosa")
    ladder._graphs.clear()
    try:
        ladders, used = ladder.make_ladders(mulberry32(1), 5)
        assert used == "en" and ladders
        assert ladder.note(Settings(complexity=5))
    finally:
        ladder._graphs.clear()
    i18n.set_language("en")
    assert ladder.note(Settings()) == ""


def test_the_ladder_answer_fills_the_rungs():
    puzzle, key = RecordingCanvas(), RecordingCanvas()
    out = ladder.draw(puzzle, Box(0, 0, 1200, 1500), mulberry32(4), 5, Settings(ladder_kind="marked"), dpi=150)
    ladder.draw(key, Box(0, 0, 1200, 1500), mulberry32(4), 5, Settings(), dpi=150, solve=True)
    shown = "".join(t for t in _texts(key) if len(t) == 1)
    assert shown == "".join("".join(path) for path in out["ladders"])
    ends = sum(len(path[0]) * 2 for path in out["ladders"])
    assert len([t for t in _texts(puzzle) if len(t) == 1]) == ends      # only the top and bottom words are given
    assert any(op[0] == "fill_rect" and op[5] == "#ddd" for op in puzzle.ops)   # the letter to change, shaded


# --- calendars -----------------------------------------------------------------------------------------------------

def test_next_month_and_the_next_one():
    assert planner.month_shown(Settings(), datetime.date(2026, 11, 26)) == (2026, 12)
    assert planner.month_shown(Settings(), datetime.date(2026, 12, 3)) == (2027, 1)
    assert planner.month_shown(Settings(cal_month=3), datetime.date(2026, 11, 26)) == (2027, 3)
    assert planner.month_shown(Settings(cal_month=11), datetime.date(2026, 11, 26)) == (2026, 11)
    assert planner.month_shown(Settings(cal_month=2, cal_year=2028), datetime.date(2026, 11, 26)) == (2028, 2)


@pytest.mark.parametrize("year,month,first,start_day,days,rows", [
    (2028, 2, 0, 1, 29, 5),     # a leap February, starting on a Tuesday
    (2027, 2, 0, 0, 28, 4),     # February 2027 starts on a Monday: exactly four weeks
    (2027, 2, 6, 1, 28, 5),     # ... and five with Sunday first
    (2026, 3, 0, 6, 31, 6),     # March 2026 starts on a Sunday: six rows with Monday first
    (2026, 3, 6, 0, 31, 5),
    (2024, 2, 6, 4, 29, 5),     # February 2024: Thursday, with Sunday first
])
def test_the_month_grid_has_the_right_dates(year, month, first, start_day, days, rows):
    weeks = planner.weeks(year, month, first)
    flat = [d for w in weeks for d in w]
    assert len(weeks) == rows and all(len(w) == 7 for w in weeks)
    assert flat.index(1) == start_day and max(flat) == days == calendar.monthrange(year, month)[1]
    assert [d for d in flat if d] == list(range(1, days + 1))
    # each day sits under its weekday's column
    for d in (1, days):
        col = flat.index(d) % 7
        assert (first + col) % 7 == datetime.date(year, month, d).weekday()


def test_the_week_starts_as_the_language_does():
    assert planner.first_weekday(Settings(paper="letter")) == 6           # US English: Sunday
    assert planner.first_weekday(Settings(paper="a4")) == 0               # elsewhere: Monday
    assert planner.first_weekday(Settings(cal_start="mon")) == 0
    assert planner.first_weekday(Settings(paper="a4", cal_start="sun")) == 6
    i18n.set_language("de")
    assert planner.first_weekday(Settings(paper="letter")) == 0
    i18n.set_language("pt")
    assert planner.first_weekday(Settings(paper="a4")) == 6


@pytest.mark.parametrize("lang", ["en", "fr", "de"])
def test_the_calendar_page_shows_the_month_in_the_language(lang):
    i18n.set_language(lang)
    s = Settings(gen="calendar", cal_month=2, cal_year=2028, cal_start="mon", dpi=72)
    ctx = RecordingCanvas()
    out = draw_page(ctx, geometry(s), single_page(s), s)
    texts = _texts(ctx)
    assert i18n.tr("{month} {year}").format(month=i18n.tr("February"), year=2028) in texts
    assert [str(d) for d in range(1, 30)] == [t for t in texts if t.isdigit() and len(t) <= 2]
    assert out["weeks"] == planner.weeks(2028, 2, 0) and out["first"] == 0
    week = Settings(gen="calendar", cal_kind="week", cal_start="sun", dpi=72, cal_art="none")
    ctx = RecordingCanvas()
    draw_page(ctx, geometry(week), single_page(week), week)
    days = [t for t in _texts(ctx) if t in [i18n.tr(d) for d in planner.WEEKDAYS]]
    assert days[0] == i18n.tr("Sunday") and len(days) == 7


def test_the_calendar_picture_is_drawn_by_the_pattern_chosen():
    plain, art = RecordingCanvas(), RecordingCanvas()
    planner.draw(plain, Box(0, 0, 800, 1000), mulberry32(1), 5, Settings(cal_art="none"), dpi=100)
    planner.draw(art, Box(0, 0, 800, 1000), mulberry32(1), 5, Settings(cal_art="truchet"), dpi=100)
    assert len(art.ops) > len(plain.ops) + 50


# --- every page fits ------------------------------------------------------------------------------------------------

def _inside(ctx, box, pad):
    """Every point drawn (outside turned text) is within the box, give or take pad."""
    turned = []
    for op in ctx.ops:
        if op[0] == "save":
            turned.append(False)
        elif op[0] == "restore":
            turned.pop()
        elif op[0] in ("translate", "transform"):
            turned[-1] = True
        elif not any(turned) and op[0] in ("M", "L", "text", "fill_rect", "stroke_rect"):
            x, y = op[1:3] if op[0] in ("M", "L", "fill_rect", "stroke_rect") else op[2:4]
            if not (box.x - pad <= x <= box.x + box.w + pad and box.y - pad <= y <= box.y + box.h + pad):
                return op
            if op[0] in ("fill_rect", "stroke_rect"):
                if x + op[3] > box.x + box.w + pad or y + op[4] > box.y + box.h + pad:
                    return op
    return None


@pytest.mark.parametrize("gen,extra", [("logic", {}), ("cryptogram", {}), ("cryptogram", {"crypto_code": "symbols"}),
                                       ("ladder", {"ladder_kind": "marked"}), ("calendar", {}),
                                       ("calendar", {"cal_kind": "week", "cal_art": "flow"})])
@pytest.mark.parametrize("paper,orient", [("letter", "portrait"), ("letter", "landscape"), ("a4", "portrait"),
                                          ("a4", "landscape")])
def test_each_page_fits_letter_and_a4_both_ways(gen, extra, paper, orient):
    for c in (1, 5, 10):
        s = Settings(gen=gen, complexity=c, seed=c * 5, paper=paper, orient=orient, dpi=72, title="T", name_line=True,
                     **extra)
        g = geometry(s)
        spec = single_page(s)
        box = design_box(g, spec, s)
        ctx = RecordingCanvas()
        GENERATORS[gen](ctx, box, mulberry32(spec.seed), c, s, lw=1, seed=spec.seed, dpi=g.dpi)
        assert _inside(ctx, box, 2) is None
        if gen in HAS_ANSWER:
            key = answer_page([PageSpec(gen=gen, seed=spec.seed, c=c, label="x")])
            ctx = RecordingCanvas()
            draw_page(ctx, g, key, s)
            ctx.ops = ctx.ops[1:]   # (after the white paper)
            assert _inside(ctx, g.box, 2) is None


@pytest.mark.parametrize("lang", LANGS)
def test_each_page_draws_in_each_language(lang):
    i18n.set_language(lang)
    i18n.MISSING.clear()
    for gen in NEW:
        s = Settings(gen=gen, dpi=36)
        draw_page(RecordingCanvas(), geometry(s), single_page(s), s)
        if gen in HAS_ANSWER:
            draw_page(RecordingCanvas(), geometry(s), answer_page([PageSpec(gen=gen, seed=s.seed, c=5, label="x")]), s)
    assert sorted(m for m in i18n.MISSING if re.search(r"[A-Za-z]{2}", m)) == []


# --- the sidebar, the gallery and presets ------------------------------------------------------------------------------

@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("6.1.0", remember=False)
    w.show()
    yield w


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_the_sidebar_shows_each_ones_options(win):
    sb = win.sidebar
    _set(win, gen="logic")                              # its one hint is Complexity's, under the slider
    assert sb.complexity_hint.text().startswith("Complexity sets the grid: 3, 4 or 5") and not sb.shown(sb.crypto_opts)
    _set(win, gen="cryptogram")
    assert sb.shown(sb.crypto_opts) and not sb.shown(sb.crypto_text_row) and not sb.shown(sb.crypto_note)
    sb.crypto_code.set_value("symbols")
    assert win.state.settings.crypto_code == "symbols"
    _set(win, crypto_source="custom")
    assert sb.shown(sb.crypto_text_row) and sb.shown(sb.crypto_note)    # nothing typed yet
    _set(win, crypto_text="Hello")
    assert not sb.shown(sb.crypto_note)
    _set(win, gen="ladder")
    assert sb.shown(sb.ladder_opts) and not sb.shown(sb.ladder_note)
    _set(win, gen="calendar")
    assert sb.shown(sb.cal_opts) and sb.shown(sb.cal_date_row)
    _set(win, cal_kind="week")
    assert not sb.shown(sb.cal_date_row)
    sb.cal_month.set_value(2)
    assert win.state.settings.cal_month == 2
    _set(win, mode="convert", style="dots")
    assert sb.shown(sb.pdots_opts) and not sb.shown(sb.pnono_opts)


def test_the_gallery_finds_them_by_kind():
    from inkapp import layout, sidebar
    descriptions = dict(sidebar.GEN_OPTIONS)
    found = {q: [g for g in NEW if layout.matches(g, q, NAMES, descriptions)]
             for q in ("secret", "Einstein", "planner", "one letter")}
    assert found == {"secret": ["cryptogram"], "Einstein": ["logic"], "planner": ["calendar"], "one letter": ["ladder"]}
    assert all(any(g in gens for _group, gens in layout.GROUPS) for g in NEW)
    i18n.set_language("es")
    assert layout.matches("cryptogram", "código", NAMES, descriptions)
    assert layout.matches("calendar", "agenda", NAMES, descriptions)


def test_presets_and_ages():
    from inkapp.state import BUILTIN_PRESETS, State
    from inkengine import ages
    for gen in NEW:
        assert set(ages.COMPLEXITY[gen]) == {"4-6", "7-9", "10+"}
    st = State()
    st.apply_preset(BUILTIN_PRESETS["Calendar for next month"])
    s = st.settings
    assert (s.gen, s.cal_month, s.cal_kind) == ("calendar", 0, "month")
    st.apply_preset(BUILTIN_PRESETS["Photo dot-to-dot"])
    s = st.settings
    assert (s.mode, s.style, s.pdots_n) == ("convert", "dots", 60)
    st.apply_preset(BUILTIN_PRESETS["Logic puzzle booklet with answers"])
    s = st.settings
    assert (s.gen, s.booklet, s.key) == ("logic", True, True)


# --- after an independent check --------------------------------------------------------------------------------------

def _ink_in_picture(s):
    """How much of the middle of the calendar's picture is inked, printed."""
    import numpy as np
    from PySide6.QtGui import QImage
    from inkengine import output
    img = output.render_image(s, single_page(s)).convertToFormat(QImage.Format.Format_Grayscale8)
    a = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).reshape(img.height(), img.bytesPerLine())[:, :img.width()]
    b = draw_page(RecordingCanvas(), geometry(s), single_page(s), s)["art_box"]
    side = min(b.w, b.h)
    x, y = int(b.x + (b.w - side) / 2), int(b.y + (b.h - side) / 2)
    return (a[y:y + int(side), x:x + int(side)] < 128).mean()


@pytest.mark.parametrize("art", ["mandala", "truchet", "flow", "contour"])
def test_the_calendars_picture_stays_open_enough_to_colour(art):
    for weight in (3, 4):   # Age 10+'s line weight, and the usual one
        assert _ink_in_picture(Settings(gen="calendar", cal_art=art, complexity=10, weight=weight, dpi=100)) < 0.3
    assert planner.art_complexity(10) <= 3 and planner.art_complexity(1) == 1


def test_a_calendar_booklet_is_a_month_a_page():
    from inkengine import book
    s = Settings(gen="calendar", booklet=True, pages=12, cal_month=11, cal_year=2027, ramp=False, key=True)
    pages = book.book_pages(s)
    designs = [p for p in pages if p.kind == "design"]
    months = [planner.month_shown(replace(s, **d.opts)) for d in designs]
    assert months == [(2027, 11), (2027, 12)] + [(2028, m) for m in range(1, 11)]
    assert pages[0].kind == "cover" and pages[0].title == "November 2027 – October 2028"
    assert not any(p.kind == "answers" for p in pages)
    ctx = RecordingCanvas()
    out = draw_page(ctx, geometry(s), designs[2], s)
    assert (out["year"], out["month"]) == (2028, 1) and "January 2028" in _texts(ctx)
    ctx = RecordingCanvas()
    draw_page(ctx, geometry(s), pages[0], s)   # the cover's picture is a mandala, not a calendar
    assert not any(t.isdigit() for t in _texts(ctx))
    week = replace(s, cal_kind="week")
    assert all(not p.opts for p in book.book_pages(week) if p.kind == "design")
    assert book.book_pages(replace(s, gen="maze"))[1].opts == {}


@pytest.mark.parametrize("paper,orient", [("letter", "portrait"), ("a4", "portrait"), ("letter", "landscape"),
                                          ("a4", "landscape")])
def test_the_weekly_planner_fills_each_day_with_lines(paper, orient):
    for art in ("mandala", "none"):
        s = Settings(gen="calendar", cal_kind="week", cal_art=art, paper=paper, orient=orient, dpi=100)
        out = draw_page(RecordingCanvas(), geometry(s), single_page(s), s)
        assert len(out["lines"]) == 7 and min(out["lines"]) >= (3 if orient == "portrait" else 8)


def test_the_year_list_starts_this_year_and_keeps_a_saved_one():
    now = datetime.date(2026, 11, 26)
    years = [y for y, _t in planner.year_choices(now)]
    assert years == [0] + list(range(2026, 2037))
    assert 2019 in [y for y, _t in planner.year_choices(now, keep=2019)]
    assert Settings.from_dict({"calYear": 2019}).cal_year == 2019 and Settings.from_dict({"calYear": 5000}).cal_year == 2100
    assert planner.month_shown(Settings(cal_month=3, cal_year=2019), now) == (2019, 3)
    assert planner.month_shown(Settings(cal_month=3, cal_year=5), now) == (2027, 3)   # not a year: the next March


def test_a_saved_year_shows_in_the_sidebar(win):
    _set(win, gen="calendar", cal_month=3, cal_year=2019)
    assert win.sidebar.cal_year.value() == 2019 and win.state.settings.cal_year == 2019


def test_cryptogram_punctuation_is_narrow_and_the_key_heading_is_centred():
    s = Settings(crypto_source="custom", crypto_text="Hi, Grandma!")
    ctx = RecordingCanvas()
    out = cryptogram.draw(ctx, Box(0, 0, 1000, 1300), mulberry32(1), 5, s, dpi=100)
    texts = {op[1]: op for op in ctx.ops if op[0] == "text"}
    rects = [op for op in ctx.ops if op[0] == "stroke_rect"]
    cell = out["cell"] * 100
    last_box = max(r[1] + r[3] for r in rects if abs(r[2] - rects[0][2]) < 1 and r[3] < cell)   # the line's last box
    assert texts["!"][2] - last_box < cell * 0.4     # the ! right after the last letter, not a whole slot on
    key = texts[i18n.tr("Key")]
    assert abs(key[2] - 500) < 1


def test_the_cryptogram_hint_suits_your_own_text(win):
    sb = win.sidebar
    _set(win, gen="cryptogram")
    assert sb.shown(sb.complexity_hint) and "how long the saying is" in sb.complexity_hint.text()
    _set(win, crypto_source="custom")
    assert sb.complexity_hint.text() == "Complexity sets how few letters the key gives away."


def test_three_ladders_in_two_rows_centre_the_last():
    ctx = RecordingCanvas()
    out = ladder.draw(ctx, Box(0, 0, 1000, 1300), mulberry32(2), 9, Settings(), dpi=100)
    assert len(out["ladders"]) == 3
    rects = [op for op in ctx.ops if op[0] == "stroke_rect"]
    per = len(rects) // 3
    lefts = [min(r[1] for r in rects[k * per:(k + 1) * per]) for k in range(3)]
    rights = [max(r[1] + r[3] for r in rects[k * per:(k + 1) * per]) for k in range(3)]
    assert abs((lefts[2] + rights[2]) / 2 - 500) < 2      # the third, alone on its row, in the middle


def test_the_youngest_logic_puzzle_uses_the_page():
    ctx = RecordingCanvas()
    box = Box(0, 0, 750, 1000)
    logic.draw(ctx, box, mulberry32(1), 1, Settings(), dpi=100)
    ys = [op[2] for op in ctx.ops if op[0] in ("M", "L", "text")] + [op[2] + op[4] for op in ctx.ops if op[0] == "stroke_rect"]
    assert max(ys) > box.h * 0.7   # (it was 0.6: the grid now takes what the few clues leave)
