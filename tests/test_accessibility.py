"""Accessibility: every control has a name a screen reader can say (as Qt's accessibility derives it: its own
accessible name, its text, or for a list its label), Tab goes rail → options → toolbar → preview, focus is visible on
every kind of control, and the gallery, the booklet's page list and the photo list work from the keyboard."""

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAccessible, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSlider, QAbstractSpinBox, QApplication,
                               QComboBox, QLabel, QLineEdit, QScrollBar, QWidget)

from inkengine.i18n import tr
from conftest import settle

CONTROLS = (QAbstractButton, QAbstractSlider, QAbstractSpinBox, QComboBox, QLineEdit, QAbstractItemView)


def _qt_own(w):
    """Qt's own parts of a control (a scroll bar, a combo box's pop-up list, a line edit's clear button, the menu
    bar's overflow button): Qt names those itself, or they're never reached on their own."""
    p = w.parentWidget()
    return (isinstance(w, QScrollBar) or w.objectName().startswith("qt_") or isinstance(p, QLineEdit)
            or (p is not None and isinstance(p.parentWidget(), QComboBox)))


def unnamed(root):
    """The controls in root that a screen reader would have no name for, described for the failure message."""
    buddies = {lab.buddy() for lab in root.findChildren(QLabel) if lab.buddy() is not None and lab.text()}
    out = []
    for w in root.findChildren(QWidget):
        if not isinstance(w, CONTROLS) or _qt_own(w):
            continue
        if isinstance(w, QComboBox):   # Qt names a list by its current entry: it needs its own name, or a label's
            ok = bool(w.accessibleName()) or w in buddies
        else:
            face = QAccessible.queryAccessibleInterface(w)
            ok = face is not None and bool(face.text(QAccessible.Text.Name).strip())
        if not ok:
            out.append(f"{type(w).__name__} {w.objectName()!r} tip={w.toolTip()!r} in {type(w.parentWidget()).__name__}")
    return out


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("6.0.0", remember=False)
    w.resize(1280, 820)
    w.show()
    settle(w)
    yield w
    from inkapp import theme
    w.set_touch(False, save=False)
    theme.TOUCH["on"] = False


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def _photo(name):
    from inkengine.photo import Photo
    img = QImage(60, 40, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.gray)
    return Photo(img, name=name)


def test_every_control_in_the_window_has_a_name(win):
    win.sidebar.build_all()   # every pattern's options, built otherwise only once their pattern is chosen
    assert unnamed(win) == []
    # a booklet built page by page (its rows' buttons), a photo book (its photos' buttons), and a touch screen
    _set(win, booklet=True, pages=3)
    win.sidebar.pages_edit.emit(True)
    settle(win)
    assert win.sidebar.page_list.count() == 3 and unnamed(win) == []
    _set(win, booklet=False)
    win._set_mode("convert")
    win.add_photos([_photo("a.png"), _photo("b.png")], True)
    settle(win)
    assert win.sidebar.photo_list.count() >= 2 and unnamed(win) == []
    win.set_touch(True, save=False)
    win.resize(600, 800)   # one column, with the bottom bar
    QApplication.processEvents()
    assert win.bottom.isVisible() and unnamed(win) == []


def test_lists_and_icon_buttons_are_named_by_their_label_not_their_value(win):
    sb = win.sidebar
    assert sb.rail.buttons["make"].accessibleName() == "" and sb.rail.buttons["make"].text() == tr("Create")
    # a list: its label's text as its name (Windows and macOS say that) and its label as a buddy (Linux's screen
    # readers say the label it's "labelled by", Qt there naming a list by its current entry)
    gen = sb._binds["gen"][0]
    assert gen.accessibleName() == tr("Pattern")
    face = QAccessible.queryAccessibleInterface(gen)
    labels = [r[0].text(QAccessible.Text.Name) for r in face.relations(QAccessible.Relation.Label)]
    assert tr("Pattern") in labels
    assert win.menu_btn.accessibleName() == tr("Menu") and sb.presets_btn.accessibleName() == tr("Presets")
    assert sb.photo_list.accessibleName() == tr("Photo book") and sb.page_list.accessibleName() == tr("Booklet pages")
    # a tooltip that explains a button is its description too
    face = QAccessible.queryAccessibleInterface(sb.svg_btn)
    assert face.text(QAccessible.Text.Description) == sb.svg_btn.toolTip() != ""


