"""The first-start tour of the 6.0 window."""

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from inkapp import config, tour


@pytest.fixture
def make_win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))

    def make(remember=True):
        from inkapp.window import Window
        w = Window("6.0.0", remember=remember)
        w.resize(1280, 820)
        w.show()
        QApplication.processEvents()
        return w
    return make


def test_the_first_start_shows_the_tour_once(make_win):
    w = make_win()
    assert w.offer_tour()
    t = w._tour
    assert t.isVisible() and t.outline.isVisible() and "1 OF 5" in t.count.text() and not t.back.isEnabled()
    seen = []
    for _ in range(len(tour.STEPS)):
        name = tour.STEPS[t.i][0]
        target = tour.target(w, name)
        r = QRect(target.mapTo(w, target.rect().topLeft()), target.size())
        assert t.outline.geometry().contains(r.center())       # the outline is round what it's about
        assert w.rect().contains(t.geometry())                 # the card is inside the window
        assert t.height() >= t.layout().totalHeightForWidth(t.width())   # and tall enough for its text
        seen.append(name)
        t.next.click()
    assert seen == ["rail", "gallery", "toolbar", "sidebar", "menu"]
    assert not t.isVisible() and not t.outline.isVisible()     # Done
    assert config.read("preferences.json")["tour_seen"] is True
    assert not make_win().offer_tour()                         # not again


def test_skip_back_and_escape(make_win):
    w = make_win()
    t = w.show_tour(first=True)
    t.next.click()
    t.next.click()
    t.back.click()
    assert t.i == 1 and t.next.text() == "Next"
    QTest.keyClick(w, Qt.Key.Key_Escape)                       # Escape skips, and counts as seen
    assert not t.isVisible() and config.read("preferences.json")["tour_seen"] is True


def test_help_menu_brings_it_back(make_win):
    w = make_win()
    help_menu = next(a.menu() for a in w.menuBar().actions() if a.text() == "&Help")
    item = next(a for a in help_menu.actions() if a.text() == "T&our of the window")
    item.trigger()
    assert w._tour.isVisible()
    w._tour.skip.click()
    assert "tour_seen" not in config.read("preferences.json")  # seen from the menu: the first-start one still due


def test_no_tour_without_remembering(make_win):
    assert not make_win(remember=False).offer_tour()


def test_the_tour_starts_where_the_gallery_is(make_win):
    w = make_win()
    w.sidebar.show_page("print")
    t = w.show_tour()
    t.next.click()                                             # the gallery: on Create
    assert w.sidebar.page_key() == "make" and w.sidebar.gallery.isVisible()


def test_touch_mode_describes_its_own_toolbar():
    from inkapp import tour
    assert "PNG" in tour.step_text("toolbar") and "PNG" not in tour.step_text("toolbar", touch=True)
    assert "Menu" in tour.step_text("menu", touch=True) and tour.step_text("rail", touch=True) == tour.step_text("rail")


def test_the_card_has_its_own_background_with_the_desktops_style(make_win):
    """With View → Use my desktop's style there's no stylesheet: the card still draws an opaque background in the
    desktop's colours (it was see-through, its text on top of the gallery) and the outline its border."""
    from PySide6.QtGui import QColor, QPalette
    app = QApplication.instance()
    sheet, pal = app.styleSheet(), QPalette(app.palette())
    w = make_win()
    try:
        app.setStyleSheet("")
        dark = QPalette(pal)
        dark.setColor(QPalette.ColorRole.Window, QColor(30, 33, 38))
        dark.setColor(QPalette.ColorRole.Highlight, QColor(61, 174, 233))
        app.setPalette(dark)
        item = next(a for a in next(a.menu() for a in w.menuBar().actions() if a.text() == "&Help").actions()
                    if a.text() == "T&our of the window")
        item.trigger()
        QApplication.processEvents()
        card = w._tour
        img = w.grab(card.geometry()).toImage()   # what's on screen there: the card over the gallery
        inside = [img.pixelColor(x, y) for x in (12, card.width() // 2, card.width() - 12) for y in (card.height() - 8,)]
        assert all(c == QColor(30, 33, 38) for c in inside), [c.name() for c in inside]
        edge = img.pixelColor(card.width() // 2, 0)
        assert edge.blue() > 150 and edge.red() < 120, edge.name()   # the highlight border
        out = w._tour.outline.grab().toImage()
        assert out.pixelColor(w._tour.outline.width() // 2, 1).blue() > 150
        w._tour.skip.click()
    finally:
        app.setPalette(pal)
        app.setStyleSheet(sheet)
