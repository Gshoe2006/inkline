"""The preview's own zoom, to look closer at the page: pinching it (two fingers), a trackpad's pinch, Ctrl+wheel and
View → Zoom in / Zoom out / Whole page. While zoomed, one finger (or the mouse) drags the view; a double tap shows
the whole page again. The zoom is the view's only: the page and the photo's crop don't change."""

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QImage, QNativeGestureEvent, QPointingDevice, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from inkapp.preview import MAX_VIEW_ZOOM, ZOOM_STEP, Page


@pytest.fixture
def page():
    p = Page()
    p.resize(400, 500)
    img = QImage(850, 1100, QImage.Format.Format_RGB32)   # Letter's shape
    img.fill(Qt.GlobalColor.white)
    p.set_image(img)
    p.show()
    QApplication.processEvents()
    yield p
    p.close()


@pytest.fixture(scope="module")
def finger():
    return QTest.createTouchDevice()


def _shown(p):
    r = p.visible_rect()
    return round(r.x(), 3), round(r.y(), 3), round(r.width(), 3), round(r.height(), 3)


def test_fitted_to_begin_with_and_after_a_reset(page):
    assert not page.zoomed() and _shown(page) == (0, 0, 1, 1)
    page.zoom_to(2)
    assert page.zoomed() and page.view_zoom == 2
    page.reset_view()
    assert page.view_zoom == 1 and _shown(page) == (0, 0, 1, 1)


def test_zoom_keeps_the_point_under_the_fingers_and_stays_in_bounds(page):
    r = page.page_rect()
    corner = QPointF(r.x() + r.width() * 0.25, r.y() + r.height() * 0.25)   # a quarter of the way into the page
    page.zoom_to(2, corner)
    r2 = page.page_rect()
    assert abs((corner.x() - r2.x()) / r2.width() - 0.25) < 1e-6 and abs((corner.y() - r2.y()) / r2.height() - 0.25) < 1e-6
    shown = page.visible_rect()
    assert shown.width() < 0.6 and shown.height() < 0.6 and shown.x() >= 0 and shown.y() >= 0
    page.zoom_to(50)
    assert page.view_zoom == MAX_VIEW_ZOOM
    page.zoom_to(0.1)
    assert page.view_zoom == 1
    page.zoom_to(3)
    page.pan_view(-10_000, -10_000)   # dragged far past the bottom right: the page's corner stops at the view's
    r = page.page_rect()
    assert abs(r.right() - page.width()) < 1e-6 and abs(r.bottom() - page.height()) < 1e-6
    x, y, w, h = _shown(page)
    assert x + w == 1 and y + h == 1
    page.pan_view(10_000, 10_000)
    assert page.page_rect().topLeft() == QPointF(0, 0)


def test_pinch_with_two_fingers_then_drag_and_double_tap(page, finger):
    QTest.touchEvent(page, finger).press(0, QPoint(150, 250)).press(1, QPoint(250, 250)).commit()
    QTest.touchEvent(page, finger).move(0, QPoint(100, 250)).move(1, QPoint(300, 250)).commit()   # twice as far apart
    QTest.touchEvent(page, finger).release(0, QPoint(100, 250)).release(1, QPoint(300, 250)).commit()
    assert abs(page.view_zoom - 2) < 0.01
    before = page.visible_rect()
    QTest.touchEvent(page, finger).press(0, QPoint(200, 300)).commit()   # one finger drags the zoomed view
    QTest.touchEvent(page, finger).move(0, QPoint(260, 340)).commit()
    QTest.touchEvent(page, finger).release(0, QPoint(260, 340)).commit()
    after = page.visible_rect()
    assert after.x() < before.x() and after.y() < before.y() and page.view_zoom == pytest.approx(2, abs=0.01)
    for _ in range(2):   # a double tap: the whole page again
        QTest.touchEvent(page, finger).press(0, QPoint(200, 250)).commit()
        QTest.touchEvent(page, finger).release(0, QPoint(200, 250)).commit()
    assert page.view_zoom == 1 and _shown(page) == (0, 0, 1, 1)


