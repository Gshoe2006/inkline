"""Each pattern's own options are built the first time they're wanted (start-up builds about half the widgets it did),
and everything that reads them still works: sync(), load(), presets, undo, projects, and reading a control by name."""

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from inkapp import sidebar
from inkapp.sidebar import PATTERN_PANELS


@pytest.fixture
def make_win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))

    def make(remember=False):
        from inkapp.window import Window
        w = Window("6.3.0", remember=remember)
        w.resize(1280, 820)
        w.show()
        QApplication.processEvents()
        return w
    return make


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_only_the_chosen_patterns_options_are_built(make_win):
    w = make_win()
    sb = w.sidebar
    assert w.state.settings.gen == "mandala" and sb._built == {}            # a mandala has none of its own
    few = len(sb.findChildren(QWidget))
    _set(w, gen="speed")
    assert set(sb._built) == {"speed"} and sb.shown(sb.speed_opts)
    sb.build_all()
    assert set(sb._built) == set(PATTERN_PANELS)
    assert len(sb.findChildren(QWidget)) > few + 400                        # what start-up no longer builds
    assert not sb.shown(sb.trace_opts) and sb.shown(sb.speed_opts)          # sync() still shows only the one


def test_the_table_names_what_each_panel_makes(make_win):
    sb = make_win().sidebar
    before = set(sb.__dict__)
    sb.build_all()
    made = set(sb.__dict__) - before
    named = {n for _g, names in PATTERN_PANELS.values() for n in names.split()}
    assert made - {"_render_note"} >= named and not (named & before)
    for key, (_gens, names) in PATTERN_PANELS.items():
        assert f"{key}_opts" in names.split(), key


def test_reading_a_control_builds_its_panel_with_the_settings_shown(make_win):
    w = make_win()
    sb = w.sidebar
    w.state.update(bingo_kind="words", bingo_words="cat, dog")              # set before the panel exists
    assert "bingo" not in sb._built
    assert sb.bingo_kind.value() == "words" and sb.bingo_words.text() == "cat, dog"
    assert "bingo" in sb._built and not sb.shown(sb.bingo_opts)             # built, hidden: not the pattern chosen
    with pytest.raises(AttributeError):
        sb.no_such_control


def test_panels_sit_in_their_order_before_complexity(make_win):
    w = make_win()
    sb = w.sidebar
    for gen in ("crossword", "maze", "bingo", "words"):                     # built out of order
        _set(w, gen=gen)
    lay = sb._panel_lay
    keys = [k for k in PATTERN_PANELS if k in sb._built]
    places = [lay.indexOf(sb._built[k]) for k in keys]
    assert places == sorted(places) and max(places) < lay.indexOf(sb.complexity_row)


def test_presets_undo_and_projects_reach_unbuilt_panels(make_win, tmp_path):
    w = make_win()
    sb = w.sidebar
    _set(w, gen="cryptogram")
    sb.crypto_code.set_value("symbols")                                      # a change made in a built panel
    assert w.state.settings.crypto_code == "symbols"
    w.history.undo()
    assert w.state.settings.crypto_code != "symbols" and sb.crypto_code.value() == w.state.settings.crypto_code
    _set(w, gen="mandala")
    w.state.update(trace_source="words")                                     # e.g. a project or preset sets it
    sb.load()                                                                # load() skips what isn't built yet
    _set(w, gen="trace")
    assert sb.trace_source.value() == "words" and sb.shown(sb.trace_text_row)


def test_the_render_note_reaches_a_panel_built_later(make_win):
    w = make_win()
    sb = w.sidebar
    sb.set_render_note("Left out: hippopotamus (too long)")
    _set(w, gen="words")
    assert sb.ws_note.text() == "Left out: hippopotamus (too long)" and sb.shown(sb.ws_note)


def test_a_mixed_booklet_shows_the_maze_shape(make_win):
    w = make_win()
    sb = w.sidebar
    _set(w, gen="mandala", booklet=True, mix=True)
    assert sb.shown(sb.maze_opts)


def test_every_panel_name_is_a_real_attribute():
    for name, key in sidebar._PANEL_OF.items():
        assert hasattr(sidebar.Sidebar, f"_panel_{key}"), name
