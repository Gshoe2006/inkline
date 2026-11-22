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


def test_the_design_section_leaves_the_pages_alone_while_the_booklet_isnt_made(win):
    _booklet(win)
    pl0 = win.state.settings.page_list
    _set(win, booklet=False)
    _set(win, gen="maze", complexity=9)          # the single page
    assert win.state.settings.page_list == pl0
    _set(win, booklet=True)
    _set(win, poster=True)
    _set(win, complexity=2)
    assert win.state.settings.page_list == pl0
    _set(win, poster=False, booklet=True)
    assert win.state.settings.gen == pl0[0]["gen"] and win.state.settings.complexity == pl0[0]["complexity"]
    assert win.history.undoText() != ""


def _thumbs_done(w, ms=8000):
    app = QApplication.instance()
    end = time.time() + ms / 1000
    while time.time() < end and not w.sidebar.thumbs.idle:
        app.processEvents()
        time.sleep(0.01)
    _wait(app, 50)


def _thumb(w, i):
    return w.sidebar._thumb_rows[i].pixmap()


def test_each_row_shows_its_own_page(win):
    _booklet(win)
    _thumbs_done(win)
    from inkapp import thumbs
    pix = [_thumb(win, i) for i in range(6)]
    assert all(not p.isNull() for p in pix)
    w, h = thumbs.thumb_size(win.state.settings)
    assert (pix[0].width(), pix[0].height()) == (w, h) and h == thumbs.THUMB_H and w < h   # a portrait page
    assert len({p.toImage().bits().tobytes() for p in pix}) == 6                         # six different pictures
    first = pix[0].toImage()
    win.sidebar.book_page_moved.emit(0, 1)                    # moved: the picture moves with it, from the cache
    assert win.sidebar.thumbs.idle and _thumb(win, 1).toImage() == first


def test_a_change_draws_that_page_again(win):
    _booklet(win)
    _thumbs_done(win)
    before = [_thumb(win, i).toImage() for i in range(6)]
    win.sidebar.book_page_selected.emit(2)
    win.new_design()
    _thumbs_done(win)
    after = [_thumb(win, i).toImage() for i in range(6)]
    assert after[2] != before[2] and [a for i, a in enumerate(after) if i != 2] == [b for i, b in enumerate(before) if i != 2]
    _set(win, frame=True)                                     # the booklet's border is drawn on every page
    _thumbs_done(win)
    assert all(_thumb(win, i).toImage() != after[i] for i in range(6))
    _set(win, orient="landscape")
    _thumbs_done(win)
    assert _thumb(win, 0).width() > _thumb(win, 0).height()


def test_thumbnails_are_darker_than_the_page_scaled_down(monkeypatch):
    from inkapp import thumbs
    import numpy as np
    from inkengine.page import Settings

    def ink(img):
        a = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).reshape(img.height(), img.bytesPerLine())
        return 255 - a[:, :img.width()].mean()
    s = Settings(booklet=True, page_list=[{"gen": "truchet", "seed": 1, "complexity": 3}])
    spec = [p for p in book.book_pages(s) if p.kind == "design"][0]
    shown = ink(thumbs.draw(s, spec))
    monkeypatch.setattr(thumbs, "THICKEN", 1)
    monkeypatch.setattr(thumbs, "DARKEN", 1)
    assert shown > 2 * ink(thumbs.draw(s, spec))   # thin lines show as more than a faint grey


def test_pictures_fit_their_slot_and_come_back_after_convert(win):
    _booklet(win)
    _thumbs_done(win)
    slot = win.sidebar._thumb_rows[0]
    assert slot.width() <= 36 and slot.height() <= 36
    win._set_mode("convert")
    win.sidebar.fill_pages()
    win._set_mode("make")
    _thumbs_done(win)
    assert all(not _thumb(win, i).isNull() for i in range(6))


def test_fold_and_staple_pages_are_half_sheets(win):
    from inkapp import thumbs
    _booklet(win)
    _set(win, orient="landscape")
    _thumbs_done(win)
    assert _thumb(win, 0).width() > _thumb(win, 0).height()
    _set(win, fold=True)                       # half a landscape sheet: a portrait page, whatever the orientation
    _thumbs_done(win)
    assert _thumb(win, 0).width() < _thumb(win, 0).height() == thumbs.THUMB_H


def test_dragging_a_page_moves_it_any_distance(win):
    _booklet(win)
    sb, h = win.sidebar, win.history
    pl0 = list(win.state.settings.page_list)
    sb.book_page_selected.emit(1)
    lst = sb.page_list
    assert lst.count() == 6                                # choosing a page doesn't rebuild the list (a drag goes on)
    lst.setCurrentRow(5)
    lst.moved.emit(5, 0)                                   # dropped at the top
    pl = win.state.settings.page_list
    assert pl == [pl0[5]] + pl0[:5] and h.undoText() == "Move page"
    assert win.state.book_sel == 0 and lst.currentRow() == 0   # the dragged page is the one being edited
    h.undo()
    assert win.state.settings.page_list == pl0


def test_where_a_drop_lands(win):
    _booklet(win)
    lst = win.sidebar.page_list
    lst.show()
    r0, r2 = lst.visualRect(lst.model().index(0, 0)), lst.visualRect(lst.model().index(2, 0))
    assert lst.drop_row(r0.top() + 2) == 0 and lst.drop_row(r0.bottom() - 2) == 1
    assert lst.drop_row(r2.center().y() + 3) == 3
    assert lst.drop_row(10000) == lst.count()


