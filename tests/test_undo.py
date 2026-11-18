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


def _type(app, field, text):
    from PySide6.QtTest import QTest
    QTest.keyClicks(field, text)
    _wait(app, 50)


def test_typing_is_one_step_until_the_cursor_leaves_the_field(win):
    app, h = QApplication.instance(), win.history
    _set(win, gen="name")
    _wait(app, 100)
    n = h.count()
    field = win.sidebar._binds["title"][0]
    field.setFocus()
    _wait(app, 50)
    _type(app, field, "Ra")
    _wait(app, 1700)
    _type(app, field, "in")
    assert h.count() == n + 1 and h.undoText() == "Title"
    win.sidebar._binds["frame"][0].setFocus()
    field.setFocus()
    _wait(app, 50)
    _type(app, field, "y")
    assert h.count() == n + 2       # back in the field: a new step


def test_changes_made_while_a_field_has_the_cursor_are_not_typing(win):
    app, h = QApplication.instance(), win.history
    _set(win, gen="name")
    field = win.sidebar._binds["title"][0]
    field.setFocus()
    _wait(app, 50)
    n = h.count()
    win.new_design()
    win.new_design()
    assert h.count() - n == 2       # Ctrl+N twice is two steps, though the cursor is in Title
    on = win.state.settings.frame
    _set(win, frame=not on)
    _set(win, frame=on)
    assert h.count() - n == 4       # and the Border clicks stay separate steps


def test_history_lists_the_steps_and_jumps_to_one(win):
    app, h = QApplication.instance(), win.history
    from PySide6.QtWidgets import QUndoView
    start, frame = win.state.settings.weight, win.state.settings.frame
    _set(win, weight=start + 1)
    _set(win, frame=not frame)
    _set(win, frame=frame)          # three steps: clicks never join
    win.show_history()
    _wait(app, 50)
    view = win._history_view.findChild(QUndoView)
    assert view.model().rowCount() == 4          # "Start" and the three steps
    view.setCurrentIndex(view.model().index(1, 0))
    _wait(app, 50)
    assert h.index() == 1 and win.state.settings.weight == start + 1 and win.state.settings.frame == frame
    view.setCurrentIndex(view.model().index(0, 0))
    _wait(app, 50)
    assert win.state.settings.weight == start
    win.show_history()                           # opened again: the same window, not a second one
    assert len(win.findChildren(QUndoView)) == 1
