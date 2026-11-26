"""6.0's window layout: a rail of what you're working on, the options for it, and a toolbar over the preview.

- Rail: Make · Photo (the two modes) and Booklet · Poster · Print (more options for what's made); each shows its own
  page of options beside it.
- Fold: a section of options that opens and closes; the folds on a page take turns, one open at a time, so a page
  fits without scrolling.
- Gallery: the patterns used last as pictures, to choose one by sight (the Pattern list under it has them all).
- Popup: a toolbar button whose panel holds real controls (Presets).
- Touch screens (theme.TOUCH): BottomBar, the rail's entries along the bottom of a phone-width window, with Preview
  (the options page and the preview take turns there); MenuButton, the menu bar's menus in the toolbar, as Android
  has no menu bar.
"""

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QMenu, QScrollArea, QToolButton, QVBoxLayout, QWidget

from inkengine.i18n import tr

from . import theme

RAIL = [("make", "Create"), ("photo", "Photo"), ("booklet", "Booklet"), ("poster", "Poster"), ("print", "Print")]
RAIL_WIDTH = 100
GALLERY = 6                     # patterns shown as pictures
GALLERY_START = ["mandala", "maze", "words", "maths", "crossword", "bingo"]   # before any have been used


class Rail(QFrame):
    """The column of what you're working on. chosen(key) when one is clicked."""
    chosen = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("rail")
        self.setFixedWidth(RAIL_WIDTH)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 12, 8, 12)
        lay.setSpacing(theme.PAIR_GAP)
        self.buttons = {}
        for i, (key, text) in enumerate(RAIL):
            if i == 2:   # the modes, then what's made from them
                line = QFrame()
                line.setObjectName("railLine")
                line.setFixedHeight(1)
                lay.addWidget(line)
            b = QToolButton()
            b.setObjectName("railButton")
            b.setText(tr(text))
            b.setToolTip(tr("{name} ({keys})").format(name=tr(text), keys=f"Ctrl+{i + 1}"))   # the window's shortcut
            b.setCheckable(True)   # not exclusive buttons: those switch on the arrow keys, changing the mode by accident
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            b.setMinimumHeight(48)
            b.clicked.connect(lambda _c=False, k=key: self.chosen.emit(k))
            lay.addWidget(b)
            self.buttons[key] = b
        lay.addStretch(1)
        self.fit_width()

    def fit_width(self):
        """As wide as RAIL_WIDTH, or wider when a label needs it (a longer language, a wider font)."""
        need = max(b.fontMetrics().horizontalAdvance(b.text()) for b in self.buttons.values()) + 16 + 16
        w = max(RAIL_WIDTH, need)
        if self.width() != w or self.minimumWidth() != w:
            self.setFixedWidth(w)
        for b in self.buttons.values():
            b.setFixedWidth(w - 16)

    def changeEvent(self, ev):
        from PySide6.QtCore import QEvent
        if ev.type() in (QEvent.Type.StyleChange, QEvent.Type.FontChange, QEvent.Type.PolishRequest):
            self.fit_width()
        super().changeEvent(ev)

    def showEvent(self, ev):
        self.fit_width()   # once the stylesheet has set the labels' font
        super().showEvent(ev)

    def show_key(self, key):
        """Mark one as chosen (clicking the one already chosen keeps it so)."""
        for k, b in self.buttons.items():
            if b.isChecked() != (k == key):
                b.setChecked(k == key)


