"""Age levels: a starting point for each pattern that suits a child's age."""

import pytest
from PySide6.QtWidgets import QApplication

from inkengine import ages
from inkengine.page import Settings
from inkengine.patterns import GENERATORS


def test_every_pattern_has_a_complexity_for_every_age_rising_with_age():
    assert set(ages.COMPLEXITY) == set(GENERATORS)
    for gen, by_age in ages.COMPLEXITY.items():
        assert set(by_age) == {"4-6", "7-9", "10+"}
        assert 1 <= by_age["4-6"] < by_age["7-9"] < by_age["10+"] <= 10, gen
    assert ages.for_age(Settings(age="any")) == {}
    young = ages.for_age(Settings(gen="maths", age="4-6"))
    assert young == {"weight": 6, "cbn_colours": 4, "maths_kind": "add", "trace_source": "upper", "complexity": 1}
    assert ages.for_pattern(Settings(gen="crossword", age="10+")) == {"complexity": 8}
    assert ages.for_pattern(Settings(gen="crossword", age="any")) == {}
    assert Settings.from_dict({"age": "99"}).age == "any"


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    QApplication.instance() or QApplication([])
    from inkapp.window import Window
    w = Window("5.0.0", remember=False)
    w.show()
    yield w
    w.close()
    w.deleteLater()


def _pick(win, combo, value):
    combo.set_value(value)   # as the person choosing it: the sidebar tells the window
    QApplication.processEvents()


def test_choosing_an_age_sets_the_page_up_for_it_in_one_undo_step(win):
    sb = win.sidebar
    _pick(win, sb.gen, "maze")
    before = win.history.count()
    _pick(win, sb.age, "4-6")
    s = win.state.settings
    assert s.age == "4-6" and s.complexity == 2 and s.weight == 6 and s.cbn_colours == 4
    assert sb.age_hint.isVisibleTo(sb)
    assert win.history.count() == before + 1 and win.history.undoText() == "Age"
    _pick(win, sb.gen, "words")                                            # another pattern: its age complexity
    assert win.state.settings.complexity == 1 and win.state.settings.weight == 6
    win.state.update(complexity=6)                                         # changed after: kept until the next choice
    win.sidebar.load()
    win._changed("complexity")
    assert win.state.settings.complexity == 6
    win.history.undo()
    win.history.undo()
    win.history.undo()
    assert win.state.settings.age == "any" and win.state.settings.gen == "maze"


def test_an_age_in_a_booklet_built_page_by_page_sets_the_page_being_edited(win):
    sb = win.sidebar
    win.state.update(booklet=True, gen="maze", page_list=[{"gen": "maze", "seed": 1}, {"gen": "maths", "seed": 2}])
    win.state.book_sel = 1
    win.state.mirror()
    sb.load()
    sb.fill_pages()
    _pick(win, sb.age, "7-9")
    pl = win.state.settings.page_list
    assert pl[1]["complexity"] == 4 and pl[1]["maths_kind"] == "addsub"
    assert pl[0] == {"gen": "maze", "seed": 1}                             # only the page being edited
