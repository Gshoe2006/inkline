"""Graph and lined paper, reward charts and certificates, reading comprehension and sight words."""

import json
import os

import pytest

from inkengine import i18n, pack
from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings, draw_page, geometry, single_page
from inkengine.patterns import reading, reward, ruled, words
from inkengine.rng import mulberry32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _texts(ctx):
    return [op[1] for op in ctx.ops if op[0] == "text"]


@pytest.mark.parametrize("kind", list(ruled.KINDS))
def test_every_paper_fills_the_page_and_gets_finer_with_complexity(kind):
    box = Box(0, 0, 8 * 100, 10 * 100)
    wide = ruled.draw(RecordingCanvas(), box, None, 1, Settings(ruled_kind=kind), dpi=100)
    fine = ruled.draw(RecordingCanvas(), box, None, 10, Settings(ruled_kind=kind), dpi=100)
    key = next(iter(wide))   # cols, dots, staves or rows
    assert fine[key] > wide[key] > 0
    assert ruled.spacing(1) == pytest.approx(1.0) and ruled.spacing(10) == pytest.approx(5 / 25.4)


def test_squared_paper_is_square_and_every_fifth_line_darker():
    ctx = RecordingCanvas()
    out = ruled.draw(ctx, Box(0, 0, 800, 1000), None, 10, Settings(ruled_kind="squared"), dpi=100)
    assert out["cols"] == int(800 // (ruled.spacing(10) * 100))
    widths = {op[2] for op in ctx.ops if op[0] == "stroke"}
    assert len(widths) == 2


def test_a_sticker_chart_counts_to_its_goal_and_shows_the_name():
    assert [reward.count_for(c) for c in (1, 4, 7, 10)] == [10, 20, 30, 40]
    ctx = RecordingCanvas()
    out = reward.draw(ctx, Box(0, 0, 800, 1000), None, 4, Settings(reward_text="Tidy room"), dpi=100, filled_name="Ana")
    texts = _texts(ctx)
    assert out["count"] == 20 and "Ana" in texts and "Tidy room" in texts and "19" in texts and "20" not in texts


def test_a_certificate_carries_the_name_and_reason_or_lines_for_them():
    ctx = RecordingCanvas()
    reward.draw(ctx, Box(0, 0, 1000, 700), None, 1, Settings(reward_kind="certificate", reward_text="Kindness"),
                dpi=100, filled_name="Ben")
    texts = _texts(ctx)
    assert {"Well done!", "Ben", "Kindness", "CERTIFICATE"} <= set(texts)
    blank = RecordingCanvas()
    reward.draw(blank, Box(0, 0, 1000, 700), None, 1, Settings(reward_kind="certificate"), dpi=100)
    assert "Ben" not in _texts(blank) and "Kindness" not in _texts(blank)


def test_names_put_each_childs_name_on_their_certificate():
    from inkapp import jobs
    from inkapp.state import State
    seen = []
    real = reward.draw

    def spy(*a, **k):
        seen.append(k.get("filled_name"))
        return real(*a, **k)
    reward.draw = spy
    try:
        from inkengine import patterns
        patterns.GENERATORS["reward"] = spy
        j = jobs.job(State(Settings(gen="reward", reward_kind="certificate", dpi=30, name_line=True)), names=["Ana", "Ben"])
        for i in range(j.count):
            j.draw(RecordingCanvas(), i)
    finally:
        reward.draw = real
        patterns.GENERATORS["reward"] = real
    assert seen == ["Ana", "Ben"]


@pytest.mark.parametrize("lang", ["en", "es", "fr", "pt", "de"])
def test_every_language_has_the_passages_and_their_answers_are_sound(lang):
    path = os.path.join(ROOT, "inkengine", "reading", f"{lang}.json")
    data = json.load(open(path, encoding="utf-8"))
    english = json.load(open(os.path.join(ROOT, "inkengine", "reading", "en.json"), encoding="utf-8"))
    assert len(data) == len(english) == 30
    for p, e in zip(data, english):
        assert p["level"] == e["level"] and len(p["questions"]) == len(e["questions"]) and p["title"] and p["text"]
        for q, eq in zip(p["questions"], e["questions"]):
            assert ("choices" in q) == ("choices" in eq) and q["q"]
            if "choices" in q:
                assert len(q["choices"]) == len(eq["choices"]) and q["answer"] == eq["answer"] < len(q["choices"])
            else:
                assert isinstance(q["answer"], str) and q["answer"]


@pytest.mark.parametrize("c, level", [(1, 1), (3, 1), (4, 2), (7, 2), (8, 3), (10, 3)])
def test_complexity_picks_the_level_and_the_answers_are_on_the_answer_page(c, level):
    s = Settings(gen="reading")
    plain, solved = RecordingCanvas(), RecordingCanvas()
    out = reading.draw(plain, Box(0, 0, 900, 1100), mulberry32(c), c, s, dpi=100)
    reading.draw(solved, Box(0, 0, 900, 1100), mulberry32(c), c, s, dpi=100, solve=True)
    assert out["level"] == level and out["title"] in _texts(plain)
    p = next(x for x in reading.passages() if x["title"] == out["title"])
    written = [q["answer"] for q in p["questions"] if "choices" not in q]
    assert not set(written) & set(_texts(plain)) and set(written) <= set(_texts(solved))
    assert sum(op[0] == "fill" for op in solved.ops) >= sum(1 for q in p["questions"] if "choices" in q)


def test_a_long_passage_shrinks_to_fit_the_page():
    out = reading.draw(RecordingCanvas(), Box(0, 0, 500, 500), mulberry32(1), 10, Settings(), dpi=100)
    small = reading.draw(RecordingCanvas(), Box(0, 0, 900, 1400), mulberry32(1), 10, Settings(), dpi=100)
    assert out["size"] < small["size"]


@pytest.mark.parametrize("lang", ["en", "es", "fr", "pt", "de"])
def test_sight_words_in_every_language_and_a_sight_word_week(lang):
    i18n.set_language(lang)
    try:
        for stage in pack.SIGHT:
            ws = words.THEMES_BY_LANGUAGE.get(lang, words.THEMES)[stage].split()
            assert len(ws) >= 25 and all(len(w) >= 3 for w in ws)
            grid = words.make_word_search(mulberry32(3), 6, words.word_pool(mulberry32(3), 6, stage))
            assert grid and len(grid["placed"]) >= 8
        out = pack.week(Settings(pack_theme="sight1"), [1, 2, 3, 4, 5])
        pages = out["page_list"]
        assert out["pack_theme"] == "sight1" and [p["gen"] for p in pages][-1] == "spelltest"
        listed = pages[0]["trace_text"].split(", ")
        theme = words.THEMES_BY_LANGUAGE.get(lang, words.THEMES)["sight1"].split()
        assert len(listed) == pack.SIGHT_WEEK and set(listed) <= set(theme)
    finally:
        i18n.set_language("en")


@pytest.mark.parametrize("gen", ["ruled", "reward", "reading"])
def test_the_new_pages_draw_on_a_page(gen):
    s = Settings(gen=gen, dpi=40)
    draw_page(RecordingCanvas(), geometry(s), single_page(s), s)
