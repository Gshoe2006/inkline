"""Draws Inkline's Android and Google Play pictures with Qt, from inkline.svg and Inkline's own patterns:

    python3 packaging/android/play/make_graphics.py OUTDIR

The listing's graphics:
- icon-512.png: the store icon, 512×512 with alpha, a full square (Play rounds the corners itself)
- feature-graphic.png: 1024×500, no alpha (Play refuses one with transparency): the name on the left, a mandala
  and a maze from inkengine on the right

build.py also uses app_icons() for the launcher icon in the APK: the plain one (python-for-android's Qt bootstrap
can't take an adaptive icon; the foreground and background layers are still drawn, for Play's icon).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from inkengine.qt import easy_family, ensure_app  # noqa: E402

SVG = os.path.join(ROOT, "inkline.svg")
TOP, BOTTOM = "#2a2e36", "#121418"   # inkline.svg's background gradient
FEATURE = (1024, 500)
ADAPTIVE = 432    # an adaptive icon layer: 108 dp at xxxhdpi; Android shows the middle 66 dp (264 px) for sure
TAGLINE = "Colouring pages, puzzles and worksheets to print"


def _svg_text():
    with open(SVG, encoding="utf-8") as f:
        return f.read()


def _foreground_svg():
    """inkline.svg without its rounded dark square (the first two rects): the page on its own."""
    text = _svg_text()
    for _ in range(2):
        start = text.index("<rect ")
        text = text[:start] + text[text.index("/>", start) + 2:]
    return text


def _render(svg_text, img, rect):
    r = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not r.isValid():
        raise ValueError("make_graphics: inkline.svg didn't load")
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, rect)
    p.end()


def _gradient(p, rect):
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0, QColor(TOP))
    g.setColorAt(1, QColor(BOTTOM))
    p.fillRect(rect, g)


def _blank(w, h, alpha=True):
    ensure_app()
    img = QImage(w, h, QImage.Format.Format_ARGB32 if alpha else QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.transparent if alpha else Qt.GlobalColor.black)
    return img


def legacy_icon(size=512):
    """inkline.svg as it is (the rounded dark square), for launchers without adaptive icons."""
    img = _blank(size, size)
    _render(_svg_text(), img, QRectF(0, 0, size, size))
    return img


def adaptive_background(size=ADAPTIVE):
    img = _blank(size, size)
    p = QPainter(img)
    _gradient(p, QRectF(0, 0, size, size))
    p.end()
    return img


def adaptive_foreground(size=ADAPTIVE):
    """The page from inkline.svg, small enough to stay inside the safe middle 66 of 108 dp whatever the mask."""
    img = _blank(size, size)
    side = size * 0.66   # the page's corners (116 of the svg's 256 units from its middle) inside that circle
    off = (size - side) / 2
    _render(_foreground_svg(), img, QRectF(off, off, side, side))
    return img


def store_icon(size=512):
    """Play's icon: a full square (Play masks the corners), the adaptive icon's two layers, the page larger."""
    img = adaptive_background(size)
    side = size * 1.04
    off = (size - side) / 2
    _render(_foreground_svg(), img, QRectF(off, off, side, side))
    return img


def _page(p, rect, angle, gen, seed, c):
    """A white sheet with one of Inkline's patterns on it, turned a little, with a soft shadow."""
    from inkengine.box import Box
    from inkengine.canvas import QtCanvas
    from inkengine.page import Settings, draw_design, geometry
    s = Settings(gen=gen, seed=seed, complexity=c, dpi=150)
    p.save()
    p.translate(rect.center())
    p.rotate(angle)
    w, h = rect.width(), rect.height()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 60))
    p.drawRoundedRect(QRectF(-w / 2 + 4, -h / 2 + 6, w, h), 6, 6)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(-w / 2, -h / 2, w, h), 6, 6)
    p.translate(-w / 2, -h / 2)
    m = w * 0.09
    draw_design(QtCanvas(p, w, h), geometry(s), Box(m, m, w - 2 * m, h - 2 * m), gen, seed, c, s, 2.2)
    p.restore()


def feature_graphic():
    w, h = FEATURE
    img = _blank(w, h, alpha=False)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    _gradient(p, QRectF(0, 0, w, h))
    _page(p, QRectF(560, 70, 300, 388), 8, "maze", 61, 4)
    _page(p, QRectF(700, 40, 300, 388), -6, "mandala", 20261117, 6)
    p.end()
    icon = adaptive_foreground(200)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.drawImage(QPointF(40, 150), icon)
    family = easy_family()
    title = QFont(family) if family else QFont()
    title.setPixelSize(84)
    title.setBold(True)
    p.setFont(title)
    p.setPen(QColor("#ffffff"))
    p.drawText(QRectF(230, 160, 380, 100), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Inkline")
    sub = QFont(family) if family else QFont()
    sub.setPixelSize(27)
    p.setFont(sub)
    p.setPen(QColor("#cfd5dc"))
    p.drawText(QRectF(236, 262, 330, 90), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
               | Qt.TextFlag.TextWordWrap, TAGLINE)
    p.end()
    return img


def _save(img, path):
    if not img.save(path, "PNG"):
        raise OSError(f"make_graphics: couldn't write {path}")
    return path


def app_icons(out):
    """The launcher icons build.py gives buildozer: {"icon": plain, "foreground": ..., "background": ...} paths."""
    os.makedirs(out, exist_ok=True)
    return {"icon": _save(legacy_icon(512), os.path.join(out, "icon.png")),
            "foreground": _save(adaptive_foreground(), os.path.join(out, "icon_fg.png")),
            "background": _save(adaptive_background(), os.path.join(out, "icon_bg.png"))}


def listing_graphics(out):
    os.makedirs(out, exist_ok=True)
    return {"icon": _save(store_icon(512), os.path.join(out, "icon-512.png")),
            "feature": _save(feature_graphic(), os.path.join(out, "feature-graphic.png"))}


def main(argv):
    if len(argv) != 1:
        raise SystemExit(__doc__)
    for kind, path in listing_graphics(argv[0]).items():
        print(kind, path)


if __name__ == "__main__":
    main(sys.argv[1:])
