"""File → Open recent: photos opened lately, kept between runs in recent.json."""

import json
import os
import time

import pytest

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication


def _wait(ms):
    app = QApplication.instance()
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def _photo(folder, name):
    img = QImage(40, 30, QImage.Format.Format_RGB32)
    img.fill(QColor("#888"))
    path = os.path.join(folder, name)
    img.save(path)
    return path


@pytest.fixture
def make(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path / "config"))
    made = []

    def new(remember=True):
        from inkapp.window import Window
        w = Window("3.0.0", remember=remember)
        made.append(w)
        return w
    yield new
    for w in made:
        w.close()
        w.deleteLater()
    _wait(50)


def _items(w):
    w._fill_recent()
    return [a.text() for a in w.recent_menu.actions() if a.text()]


def test_opened_photos_are_listed_newest_first_and_kept(make, tmp_path):
    w = make()
    assert not w.recent_menu.isEnabled()
    a, b = _photo(tmp_path, "a.png"), _photo(tmp_path, "b & c.png")
    w._load_files([a], False)
    w._load_files([b], False)
    w._load_files([a], False)                    # opened again: moves to the top, not listed twice
    assert w.recent_menu.isEnabled()
    assert _items(w) == ["&1 a.png", "&2 b && c.png", "&Clear list"]
    assert w.recent_menu.actions()[0].statusTip() == os.path.abspath(a)
    again = make()                               # the next run remembers them
    assert again.recent == [os.path.abspath(a), os.path.abspath(b)]


def test_opening_one_loads_it_and_a_missing_one_is_dropped(make, tmp_path):
    w = make()
    msgs = []
    w.status.connect(msgs.append)
    a, b = _photo(tmp_path, "a.png"), _photo(tmp_path, "b.png")
    w._load_files([a], False)
    w._load_files([b], False)
    w.open_recent(os.path.abspath(a))
    assert w.state.photos[0].name == "a.png" and w.recent[0] == os.path.abspath(a)
    os.remove(b)
    w.open_recent(os.path.abspath(b))
    assert msgs[-1] == "Couldn't find b.png. It may have been moved or deleted."
    assert w.recent == [os.path.abspath(a)]


def test_clear_list_and_the_limit(make, tmp_path):
    w = make()
    paths = [_photo(tmp_path, f"p{i}.png") for i in range(12)]
    for p in paths:
        w._load_files([p], False)
    assert len(w.recent) == 10 and w.recent[0] == os.path.abspath(paths[-1])
    assert _items(w)[9] == "1&0 p2.png"
    w.recent_menu.actions()[-1].trigger()        # Clear list
    assert w.recent == [] and not w.recent_menu.isEnabled()
    with open(tmp_path / "config" / "recent.json", encoding="utf-8") as f:
        assert json.load(f) == {"photos": []}


def test_nothing_is_kept_when_not_remembering(make, tmp_path):
    w = make(remember=False)
    w._load_files([_photo(tmp_path, "a.png")], False)
    assert w.recent == [] and not (tmp_path / "config" / "recent.json").exists()
