"""The one Qt application object the engine needs for fonts and painting.

Text measuring and painting need a QGuiApplication. The desktop app makes its own; command-line use
and tests get one here, on the offscreen platform when there is no display.
"""

import os

from PySide6.QtCore import QHashSeed
from PySide6.QtGui import QFont, QGuiApplication

# The same fonts index.html asks for, in the same order.
FONT_FAMILIES = ["Cantarell", "Noto Sans", "Inter", "DejaVu Sans", "sans-serif"]

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


def make_font(size, weight=400):
    """A QFont at a pixel size and CSS weight (400 regular, 700 bold, 900 black)."""
    ensure_app()
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPixelSize(max(1, round(size)))
    font.setWeight(QFont.Weight(max(100, min(900, int(weight)))))
    return font
