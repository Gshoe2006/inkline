"""Print and Save PDF of several copies of a single page, each with its own design or alike."""

import pytest
from dataclasses import replace
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
    assert sb.shown(sb.copies_row) and not sb.shown(sb.copies_hint)
    sb.copies.setText("25")
    assert sb.shown(sb.copies_vary)
    assert sb.copies_hint.text() == "Print and Save PDF make 25 copies, each with its own design (the first is the one shown)."
    sb.copies_vary.setChecked(False)
    assert sb.copies_hint.text().endswith("all alike.")
    from PySide6.QtTest import QTest
    sb.copies.clear()
    QTest.keyClicks(sb.copies, "ab7c")                                     # the field takes digits only
    assert sb.copies.text() == "7" and sb.copies_count() == 7
    _set(win, booklet=True)                                                # a booklet: copies of the booklet
    assert sb.shown(sb.copies_row) and sb.shown(sb.only_row)
    _set(win, booklet=False, poster=True)
    assert not sb.shown(sb.copies_row)


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
    assert got[-1][2] == 12                                                # a class set of booklets
    _set(win, booklet=False, poster=True)
    win.print_()
    assert got[-1][2] == 1                                                 # a poster has no copies


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
    assert not sb.shown(sb.copies_vary)                              # nothing to vary: no switch for it
    assert sb.copies_hint.text().startswith("Print and Save PDF make 4 copies, all alike. A name page")
    _set(win, gen="dots")
    assert sb.shown(sb.copies_vary) and "some copies repeat." in sb.copies_hint.text()
    sb.copies_vary.setChecked(False)
    assert "all alike." in sb.copies_hint.text() and "repeat" not in sb.copies_hint.text()   # alike anyway


def test_a_number_out_of_range_says_what_will_print_and_is_put_right_on_leaving(win):
    sb = win.sidebar
    sb.copies.setText("101")
    assert sb.copies_count() == 100
    assert sb.shown(sb.copies_hint) and sb.copies_hint.text().startswith("Copies go from 1 to 100. Print and Save PDF make 100 copies")
    sb.copies.setText("0")
    assert sb.copies_hint.text() == "Copies go from 1 to 100. Print and Save PDF make 1 copy."
    assert sb.copies.validator().fixup("000") == "1" and sb.copies.validator().fixup("250") == "100"
    sb.copies.setText("")
    assert not sb.shown(sb.copies_hint)


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
    assert not sb.shown(sb.copies_answers)                           # one copy: no switch
    sb.copies.setText("5")
    assert sb.shown(sb.copies_answers) and sb.copies_answers.isChecked()
    assert sb.copies_hint.text().endswith("Answer pages follow, and each copy is numbered to match them.")
    sb.copies_vary.setChecked(False)
    assert sb.copies_hint.text().endswith("all alike. One answer page follows.")
    sb.copies_answers.setChecked(False)
    assert sb.copies_hint.text().endswith("all alike.")
    _set(win, gen="mandala")
    assert not sb.shown(sb.copies_answers)


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
    assert sb.shown(sb.copies_names_row)
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


def test_run_stops_a_pdf_when_cancelled():
    from PySide6.QtGui import QImage
    QApplication.instance() or QApplication([])

    class Device(QImage):   # a page to paint on, with a PDF writer's newPage
        def __init__(self):
            super().__init__(10, 10, QImage.Format.Format_RGB32)
        def newPage(self):
            return True
    drawn = []
    j = jobs.Job("x", "copies", 5, "portrait", type("G", (), {"W": 10, "H": 10})(), lambda ctx, i: drawn.append(i))
    assert jobs.run(j, Device(), cancelled=lambda: len(drawn) >= 2) is False and drawn == [0, 1]
    drawn.clear()
    assert jobs.run(j, Device()) is True and drawn == [0, 1, 2, 3, 4]


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

    def slow_run(j, device, progress=None, cancelled=lambda: False):   # holds page 2 until Cancel
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
    assert sb.shown(sb.progress_row) and sb.cancel_btn.isEnabled()
    deadline = time.time() + 30
    while win._busy_saving and time.time() < deadline:
        QCoreApplication.processEvents()
        if reached.is_set() and sb.cancel_btn.isEnabled():
            sb.cancel_btn.click()                                           # the button, as a person would
            assert not sb.cancel_btn.isEnabled() and sb.status.text() == "Cancelling after this page…"
        time.sleep(0.01)
    assert not win._busy_saving
    assert sb.status.text() == "Save cancelled: the PDF wasn't kept."
    assert not (tmp_path / "set.pdf").exists() and not sb.shown(sb.progress_row)
    win.cancel_job()                                                        # nothing running: nothing happens
    assert sb.status.text() == "Save cancelled: the PDF wasn't kept."



