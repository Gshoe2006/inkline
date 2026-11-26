"""The one Qt application object the engine needs for fonts and painting.

Text measuring and painting need a QGuiApplication. The desktop app makes its own; command-line use
and tests get one here, on the offscreen platform when there is no display.
"""

import os

from PySide6.QtCore import QHashSeed
from PySide6.QtGui import QFont, QGuiApplication

# The same fonts index.html asks for, in the same order. Windows has none of them, so it gets its own UI
# font and Arial before the generic fallback (Linux's list, and so its output, stays as it was).
FONT_FAMILIES = ["Cantarell", "Noto Sans", "Inter", "DejaVu Sans"] + \
    (["Segoe UI", "Arial"] if os.name == "nt" else []) + ["sans-serif"]

# Same drawing, same PDF bytes. Qt's PDF engine keeps the fonts a document uses in a QHash and writes
# them out in hash order, which decides each font's object number and subset tag (QTAAAA+Inter-Bold...).
# Qt seeds QHash randomly per process, so a PDF with several weights came out with its fonts shuffled
# from run to run (the text still used the right weights). A fixed seed makes that order repeatable.
# A QHash takes the seed when it first allocates, so this only has to happen before any PDF is
# painted; it's done once, at import, because changing the seed isn't thread-safe and print jobs
# paint on a worker thread. Inkline never hashes untrusted keys, so randomized hashing buys nothing.
QHashSeed.setDeterministicGlobalSeed()


def ensure_app():
    app = QGuiApplication.instance()
    if app is None:
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QGuiApplication([])
    return app


# Joined-up handwriting fonts shipped with Inkline (inkengine/fonts, SIL Open Font License): Playwrite, made for
# teaching children to write, in thirteen countries' school styles. Registered with Qt the first time one is asked for.
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
HAND_FONTS = {"gb": "PlaywriteGBJ-Regular.ttf", "us-trad": "PlaywriteUSTrad-Regular.ttf",
              "us-modern": "PlaywriteUSModern-Regular.ttf", "au": "PlaywriteAUNSW-Regular.ttf", "nz": "PlaywriteNZ-Regular.ttf",
              "ie": "PlaywriteIE-Regular.ttf", "ca": "PlaywriteCA-Regular.ttf", "es": "PlaywriteES-Regular.ttf",
              "mx": "PlaywriteMX-Regular.ttf", "fr": "PlaywriteFRTrad-Regular.ttf", "br": "PlaywriteBR-Regular.ttf",
              "pt": "PlaywritePT-Regular.ttf", "de": "PlaywriteDEVA-Regular.ttf"}
LANGUAGE_HANDS = {"en": "gb", "es": "es", "fr": "fr", "pt": "br", "de": "de"}   # "auto": the school style of Inkline's language
_registered = {}


def joined_family(lang, hand="auto"):
    """The family name of a joined-up handwriting font, registered with Qt: the style chosen, or for "auto" the
    language's (England's for a language without one); "" if it couldn't be loaded (the sheet is then in print)."""
    from PySide6.QtGui import QFontDatabase
    ensure_app()
    file = HAND_FONTS.get(hand) or HAND_FONTS[LANGUAGE_HANDS.get(lang, "gb")]
    if file not in _registered:
        fid = QFontDatabase.addApplicationFont(os.path.join(FONTS_DIR, file))
        families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        _registered[file] = families[0] if families else ""
    return _registered[file]


EASY_FILES = ("AtkinsonHyperlegible-Regular.ttf", "AtkinsonHyperlegible-Bold.ttf")
EASY_LETTERS = 106   # % of the usual letter spacing, for "Easier to read"
EASY_WORDS = 0.16    # extra space between words, in font sizes


def easy_family():
    """Atkinson Hyperlegible (made for readers with low vision, and recommended for dyslexia), registered with Qt;
    "" if it couldn't be loaded."""
    from PySide6.QtGui import QFontDatabase
    ensure_app()
    if "easy" not in _registered:
        name = ""
        for file in EASY_FILES:
            fid = QFontDatabase.addApplicationFont(os.path.join(FONTS_DIR, file))
            families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            name = name or (families[0] if families else "")
        _registered["easy"] = name
    return _registered["easy"]


def make_font(size, weight=400, family="", easy=False):
    """A QFont at a pixel size and CSS weight (400 regular, 700 bold, 900 black); family first if given. easy: the
    clearer font with wider letter and word spacing (Page text → Easier to read), unless a family is asked for
    (joined-up handwriting keeps its own)."""
    ensure_app()
    font = QFont()
    first = [family] if family else ([easy_family()] if easy and easy_family() else [])
    font.setFamilies(first + FONT_FAMILIES)
    font.setPixelSize(max(1, round(size)))
    font.setWeight(QFont.Weight(max(100, min(900, int(weight)))))
    if easy and not family:
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, EASY_LETTERS)
        font.setWordSpacing(size * EASY_WORDS)
    return font
