"""6.0's layout: the rail chooses a page of options, the folds take turns, the gallery picks a pattern by sight, and
the toolbar holds what's used most."""

import time

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import config, layout


@pytest.fixture
def make_win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))

    def make(remember=False, size=(1280, 820)):
        from inkapp.window import Window
        w = Window("6.0.0", remember=remember)
        w.resize(*size)
        w.show()
        QApplication.processEvents()
        return w
    return make


def spin(seconds=0.3):
    end = time.time() + seconds
    while time.time() < end:
        QApplication.processEvents()
        time.sleep(0.01)


def test_the_rail_chooses_the_page_and_the_mode(make_win):
    w = make_win()
    sb = w.sidebar
    assert sb.page_key() == "make" and sb.rail.buttons["make"].isChecked()
    sb.rail.buttons["print"].click()
    assert sb.page_key() == "print" and w.state.settings.mode == "make"
    sb.rail.buttons["photo"].click()                         # Photo is the other mode
    spin()
    assert w.state.settings.mode == "convert" and sb.page_key() == "photo"
    assert not sb.rail.buttons["booklet"].isEnabled()        # a photo book is on the Photo page
    sb.rail.buttons["make"].click()
    spin()
    assert w.state.settings.mode == "make" and sb.page_key() == "make" and sb.rail.buttons["booklet"].isEnabled()
    sb.rail.buttons["booklet"].click()
    assert sb.page_key() == "booklet"
    w.history.undo()                                         # back to the photo: its page follows the mode
    spin()
    assert w.state.settings.mode == "convert" and sb.page_key() == "photo"


@pytest.mark.parametrize("lang", ["en", "de"])
def test_every_page_fits_without_scrolling(make_win, lang):
    """At 820 px high: Create with a pattern's options, Booklet edited page by page, Print with copies open,
    Photo, Poster."""
    from inkengine import i18n
    try:
        i18n.set_language(lang)
        w = make_win()
        sb = w.sidebar
        w.state.update(gen="maths")
        sb.load()
        w._changed("gen")
        cases = [("make", None)]
        w.state.update(booklet=True)
        sb.load()
        w._changed("booklet")
        sb.pages_edit.emit(True)
        cases += [("booklet", None), ("print", "paper"), ("print", "copies"), ("print", "text"), ("poster", None)]
        for page, fold in cases:
            sb.show_page(page)
            if fold:
                sb.folds[fold].set_open(True)
            spin(0.2)
            col, view = sb._columns[page], sb._scrolls[page].viewport()
            assert col.sizeHint().height() <= view.height(), (lang, page, fold, col.sizeHint().height(), view.height())
        sb.rail.buttons["photo"].click()
        spin(0.3)
        assert sb._columns["photo"].sizeHint().height() <= sb._scrolls["photo"].viewport().height()
    finally:
        i18n.set_language("en")


def test_the_gallery_picks_and_remembers_patterns(make_win):
    w = make_win(remember=True)
    sb = w.sidebar
    assert sb.gallery.gens == layout.GALLERY_START
    i = layout.GALLERY_START.index("bingo")
    sb.gallery.buttons[i].click()
    spin()
    assert w.state.settings.gen == "bingo" and sb.gallery.gens == layout.GALLERY_START   # nothing moves under the cursor
    assert sb.gallery.buttons[i].isChecked()
    sb.gallery.buttons[i].click()                            # clicked again: still the one chosen
    assert sb.gallery.buttons[i].isChecked()
    sb.gen.set_value("sudoku")                               # the Pattern list has the rest: a new one comes first
    spin()
    assert sb.gallery.gens[:2] == ["sudoku", "bingo"] and len(sb.gallery.gens) == layout.GALLERY
    assert config.read("preferences.json")["recent_patterns"][:2] == ["sudoku", "bingo"]
    again = make_win(remember=True)                          # kept for the next start
    assert again.sidebar.gallery.gens[:2] == ["sudoku", "bingo"]
    spin(3)                                                  # its pictures arrive
    assert any(not b.icon().isNull() for b in again.sidebar.gallery.buttons)


def test_recent_patterns():
    known = {"maze": 1, "words": 1, "mandala": 1, "maths": 1, "crossword": 1, "bingo": 1, "sudoku": 1}
    assert layout.recent_patterns([], known) == layout.GALLERY_START
    assert layout.recent_patterns(["sudoku", "gone", "maze"], known)[:3] == ["sudoku", "maze", "mandala"]