def _printer_to(path, s=None, orient="portrait"):
    """A printer writing a PDF, set up as Print sets one up (its page from the settings)."""
    from PySide6.QtPrintSupport import QPrinter
    pr = QPrinter(QPrinter.PrinterMode.HighResolution)
    pr.setPageLayout(jobs.page_layout(s or Settings(), orient))
    pr.setFullPage(True)
    pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    pr.setOutputFileName(str(path))
    return pr


def test_a_print_is_drawn_first_so_cancelling_sends_nothing(tmp_path):
    """Pages are drawn before the printer starts: a cancel at any point while drawing leaves nothing printed
    (here a printer writing a PDF stands in for one, as Linux's printing works)."""
    QApplication.instance() or QApplication([])
    st = State(Settings(gen="maze", seed=3, dpi=36))
    j = jobs.job(st, copies=4, vary=True)
    for stop in (0, 2, 3):                                                  # before page 1, 3 and the last
        out = tmp_path / f"stop{stop}.pdf"
        drawn = []
        assert jobs.run(j, _printer_to(out), progress=drawn.append, cancelled=lambda: len(drawn) > stop) is False
        assert not out.exists()                                             # the printer was never started
    out = tmp_path / "all.pdf"
    assert jobs.run(j, _printer_to(out)) is True and out.exists()


