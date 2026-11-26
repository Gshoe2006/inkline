"""Edit → Settings…: what Inkline starts with, in one place. Changes apply at once, as the menus' do.

- Printing: the printer Print starts with (its margins show on the preview), and the paper size, orientation,
  margin and resolution new projects start with ("Use for this design" puts them on the one open now).
- Saving: what Ctrl+E saves, PDF (as before), PNG or SVG.
- Updates: when Inkline checks (as Help → Check for updates automatically), and a button to check now.
- Language: as View → Language, from the next start.

They're kept in preferences.json (defaults, save_format, the update and language choices) and printer.json, as the
menus keep them.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout

from inkengine import i18n
from inkengine.i18n import tr

from . import config, theme, update_schedule
from .widgets import Hint, OptionRow, Pair, Section, button, check, combo

PAPERS = [("letter", "Letter"), ("a4", "A4")]
ORIENTS = [("portrait", "Portrait"), ("landscape", "Landscape")]
DPIS = [(150, "150 dpi (draft)"), (300, "300 dpi")]
FORMATS = {"pdf": "PDF", "png": "PNG image", "svg": "SVG vector image"}
PRINTER_DEFAULT = {"": "The system's default printer"}
DEFAULT_KEYS = ("paper", "orient", "margin", "dpi")


def defaults(prefs=None):
    """The paper settings new projects start with: {key: value}, only those chosen and allowed."""
    from .sidebar import MARGINS
    prefs = config.read("preferences.json") if prefs is None else prefs
    chosen = prefs.get("defaults") if isinstance(prefs.get("defaults"), dict) else {}
    allowed = {"paper": [v for v, _ in PAPERS], "orient": [v for v, _ in ORIENTS], "margin": [v for v, _ in MARGINS],
               "dpi": [v for v, _ in DPIS]}
    return {k: chosen[k] for k in DEFAULT_KEYS if chosen.get(k) in allowed[k]}


def save_format(prefs=None):
    prefs = config.read("preferences.json") if prefs is None else prefs
    return prefs.get("save_format") if prefs.get("save_format") in FORMATS else "pdf"


def printers():
    """The printers the system knows, by name."""
    try:
        from PySide6.QtPrintSupport import QPrinterInfo
        return list(QPrinterInfo.availablePrinterNames())
    except ImportError:
        return []


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        from .sidebar import MARGINS
        self.window = window
        self.setWindowTitle(tr("Settings"))
        self.setObjectName("settings")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(theme.PAD_X, theme.PAD_X, theme.PAD_X, theme.PAD_X)
        outer.setSpacing(theme.SECTION_GAP)
        columns = QHBoxLayout()   # two columns, so it fits a small laptop's screen
        columns.setSpacing(theme.SECTION_GAP)
        left, right = QVBoxLayout(), QVBoxLayout()
        for col in (left, right):
            col.setSpacing(theme.SECTION_GAP)
            columns.addLayout(col, 1)
        outer.addLayout(columns)
        prefs = config.read("preferences.json") if window.remember else {}
        s = window.state.settings
        start = {**{k: getattr(s, k) for k in DEFAULT_KEYS}, **defaults(prefs)}

        printing = Section("Printing")
        names = printers()
        current = window.print_with if window.print_with in names else ""
        self.printer = combo(list(PRINTER_DEFAULT.items()) + [(n, n) for n in names], current)
        for i, n in enumerate(names, 1):   # the system's names, as they are (not looked up for a translation)
            self.printer.setItemText(i, n)
        printing.add(OptionRow("Printer", self.printer))
        self.paper = combo(PAPERS, start["paper"])
        self.orient = combo(ORIENTS, start["orient"])
        self.margin = combo(MARGINS, start["margin"])
        self.dpi = combo(DPIS, start["dpi"])
        printing.add(Pair(OptionRow("Size", self.paper), OptionRow("Orientation", self.orient)))
        printing.add(Pair(OptionRow("Margin", self.margin), OptionRow("Resolution", self.dpi)))
        printing.add(Hint("New projects start with these. The design open now keeps its own until you use them for it."))
        self.use_now = button("Use for this design", tip="Put this size, orientation, margin and resolution on the "
                                                         "design open now (Undo takes it back)")
        self.use_now.setAutoDefault(False)   # Enter closes the dialog; it doesn't press these
        printing.add(self.use_now)
        left.addWidget(printing)

        looks = Section("Appearance")
        self.theme = combo([])
        looks.add(OptionRow("Theme", self.theme))
        self.desktop = check("Use my desktop's style", window.act_desktop.isChecked())
        self.desktop.setEnabled(window.act_desktop.isEnabled())
        self.desktop.setToolTip(window.act_desktop.toolTip())
        self.desktop.toggled.connect(lambda on: window.act_desktop.isChecked() != on and window.act_desktop.trigger())
        looks.add(self.desktop)
        self.touch = check("Larger controls for touch screens", theme.TOUCH["on"])
        self.touch.setEnabled(not theme.touch_forced())   # always on Android
        self.touch.toggled.connect(lambda on: theme.TOUCH["on"] != on and window.set_touch(on))
        looks.add(self.touch)
        looks.add(Hint("More themes to choose from:"))
        self.extra = {}
        for key in theme.EXTRA_THEMES:
            c = check(theme.THEME_NAMES[key], key in window.themes_offered())
            c.toggled.connect(lambda on, k=key: self._offer(k, on))
            looks.add(c)
            self.extra[key] = c
        self._fill_themes()
        self.theme.currentIndexChanged.connect(self._theme_picked)

        saving = Section("Saving")
        self.format = combo(list(FORMATS.items()), save_format(prefs))
        saving.add(OptionRow("Ctrl+E saves as", self.format))
        saving.add(Hint("The other formats are still in the File menu and under the preview."))
        right.addWidget(saving)

        updates = Section("Updates")
        self.schedule = combo([("off", "Never"), *update_schedule.SCHEDULES.items()], window.updates.schedule())
        can = update_schedule.supported(window.updates.kind)
        for i, key in enumerate(["off", *update_schedule.SCHEDULES]):
            if key in update_schedule.BACKGROUND and not can:
                item = self.schedule.model().item(i)
                item.setEnabled(False)
                item.setToolTip(tr("Only while Inkline is open: a Flatpak or Snap can't check in the background.")
                                if window.updates.kind in ("flatpak", "snap") else tr("Only while Inkline is open, on this system."))
        updates.add(OptionRow("Check for updates automatically", self.schedule))
        self.check_now = button("Check now", tip="Ask GitHub for the latest version now")
        self.check_now.setAutoDefault(False)
        updates.add(self.check_now)
        right.addWidget(updates)

        language = Section("Language")
        chosen = prefs.get("language") if prefs.get("language") in i18n.LANGUAGES else i18n.LANG
        self.language = combo(list(i18n.LANGUAGES.items()), chosen)
        for i, name in enumerate(i18n.LANGUAGES.values()):   # each in its own language, as View → Language has them
            self.language.setItemText(i, name)
        language.add(OptionRow("Language", self.language))
        language.add(Hint("Inkline uses it from the next start."))
        left.addWidget(language)
        left.addStretch(1)
        right.addWidget(looks)
        right.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(theme.PAIR_GAP)
        row.addStretch(1)
        close = button("Close", "primary")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        outer.addLayout(row)

        self.printer.currentIndexChanged.connect(lambda _i: window.set_printer(self.printer.value()))
        for key, c in (("paper", self.paper), ("orient", self.orient), ("margin", self.margin), ("dpi", self.dpi)):
            c.currentIndexChanged.connect(lambda _i, k=key, c=c: self._default(k, c.value()))
        self.use_now.clicked.connect(self._use_now)
        self.format.currentIndexChanged.connect(lambda _i: window.set_save_format(self.format.value()))
        self.schedule.currentIndexChanged.connect(lambda _i: window.updates.set_schedule(self.schedule.value()))
        self.check_now.clicked.connect(lambda: window.updates.check(asked=True))
        self.language.currentIndexChanged.connect(lambda _i: window._choose_language(self.language.value()))
        if not window.remember:   # nothing can be kept: say so rather than seem to keep it
            for c in (self.paper, self.orient, self.margin, self.dpi, self.format, self.schedule, self.language,
                      *self.extra.values()):
                c.setEnabled(False)
        self.setMinimumWidth(640)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def _fill_themes(self):
        """The Theme list: following the system, light, dark, and the extras turned on, the one in use chosen."""
        self.theme.blockSignals(True)
        self.theme.clear()
        for key in theme.offered(self.window.themes_offered()):
            self.theme.addItem(tr(theme.THEME_NAMES[key]), key)
        self.theme.set_value(theme.CHOSEN["name"])
        self.theme.blockSignals(False)

    def _theme_picked(self, _i):
        if self.theme.value() and self.theme.value() != theme.CHOSEN["name"]:
            self.window.set_theme(self.theme.value())

    def _offer(self, key, on):
        self.window.offer_theme(key, on)
        self._fill_themes()

    def _default(self, key, value):
        prefs = config.read("preferences.json")
        chosen = prefs.get("defaults") if isinstance(prefs.get("defaults"), dict) else {}
        err = config.write("preferences.json", {**prefs, "defaults": {**chosen, key: value}}, "Preferences")
        if err:
            self.window._msg(err)

    def _use_now(self):
        self.window.use_paper({"paper": self.paper.value(), "orient": self.orient.value(), "margin": self.margin.value(),
                               "dpi": self.dpi.value()})
