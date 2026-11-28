"""Look-say-cover-write-check and the spelling week, missing letters, times-table speed tests, draw what you read,
coordinate grids (plot the points, Battleships) and memory cards: each made the same way from a seed, right, in every
language, and fitting the page on Letter and A4, upright and sideways."""

import re
import subprocess
import sys
from dataclasses import replace

import pytest
from PySide6.QtWidgets import QApplication

from inkengine import i18n, pack, pictures
from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import (PageSpec, Settings, answer_page, backs_page, design_box, draw_page, geometry, has_answer,
                            single_page)
from inkengine.patterns import GENERATORS, HAS_ANSWER, NAMES, coords, drawread, lscwc, memory, scramble, speed
from inkengine.rng import mulberry32

NEW = ("lscwc", "speed", "drawread", "coords", "memory")
LANGS = ["en", "es", "fr", "pt", "de", "it", "nl"]
ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])
    yield
    i18n.set_language("en")


class Measuring(RecordingCanvas):
    """A recording that also notes where each line of text starts and ends, by its alignment."""

    def fill_text(self, text, x, y, max_width=None):
        super().fill_text(text, x, y, max_width)
        w = self.measure_text(text)
        if max_width is not None:
            w = min(w, max_width)
        left = {"center": x - w / 2, "right": x - w, "end": x - w}.get(self.st.text_align, x)
        self.ops.append(("extent", text, left, left + w, y))


def _texts(ctx):
    return [op[1] for op in ctx.ops if op[0] == "text"]


def _draw(gen, c=5, seed=1, solve=False, box=Box(0, 0, 2400, 3000), **kw):
    ctx = Measuring()
    out = GENERATORS[gen](ctx, box, mulberry32(seed), c, Settings(gen=gen, **kw), lw=4, seed=seed, dpi=300, solve=solve)
    return ctx, out


def _outside(ctx, box, pad):
    """The first thing drawn outside the box (give or take pad), text by its whole width, or None."""
    for op in ctx.ops:
        if op[0] in ("M", "L"):
            x, y = op[1:3]
            if not (box.x - pad <= x <= box.x + box.w + pad and box.y - pad <= y <= box.y + box.h + pad):
                return op
        elif op[0] in ("fill_rect", "stroke_rect"):
            x, y, w, h = op[1:5]
            if x < box.x - pad or y < box.y - pad or x + w > box.x + box.w + pad or y + h > box.y + box.h + pad:
                return op
        elif op[0] == "A":
            cx, cy, r = op[1:4]
            if cx - r < box.x - pad or cx + r > box.x + box.w + pad or cy - r < box.y - pad or cy + r > box.y + box.h + pad:
                return op
        elif op[0] == "extent":
            _t, left, right, y = op[1:5]
            if left < box.x - pad or right > box.x + box.w + pad or not box.y - pad <= y <= box.y + box.h + pad:
                return op
    return None


def test_they_are_patterns():
    for gen in NEW:
        assert gen in GENERATORS and gen in NAMES
    assert {"speed", "coords"} <= HAS_ANSWER and not {"lscwc", "drawread", "memory"} & HAS_ANSWER
    assert has_answer("coords", Settings(coord_kind="plot")) and not has_answer("coords", Settings(coord_kind="battle"))


VARIANTS = [("lscwc", {}), ("lscwc", {"ws_theme": "custom", "ws_words": "because friend said which Wednesday " * 4}),
            ("scramble", {"scramble_kind": "missing"}), ("speed", {}), ("speed", {"speed_count": 100, "speed_chart": True}),
            ("speed", {"speed_count": 25, "speed_op": "both", "speed_order": "order"}), ("drawread", {}),
            ("drawread", {"draw_source": "custom", "draw_text": "A red car; A dog in the rain; " * 3}),
            ("coords", {}), ("coords", {"coord_kind": "battle"}), ("memory", {}), ("memory", {"memory_kind": "words"}),
            ("memory", {"memory_kind": "dots"}), ("memory", {"memory_kind": "custom", "memory_words": "cat: chat; the red house: la maison rouge"}),
            ("memory", {"memory_backs": True})]


@pytest.mark.parametrize("gen,extra", VARIANTS)
def test_the_same_seed_draws_the_same_page(gen, extra):
    for c in (1, 5, 10):
        a, _ = _draw(gen, c, 7, **extra)
        b, _ = _draw(gen, c, 7, **extra)
        assert a.ops == b.ops
    pages = {repr(_draw(gen, 6, seed, **extra)[0].ops) for seed in range(6)}
    fixed = (gen == "coords" and extra) or (gen == "speed" and extra.get("speed_order") == "order") or \
            (gen == "drawread" and extra) or (gen == "lscwc" and extra)
    assert len(pages) == 1 if fixed else len(pages) > 1


