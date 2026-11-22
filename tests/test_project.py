"""Project files (.inkline): saving and opening everything being made, photos and booklet pages included."""

import json
import os
import time

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QMessageBox

from inkapp import project
from inkapp.state import State
from inkengine.photo import Photo


def _wait(ms):
    app = QApplication.instance()
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def _img(w=40, h=30, colour="#468"):
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(QColor(colour))
    return img


@pytest.fixture
def answers(monkeypatch):
    """What "Save changes?" is answered with, in order; it records each time it was asked."""
    asked, queue = [], []

    def exec_(box):
        asked.append(box.text())
        return queue.pop(0) if queue else QMessageBox.StandardButton.Cancel
    monkeypatch.setattr(QMessageBox, "exec", exec_)
    return asked, queue


@pytest.fixture
def win(tmp_path, monkeypatch, answers):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path / "config"))
    QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("4.0.0", remember=True)
    w.show()
    _wait(100)
    yield w
    w.history.setClean()   # closing doesn't ask
    w.close()
    w.deleteLater()
    _wait(50)


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_a_project_keeps_settings_pages_and_photos_with_their_crops(tmp_path):
    QApplication.instance() or QApplication([])
    st = State()
    st.update(booklet=True, title="Maya's book", page_list=[{"gen": "maze", "seed": 3, "complexity": 4},
                                                              {"gen": "kakuro", "seed": 9, "complexity": 2}], testpage=True)
    st.photos = [Photo(_img(), rot=90, zoom=150, panx=-20, pany=30, name="cat.png"), Photo(_img(8, 8, "#000"), name="dot.png")]
    st.sel, st.book_sel = 1, 1
    path = str(tmp_path / "book.inkline")
    project.save(path, st, "4.0.0")
    p = project.load(path)
    assert p.settings == st.settings.__class__(**{**st.settings.__dict__, "testpage": False})
    assert (p.sel, p.book_sel) == (1, 1)
    a, b = p.photos
    assert (a.name, a.rot, a.zoom, a.panx, a.pany) == ("cat.png", 90, 150, -20, 30)
    assert a.image.size() == st.photos[0].image.size() and a.image.pixelColor(5, 5) == QColor("#468")
    assert b.image.pixelColor(0, 0) == QColor("#000")
    data = json.load(open(path, encoding="utf-8"))
    assert data["app"] == "Inkline" and data["format"] == project.FORMAT and data["version"] == "4.0.0"
    assert project.title(path) == "book"


@pytest.mark.parametrize("content, why", [
    ("not json at all", "isn't an Inkline project, or it's damaged"),
    ('{"settings": {}}', "isn't an Inkline project"),
    ('{"app": "Inkline", "format": 99, "version": "9.0.0", "settings": {}}', "newer Inkline (9.0.0)"),
    ('{"app": "Inkline", "settings": {}, "photos": [{"png": "bm9wZQ=="}]}', "photo that couldn't be read"),
])
def test_a_file_that_isnt_a_project_says_why(tmp_path, content, why):
    QApplication.instance() or QApplication([])
    path = tmp_path / "x.inkline"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(project.ProjectError, match=why.replace("(", r"\(").replace(")", r"\)")):
        project.load(str(path))


def test_odd_values_are_brought_into_range(tmp_path):
    QApplication.instance() or QApplication([])
    good = project.to_json(State())
    good["photos"] = [{"png": project._png(_img()), "rot": 45, "zoom": 9000, "panx": "x", "pany": None}]
    good["sel"], good["bookSel"] = 7, -3
    p = project.from_json(good)
    ph = p.photos[0]
    assert (ph.rot, ph.zoom, ph.panx, ph.pany) == (0, 400, 0, 0) and (p.sel, p.book_sel) == (0, 0)


def test_save_open_and_the_title(win, tmp_path, monkeypatch):
    assert win.windowTitle() == "Inkline 4.0.0"
    _set(win, gen="maze", complexity=7)
    path = str(tmp_path / "mazes.inkline")
    monkeypatch.setattr("inkapp.window.QFileDialog.getSaveFileName", lambda *a, **k: (path[:-8], ""))
    assert win.save_project_as()
    assert os.path.isfile(path) and win.project_path == path
    assert win.windowTitle() == "mazes[*] — Inkline 4.0.0" and not win.isWindowModified()
    _set(win, complexity=2)
    assert win.isWindowModified()
    win.history.undo()
    assert not win.isWindowModified()   # back to what's saved
    _set(win, complexity=3)
    assert win.save_project() and not win.isWindowModified()
    assert win.recent_projects == [path] and win.recent_projects_menu.isEnabled()
    win.new_project()
    assert win.project_path is None and win.state.settings.gen == "mandala" and win.history.count() == 0
    assert win.open_project(path)
    assert win.state.settings.gen == "maze" and win.state.settings.complexity == 3
    assert win.history.count() == 0 and win.windowTitle().startswith("mazes")


def test_unsaved_changes_ask_first(win, tmp_path, answers):
    asked, queue = answers
    path = str(tmp_path / "a.inkline")
    win._write_project(path)
    _set(win, weight=9)
    queue.append(QMessageBox.StandardButton.Cancel)
    win.new_project()
    assert asked == ["Save the changes to “a”?"] and win.project_path == path and win.state.settings.weight == 9
    queue.append(QMessageBox.StandardButton.Discard)
    win.new_project()
    assert win.project_path is None and win.state.settings.weight != 9
    _set(win, weight=8)
    queue.append(QMessageBox.StandardButton.Save)   # untitled: Save asks where
    import inkapp.window as wmod
    b = str(tmp_path / "b.inkline")
    wmod.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (b, ""))
    try:
        assert win.open_project(path)
    finally:
        del wmod.QFileDialog.getSaveFileName
    assert asked[-1] == "Save your work as a project first?" and os.path.isfile(b)
    assert project.load(b).settings.weight == 8 and win.project_path == path


def test_closing_with_changes_asks_and_can_be_cancelled(win, tmp_path, answers):
    asked, queue = answers
    win._write_project(str(tmp_path / "c.inkline"))
    _set(win, weight=2)
    queue.append(QMessageBox.StandardButton.Cancel)
    assert not win.close() and win.isVisible() and len(asked) == 1


def test_a_missing_or_broken_project_leaves_the_work_alone(win, tmp_path):
    before = win.state.settings
    bad = tmp_path / "bad.inkline"
    bad.write_text("{", encoding="utf-8")
    assert not win.open_project(str(bad))
    assert "Couldn't open bad.inkline: it isn't an Inkline project, or it's damaged." in win.sidebar.status.text()
    win.recent_projects = [str(tmp_path / "gone.inkline")]
    assert not win.open_project(str(tmp_path / "gone.inkline"))
    assert win.recent_projects == [] and win.state.settings is before
