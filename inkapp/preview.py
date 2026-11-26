"""The right-hand side: an info bar over a true-to-scale sheet of paper on the light table (2.x's main).

The page is drawn with a soft shadow, scaled to fit. While the renderer works, a "rendering…" badge
shows top right. Posters show their sheets' outlines, shared overlap strips and names. With a photo
open, dragging the page moves the photo across its overhang and the wheel zooms it; images dropped
anywhere on the window are opened (the window handles drop and paste).

Looking closer: the preview has a zoom of its own, which changes only the view, never the page. Pinch it (a touch
screen or a trackpad), Ctrl+wheel, or View → Zoom in / Zoom out; while it's zoomed, one finger (or the mouse) drags
the view round, and a double tap or double click (or View → Whole page) shows the whole page again.
"""

import math
import time

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QEventPoint, QFont, QInputDevice, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from inkengine.i18n import tr
from inkengine.poster import row_name, sheet_rect

from . import theme
from .widgets import label_as


MAX_VIEW_ZOOM = 4.0   # the view's zoom: up to 4× the fitted page (the preview is drawn at 150 dpi: sharp to about 3×)
ZOOM_STEP = 1.25      # one Ctrl+wheel notch, or View → Zoom in / Zoom out
TAP_SLOP = 12         # px a finger may move and still tap