@pytest.mark.parametrize("gen,extra", VARIANTS)
@pytest.mark.parametrize("paper,orient", [("letter", "portrait"), ("letter", "landscape"), ("a4", "portrait"),
                                          ("a4", "landscape")])
def test_each_page_fits_letter_and_a4_both_ways(gen, extra, paper, orient):
    for c in (1, 3, 5, 8, 10):
        s = Settings(gen=gen, complexity=c, seed=c * 5, paper=paper, orient=orient, dpi=100, title="T", name_line=True,
                     **extra)
        g = geometry(s)
        spec = single_page(s)
        box = design_box(g, spec, s)
        ctx = Measuring()
        GENERATORS[gen](ctx, box, mulberry32(spec.seed), c, s, lw=2, seed=spec.seed, dpi=g.dpi)
        assert _outside(ctx, box, 2) is None, (c, _outside(ctx, box, 2))
        if has_answer(gen, s):
            key = answer_page([PageSpec(gen=gen, seed=spec.seed, c=c, label="x")])
            ctx = Measuring()
            draw_page(ctx, g, key, s)
            ctx.ops = ctx.ops[1:]   # (after the white paper)
            assert _outside(ctx, g.box, 2) is None
        if s.memory_backs:
            ctx = Measuring()
            draw_page(ctx, g, backs_page(spec), s)
            ctx.ops = ctx.ops[1:]
            assert _outside(ctx, g.box, 2) is None


@pytest.mark.parametrize("lang", LANGS)
def test_each_page_draws_in_each_language(lang):
    i18n.set_language(lang)
    i18n.MISSING.clear()
    for gen, extra in VARIANTS:
        s = Settings(gen=gen, dpi=36, **extra)
        draw_page(RecordingCanvas(), geometry(s), single_page(s), s)
        if has_answer(gen, s):
            draw_page(RecordingCanvas(), geometry(s), answer_page([PageSpec(gen=gen, seed=s.seed, c=5, label="x")]), s)
    assert sorted(m for m in i18n.MISSING if re.search(r"[A-Za-z]{2}", m)) == []


# --- look, say, cover, write, check and the spelling week ------------------------------------------------------------

def test_look_say_cover_write_check_prints_the_words_as_typed():
    ctx, out = _draw("lscwc", ws_theme="custom", ws_words="because, Friend; said\nsaid which")
    assert out["words"] == ["because", "Friend", "said", "which"]
    assert all(w in _texts(ctx) for w in out["words"])
    assert any(op[0] == "stroke" and len(op) > 5 for op in ctx.ops)   # the dashed line to fold along
    many = _draw("lscwc", ws_theme="custom", ws_words=" ".join(f"w{k}x" for k in range(30)))[1]["words"]
    assert len(many) == lscwc.MAX_OWN
    assert [len(_draw("lscwc", c)[1]["words"]) for c in (1, 10)] == [6, 12]


def test_look_say_cover_write_check_in_german_keeps_capitals_and_umlauts():
    i18n.set_language("de")
    words = _draw("lscwc", ws_theme="custom", ws_words="Äpfel, Straße")[1]["words"]
    assert words == ["Äpfel", "Straße"]


def test_missing_letters_leave_out_some_letters_never_all():
    for c, word, want in ((1, "ELEPHANT", 1), (5, "ELEPHANT", 3), (9, "ELEPHANT", 4), (9, "AT", 1), (1, "AT", 1)):
        assert scramble.missing_count(c, len(word)) == want
    ctx, out = _draw("scramble", 9, scramble_kind="missing", ws_theme="custom", ws_words="because friend")
    assert out["kind"] == "missing" and [w for w, _g in out["words"]] == ["BECAUSE", "FRIEND"]
    shown = [t for t in _texts(ctx) if len(t) == 1]
    gaps = sum(len(g) for _w, g in out["words"])
    assert len(shown) == len("BECAUSEFRIEND") - gaps
    solved, _ = _draw("scramble", 9, solve=True, scramble_kind="missing", ws_theme="custom", ws_words="because friend")
    assert sorted(t for t in _texts(solved) if len(t) == 1) == sorted("BECAUSEFRIEND")
    unchanged, _ = _draw("scramble", 5, 3)   # mixed-up letters draw as before
    assert unchanged.ops == _draw("scramble", 5, 3, scramble_kind="mixed")[0].ops


