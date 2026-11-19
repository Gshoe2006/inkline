"""The printer's dead strip: hatched on the preview, and a warning under Margin when the design runs into it.
There's no printer here, so jobs.printer_margins is replaced with one that reports given margins."""

import time

import pytest

from PySide6.QtWidgets import QApplication

from inkapp import jobs


def _wait(ms):
    app = QApplication.instance()
    end = time.time() + ms / 1000
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    asked = []
    edges = {"Office": (0.2, 0.2, 0.2, 0.6), "": (0.125, 0.125, 0.125, 0.125)}

    def fake(name, s, orient):
        asked.append((name, s.paper, orient))
        w, h = (8.5, 11) if s.paper == "letter" else (8.27, 11.69)
        if orient == "landscape":
            w, h = h, w
        return (name or "Default printer", edges[name], (w, h)) if name in edges else None
    monkeypatch.setattr(jobs, "printer_margins", fake)
    from inkapp.window import Window
    w = Window("3.1.1", remember=True)
    w.asked, w.edges = asked, edges
    w.show()
    _wait(600)
    yield w
    w.close()
    w.deleteLater()
    _wait(50)


def _redraw(w, **kw):
    w.state.update(**kw)
    w.sidebar.load()
    w.schedule()
    _wait(700)


def test_the_default_printer_is_hatched_with_no_warning_inside_the_margin(win):
    assert win.asked[-1][0] == ""                          # nothing printed yet: the default printer
    left, top, right, bottom = win.preview.page.dead
    assert left == pytest.approx(0.125 / 8.5) and top == pytest.approx(0.125 / 11)
    assert not win.sidebar.margin_hint.isVisibleTo(win)    # ½ in margin, 1/8 in dead strip


def test_a_printer_that_reaches_into_the_margin_is_named_with_the_fix(win, tmp_path):
    win._remember_printer("Office")
    assert (tmp_path / "printer.json").read_text().count("Office") == 1
    _redraw(win, margin=0.25)
    assert win.sidebar.margin_hint.isVisibleTo(win)
    assert win.sidebar.margin_hint.text() == ("Office can't print the outer 0.6 in of the page, so the design will be cut off. "
                                              "Choose a ¾ in margin or more.")
    _redraw(win, margin=0.75)
    assert not win.sidebar.margin_hint.isVisibleTo(win)


def test_no_margin_choice_is_wide_enough(win):
    win.edges["Office"] = (1.2, 0.2, 0.2, 0.2)
    win._remember_printer("Office")
    assert win.sidebar.margin_hint.text().endswith("No margin choice is wide enough for it.")


def test_sheet_orientation_and_the_poster_and_test_page(win):
    win._remember_printer("Office")
    _redraw(win, booklet=True, fold=True)
    assert win.asked[-1][2] == "landscape"                 # fold-and-staple sheets print landscape
    _redraw(win, fold=False, booklet=False, poster=True)
    assert win.preview.page.dead is None                   # a whole poster shows no sheet margins
    assert win.sidebar.margin_hint.isVisibleTo(win)        # but every sheet would be cut off
    _redraw(win, poster=False, testpage=True)
    assert win.preview.page.dead is not None and not win.sidebar.margin_hint.isVisibleTo(win)


def test_no_printer_shows_nothing(win):
    win._remember_printer("Gone")
    assert win.preview.page.dead is None and not win.sidebar.margin_hint.isVisibleTo(win)


def test_the_printer_is_remembered_between_runs(win):
    win._remember_printer("Office")
    from inkapp.window import Window
    again = Window("3.1.1", remember=True)
    assert again.printer_name == "Office"
    again.deleteLater()
