"""Languages: the Spanish translation is complete, well formed and used; English is unchanged."""

import json
import os
import re
import sys

import pytest
from PySide6.QtWidgets import QApplication

from inkengine import i18n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packaging"))


@pytest.fixture
def spanish():
    i18n.set_language("es")
    yield
    i18n.set_language("en")


def test_the_spanish_file_covers_every_string_with_the_same_placeholders():
    import i18n_strings
    es = json.load(open(os.path.join(ROOT, "inkengine", "locale", "es.json"), encoding="utf-8"))
    missing = [s for s in i18n_strings.scan() if s not in es]
    assert missing == []
    for en, tr in es.items():
        assert sorted(re.findall(r"\{\w+\}", en)) == sorted(re.findall(r"\{\w+\}", tr)), en
        assert bool(re.search(r"&(?!amp;)\w", en)) == bool(re.search(r"&(?!amp;)\w", tr)), en   # menus keep a keyboard letter
        assert tr.strip() and tr == tr.strip(), en


def test_choosing_a_language():
    assert i18n.system_language("es_ES") == i18n.system_language("es-MX") == "es"
    assert i18n.system_language("fr_FR") == i18n.system_language("") == "en"
    i18n.set_language("xx")
    assert i18n.LANG == "en" and i18n.tr("Name") == "Name"
    i18n.set_language("es")
    try:
        assert i18n.tr("Name") == "Nombre" and i18n.tr("Answers") == "Soluciones"
        assert i18n.tr("{n} copies").format(n=3) == "3 copias"
        assert i18n.tr("not a string anyone translated") == "not a string anyone translated"
        assert "not a string anyone translated" in i18n.MISSING
    finally:
        i18n.set_language("en")


def _walk_states(w):
    """Drive the window through its states, so every string it can show is asked for."""
    from inkapp import render
    from inkapp.state import State
    sb = w.sidebar

    def go(**kw):
        for k, v in kw.items():
            w.state.update(**{k: v})
            sb.load()
            w._changed(k)
        st = w.state
        sb.sync(render.view(State(st.settings, st.photos, st.sel, st.page, copy=st.copy, class_set=sb.class_set_view())))
    for gen in ("mandala", "maze", "truchet", "contour", "flow", "dots", "sudoku", "name", "words", "nonogram",
                "spot", "kakuro", "maths", "trace", "crossword"):
        go(gen=gen)
    go(gen="maze", maze_shape="word")
    go(gen="words", ws_theme="custom", ws_words="sol, luna")
    go(gen="trace", trace_source="words")
    go(trace_source="name")
    go(gen="crossword", cross_theme="custom", cross_words="zzz")
    go(gen="mandala", cbn=True)
    go(gen="name", name_bg="none")
    go(gen="maze", age="7-9", sheet="banner")
    sb.copies.setText("3")
    go(name_line=True)
    sb.copies_names.setText("Ana, Ben")
    go(sheet="one")
    sb.copies_names.setText("Ana")
    sb.copies_names.setText("")
    sb.copies.setText("0")
    go(booklet=True, key=True)
    sb.copies.setText("4")
    sb.copies_answer_book.setChecked(True)
    sb.only_pages.setText("1-2, cover")
    sb.only_pages.setText("99")
    go(fold=True)
    go(fold=False, mix=True)
    w.edit_pages() if hasattr(w, "edit_pages") else None
    go(booklet=False, poster=True)
    go(poster=False, testpage=True)
    go(testpage=False, mode="convert")
    for style in ("fs", "atkinson", "bayer", "halftone", "engrave", "stipple", "cbn", "nono", "threshold", "line"):
        go(style=style)
    go(mode="make")
    w.offer_whats_new() if False else None