def test_the_spelling_week_with_sight_words():
    out = pack.week(Settings(pack_theme="sight1"), [1, 2, 3, 4, 5])
    assert [p["gen"] for p in out["page_list"]] == list(pack.SPELLING_DAYS)
    assert out["page_list"][2]["scramble_kind"] == "missing"
    theme = pack.week(Settings(pack_theme="animals", pack_days="scramble,words,maths,trace,maze"), [1, 2, 3, 4, 5])
    assert theme["page_list"][0]["scramble_kind"] == "mixed"
    assert {"lscwc", "speed", "drawread", "coords"} <= set(pack.DAY_CHOICES)


# --- times-table speed tests -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("op", ["times", "divide", "both"])
@pytest.mark.parametrize("order", ["mixed", "order"])
def test_speed_test_facts_are_right(op, order):
    for count in (25, 50, 100):
        s = Settings(speed_count=count, speed_op=op, speed_order=order, speed_tables="3, 7, 7, 13, 0")
        facts = speed.make_facts(mulberry32(4), 5, s)
        assert len(facts) == count
        for a, sign, b, answer in facts:
            assert sign in "×÷"
            if sign == "×":
                assert a * b == answer and (a in (3, 7) or b in (3, 7)) and 1 <= min(a, b) and max(a, b) <= 12
            else:
                assert a == b * answer and b in (3, 7) and 1 <= answer <= 12
        if op != "both":
            assert {f[1] for f in facts} == {"×" if op == "times" else "÷"}


def test_speed_tests_in_order_and_mixed():
    s = Settings(speed_count=25, speed_order="order", speed_tables="4")
    facts = speed.make_facts(mulberry32(1), 5, s)
    assert [f[:3] for f in facts[:13]] == [(n, "×", 4) for n in range(1, 13)] + [(1, "×", 4)]
    mixed = speed.make_facts(mulberry32(1), 5, replace(s, speed_order="mixed", speed_count=50))
    first = {(max(a, b), min(a, b)) for a, _s, b, _ans in mixed[:12]}   # every fact of the table once before any again
    assert len(first) == 12
    assert all(mixed[k] != mixed[k + 1] for k in range(len(mixed) - 1))


def test_speed_tests_tables_come_from_complexity_unless_typed():
    assert speed.tables_for(1) == [2, 5, 10] and speed.tables_for(10) == list(range(2, 13))
    assert speed.tables_for(1, "8, 3; 8 and 12, 99") == [8, 3, 12]
    assert speed.note(Settings(speed_tables="")) == "" and speed.note(Settings(speed_tables="6")) == ""
    assert "1 to 12" in speed.note(Settings(speed_tables="zero"))


def test_speed_test_page_has_a_time_and_score_box_and_answers():
    ctx, out = _draw("speed", speed_count=50, speed_chart=True)
    texts = _texts(ctx)
    assert "Time:" in texts and "Score:" in texts and "/ 50" in texts and "My progress" in texts
    solved, out2 = _draw("speed", speed_count=50, speed_chart=True, solve=True)
    assert out2["facts"] == out["facts"]
    answers = [op[1] for op in solved.ops if op[0] == "text" and op[4] == "#666" and op[5] == 500]   # written in grey
    assert answers == [str(f[3]) for f in out["facts"]]
    numbers = [op[1] for op in ctx.ops if op[0] == "text" and op[4] == "#666" and op[5] == 400]   # numbered as drills are
    assert numbers == [f"{k + 1}." for k in range(50)]
    assert "My progress" in _texts(solved)   # the answer is the sheet: the same layout


@pytest.mark.parametrize("count,chart,orient", [(50, True, "portrait"), (100, False, "portrait"), (100, True, "landscape"),
                                                (25, False, "portrait")])
def test_the_speed_answer_page_is_the_sheet_scaled_down(count, chart, orient):
    s = Settings(gen="speed", speed_count=count, speed_chart=chart, orient=orient, dpi=60, title="T", name_line=True)
    g = geometry(s)
    spec = single_page(s)
    sheet = draw_page(RecordingCanvas(), g, spec, s)
    key = PageSpec(kind="answers", header=True, title="Answers", items=[spec])
    ctx = RecordingCanvas()
    draw_page(ctx, g, key, s)
    assert any(op[0] == "transform" for op in ctx.ops)
    texts = [op[1] for op in ctx.ops if op[0] == "text"]
    assert texts.count("Time:") == 1 and str(sheet["facts"][-1][3]) in texts
    # the same columns as the sheet, drawn from the sheet's own box
    box = design_box(g, spec, s)
    again = GENERATORS["speed"](RecordingCanvas(), box, mulberry32(spec.seed), spec.c, s, lw=1, dpi=g.dpi, solve=True)
    assert again["columns"] == sheet["columns"]


