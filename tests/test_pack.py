"""Worksheet packs: a week of worksheets for one age and theme, as a booklet built page by page."""

import pytest
from PySide6.QtWidgets import QApplication

from conftest import settle
from inkapp import jobs
from inkengine import ages, book, i18n, pack
from inkengine.page import Settings

PRESET = "Worksheet pack: a week, with answers"


@pytest.mark.parametrize("age", ["4-6", "7-9", "10+"])
def test_a_week_is_five_worksheets_set_for_the_age(age):
    out = pack.week(Settings(age=age, pack_theme="space"), [11, 12, 13, 14, 15])
    pages = out["page_list"]
    assert [p["gen"] for p in pages] == ["maths", "trace", "crossword", "words", "maze"]
    assert [p["seed"] for p in pages] == [11, 12, 13, 14, 15]
    for p in pages:
        assert p["complexity"] == ages.COMPLEXITY[p["gen"]][age]
        assert p["maths_kind"] == ages.EXTRAS[age]["maths_kind"] and p["trace_source"] == ages.EXTRAS[age]["trace_source"]
        assert p["ws_theme"] == p["cross_theme"] == "space" and p["maze_shape"] == "rect" and not p["cbn"]
    assert out["booklet"] and out["key"] and out["cover"] and out["name_line"] and out["age"] == age
    assert out["weight"] == ages.EXTRAS[age]["weight"] and out["pages"] == 5 and out["gen"] == "maths"
    s = Settings(**{k: v for k, v in out.items()})
    kinds = [p.kind for p in book.book_pages(s)]
    assert kinds[0] == "cover" and kinds.count("design") == 5 and kinds[-1] == "answers"


def test_older_children_trace_the_themes_words_and_any_age_means_the_middle():
    out = pack.week(Settings(age="10+", pack_theme="food"), [1] * 5)
    assert out["page_list"][1]["trace_text"].split(", ")[:2] == ["apple", "banana"]
    assert pack.week(Settings(age="any"), [1] * 5)["age"] == pack.DEFAULT_AGE
    ocean = pack.week(Settings(pack_theme="ocean"), [1] * 5)["page_list"]
    assert ocean[2]["cross_theme"] == ocean[3]["ws_theme"] == "ocean"
    assert pack.week(Settings(pack_theme="spelling", pack_words=" , "), [1] * 5)["pack_theme"] == "animals"
    i18n.set_language("fr")
    try:
        assert pack.theme_words("food", 2) == ["pomme", "banane"]
    finally:
        i18n.set_language("en")


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("5.1.0", remember=False)
    w.show()
    settle(w)
    yield w
    w.close()
    w.deleteLater()


def test_the_preset_makes_the_pack_for_the_age_chosen_and_undoes_in_one_step(win):
    win.state.update(age="4-6")
    win.sidebar.load()
    before = win.state.settings
    win._apply_preset("b", PRESET)
    settle(win)
    s = win.state.settings
    assert [p["gen"] for p in s.page_list] == list(pack.DAYS) and s.age == "4-6" and s.booklet
    assert win.history.undoText() == f"“{PRESET}”"
    assert "ages 4–6" in win.sidebar.status.text() and "animals" in win.sidebar.status.text()
    assert not win.sidebar.pack_words_row.isVisibleTo(win)
    assert win.sidebar.page_list.count() == 5   # the page list shows the five pages to change
    win.history.undo()
    assert win.state.settings.page_list == before.page_list and not win.state.settings.booklet
    win.history.redo()
    again = win.state.settings.page_list
    win._apply_preset("b", PRESET)   # chosen again: new designs
    assert [p["seed"] for p in win.state.settings.page_list] != [p["seed"] for p in again]


def test_a_pack_for_every_child_with_a_teachers_answer_book(win):
    win._apply_preset("b", PRESET)
    settle(win)
    j = jobs.job(win.state, copies=3, answer_book=True)
    per_child = 1 + 5   # cover and five worksheets; the answers go to the teacher's book
    assert j.count >= 3 * per_child + 1 and j.answers >= 1


def test_the_cover_says_worksheets():
    out = pack.week(Settings(), [1] * 5)
    cover = book.book_pages(Settings(**out))[0]
    assert cover.kind == "cover" and cover.title == "Worksheets"
    assert book.book_pages(Settings(**{**out, "title": "Week 3"}))[0].title == "Week 3"


def test_a_spelling_week_uses_the_words_four_ways():
    out = pack.week(Settings(age="7-9", pack_theme="spelling", pack_words="because, Friend; said\nsaid which"), [1, 2, 3, 4, 5])
    pages = out["page_list"]
    assert [p["gen"] for p in pages] == ["trace", "crossword", "words", "scramble", "spelltest"]
    listed = "because, Friend, said, which"
    assert pages[0]["trace_source"] == "words" and pages[0]["trace_text"] == listed
    assert pages[2]["ws_theme"] == pages[3]["ws_theme"] == pages[4]["ws_theme"] == "custom"
    assert pages[2]["ws_words"] == pages[4]["ws_words"] == listed
    from inkengine.patterns import crossword
    clues = crossword.parse_entries(pages[1]["cross_words"])
    assert [w for w, _c in clues] == ["BECAUSE", "FRIEND", "SAID", "WHICH"]
    for w, clue in clues:
        letters = clue.split(": ", 1)[1].replace(" ", "")
        assert clue.startswith("Unscramble: ") and sorted(letters) == sorted(w) and letters != w


def test_the_booklet_section_makes_a_pack_from_its_own_controls(win):
    sb = win.sidebar
    win.state.update(age="10+")
    sb.load()
    sb.pack_theme.set_value("spelling")
    QApplication.processEvents()
    assert sb.pack_words_row.isVisibleTo(win) and not sb.pack_btn.isEnabled()   # no words yet, and it says so
    assert sb.pack_hint.text() == "Type this week's spelling words to make the pack."
    sb.pack_words.setText("rain, cloud, thunder")
    sb.pack_words.editingFinished.emit()
    QApplication.processEvents()
    assert sb.pack_btn.isEnabled() and "unscramble" in sb.pack_hint.text() and "10 and up" in sb.pack_hint.text()
    sb.pack_btn.click()
    settle(win)
    s = win.state.settings
    assert [p["gen"] for p in s.page_list][-2:] == ["scramble", "spelltest"]
    assert s.page_list[2]["ws_words"] == "rain, cloud, thunder"
    assert win.history.undoText() == "Make a week of worksheets"
