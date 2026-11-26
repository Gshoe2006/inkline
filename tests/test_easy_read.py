"""Easier to read (a clearer font, spaced wider) and cream paper for screens and PDFs."""

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from inkengine import qt
from inkengine.canvas import RecordingCanvas, SvgCanvas
from inkengine.page import CREAM, Settings, draw_page, geometry, single_page


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


def test_the_font_and_its_spacing():
    assert qt.easy_family() == "Atkinson Hyperlegible"
    f = qt.make_font(40, 400, easy=True)
    assert f.families()[0] == "Atkinson Hyperlegible" and f.letterSpacing() == qt.EASY_LETTERS
    assert f.letterSpacingType() == QFont.SpacingType.PercentageSpacing and f.wordSpacing() == pytest.approx(40 * qt.EASY_WORDS, abs=0.05)
    plain = qt.make_font(40, 400)
    assert plain.families()[0] != "Atkinson Hyperlegible" and plain.wordSpacing() == 0
    hand = qt.make_font(40, 400, family="Playwrite GB J", easy=True)   # joined-up handwriting keeps its own font
    assert hand.families()[0] == "Playwrite GB J" and hand.wordSpacing() == 0
    assert qt.make_font(40, 700, easy=True).weight() == QFont.Weight.Bold


def test_wider_text_measures_wider():
    from inkengine.qt import make_font
    from PySide6.QtGui import QFontMetricsF
    from inkengine.qt import easy_family
    text = "The afternoon sky turned dark grey"
    same_font = make_font(30, family=easy_family())          # Atkinson Hyperlegible without the extra spacing
    plain = QFontMetricsF(same_font).horizontalAdvance(text)
    easy = QFontMetricsF(make_font(30, easy=True)).horizontalAdvance(text)
    assert easy > plain * 1.05                               # spaced wider; measured so, so pages lay it out with room


def test_draw_page_paints_cream_and_sets_the_canvas():
    s = Settings(gen="reading", dpi=30, easy_read=True, cream=True)
    ctx = RecordingCanvas()
    draw_page(ctx, geometry(s), single_page(s), s)
    assert ctx.easy_read is True
    plain = RecordingCanvas()
    draw_page(plain, geometry(Settings(gen="reading", dpi=30)), single_page(Settings(gen="reading", dpi=30)),
              Settings(gen="reading", dpi=30))
    assert plain.easy_read is False
    assert CREAM == "#fbf3df"


def test_svg_says_the_font_and_spacing():
    s = Settings(gen="reading", dpi=30, easy_read=True)
    g = geometry(s)
    svg = SvgCanvas(g.W, g.H, g.w, g.h)
    draw_page(svg, g, single_page(s), s)
    out = "".join(svg.out)
    assert "Atkinson Hyperlegible" in out and 'letter-spacing="' in out and 'word-spacing="' in out


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    return Window("6.0.0", remember=False)


def test_the_checkboxes_and_print_uses_white(win, monkeypatch):
    sb = win.sidebar
    sb._binds["easy_read"][0].setChecked(True)
    sb._binds["cream"][0].setChecked(True)
    QApplication.processEvents()
    assert win.state.settings.easy_read and win.state.settings.cream
    assert sb.folds["text"].isAncestorOf(sb._binds["easy_read"][0]) and sb.folds["paper"].isAncestorOf(sb._binds["cream"][0])
    import inkapp.window as w
    seen = []
    real = w.jobs.job
    monkeypatch.setattr(w.jobs, "job", lambda snap, *a, **k: (seen.append(snap.settings.cream), real(snap, *a, **k))[1])

    class Dialog:
        DialogCode = w.QPrintDialog.DialogCode

        def __init__(self, *a):
            pass

        def setOption(self, *a):
            pass

        def exec(self):
            return self.DialogCode.Rejected
    monkeypatch.setattr(w, "QPrintDialog", Dialog)
    win.print_()
    assert seen == [False] and win.state.settings.cream      # the printer gets white; the setting stays
