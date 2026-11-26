"""A short tour of the 6.0 window: the first time it opens (and from Help → Tour of the window), a card points at the
rail, the gallery, the toolbar, the sections and Settings in turn, with an outline round each. Back, Next and Skip;
Escape skips. Once finished or skipped it isn't shown again (preferences.json "tour_seen").
"""

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from inkengine.i18n import tr

from . import config, theme
from .widgets import button, label

# what each step points at (found on the window by target()), with its title and text
TOUR_TITLES = {"rail": "Choose what you're working on", "gallery": "Pick a pattern by its picture",
               "toolbar": "Make, save and print", "sidebar": "One section open at a time", "menu": "Settings and themes"}
TOUR_TEXTS = {
    "rail": "Create makes up a design and Photo converts one; Booklet, Poster and Print hold more options. Ctrl+1 to "
            "Ctrl+5 choose them from the keyboard.",
    "gallery": "The patterns you used last are here. All patterns… shows every one, by kind, with a search box.",
    "toolbar": "Presets, New design and More designs, then save as PDF, PNG or SVG, or print.",
    "sidebar": "On Print and Booklet, opening a section closes the others, so every page fits without scrolling.",
    "menu": "Edit → Settings (Ctrl+,) has printing defaults, what Ctrl+E saves, updates, the language and the themes."}
STEPS = [(k, TOUR_TITLES[k], TOUR_TEXTS[k]) for k in TOUR_TITLES]
CARD_W = 320


def target(window, name):
    sb = window.sidebar
    bottom = getattr(window, "bottom", None)
    menu_btn = getattr(window, "menu_btn", None)
    rail = bottom if bottom is not None and bottom.isVisible() else sb.rail   # one column: the bottom bar
    menus = menu_btn if menu_btn is not None and menu_btn.isVisible() else window.menuBar()   # touch: Menu button
    return {"rail": rail, "gallery": sb.gallery, "toolbar": sb.toolbar, "sidebar": sb, "menu": menus}[name]


class Tour(QFrame):
    """The tour's card and the outline round what it points at; both are children of the window."""

    def __init__(self, window, done=None):
        super().__init__(window)
        self.window, self.done, self.i = window, done, 0
        self.setObjectName("tourCard")
        self.setFixedWidth(CARD_W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(theme.PAD_X, 16, theme.PAD_X, 16)
        lay.setSpacing(theme.ROW_GAP)
        self.count = label("", "legend")
        self.title = QLabel()
        self.title.setObjectName("tourTitle")
        self.title.setWordWrap(True)
        self.text = label("", "hint")
        self.text.setWordWrap(True)
        lay.addWidget(self.count)
        lay.addWidget(self.title)
        lay.addWidget(self.text)
        row = QHBoxLayout()
        row.setSpacing(theme.PAIR_GAP)
        self.skip = button("Skip tour", "mini")
        self.back = button("Back")
        self.next = button("Next", "primary")
        self.skip.clicked.connect(self.finish)
        self.back.clicked.connect(lambda: self.go(self.i - 1))
        self.next.clicked.connect(lambda: self.go(self.i + 1) if self.i + 1 < len(STEPS) else self.finish())
        row.addWidget(self.skip)
        row.addStretch(1)
        row.addWidget(self.back)
        row.addWidget(self.next)
        lay.addLayout(row)
        self.outline = QFrame(window)
        self.outline.setObjectName("tourOutline")
        self.outline.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        window.installEventFilter(self)

    def start(self):
        if self.window.sidebar.page_key() != "make":   # the gallery is on Create
            self.window.sidebar.show_page("make")
        self.go(0)
        self.next.setFocus()

    def go(self, i):
        self.i = max(0, min(i, len(STEPS) - 1))
        name, title, text = STEPS[self.i]
        self.count.setText(tr("{i} of {n}").format(i=self.i + 1, n=len(STEPS)).upper())
        self.title.setText(tr(title))
        self.text.setText(tr(text))
        self.back.setEnabled(self.i > 0)
        self.next.setText(tr("Done") if self.i == len(STEPS) - 1 else tr("Next"))
        self.place()
        self.show()
        self.raise_()

    def place(self):
        """The outline round the step's part of the window, the card beside it (right of it, or under it)."""
        w = self.window
        t = target(w, STEPS[self.i][0])
        r = QRect(t.mapTo(w, QPoint(0, 0)), t.size())
        self.outline.setGeometry(r.adjusted(-3, -3, 3, 3))
        self.outline.show()
        self.outline.raise_()
        self.resize(CARD_W, self.layout().totalHeightForWidth(CARD_W))   # as tall as its wrapped text
        if r.height() > r.width() * 1.2:   # a column (the rail, the options): beside it
            x, y = r.right() + 16, r.top() + 40
        else:                              # a row (the toolbar, the menu) or the gallery: under it
            x, y = r.left() + 24, r.bottom() + 16
        x = max(8, min(x, w.width() - self.width() - 8))
        y = max(8, min(y, w.height() - self.height() - 8))
        self.move(x, y)

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if obj is self.window and ev.type() == QEvent.Type.Resize and self.isVisible():
            self.place()
        return False

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.finish()
            return
        super().keyPressEvent(e)

    def finish(self):
        self.hide()
        self.outline.hide()
        self.window.removeEventFilter(self)
        if self.done:
            self.done()


def due(remember):
    return remember and not config.read("preferences.json").get("tour_seen")


def mark_seen():
    config.write("preferences.json", {**config.read("preferences.json"), "tour_seen": True}, "Preferences")
