"""Getting unsaved work back after Inkline closes unexpectedly."""

import os
import time

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QMessageBox

from inkapp import config, project, recovery
from inkapp.state import State
from inkengine.page import Settings
from inkengine.photo import Photo

ENDED = "endedsession"          # a session that's over: nobody holds its lock


def _wait(ms=100):
    app = QApplication.instance()
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def _photo():
    img = QImage(30, 20, QImage.Format.Format_ARGB32)
    img.fill(QColor("#468"))
    return Photo(img, name="cat.png")


@pytest.fixture
def make(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path / "config"))
    QApplication.instance() or QApplication([])
    made = []

    def new(remember=True):
        from inkapp.window import Window
        w = Window("4.2.0", remember=remember)
        w.show()
        made.append(w)
        return w
    yield new
    for w in made:
        w.history.setClean()
        w.close()
        w.deleteLater()
    _wait(50)


def _settle(w):
    end = time.time() + 5
    while time.time() < end and not w.keeper.idle:
        _wait(20)


def _answer(monkeypatch, recover):
    def exec_(box):
        box._chosen = next(b for b in box.buttons() if (b.text() == "Recover") == recover
                           and box.buttonRole(b) != QMessageBox.ButtonRole.InvalidRole)
        return 0
    monkeypatch.setattr(QMessageBox, "exec", exec_)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: getattr(box, "_chosen", None))


def test_unsaved_photos_are_copied_and_the_copy_goes_when_saved_or_closed(make, tmp_path):
    w = make()
    w.add_photos([_photo()], False)
    assert w._keep_timer.isActive()          # the first unsaved change starts the minute
    w._keep_copy()
    _settle(w)
    copy = recovery.path_for()
    assert os.path.isfile(copy)
    p, data = project.read(copy)
    assert [x.name for x in p.photos] == ["cat.png"] and data["recovery"]["project"] is None
    w._write_project(str(tmp_path / "saved.inkline"))
    _settle(w)
    assert not os.path.exists(copy)          # saved: nothing to recover
    w.state.photos[0].rot = 90
    w.schedule()
    w._keep_copy()
    _settle(w)
    assert project.read(copy)[1]["recovery"]["project"] == str(tmp_path / "saved.inkline")
    w.close()
    assert not os.path.exists(copy)          # closed properly


def test_settings_alone_arent_copied(make):
    w = make()
    w.state.update(weight=9)
    w.sidebar.load()
    w._changed("weight")
    w._keep_copy()
    _settle(w)
    assert not os.path.exists(recovery.path_for())   # remembered in last-settings.json already


def test_a_window_that_remembers_nothing_keeps_no_copy(make):
    w = make(remember=False)
    w.add_photos([_photo()], False)
    assert w.keeper is None and not w._keep_timer.isActive()


def _leftover(session=ENDED, source=None):
    st = State(Settings(booklet=True, page_list=[{"gen": "maze", "seed": 4, "complexity": 6}] * 3))
    st.photos = [_photo()]
    os.makedirs(config.config_dir(), exist_ok=True)
    path = recovery.path_for(session)
    project.save(path, st, "4.2.0", {"recovery": {"project": source, "saved": time.time()}})
    return path


def test_work_left_by_a_crash_is_offered_and_recovered(make, monkeypatch, tmp_path):
    w = make()
    src = str(tmp_path / "maya.inkline")
    path = _leftover(source=src)
    shown = []
    real = QMessageBox.setInformativeText
    monkeypatch.setattr(QMessageBox, "setInformativeText", lambda box, t: (shown.append(t), real(box, t)))
    _answer(monkeypatch, recover=True)
    assert w.offer_recovery()
    assert len(w.state.settings.page_list) == 3 and [p.name for p in w.state.photos] == ["cat.png"]
    assert w.project_path == src and w.isWindowModified()      # recovered, not saved
    assert not os.path.exists(path)
    assert shown[0].endswith(" · maya · 3 pages · 1 photo")
    assert w.sidebar.status.text() == "Recovered your unsaved work. Save it as a project to keep it."
    _settle(w)
    assert os.path.isfile(recovery.path_for())                  # this session keeps it now


def test_discarding_it_leaves_the_work_alone(make, monkeypatch):
    w = make()
    path = _leftover()
    _answer(monkeypatch, recover=False)
    assert not w.offer_recovery()
    assert w.state.settings.page_list == [] and not os.path.exists(path)


def test_another_running_inkline_isnt_mistaken_for_a_crash(make, monkeypatch):
    import fcntl
    w = make()
    alive = _leftover(session="othersession")
    lock = open(recovery._lock_path(alive), "w")    # another Inkline, running: it holds its lock
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    asked = []
    monkeypatch.setattr(QMessageBox, "exec", lambda box: asked.append(1) or 0)
    try:
        assert not w.offer_recovery() and asked == [] and os.path.exists(alive)
    finally:
        lock.close()
    _answer(monkeypatch, recover=False)
    w.offer_recovery()                               # once it has closed without tidying up, it's offered
    assert not os.path.exists(alive) and not os.path.exists(recovery._lock_path(alive))


def test_a_damaged_copy_is_removed_without_asking(make, monkeypatch):
    w = make()
    os.makedirs(config.config_dir(), exist_ok=True)
    bad = recovery.path_for(ENDED)
    with open(bad, "w") as f:
        f.write("{")
    asked = []
    monkeypatch.setattr(QMessageBox, "exec", lambda box: asked.append(1) or 0)
    assert not w.offer_recovery() and asked == [] and not os.path.exists(bad)


def test_closing_properly_leaves_no_files(make):
    import glob
    w = make()
    w.add_photos([_photo()], False)
    w._keep_copy()
    _settle(w)
    assert glob.glob(os.path.join(config.config_dir(), "recovery-*"))
    w.history.setClean()
    w.close()
    _settle(w)
    assert glob.glob(os.path.join(config.config_dir(), "recovery-*")) == []


def test_stray_lock_files_from_ended_sessions_are_tidied(make):
    w = make()
    os.makedirs(config.config_dir(), exist_ok=True)
    stray = os.path.join(config.config_dir(), "recovery-gone.lock")
    open(stray, "w").close()
    assert recovery.leftovers() == [] and not os.path.exists(stray)
    assert os.path.exists(recovery._lock_path(recovery.path_for()))   # this session's own stays while it runs
