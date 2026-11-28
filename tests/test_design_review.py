"""The 6.2 design review's fixes: what a disabled control looks like, hints that point where things are, one name for
each pattern, Page text on Create, Print… the one primary button, three shortcuts in the footer and the rest under
Help, messages that go, and the "rendering…" pill and the tour's card with a background of their own."""

import re
import time

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from inkapp import layout, sidebar, theme
from inkengine import cbn, i18n
from inkengine.patterns import GENERATORS, NAMES


@pytest.fixture
def make_win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))

    def make(remember=False, size=(1280, 820)):
        from inkapp.window import Window
        w = Window("6.2.0", remember=remember)
        w.resize(*size)
        w.show()
        QApplication.processEvents()
        return w
    return make


def spin(seconds=0.3):
    end = time.time() + seconds
    while time.time() < end:
        QApplication.processEvents()
        time.sleep(0.01)


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def _rule(sheet, selector):
    """The declarations of the stylesheet's rule for exactly this selector list."""
    m = re.search(r"(?m)^" + re.escape(selector) + r" \{\{?([^}]*)\}", sheet)
    assert m, selector
    return m.group(1)


# --- 1, 13, 14: disabled controls, checkboxes, the rail's focus and selection ------------------------------------
@pytest.mark.parametrize("name", sorted(theme.THEMES))
def test_a_disabled_control_looks_disabled_in_every_theme(name):
    t = theme.THEMES[name]
    assert t.off not in (t.ink, t.muted, t.line), name   # High contrast's line is black: off is a grey of its own
    sheet = theme.stylesheet(t, touch=False)
    assert f"color: {t.off}" in _rule(sheet, "QToolButton#railButton:disabled")
    assert f"color: {t.off}" in _rule(sheet, "QComboBox:disabled, QLineEdit:disabled")
    assert f"color: {t.off}" in _rule(sheet, 'QLabel[role="label"]:disabled, QCheckBox:disabled, QLabel[role="value"]:disabled')
    assert f"color: {t.off}" in _rule(sheet, 'QPushButton:disabled, QPushButton[role="primary"]:disabled')
    pal = theme.palette(t)
    assert pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text) == QColor(t.off)
    touch = theme.stylesheet(t, touch=True)
    assert f"color: {t.off}" in _rule(touch, "QToolButton#bottomButton:disabled")   # the bottom bar, the same


def test_checkboxes_have_a_box_you_can_see_and_a_tick():
    for t in theme.THEMES.values():
        sheet = theme.stylesheet(t)
        assert f"border: 1px solid {t.muted}" in _rule(sheet, "QCheckBox::indicator")
        checked = _rule(sheet, "QCheckBox::indicator:checked")
        assert f"background: {t.accent}" in checked and "tick-" in checked


def test_a_disabled_checkbox_label_doesnt_toggle_it(make_win):
    from inkapp.widgets import check
    c = check("Something")
    c.setEnabled(False)
    c.text.mousePressEvent(None)
    assert not c.isChecked()


def test_the_rails_focus_ring_isnt_its_selection(make_win):
    sheet = theme.stylesheet(theme.LIGHT)
    t = theme.LIGHT
    chosen, focus = _rule(sheet, "QToolButton#railButton:checked"), _rule(sheet, "QToolButton#railButton:focus")
    assert f"border-left: 4px solid {t.accent}" in chosen and f"2px solid {t.ink}" in focus and t.accent not in focus
    w = make_win()
    spin()
    assert QApplication.focusWidget() not in w.sidebar.rail.buttons.values()   # nothing on the rail at the start
    photo = w.sidebar.rail.buttons["photo"]
    QTest.mouseClick(photo, Qt.MouseButton.LeftButton)
    assert QApplication.focusWidget() is photo                                 # a click takes the focus along
    assert w.sidebar.rail.buttons["booklet"].isEnabled() is False


# --- 2, 3, 17, 10: hints and labels -----------------------------------------------------------------------------
def _texts(widget):
    out = [lab.text() for lab in widget.findChildren(QLabel)]
    return out + [b.text() for b in widget.findChildren(QPushButton)]


def test_hints_point_where_things_are(make_win):
    from inkapp import settings
    w = make_win()
    sb = w.sidebar
    texts = _texts(sb) + [sb.trace_hint.text()]
    assert not [t for t in texts if "Paper → Names" in t or "Paper → Copies" in t or "under Paper." in t]
    _set(w, gen="trace", trace_source="name")
    assert "Print → Copies and names" in sb.trace_hint.text()
    d = settings.SettingsDialog(w)
    assert any("in the toolbar above the preview" in t for t in _texts(d))


