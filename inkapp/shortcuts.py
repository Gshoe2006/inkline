"""Help → Keyboard shortcuts: every shortcut in one list, as the footer only has room for three.

The menus' shortcuts are read from the menus themselves (so Ctrl+E shows whatever Edit → Settings made it save),
then the ones that live outside the menus: the rail's Ctrl+1 to Ctrl+5, Esc, and the keys of the photo and page
lists and of the preview.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLayout, QScrollArea, QVBoxLayout, QWidget

from inkengine.i18n import tr

from . import theme
from .widgets import Section, button, label_as

# the shortcuts that aren't on a menu: (keys, what they do)
SHORTCUT_EXTRAS = [("Ctrl+1 … Ctrl+5", "Create, Photo, Booklet, Poster or Print"),
                   ("Esc", "Stop printing or saving"),
                   ("Return", "In the booklet's page list: change the selected page here"),
                   ("Ctrl+D", "In the booklet's page list: duplicate the selected page"),
                   ("Alt+↑  Alt+↓", "In the photo or page list: move the selected one up or down"),
                   ("Delete", "In the photo or page list: remove the selected one"),
                   ("+  −  0", "With the preview focused: zoom in, zoom out, whole page")]


# the keys' names as a keyboard in the person's language prints them (Entf, Suppr, Intro...)
KEY_NAMES = {"Esc": "Esc", "Return": "Return", "Delete": "Del"}


def key_names(keys):
    """A shortcut's keys with their names in the person's language."""
    return " ".join(tr(KEY_NAMES[k]) if k in KEY_NAMES else k for k in keys.split(" "))


def _plain(text):
    """A menu entry's name without its keyboard letter or the shortcut written after a tab."""
    return text.split("\t")[0].replace("&&", "\0").replace("&", "").replace("\0", "&")


def menu_rows(menu):
    """(name, keys) for each entry of a menu that has a shortcut, in the menu's order."""
    rows = []
    for a in menu.actions():
        if a.isSeparator() or a.menu() is not None:
            continue
        seqs = [k for k in a.shortcuts() if not k.isEmpty()]
        # the Ctrl ones where there are some (Undo's Alt+Backspace and the keyboard's own Undo key aren't worth a line)
        seqs = [k for k in seqs if k.toString().startswith("Ctrl+")] or seqs
        keys = ", ".join(k.toString(QKeySequence.SequenceFormat.NativeText) for k in seqs)
        if not keys and "\t" in a.text():   # written in the entry (Ctrl+C, Ctrl+V, ← →): another widget handles it
            keys = a.text().split("\t", 1)[1]
        if keys:
            name = a.data() if isinstance(a.data(), str) and a.data() else _plain(a.text())   # Undo, not "Undo Age"
            rows.append((name, keys))
    return rows


def all_rows(window):
    """[(section title, [(name, keys)])]: each menu's, then the window's own."""
    groups = [(_plain(m.title()), menu_rows(m)) for m in getattr(window, "_top_menus", [])]
    groups = [(t, rows) for t, rows in groups if rows]
    return groups + [(tr("In the window and its lists"), [(tr(what), key_names(keys)) for keys, what in SHORTCUT_EXTRAS])]


class ShortcutsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle(tr("Keyboard shortcuts"))
        self.setObjectName("shortcuts")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(theme.PAD_X, theme.PAD_X, theme.PAD_X, theme.PAD_X)
        outer.setSpacing(theme.SECTION_GAP)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, theme.PAD_X // 2, 0)
        col.setSpacing(theme.SECTION_GAP)
        self.groups = all_rows(window)
        for title, rows in self.groups:
            sec = Section(title)   # translated already: Section translates it again, which leaves it as it is
            grid = QWidget()
            g = QGridLayout(grid)
            g.setContentsMargins(0, 0, 0, 0)
            g.setHorizontalSpacing(theme.SECTION_GAP)
            g.setVerticalSpacing(theme.LABEL_GAP)
            for i, (name, keys) in enumerate(rows):
                what = label_as(name)
                what.setWordWrap(True)
                g.addWidget(what, i, 0)
                g.addWidget(label_as(keys, "value"), i, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            g.setColumnStretch(0, 1)
            sec.add(grid)
            col.addWidget(sec)
        col.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        close = button("Close", "primary")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        outer.addLayout(row)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.resize(520, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
