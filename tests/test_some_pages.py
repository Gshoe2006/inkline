"""Print and Save PDF of only some pages of a booklet or photo book."""

import time

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import jobs
from inkapp.state import State
from inkengine import book
from inkengine.page import Settings


def _pages(**kw):
    return book.book_pages(Settings(booklet=True, pages=10, gen="maze", **kw))   # cover, 10 designs, 3 answer pages


def test_reading_a_choice_of_pages():
    p = _pages()
    assert len(p) == 14
    assert jobs.parse_pages("", p) == list(range(14))
    assert jobs.parse_pages("3-5, 8, cover", p) == [0, 2, 3, 4, 7]
    assert jobs.parse_pages("5–3; 4", p) == [2, 3, 4]            # en dash, backwards, overlapping
    assert jobs.parse_pages(" Answers ", p) == [11, 12, 13]
    assert jobs.describe_pages([0, 2, 3, 4, 7], 14) == "pages 1, 3–5 and 8"
    assert jobs.describe_pages([6], 14) == "page 7"


@pytest.mark.parametrize("text, why", [
    ("20", "There's no page 20: this book has 14 pages."),
    ("0", "There's no page 0"),
    ("two", "“two” isn't a page"),
])
def test_a_choice_that_doesnt_make_sense_says_why(text, why):
    with pytest.raises(ValueError, match=why):
        jobs.parse_pages(text, _pages())
    with pytest.raises(ValueError, match="no cover page"):
        jobs.parse_pages("cover", _pages(cover=False))
    with pytest.raises(ValueError, match="no answer pages"):
        jobs.parse_pages("answers", _pages(key=False))


def test_a_job_draws_only_the_pages_chosen():
    st = State(Settings(booklet=True, pages=10, gen="maze"))
    whole, part = jobs.job(st), jobs.job(st, "3-5, 8")
    assert (whole.count, part.count) == (14, 4) and part.name == whole.name + "-p3-5_8"
    drawn = []
    real = jobs.draw_page
    jobs.draw_page = lambda ctx, g, spec, s: drawn.append(spec)
    try:
        for i in range(part.count):
            part.draw(None, i)
    finally:
        jobs.draw_page = real
    pages = book.book_pages(st.settings)
    assert drawn == [pages[2], pages[3], pages[4], pages[7]]


def test_a_fold_and_staple_book_prints_the_sheets_holding_them():
    st = State(Settings(booklet=True, pages=10, gen="maze", fold=True))   # 14 pages, padded to 16: 4 sheets
    assert jobs.job(st).count == 8                                          # every side
    j = jobs.job(st, "3")
    assert j.count == 2 and j.duplex                                        # sheet 2, front and back
    assert jobs.fold_sheets([2], 16) == [1] and jobs.fold_sheets([0, 15], 16) == [0]


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("4.3.0", remember=False)
    w.show()
    yield w
    w.close()
    w.deleteLater()


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_the_field_shows_for_books_and_says_what_will_print(win):
    sb = win.sidebar
    assert not sb.only_row.isVisibleTo(sb)                                  # a single page
    _set(win, booklet=True, pages=10, gen="maze")
    assert sb.only_row.isVisibleTo(sb) and not sb.only_hint.isVisibleTo(sb)
    sb.only_pages.setText("3-5, 8")
    assert sb.only_hint.isVisibleTo(sb) and sb.only_hint.text() == "Prints and saves pages 3–5 and 8 of 14."
    sb.only_pages.setText("30")
    assert sb.only_hint.text() == "There's no page 30: this book has 14 pages."
    _set(win, fold=True)
    sb.only_pages.setText("3")
    assert sb.only_hint.text() == "Prints sheet 2, both sides: they hold page 3."


def test_print_and_save_use_the_choice_or_say_whats_wrong(win, monkeypatch):
    _set(win, booklet=True, pages=10, gen="maze")
    win.sidebar.only_pages.setText("99")
    asked = []
    monkeypatch.setattr(win, "_ask_path", lambda *a: asked.append(a) or None)
    win.save("pdf")
    assert asked == [] and win.sidebar.status.text().startswith("There's no page 99")
    win.sidebar.only_pages.setText("2")
    win.save("pdf")
    assert asked and asked[0][1].endswith("-p2")                            # the file is named for the page
    win.sidebar.only_pages.setText("")
    asked.clear()
    win.save("pdf")
    assert not asked[0][1].endswith("-p2")
