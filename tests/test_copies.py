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
    jobs.draw_page = lambda ctx, g, spec, s: seen.append((spec.seed, spec.gen))
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
    assert len(set(_drawn(jobs.job(photo, copies=4, vary=True)))) == 1     # one look for every copy
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
    monkeypatch.setattr(win, "_start", lambda j, dev, done, failed, **kw: told.append(done))

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
    assert [c.stamp for c in copies] == [f"Copy {n}" for n in range(1, 10)]   # under each copy, in the margin
    assert all(c.page_no == 0 for c in copies)
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


def test_answer_pages_leave_every_copy_exactly_as_without_them():
    """Each copy draws just what it draws without answers (the first being the design shown), only with "Copy N"
    under it: a maze's grid, spot the difference's picture and colour by number fill the same space."""
    from inkengine.canvas import RecordingCanvas
    for kw in ({"gen": "maze"}, {"gen": "spot"}, {"gen": "contour", "cbn": True}, {"gen": "truchet", "cbn": True},
               {"gen": "maze", "title": "Friday", "name_line": True, "orient": "landscape"}):
        st = State(Settings(seed=7, dpi=36, **kw))
        plain, keyed = jobs.job(st, copies=3, vary=True), jobs.job(st, copies=3, vary=True, answers=True)
        for i in range(3):
            a, b = RecordingCanvas(), RecordingCanvas()
            plain.draw(a, i)
            keyed.draw(b, i)
            stamp = [op for op in b.ops if op[0] == "text" and op[1] == f"Copy {i + 1}"]
            assert len(stamp) == 1 and [op for op in b.ops if op not in stamp] == a.ops, kw


def test_names_make_one_copy_each_with_the_name_on_its_line():
    assert jobs.parse_names(" Ana, Ben ;\nCara,, ") == ["Ana", "Ben", "Cara"]
    assert len(jobs.parse_names(",".join(f"P{i}" for i in range(150)))) == jobs.MAX_COPIES
    assert jobs.copy_labels(["Sam", "Ana", "Sam"]) == ["Sam (copy 1)", "Ana", "Sam (copy 3)"]
    st = State(Settings(gen="maze", seed=3, name_line=True))
    j = jobs.job(st, copies=10, vary=True, names=["Ana", "Ben", "Cara"])  # the names say how many
    assert j.count == 3 and j.name.endswith("-3-designs-named")
    seen = []
    real = jobs.draw_page
    jobs.draw_page = lambda ctx, g, spec, s: seen.append(spec)
    try:
        for i in range(j.count):
            j.draw(None, i)
        k = jobs.job(st, copies=1, vary=True, answers=True, names=["Ana", "Ben", "Cara"])
        for i in range(k.count):
            k.draw(None, i)
    finally:
        jobs.draw_page = real
    assert [p.filled_name for p in seen[:3]] == ["Ana", "Ben", "Cara"]
    assert [p.seed for p in seen[:3]] == [s for s, _ in _drawn(jobs.job(st, copies=3, vary=True))]   # same designs
    keyed, key = seen[3:6], seen[6]
    assert [p.filled_name for p in keyed] == ["Ana", "Ben", "Cara"] and all(p.stamp == "" for p in keyed)
    assert [d.key_label for d in key.items] == ["Ana", "Ben", "Cara"]
    # without the Name line there's nowhere to write them: plain copies, as many as asked
    assert jobs.job(State(Settings(gen="maze")), copies=2, names=["Ana", "Ben", "Cara"]).count == 2


def test_a_name_is_written_on_the_line_and_the_design_is_unchanged():
    from inkengine.canvas import RecordingCanvas
    st = State(Settings(gen="maze", seed=3, name_line=True, dpi=36))
    a, b = RecordingCanvas(), RecordingCanvas()
    jobs.job(st, copies=2, vary=True).draw(a, 1)
    jobs.job(st, copies=2, vary=True, names=["Ana", "Ben"]).draw(b, 1)
    written = [op for op in b.ops if op[0] == "text" and op[1] == "Ben"]
    assert len(written) == 1 and [op for op in b.ops if op not in written] == a.ops


def test_the_names_field_says_what_it_does(win):
    sb = win.sidebar
    assert sb.copies_names_row.isVisibleTo(sb)
    sb.copies_names.setText("Ana, Ben, Cara")                              # no Name line yet
    assert sb.copies_hint.text().startswith('To write the names on the copies, turn on Page text → Add a "Name ______" line.')
    assert sb.copies.isEnabled()
    _set(win, name_line=True, gen="maze")
    assert not sb.copies.isEnabled()                                        # the names say how many
    assert sb.copies_hint.text().startswith("Print and Save PDF make 3 copies, one for each name, each with its own design")
    assert sb.copies_hint.text().endswith("Answer pages follow, each labelled with its copy's name.")
    sb.copies_names.setText(",".join(f"P{i}" for i in range(120)))
    assert "one for each name (the first 100)" in sb.copies_hint.text()
    sb.copies_names.setText("")
    assert sb.copies.isEnabled()


def test_run_stops_when_cancelled_and_calls_off_a_printer_job():
    from PySide6.QtGui import QImage
    QApplication.instance() or QApplication([])

    class Device(QImage):   # a page to paint on, with a printer's newPage and abort
        def __init__(self):
            super().__init__(10, 10, QImage.Format.Format_RGB32)
            self.aborted = False
        def newPage(self):
            return True
        def abort(self):
            self.aborted = True
    drawn = []
    j = jobs.Job("x", "copies", 5, "portrait", type("G", (), {"W": 10, "H": 10})(), lambda ctx, i: drawn.append(i))
    d = Device()
    assert jobs.run(j, d, cancelled=lambda: len(drawn) >= 2) is False and drawn == [0, 1] and d.aborted
    drawn.clear()
    d2 = Device()
    assert jobs.run(j, d2) is True and drawn == [0, 1, 2, 3, 4] and not d2.aborted


def test_cancel_stops_a_pdf_and_deletes_it(win, tmp_path, monkeypatch):
    import threading
    import time
    from PySide6.QtCore import QCoreApplication
    sb = win.sidebar
    sb.copies.setText("40")
    path = str(tmp_path / "set.pdf")
    monkeypatch.setattr(win, "_ask_path", lambda *a: path)
    real_run = jobs.run
    reached = threading.Event()

    def slow_run(j, device, progress=None, cancelled=lambda: False):   # holds page 2 until Cancel is pressed
        def prog(i):
            if i == 1:
                reached.set()
                deadline = time.time() + 10
                while not cancelled() and time.time() < deadline:
                    time.sleep(0.01)
            progress(i)
        return real_run(j, device, prog, cancelled)
    monkeypatch.setattr(jobs, "run", slow_run)
    win.save("pdf")
    assert sb.progress_row.isVisibleTo(sb) and sb.cancel_btn.isEnabled()
    deadline = time.time() + 30
    while win._busy_saving and time.time() < deadline:
        QCoreApplication.processEvents()
        if reached.is_set() and sb.cancel_btn.isEnabled():
            sb.cancel_btn.click()                                           # the button, as a person would
            assert not sb.cancel_btn.isEnabled() and sb.status.text() == "Cancelling after this page…"
        time.sleep(0.01)
    assert not win._busy_saving
    assert sb.status.text() == "Save cancelled: the PDF wasn't kept."
    assert not (tmp_path / "set.pdf").exists() and not sb.progress_row.isVisibleTo(sb)
    win.cancel_job()                                                        # nothing running: nothing happens
    assert sb.status.text() == "Save cancelled: the PDF wasn't kept."
