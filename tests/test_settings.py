"""Edit → Settings…: printing defaults, what Ctrl+E saves, when to check for updates, and the language."""

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import config, settings, update_schedule


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


@pytest.fixture
def make_win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    asked = []
    monkeypatch.setattr(update_schedule, "apply", lambda schedule, kind=None, **kw: asked.append(schedule) or "")
    monkeypatch.setattr(settings, "printers", lambda: ["Office", "Lab"])

    def make(remember=True):
        from inkapp.window import Window
        w = Window("5.7.0", remember=remember)
        w.updates.kind = "deb"
        w.asked = asked
        return w
    return make


def test_the_edit_menu_opens_settings(make_win):
    w = make_win()
    edit = next(a.menu() for a in w.menuBar().actions() if a.text() == "&Edit")
    item = next(a for a in edit.actions() if a.text() == "&Settings…")
    assert item.shortcut().toString() == "Ctrl+,"
    shown = []
    from inkapp.settings import SettingsDialog
    SettingsDialog.exec = lambda dlg: shown.append(dlg) or 0
    try:
        item.trigger()
    finally:
        del SettingsDialog.exec
    assert len(shown) == 1 and shown[0].windowTitle() == "Settings"


def test_paper_defaults_are_for_new_projects(make_win):
    w = make_win()
    d = settings.SettingsDialog(w)
    assert d.paper.value() == w.state.settings.paper == "letter"
    d.paper.set_value("a4")
    d.orient.set_value("landscape")
    d.margin.set_value(0.25)
    d.dpi.set_value(150)
    assert config.read("preferences.json")["defaults"] == {"paper": "a4", "orient": "landscape", "margin": 0.25,
                                                           "dpi": 150}
    assert w.state.settings.paper == "letter"              # the design open now keeps its own
    w.new_project()
    s = w.state.settings
    assert (s.paper, s.orient, s.margin, s.dpi) == ("a4", "landscape", 0.25, 150)
    assert settings.defaults({"defaults": {"paper": "a3", "dpi": 300, "margin": "x"}}) == {"dpi": 300}   # only allowed


def test_a_first_start_uses_the_defaults(make_win):
    config.write("preferences.json", {"defaults": {"paper": "a4", "margin": 1.0}}, "Preferences")
    w = make_win()
    assert w.state.settings.paper == "a4" and w.state.settings.margin == 1.0
    w._save_settings()
    config.write("preferences.json", {"defaults": {"paper": "letter"}}, "Preferences")
    assert make_win().state.settings.paper == "a4"          # the last session's own settings come back instead


def test_use_for_this_design_and_undo(make_win):
    w = make_win()
    d = settings.SettingsDialog(w)
    d.paper.set_value("a4")
    d.margin.set_value(1.0)
    d.use_now.click()
    assert w.state.settings.paper == "a4" and w.state.settings.margin == 1.0
    assert w.sidebar._binds["paper"][0].value() == "a4"     # the Paper section shows it too
    QApplication.processEvents()
    assert "Use my paper settings" in w.history.undoText()
    w.history.undo()                                         # one Undo takes it all back
    assert w.state.settings.paper == "letter" and w.state.settings.margin == 0.5


def test_ctrl_e_saves_the_chosen_format(make_win):
    w = make_win()
    assert w.act_pdf.shortcut().toString() == "Ctrl+E" and w.act_png.shortcut().toString() == "Ctrl+Shift+E"
    d = settings.SettingsDialog(w)
    d.format.set_value("png")
    assert w.act_png.shortcut().toString() == "Ctrl+E" and w.act_pdf.shortcut().toString() == "Ctrl+Shift+E"
    assert w.sidebar.png_btn.toolTip() == "Save PNG (Ctrl+E)" and w.sidebar.pdf_btn.toolTip() == "Save PDF (Ctrl+Shift+E)"
    assert "Ctrl+E PNG" in w.sidebar.keys.text()             # the shortcuts line under the buttons too
    d.format.set_value("svg")
    assert w.act_svg.shortcut().toString() == "Ctrl+E" and w.act_pdf.shortcut().toString() == ""
    assert w.sidebar.svg_btn.toolTip().endswith("(Ctrl+E)")
    w.state.update(mode="convert", style="floyd")            # a photo in pixels can't be SVG: Ctrl+E saves PDF
    w.sidebar.load()
    w._changed("mode")
    QApplication.processEvents()
    assert not w.sidebar.svg_btn.isEnabled() and w.act_pdf.shortcut().toString() == "Ctrl+E"
    assert "Ctrl+E PDF" in w.sidebar.keys.text()
    w.state.update(mode="make")
    w.sidebar.load()
    w._changed("mode")
    QApplication.processEvents()
    assert w.act_svg.shortcut().toString() == "Ctrl+E"
    again = make_win()                                       # kept for the next start
    assert again.act_svg.shortcut().toString() == "Ctrl+E" and again.act_png.shortcut().toString() == "Ctrl+Shift+E"