def test_a_few_facts_are_centred_in_their_columns():
    ctx, out = _draw("speed", speed_count=25)
    xs = [op[2] for op in ctx.ops if op[0] == "text" and op[5] == 400 and op[1].endswith(".")]
    right = max(op[3] for op in ctx.ops if op[0] == "extent")
    assert min(xs) > 2400 * 0.05 and 2400 - right < 2400 * 0.2 and out["columns"] >= 2


# --- draw what you read --------------------------------------------------------------------------------------------------

def test_every_language_has_sentences_at_each_level():
    for lang in LANGS:
        levels = drawread.READ_SENTENCES[lang]
        assert len(levels) == 3 and all(len(lv) == 12 and len(set(lv)) == 12 for lv in levels), lang
        lengths = [sum(len(t.split()) for t in lv) / len(lv) for lv in levels]
        assert lengths[0] < lengths[1] < lengths[2], lang


def test_draw_what_you_read_picks_sentences_for_the_age():
    i18n.set_language("fr")
    ctx, out = _draw("drawread", 1)
    assert len(out["sentences"]) == 4 and set(out["sentences"]) <= set(drawread.READ_SENTENCES["fr"][0])
    assert len(out["frames"]) == 4 and all(w > 300 and h > 300 for _x, _y, w, h in out["frames"])
    assert len(_draw("drawread", 5)[1]["sentences"]) == 6
    assert set(_draw("drawread", 9)[1]["sentences"]) <= set(drawread.READ_SENTENCES["fr"][2])


def test_your_own_sentences_to_draw():
    out = _draw("drawread", draw_source="custom", draw_text="A red car; ; A dog in the rain\nThe sun")[1]
    assert out["sentences"] == ["A red car", "A dog in the rain", "The sun"]
    assert drawread.note(Settings(draw_source="custom", draw_text=" ; ")) != ""
    assert _draw("drawread", draw_source="custom", draw_text="")[1]["sentences"]   # nothing typed: Inkline's own


# --- coordinate grids ------------------------------------------------------------------------------------------------------

def test_pictures_are_whole_numbers_on_the_grid_and_named_in_every_language():
    for name, pic in pictures.PICTURES.items():
        for stroke in pic["strokes"]:
            assert len(stroke) >= 2
            assert all(isinstance(x, int) and isinstance(y, int) and 0 <= x <= 10 and 0 <= y <= 10 for x, y in stroke)
    assert set(pictures.SIMPLE) <= set(pictures.PICTURES)
    for lang in LANGS:
        assert set(pictures.WORDS[lang]) == set(pictures.PICTURES), lang


@pytest.mark.parametrize("c", [1, 5, 9])
def test_plot_the_points_lists_every_point_and_the_answer_joins_them(c):
    ctx, out = _draw("coords", c, 3)
    lo, hi = coords.plot_range(c)
    assert out["kind"] == "plot" and out["range"] == (lo, hi)
    pts = [p for stroke in out["strokes"] for p in stroke]
    assert all(lo <= x <= hi and lo <= y <= hi for x, y in pts)
    if c >= 8:
        assert lo < 0
    if c <= 3:
        assert out["picture"] in pictures.SIMPLE
    listed = " ".join(_texts(ctx))
    assert all(coords._point(p) in listed for p in pts)
    solved, _ = _draw("coords", c, 3, solve=True)
    lines = len([op for op in solved.ops if op[0] == "L"]) - len([op for op in ctx.ops if op[0] == "L"])
    assert lines == sum(len(s) - 1 for s in out["strokes"])


def test_battleships_grids_and_fleet():
    assert [coords.battle_size(c)[0] for c in (1, 5, 10)] == [6, 8, 10]
    ctx, out = _draw("coords", 10, coord_kind="battle")
    texts = _texts(ctx)
    assert "My ships" in texts and "Their ships" in texts and texts.count("J") == 2 and texts.count("10") == 2
    assert out["fleet"] == [5, 4, 3, 3, 2] and texts.count("Sunk") == 5


