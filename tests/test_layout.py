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
        for key, b in w.sidebar.rail.buttons.items():
            assert b.fontMetrics().horizontalAdvance(b.text()) + 12 <= b.width(), (lang, key, b.text())
    finally:
        i18n.set_language("en")
