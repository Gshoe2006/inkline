"""The right-hand side: an info bar over a true-to-scale sheet of paper on the light table (2.x's main).

The page is drawn with a soft shadow, scaled to fit. While the renderer works, a "rendering…" badge
shows top right. Posters show their sheets' outlines, shared overlap strips and names. With a photo
open, dragging the page moves the photo across its overhang and the wheel zooms it; images dropped
anywhere on the window are opened (the window handles drop and paste).
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from inkengine.i18n import tr
from inkengine.poster import row_name, sheet_rect

from . import theme
from .widgets import label_as


class Page(QWidget):
    """The sheet itself: the rendered image, scaled to fit, keeping its aspect ratio."""

    pan = Signal(float, float)    # how far the pointer moved, in page pixels at the preview's resolution
    zoom = Signal(int)            # +1 wheel up, -1 down
    pan_end = Signal()

    def __init__(self):
        super().__init__()
        self.image = None
        self.poster = None        # a poster's geometry: draw the sheet overlay
        self.dead = None          # the printer's dead strip: (left, top, right, bottom) as shares of the page
        self.pannable = False
        self._drag = None
        self.setMinimumSize(200, 200)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(theme.SHADOW_BLUR)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(*theme.SHADOW_COLOUR))
        self.setGraphicsEffect(shadow)
        self.setAccessibleName(tr("Page preview"))

    def set_image(self, image, poster=None):
        self.image, self.poster = image, poster
        self.updateGeometry()
        self.update()

    def page_rect(self):
        if not self.image:
            return QRectF()
        w, h = self.image.width(), self.image.height()
        s = min(self.width() / w, self.height() / h)
        return QRectF((self.width() - w * s) / 2, (self.height() - h * s) / 2, w * s, h * s)

    def paintEvent(self, _e):
        if not self.image:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        r = self.page_rect()
        p.drawImage(r, self.image)
        if self.poster:
            self._overlay(p, r)
        if self.dead:
            self._dead_strip(p, r)
        p.end()

    def set_dead(self, shares):
        if shares != self.dead:
            self.dead = shares
            self.update()

    def _dead_strip(self, p, r):
        """Hatch the edge of the sheet the printer can't reach (preview only)."""
        left, top, right, bottom = self.dead
        # drawn on the paper, which is white in both themes: the light theme's muted grey shows on it
        brush = QBrush(QColor(theme.LIGHT.muted), Qt.BrushStyle.BDiagPattern)
        lw, th, rw, bh = left * r.width(), top * r.height(), right * r.width(), bottom * r.height()
        for strip in (QRectF(r.x(), r.y(), r.width(), th), QRectF(r.x(), r.bottom() - bh, r.width(), bh),
                      QRectF(r.x(), r.y() + th, lw, r.height() - th - bh),
                      QRectF(r.right() - rw, r.y() + th, rw, r.height() - th - bh)):
            if strip.width() > 0 and strip.height() > 0:
                p.fillRect(strip, brush)

    def _overlay(self, p, r):
        """Sheet outlines, shared overlap strips and sheet names over the whole poster (preview only)."""
        P, t = self.poster, theme.tokens()
        k = r.width() / P.W
        accent = QColor(t.accent)
        strip = QColor(accent)
        strip.setAlpha(33)
        for c in range(1, P.cols):
            p.fillRect(QRectF(r.x() + c * (P.pw - P.o) * P.dpi * k, r.y(), P.o * P.dpi * k, r.height()), strip)
        for row in range(1, P.rows):
            p.fillRect(QRectF(r.x(), r.y() + row * (P.ph - P.o) * P.dpi * k, r.width(), P.o * P.dpi * k), strip)
        pen = QPen(accent, 1.5, Qt.PenStyle.DashLine)
        f = QFont()
        f.setPixelSize(max(12, int(r.width() / 40)))
        f.setBold(True)
        p.setFont(f)
        for i in range(P.sheets):
            c, row, b = sheet_rect(P, i)
            rect = QRectF(r.x() + b.x * k, r.y() + b.y * k, b.w * k, b.h * k).adjusted(1, 1, -1, -1)
            p.setPen(pen)
            p.drawRect(rect)
            name = f"{row_name(row)}{c + 1}"
            tw = p.fontMetrics().horizontalAdvance(name) + 12
            tag = QRectF(rect.x() + 3, rect.y() + 3, tw, p.fontMetrics().height() + 4)
            p.fillRect(tag, accent)
            p.setPen(QColor(t.accent_ink))
            p.drawText(tag, Qt.AlignmentFlag.AlignCenter, name)

    # drag to move the photo, wheel to zoom it
    def mousePressEvent(self, e):
        if self.pannable and e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None and self.image:
            k = self.image.width() / max(1.0, self.page_rect().width())   # screen pixels to page pixels
            d = e.position() - self._drag
            self.pan.emit(d.x() * k, d.y() * k)

    def mouseReleaseEvent(self, _e):
        if self._drag is not None:
            self.pan_end.emit()
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor if self.pannable else Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, e):
        if self.pannable:
            self.zoom.emit(1 if e.angleDelta().y() > 0 else -1)
            e.accept()

    def set_pannable(self, on):
        self.pannable = on
        self.setCursor(Qt.CursorShape.OpenHandCursor if on else Qt.CursorShape.ArrowCursor)


class Preview(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = QFrame()
        bar.setObjectName("infoBar")
        self._bar = QHBoxLayout(bar)
        self._bar.setContentsMargins(18, 10, 18, 10)
        self._bar.setSpacing(18)
        self._bar.addStretch(1)
        lay.addWidget(bar)
        stage = QWidget()
        stage.setObjectName("stage")
        stage.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sl = QVBoxLayout(stage)
        sl.setContentsMargins(theme.STAGE_PAD, theme.STAGE_PAD, theme.STAGE_PAD, theme.STAGE_PAD)
        self.page = Page()
        sl.addWidget(self.page)
        lay.addWidget(stage, 1)
        self.busy = QLabel(tr("rendering…"), stage)
        self.busy.setObjectName("busy")
        self.busy.hide()
        self._stage = stage

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.busy.adjustSize()
        self.busy.move(self._stage.width() - self.busy.width() - 34, 34)

    def set_busy(self, text):
        self.busy.setVisible(bool(text))
        if text:
            self.busy.setText(text)
            self.busy.adjustSize()
            self.busy.move(self._stage.width() - self.busy.width() - 34, 34)
            self.busy.raise_()

    def set_info(self, groups):
        """Info bar facts: groups of (text, bold) runs, e.g. [("Letter", True), (" 8.5 × 11 in", False)]."""
        while self._bar.count() > 1:
            item = self._bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, runs in enumerate(groups):
            box = QWidget()
            lay = QHBoxLayout(box)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)
            for text, bold in runs:
                lay.addWidget(label_as(text.replace(" ", "\u00a0"), "infoBold" if bold else "info"))
            self._bar.insertWidget(i, box)
        self._fit_info()

    def _fit_info(self):
        """The facts that fit the bar's width, in order (a phone shows the first ones rather than cut them off)."""
        room = self.width() - 18 * 2
        for i in range(self._bar.count() - 1):
            box = self._bar.itemAt(i).widget()
            need = box.sizeHint().width()
            box.setVisible(need <= room)
            room -= need + self._bar.spacing() if need <= room else room + 1

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._fit_info()

    def set_drop(self, over):
        """A dashed outline round the light table while a file is dragged over the window (2.x's .stage.over)."""
        self._stage.setProperty("over", "true" if over else "false")
        self._stage.style().unpolish(self._stage)
        self._stage.style().polish(self._stage)