def test_folds_take_turns_and_reveal_opens_the_way(make_win):
    w = make_win()
    sb = w.sidebar
    f = sb.folds
    assert f["paper"].is_open() and not f["copies"].is_open() and not f["text"].is_open()
    f["copies"].set_open(True)
    assert f["copies"].is_open() and not f["paper"].is_open()
    sb.show_page("make")
    sb.reveal(sb.margin_hint.parentWidget())                 # something in the Paper fold
    assert sb.page_key() == "print" and f["paper"].is_open() and not f["copies"].is_open()
    assert sb.shown(sb.copies_row)                           # shown once its fold opens, though it's shut now
    w.state.update(booklet=True, pages=4)
    sb.load()
    w._changed("booklet")
    sb.copies.setText("3")
    assert sb.shown(sb.copies_answer_book) is False or sb.shown(sb.copies_row)


def test_the_toolbar_and_status_line(make_win):
    w = make_win()
    sb = w.sidebar
    for b in (sb.presets_btn, sb.new_design, sb.more_btn, sb.pdf_btn, sb.png_btn, sb.svg_btn, sb.print_btn):
        assert sb.toolbar.isAncestorOf(b)
    assert sb.presets_btn.panel is sb.presets_panel and sb.presets_panel.isAncestorOf(sb.preset_name)
    assert sb.statusbar.isAncestorOf(sb.status) and sb.statusbar.isAncestorOf(sb.keys)
    seed = w.state.settings.seed
    sb.new_design.click()
    assert w.state.settings.seed != seed
    w._msg("Hello")
    assert sb.status.text() == "Hello"


def test_arrow_keys_on_the_rail_dont_change_the_mode(make_win):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w = make_win()
    b = w.sidebar.rail.buttons["make"]
    b.setFocus()
    for key in (Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_Down):
        QTest.keyClick(b, key)
        spin(0.05)
    assert w.state.settings.mode == "make" and w.sidebar.page_key() == "make"
    w.sidebar.rail.buttons["make"].click()                   # clicking the one chosen keeps it chosen
    assert w.sidebar.rail.buttons["make"].isChecked()


def test_the_presets_panel_opens_for_a_name(make_win):
    w = make_win()
    sb = w.sidebar
    assert not sb.presets_btn.frame.isVisible()
    w._save_preset("")                                       # Save with no name: the panel opens at the name
    spin()
    assert sb.presets_btn.frame.isVisible() and sb.presets_btn.frame.isAncestorOf(sb.preset_name)
    assert sb.preset_name.focusPolicy() != sb.preset_name.focusPolicy().NoFocus
    focusable = [c for c in (sb.preset, sb.preset_del, sb.preset_name) if c.focusPolicy() & c.focusPolicy().TabFocus]
    assert len(focusable) == 3                               # Tab reaches each control in the panel
    sb.presets_btn.close()
    assert not sb.presets_btn.frame.isVisible()


def test_new_design_is_for_made_up_designs(make_win):
    w = make_win()
    sb = w.sidebar
    assert sb.new_design.isEnabled() and sb.more_btn.isEnabled()
    sb.rail.buttons["photo"].click()
    spin()
    assert not sb.new_design.isEnabled() and not sb.more_btn.isEnabled()


def test_a_wrong_page_range_shows_the_field(make_win):
    w = make_win()
    sb = w.sidebar
    w.state.update(booklet=True, pages=3)
    sb.load()
    w._changed("booklet")
    sb.only_pages.setText("99")
    sb.show_page("make")
    sb.folds["copies"].set_open(True)
    w.print_()
    assert sb.page_key() == "print" and sb.folds["paper"].is_open()


@pytest.mark.parametrize("lang", ["en", "es", "fr", "pt", "de"])
def test_the_rail_labels_fit(make_win, lang):
    from inkengine import i18n
    try:
        i18n.set_language(lang)
        w = make_win()
        for font in (None, "DejaVu Sans"):   # Inkline's own, and a wider one (CI's)
            if font:
                from PySide6.QtGui import QFont
                for b in w.sidebar.rail.buttons.values():
                    b.setFont(QFont(font, 12))
                w.sidebar.rail.fit_width()
            for key, b in w.sidebar.rail.buttons.items():
                assert b.fontMetrics().horizontalAdvance(b.text()) + 12 <= b.width(), (lang, font, key, b.text())
    finally:
        i18n.set_language("en")


