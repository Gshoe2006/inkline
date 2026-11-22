"""The booklet built page by page, in the window: the page list, the Design section editing the selected page,
and undo."""

import time

import pytest
from PySide6.QtWidgets import QApplication

from inkengine import book


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("4.0.0", remember=False)
    w.show()
    _wait(app, 200)
    yield w
    w.close()
    w.deleteLater()
    _wait(app, 50)


def _wait(app, ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def _set(w, **kw):
    """As the sidebar does it: the control changes the setting, then says which."""
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def _booklet(w, **kw):
    _set(w, booklet=True, pages=6, mix=True, ramp=True, **kw)
    w.sidebar.pages_edit.emit(True)


def _designs(w):
    return [(p.gen, p.seed, p.c) for p in book.book_pages(w.state.settings) if p.kind == "design"]


def test_edit_pages_one_by_one_keeps_the_booklet_as_it_was(win):
    _set(win, booklet=True, pages=6, mix=True, ramp=True)
    before = _designs(win)
    win.sidebar.pages_edit.emit(True)
    s = win.state.settings
    assert len(s.page_list) == 6 and _designs(win) == before
    sb = win.sidebar
    assert sb.page_list.isVisibleTo(sb) and sb.page_list.count() == 6
    assert not sb.pages_row.isVisibleTo(sb) and not sb.mix_check.isVisibleTo(sb) and not sb.pages_edit_btn.isVisibleTo(sb)
    assert sb.page_count.text() == "6 design pages"
    assert win.history.undoText() == "Edit pages one by one"
    win.history.undo()
    assert win.state.settings.page_list == [] and not sb.page_list.isVisibleTo(sb)


def test_the_design_section_edits_the_selected_page_only(win):
    _booklet(win)
    sb = win.sidebar
    sb.book_page_selected.emit(2)
    assert win.state.book_sel == 2 and sb.page_list.currentRow() == 2
    assert win.state.settings.gen == win.state.settings.page_list[2]["gen"]   # Design shows that page
    assert win.state.page == 1 + 2                                            # and the preview turns to it (after the cover)
    assert sb.design_note.isVisibleTo(sb) and "page 3 of 6" in sb.design_note.text()
    others = [dict(p) for i, p in enumerate(win.state.settings.page_list) if i != 2]
    _set(win, gen="kakuro", complexity=9)
    pl = win.state.settings.page_list
    assert pl[2]["gen"] == "kakuro" and pl[2]["complexity"] == 9
    assert [p for i, p in enumerate(pl) if i != 2] == others
    assert "Kakuro · 9/10" in sb.page_list.item(2).toolTip()
    assert win.history.undoText() == "Complexity"
    win.history.undo()
    assert win.state.settings.page_list[2]["complexity"] != 9 and win.state.settings.page_list[2]["gen"] == "kakuro"
    assert win.state.settings.gen == "kakuro"                                 # the controls show the page again


def test_choosing_a_page_is_not_an_edit(win):
    _booklet(win)
    n = win.history.count()
    for i in (3, 0, 5):
        win.sidebar.book_page_selected.emit(i)
        win.schedule()
    win.step_page(-1)
    assert win.history.count() == n
    assert win.state.book_sel == 4   # paging onto a design page selects it


def test_add_move_copy_and_remove_pages_each_undo(win):
    _booklet(win)
    sb, h = win.sidebar, win.history
    pl0 = list(win.state.settings.page_list)
    sb.book_page_added.emit()
    pl = win.state.settings.page_list
    assert len(pl) == 7 and win.state.book_sel == 6 and pl[6]["gen"] == pl0[5]["gen"] and pl[6]["seed"] != pl0[5]["seed"]
    assert h.undoText() == "Add page"
    sb.book_page_copied.emit(0)
    pl = win.state.settings.page_list
    assert len(pl) == 8 and win.state.book_sel == 1 and pl[1]["gen"] == pl[0]["gen"] and pl[1]["seed"] != pl[0]["seed"]
    assert h.undoText() == "Duplicate page"
    sb.book_page_moved.emit(1, 1)
    assert win.state.settings.page_list[2] == pl[1] and win.state.book_sel == 2   # the page being edited moves with it
    assert h.undoText() == "Move page"
    sb.book_page_removed.emit(0)
    assert len(win.state.settings.page_list) == 7 and win.state.book_sel == 1
    assert h.undoText() == "Remove page"
    for _ in range(4):
        h.undo()
    assert win.state.settings.page_list == pl0


def test_new_design_changes_the_selected_page_only(win):
    _booklet(win)
    win.sidebar.book_page_selected.emit(1)
    pl0 = win.state.settings.page_list
    seed0 = win.state.settings.seed
    win.new_design()
    pl = win.state.settings.page_list
    assert pl[1]["seed"] != pl0[1]["seed"] and pl[0] == pl0[0] and pl[2:] == pl0[2:]
    assert win.state.settings.seed == seed0   # the cover art keeps its design
    assert win.sidebar.seed.text() == f"seed {pl[1]['seed']}"
    assert win.history.undoText() == "New design"


def test_the_last_page_cant_be_removed_and_forty_is_the_most(win):
    _booklet(win)
    sb = win.sidebar
    for _ in range(5):
        sb.book_page_removed.emit(0)
    assert len(win.state.settings.page_list) == 1
    sb.book_page_removed.emit(0)
    assert len(win.state.settings.page_list) == 1
    for _ in range(45):
        sb.book_page_added.emit()
    assert len(win.state.settings.page_list) == 40 and not sb.page_add.isEnabled()


def test_back_to_quick_booklet_and_a_preset_start_again_from_the_controls(win):
    _booklet(win)
    win.sidebar.book_page_removed.emit(0)
    win.sidebar.pages_edit.emit(False)
    s = win.state.settings
    assert s.page_list == [] and s.pages == 5 and win.history.undoText() == "Back to quick booklet"
    win.history.undo()
    assert len(win.state.settings.page_list) == 5
    win._apply_preset("b", "Maze booklet with answers")
    assert win.state.settings.page_list == [] and win.state.settings.pages == 10


def test_every_row_has_named_buttons(win):
    _booklet(win)
    from PySide6.QtWidgets import QPushButton
    lst = win.sidebar.page_list
    names = [b.accessibleName() for b in lst.itemWidget(lst.item(0)).findChildren(QPushButton)]
    assert names == ["Move up", "Move down", "Duplicate with a new design", "Remove"]