def test_settings_and_all_patterns_have_names(win):
    from inkapp.layout import show_all_patterns
    from inkapp.settings import SettingsDialog
    from inkengine.patterns import NAMES
    d = SettingsDialog(win)
    assert unnamed(d) == []
    a = show_all_patterns(win, NAMES, {}, "maze", lambda g: None)
    assert unnamed(a) == []
    assert all(b.accessibleName() for b in a.grid.buttons.values())


def test_the_preview_says_which_page_it_shows(win):
    page = win.preview.page
    assert page.accessibleName() == tr("Page preview")
    from inkengine.patterns import NAMES
    assert page.accessibleDescription() == tr(NAMES[win.state.settings.gen])
    _set(win, gen="maze", booklet=True, pages=3)
    win.step_page(1)
    settle(win)
    n = win._view.count   # with its cover and answer pages
    assert page.accessibleDescription() == tr("{page}: {what}").format(page=tr("Page {i} of {n}").format(i=2, n=n),
                                                                     what=tr(NAMES["maze"]))


def _tab_chain(w):
    """The widgets Tab goes through, in order, from the first."""
    out, seen = [], set()
    x = w.nextInFocusChain()
    while x is not w and id(x) not in seen:
        seen.add(id(x))
        if x.focusPolicy() & Qt.FocusPolicy.TabFocus and x.isVisibleTo(w) and x.isEnabled() and x.window() is w:
            out.append(x)
        x = x.nextInFocusChain()
    return out


def test_tab_goes_rail_then_options_then_toolbar_then_preview(win):
    sb, chain = win.sidebar, _tab_chain(win)
    rail = chain.index(sb.rail.buttons["make"])
    options = min(chain.index(b) for b in sb.gallery.buttons)
    toolbar = [chain.index(b) for b in (sb.presets_btn, sb.new_design, sb.more_btn, sb.pdf_btn, sb.png_btn,
                                        sb.svg_btn, sb.print_btn)]
    preview = chain.index(win.preview.page)
    assert rail < options < toolbar[0] and toolbar == sorted(toolbar) and toolbar[-1] < preview
    assert max(chain.index(b) for b in sb.rail.buttons.values()) < options


def test_focus_shows_on_every_kind_of_control():
    from inkapp import theme
    for touch in (False, True):
        sheet = theme.stylesheet(theme.LIGHT, touch=touch)
        for selector in ("QPushButton:focus", "QComboBox:focus", "QLineEdit:focus", "QCheckBox:focus",
                         "QSlider::handle:horizontal:focus", "QToolButton#railButton:focus",
                         "QToolButton#galleryItem:focus", "QToolButton#toolbarMenu:focus", "QToolButton#foldHead:focus",
                         "QToolButton#designOption:focus", "QListWidget#pageList:focus", "QListWidget#photoList:focus"):
            assert selector in sheet, selector
    assert "QToolButton#bottomButton:focus" in theme.stylesheet(theme.LIGHT, touch=True)


def test_the_preview_shows_its_focus_and_zooms_from_the_keyboard(win):
    page = win.preview.page
    before = page.grab().toImage()
    page.setFocus(Qt.FocusReason.TabFocusReason)
    QApplication.processEvents()
    if not page.hasFocus():
        pytest.skip("no keyboard focus offscreen here")
    assert page.grab().toImage() != before   # the outline
    QTest.keyClick(page, Qt.Key.Key_Plus)
    assert page.zoomed()
    shown = page.visible_rect()
    QTest.keyClick(page, Qt.Key.Key_Down)   # moves the zoomed view
    assert page.visible_rect().y() > shown.y()
    QTest.keyClick(page, Qt.Key.Key_Plus)
    QTest.keyClick(page, Qt.Key.Key_Plus)
    shown = page.visible_rect()
    QTest.keyClick(page, Qt.Key.Key_Right)   # ... rather than turning a page
    assert page.visible_rect().x() > shown.x()
    QTest.keyClick(page, Qt.Key.Key_0)
    assert not page.zoomed()