def test_all_patterns_by_kind_and_search(make_win):
    from inkengine.patterns import GENERATORS
    from inkapp.sidebar import GEN_OPTIONS
    w = make_win()
    grouped = [g for _k, gens in layout.GROUPS for g in gens]
    assert sorted(grouped) == sorted(GENERATORS)             # every pattern, each once
    d = layout.show_all_patterns(w, __import__("inkengine.patterns", fromlist=["x"]).NAMES, dict(GEN_OPTIONS),
                                 "maze", w.sidebar.gen.set_value)
    grid = d.grid
    assert set(grid.buttons) == set(GENERATORS) and grid.buttons["maze"].isChecked()
    assert grid.filter("maze") == 1 and grid.buttons["maze"].isVisibleTo(grid)
    assert grid.filter("colour") >= 2 and not grid.empty.isVisibleTo(grid)
    assert grid.filter("zzzz") == 0 and grid.empty.isVisibleTo(grid)
    assert grid.filter("") == len(GENERATORS)
    grid.buttons["bingo"].click()
    assert w.state.settings.gen == "bingo" and d.result() == d.DialogCode.Accepted
    spin(3)
    assert sum(not b.icon().isNull() for b in grid.buttons.values()) > 0   # pictures arrive


def test_searching_in_another_language():
    from inkengine import i18n
    try:
        i18n.set_language("es")
        names = {"maze": "Maze"}
        assert layout.matches("maze", "laberinto", names, {}) and layout.matches("maze", "maze", names, {})
        assert layout.matches("maze", "LABERÍNTO", names, {})   # accents and capitals don't matter
        assert not layout.matches("maze", "sudoku", names, {})
    finally:
        i18n.set_language("en")


def test_changing_a_booklet_page_on_the_booklet_page(make_win):
    w = make_win()
    sb = w.sidebar
    w.state.update(booklet=True, pages=4)
    sb.load()
    w._changed("booklet")
    sb.pages_edit.emit(True)
    sb.reveal(sb.page_list)
    assert sb.shown(sb.page_change_btn)
    sb.page_list.setCurrentRow(2)
    spin()
    sb.page_change_btn.click()
    assert sb.page_key() == "booklet" and sb.page_editor.isVisibleTo(sb) and not sb.book_list_view.isVisibleTo(sb)
    assert sb.page_editor.isAncestorOf(sb.gen) and "PAGE 3" in sb.page_editing.text()
    sb.gen.set_value("words")                                # changes page 3, here on the Booklet page
    spin()
    assert w.state.settings.page_list[2]["gen"] == "words" and "WORD SEARCH" in sb.page_editing.text()
    assert sb._columns["booklet"].sizeHint().height() <= sb._scrolls["booklet"].viewport().height()
    sb.page_back.click()                                     # the list again; Create's controls go home
    assert sb.book_list_view.isVisibleTo(sb) and sb._columns["make"].isAncestorOf(sb.gen)
    sb.edit_page()
    sb.rail.buttons["make"].click()                          # Create while changing a page: its controls follow
    assert sb._columns["make"].isAncestorOf(sb.gen) and sb.page_editor.isHidden()
    sb.edit_page()
    sb.pages_edit.emit(False)                                # back to a quick booklet: nothing to change
    spin()
    assert sb._columns["make"].isAncestorOf(sb.gen) and sb.page_editor.isHidden()


def test_double_click_or_enter_changes_the_page(make_win):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w = make_win()
    sb = w.sidebar
    w.state.update(booklet=True, pages=3)
    sb.load()
    w._changed("booklet")
    sb.pages_edit.emit(True)
    sb.reveal(sb.page_list)
    sb.page_list.setFocus()
    QTest.keyClick(sb.page_list, Qt.Key.Key_Down)            # arrows only move through the list
    assert sb.page_editor.isHidden()
    QTest.keyClick(sb.page_list, Qt.Key.Key_Return)
    assert not sb.page_editor.isHidden()
    sb.back_to_pages()
    sb.page_list.itemDoubleClicked.emit(sb.page_list.item(0))
    assert not sb.page_editor.isHidden()


def test_ctrl_1_to_5_choose_the_rail(make_win):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w = make_win()
    sb = w.sidebar
    assert sb.rail.buttons["print"].toolTip() == "Print (Ctrl+5)" and sb.rail.buttons["make"].toolTip() == "Create (Ctrl+1)"
    mod = Qt.KeyboardModifier.ControlModifier
    QTest.keyClick(w, Qt.Key.Key_5, mod)
    assert sb.page_key() == "print"
    QTest.keyClick(w, Qt.Key.Key_3, mod)
    assert sb.page_key() == "booklet"
    QTest.keyClick(w, Qt.Key.Key_2, mod)
    spin()
    assert w.state.settings.mode == "convert" and sb.page_key() == "photo"
    msgs = []
    w._msg = msgs.append
    QTest.keyClick(w, Qt.Key.Key_3, mod)                     # no Booklet for a photo: it says where
    assert sb.page_key() == "photo" and "Photo page" in msgs[-1]
    QTest.keyClick(w, Qt.Key.Key_1, mod)
    spin()
    assert w.state.settings.mode == "make" and sb.page_key() == "make"
