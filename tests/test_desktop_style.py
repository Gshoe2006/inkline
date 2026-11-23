"""View → Use my desktop's style: the desktop's own look instead of Inkline's, where this copy can load it."""

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import config, theme


@pytest.fixture
def desktop(monkeypatch):
    """As if Qt had found a desktop style (Qt's own "Windows" style stands in for Breeze here)."""
    monkeypatch.setattr(theme, "PLAIN", set())
    monkeypatch.setitem(theme.DESKTOP, "style", "Windows")
    monkeypatch.setitem(theme.DESKTOP, "palette", None)
    monkeypatch.setitem(theme.DESKTOP, "on", False)
    yield
    theme.DESKTOP["on"] = False
    theme.apply(QApplication.instance(), dark=False)


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])

    def make(remember=True):
        from inkapp.window import Window
        w = Window("4.7.0", remember=remember)
        w.show()
        made.append(w)
        return w
    made = []
    yield make
    for w in made:
        w.close()
        w.deleteLater()


def test_switching_to_the_desktops_style_and_back(desktop, win):
    app = QApplication.instance()
    theme.apply(app, dark=False)
    w = win()
    assert app.styleSheet() and w.act_desktop.isEnabled() and not w.act_desktop.isChecked()
    w.act_desktop.trigger()
    assert w.act_desktop.isChecked() and app.styleSheet() == "" and app.style().name().lower() == "windows"
    assert w.sidebar.status.text() == "Using your desktop's style (Windows)."
    assert config.read("preferences.json") == {"desktop_style": True}       # remembered for the next start
    w.act_desktop.trigger()
    assert app.styleSheet()                                                  # Inkline's own look again
    assert config.read("preferences.json") == {"desktop_style": False}


def test_switching_light_and_dark_keeps_the_desktops_style(desktop):
    app = QApplication.instance()
    theme.use_desktop(app, True)
    theme.apply(app, dark=True)                                              # as follow_system does
    assert app.styleSheet() == "" and app.style().name().lower() == "windows"


def test_unavailable_where_this_copy_cant_load_the_desktops_style(win, monkeypatch):
    monkeypatch.setitem(theme.DESKTOP, "style", "fusion")                   # a bundled Qt finds only Fusion
    assert theme.desktop_style_name() == ""
    w = win()
    assert not w.act_desktop.isEnabled() and "brings its own Qt" in w.act_desktop.toolTip()


def test_a_window_that_remembers_nothing_saves_no_preference(desktop, win, tmp_path):
    w = win(remember=False)
    w.act_desktop.trigger()
    assert not (tmp_path / "preferences.json").exists()