def test_the_gallery_from_the_keyboard(win):
    sb = win.sidebar
    cards = sb.gallery.buttons
    cards[0].setFocus()
    QTest.keyClick(cards[0], Qt.Key.Key_Right)
    assert QApplication.focusWidget() is cards[1]
    QTest.keyClick(cards[1], Qt.Key.Key_Down)
    assert QApplication.focusWidget() is cards[4]
    QTest.keyClick(cards[4], Qt.Key.Key_Left)
    assert QApplication.focusWidget() is cards[3]
    want = sb.gallery.gens[3]
    QTest.keyClick(cards[3], Qt.Key.Key_Return)
    settle(win)
    assert win.state.settings.gen == want


def test_all_patterns_from_the_keyboard(win):
    from inkapp.layout import show_all_patterns
    from inkengine.patterns import NAMES
    picked = []
    d = show_all_patterns(win, NAMES, {}, "maze", picked.append)
    d.show()
    QApplication.processEvents()
    g = d.grid
    QTest.keyClicks(g.search, "maze")
    QTest.keyClick(g.search, Qt.Key.Key_Down)
    assert QApplication.focusWidget() is g.buttons["maze"]
    QTest.keyClick(g.buttons["maze"], Qt.Key.Key_Up)   # back to the search box
    assert QApplication.focusWidget() is g.search
    g.search.clear()
    QTest.keyClick(g.search, Qt.Key.Key_Down)
    first = QApplication.focusWidget()
    QTest.keyClick(first, Qt.Key.Key_Right)
    second = QApplication.focusWidget()
    assert first is g.buttons["mandala"] and second is g.buttons["truchet"]
    QTest.keyClick(second, Qt.Key.Key_Down)   # the next row of the same kind
    assert QApplication.focusWidget() is g.buttons["symmetry"]
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Enter)
    assert picked == ["symmetry"]
    d2 = show_all_patterns(win, NAMES, {}, "maze", picked.append)
    d2.show()
    QTest.keyClicks(d2.grid.search, "sudoku")
    QTest.keyClick(d2.grid.search, Qt.Key.Key_Return)   # Enter in the search box: the first match
    assert picked == ["symmetry", "sudoku"]


def test_the_photo_list_from_the_keyboard(win):
    win._set_mode("convert")
    _set(win, photobook=True)
    win.add_photos([_photo("a.png"), _photo("b.png"), _photo("c.png")], False)
    settle(win)
    lst = win.sidebar.photo_list
    names = lambda: [p.name for p in win.state.photos]   # noqa: E731
    assert names()[-3:] == ["a.png", "b.png", "c.png"]
    n = len(names())
    lst.setCurrentRow(n - 1)
    lst.setFocus()
    QTest.keyClick(lst, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    assert names()[-2:] == ["c.png", "b.png"]
    lst.setCurrentRow(n - 1)
    QTest.keyClick(lst, Qt.Key.Key_Delete)
    assert names()[-2:] == ["a.png", "c.png"] and len(names()) == n - 1
    tip = [b.toolTip() for b in lst.itemWidget(lst.item(0)).findChildren(QAbstractButton)]
    assert any("(Delete)" in t for t in tip) and any("(Alt+↑)" in t for t in tip)


def test_high_contrast_is_a_theme_to_choose(win):
    from inkapp import theme
    assert "contrast" in theme.EXTRA_THEMES and theme.THEME_NAMES["contrast"] == "High contrast"
    t = theme.THEMES["contrast"]
    assert (t.ink, t.bg) == ("#000000", "#ffffff")
    win.offer_theme("contrast", True)
    win.set_theme("contrast")
    try:
        assert theme.tokens() is t
        assert f"border: 2px solid {t.accent}" in QApplication.instance().styleSheet()   # the focus border, in its accent
    finally:
        win.set_theme("system")
        win.offer_theme("contrast", False)
