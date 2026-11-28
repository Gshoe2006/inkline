"""Start-up: building the window doesn't do the expensive things twice (docs/performance.md, "Start-up").

Timings are too noisy to test on a shared machine, so these check what made start-up slow: restyling every widget
again with the look the application already had, and re-parenting the finished window's widgets."""

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

from inkapp import theme


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    yield a
    theme.CHOSEN["name"] = "system"
    theme.TOUCH["on"] = False
    theme.DESKTOP["on"] = False
    theme.apply(a, dark=False)


@pytest.fixture
def restyles(monkeypatch):
    """Every time the application's style or stylesheet is set: each restyles every widget there is."""
    calls = []
    sheet, style = QApplication.setStyleSheet, QApplication.setStyle
    monkeypatch.setattr(QApplication, "setStyleSheet", lambda a, s: (calls.append("sheet"), sheet(a, s))[1])
    monkeypatch.setattr(QApplication, "setStyle", staticmethod(lambda s: (calls.append("style"), style(s))[1]))
    return calls


def test_the_same_look_again_changes_nothing(app, restyles):
    theme.apply(app, dark=False)
    restyles.clear()
    theme.apply(app, dark=False)
    assert restyles == []


def test_a_different_look_is_still_applied(app, restyles):
    theme.apply(app, dark=False)
    restyles.clear()
    theme.apply(app, dark=True)                       # dark
    assert app.styleSheet() == theme.stylesheet(theme.DARK) and "sheet" in restyles
    theme.TOUCH["on"] = True                          # touch sizes are part of the stylesheet
    restyles.clear()
    theme.apply(app, dark=True)
    assert app.styleSheet() == theme.stylesheet(theme.DARK, touch=True) and "sheet" in restyles
    theme.TOUCH["on"] = False
    app.setStyleSheet("")                             # changed behind theme's back: put right again
    restyles.clear()
    theme.apply(app, dark=True)
    assert app.styleSheet() == theme.stylesheet(theme.DARK)


def test_the_desktop_style_again_changes_nothing(app, restyles):
    theme.remember_desktop(app)
    theme.DESKTOP["on"] = True
    theme.apply(app)
    restyles.clear()
    theme.apply(app)
    assert restyles == []


def test_building_the_window_restyles_nothing(app, restyles, tmp_path, monkeypatch):
    """main() styles the application before building the window; the window's touch set-up asks for the same
    look again, which used to restyle all of its thousand widgets (half the time it took to build)."""
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    theme.apply(app)
    restyles.clear()
    w = Window("test", remember=False)
    assert restyles == []
    w.close()


def test_the_central_widget_is_placed_before_it_is_filled(app, tmp_path, monkeypatch):
    """Putting a widget into the window re-polishes everything inside it: the central widget goes in empty."""
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from PySide6.QtWidgets import QWidget
    from inkapp.window import Window
    sizes = []
    real = QMainWindow.setCentralWidget
    monkeypatch.setattr(QMainWindow, "setCentralWidget",
                        lambda win, c: (sizes.append(len(c.findChildren(QWidget))), real(win, c))[1])
    w = Window("test", remember=False)
    assert sizes == [0]
    w.close()