def test_answer_pages_go_by_one_name(make_win):
    w = make_win()
    sb = w.sidebar
    assert sb._binds["key"][0].text.text() == "Answer pages (puzzles, worksheets and colour by number)"
    assert sb.copies_answers.text.text() == "Answer pages at the end"
    assert sb.copies_answer_book.text.text() == "Answer pages in a separate teacher's book"
    assert sb.page_answer_check.text.text() == "Include this page in the answer pages"
    assert sb._binds["pnono_answer"][0].text.text() == "Show the answer on the puzzle"   # on the page, not a page


def test_no_row_repeats_its_section_or_its_neighbour(make_win):
    sb = make_win().sidebar
    assert sb.pack_theme.accessibleName() == "Theme"            # in the Worksheet pack fold
    assert sb.reward_kind.accessibleName() == sb.cal_kind.accessibleName() == "Kind"
    assert sb.page_back.text() == "‹ Back to page list"


# --- 4, 16: colour by number, Complexity's hint ------------------------------------------------------------------
def test_colour_by_number_shows_only_where_it_works(make_win):
    w = make_win()
    sb = w.sidebar
    for gen in GENERATORS:
        _set(w, gen=gen)
        assert sb.shown(sb.cbn_check) == (gen in cbn.CBN_GENS), gen
    _set(w, gen="maze", booklet=True, mix=True)                 # a booklet of every pattern: some can
    assert sb.shown(sb.cbn_check)


def test_complexity_has_one_hint_under_its_slider(make_win):
    w = make_win()
    sb = w.sidebar
    for gen in ("maze", "sudoku", "words", "crossword", "reading", "trace", "maths", "logic", "clock"):
        _set(w, gen=gen)
        assert sb.shown(sb.complexity_hint) and sb.complexity_hint.text().startswith("Complexity"), gen
    _set(w, gen="mandala")
    assert not sb.shown(sb.complexity_hint)
    from inkapp.widgets import Hint, SubOptions
    stray = [h.text() for s in sb.findChildren(SubOptions) for h in s.findChildren(Hint) if h.text().startswith("Complexity")]
    assert stray == []                                          # none left inside the patterns' own options
    lay = sb.complexity_hint.parentWidget().layout()
    i = lay.indexOf(sb.complexity_hint)
    assert lay.itemAt(i - 1).widget().control is sb._binds["complexity"][0]   # straight under the slider


# --- 5, 6: All patterns' empty state, the sample's name -----------------------------------------------------------
def test_no_match_says_so_at_the_top(make_win):
    w = make_win()
    d = layout.show_all_patterns(w, NAMES, dict(sidebar.GEN_OPTIONS), "maze", lambda g: None)
    d.show()
    d.grid.search.setText("zzzz")
    QApplication.processEvents()
    assert d.grid.empty.isVisible() and d.grid.empty.y() < 40


def test_the_sample_photo_is_named_in_your_language():
    from inkapp.sample import sample_photo
    try:
        i18n.set_language("de")
        assert sample_photo().name == "Beispiel: Bergsee"
    finally:
        i18n.set_language("en")


# --- 7: a touch screen's words -----------------------------------------------------------------------------------
def test_touch_hints_say_tap_and_finger(make_win):
    w = make_win()
    sb = w.sidebar
    w.set_touch(True)
    try:
        assert "finger" in sb.drag_hint.text() and "Double-tap" in sb.page_list_hint.text()
        assert sb.paper_hint.text().startswith("For this design. Menu → Edit → Settings")
        _set(w, mode="convert")
        w._rail_key("booklet")
        assert sb.status.text() == "A photo book is made on the Photo page."   # no Ctrl+2 without a keyboard
    finally:
        w.set_touch(False)
    assert "scroll over it to zoom" in sb.drag_hint.text() and "Double-click" in sb.page_list_hint.text()


# --- 8: messages go ----------------------------------------------------------------------------------------------
def test_a_message_goes_with_the_next_change_or_after_a_while(make_win):
    from inkapp.window import STATUS_SECONDS
    w = make_win()
    sb = w.sidebar
    w._msg("Hello")
    assert sb.status.text() == "Hello" and w._status_timer.isActive()
    assert w._status_timer.interval() >= STATUS_SECONDS * 1000 >= 8000
    sb._binds["frame"][0].setChecked(True)                      # a change made: the message was about before
    assert sb.status.text() == ""
    w._msg("Again")
    w._status_timer.timeout.emit()
    assert sb.status.text() == ""
    w._busy(True, "Saving page 1 of 3…")                        # a print's progress stays while it runs
    assert not w._status_timer.isActive()
    sb._binds["frame"][0].setChecked(False)
    assert sb.status.text() == "Saving page 1 of 3…"
    w._busy(False, "")


