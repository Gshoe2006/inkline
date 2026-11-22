"""More designs…: six designs for what New design would change, to choose one."""

import time

import pytest
from PySide6.QtWidgets import QApplication

from inkengine import book


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("4.4.0", remember=False)
    w.show()
    yield w
    w.close()
    w.deleteLater()


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def _drawn(dlg, ms=15000):
    app = QApplication.instance()
    end = time.time() + ms / 1000
    while time.time() < end and not dlg.thumbs.idle:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()


def test_a_single_page_offers_six_designs_and_takes_the_one_chosen(win):
    from inkapp.options import COUNT, Options
    _set(win, gen="maze", complexity=4)
    candidate, chosen, what = win.design_options()
    assert what == "this page"
    dlg = Options(win, candidate, chosen, what)
    _drawn(dlg)
    assert len(dlg.buttons) == COUNT and all(not b.icon().isNull() for b in dlg.buttons)
    pics = {b.icon().pixmap(190, 190).toImage().bits().tobytes() for b in dlg.buttons}
    assert len(pics) == COUNT                                      # six different designs
    seeds = list(dlg.seeds)
    dlg.reroll()
    assert dlg.seeds != seeds                                      # six more
    pick = dlg.seeds[3]
    dlg.buttons[3].click()
    assert win.state.settings.seed == pick and win.history.undoText() == "New design"
    assert dlg.result() == dlg.DialogCode.Accepted


def test_a_quick_booklet_offers_booklets_seen_on_the_page_shown(win):
    _set(win, gen="maze", booklet=True, pages=4, mix=True, ramp=False)
    win.step_page(1)
    win.step_page(1)                                               # cover, page 1, page 2 (a woven tiles page?)
    candidate, chosen, what = win.design_options()
    shown = book.book_pages(win.state.settings)[win.state.page]
    s2, spec = candidate(123)
    assert spec.gen == shown.gen and spec.idx == shown.idx and s2.seed == 123
    assert what == f"the whole booklet (each shows page {win.state.page + 1})"
    win.state.update(page_seeds={1: 99})
    chosen(456)
    assert win.state.settings.seed == 456 and win.state.settings.page_seeds == {}


def test_a_page_by_page_booklet_offers_designs_for_the_page_being_edited(win):
    _set(win, gen="maze", booklet=True, pages=3, mix=True, ramp=False)
    win.sidebar.pages_edit.emit(True)
    win.sidebar.book_page_selected.emit(2)
    pl0 = win.state.settings.page_list
    candidate, chosen, what = win.design_options()
    assert what == "page 3"
    s2, spec = candidate(777)
    assert spec.seed == 777 and spec.gen == pl0[2]["gen"]
    chosen(777)
    pl = win.state.settings.page_list
    assert pl[2]["seed"] == 777 and pl[:2] == pl0[:2] and win.history.undoText() == "New design"
    win.history.undo()
    assert win.state.settings.page_list == pl0


def test_nothing_is_offered_for_a_photo(win):
    win._set_mode("convert")
    assert win.design_options() is None
    win.more_designs()                                             # does nothing, opens nothing


def test_the_button_and_menu_open_it(win, monkeypatch):
    from inkapp import options
    opened = []
    monkeypatch.setattr(options.Options, "exec", lambda dlg: opened.append(dlg) or 0)
    win.sidebar.more_btn.click()
    acts = {a.text().replace("&", ""): a for m in win.menuBar().actions() for a in m.menu().actions()}
    acts["More designs…"].trigger()
    assert len(opened) == 2 and acts["More designs…"].shortcut().toString() == "Ctrl+Shift+N"


def test_enter_chooses_the_design_with_the_focus(win):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent
    from inkapp.options import Options
    dlg = Options(win, *win.design_options())
    dlg.show()
    dlg.buttons[2].setFocus()
    QApplication.instance().processEvents()
    pick = dlg.seeds[2]
    QApplication.sendEvent(dlg, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    assert win.state.settings.seed == pick


def test_buttons_say_drawing_until_their_picture_arrives(win):
    from inkapp.options import Options
    dlg = Options(win, *win.design_options())
    assert all(b.text() == "Drawing…" for b in dlg.buttons)
    _drawn(dlg)
    assert all(b.text() == "" and not b.icon().isNull() for b in dlg.buttons)
    from PySide6.QtCore import Qt
    assert dlg.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)   # nothing left behind, drawing


def test_a_posters_design_is_shown_on_one_page_and_fold_shows_the_side_in_view(win):
    _set(win, poster=True, grid="3x2")
    candidate, _chosen, what = win.design_options()
    s2, spec = candidate(5)
    assert not s2.poster and not s2.fold and what == "the poster's design (shown on one page)"
    _set(win, poster=False, booklet=True, pages=6, mix=True, fold=True)
    win.step_page(1)                                               # sheet 1's back: pages 2 and 15 (padded)
    candidate, _chosen, _what = win.design_options()
    from inkengine import book as bk
    v_pages = bk.fold_pages(bk.book_pages(win.state.settings))
    left, right = bk.fold_order(len(v_pages))[win.state.page]
    first = next(p for p in (v_pages[left], v_pages[right]) if p.kind == "design")
    assert candidate(9)[1].idx == first.idx


def test_new_design_is_one_step_named_so_even_with_swapped_pages(win):
    _set(win, booklet=True, pages=4)
    win.state.update(page_seeds={1: 42})
    win.sidebar.load()
    win._changed("page_seeds")
    win.new_design()
    assert win.history.undoText() == "New design"