class BottomBar(QFrame):
    """The rail's entries along the bottom of a phone-width window, and Preview: chosen(key) when one is tapped
    ("preview" for Preview). The one shown is marked as the rail marks it."""
    chosen = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("bottomBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(0)
        self.buttons = {}
        for i, (key, text) in enumerate(RAIL + [("preview", "Preview")]):
            b = QToolButton()
            b.setObjectName("bottomButton")
            b.setText(tr(text))
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            b.setSizePolicy(b.sizePolicy().horizontalPolicy().Expanding, b.sizePolicy().verticalPolicy())
            b.setMinimumHeight(theme.TOUCH_TARGET)
            b.clicked.connect(lambda _c=False, k=key: self.chosen.emit(k))
            lay.addWidget(b, 1)
            self.buttons[key] = b

    def show_key(self, key):
        for k, b in self.buttons.items():
            if b.isChecked() != (k == key):
                b.setChecked(k == key)


class MenuButton(QToolButton):
    """The menu bar's menus (File, Edit, View, Help: the same menus, so their shortcuts and ticks stay one) from a
    toolbar button, for a touch screen with no menu bar."""

    def __init__(self, menus):
        super().__init__()
        self.setObjectName("toolbarMenu")   # as Presets and More designs
        self.setText(tr("Menu") + "  ▾")   # as Popup's buttons (Presets)
        self.setAccessibleName(tr("Menu"))
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.panel = QMenu(self)
        self.presets = QAction(tr("Presets"), self)   # on a phone, where the toolbar has no room for it
        self.panel.addAction(self.presets)
        self.presets.setVisible(False)
        self.panel.addSeparator()
        for m in menus:
            self.panel.addMenu(m)
        self.setMenu(self.panel)


class Fold(QWidget):
    """A section that opens and closes (its heading is the button). Same .add() as widgets.Section."""
    opened = Signal()

    def __init__(self, title, open_=False):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(theme.HEADING_GAP)
        self.title = tr(title)
        self.head = QToolButton()
        self.head.setObjectName("foldHead")
        self.head.setCheckable(True)
        self.head.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.head.setArrowType(Qt.ArrowType.DownArrow if open_ else Qt.ArrowType.RightArrow)
        self.head.setText(self.title.upper())   # as Section's legend
        self.head.setAccessibleName(self.title)
        self.head.setCursor(Qt.CursorShape.PointingHandCursor)
        self.head.setSizePolicy(self.head.sizePolicy().horizontalPolicy().Expanding,
                                self.head.sizePolicy().verticalPolicy())
        outer.addWidget(self.head)
        self.body = QWidget()
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.ROW_GAP)
        self._lay = lay
        outer.addWidget(self.body)
        self.head.toggled.connect(self._toggled)
        self.head.setChecked(open_)
        self.body.setVisible(open_)

    def add(self, *widgets):
        for w in widgets:
            self._lay.addWidget(w)
        return widgets[0] if len(widgets) == 1 else widgets

    def is_open(self):
        return self.head.isChecked()

    def set_open(self, on):
        self.head.setChecked(bool(on))

    def _toggled(self, on):
        self.body.setVisible(on)
        self.head.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)
        if on:
            self.opened.emit()


class ArrowKeys(QObject):
    """The keyboard in a grid of picture buttons (the gallery's patterns): the arrow keys move to the nearest one that
    way, as they're laid out on the screen (so a search that hides some, or a row that's short, still works), and
    Enter or Return chooses the one focused, as a click does. Up from the top row goes to `above`, if given (All
    patterns' search box); `scroll` is scrolled to keep the focused button in view."""

    DIRS = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}

    def __init__(self, parent, buttons, above=None, scroll=None):
        super().__init__(parent)
        self.buttons, self.above, self._scroll = list(buttons), above, scroll
        for b in self.buttons:
            b.installEventFilter(self)
        if above is not None:
            above.installEventFilter(self)

    @property
    def scroll(self):
        """The scroll area given, else the one the buttons sit in (the gallery, in the sidebar's), if any."""
        if self._scroll is None and self.buttons:
            w = self.buttons[0].parentWidget()
            while w is not None and not isinstance(w, QScrollArea):
                w = w.parentWidget()
            return w
        return self._scroll

    def first(self):
        """The first button shown, in reading order (the top left one)."""
        shown = [b for b in self.buttons if b.isVisibleTo(b.window()) and b.isEnabled()]
        return min(shown, key=lambda b: (b.mapTo(b.window(), b.rect().topLeft()).y(),
                                         b.mapTo(b.window(), b.rect().topLeft()).x()), default=None)

    def eventFilter(self, obj, e):
        if obj is self.above and e.type() == QEvent.Type.KeyPress and e.key() == Qt.Key.Key_Down:
            b = self.first()   # down from the search box: into the pictures
            if b is not None:
                b.setFocus(Qt.FocusReason.TabFocusReason)
                if self.scroll is not None:
                    self.scroll.ensureWidgetVisible(b)
                return True
        if e.type() == QEvent.Type.KeyPress and obj in self.buttons and \
                not e.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                obj.click()
                return True
            if e.key() in self.DIRS:
                target = self.nearest(obj, *self.DIRS[e.key()])
                if target is None and e.key() == Qt.Key.Key_Up and self.above is not None:
                    target = self.above
                if target is not None:
                    target.setFocus(Qt.FocusReason.TabFocusReason)
                    if self.scroll is not None and target in self.buttons:
                        self.scroll.ensureWidgetVisible(target)
                return True   # at the edge: stay (rather than the window turning a booklet's page)
        return super().eventFilter(obj, e)

    def nearest(self, b, dx, dy):
        """The button next to b that way: the nearest along it, keeping to its row or column."""
        top = b.window()
        here = b.mapTo(top, b.rect().center())
        best, score = None, None
        for c in self.buttons:
            if c is b or not c.isVisibleTo(top) or not c.isEnabled():
                continue
            p = c.mapTo(top, c.rect().center()) - here
            along, across = p.x() * dx + p.y() * dy, abs(p.x() * dy - p.y() * dx)
            if along > 2 and (score is None or along + 3 * across < score):
                best, score = c, along + 3 * across
        return best


