"""Edit → Undo and Redo in the window: what makes one step, and that undoing puts everything back."""

import time

import pytest

from PySide6.QtWidgets import QApplication


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("3.0.0", remember=False)
    w.show()
    _wait(app, 300)
    yield w
    w.close()
    w.deleteLater()
    _wait(app, 100)


def _wait(app, ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_a_change_is_one_step_and_undo_puts_it_back(win):
    h = win.history
    before = win.state.settings.weight
    _set(win, weight=before + 1)
    assert h.count() == 1 and h.undoText() == "Line weight"
    h.undo()
    assert win.state.settings.weight == before
    h.redo()
    assert win.state.settings.weight == before + 1


def test_clicks_never_join(win):
    h = win.history
    on = win.state.settings.frame
    _set(win, frame=not on)
    _set(win, frame=on)
    assert h.count() == 2          # on and off again: two steps, each one undoable
    h.undo()
    assert win.state.settings.frame == (not on)


def test_slider_keys_join_when_quick_and_vanish_when_back(win):
    h = win.history
    start = win.state.settings.complexity
    win._timed = True
    _set(win, complexity=start + 1)
    win._timed = True
    _set(win, complexity=start + 2)
    assert h.count() == 1
    win._timed = True
    _set(win, complexity=start + 1)
    win._timed = True
    _set(win, complexity=start)
    assert h.count() == 0          # back where it started: no step left


def test_a_preset_that_changes_nothing_does_not_name_the_next_step(win):
    h = win.history
    win._apply_preset("b", "Start fresh (defaults)")
    win._apply_preset("b", "Start fresh (defaults)")
    _set(win, weight=win.state.settings.weight + 1)
    assert h.undoText() == "Line weight"
