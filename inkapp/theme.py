"""Inkline's look, in one place: 2.x's colour tokens, fonts and sizes as a Qt palette and stylesheet.

Every widget gets its colours, type and spacing from here (by object name or a "role" property),
never from literals of its own. Light and dark follow the desktop's colour scheme, as 2.x followed
the system's.
"""

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette


@dataclass(frozen=True)
class Tokens:
    bg: str            # window background
    panel: str         # the sidebar
    ink: str           # text
    muted: str         # secondary text
    line: str          # borders and dividers
    accent: str        # process cyan: primary buttons, sliders, focus, selection
    accent_ink: str    # text on the accent
    table: str         # the "light table" the page sits on
    field: str         # inputs and plain buttons


LIGHT = Tokens(bg="#eceff2", panel="#ffffff", ink="#16181d", muted="#5b626e", line="#d3d8de",
               accent="#0b7ea6", accent_ink="#ffffff", table="#d9dee4", field="#f5f7f9")
DARK = Tokens(bg="#121418", panel="#1a1d22", ink="#e7e9ed", muted="#9aa2ad", line="#2d323a",
              accent="#4dc2e6", accent_ink="#06222c", table="#0b0d10", field="#22262c")

FONT_UI = ["Inter", "Cantarell", "Noto Sans", "Segoe UI", "sans-serif"]
FONT_HEAD = ["Space Grotesk", "Inter", "Cantarell", "Noto Sans", "sans-serif"]
FONT_MONO = ["JetBrains Mono", "IBM Plex Mono", "DejaVu Sans Mono", "monospace"]

# Sizes, in pixels, as 2.x set them.
SIDEBAR_WIDTH = 330
PAD_X = 20            # sidebar's side padding
SECTION_GAP = 18      # between sections
ROW_GAP = 10          # between rows in a section
HEADING_GAP = 8       # a section's heading to its first row
LABEL_GAP = 4         # a label to its control
SUB_INDENT = 12       # sub-options' indent, beside a 2 px line
PAIR_GAP = 8          # two controls side by side
STAGE_PAD = 24        # round the page in the preview
SHADOW_BLUR = 30      # the page's shadow
SHADOW_COLOUR = (0, 0, 0, 46)   # its colour: black at 18%, as 2.x's (rgb(0 0 0 / .18))
PAPER_COLOUR = "#ffffff"   # pages are white paper in both themes (the preview's page, the page list's pictures)


def _families(fams):
    return ", ".join(f'"{f}"' if " " in f else f for f in fams)


def is_dark():
    app = QGuiApplication.instance()
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:   # Qt before 6.5
        return False


def tokens(dark=None):
    return DARK if (is_dark() if dark is None else dark) else LIGHT


def palette(t):
    p = QPalette()
    c = QColor
    for role, value in ((QPalette.ColorRole.Window, t.bg), (QPalette.ColorRole.WindowText, t.ink),
                        (QPalette.ColorRole.Base, t.field), (QPalette.ColorRole.AlternateBase, t.panel),
                        (QPalette.ColorRole.Text, t.ink), (QPalette.ColorRole.Button, t.field),
                        (QPalette.ColorRole.ButtonText, t.ink), (QPalette.ColorRole.Highlight, t.accent),
                        (QPalette.ColorRole.HighlightedText, t.accent_ink), (QPalette.ColorRole.ToolTipBase, t.panel),
                        (QPalette.ColorRole.ToolTipText, t.ink), (QPalette.ColorRole.PlaceholderText, t.muted),
                        (QPalette.ColorRole.Mid, t.line), (QPalette.ColorRole.Link, t.accent)):
        p.setColor(role, c(value))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, c(t.muted))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, c(t.muted))
    return p


_ARROW_DIR = None


def _arrow(colour):
    """A small down-pointing triangle in the given colour, as an image file the stylesheet can use (Qt
    stylesheets can't draw one from borders, as 2.x's CSS could). Drawn fresh into this run's own
    temporary folder, so a stale or someone else's file is never picked up."""
    import os
    import tempfile
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QImage, QPainter, QPolygonF
    global _ARROW_DIR
    if _ARROW_DIR is None:
        _ARROW_DIR = tempfile.mkdtemp(prefix="inkline-")
    path = os.path.join(_ARROW_DIR, f"arrow-{colour.lstrip('#')}.png")
    if not os.path.exists(path):
        img = QImage(20, 12, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(colour))
        p.drawPolygon(QPolygonF([QPointF(1, 1), QPointF(19, 1), QPointF(10, 11)]))
        p.end()
        img.save(path, "PNG")
    return path.replace("\\", "/")


