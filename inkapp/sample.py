"""The sample photo: a mountain lake painted in code (2.x's loadSample), so the converter has something
to show before any photo is opened."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPolygonF, QRadialGradient

from inkengine.photo import Photo
from inkengine.qt import ensure_app
from inkengine.rng import mulberry32


def sample_photo():
    ensure_app()
    img = QImage(1400, 1000, QImage.Format.Format_ARGB32)
    img.fill(QColor("#ffffff"))
    x = QPainter(img)
    x.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    x.setPen(Qt.PenStyle.NoPen)
    g = QLinearGradient(0, 0, 0, 620)
    g.setColorAt(0, QColor("#5a7fb0"))
    g.setColorAt(1, QColor("#f2d6b0"))
    x.fillRect(QRectF(0, 0, 1400, 620), g)
    r = QRadialGradient(QPointF(980, 330), 160)
    r.setColorAt(0, QColor("#fff8e0"))
    r.setColorAt(0.45, QColor("#ffe7a8"))
    r.setColorAt(1, QColor(255, 230, 170, 0))
    x.fillRect(QRectF(800, 150, 360, 360), r)
    rnd = mulberry32(7)

    def ridge(base, amp, c1, c2):
        path = QPainterPath(QPointF(0, 1000))
        y = base
        for px in range(0, 1401, 20):
            y += (rnd() - 0.5) * amp
            y = max(base - amp * 3, min(base + amp, y))
            path.lineTo(px, y)
        path.lineTo(1400, 1000)
        path.closeSubpath()
        gg = QLinearGradient(0, base - amp * 3, 0, 1000)
        gg.setColorAt(0, QColor(c1))
        gg.setColorAt(1, QColor(c2))
        x.fillPath(path, gg)

    ridge(430, 60, "#8a95a8", "#5f6b80")
    ridge(520, 45, "#4f5d70", "#2f3a48")
    g = QLinearGradient(0, 620, 0, 1000)
    g.setColorAt(0, QColor("#c9b79a"))
    g.setColorAt(1, QColor("#47506a"))
    x.fillRect(QRectF(0, 620, 1400, 380), g)
    ridge(700, 35, "#2b3324", "#141a12")
    x.setBrush(QColor("#1a1f16"))
    for _ in range(26):
        tx, th = rnd() * 1400, 80 + rnd() * 140
        ty = 760 + rnd() * 160
        x.drawPolygon(QPolygonF([QPointF(tx, ty - th), QPointF(tx - th * 0.25, ty), QPointF(tx + th * 0.25, ty)]))
    x.end()
    return Photo(img, name="Sample: mountain lake")
