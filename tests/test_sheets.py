"""Several designs on one sheet."""

from dataclasses import replace

import pytest
from PySide6.QtWidgets import QApplication

from inkengine.canvas import RecordingCanvas
from inkengine.page import (PANELS, SHEETS, Settings, design_box, draw_page, geometry, panel_specs, sheet_boxes,
                            sheet_gens, single_page)


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


def test_each_layout_shares_out_the_design_box_without_overlap():
    s = Settings(dpi=72)
    g = geometry(s)
    box = design_box(g, single_page(s), s)
    for sheet, n in PANELS.items():
        boxes = sheet_boxes(box, sheet, 20)
        assert len(boxes) == n
        for b in boxes:
            assert box.x - 0.01 <= b.x and b.x + b.w <= box.x + box.w + 0.01
            assert box.y - 0.01 <= b.y and b.y + b.h <= box.y + box.h + 0.01
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert a.x + a.w <= b.x + 0.01 or b.x + b.w <= a.x + 0.01 or a.y + a.h <= b.y + 0.01 or b.y + b.h <= a.y + 0.01


def test_the_patterns_on_a_sheet_and_their_seeds():
    s = Settings(gen="mandala", seed=10, sheet="quarters", panel_gens="maze, sudoku ,nonsense,dots")
    assert sheet_gens(s) == ["mandala", "maze", "sudoku", "dots"]               # unknown ones are skipped
    assert sheet_gens(replace(s, panel_gens="")) == ["mandala", "words", "maze", "dots"]
    assert sheet_gens(replace(s, sheet="halves")) == ["mandala", "maze"]
    g = geometry(s)
    panels = panel_specs(g, single_page(s), s)
    assert [p.gen for p in panels] == ["mandala", "maze", "sudoku", "dots"]
    assert panels[0].seed == 10 and len({p.seed for p in panels}) == 4          # the first keeps the page's seed
    assert panel_specs(g, single_page(s), replace(s, sheet="one")) == []


def test_a_sheet_draws_each_design_in_its_place():
    s = Settings(gen="mandala", seed=10, dpi=72, sheet="banner", panel_gens="words,maze")
    c = RecordingCanvas()
    out = draw_page(c, geometry(s), single_page(s), s)
    assert len(out["panels"]) == 3
    # each design alone draws what it draws in its place on the sheet
    from inkengine.page import draw_design, line_width
    g = geometry(s)
    for p in panel_specs(g, single_page(s), s):
        alone = RecordingCanvas()
        alone.stroke_style = alone.fill_style = "#000"
        alone.line_cap = alone.line_join = "round"
        alone.line_width = line_width(s, g)
        draw_design(alone, g, p.panel_box, p.gen, p.seed, p.c, s, line_width(s, g))
        ops = [op for op in alone.ops if op[0] != "save" and op[0] != "restore"]
        assert all(op in c.ops for op in ops[:50])


def test_not_for_booklets_or_posters():
    from inkengine import book
    s = Settings(gen="maze", sheet="quarters", booklet=True, pages=2, dpi=36)
    assert all(panel_specs(geometry(s), p, s) == [] for p in book.book_pages(s))
    assert panel_specs(geometry(s), single_page(s), replace(s, booklet=False, poster=True)) == []


def test_copies_of_a_sheet_have_an_answer_for_each_puzzle_matching_it():
    from inkapp import jobs
    from inkapp.state import State
    s = Settings(gen="mandala", seed=5, dpi=36, sheet="quarters", panel_gens="maze,words,mandala")
    j = jobs.job(State(s), copies=3, vary=True, answers=True)
    assert j.answers == 2                                                      # 3 copies × 2 puzzles, 4 a page
    seen = []
    real = jobs.draw_page
    jobs.draw_page = lambda ctx, g, spec, st: seen.append(spec)
    try:
        for i in range(j.count):
            j.draw(None, i)
    finally:
        jobs.draw_page = real
    items = [d for p in seen if p.kind == "answers" for d in p.items]
    assert [d.key_label for d in items] == [f"Copy {n} · {w}" for n in (1, 2, 3) for w in ("Maze", "Word search")]
    g = geometry(s)
    for n, page in enumerate(seen[:3]):
        puzzles = [p for p in panel_specs(g, page, s) if p.gen in ("maze", "words")]
        assert [(d.gen, d.seed, tuple(d.panel_box)) for d in items[2 * n:2 * n + 2]] == \
            [(p.gen, p.seed, tuple(p.panel_box)) for p in puzzles]             # the same puzzle in the same place
    # a sheet with no puzzle on it has no answers
    assert jobs.job(State(replace(s, panel_gens="mandala,flow,truchet")), copies=2, answers=True).answers == 0


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("5.0.0", remember=False)
    w.show()
    yield w
    w.close()
    w.deleteLater()


def test_the_sheet_controls(win):
    sb = win.sidebar
    assert sb.sheet_row.isVisibleTo(sb) and not sb.sheet_opts.isVisibleTo(sb)
    sb.sheet.set_value("banner")
    assert win.state.settings.sheet == "banner" and sb.sheet_opts.isVisibleTo(sb)
    assert [row.isVisibleTo(sb) for row, _c in sb.panel_combos] == [True, True, False]
    sb.panel_combos[1][1].set_value("crossword")
    assert sheet_gens(win.state.settings)[2] == "crossword"
    assert win.history.undoText() == "Undo Designs on the sheet" or "sheet" in win.history.undoText().lower()
    win.state.update(booklet=True)
    win.sidebar.load()
    win._changed("booklet")
    assert not sb.sheet_row.isVisibleTo(sb)