def test_the_window_in_spanish_asks_for_nothing_untranslated(spanish, tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("5.0.0", remember=False)
    w.show()
    try:
        _walk_states(w)
        # pages of every kind, printed: their words too
        from inkapp import jobs, render
        from inkapp.state import State
        from inkengine.canvas import RecordingCanvas
        from inkengine.page import Settings
        for s in (Settings(gen="words", dpi=36, booklet=True, pages=2, cover=True, key=True, name_line=True, title="T"),
                  Settings(gen="crossword", dpi=36), Settings(gen="sudoku", dpi=36), Settings(gen="kakuro", dpi=36),
                  Settings(gen="nonogram", dpi=36), Settings(gen="spot", dpi=36), Settings(gen="mandala", dpi=36, cbn=True),
                  Settings(gen="mandala", dpi=36, cbn=True, cbn_maths=True), Settings(dpi=36, testpage=True),
                  Settings(gen="maze", dpi=36, booklet=True, pages=4, fold=True)):
            j = jobs.job(State(s), copies=2, answers=True)
            for i in range(j.count):
                j.draw(RecordingCanvas(), i)
            j.amount()
            render.render_view(State(s))
        jobs.job(State(Settings(gen="maze", booklet=True, pages=2, key=True)), copies=2, answer_book=True).amount()
        missing = sorted(m for m in i18n.MISSING if re.search(r"[A-Za-z]{2}", m))
        assert missing == []
        # and the window really is in Spanish
        assert w.menuBar().actions()[0].text() == "&Archivo"
        assert w.sidebar.copies_row.label.text() == "Copias"
    finally:
        w.close()
        w.deleteLater()


def test_spanish_pages_print_spanish_words_and_keep_n_tilde(spanish):
    from inkengine.canvas import RecordingCanvas
    from inkengine.page import PageSpec, Settings, draw_page, geometry, single_page
    from inkengine.patterns import crossword, trace, words
    from inkengine.rng import mulberry32
    s = Settings(gen="words", seed=4, dpi=72, name_line=True)
    c = RecordingCanvas()
    draw_page(c, geometry(s), single_page(s), s)
    texts = [op[1] for op in c.ops if op[0] == "text"]
    assert "Nombre" in texts and "Encuentra estas palabras" in texts
    assert words.clean_word("Pingüino niño") == "PINGUINONIÑO"
    assert crossword.letters("niño") == "NIÑO"
    assert any("Ñ" in "".join(trace.lines_to_trace(mulberry32(k), 10, Settings(trace_source="upper"))) for k in range(40))
    _g, clues, _l = crossword.make_crossword(mulberry32(2), 6, Settings(cross_theme="animals"))
    assert all(re.search(r"[áéíóúñ]|[a-z]", cl) for _n, _w, cl, _r, _c, _a in clues)
    assert {w for _n, w, *_ in clues} <= {w for w, _c in crossword.parse_entries(crossword.THEMES_ES["animals"])}


def test_english_pages_are_as_before():
    """English is the default and draws exactly what it drew (the word search still matches 2.x's recordings
    in tests/test_words.py); a Spanish run doesn't leave anything behind."""
    from inkengine.patterns import words
    assert i18n.LANG == "en"
    assert words.clean_word("Pingüino niño") == "PINGINONIO"
    i18n.set_language("es")
    i18n.set_language("en")
    assert words.clean_word("Pingüino niño") == "PINGINONIO" and i18n.tr("Name") == "Name"


def test_view_language_remembers_the_choice(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp import config
    from inkapp.window import Window
    w = Window("5.0.0", remember=False)
    w.show()
    try:
        assert set(w.lang_actions) == {"en", "es"} and w.lang_actions["en"].isChecked()
        assert w.lang_actions["es"].text() == "Español"
        w.lang_actions["es"].trigger()
        assert config.read("preferences.json")["language"] == "es"
        assert w.sidebar.status.text() == "Reinicia Inkline para usar Español."   # said in Spanish
        assert w.lang_actions["es"].isChecked() and not w.lang_actions["en"].isChecked()
    finally:
        w.close()
        w.deleteLater()