def test_updates_and_language(make_win):
    w = make_win()
    d = settings.SettingsDialog(w)
    assert d.schedule.value() == "off"
    d.schedule.set_value("weekly")
    prefs = config.read("preferences.json")
    assert prefs["update_check"] is True and prefs["update_schedule"] == "weekly"
    assert w.updates.schedule_actions["weekly"].isChecked()  # the Help menu agrees
    checks = []
    w.updates.check = lambda asked=True: checks.append(asked)
    d.check_now.click()
    assert checks == [True]
    d.language.set_value("fr")
    assert config.read("preferences.json")["language"] == "fr" and w.lang_actions["fr"].isChecked()
    assert [d.language.itemText(i) for i in range(d.language.count())][:2] == ["English", "Español"]


def test_a_flatpak_cant_choose_background_checks(make_win, monkeypatch):
    w = make_win()
    w.updates.kind = "flatpak"
    d = settings.SettingsDialog(w)
    model = d.schedule.model()
    enabled = {d.schedule.itemData(i): model.item(i).isEnabled() for i in range(d.schedule.count())}
    assert enabled == {"off": True, "start": True, "login": False, "daily": False, "weekly": False}


def test_the_printer(make_win, monkeypatch):
    w = make_win()
    d = settings.SettingsDialog(w)
    assert [d.printer.itemData(i) for i in range(d.printer.count())] == ["", "Office", "Lab"]
    d.printer.set_value("Lab")
    assert w.printer_name == "Lab" and config.read("printer.json")["name"] == "Lab"
    import inkapp.window as win_mod
    named = []

    class Printer(win_mod.QPrinter):
        def setPrinterName(self, name):
            named.append(name)
            super().setPrinterName(name)

    class Dialog:
        DialogCode = win_mod.QPrintDialog.DialogCode

        def __init__(self, printer, parent):
            pass

        def setOption(self, *a):
            pass

        def exec(self):
            return self.DialogCode.Rejected
    monkeypatch.setattr(win_mod, "QPrinter", Printer)
    monkeypatch.setattr(win_mod, "QPrintDialog", Dialog)
    w.print_()
    assert named == ["Lab"]                                  # Print starts with it
    w._remember_printer("Office")                            # printing once to another printer
    assert w.printer_name == "Office" and w.print_with == "Lab"
    named.clear()
    w.print_()
    assert named == ["Lab"]                                  # still starts with the one chosen in Settings
    assert make_win().print_with == "Lab"
    d.printer.set_value("")
    assert w.printer_name == "" and config.read("printer.json")["name"] == ""
    named.clear()
    w.print_()
    assert named == []                                       # the system's own default


def test_nothing_to_keep_without_remembering(make_win):
    w = make_win(remember=False)
    d = settings.SettingsDialog(w)
    assert not d.paper.isEnabled() and not d.format.isEnabled() and not d.language.isEnabled()
    assert d.check_now.isEnabled() and d.use_now.isEnabled()


def test_it_fits_a_small_screen(make_win):
    """A small laptop's 768-pixel screen, less the panel and title bar: every control at its full height."""
    from inkengine import i18n
    for lang in ("en", "de"):
        try:
            i18n.set_language(lang)
            d = settings.SettingsDialog(make_win())
            assert d.sizeHint().height() <= 600, (lang, d.sizeHint())
        finally:
            i18n.set_language("en")