def test_a_drop_on_its_own_place_changes_nothing(win):
    _booklet(win)
    lst, n = win.sidebar.page_list, win.history.count()
    got = []
    lst.moved.connect(lambda i, j: got.append((i, j)))
    lst.setCurrentRow(2)
    for dst in (2, 3):                                     # just above or just below itself
        to = dst - 1 if dst > 2 else dst
        if to != 2:
            lst.moved.emit(2, to)
    assert got == [] and win.history.count() == n


def test_a_real_drop_event_moves_the_page(win):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QDropEvent
    _booklet(win)
    lst = win.sidebar.page_list
    lst.show()
    pl0 = list(win.state.settings.page_list)
    lst.setCurrentRow(0)
    data = lst.model().mimeData([lst.model().index(0, 0)])
    below_row_3 = lst.visualRect(lst.model().index(3, 0)).bottom() - 2
    e = QDropEvent(QPointF(20, below_row_3), Qt.DropAction.MoveAction, data, Qt.MouseButton.LeftButton,
                   Qt.KeyboardModifier.NoModifier)
    lst.dropEvent(e)
    assert win.state.settings.page_list == pl0[1:4] + [pl0[0]] + pl0[4:]
    assert lst.count() == 6 and lst.currentRow() == 3     # filled again from the settings, the page still selected


def test_undo_shows_the_page_the_list_highlights(win):
    _booklet(win)
    win.sidebar.book_page_selected.emit(0)
    _set(win, complexity=9)                      # an edit to page 1
    win.sidebar.book_page_selected.emit(4)       # then look at page 5
    win.history.undo()
    assert win.state.book_sel == 0 and win.sidebar.page_list.currentRow() == 0
    assert win.state.page == 1                   # the preview turned back to page 1 (after the cover)


def test_a_booklet_word_search_page_says_which_words_didnt_fit():
    from inkapp.render import render_view
    from inkapp.state import State
    from inkengine.page import Settings
    long_words = "mum, dad, extraordinarily, pizza"
    st = State(Settings(booklet=True, cover=True, page_list=[
        {"gen": "maze", "seed": 1, "complexity": 3},
        {"gen": "words", "seed": 2, "complexity": 1, "ws_theme": "custom", "ws_words": long_words}]))
    st.page = 2                                            # cover, maze, then the word search
    assert "Left out: EXTRAORDINARILY" in render_view(st).note
    st.page = 1
    assert render_view(st).note == ""                     # the maze has nothing to say
    single = State(Settings(gen="words", complexity=1, ws_theme="custom", ws_words=long_words))
    assert "Left out: EXTRAORDINARILY" in render_view(single).note   # a single page, as before


def test_rows_tell_pages_of_one_pattern_apart(win):
    _set(win, gen="words", booklet=True, pages=3, mix=False, ramp=False)
    win.sidebar.pages_edit.emit(True)
    win.sidebar.book_page_selected.emit(0)
    _set(win, ws_theme="custom")
    _set(win, ws_words="mum, dad, pizza")
    win.sidebar.book_page_selected.emit(1)
    _set(win, ws_theme="ocean")
    lst = win.sidebar.page_list
    tips = [lst.item(i).toolTip() for i in range(3)]
    assert tips[0].startswith("1. Word search · Your words · ") and tips[0].endswith("Words: mum, dad, pizza")
    assert tips[1].startswith("2. Word search · Ocean · ") and tips[2].startswith("3. Word search · Animals · ")
    pl = win.state.settings.page_list
    assert (pl[0]["ws_theme"], pl[0]["ws_words"], pl[1]["ws_theme"]) == ("custom", "mum, dad, pizza", "ocean")


def test_each_puzzle_can_leave_its_answer_out(win):
    _set(win, gen="maze", booklet=True, pages=3, mix=False, ramp=False, key=True)
    win.sidebar.pages_edit.emit(True)
    sb, h = win.sidebar, win.history
    sb.book_page_selected.emit(1)
    chk = sb.page_answer_check
    assert chk.isVisibleTo(sb) and chk.isChecked()
    chk.setChecked(False)                                  # as a click does
    pl = win.state.settings.page_list
    assert pl[1]["answer"] is False and "answer" not in pl[0]
    answered = [d.idx for p in book.book_pages(win.state.settings) if p.kind == "answers" for d in p.items]
    assert answered == [0, 2]
    assert sb.page_list.item(1).toolTip().endswith("· no answer") and h.undoText() == "Leave its answer out"
    sb.book_page_selected.emit(0)
    assert chk.isChecked()                                 # the other page still has its answer
    sb.book_page_selected.emit(1)
    assert not chk.isChecked()
    h.undo()
    assert "answer" not in win.state.settings.page_list[1] and chk.isChecked()


def test_the_switch_shows_only_where_there_is_an_answer(win):
    _set(win, gen="mandala", booklet=True, pages=2, mix=False, ramp=False, key=True, cbn=False)
    win.sidebar.pages_edit.emit(True)
    sb = win.sidebar
    assert not sb.page_answer_check.isVisibleTo(sb)        # a plain colouring page has no answer
    _set(win, cbn=True)
    assert sb.page_answer_check.isVisibleTo(sb)            # colour by number has a shaded one
    _set(win, key=False)
    assert not sb.page_answer_check.isVisibleTo(sb)        # no answer pages at all
    _set(win, booklet=False)
    _set(win, key=True)
    assert not sb.page_answer_check.isVisibleTo(sb)        # a single page
