"""Print and Save PDF of several copies of a single page, each with its own design or alike."""

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import jobs
from inkapp.state import State
from inkengine.page import Settings


def _drawn(job):
    """The seeds and specs each page of a job draws."""
    seen = []
    real = jobs.draw_page
    jobs.draw_page = lambda ctx, g, spec, s: seen.append((s.seed, spec.gen))
    try:
        for i in range(job.count):
            job.draw(None, i)
    finally:
        jobs.draw_page = real
    return seen


def test_copies_each_with_their_own_design_the_first_being_the_one_shown():
    st = State(Settings(gen="maze", seed=1234))
    j = jobs.job(st, copies=25, vary=True)
    assert j.count == 25 and j.label == "copies" and j.amount() == "25 copies" and j.name.endswith("-25-designs")
    seeds = [s for s, _ in _drawn(j)]
    assert seeds[0] == 1234 and len(set(seeds)) == 25                      # all different, the first as shown
    assert seeds == [s for s, _ in _drawn(jobs.job(st, copies=25, vary=True))]   # the same set again


def test_copies_alike_and_photos_always_alike():
    st = State(Settings(gen="maze", seed=7))
    assert [s for s, _ in _drawn(jobs.job(st, copies=3, vary=False))] == [7, 7, 7]
    photo = State(Settings(mode="convert", seed=7))
    assert {s for s, _ in _drawn(jobs.job(photo, copies=4, vary=True))} == {7}
    assert jobs.job(st, copies=1).count == 1 and jobs.job(st, copies=500).count == jobs.MAX_COPIES


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("4.7.0", remember=False)
    w.show()
    yield w
    w.close()
    w.deleteLater()


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_the_field_shows_for_single_pages_and_says_what_will_print(win):
    sb = win.sidebar
    assert sb.copies_row.isVisibleTo(sb) and not sb.copies_hint.isVisibleTo(sb)
    sb.copies.setText("25")
    assert sb.copies_vary.isVisibleTo(sb)
    assert sb.copies_hint.text() == "Print and Save PDF make 25 copies, each with its own design (the first is the one shown)."
    sb.copies_vary.setChecked(False)
    assert sb.copies_hint.text().endswith("all alike.")
    from PySide6.QtTest import QTest
    sb.copies.clear()
    QTest.keyClicks(sb.copies, "ab7c")                                     # the field takes digits only
    assert sb.copies.text() == "7" and sb.copies_count() == 7
    _set(win, booklet=True)                                                # a booklet: Print or save only instead
    assert not sb.copies_row.isVisibleTo(sb)
    _set(win, booklet=False, poster=True)
    assert not sb.copies_row.isVisibleTo(sb)


def test_save_pdf_and_print_use_the_copies(win, monkeypatch):
    sb = win.sidebar
    sb.copies.setText("12")
    asked = []
    monkeypatch.setattr(win, "_ask_path", lambda *a: asked.append(a) or None)
    win.save("pdf")
    assert asked[0][1].endswith("-12-designs")
    got = []
    real = jobs.job
    monkeypatch.setattr(jobs, "job", lambda *a, **k: got.append(a) or real(*a, **k))
    from PySide6.QtPrintSupport import QPrintDialog
    monkeypatch.setattr(QPrintDialog, "exec", lambda d: QPrintDialog.DialogCode.Rejected)
    win.print_()
    assert got[-1][2] == 12 and got[-1][3] is True
    _set(win, booklet=True)
    win.print_()
    assert got[-1][2] == 1                                                 # copies are for single pages only


def test_pages_that_cant_vary_print_alike_and_the_hint_says_when_some_repeat(win):
    assert jobs.copies_vary(Settings(gen="name", name_bg="none"))[0] is False
    assert jobs.copies_vary(Settings(gen="name", name_bg="flow")) == (True, "")
    assert jobs.copies_vary(Settings(gen="maze")) == (True, "")
    assert jobs.copies_vary(Settings(gen="dots"))[1].startswith("Dot-to-dot has only a handful")
    assert jobs.copies_vary(Settings(gen="nonogram", complexity=1))[1] and not jobs.copies_vary(Settings(gen="nonogram", complexity=2))[1]
    plain = State(Settings(gen="name", name_bg="none", seed=5))
    j = jobs.job(plain, copies=3, vary=True)
    assert j.name.endswith("-3-copies") and [s for s, _ in _drawn(j)] == [5, 5, 5]
    sb = win.sidebar
    _set(win, gen="name", name_bg="none")
    sb.copies.setText("4")
    assert not sb.copies_vary.isVisibleTo(sb)                              # nothing to vary: no switch for it
    assert sb.copies_hint.text().startswith("Print and Save PDF make 4 copies, all alike. A name page")
    _set(win, gen="dots")
    assert sb.copies_vary.isVisibleTo(sb) and "some copies repeat." in sb.copies_hint.text()
    sb.copies_vary.setChecked(False)
    assert "all alike." in sb.copies_hint.text() and "repeat" not in sb.copies_hint.text()   # alike anyway


