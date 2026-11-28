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
    off: str           # a disabled control's text and marks: plainly fainter than muted (High contrast's line is black)


LIGHT = Tokens(bg="#eceff2", panel="#ffffff", ink="#16181d", muted="#5b626e", line="#d3d8de",
               accent="#0b7ea6", accent_ink="#ffffff", table="#d9dee4", field="#f5f7f9", off="#a3aab4")
DARK = Tokens(bg="#121418", panel="#1a1d22", ink="#e7e9ed", muted="#9aa2ad", line="#2d323a",
              accent="#4dc2e6", accent_ink="#06222c", table="#0b0d10", field="#22262c", off="#5a616b")
# more looks, under Edit → Settings → Appearance (each turned on there to be offered); every text colour on its
# background is at least 4.5:1 (WCAG AA), High contrast's at least 10:1
CONTRAST = Tokens(bg="#ffffff", panel="#ffffff", ink="#000000", muted="#2b2b2b", line="#000000",
                  accent="#003f8a", accent_ink="#ffffff", table="#c8c8c8", field="#ededed", off="#8a8a8a")
WARM = Tokens(bg="#efe7da", panel="#fbf7f0", ink="#2b2219", muted="#62564a", line="#d8cbb6",
              accent="#9a4a12", accent_ink="#ffffff", table="#e2d6c3", field="#f6efe4", off="#ab9d89")
SLATE = Tokens(bg="#18202b", panel="#202a37", ink="#e6ebf2", muted="#a3afbf", line="#364357",
               accent="#7db3ff", accent_ink="#0a1830", table="#111821", field="#283444", off="#5f6d82")
THEMES = {"light": LIGHT, "dark": DARK, "contrast": CONTRAST, "warm": WARM, "slate": SLATE}
THEME_NAMES = {"system": "Follow the system", "light": "Light", "dark": "Dark", "contrast": "High contrast",
               "warm": "Warm paper", "slate": "Slate"}
EXTRA_THEMES = ("contrast", "warm", "slate")   # offered only once turned on in Settings
CHOSEN = {"name": "system"}                    # the theme in use: a THEMES key, or "system" (light or dark as it is)

FONT_UI = ["Inter", "Cantarell", "Noto Sans", "Segoe UI", "sans-serif"]
FONT_HEAD = ["Space Grotesk", "Inter", "Cantarell", "Noto Sans", "sans-serif"]
FONT_MONO = ["JetBrains Mono", "IBM Plex Mono", "DejaVu Sans Mono", "monospace"]

# Sizes, in pixels, as 2.x set them.
SIDEBAR_WIDTH = 330
MAX_SIDEBAR_WIDTH = 480   # px: a desktop style with wide controls widens the sidebar this far at most
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

# Touch screens (Android, or Edit → Settings → Appearance): every control at least as tall as a rail button, and a
# window narrower than ONE_COLUMN_WIDTH laid out in one column (the options page and the preview take turns): phones,
# and tablets held upright; beside the rail and the options page a narrower window would leave the preview too little
TOUCH_TARGET = 48          # px: the rail buttons' height, for every control
ONE_COLUMN_WIDTH = 1000    # px: narrower than this, one column
# A tablet held sideways (touch, at least ONE_COLUMN_WIDTH wide): its height is what limits a portrait page, so the
# page gets a narrower margin on the light table, and the options get the room beside the page it can't use, up to
# TOUCH_SIDEBAR_WIDTH (touch-sized lists show more of their text; at 1024 px the preview keeps over half the width)
TOUCH_STAGE_PAD = 12       # px: round the page in the preview, on a touch screen (STAGE_PAD otherwise)
TOUCH_SIDEBAR_WIDTH = 380  # px: the options' width on a tablet, at most
TOUCH = {"on": False}


def _families(fams):
    return ", ".join(f'"{f}"' if " " in f else f for f in fams)


def is_dark():
    app = QGuiApplication.instance()
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:   # Qt before 6.5
        return False


def tokens(dark=None):
    """The colours to use: dark or light when asked (the self-test), else the theme chosen, else the system's."""
    if dark is None and CHOSEN["name"] in THEMES:
        return THEMES[CHOSEN["name"]]
    return DARK if (is_dark() if dark is None else dark) else LIGHT


def offered(shown=()):
    """The themes to choose from: following the system, light and dark, then the extras turned on, in order."""
    return ["system", "light", "dark"] + [k for k in EXTRA_THEMES if k in (shown or ())]


