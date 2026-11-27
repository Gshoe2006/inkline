"""Touch screens (step 2 of Android): larger controls, the menus from the toolbar, and below theme.ONE_COLUMN_WIDTH one
column, where the options page and the preview take turns over a bottom bar."""

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import config, theme


@pytest.fixture
def make_win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    made = []

    def make(remember=False, size=(1280, 820)):
        from inkapp.window import Window
        w = Window("6.0.0", remember=remember)
        w.resize(*size)
        w.show()
        QApplication.processEvents()
        made.append(w)
        return w
    yield make
    for w in made:   # the next test starts with Inkline's desktop look
        w.set_touch(False, save=False)
    theme.TOUCH["on"] = False


def test_when_touch_is_on():
    assert theme.touch_wanted({}, platform="android", env={})
    assert theme.touch_wanted({"touch": True}, platform="linux", env={})
    assert theme.touch_wanted({}, platform="linux", env={"INKLINE_TOUCH": "1"})
    assert not theme.touch_wanted({}, platform="linux", env={}) and not theme.touch_wanted({"touch": "yes"}, "win32", {})


def test_touch_controls_are_as_tall_as_a_rail_button():
    sheet = theme.stylesheet(theme.LIGHT, touch=True)
    assert sheet.startswith(theme.stylesheet(theme.LIGHT, touch=False))   # the desktop look, then larger controls
    assert f"min-height: {theme.TOUCH_TARGET}px" in sheet and "QToolButton#bottomButton" in sheet
    assert "#bottomButton" not in theme.stylesheet(theme.LIGHT, touch=False)
    from inkapp.layout import Rail
    assert all(b.minimumHeight() == theme.TOUCH_TARGET for b in Rail().buttons.values())   # the value it comes from


def test_wide_touch_keeps_the_rail_with_the_menus_in_the_toolbar(make_win):
    w = make_win()
    assert w.menuBar().isVisible() and w.menu_btn.isHidden() and w.bottom.isHidden()
    w.set_touch(True, save=False)
    QApplication.processEvents()
    sb = w.sidebar
    assert not w.menuBar().isVisible() and w.menu_btn.isVisible() and w.turns is None
    assert sb.rail.isVisible() and w.preview.isVisible() and w.bottom.isHidden()
    assert [a.menu() for a in w.menu_btn.panel.actions() if a.menu()] == w._top_menus   # the menu bar's own menus
    for b in (sb.png_btn, sb.svg_btn, sb.brand):   # in the File and View menus instead
        assert b.isHidden()
    assert sb.more_btn.isVisible()   # 1280 px: the toolbar has room for it
    assert sb.pdf_btn.isVisible() and sb.presets_btn.isVisible() and sb.print_btn.isVisible() and sb.keys.isHidden()
    w.set_touch(False, save=False)
    QApplication.processEvents()
    assert w.menuBar().isVisible() and w.menu_btn.isHidden() and sb.png_btn.isVisible() and sb.keys.isVisible()


@pytest.mark.parametrize("size", [(1024, 600), (1280, 800), (1366, 1024)])
def test_a_tablet_sideways_gives_the_page_its_height_and_the_options_the_room_beside_it(make_win, size):
    w = make_win()
    w.set_touch(True, save=False)
    w.resize(*size)
    from conftest import settle
    settle(w)
    QApplication.processEvents()
    sb, page = w.sidebar, w.preview.page
    assert w.turns is None and sb.rail.isVisible()
    assert theme.SIDEBAR_WIDTH < sb.width() <= theme.TOUCH_SIDEBAR_WIDTH   # a portrait page leaves room beside it
    assert w.preview.pad() == theme.TOUCH_STAGE_PAD
    r = page.page_rect()
    assert abs(r.height() - page.height()) < 1   # the page as tall as the preview lets it be
    for b in (sb.presets_btn, sb.new_design, sb.pdf_btn, sb.print_btn, w.menu_btn):   # nothing cut off
        assert b.isVisible() and b.width() >= b.sizeHint().width(), b.text()
    toolbar = sb.toolbar
    assert toolbar.sizeHint().width() <= toolbar.width()
    for b in sb.rail.buttons.values():   # the rail's labels whole
        assert b.fontMetrics().horizontalAdvance(b.text()) <= b.width()
    assert sb.more_btn.isVisible() == (size[0] >= 1280)   # More designs when there's room


def test_a_landscape_page_keeps_the_width_on_a_tablet(make_win):
    w = make_win()
    w.set_touch(True, save=False)
    w.resize(1024, 600)
    from conftest import settle
    w.state.update(orient="landscape")
    w.sidebar.load()
    w._changed("orient")
    settle(w)
    QApplication.processEvents()
    assert w.sidebar.width() < theme.TOUCH_SIDEBAR_WIDTH   # the page needs the room
    w.set_touch(False, save=False)
    QApplication.processEvents()
    assert w.sidebar.width() == theme.SIDEBAR_WIDTH and w.preview.pad() == theme.STAGE_PAD