def test_a_printed_page_matches_the_saved_pdf(tmp_path):
    """Played back from its recording, a printed page looks like the PDF saved straight from the same job."""
    import subprocess
    import shutil
    from PySide6.QtGui import QImage, QPdfWriter
    if not shutil.which("pdftoppm"):
        pytest.skip("needs pdftoppm")
    QApplication.instance() or QApplication([])
    for kw in ({"gen": "maze", "title": "Mazes", "name_line": True}, {"gen": "words"}, {"gen": "mandala", "cbn": True}):
        s = Settings(seed=8, dpi=72, **kw)
        j = jobs.job(State(s), copies=1, names=["Ana"] if kw.get("name_line") else ())
        printed, saved = tmp_path / "printed.pdf", tmp_path / "saved.pdf"
        assert jobs.run(j, _printer_to(printed, s, j.orient))
        w = QPdfWriter(str(saved))
        w.setPageLayout(jobs.page_layout(s, j.orient))
        w.setResolution(s.dpi)
        assert jobs.run(j, w)
        pics = []
        for f in (printed, saved):
            subprocess.run(["pdftoppm", "-r", "40", "-gray", "-png", "-singlefile", str(f), str(f.with_suffix(""))],
                           check=True)
            pics.append(QImage(str(f.with_suffix(".png"))).convertToFormat(QImage.Format.Format_Grayscale8))
        a, b = pics
        assert a.size() == b.size()
        diff = sum(abs(a.pixelColor(x, y).value() - b.pixelColor(x, y).value()) > 64
                   for x in range(0, a.width(), 2) for y in range(0, a.height(), 2))
        assert diff < 0.01 * (a.width() // 2) * (a.height() // 2), (kw, diff)


def _print_and_cancel(win, monkeypatch, at, file=None):
    """Print the sidebar's copies, pressing Cancel as page at+1 starts; returns the status line."""
    import threading
    import time
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    def accept(d):
        if file:
            d.printer().setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            d.printer().setOutputFileName(file)
        return QPrintDialog.DialogCode.Accepted
    monkeypatch.setattr(QPrintDialog, "exec", accept)
    real_run, reached = jobs.run, threading.Event()

    def slow_run(j, device, progress=None, cancelled=lambda: False):
        def prog(i):
            if i == at:
                reached.set()
                deadline = time.time() + 10
                while not cancelled() and time.time() < deadline:
                    time.sleep(0.01)
            progress(i)
        if not file:   # no printer here: a PDF stands in, as Linux's print system does
            device.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            device.setOutputFileName(str(win._tmp / "spool.pdf"))
        return real_run(j, device, prog, cancelled)
    monkeypatch.setattr(jobs, "run", slow_run)
    if not file:   # so the printer isn't treated as "Print to file" afterwards
        monkeypatch.setattr(QPrinter, "outputFileName", lambda p: "")
    win.print_()
    deadline = time.time() + 30
    while win._busy_saving and time.time() < deadline:
        QCoreApplication.processEvents()
        if reached.is_set() and win.sidebar.cancel_btn.isEnabled():
            win.sidebar.cancel_btn.click()
        time.sleep(0.01)
    return win.sidebar.status.text()


def test_cancelled_printing_sends_nothing(win, tmp_path, monkeypatch):
    win._tmp = tmp_path
    win.sidebar.copies.setText("6")
    assert _print_and_cancel(win, monkeypatch, 2) == "Printing cancelled: nothing was sent to the printer."
    assert not (tmp_path / "spool.pdf").exists()                           # nothing reached the "printer"


def test_cancelled_print_to_file_isnt_kept(win, tmp_path, monkeypatch):
    win._tmp = tmp_path
    win.sidebar.copies.setText("6")
    out = tmp_path / "printed.pdf"
    assert _print_and_cancel(win, monkeypatch, 2, file=str(out)) == "Printing cancelled: no file was written."
    assert not out.exists()


def test_a_single_name_has_no_hidden_answer_page_and_esc_leaves_one_page_alone(win, tmp_path, monkeypatch):
    sb = win.sidebar
    _set(win, gen="maze", name_line=True)
    sb.copies_names.setText("Ana")
    assert not sb.shown(sb.copies_answers) and sb.copies_answers.isChecked()
    j = win._job(State(replace(win.state.settings)))
    assert j.count == 1 and j.answers == 0                                  # one copy: no answers, as the hint says
    sb.copies_names.setText("")
    win._busy_saving = True                                                 # a one-page job: no Cancel button
    sb.progress_row.hide()
    win.cancel_job()
    assert not win._cancel.is_set()
    win._busy_saving = False


def test_a_long_name_is_written_smaller_to_fit():
    from inkengine.canvas import RecordingCanvas
    st = State(Settings(gen="maze", seed=3, name_line=True, dpi=36))
    short, long_ = RecordingCanvas(), RecordingCanvas()
    jobs.job(st, copies=2, names=["Al", "Bo"]).draw(short, 0)
    jobs.job(st, copies=2, names=["Bartholomew Alexander Featherstonehaugh-Montgomery the Third", "Bo"]).draw(long_, 0)
    def size(c, n):   # a text op is ("text", text, x, y, colour, weight, size)
        return [op for op in c.ops if op[0] == "text" and op[1].startswith(n)][0][6]
    assert size(long_, "Bartholomew") < size(short, "Al")



def test_a_class_set_of_booklets_each_with_its_own_designs_and_name():
    s = Settings(gen="maze", seed=11, booklet=True, pages=3, cover=True, key=True, name_line=True)
    one = jobs.job(State(s))
    per = one.count
    j = jobs.job(State(s), copies=4, vary=True)
    assert j.label == "booklets" and j.copies == 4 and j.count == 4 * per and j.amount() == f"4 booklets ({4 * per} pages)"
    seen = []
    real = jobs.draw_page
    jobs.draw_page = lambda ctx, g, spec, st: seen.append(spec)
    try:
        for i in range(j.count):
            j.draw(None, i)
        named = jobs.job(State(s), copies=1, vary=True, names=["Ana", "Ben"])
        nseen = []
        jobs.draw_page = lambda ctx, g, spec, st: nseen.append(spec)
        for i in range(named.count):
            named.draw(None, i)
    finally:
        jobs.draw_page = real
    designs = [[p.seed for p in seen[b * per:(b + 1) * per] if p.kind == "design"] for b in range(4)]
    assert len({tuple(d) for d in designs}) == 4                           # every booklet its own designs
    first = [p.seed for p in seen[:per] if p.kind == "design"]
    plain = []
    jobs.draw_page = lambda ctx, g, spec, st: plain.append(spec)
    try:
        for i in range(one.count):
            one.draw(None, i)
    finally:
        jobs.draw_page = real
    assert first == [p.seed for p in plain if p.kind == "design"]          # the first is the one shown
    assert named.count == 2 * per and named.name.endswith("-2-booklets-named")
    ana = nseen[:per]
    assert ana[0].kind == "cover" and ana[0].filled_name == "Ana"
    assert all(p.filled_name == "Ana" for p in ana if p.kind == "design")
    assert [p.title for p in ana if p.kind == "answers"] == ["Answers · Ana"]
    assert nseen[per].filled_name == "Ben"


def test_booklets_built_page_by_page_and_swapped_pages_vary_too():
    s = Settings(gen="maze", seed=5, booklet=True, page_list=[{"gen": "maze", "seed": 100}, {"gen": "words", "seed": 200}],
                 page_seeds={"cover": 300}, cover=True)
    a, b = jobs.copy_settings(s, 0, True), jobs.copy_settings(s, 3, True)
    assert a is s
    assert [p["seed"] for p in b.page_list] == [jobs.copy_seed(100, 3), jobs.copy_seed(200, 3)]
    assert b.page_seeds == {"cover": jobs.copy_seed(300, 3)} and [p["gen"] for p in b.page_list] == ["maze", "words"]
    assert jobs.copy_settings(s, 3, False) is s


def test_booklet_class_sets_fold_each_booklet_on_its_own_and_pick_pages():
    s = Settings(gen="maze", seed=2, booklet=True, pages=6, cover=True, fold=True)
    one = jobs.job(State(s))
    j = jobs.job(State(s), copies=3, vary=True)
    assert j.duplex and j.count == 3 * one.count and j.amount() == f"3 booklets, {j.count // 2} sheets (both sides)"
    flat = jobs.job(State(replace(s, fold=False)), only="1-2", copies=3)
    assert flat.count == 6 and "-p1-2" in flat.name


def test_the_paper_section_offers_copies_of_a_booklet(win):
    sb = win.sidebar
    _set(win, gen="maze", booklet=True, name_line=True)
    sb.copies.setText("5")
    assert sb.shown(sb.copies_vary) and not sb.shown(sb.copies_answers)   # it has its own answers
    assert sb.copies_hint.text() == "Print and Save PDF make 5 booklets, each with its own designs (the first is the one shown)."
    sb.copies_names.setText("Ana, Ben")
    assert sb.copies_hint.text().startswith("Print and Save PDF make 2 booklets, one for each name, each with its own designs")
    assert sb.copies_hint.text().endswith("Each name goes on its booklet's cover, Name lines and answer pages.")


def test_the_preview_shows_any_copy_with_its_designs_and_name():
    from inkapp import render
    from inkapp.classset import ClassSet
    QApplication.instance() or QApplication([])
    s = Settings(gen="maze", seed=4, name_line=True)
    cs = ClassSet(count=3, vary=True, names=["Ana", "Ben", "Cara"])
    first = render.render_view(State(s))
    shown0 = render.render_view(State(s, copy=0, class_set=cs))
    shown1 = render.render_view(State(s, copy=1, class_set=cs))
    assert shown0.view.copy_label == "Copy 1 of 3 · Ana" and shown1.view.copy_label == "Copy 2 of 3 · Ben"
    assert shown1.view.copy == 1 and render.render_view(State(s, copy=9, class_set=cs)).view.copy == 2   # kept in range
    assert shown0.image != shown1.image                                   # copy 2 has its own maze
    assert shown0.image != first.image                                    # and the name is on its line
    alike = render.render_view(State(s, copy=1, class_set=ClassSet(count=3, vary=False)))
    assert alike.image == first.image and alike.view.copy_label == "Copy 2 of 3"
    assert render.view(State(s)).copy_label == ""                         # no class set, no copy pager
    # a booklet: the copy's own pages (paging through them as before), its name on the cover
    b = Settings(gen="maze", seed=4, booklet=True, pages=2, cover=True, name_line=True)
    v = render.view(State(b, copy=1, class_set=cs))
    assert v.kind == "booklet" and v.pages[0].filled_name == "Ben" and v.copy_label == "Copy 2 of 3 · Ben"
    assert [p.seed for p in v.pages if p.kind == "design"] != \
        [p.seed for p in render.view(State(b)).pages if p.kind == "design"]
    # no class set where there can't be one
    assert render.view(State(replace(b, poster=True), copy=1, class_set=cs)).copy_label == ""


def test_the_copy_pager_steps_through_the_copies(win):
    sb = win.sidebar
    _set(win, gen="maze", name_line=True)
    assert not sb.shown(sb.copy_pager) and sb.class_set_view() is None
    sb.copies_names.setText("Ana, Ben, Cara")
    assert sb.shown(sb.copy_pager) and sb.class_set_view().count == 3
    win.step_copy(1)
    win.step_copy(1)
    win.step_copy(1)                                                       # stops at the last
    assert win.state.copy == 2
    win.step_copy(-5)
    assert win.state.copy == 0
    from inkapp import render
    sb.sync(render.view(State(win.state.settings, copy=1, class_set=sb.class_set_view())))
    assert sb.copy_pager.text.text() == "Copy 2 of 3 · Ben"
    assert sb.copy_pager.back.accessibleName() == "Previous copy"


def test_png_and_svg_save_the_copy_shown():
    from inkapp.classset import ClassSet
    QApplication.instance() or QApplication([])
    s = Settings(gen="maze", seed=4, name_line=True, dpi=36)
    cs = ClassSet(count=3, vary=True, names=["Ana", "Ben", "Cara"])
    text0, name0 = jobs.svg(State(s))
    text1, name1 = jobs.svg(State(s, copy=1, class_set=cs))
    assert name1 == name0 + "-copy2" and text1 != text0 and ">Ben<" in text1
    img0, _ = jobs.png(State(s))
    img1, n1 = jobs.png(State(s, copy=1, class_set=cs))
    assert n1.endswith("-copy2") and img0 != img1
    assert jobs.svg(State(s, copy=0, class_set=cs))[1] == name0          # the first copy keeps the plain name


def test_fixes_from_checking_booklet_class_sets(win, tmp_path):
    from inkapp import render
    from inkapp.classset import ClassSet
    QApplication.instance() or QApplication([])
    # the PNG of a folded side carries the copy's name, as the preview does
    b = Settings(gen="maze", seed=4, booklet=True, pages=2, cover=True, fold=True, name_line=True, dpi=36)
    cs = ClassSet(count=2, vary=True, names=["Ana", "Ben"])
    named, _ = jobs.png(State(b, copy=0, class_set=cs))
    plain, _ = jobs.png(State(b))
    assert named != plain
    # one name is a class set too: the preview and PNG/SVG show it
    sb = win.sidebar
    _set(win, gen="maze", name_line=True)
    sb.copies_names.setText("Ana")
    one = sb.class_set_view()
    assert one is not None and one.count == 1 and not sb.shown(sb.copy_pager)
    assert ">Ana<" in jobs.svg(State(win.state.settings, class_set=one))[0]
    # Booklet left on from Make one up doesn't stop a photo's copies showing their names
    p = Settings(mode="convert", booklet=True, name_line=True)
    from inkengine.photo import Photo
    from PySide6.QtGui import QImage, QColor
    img = QImage(40, 30, QImage.Format.Format_ARGB32)
    img.fill(QColor("#468"))
    v = render.view(State(p, [Photo(img)], copy=1, class_set=ClassSet(count=2, names=["Ana", "Ben"])))
    assert v.copy == 1 and v.copy_label == "Copy 2 of 2 · Ben"
    # opening a project starts at its first copy
    win.state.copy = 3
    path = str(tmp_path / "p.inkline")
    win._write_project(path)
    win.open_project(path)
    assert win.state.copy == 0


def test_a_print_says_when_its_pages_go_to_the_printer(tmp_path):
    QApplication.instance() or QApplication([])
    j = jobs.job(State(Settings(gen="maze", dpi=36)), copies=3, vary=True)
    said = []
    assert jobs.run(j, _printer_to(tmp_path / "out.pdf"), progress=said.append)
    assert said == [0, 1, 2, 3]                                            # 3 means: now sending


def _pages_of(j):
    seen = []
    real = jobs.draw_page
    jobs.draw_page = lambda ctx, g, spec, st: seen.append(spec)
    try:
        for i in range(j.count):
            j.draw(None, i)
    finally:
        jobs.draw_page = real
    return seen


def test_a_teachers_answer_book_gathers_every_booklets_answers():
    s = Settings(gen="maze", seed=11, booklet=True, pages=4, cover=True, key=True, name_line=True)
    plain = jobs.job(State(s), names=["Ana", "Ben", "Cara"])
    j = jobs.job(State(s), names=["Ana", "Ben", "Cara"], answer_book=True)
    assert j.count == plain.count and j.answers == 3 and j.name.endswith("-named-answer-book")
    assert j.amount() == f"3 booklets ({j.count - 3} pages) and a 3-page answer book"
    pages = _pages_of(j)
    kids, book = pages[:-3], pages[-3:]
    assert not any(p.kind == "answers" for p in kids)                      # no answers in the children's booklets
    assert [p.title for p in book] == ["Answers · Ana", "Answers · Ben", "Answers · Cara"]
    assert all(p.page_no == 0 for p in book)
    by_kid = [p for p in _pages_of(plain) if p.kind == "answers"]
    assert [[d.seed for d in p.items] for p in book] == [[d.seed for d in p.items] for p in by_kid]   # same answers


def test_unnamed_booklets_are_numbered_to_match_the_answer_book():
    s = Settings(gen="sudoku", seed=2, booklet=True, pages=2, cover=True, key=True)
    pages = _pages_of(jobs.job(State(s), copies=2, answer_book=True))
    covers = [p for p in pages if p.kind == "cover"]
    assert [p.filled_name for p in covers] == ["Booklet 1", "Booklet 2"]
    assert [p.title for p in pages if p.kind == "answers"] == ["Answers · Booklet 1", "Answers · Booklet 2"]
    assert not any(p.filled_name for p in _pages_of(jobs.job(State(s), copies=2)) if p.kind == "cover")   # only then


def test_the_answer_book_folds_on_its_own_and_needs_answer_pages():
    s = Settings(gen="maze", seed=3, booklet=True, pages=6, cover=True, key=True, fold=True)
    j = jobs.job(State(s), copies=2, answer_book=True)
    assert j.duplex and j.answers == 4 and "and an answer book" in j.amount()   # 2 × 2 answer pages
    assert jobs.job(State(replace(s, key=False)), copies=2, answer_book=True).answers == 0   # no answer pages: no book


def test_the_answer_book_switch_shows_for_booklet_class_sets(win):
    sb = win.sidebar
    _set(win, gen="maze", booklet=True, key=True, name_line=True)
    assert not sb.shown(sb.copies_answer_book)                      # one booklet: nothing to gather
    sb.copies_names.setText("Ana, Ben")
    assert sb.shown(sb.copies_answer_book) and not sb.copies_answer_book.isChecked()
    sb.copies_answer_book.setChecked(True)
    assert "heads its answers in the teacher's book" in sb.copies_hint.text()
    j = win._job(State(win.state.settings))
    assert j.answers > 0
    _set(win, key=False)
    assert not sb.shown(sb.copies_answer_book)
    assert win._job(State(win.state.settings)).answers == 0
