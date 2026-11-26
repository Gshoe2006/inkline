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
    for b in (sb.png_btn, sb.svg_btn, sb.more_btn, sb.brand):   # in the File and View menus instead
        assert b.isHidden()
    assert sb.pdf_btn.isVisible() and sb.presets_btn.isVisible() and sb.print_btn.isVisible() and sb.keys.isHidden()
    w.set_touch(False, save=False)
    QApplication.processEvents()
    assert w.menuBar().isVisible() and w.menu_btn.isHidden() and sb.png_btn.isVisible() and sb.keys.isVisible()


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