def stylesheet(t):
    ui, head, mono = _families(FONT_UI), _families(FONT_HEAD), _families(FONT_MONO)
    return f"""
* {{ font-family: {ui}; font-size: 14px; color: {t.ink}; }}
QMainWindow, QWidget#central {{ background: {t.bg}; }}

QFrame#sidebar {{ background: {t.panel}; border-right: 1px solid {t.line}; }}
QFrame#sidebar QWidget#sidebarColumn {{ background: {t.panel}; }}
QScrollArea#sidebarScroll {{ background: {t.panel}; border: 0; }}
QFrame#brand, QFrame#footer {{ background: {t.panel}; }}
QFrame#brand {{ border-bottom: 1px solid {t.line}; }}
QFrame#footer {{ border-top: 1px solid {t.line}; }}
QLabel#brandName {{ font-family: {head}; font-size: 20px; font-weight: 700; }}
QLabel#brandTag {{ color: {t.muted}; font-size: 12px; }}
QLabel#brandVersion {{ color: {t.muted}; font-family: {mono}; font-size: 11px; }}

QLabel[role="legend"] {{ color: {t.muted}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel[role="label"], QCheckBox {{ font-size: 13px; }}
QLabel[role="value"] {{ color: {t.muted}; font-family: {mono}; font-size: 12px; }}
QLabel[role="hint"], QLabel[role="status"] {{ color: {t.muted}; font-size: 12px; }}
QLabel[role="keys"] {{ color: {t.muted}; font-size: 11px; }}
QLabel[role="seed"] {{ color: {t.muted}; font-family: {mono}; font-size: 12px; }}
QLabel[role="pager"] {{ color: {t.muted}; font-family: {mono}; font-size: 12px; }}
QFrame[role="sub"] {{ border: 0; border-left: 2px solid {t.line}; }}

QComboBox, QLineEdit, QPushButton {{
  font-size: 13px; background: {t.field}; border: 1px solid {t.line}; border-radius: 6px; padding: 7px 9px; }}
QPushButton {{ font-weight: 600; }}
QPushButton:hover, QComboBox:hover {{ border-color: {t.accent}; }}
QPushButton:focus, QComboBox:focus, QLineEdit:focus {{ border: 2px solid {t.accent}; padding: 6px 8px; }}
QCheckBox:focus {{ border: 2px solid {t.accent}; border-radius: 4px; }}
QSlider::handle:horizontal:focus {{ border: 2px solid {t.ink}; }}
QTabBar#modeTabs:focus {{ border: 2px solid {t.accent}; }}
QComboBox::drop-down {{ border: 0; width: 22px; }}
QComboBox::down-arrow {{ image: url("{_arrow(t.muted)}"); width: 10px; height: 6px; margin-right: 8px; }}
QPushButton:disabled {{ color: {t.muted}; border-color: {t.line}; }}
QPushButton[role="primary"] {{ background: {t.accent}; color: {t.accent_ink}; border-color: {t.accent}; }}
QPushButton[role="mini"] {{ font-size: 12px; padding: 3px 8px; }}
QPushButton[role="mini"]:focus {{ padding: 2px 7px; }}
QPushButton#newDesign {{ padding: 7px 14px; }}
QPushButton#newDesign:focus {{ padding: 6px 13px; }}
QComboBox QAbstractItemView {{ background: {t.panel}; border: 1px solid {t.line}; selection-background-color: {t.accent};
  selection-color: {t.accent_ink}; }}
QSlider::groove:horizontal {{ height: 4px; background: {t.line}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {t.accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {t.accent}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QProgressBar {{ background: {t.field}; border: 0; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: {t.accent}; border-radius: 3px; }}

QTabBar#modeTabs {{ background: {t.field}; border: 1px solid {t.line}; border-radius: 8px; }}
QTabBar#modeTabs::tab {{ background: transparent; color: {t.muted}; font-size: 13px; font-weight: 600; padding: 8px;
  margin: 3px; border-radius: 6px; }}
QTabBar#modeTabs::tab:selected {{ background: {t.panel}; color: {t.ink}; }}

QListWidget#photoList, QListWidget#pageList {{ background: {t.panel}; border: 0; font-size: 12px; }}
QListWidget#photoList::item, QListWidget#pageList::item {{ border: 1px solid {t.line}; border-radius: 6px; padding: 4px; margin-bottom: 4px; }}
QListWidget#photoList::item:selected, QListWidget#pageList::item:selected {{ border-color: {t.accent}; background: {t.field}; color: {t.ink}; }}
QFrame#drop {{ border: 2px dashed {t.line}; border-radius: 8px; }}
QLabel#dropText {{ color: {t.muted}; font-size: 13px; }}
QLabel#dropText[named="true"] {{ color: {t.ink}; font-weight: 600; }}
QLabel#photoName, QLabel#pageName {{ font-size: 12px; }}
QLabel#pageThumb {{ background: {PAPER_COLOUR}; border: 1px solid {t.line}; }}

QFrame#infoBar {{ background: {t.bg}; border-bottom: 1px solid {t.line}; }}
QLabel[role="info"] {{ color: {t.muted}; font-family: {mono}; font-size: 12px; }}
QLabel[role="infoBold"] {{ color: {t.ink}; font-family: {mono}; font-size: 12px; font-weight: 600; }}
QWidget#stage {{ background: {t.table}; border: 3px dashed transparent; }}
QWidget#stage[over="true"] {{ border-color: {t.accent}; }}
QLabel#busy {{ background: {t.panel}; color: {t.muted}; font-family: {mono}; font-size: 12px; border: 1px solid {t.line};
  border-radius: 10px; padding: 4px 10px; }}
QMenuBar {{ background: {t.bg}; }}
QMenu {{ background: {t.panel}; border: 1px solid {t.line}; }}
QMenu::item:selected {{ background: {t.accent}; color: {t.accent_ink}; }}
"""


def apply(app, dark=None):
    """Style the whole application; returns the tokens used (the preview draws its light table with them)."""
    t = tokens(dark)
    app.setStyle("Fusion")
    app.setPalette(palette(t))
    app.setStyleSheet(stylesheet(t))
    return t


def follow_system(app, changed=None):
    """Restyle when the desktop switches between light and dark, as 2.x followed the system."""
    def again(*_a):
        apply(app)
        if changed:
            changed()
    try:
        app.styleHints().colorSchemeChanged.connect(again)
    except AttributeError:   # Qt before 6.5: no live switching
        pass