# --- memory cards ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["pictures", "words", "dots"])
def test_memory_cards_come_in_pairs(kind):
    for c, n in ((1, 8), (3, 12), (5, 16), (7, 20), (10, 24)):
        (cols, rows), cards = memory.make_cards(mulberry32(c), c, Settings(memory_kind=kind))
        assert cols * rows == n == len(cards)
        pairs = {}
        for card, pair in cards:
            pairs.setdefault(pair, []).append(card)
        assert len(pairs) == n // 2 and all(len(v) == 2 for v in pairs.values())
        for a, b in pairs.values():
            if kind == "pictures":
                assert a == b
            elif kind == "words":
                assert {a[0], b[0]} == {"picture", "word"}
            else:
                assert {a[0], b[0]} == {"number", "dots"} and a[1] == b[1]
    assert memory.grid_for(10, landscape=True) == (6, 4)


def test_word_cards_use_the_language():
    i18n.set_language("es")
    _ctx, out = _draw("memory", 10, memory_kind="words")
    words = {v for (what, v), _p in out["cards"] if what == "word"}
    assert "estrella" in words or "casa" in words or words <= set(pictures.WORDS["es"].values())
    assert words <= set(pictures.WORDS["es"].values())


def test_your_own_pairs():
    assert memory.own_pairs("cat: chat; dog = chien\n sun ;;") == [("cat", "chat"), ("dog", "chien"), ("sun", "sun")]
    (cols, rows), cards = memory.make_cards(mulberry32(1), 10, Settings(memory_kind="custom", memory_words="a: b; c: d"))
    assert (cols, rows) == (2, 4) and len(cards) == 4   # few pairs: the smallest grid, bigger cards
    ten = "; ".join(f"w{k}: v{k}" for k in range(10))   # your pairs set the grid, whatever the complexity
    (cols, rows), cards = memory.make_cards(mulberry32(1), 1, Settings(memory_kind="custom", memory_words=ten))
    assert len(cards) == 20 and cols * rows >= 20
    assert memory.note(Settings(memory_kind="custom", memory_words=ten)) == ""
    assert memory.note(Settings(memory_kind="custom")) != ""
    many = "; ".join(f"w{k}: v{k}" for k in range(20))
    assert "12" in memory.note(Settings(memory_kind="custom", memory_words=many))
    assert len(memory.make_cards(mulberry32(1), 10, Settings(memory_kind="custom", memory_words=many))[1]) == 24


def test_dots_cards_have_that_many_dots():
    ctx = RecordingCanvas()
    for n in range(1, 13):
        ctx.ops = []
        assert memory._dots(ctx, n, 0, 0, 300, 400) == n
        assert len([op for op in ctx.ops if op[0] == "A"]) == n


def test_card_backs_are_mirrored_for_long_edge_duplex():
    # upright: the sheet flips side to side, so card (row, col) has its back at (row, cols - 1 - col)
    assert [memory.back_place(k, 4, 2, "cols") for k in range(8)] == [3, 2, 1, 0, 7, 6, 5, 4]
    # sideways: the sheet flips top to bottom, so the rows swap
    assert [memory.back_place(k, 4, 2, "rows") for k in range(8)] == [4, 5, 6, 7, 0, 1, 2, 3]
    for flip in ("cols", "rows"):   # each back once
        assert sorted(memory.back_place(k, 4, 6, flip) for k in range(24)) == list(range(24))


def _flipped(point, g, orient):
    """Where a point printed on the back of the sheet lands on the front, after a long-edge flip."""
    x, y = point
    return (g.W - x, y) if orient == "portrait" else (x, g.H - y)


@pytest.mark.parametrize("orient", ["portrait", "landscape"])
@pytest.mark.parametrize("paper", ["letter", "a4"])
def test_each_back_lands_behind_its_card(orient, paper):
    s = Settings(gen="memory", memory_backs=True, complexity=6, paper=paper, orient=orient, dpi=50, title="Cards",
                 name_line=True, seed=9)
    g = geometry(s)
    spec = single_page(s)
    front = draw_page(RecordingCanvas(), g, spec, s)
    back = draw_page(RecordingCanvas(), g, backs_page(spec), s)
    assert front["cards"] == back["cards"]
    (cols, _rows), (cw, ch) = front["grid"], front["card_size"]

    def centre(out, spot):
        r, c = divmod(spot, cols)
        x0, y0 = out["origin"]
        return x0 + (c + 0.5) * cw, y0 + (r + 0.5) * ch
    for k in range(len(front["cards"])):
        fx, fy = centre(front, front["places"][k])
        bx, by = _flipped(centre(back, back["places"][k]), g, orient)
        assert abs(fx - bx) < 0.5 and abs(fy - by) < 0.5, (k, (fx, fy), (bx, by))