def restore(prefs):
    """At start: the theme chosen last time, if it's still offered (an extra turned off since goes back to the
    system's)."""
    name = prefs.get("theme")
    CHOSEN["name"] = name if name in offered(prefs.get("themes_offered") or ()) else "system"


def use_theme(app, name):
    """Switch to a theme (a THEME_NAMES key) and restyle."""
    CHOSEN["name"] = name if name in THEME_NAMES else "system"
    return apply(app)


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
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, role, c(t.off))
    return p


_ARROW_DIR = None


def _arrow(colour):
    """A small down-pointing triangle in the given colour, as an image file the stylesheet can use (Qt
    stylesheets can't draw one from borders, as 2.x's CSS could)."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF

    def draw(p):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(colour))
        p.drawPolygon(QPolygonF([QPointF(1, 1), QPointF(19, 1), QPointF(10, 11)]))
    return _icon(f"arrow-{colour.lstrip('#')}", 20, 12, draw)


def _tick(colour):
    """A check mark in the given colour, for a ticked checkbox's box."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPen

    def draw(p):
        p.setPen(QPen(QColor(colour), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPolyline([QPointF(2, 6.5), QPointF(5, 9.5), QPointF(10.5, 2.5)])
    return _icon(f"tick-{colour.lstrip('#')}", 12, 12, draw)


def _icon(name, w, h, draw):
    """An image file drawn by draw(painter), for the stylesheet. Drawn fresh into this run's own temporary folder, so
    a stale or someone else's file is never picked up."""
    import os
    import tempfile
    from PySide6.QtGui import QImage, QPainter
    global _ARROW_DIR
    if _ARROW_DIR is None:
        _ARROW_DIR = tempfile.mkdtemp(prefix="inkline-")
    path = os.path.join(_ARROW_DIR, f"{name}.png")
    if not os.path.exists(path):
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw(p)
        p.end()
        img.save(path, "PNG")
    return path.replace("\\", "/")


def touch_wanted(prefs, platform=None, env=None):
    """Whether to lay Inkline out for a finger: always on Android, else as Settings (or INKLINE_TOUCH=1) says."""
    return touch_forced(platform, env) or prefs.get("touch") is True


def touch_forced(platform=None, env=None):
    """Touch mode that Settings can't turn off: on Android, or with INKLINE_TOUCH=1."""
    import os
    import sys
    env = os.environ if env is None else env
    return (platform or sys.platform) == "android" or env.get("INKLINE_TOUCH") == "1"


def stylesheet(t, touch=None):
    touch = TOUCH["on"] if touch is None else touch
    return _stylesheet(t) + (touch_rules(t) if touch else "")


def touch_rules(t):
    """Touch mode's additions: controls a finger can hit (TOUCH_TARGET tall), larger handles and boxes, and text one
    step up the type sizes the stylesheet already uses (13 → 14, 14 → 16)."""
    h = TOUCH_TARGET
    return f"""
* {{ font-size: 16px; }}
QLabel[role="label"], QCheckBox, QComboBox, QLineEdit, QPushButton, QToolButton#toolbarMenu {{ font-size: 14px; }}
QComboBox, QLineEdit, QPushButton, QToolButton#toolbarMenu, QToolButton#foldHead {{ min-height: {h - 2 * 10}px; }}
QComboBox, QLineEdit, QPushButton, QToolButton#toolbarMenu {{ padding: 10px 10px; }}
QPushButton:focus, QComboBox:focus, QLineEdit:focus, QToolButton#toolbarMenu:focus {{ padding: 9px 9px; }}
QPushButton#newDesign {{ padding: 10px 14px; }}
QPushButton#newDesign:focus {{ padding: 9px 13px; }}
QPushButton[role="mini"] {{ font-size: 13px; padding: 10px 12px; }}
QPushButton[role="mini"]:focus {{ padding: 9px 11px; }}
QToolButton#foldHead {{ font-size: 12px; padding: 10px 0; }}
QToolButton#railButton {{ font-size: 13px; min-height: {h}px; }}
QToolButton#bottomButton {{ background: transparent; border: 0; border-top: 3px solid transparent; color: {t.muted};
  font-size: 13px; font-weight: 600; min-height: {h}px; padding: 2px 4px; }}
QToolButton#bottomButton:checked {{ border-top-color: {t.accent}; color: {t.accent}; }}
QToolButton#bottomButton:hover {{ color: {t.ink}; }}
QToolButton#bottomButton:focus {{ border: 2px solid {t.ink}; border-top-width: 3px; padding: 0 2px; }}
QToolButton#bottomButton:disabled {{ color: {t.off}; }}
QFrame#bottomBar {{ background: {t.panel}; border-top: 1px solid {t.line}; }}
QCheckBox::indicator {{ width: 22px; height: 22px; }}
QSlider {{ min-height: {h}px; }}
QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 24px; height: 24px; margin: -9px 0; border-radius: 12px; }}
QScrollBar:vertical {{ width: 12px; }}
QMenu::item {{ padding: 12px 24px; }}
"""


def _stylesheet(t):
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
QFrame#toolbar {{ background: {t.panel}; border-bottom: 1px solid {t.line}; }}
QFrame#toolbar QFrame#brand {{ border: 0; background: transparent; }}
QFrame#rail {{ background: {t.panel}; border-right: 1px solid {t.line}; }}
QFrame#railLine {{ background: {t.line}; border: 0; }}
QToolButton#railButton {{ background: transparent; border: 1px solid transparent; border-radius: 8px; color: {t.muted};
  font-size: 12px; font-weight: 600; padding: 4px; }}