def test_a_number_out_of_range_says_what_will_print_and_is_put_right_on_leaving(win):
    sb = win.sidebar
    sb.copies.setText("101")
    assert sb.copies_count() == 100
    assert sb.copies_hint.isVisibleTo(sb) and sb.copies_hint.text().startswith("Copies go from 1 to 100. Print and Save PDF make 100 copies")
    sb.copies.setText("0")
    assert sb.copies_hint.text() == "Copies go from 1 to 100. Print and Save PDF make 1 copy."
    assert sb.copies.validator().fixup("000") == "1" and sb.copies.validator().fixup("250") == "100"
    sb.copies.setText("")
    assert not sb.copies_hint.isVisibleTo(sb)


def test_print_says_copies_and_the_print_dialogs_own_copies(win, monkeypatch):
    from PySide6.QtPrintSupport import QPrintDialog
    sb = win.sidebar
    sb.copies.setText("25")
    told = []
    monkeypatch.setattr(win, "_start", lambda j, dev, done, failed: told.append(done))

    def accept(d, times):
        d.printer().setCopyCount(times)
        return QPrintDialog.DialogCode.Accepted
    monkeypatch.setattr(QPrintDialog, "exec", lambda d: accept(d, 1))
    win.print_()
    assert told[-1] == "Sent 25 copies to the printer."
    monkeypatch.setattr(QPrintDialog, "exec", lambda d: accept(d, 3))
    win.print_()
    assert told[-1] == "Sent 25 copies to the printer, 3 times over (Copies in the print dialog)."
    sb.copies.setText("")
    win.print_()
    assert told[-1] == "Sent to the printer, 3 copies (Copies in the print dialog)."


def test_answer_pages_after_the_copies_each_copy_numbered_to_match():
    st = State(Settings(gen="maze", seed=1234))
    j = jobs.job(st, copies=9, vary=True, answers=True)
    assert j.count == 9 + 3 and j.answers == 3 and j.amount() == "9 copies and 3 answer pages"
    assert j.name.endswith("-9-designs-with-answers")
    seen = []
    real = jobs.draw_page
    jobs.draw_page = lambda ctx, g, spec, s: seen.append(spec)
    try:
        for i in range(j.count):
            j.draw(None, i)
    finally:
        jobs.draw_page = real
    copies, keys = seen[:9], seen[9:]
    assert [c.page_no for c in copies] == list(range(1, 10))               # the number at the foot of each copy
    assert [c.seed for c in copies] == [s for s, _ in _drawn(jobs.job(st, copies=9, vary=True))]   # same designs
    assert all(k.kind == "answers" and k.title == "Answers" for k in keys)
    assert [d.key_label for k in keys for d in k.items] == [f"Copy {n}" for n in range(1, 10)]
    assert [d.seed for k in keys for d in k.items] == [c.seed for c in copies]   # each answer is its copy's


def test_alike_copies_share_one_answer_and_pages_without_answers_get_none():
    st = State(Settings(gen="sudoku", seed=5))
    j = jobs.job(st, copies=6, vary=False, answers=True)
    assert j.count == 7 and j.amount() == "6 copies and 1 answer page"
    assert jobs.job(State(Settings(gen="mandala")), copies=6, vary=True, answers=True).answers == 0   # nothing to solve
    assert jobs.job(State(Settings(mode="convert")), copies=3, answers=True).answers == 0              # a photo
    assert jobs.job(st, copies=6, vary=True, answers=False).count == 6


def test_the_answers_switch_shows_for_puzzles_and_says_what_it_adds(win):
    sb = win.sidebar
    _set(win, gen="maze")
    assert not sb.copies_answers.isVisibleTo(sb)                           # one copy: no switch
    sb.copies.setText("5")
    assert sb.copies_answers.isVisibleTo(sb) and sb.copies_answers.isChecked()
    assert sb.copies_hint.text().endswith("Answer pages follow, and each copy is numbered to match them.")
    sb.copies_vary.setChecked(False)
    assert sb.copies_hint.text().endswith("all alike. One answer page follows.")
    sb.copies_answers.setChecked(False)
    assert sb.copies_hint.text().endswith("all alike.")
    _set(win, gen="mandala")
    assert not sb.copies_answers.isVisibleTo(sb)


def test_answer_pages_draw_for_every_kind_of_puzzle():
    """Each puzzle's copies and answers really draw (the engine, at a low resolution)."""
    from PySide6.QtGui import QImage, QPainter
    from inkengine.canvas import QtCanvas
    from inkengine.patterns import GENERATORS
    from inkengine.page import has_answer
    QApplication.instance() or QApplication([])
    for gen in GENERATORS:
        s = Settings(gen=gen, seed=99, dpi=24, complexity=2)
        if not has_answer(gen, s):
            continue
        j = jobs.job(State(s), copies=2, vary=True, answers=True)
        assert j.answers == 1, gen
        g = j.geometry
        for i in range(j.count):
            img = QImage(g.W, g.H, QImage.Format.Format_RGB32)
            img.fill(0xFFFFFFFF)
            p = QPainter(img)
            j.draw(QtCanvas(p, g.W, g.H), i)
            p.end()