def one_open(folds):
    """Folds that take turns: opening one closes the others."""
    for f in folds:
        f.opened.connect(lambda f=f: [g.set_open(False) for g in folds if g is not f])


class Gallery(QWidget):
    """The patterns as pictures: picked(gen) when one is clicked."""
    picked = Signal(str)

    def __init__(self, names):
        super().__init__()
        self.names = names
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(theme.PAIR_GAP)
        self.buttons = []
        for i in range(GALLERY):
            b = QToolButton()
            b.setObjectName("galleryItem")
            b.setCheckable(True)
            b.setAutoExclusive(False)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setIconSize(QSize(64, 64))
            b.setMinimumSize(86, 96)
            b.clicked.connect(lambda _c=False, i=i: self._click(i))
            grid.addWidget(b, i // 3, i % 3)
            self.buttons.append(b)
        self.keys = ArrowKeys(self, self.buttons)
        self.gens = []

    def show_gens(self, gens, current):
        """Which patterns, in order, and the one in use (checked, if it's among them)."""
        self.gens = list(gens)[:GALLERY]
        for b, gen in zip(self.buttons, self.gens):
            b.setText(tr(self.names.get(gen, gen)))
            b.setToolTip(tr(self.names.get(gen, gen)))
            b.setAccessibleName(tr(self.names.get(gen, gen)))
            b.setChecked(gen == current)

    def set_picture(self, gen, img):
        if gen in self.gens and img is not None:
            self.buttons[self.gens.index(gen)].setIcon(QIcon(QPixmap.fromImage(img)))

    def _click(self, i):
        if i < len(self.gens):
            for k, b in enumerate(self.buttons):   # the one clicked stays chosen, even clicked again
                b.setChecked(k == i)
            self.picked.emit(self.gens[i])


def recent_patterns(used, known):
    """The gallery's patterns: those used last (newest first), then the starting ones, without repeats."""
    out = []
    for g in list(used or []) + GALLERY_START:
        if g in known and g not in out:
            out.append(g)
    return out[:GALLERY]


class Popup(QToolButton):
    """A toolbar button that opens a panel of real controls under it (Presets). The panel is a popup window of its
    own, so Tab moves through its controls and Escape or a click outside closes it."""

    def __init__(self, text, panel):
        super().__init__()
        self.setText(tr(text) + "  ▾")
        self.setAccessibleName(tr(text))   # without the arrow
        self.setObjectName("toolbarMenu")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.frame = QFrame(self, Qt.WindowType.Popup)
        self.frame.setObjectName("popupPanel")
        lay = QVBoxLayout(self.frame)
        lay.setContentsMargins(theme.PAD_X // 2 + 4, theme.PAD_X // 2 + 4, theme.PAD_X // 2 + 4, theme.PAD_X // 2 + 4)
        lay.addWidget(panel)
        self.frame.setMinimumWidth(320)
        self.panel = panel
        self.clicked.connect(lambda: self.open())

    def open(self, under=None):
        """Show the panel under the button (or under another widget: the Menu button, on a phone), kept on the
        screen, with the focus on its first control."""
        under = under or self
        self.frame.adjustSize()
        pos = under.mapToGlobal(under.rect().bottomLeft())
        screen = under.screen().availableGeometry() if under.screen() else None
        if screen is not None:
            pos.setX(max(screen.left(), min(pos.x(), screen.right() - self.frame.width())))
        self.frame.move(pos)
        self.frame.show()
        self.frame.raise_()
        self.frame.activateWindow()
        self.panel.focusNextChild() if self.panel.focusWidget() is None else None

    def close(self):
        self.frame.hide()


# --- every pattern, as pictures ------------------------------------------------------------------------------------
GROUP_NAMES = {"art": "Colouring and art", "puzzles": "Puzzles", "maths": "Maths", "literacy": "Reading and writing",
               "classroom": "Classroom"}
GROUPS = [("art", ["mandala", "truchet", "contour", "flow", "name", "symmetry"]),
          ("puzzles", ["maze", "dots", "words", "crossword", "sudoku", "kakuro", "nonogram", "spot", "scramble"]),
          ("maths", ["maths", "early", "clock", "fractions"]),
          ("literacy", ["trace", "spelltest", "reading"]),
          ("classroom", ["bingo", "reward", "ruled"])]


def _plain(text):
    """Lower case without accents, to search "maze" in "Laberinto" or "Mosaïque" alike."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def matches(gen, query, names, descriptions, group=""):
    """Whether a pattern answers a search: its name, its description or its kind, in this language or in English."""
    q = _plain(query.strip())
    if not q:
        return True
    texts = [names.get(gen, gen), descriptions.get(gen, ""), gen, group]
    return any(q in _plain(t) or q in _plain(tr(t)) for t in texts if t)


class AllPatterns(QWidget):
    """Every pattern as a picture, by kind, with a search box: picked(gen) when one is clicked. Pictures are drawn
    off the UI thread (thumbs.Thumbnails) and come in as they're ready."""
    picked = Signal(str)

    def __init__(self, names, descriptions, current=None):
        from PySide6.QtWidgets import QLabel, QLineEdit, QScrollArea
        from dataclasses import replace
        from inkengine.page import Settings, single_page
        from . import thumbs
        super().__init__()
        self.names, self.descriptions = names, descriptions
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(theme.SECTION_GAP)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search patterns, e.g. maze, maths, colouring"))
        self.search.setAccessibleName(tr("Search patterns"))
        self.search.setClearButtonEnabled(True)
        outer.addWidget(self.search)
        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.SECTION_GAP)
        self.buttons, self.headings, self._keys = {}, [], {}
        self.thumbs = thumbs.Thumbnails(thumbs.Look(h=80, dpi=16, thicken=1.6, darken=1.6))
        self.thumbs.ready.connect(self._ready)
        base = Settings(seed=20261117)
        specs = []
        for group, gens in GROUPS:
            head = QLabel(tr(GROUP_NAMES[group]).upper())
            head.setProperty("role", "legend")
            lay.addWidget(head)
            grid_w = QWidget()
            grid = QGridLayout(grid_w)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(theme.PAIR_GAP)
            for i, gen in enumerate(g for g in gens if g in names):
                b = QToolButton()
                b.setObjectName("galleryItem")
                b.setCheckable(True)
                b.setChecked(gen == current)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                b.setIconSize(QSize(80, 80))
                b.setMinimumSize(112, 120)
                b.setText(tr(names[gen]))
                b.setToolTip(tr(descriptions.get(gen, names[gen])))
                b.setAccessibleName(tr(names[gen]))
                b.clicked.connect(lambda _c=False, g=gen: self.picked.emit(g))
                grid.addWidget(b, i // 4, i % 4)
                self.buttons[gen] = b
                spec = single_page(replace(base, gen=gen))
                self._keys[thumbs.key(base, spec)] = gen
                specs.append(spec)
            lay.addWidget(grid_w)
            self.headings.append((head, grid_w, gens))
        lay.addStretch(1)
        self.empty = QLabel(tr("No pattern matches. Try another word."))
        self.empty.setProperty("role", "hint")
        self.empty.hide()
        lay.addWidget(self.empty)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        # the keyboard: Down from the search box into the pictures, arrows between them, Enter to choose; Enter in
        # the search box chooses the first match
        self.keys = ArrowKeys(self, self.buttons.values(), above=self.search, scroll=scroll)
        self.search.returnPressed.connect(lambda: self.keys.first() and self.keys.first().click())
        self.search.textChanged.connect(self.filter)
        self.thumbs.request(base, specs)

    def filter(self, query):
        shown = 0
        for (head, grid_w, gens), (group, _g) in zip(self.headings, GROUPS):
            any_here = False
            for g in gens:
                b = self.buttons.get(g)
                if b is None:
                    continue
                ok = matches(g, query, self.names, self.descriptions, GROUP_NAMES[group])
                b.setVisible(ok)
                any_here = any_here or ok
                shown += ok
            head.setVisible(any_here)
            grid_w.setVisible(any_here)
        self.empty.setVisible(shown == 0)
        return shown

    def _ready(self, k):
        gen = self._keys.get(k)
        img = self.thumbs.get(k)
        if gen in self.buttons and img is not None:
            self.buttons[gen].setIcon(QIcon(QPixmap.fromImage(img)))


def show_all_patterns(parent, names, descriptions, current, chosen):
    """The All patterns window: choosing one calls chosen(gen) and closes it."""
    from PySide6.QtWidgets import QDialog
    from .widgets import button
    d = QDialog(parent)
    d.setWindowTitle(tr("All patterns"))
    d.setObjectName("allPatterns")
    lay = QVBoxLayout(d)
    lay.setContentsMargins(theme.PAD_X, theme.PAD_X, theme.PAD_X, theme.PAD_X)
    grid = AllPatterns(names, descriptions, current)
    grid.picked.connect(lambda g: (chosen(g), d.accept()))
    lay.addWidget(grid, 1)
    close = button("Close")
    close.setAutoDefault(False)
    close.clicked.connect(d.reject)
    lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
    d.resize(560, 640)
    d.finished.connect(lambda _r: grid.thumbs.cancel())
    d.grid = grid
    grid.search.setFocus()
    return d