QToolButton#railButton:hover {{ border-color: {t.line}; color: {t.ink}; }}
QToolButton#railButton:checked {{ background: {t.field}; border-color: {t.field}; border-left: 4px solid {t.accent};
  color: {t.accent}; padding-left: 1px; }}
QToolButton#railButton:focus {{ border: 2px solid {t.ink}; padding: 3px; }}
QToolButton#railButton:checked:focus {{ border: 2px solid {t.ink}; border-left: 4px solid {t.accent}; padding: 3px 3px 3px 1px; }}
QToolButton#railButton:disabled {{ color: {t.off}; }}
QToolButton#galleryItem {{ background: {t.field}; border: 1px solid {t.line}; border-radius: 8px; font-size: 11px;
  padding: 4px; }}
QToolButton#galleryItem:hover {{ border-color: {t.accent}; }}
QToolButton#galleryItem:checked {{ border: 2px solid {t.accent}; background: {t.panel}; padding: 3px; }}
QToolButton#galleryItem:focus {{ border: 2px solid {t.ink}; padding: 3px; }}
QToolButton#foldHead {{ background: transparent; border: 0; color: {t.muted}; font-size: 11px; font-weight: 600;
  letter-spacing: 1px; padding: 2px 0; text-align: left; }}
QToolButton#foldHead:hover {{ color: {t.ink}; }}
QToolButton#foldHead:focus {{ color: {t.accent}; text-decoration: underline; }}
QFrame#tourCard {{ background: {t.panel}; border: 1px solid {t.accent}; border-radius: 10px; }}
QFrame#tourOutline {{ background: transparent; border: 3px solid {t.accent}; border-radius: 10px; }}
QLabel#tourTitle {{ font-family: {head}; font-size: 16px; font-weight: 700; }}
QFrame#popupPanel {{ background: {t.panel}; border: 1px solid {t.line}; border-radius: 8px; }}
QToolButton#toolbarMenu {{ font-size: 13px; font-weight: 600; background: {t.field}; border: 1px solid {t.line};
  border-radius: 6px; padding: 7px 9px; }}
QToolButton#toolbarMenu:hover {{ border-color: {t.accent}; }}
QToolButton#toolbarMenu:focus {{ border: 2px solid {t.accent}; padding: 6px 8px; }}
QToolButton#toolbarMenu::menu-indicator {{ image: none; width: 0; }}   /* its text ends in ▾, as Presets' does */
QToolButton#toolbarMenu:disabled {{ color: {t.off}; background: {t.panel}; }}
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
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {t.muted}; border-radius: 4px; background: {t.field}; }}
QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
QCheckBox::indicator:checked {{ background: {t.accent}; border-color: {t.accent}; image: url("{_tick(t.accent_ink)}"); }}
QCheckBox::indicator:disabled {{ background: {t.panel}; border-color: {t.off}; }}
QCheckBox::indicator:checked:disabled {{ background: {t.off}; border-color: {t.off}; image: url("{_tick(t.panel)}"); }}
QSlider::handle:horizontal:focus {{ border: 2px solid {t.ink}; }}
QComboBox::drop-down {{ border: 0; width: 22px; }}
QComboBox::down-arrow {{ image: url("{_arrow(t.muted)}"); width: 10px; height: 6px; margin-right: 8px; }}
QPushButton[role="primary"] {{ background: {t.accent}; color: {t.accent_ink}; border-color: {t.accent}; }}
QPushButton:disabled, QPushButton[role="primary"]:disabled {{ background: {t.panel}; color: {t.off}; border-color: {t.line}; }}
QComboBox:disabled, QLineEdit:disabled {{ background: {t.panel}; color: {t.off}; border-color: {t.line}; }}
QComboBox::down-arrow:disabled {{ image: url("{_arrow(t.off)}"); }}
QLabel[role="label"]:disabled, QCheckBox:disabled, QLabel[role="value"]:disabled {{ color: {t.off}; }}
QSlider::sub-page:horizontal:disabled, QSlider::handle:horizontal:disabled {{ background: {t.off}; }}
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


