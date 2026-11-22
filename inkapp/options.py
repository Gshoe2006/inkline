"""More designs…: several designs for what New design would change, side by side, to choose one.

The window says what a candidate looks like (settings and the page spec to draw for a seed) and what choosing
one does; this dialog draws them off the UI thread, as the page list's pictures are drawn, and fills them in as
they're ready.
"""

import random

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from . import theme, thumbs
from .widgets import Hint, button

COUNT = 6                     # designs shown at once (3 across, 2 down)
LOOK = thumbs.Look(h=190, dpi=40, thicken=1.3, darken=1.4)   # big enough to judge; lines still read


class Options(QDialog):
    """candidate(seed) -> (settings, spec) for a design page; chosen(seed) is called with the one picked."""

    def __init__(self, parent, candidate, chosen, what):
        super().__init__(parent)
        self.setWindowTitle("More designs")
        self.candidate, self.chosen = candidate, chosen
        self.thumbs = thumbs.Thumbnails(LOOK)
        self.thumbs.ready.connect(self._ready)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(theme.PAD_X, theme.PAD_X, theme.PAD_X, theme.PAD_X)
        lay.setSpacing(theme.SECTION_GAP)
        lay.addWidget(Hint(f"Click a design to use it for {what}."))
        grid = QGridLayout()
        grid.setSpacing(theme.PAIR_GAP)
        self.buttons = []
        for i in range(COUNT):
            b = QToolButton()
            b.setObjectName("designOption")
            b.setIconSize(QSize(LOOK.h, LOOK.h))
            b.setFixedSize(LOOK.h + 16, LOOK.h + 16)
            b.setAccessibleName(f"Design {i + 1}")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _c=False, i=i: self._pick(i))
            grid.addWidget(b, i // 3, i % 3)
            self.buttons.append(b)
        lay.addLayout(grid)
        row = QHBoxLayout()
        row.setSpacing(theme.PAIR_GAP)
        self.more = button("Show six more", tip="Draw six other designs")
        self.more.clicked.connect(self.reroll)
        cancel = button("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(self.more)
        row.addStretch(1)
        row.addWidget(cancel)
        lay.addLayout(row)
        self.reroll()

    def reroll(self):
        self.seeds = [random.randrange(10 ** 9) for _ in range(COUNT)]
        self.keys = []
        specs = []
        s = None
        for b, seed in zip(self.buttons, self.seeds):
            s, spec = self.candidate(seed)
            self.keys.append(thumbs.key(s, spec))
            specs.append(spec)
            b.setIcon(QIcon())
            b.setToolTip(f"seed {seed}")
        self._settings = s
        self.thumbs.request(s, specs)

    def _ready(self, k):
        img = self.thumbs.get(k)
        for b, key in zip(self.buttons, self.keys):
            if key == k and img is not None:
                b.setIcon(QIcon(QPixmap.fromImage(img)))

    def _pick(self, i):
        self.chosen(self.seeds[i])
        self.accept()
