"""What's new after an update, and copying booklet pages through the clipboard."""

import json
import os

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from inkapp import config, whatsnew

LOG = """# Changelog

## 4.5.0 - 2026-11-23

New five.

### What's new

- **Five.** Yes.

### Upgrading

```sh
## not a heading
sh inkline-4.5.0.run
```

### Found a problem?

Tell us.

## 4.4.0 - 2026-11-22

### What's new

- **Four.**

### Fixed

- A fix.

## 4.3.0

### What's new

- **Three.**
"""


def test_sections_keep_what_changed_and_drop_how_to_upgrade():
    got = whatsnew.sections(LOG)
    assert [v for v, _ in got] == ["4.5.0", "4.4.0", "4.3.0"]
    five = got[0][1]
    assert "**Five.**" in five and "## What's new" in five
    assert "Upgrading" not in five and "inkline-4.5.0.run" not in five and "Tell us" not in five
    assert "## Fixed" in got[1][1]
    assert [v for v, _ in whatsnew.sections(LOG, (4, 3, 0), (4, 5, 0))] == ["4.5.0", "4.4.0"]


def test_notes_since_the_version_last_used(monkeypatch):
    monkeypatch.setattr(whatsnew, "changelog_text", lambda: LOG)
    both = whatsnew.notes("4.5.0", "4.3.0")
    assert both.index("# Inkline 4.5.0") < both.index("# Inkline 4.4.0") and "Three" not in both
    assert "Four" not in whatsnew.notes("4.5.0")              # Help → What's new: this version's
    assert whatsnew.notes("dev") == "" and whatsnew.notes("9.9.9") == ""


def test_due_only_after_an_update(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    assert whatsnew.due("4.5.0", True) is None                # a first install: nothing, but remembered
    assert whatsnew.due("4.5.0", True) is None                # the same version again
    assert whatsnew.due("4.6.0", True) == "4.5.0"             # updated: what's new since 4.5.0
    assert whatsnew.due("dev", True) is None and whatsnew.due("4.7.0", False) is None
    os.remove(tmp_path / "seen-version.json")
    config.write("last-settings.json", {"gen": "maze"}, "Settings")
    assert whatsnew.due("4.6.0", True) == ""                  # updated from before this note: this version's


def test_the_changelog_ships_with_every_package():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    read = lambda *p: open(os.path.join(root, *p), encoding="utf-8").read()
    assert "CHANGELOG.md" in read("packaging", "build.sh")
    assert "/usr/share/inkline/CHANGELOG.md" in read("packaging", "arch", "PKGBUILD")
    assert '"$TMP/CHANGELOG.md"' in read("packaging", "installer-stub.sh")
    assert "VERSION CHANGELOG.md /app/lib/inkline/" in read("packaging", "flatpak", "io.github.gshoe2006.Inkline.yml")
    assert whatsnew.changelog_text().startswith("# Changelog")


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("4.5.0", remember=False)
    w.show()
    yield w
    w.close()
    w.deleteLater()


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_help_shows_whats_new(win, monkeypatch):
    shown = []
    monkeypatch.setattr(whatsnew, "changelog_text", lambda: LOG)
    monkeypatch.setattr(whatsnew.WhatsNew, "exec", lambda d: shown.append(d.windowTitle()) or 0)
    acts = {a.text().replace("&", ""): a for m in win.menuBar().actions() for a in m.menu().actions()}
    acts["What's new"].trigger()
    assert shown == ["What's new in Inkline 4.5.0"]


def _booklet(w, n=3):
    _set(w, gen="maze", booklet=True, pages=n, mix=True, ramp=False)
    w.sidebar.pages_edit.emit(True)


def test_pages_copy_and_paste_between_booklets(win):
    _booklet(win)
    win.sidebar.book_page_selected.emit(1)
    page = dict(win.state.settings.page_list[1])
    win.copy_pages()
    md = QGuiApplication.clipboard().mimeData()
    assert md.hasFormat("application/x-inkline-pages") and md.text().startswith("Inkline booklet pages: ")
    win.sidebar.book_page_selected.emit(2)
    win.paste()                                                # Ctrl+V: pages, not a picture
    pl = win.state.settings.page_list
    assert len(pl) == 4 and pl[3] == page and win.state.book_sel == 3     # after the selected page, as copied
    assert win.history.undoText() == "Paste page"
    win.copy_pages(everything=True)
    win.paste()
    assert len(win.state.settings.page_list) == 8 and win.history.undoText() == "Paste pages"
    win.history.undo()
    assert len(win.state.settings.page_list) == 4


def test_pasting_needs_a_booklet_built_page_by_page_and_room(win):
    _booklet(win, 3)
    win.copy_pages(everything=True)
    _set(win, booklet=False)
    win.paste()
    assert win.sidebar.status.text().startswith("To paste pages, turn on Make a multi-page booklet")
    _set(win, booklet=True)
    for _ in range(36):
        win.sidebar.book_page_added.emit()
    assert len(win.state.settings.page_list) == 39
    win.paste()
    assert len(win.state.settings.page_list) == 40
    assert win.sidebar.status.text() == "Pasted 1 of 3 pages: a booklet holds up to 40."


def test_odd_clipboard_contents_paste_nothing(win):
    _booklet(win)
    for raw in (b"nope", json.dumps({"pages": [{"gen": "unicorn"}, 5]}).encode()):
        win.paste_pages(raw)
        assert len(win.state.settings.page_list) == 3 and win.sidebar.status.text() == "There are no pages to paste."


def test_closing_leaves_copied_pages_as_plain_text(win):
    _booklet(win)
    win.copy_pages()
    win.close()                                  # the window's own data would crash PySide as the app quits
    md = QGuiApplication.clipboard().mimeData()
    assert not md.hasFormat("application/x-inkline-pages") and md.text().startswith("Inkline booklet pages: ")
