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