def test_a_finger_drags_the_photo_when_not_zoomed(page, finger):
    page.set_pannable(True)
    moved, ended = [], []
    page.pan.connect(lambda dx, dy: moved.append((dx, dy)))
    page.pan_end.connect(lambda: ended.append(1))
    QTest.touchEvent(page, finger).press(0, QPoint(200, 250)).commit()
    QTest.touchEvent(page, finger).move(0, QPoint(220, 250)).commit()
    QTest.touchEvent(page, finger).release(0, QPoint(220, 250)).commit()
    assert moved and moved[-1][0] > 0 and moved[-1][1] == 0 and ended == [1] and not page.zoomed()


def test_ctrl_wheel_zooms_at_the_pointer_and_the_plain_wheel_still_zooms_a_photo(page):
    def wheel(dy, mods=Qt.KeyboardModifier.NoModifier):
        e = QWheelEvent(QPointF(100, 100), page.mapToGlobal(QPointF(100, 100)), QPoint(), QPoint(0, dy),
                        Qt.MouseButton.NoButton, mods, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(page, e)
    wheel(120, Qt.KeyboardModifier.ControlModifier)
    assert page.view_zoom == pytest.approx(ZOOM_STEP)
    photo = []
    page.zoom.connect(photo.append)
    page.set_pannable(True)
    wheel(120)
    assert photo == [1] and page.view_zoom == pytest.approx(ZOOM_STEP)   # the photo's crop, not the view


def test_a_trackpad_pinch(page):
    dev = QPointingDevice.primaryPointingDevice()
    e = QNativeGestureEvent(Qt.NativeGestureType.ZoomNativeGesture, dev, 2, QPointF(200, 250), QPointF(200, 250),
                            page.mapToGlobal(QPointF(200, 250)), 0.5, QPointF(), 0)
    QApplication.sendEvent(page, e)
    assert page.view_zoom == pytest.approx(1.5)


def test_the_mouse_drags_the_zoomed_view_and_a_double_click_fits(page):
    page.zoom_to(2)
    before = page.visible_rect()
    QTest.mousePress(page, Qt.MouseButton.LeftButton, pos=QPoint(200, 250))
    QTest.mouseMove(page, QPoint(150, 200))
    QTest.mouseRelease(page, Qt.MouseButton.LeftButton, pos=QPoint(150, 200))
    assert page.visible_rect().x() > before.x()
    QTest.mouseDClick(page, Qt.MouseButton.LeftButton, pos=QPoint(200, 250))
    assert not page.zoomed()


def test_view_menu_zooms_the_preview(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    from conftest import settle
    w = Window("6.0.0", remember=False)
    w.show()
    settle(w)
    acts = {a.shortcut().toString(): a for m in w._top_menus for a in m.actions()}
    page = w.preview.page
    acts["Ctrl++"].trigger()
    assert page.view_zoom == pytest.approx(ZOOM_STEP)
    acts["Ctrl+-"].trigger()
    acts["Ctrl+-"].trigger()
    assert page.view_zoom == 1
    acts["Ctrl++"].trigger()
    acts["Ctrl+0"].trigger()
    assert not page.zoomed()


def test_a_double_click_or_tap_zooms_in_when_the_whole_page_shows(page, finger):
    QTest.mouseDClick(page, Qt.MouseButton.LeftButton, pos=QPoint(200, 250))
    assert page.view_zoom == pytest.approx(2)
    page.reset_view()
    for _ in range(2):
        QTest.touchEvent(page, finger).press(0, QPoint(200, 250)).commit()
        QTest.touchEvent(page, finger).release(0, QPoint(200, 250)).commit()
    assert page.view_zoom == pytest.approx(2)


def _set(w, **kw):
    for key, value in kw.items():
        w.state.update(**{key: value})
        w.sidebar.load()
        w._changed(key)


def test_another_pattern_shows_the_whole_page_and_page_down_still_turns(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent
    from inkapp.window import Window
    from conftest import settle
    w = Window("6.0.0", remember=False)
    w.show()
    settle(w)
    page = w.preview.page
    page.zoom_to(3)
    _set(w, gen="maze")
    settle(w)
    assert not page.zoomed()
    _set(w, booklet=True)
    settle(w)
    page.zoom_to(3)
    page.setFocus()
    before = w.state.page
    for key in (Qt.Key.Key_Right, Qt.Key.Key_PageDown):
        QApplication.sendEvent(page, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
    assert w.state.page == before + 1   # Right moved the zoomed view; Page Down turned the page
    w.close()