class Page(QWidget):
    """The sheet itself: the rendered image, scaled to fit, keeping its aspect ratio, and zoomed in when asked."""

    pan = Signal(float, float)    # how far the pointer moved, in page pixels at the preview's resolution
    zoom = Signal(int)            # +1 wheel up, -1 down
    pan_end = Signal()
    view_changed = Signal()       # the view's zoom or position changed

    def __init__(self):
        super().__init__()
        self.image = None
        self.poster = None        # a poster's geometry: draw the sheet overlay
        self.dead = None          # the printer's dead strip: (left, top, right, bottom) as shares of the page
        self.pannable = False
        self._drag = None         # where a drag of the photo started
        self._look = None         # where a drag of the zoomed view was last
        self.view_zoom = 1.0      # 1: the whole page fits
        self._centre = QPointF(0.5, 0.5)   # the point of the page in the middle of the view, as shares of the page
        self._pinch = None        # two fingers down: (their distance then, the zoom then)
        self._mid = None          # ... and their midpoint last time
        self._touch = None        # one finger down: [where it went down, whether it has moved]
        self._tapped = None       # the last tap: (when, where), for a double tap
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setMinimumSize(200, 200)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(theme.SHADOW_BLUR)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(*theme.SHADOW_COLOUR))
        self.setGraphicsEffect(shadow)
        self.setAccessibleName(tr("Page preview"))   # and what it shows, as its description (the window's)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)   # reached with Tab, after the toolbar: a screen reader reads it

    def set_image(self, image, poster=None):
        self.image, self.poster = image, poster
        self._settle()   # another paper size keeps the zoom, inside the page
        self.updateGeometry()

    def page_rect(self):
        """Where the page is drawn: fitted and centred, or zoomed round _centre without showing past its edges."""
        if not self.image:
            return QRectF()
        w, h = self.image.width(), self.image.height()
        s = min(self.width() / w, self.height() / h) * self.view_zoom
        pw, ph = w * s, h * s

        def place(room, size, share):
            if size <= room:
                return (room - size) / 2
            return max(room - size, min(0.0, room / 2 - share * size))
        return QRectF(place(self.width(), pw, self._centre.x()), place(self.height(), ph, self._centre.y()), pw, ph)

    # --- the view's zoom -----------------------------------------------------------------------------------------
    def zoomed(self):
        return self.view_zoom > 1.0 + 1e-6

    def visible_rect(self):
        """The part of the page in view, as shares of the page (0 to 1 each way)."""
        r = self.page_rect()
        if r.isEmpty():
            return QRectF()
        seen = r.intersected(QRectF(self.rect()))
        return QRectF((seen.x() - r.x()) / r.width(), (seen.y() - r.y()) / r.height(),
                      seen.width() / r.width(), seen.height() / r.height())

    def zoom_to(self, z, anchor=None):
        """Zoom the view to z (1 to MAX_VIEW_ZOOM), keeping the point of the page under anchor (widget pixels; the
        middle by default) where it is."""
        z = max(1.0, min(MAX_VIEW_ZOOM, z))
        anchor = QPointF(self.width() / 2, self.height() / 2) if anchor is None else QPointF(anchor)
        r = self.page_rect()
        if r.isEmpty():
            self.view_zoom = z
            return
        fx, fy = (anchor.x() - r.x()) / r.width(), (anchor.y() - r.y()) / r.height()
        k = z / self.view_zoom
        pw, ph = r.width() * k, r.height() * k
        x, y = anchor.x() - fx * pw, anchor.y() - fy * ph
        self.view_zoom = z
        self._centre = QPointF((self.width() / 2 - x) / pw, (self.height() / 2 - y) / ph)
        self._settle()

    def zoom_by(self, factor, anchor=None):
        self.zoom_to(self.view_zoom * factor, anchor)

    def pan_view(self, dx, dy):
        """Move the zoomed page by (dx, dy) widget pixels, as a finger drags it."""
        r = self.page_rect()
        if r.isEmpty():
            return
        self._centre = QPointF(self._centre.x() - dx / r.width(), self._centre.y() - dy / r.height())
        self._settle()

    def reset_view(self):
        """The whole page in view again."""
        self.view_zoom, self._centre = 1.0, QPointF(0.5, 0.5)
        self._settle()

    def _settle(self):
        """Keep the centre where page_rect puts the page (never panned past an edge), and redraw."""
        r = self.page_rect()
        if not r.isEmpty():
            self._centre = QPointF((self.width() / 2 - r.x()) / r.width(), (self.height() / 2 - r.y()) / r.height())
        self._cursor()
        self.update()
        self.view_changed.emit()

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
        if self.hasFocus():   # reached with Tab: an outline round the preview, as the controls' focus border
            p.setPen(QPen(QColor(theme.tokens().accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(self.rect()).adjusted(1, 1, -1, -1))
        p.end()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.update()

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.update()

    def keyPressEvent(self, e):
        """With the preview focused: + and - zoom it, 0 shows the whole page, and the arrow keys move the zoomed view
        (← → turn a booklet's pages while it isn't zoomed: the window takes them)."""
        step = 40
        moves = {Qt.Key.Key_Left: (step, 0), Qt.Key.Key_Right: (-step, 0), Qt.Key.Key_Up: (0, step),
                 Qt.Key.Key_Down: (0, -step)}
        if e.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_by(ZOOM_STEP)
        elif e.key() == Qt.Key.Key_Minus:
            self.zoom_by(1 / ZOOM_STEP)
        elif e.key() == Qt.Key.Key_0:
            self.reset_view()
        elif e.key() in moves and self.zoomed():
            self.pan_view(*moves[e.key()])
        else:
            super().keyPressEvent(e)

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

    # dragging: the zoomed view (to look round it), else the photo across its overhang
    def _press(self, pos):
        if self.zoomed():
            self._look = QPointF(pos)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self.pannable:
            self._drag = QPointF(pos)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _move(self, pos):
        if self._look is not None:
            d = QPointF(pos) - self._look
            self._look = QPointF(pos)
            self.pan_view(d.x(), d.y())
        elif self._drag is not None and self.image:
            k = self.image.width() / max(1.0, self.page_rect().width())   # screen pixels to page pixels
            d = QPointF(pos) - self._drag
            self.pan.emit(d.x() * k, d.y() * k)

    def _release(self):
        if self._drag is not None:
            self.pan_end.emit()
        self._drag = self._look = None
        self._cursor()

    def _cursor(self):
        self.setCursor(Qt.CursorShape.OpenHandCursor if self.pannable or self.zoomed() else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press(e.position())

    def mouseMoveEvent(self, e):
        self._move(e.position())

    def mouseReleaseEvent(self, _e):
        self._release()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.zoomed():
            self.reset_view()

    def wheelEvent(self, e):
        """Ctrl+wheel zooms the view at the pointer; the wheel zooms the photo (with one open), else moves the
        zoomed view."""
        notches = e.angleDelta().y() / 120
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier and notches:
            self.zoom_by(ZOOM_STEP ** notches, e.position())
        elif self.pannable and notches:
            self.zoom.emit(1 if notches > 0 else -1)
        elif self.zoomed():
            d = e.pixelDelta() if not e.pixelDelta().isNull() else e.angleDelta() / 3
            self.pan_view(d.x(), d.y())
        else:
            e.ignore()
            return
        e.accept()

    def event(self, e):
        t = e.type()
        if t == QEvent.Type.NativeGesture:   # a trackpad's pinch (macOS, Wayland)
            if e.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                self.zoom_by(1 + e.value(), e.position())
                return True
            if e.gestureType() == Qt.NativeGestureType.SmartZoomNativeGesture:   # a two-finger double tap
                self.reset_view() if self.zoomed() else self.zoom_to(2.0, e.position())
                return True
        elif t in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd, QEvent.Type.TouchCancel) \
                and e.device() is not None and e.device().type() == QInputDevice.DeviceType.TouchScreen:
            # (a trackpad's fingers, which macOS also sends as touches, stay its scrolling and pinch gestures)
            self.touch(e)
            e.accept()
            return True
        return super().event(e)

    def touch(self, e):
        """Fingers on the page: two pinch the view's zoom (and move it); one drags (the zoomed view, else the photo);
        a double tap shows the whole page again. Taken as touch events rather than the mouse events Qt would make of
        them, which only know one finger."""
        down = [] if e.type() == QEvent.Type.TouchCancel else \
            [p for p in e.points() if p.state() != QEventPoint.State.Released]
        if len(down) >= 2:
            a, b = down[0].position(), down[1].position()
            dist, mid = max(1.0, math.hypot(a.x() - b.x(), a.y() - b.y())), (a + b) / 2
            if self._pinch is None:
                self._release()   # a drag going on stops where it is
                self._pinch, self._touch = (dist, self.view_zoom), None
            else:
                self.zoom_to(self._pinch[1] * dist / self._pinch[0], mid)
                self.pan_view(mid.x() - self._mid.x(), mid.y() - self._mid.y())
            self._mid = mid
        elif down:
            if self._pinch is not None:   # one finger left after a pinch: nothing until it's lifted too
                return
            pos = down[0].position()
            if self._touch is None:
                self._touch = [QPointF(pos), False]
                self._press(pos)
            else:
                self._touch[1] = self._touch[1] or (pos - self._touch[0]).manhattanLength() > TAP_SLOP
                self._move(pos)
        else:   # every finger lifted
            tap = self._touch is not None and not self._touch[1]
            where = self._touch[0] if self._touch else None
            self._release()
            self._pinch = self._mid = self._touch = None
            if tap:
                now, last = time.monotonic(), self._tapped
                if (last and now - last[0] <= QApplication.doubleClickInterval() / 1000
                        and (where - last[1]).manhattanLength() <= 4 * TAP_SLOP):
                    self._tapped = None
                    self.reset_view()
                else:
                    self._tapped = (now, where)

    def set_pannable(self, on):
        self.pannable = on
        self._cursor()


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
        self._stage_lay = sl
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

    def set_pad(self, px):
        """The light table's margin round the page (narrower on a touch screen: theme.TOUCH_STAGE_PAD)."""
        self._stage_lay.setContentsMargins(px, px, px, px)

    def pad(self):
        return self._stage_lay.contentsMargins().left()

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