def test_a_phone_takes_turns_between_the_page_and_the_preview(make_win):
    w = make_win()
    w.set_touch(True, save=False)
    w.resize(360, 760)
    QApplication.processEvents()
    sb = w.sidebar
    assert w.turns is not None and w.bottom.isVisible() and sb.rail.isHidden()
    assert w.turns.currentWidget() is sb and sb.width() == w.width()   # the options, the whole width
    assert sb.presets_btn.isHidden() and w.menu_btn.presets.isVisible() and sb.pdf_btn.isHidden()
    for b in (sb.new_design, sb.print_btn, w.menu_btn):   # what's used most, uncut
        assert b.width() >= b.sizeHint().width(), b.text()
    w.bottom.buttons["preview"].click()
    QApplication.processEvents()
    assert w.turns.currentWidget() is w.preview and w.bottom.buttons["preview"].isChecked()
    w.bottom.buttons["print"].click()
    QApplication.processEvents()
    assert w.turns.currentWidget() is sb and sb.page_key() == "print" and w.bottom.buttons["print"].isChecked()
    w._rail_key("booklet")   # Ctrl+3 too shows the page, and marks it
    QApplication.processEvents()
    assert sb.page_key() == "booklet" and w.bottom.buttons["booklet"].isChecked()
    w.resize(1200, 800)   # turned sideways: the rail again, and the preview beside it
    QApplication.processEvents()
    assert w.turns is None and sb.rail.isVisible() and w.bottom.isHidden() and w.preview.isVisible()
    assert sb.width() >= theme.SIDEBAR_WIDTH and sb.width() < w.width() // 2


def test_the_bottom_bar_follows_what_the_rail_allows(make_win):
    w = make_win()
    w.set_touch(True, save=False)
    w.resize(360, 760)
    QApplication.processEvents()
    w.sidebar.rail.buttons["booklet"].setEnabled(False)
    w.sidebar.synced.emit()
    assert not w.bottom.buttons["booklet"].isEnabled()


def test_presets_open_from_the_menu_on_a_phone(make_win):
    w = make_win()
    w.set_touch(True, save=False)
    w.resize(360, 760)
    QApplication.processEvents()
    w.menu_btn.presets.trigger()
    QApplication.processEvents()
    frame = w.sidebar.presets_btn.frame
    assert frame.isVisible()
    frame.hide()


def test_the_setting_is_kept(make_win):
    from inkapp.settings import SettingsDialog
    w = make_win(remember=True)
    d = SettingsDialog(w)
    assert not d.touch.isChecked()
    d.touch.setChecked(True)
    assert theme.TOUCH["on"] and w.menu_btn.isVisible()
    assert config.read("preferences.json").get("touch") is True
    d.touch.setChecked(False)
    assert not theme.TOUCH["on"] and config.read("preferences.json").get("touch") is False
    d.close()


def test_what_the_independent_check_found(make_win, monkeypatch):
    from inkapp import tour
    w = make_win()
    app = QApplication.instance()
    assert w.bottom not in app.topLevelWidgets()   # hidden inside the window, not a window of its own
    w.set_touch(True, save=False)
    w.resize(360, 760)
    QApplication.processEvents()
    sb = w.sidebar
    assert sb.new_design.height() >= theme.TOUCH_TARGET   # its own padding rule no longer wins over touch's
    assert tour.target(w, "rail") is w.bottom and tour.target(w, "menu") is w.menu_btn
    w.bottom.buttons["preview"].click()
    w.preview.set_info([[("Letter", True), (" 8.5 × 11 in", False)], [("300", True), (" dpi · 2550 × 3300 px", False)],
                        [("ink coverage ", False), ("13.6%", True)]])
    QApplication.processEvents()
    boxes = [w.preview._bar.itemAt(i).widget() for i in range(w.preview._bar.count() - 1)]
    shown = [b for b in boxes if b.isVisible()]
    assert shown and shown == boxes[:len(shown)] and len(shown) < len(boxes)   # the first facts, none cut off
    assert sum(b.width() for b in shown) <= w.preview.width()
    w.resize(1200, 800)
    QApplication.processEvents()
    assert all(b.isVisible() for b in boxes) and tour.target(w, "rail") is sb.rail
    w.sidebar.png_btn.setFocus()
    monkeypatch.setattr(theme, "touch_forced", lambda *a: True)
    from inkapp.settings import SettingsDialog
    d = SettingsDialog(w)
    assert not d.touch.isEnabled()   # on Android it stays on
    d.close()