def test_a_job_prints_the_cards_then_their_backs(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp import jobs
    from inkapp.state import State
    s = Settings(gen="memory", memory_backs=True, dpi=36)
    j = jobs.job(State(s))
    assert j.count == 2 and j.backs and j.amount() == "1 sheet of cards with their backs (both sides)"
    ops = []
    for i in range(j.count):
        ctx = RecordingCanvas()
        out = j.draw(ctx, i)
        ops.append(ctx.ops)
    assert any(op[0] == "text" and op[1] == "?" for op in ops[1]) and not any(op[0] == "text" and op[1] == "?" for op in ops[0])
    j3 = jobs.job(State(s), copies=3, vary=True, answers=True)
    assert j3.count == 6 and j3.answers == 0 and j3.amount() == "3 sheets of cards with their backs (both sides)"
    plain = jobs.job(State(replace(s, memory_backs=False)))
    assert plain.count == 1 and not plain.backs
    assert jobs.job(State(replace(s, sheet="halves"))).count == 1   # several designs on the sheet: no backs page


# --- the sidebar, the gallery, presets, ages, the command line ---------------------------------------------------------------

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
    _set(win, gen="lscwc")
    assert sb.shown(sb.lscwc_opts) and sb.shown(sb.words_opts) and not sb.shown(sb.speed_opts)
    _set(win, gen="scramble")
    assert sb.shown(sb.scramble_opts) and sb.shown(sb.words_opts)
    sb.scramble_kind.set_value("missing")
    assert win.state.settings.scramble_kind == "missing"
    _set(win, gen="speed")
    assert sb.shown(sb.speed_opts) and not sb.shown(sb.speed_note)
    sb.speed_count.set_value(100)
    assert win.state.settings.speed_count == 100
    _set(win, speed_tables="none")
    assert sb.shown(sb.speed_note)
    assert win.history.undoText() == "Tables"
    sb.speed_op.set_value("both")
    assert win.history.undoText() == "Times or sharing"   # the undo step is called what the control is
    sb.speed_count.set_value(25)
    assert win.history.undoText() == "How many facts"
    _set(win, gen="drawread")
    assert sb.shown(sb.draw_opts) and not sb.shown(sb.draw_text_row)
    _set(win, draw_source="custom")
    assert sb.shown(sb.draw_text_row) and sb.shown(sb.draw_note)
    _set(win, gen="coords")
    assert "fewer points" in sb.complexity_hint.text()
    _set(win, coord_kind="battle")
    assert "Print one for each player" in sb.complexity_hint.text()
    _set(win, gen="memory")
    assert sb.shown(sb.memory_opts) and not sb.shown(sb.memory_words_row) and not sb.shown(sb.memory_backs_hint)
    _set(win, memory_kind="custom", memory_backs=True)
    assert sb.shown(sb.memory_words_row) and sb.shown(sb.memory_note) and sb.shown(sb.memory_backs_hint)
    assert sb.complexity_hint.text().startswith("Your pairs set how many cards")
    assert sb.memory_backs_check.isEnabled() and not sb.shown(sb.memory_no_backs_hint)
    for where in ({"booklet": True}, {"sheet": "halves"}, {"poster": True}):   # backs never print there: say so
        _set(win, **where)
        assert not sb.memory_backs_check.isEnabled() and sb.shown(sb.memory_no_backs_hint), where
        assert not sb.shown(sb.memory_backs_hint)
        _set(win, **{k: {"booklet": False, "sheet": "one", "poster": False}[k] for k in where})
    assert sb.memory_backs_check.isEnabled()
    _set(win, gen="lscwc", ws_theme="custom", ws_words=" ".join(f"word{chr(97 + k % 26)}{k}" for k in range(23)))
    assert sb.shown(sb.lscwc_note) and "3" in sb.lscwc_note.text()
    _set(win, gen="coords", coord_kind="plot")
    assert sb.shown(sb.coord_answer_check)
    _set(win, coord_kind="battle")
    assert not sb.shown(sb.coord_answer_check)


def test_missing_letters_is_called_missing_letters():
    from inkengine import book
    from inkengine.page import pattern_name
    assert pattern_name("scramble", Settings(scramble_kind="missing")) == "Missing letters"
    assert pattern_name("scramble", Settings()) == "Unscramble"
    week = pack.week(Settings(pack_theme="spelling", pack_words="because, friend, said"), [1, 2, 3, 4, 5])
    pages = book.book_pages(replace(Settings(), **week))
    labels = [p.label for p in pages if p.kind == "design"]
    assert labels[2] == "Missing letters 3"
    key = [p for p in pages if p.kind == "answers"]
    assert any(d.label == "Missing letters 3" for p in key for d in p.items)
    assert pack.day_name("scramble", True) == "Missing letters" and pack.day_name("scramble", False) == "Unscramble"
    one = book.book_pages(Settings(gen="scramble", scramble_kind="missing", booklet=True, pages=2))
    ctx = RecordingCanvas()
    draw_page(ctx, geometry(Settings()), one[0], Settings(gen="scramble", scramble_kind="missing", booklet=True, pages=2))
    texts = _texts(ctx)
    assert any(t.startswith("2 missing letters pages") for t in texts)


def test_the_pack_days_say_missing_letters_in_a_spelling_week(win):
    sb = win.sidebar
    at = pack.DAY_CHOICES.index("scramble")
    _set(win, pack_theme="spelling", pack_words="sun, rain")
    assert sb.pack_day_combos[2].itemText(at) == "Missing letters" and sb.pack_day_combos[2].value() == "scramble"
    _set(win, pack_days="maths,trace,scramble,words,maze")
    assert "Missing letters" in sb.pack_hint.text()
    _set(win, pack_theme="animals")
    assert sb.pack_day_combos[2].itemText(at) == "Unscramble" and "Unscramble" in sb.pack_hint.text()


def test_look_say_cover_says_when_words_are_left_out():
    many = " ".join(f"w{k}x" for k in range(25))
    assert lscwc.note(Settings(ws_theme="custom", ws_words=many)) == "A sheet holds 20 words: the last 5 aren't on it."
    assert lscwc.note(Settings(ws_theme="custom", ws_words="a b c")) == "" and lscwc.note(Settings()) == ""


def test_the_coordinate_grid_can_show_its_picture_and_the_gallery_does():
    from inkapp import thumbs
    plain, _ = _draw("coords", 5, 3)
    shown, _ = _draw("coords", 5, 3, coord_answer=True)
    assert len([op for op in shown.ops if op[0] == "L"]) > len([op for op in plain.ops if op[0] == "L"])
    spec = thumbs.gallery_spec(Settings(seed=1), "coords")
    assert spec.opts == {"coord_answer": True} and thumbs.gallery_spec(Settings(seed=1), "maze").opts == {}


def test_four_quadrant_corner_numbers_dont_touch():
    ctx, _ = _draw("coords", 9, 3)
    lows = [op for op in ctx.ops if op[0] == "extent" and op[1] == "−5"]
    assert len(lows) == 2
    (a, b) = lows
    size = [op for op in ctx.ops if op[0] == "text" and op[1] == "−5"][0][6]
    across, up = (a, b) if a[4] > b[4] else (b, a)   # along the bottom (hung from its top), and up the side (centred)
    assert across[2] > up[3] or across[4] > up[4] + size * 0.35   # beside it, or wholly below it


def test_upright_battleships_use_the_page():
    _ctx, out = _draw("coords", 10, coord_kind="battle", box=Box(0, 0, 2250, 2900))
    assert out["grids"][0][2] > 2250 * 0.5


def test_the_gallery_finds_them_by_kind():
    from inkapp import layout, sidebar
    descriptions = dict(sidebar.GEN_OPTIONS)
    found = {q: [g for g in NEW if layout.matches(g, q, NAMES, descriptions)]
             for q in ("pairs", "multiplication", "Battleships", "fold", "drawing")}
    assert found == {"pairs": ["memory"], "multiplication": ["speed"], "Battleships": ["coords"], "fold": ["lscwc"],
                     "drawing": ["drawread"]}
    assert all(any(g in gens for _group, gens in layout.GROUPS) for g in NEW)
    for lang, queries in (("es", ("parejas", "flota", "tablas")), ("de", ("Paare", "Schiffe", "Einmaleins")),
                          ("fr", ("paires", "navale", "multiplication"))):
        i18n.set_language(lang)
        assert [any(layout.matches(g, q, NAMES, descriptions) for g in NEW) for q in queries] == [True] * 3, lang


def test_presets_and_ages():
    from inkapp.state import BUILTIN_PRESETS, State
    from inkengine import ages
    for gen in NEW:
        assert set(ages.COMPLEXITY[gen]) == {"4-6", "7-9", "10+"}
    st = State()
    st.apply_preset(BUILTIN_PRESETS["Times-table speed test with a progress chart"])
    assert (st.settings.gen, st.settings.speed_chart, st.settings.speed_count) == ("speed", True, 50)
    st.apply_preset(BUILTIN_PRESETS["Memory cards with card backs"])
    assert (st.settings.gen, st.settings.memory_backs) == ("memory", True)
    st.apply_preset(BUILTIN_PRESETS["Battleships for two players"])
    assert (st.settings.gen, st.settings.coord_kind) == ("coords", "battle")


def test_settings_from_a_file_are_checked():
    s = Settings.from_dict({"speedCount": 33, "speedOp": "plus", "coordKind": "battle", "memoryKind": "dots",
                            "memoryWords": "x" * 900, "scrambleKind": "missing"})
    assert (s.speed_count, s.speed_op, s.coord_kind, s.memory_kind, s.scramble_kind) == (50, "times", "battle", "dots", "missing")
    assert len(s.memory_words) == memory.MAX_TEXT


def test_the_command_line_makes_a_spelling_week_and_cards_with_backs(tmp_path):
    env = {**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"}
    week = tmp_path / "week.pdf"
    subprocess.run([sys.executable, "-m", "inkengine", "words", "--spelling-pack", "because, friend, said", "--dpi", "150",
                    "--seed", "3", "-o", str(week)], cwd=ROOT, env=env, check=True, capture_output=True)
    cards = tmp_path / "cards.pdf"
    out = subprocess.run([sys.executable, "-m", "inkengine", "memory", "--cards", "dots", "--card-backs", "--dpi", "150",
                          "-o", str(cards)], cwd=ROOT, env=env, check=True, capture_output=True, text=True).stdout
    assert "long edge" in out
    speed_pdf = tmp_path / "speed.pdf"
    subprocess.run([sys.executable, "-m", "inkengine", "speed", "--facts", "100", "--tables", "6,7", "--answers",
                    "--dpi", "150", "-o", str(speed_pdf)], cwd=ROOT, env=env, check=True, capture_output=True)
    bad = subprocess.run([sys.executable, "-m", "inkengine", "coords", "--coords", "battle", "--answers", "-o",
                          str(tmp_path / "b.pdf")], cwd=ROOT, env=env, capture_output=True, text=True)
    assert bad.returncode != 0 and "no answers" in bad.stderr

    def pages(p):
        return int(re.search(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", p.read_bytes()).group(1))
    assert pages(week) == 7 and pages(cards) == 2 and pages(speed_pdf) == 2


def test_speed_test_never_repeats_a_fact_from_overlapping_tables():
    """2 × 6 from the 2s and 6 × 2 from the 6s are one fact: none comes twice until every fact has come once."""
    import random
    from inkengine.patterns import speed

    class S:
        speed_count, speed_tables, speed_op, speed_order = 50, "", "times", "mixed"
    for seed in range(20):
        facts = speed.make_facts(random.Random(seed).random, 5, S())
        keys = [tuple(sorted((a, b))) for a, _s, b, _r in facts]
        assert len(keys) == len(set(keys)), seed


@pytest.mark.parametrize("family", ["DejaVu Sans", "DejaVu Sans Mono"])
def test_each_page_fits_in_wider_fonts(family, monkeypatch):
    """Text is measured in the font the page is drawn in: DejaVu Sans (Linux machines without Inter or Cantarell, as
    CI's) and a wider one still fit."""
    from PySide6.QtGui import QFontDatabase
    from inkengine import qt
    if family not in QFontDatabase.families():
        pytest.skip(f"{family} isn't installed")
    monkeypatch.setattr(qt, "FONT_FAMILIES", [family])
    for gen, extra in VARIANTS:
        for paper in ("letter", "a4"):
            for orient in ("portrait", "landscape"):
                for c in (1, 8):
                    s = Settings(gen=gen, complexity=c, seed=c * 5, paper=paper, orient=orient, dpi=100, title="T",
                                 name_line=True, **extra)
                    g = geometry(s)
                    spec = single_page(s)
                    box = design_box(g, spec, s)
                    ctx = Measuring()
                    GENERATORS[gen](ctx, box, mulberry32(spec.seed), c, s, lw=2, seed=spec.seed, dpi=g.dpi)
                    assert _outside(ctx, box, 2) is None, (gen, extra, paper, orient, c, _outside(ctx, box, 2))
