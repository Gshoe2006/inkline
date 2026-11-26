"""6.0's window layout: a rail of what you're working on, the options for it, and a toolbar over the preview.

- Rail: Make · Photo (the two modes) and Booklet · Poster · Print (more options for what's made); each shows its own
  page of options beside it.
- Fold: a section of options that opens and closes; the folds on a page take turns, one open at a time, so a page
  fits without scrolling.
- Gallery: the patterns used last as pictures, to choose one by sight (the Pattern list under it has them all).
- Popup: a toolbar button whose panel holds real controls (Presets).
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFrame, QGridLayout, QMenu, QToolButton, QVBoxLayout, QWidget,
                               QWidgetAction)

from inkengine.i18n import tr

from . import theme

RAIL = [("make", "Create"), ("photo", "Photo"), ("booklet", "Booklet"), ("poster", "Poster"), ("print", "Print")]
RAIL_WIDTH = 92
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
        self.group = QButtonGroup(self)
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
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            b.setFixedWidth(RAIL_WIDTH - 16)
            b.setMinimumHeight(48)
            b.clicked.connect(lambda _c=False, k=key: self.chosen.emit(k))
            self.group.addButton(b)
            lay.addWidget(b)
            self.buttons[key] = b
        lay.addStretch(1)

    def show_key(self, key):
        b = self.buttons.get(key)
        if b is not None and not b.isChecked():
            b.setChecked(True)


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
            self.picked.emit(self.gens[i])


def recent_patterns(used, known):
    """The gallery's patterns: those used last (newest first), then the starting ones, without repeats."""
    out = []
    for g in list(used or []) + GALLERY_START:
        if g in known and g not in out:
            out.append(g)
    return out[:GALLERY]


class Popup(QToolButton):
    """A toolbar button whose panel holds real controls (a widget), shown under it."""

    def __init__(self, text, panel):
        super().__init__()
        self.setText(tr(text))
        self.setObjectName("toolbarMenu")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(self)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(theme.PAD_X // 2, theme.PAD_X // 2, theme.PAD_X // 2, theme.PAD_X // 2)
        lay.addWidget(panel)
        holder.setMinimumWidth(300)
        act = QWidgetAction(menu)
        act.setDefaultWidget(holder)
        menu.addAction(act)
        self.setMenu(menu)
        self.panel = panel