QListWidget#photoList, QListWidget#pageList {{ background: {t.panel}; border: 2px solid transparent; border-radius: 6px;
  font-size: 12px; }}
QListWidget#photoList:focus, QListWidget#pageList:focus {{ border-color: {t.accent}; }}
QListWidget#photoList::item, QListWidget#pageList::item {{ border: 1px solid {t.line}; border-radius: 6px; padding: 4px; margin-bottom: 4px; }}
QListWidget#photoList::item:selected, QListWidget#pageList::item:selected {{ border-color: {t.accent}; background: {t.field}; color: {t.ink}; }}
QFrame#drop {{ border: 2px dashed {t.line}; border-radius: 8px; }}
QLabel#dropText {{ color: {t.muted}; font-size: 13px; }}
QLabel#dropText[named="true"] {{ color: {t.ink}; font-weight: 600; }}
QLabel#photoName, QLabel#pageName {{ font-size: 12px; }}
QLabel#pageThumb {{ background: {PAPER_COLOUR}; border: 1px solid {t.line}; }}
QTextBrowser#whatsNew {{ background: {t.panel}; border: 1px solid {t.line}; border-radius: 6px; padding: 8px; }}
QToolButton#designOption {{ background: {PAPER_COLOUR}; color: {LIGHT.muted}; border: 1px solid {t.line}; border-radius: 6px; padding: 1px; }}   /* "Drawing…" on white paper, in both themes */
QToolButton#designOption:hover, QToolButton#designOption:focus {{ border: 2px solid {t.accent}; padding: 0; }}

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


# The desktop's own look, as Qt found it before Inkline styled anything (remember_desktop), and whether to use it
# instead of Inkline's (View → Use my desktop's style). Only a copy of Inkline that runs on the system's Qt can
# load the desktop's style (Breeze, Union...); the Flatpak, AppImage and .deb bring their own Qt, which has
# only its plain Fusion style.
DESKTOP = {"style": None, "palette": None, "on": False}
PLAIN = {"fusion", "windows"}   # Qt's own styles: what a copy without the desktop's style plugins finds


def remember_desktop(app):
    """Note the style and colours Qt chose from the desktop, before apply() replaces them."""
    if DESKTOP["style"] is None:
        DESKTOP["style"] = app.style().name()
        DESKTOP["palette"] = QPalette(app.palette())


def desktop_style_name():
    """The desktop's style, as Qt names it ("breeze"), or "" when this copy of Inkline can't load one."""
    name = (DESKTOP["style"] or "").lower()
    return "" if name in PLAIN else name


def apply(app, dark=None):
    """Style the whole application; returns the tokens used (the preview draws its light table with them).
    With the desktop's style on, the widgets keep the desktop's look and colours; the preview's paper and table
    still come from the tokens. Asked for the look the application already has, it changes nothing: setting a
    style or stylesheet again restyles every widget there is (half a second once the window is built)."""
    t = tokens(dark)
    if DESKTOP["on"] and DESKTOP["style"] and not TOUCH["on"]:   # touch sizes are Inkline's own stylesheet
        if _APPLIED["look"] == "desktop" and app.style() is _APPLIED["style"] and not app.styleSheet():
            return t
        app.setStyleSheet("")
        app.setStyle(DESKTOP["style"])
        app.setPalette(DESKTOP["palette"] if DESKTOP["palette"] is not None else app.style().standardPalette())
        _APPLIED.update(look="desktop", style=app.style())
        return t
    pal, sheet = palette(t), stylesheet(t)
    if (_APPLIED["look"] == "inkline" and app.style() is _APPLIED["style"] and app.styleSheet() == sheet
            and app.palette() == pal):
        return t
    app.setStyle("Fusion")
    app.setPalette(pal)
    app.setStyleSheet(sheet)
    _APPLIED.update(look="inkline", style=app.style())
    return t


_APPLIED = {"look": None, "style": None}   # what apply() last left the application with: "inkline" or "desktop"


def use_desktop(app, on):
    """Switch between Inkline's look and the desktop's style."""
    DESKTOP["on"] = bool(on)
    return apply(app)


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