# --- 9 and the busy pill: one resizeEvent, its own background -----------------------------------------------------
def test_the_rendering_pill_follows_the_window_and_has_its_own_background(make_win):
    from inkapp.preview import Preview
    assert list(Preview.__dict__).count("resizeEvent") == 1
    w = make_win()
    pv = w.preview
    pv.set_busy("rendering…")
    w.resize(1100, 820)
    spin(0.2)
    assert abs(pv.busy.geometry().right() - (pv._stage.width() - 34)) <= 2   # top right, after the resize too
    app = QApplication.instance()
    sheet, pal = app.styleSheet(), QPalette(app.palette())
    try:
        app.setStyleSheet("")                                   # View → Use my desktop's style
        own = QPalette(pal)
        own.setColor(QPalette.ColorRole.Window, QColor(30, 33, 38))
        app.setPalette(own)
        pv.set_busy("rendering…")
        QApplication.processEvents()
        assert pv.busy.contentsMargins().left() == 10           # padded by itself
        img = pv.busy.grab().toImage()
        assert img.pixelColor(pv.busy.width() // 2, pv.busy.height() - 3) == QColor(30, 33, 38)
    finally:
        app.setPalette(pal)
        app.setStyleSheet(sheet)
        pv.set_busy("")


# --- 11, 12: Settings opens big enough, Presets isn't cut off in French ---------------------------------------------
def test_settings_opens_at_its_full_size(make_win):
    from inkapp import settings
    d = settings.SettingsDialog(make_win())
    d.show()
    QApplication.processEvents()
    assert d.height() >= d.sizeHint().height() and d.width() >= d.sizeHint().width()
    assert d.theme.height() >= d.theme.sizeHint().height()


@pytest.mark.parametrize("lang", ["en", "fr", "de"])
def test_presets_fits_its_text(make_win, lang):
    try:
        i18n.set_language(lang)
        w = make_win()
        spin(0.2)
        b = w.sidebar.presets_btn
        assert b.width() >= b.sizeHint().width(), (lang, b.width(), b.sizeHint().width())
    finally:
        i18n.set_language("en")


# --- 15: one short name for each pattern, on two lines in the gallery ----------------------------------------------
def test_each_pattern_has_one_name_and_its_description_as_a_tooltip(make_win):
    sb = make_win().sidebar
    c = sb.gen
    assert [c.itemText(i) for i in range(c.count())] == [NAMES[g] for g, _d in sidebar.GEN_OPTIONS]
    descriptions = dict(sidebar.GEN_OPTIONS)
    assert c.itemData(c.findData("bingo"), Qt.ItemDataRole.ToolTipRole) == descriptions["bingo"]
    _row, second = sb.panel_combos[0]
    assert second.itemText(second.findData("reward")) == NAMES["reward"]


def test_gallery_names_wrap_rather_than_lose_their_middle(make_win):
    from PySide6.QtGui import QFontMetrics, QFont
    fm = QFontMetrics(QFont())
    two = layout.two_lines("Telling the time", fm, fm.horizontalAdvance("Telling the"))
    assert two == "Telling the\ntime"
    assert layout.two_lines("Maze", fm, 200) == "Maze"
    long = layout.two_lines("Kreuzworträtsel", fm, fm.horizontalAdvance("Kreuzwort-"))   # one long word: hyphenated
    assert long == "Kreuzwort-\nrätsel"
    sb = make_win().sidebar
    _set(sb.window(), gen="clock")
    spin(0.2)
    tile = sb.gallery.buttons[sb.gallery.gens.index("clock")]
    assert "…" not in tile.text().split("\n")[0] and tile.text().replace("\n", " ").startswith("Telling")


# --- 18: names turn the Name line on (tests/test_copies.py), 22: Page text on Create, the test page in View ----------
def test_page_text_is_on_create_or_photo_and_the_test_page_in_view(make_win):
    w = make_win()
    sb = w.sidebar
    title = sb._binds["title"][0]
    assert sb._scrolls["make"].isAncestorOf(title)
    assert not sb._scrolls["print"].isAncestorOf(title) and "testpage" not in sb._binds
    _set(w, mode="convert")
    assert sb._scrolls["photo"].isAncestorOf(title) and sb.folds["photo"].is_open()   # written on a photo's page too
    _set(w, mode="make")
    assert sb._scrolls["make"].isAncestorOf(title)
    sb.folds["text"].set_open(True)                             # takes turns with Design
    assert not sb.folds["design"].is_open()
    w.act_test.trigger()                                        # View → Printer test page
    assert w.state.settings.testpage and w.act_test.isChecked() and sb.shown(sb.testpage_hint)
    w.act_test.trigger()
    assert not w.state.settings.testpage and not sb.shown(sb.testpage_hint)
    assert "Edit → Settings" in sb.paper_hint.text()            # Print → Paper is this design's; Settings the defaults


def test_editing_a_booklet_page_opens_design(make_win):
    w = make_win()
    sb = w.sidebar
    _set(w, booklet=True)
    sb.pages_edit.emit(True)
    sb.folds["text"].set_open(True)
    sb.edit_page()
    assert sb.folds["design"].is_open() and sb.page_editor.isAncestorOf(sb._binds["complexity"][0])


# --- 20: a photo style shows the sliders it uses ------------------------------------------------------------------
def test_each_photo_style_shows_its_own_sliders(make_win):
    w = make_win()
    sb = w.sidebar
    _set(w, mode="convert")
    expect = {"fs": {"brightness", "contrast", "threshold", "dot"}, "halftone": {"brightness", "contrast", "dot"},
              "nono": {"brightness", "contrast", "threshold"}, "cbn": {"threshold"}}
    for style, shown in expect.items():
        _set(w, style=style)
        assert {k for k, row in sb.photo_sliders.items() if sb.shown(row)} == shown, style
        assert sb.shown(sb.invert_check) == (style != "cbn")
    from inkapp.widgets import Pair
    assert not any(p.isAncestorOf(sb.invert_check) for p in sb.photo_panel.findChildren(Pair))   # a row of its own


# --- 23, 24: the design's number, one primary button --------------------------------------------------------------
def test_the_design_number_is_in_new_designs_tooltip_and_copies(make_win):
    w = make_win()
    sb = w.sidebar
    assert not [lab for lab in sb.findChildren(QLabel) if lab.property("role") == "seed"]
    n = w.state.settings.seed
    assert f"Design number {n}." in sb.new_design.toolTip() and sb.copy_number in sb.new_design.actions()
    sb.copy_number.trigger()
    assert QApplication.clipboard().text() == str(n) and str(n) in sb.status.text()


def test_print_is_the_one_primary_button_and_photos_have_no_new_design(make_win):
    w = make_win()
    sb = w.sidebar
    primary = [b for b in sb.toolbar.findChildren(QPushButton) if b.property("role") == "primary"]
    assert primary == [sb.print_btn]
    _set(w, mode="convert")
    assert not sb.new_design.isVisible() and not sb.more_btn.isVisible()
    assert not w.act_new.isEnabled() and not w.act_more.isEnabled()
    _set(w, mode="make")
    assert sb.new_design.isVisible() and sb.more_btn.isVisible() and w.act_new.isEnabled()


# --- 21, 25: shortcuts ----------------------------------------------------------------------------------------------
def test_no_two_actions_share_a_shortcut_and_new_project_has_one(make_win):
    from PySide6.QtGui import QAction, QShortcut
    w = make_win()
    seen = {}
    for a in w.findChildren(QAction):
        for k in a.shortcuts():
            if not k.isEmpty():
                assert k.toString() not in seen, (k.toString(), a.text(), seen.get(k.toString()))
                seen[k.toString()] = a.text()
    for sc in w.findChildren(QShortcut):
        if sc.context() == Qt.ShortcutContext.WindowShortcut and not sc.key().isEmpty():
            assert sc.key().toString() not in seen, sc.key().toString()
    acts = {a.text().replace("&", ""): a for a in w.findChildren(QAction)}
    assert acts["New design"].shortcut().toString() == "Ctrl+N"
    assert acts["New project"].shortcut().toString() == "Ctrl+Shift+N"
    assert acts["More designs…"].shortcut().toString() == "Ctrl+Shift+M"


@pytest.mark.parametrize("lang", ["en", "de"])
def test_the_footer_has_three_shortcuts_on_one_line(make_win, lang):
    try:
        i18n.set_language(lang)
        w = make_win(size=(1280, 820))
        spin(0.2)
        keys = w.sidebar.keys
        assert keys.text() == i18n.tr("Ctrl+P print · Ctrl+N new design · ← → pages")
        assert keys.height() < 2 * keys.fontMetrics().lineSpacing()   # one line
        assert keys.width() >= keys.sizeHint().width()
    finally:
        i18n.set_language("en")


def test_help_lists_every_shortcut(make_win, monkeypatch):
    from inkapp.shortcuts import ShortcutsDialog, all_rows
    w = make_win()
    rows = dict(all_rows(w))
    assert ("New project", "Ctrl+Shift+N") in rows["File"] and ("New design", "Ctrl+N") in rows["View"]
    assert ("Undo", "Ctrl+Z") in rows["Edit"]                   # not "Undo Pattern", and only its Ctrl key
    assert any(k.startswith("Ctrl+1") for _n, k in rows["In the window and its lists"])
    shown = []
    monkeypatch.setattr(ShortcutsDialog, "exec", lambda d: shown.append(d) or 0)
    help_menu = next(a.menu() for a in w.menuBar().actions() if a.text() == "&Help")
    next(a for a in help_menu.actions() if a.text() == "&Keyboard shortcuts").trigger()
    assert shown and shown[0].groups == all_rows(w)
