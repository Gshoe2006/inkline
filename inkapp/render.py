"""Drawing the preview, off the UI thread.

view() works out what the preview shows (2.x's viewGeometry and drawView): the printer test page, a
folded sheet's side, a whole poster, a booklet or photo book page, or the single page. render_view()
draws it into a QImage at screen resolution, with the facts for the info bar. Renderer runs those on
a worker thread: a new request replaces any that hasn't started, so dragging a slider never queues up
work, and the newest result is the one shown.
"""

import threading
import traceback
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QImage, QPainter

from inkengine import book, poster
from inkengine.canvas import QtCanvas
from inkengine.page import PAPER, Geometry, draw_page, geometry, single_page
from inkengine.box import Box
from inkengine.qt import ensure_app

PREVIEW_DPI = 150          # colour by number's grid is 150 dpi, so the preview shows the same regions as print
POSTER_PREVIEW_PX = 2400   # a whole poster is drawn with its long side about this many pixels


@dataclass
class View:
    kind: str              # testpage | fold | poster | photobook | booklet | page
    pages: list = None     # booklet / photo book / fold: every page
    index: int = 0         # the page (or folded side) shown
    count: int = 1         # how many pages (or sides) the pager steps through
    label: str = ""        # what the pager says


def view(state):
    s = state.settings
    if s.testpage:
        return View("testpage")
    photo_book = s.mode == "convert" and s.photobook and state.photos and not s.poster
    booklet = s.mode == "make" and s.booklet and not s.poster
    if s.poster:
        return View("poster")
    if photo_book or booklet:
        pages = book.photo_book_pages(s, state.photos) if photo_book else book.book_pages(s)
        if s.fold:
            pages = book.fold_pages(pages)
            sides = len(book.fold_order(len(pages)))
            i = max(0, min(state.page, sides - 1))
            return View("fold", pages, i, sides, book.fold_side_label(pages, i))
        i = max(0, min(state.page, len(pages) - 1))
        return View("photobook" if photo_book else "booklet", pages, i, len(pages), book.page_label(pages, i))
    return View("page")


@dataclass
class Rendered:
    image: QImage
    view: View
    info: list             # the info bar: groups of (text, bold) runs, as 2.x's spans
    note: str = ""         # the word search's "Left out: ..." note, worked out here, off the UI thread
    poster: object = None  # the poster's geometry, for the sheet overlay
    scale: float = 1.0     # preview pixels per page pixel at the settings' dpi


def _paper_name(s):
    return "A4" if s.paper == "a4" else "Letter"


def _num(x):
    return f"{x:g}"


def ink_coverage(img):
    """The share of the page that's ink, in %, as 2.x's info bar shows it."""
    img = img.convertToFormat(QImage.Format.Format_Grayscale8)
    a = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).reshape(img.height(), img.bytesPerLine())[:, :img.width()]
    return float((255 - a.astype(np.float64)).mean() / 255 * 100)


def render_view(state):
    """The preview image and its info bar, for whatever the state shows."""
    ensure_app()
    s, v = state.settings, view(state)
    P = None
    if v.kind == "testpage":
        from dataclasses import replace
        from inkengine.testpage import draw_test_page
        st = replace(s, orient="portrait")   # drawn at the settings' dpi, so its heading says the dpi it prints at
        full = geometry(st)
        sc = PREVIEW_DPI / s.dpi
        g = geometry(st, PREVIEW_DPI)
        img = _blank(g.W, g.H)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.scale(sc, sc)
        draw_test_page(QtCanvas(p, full.W, full.H), st)
        p.end()
    elif v.kind == "fold":
        gs = book.sheet_geometry(s)
        sc = PREVIEW_DPI / s.dpi
        W, H = round(gs.W * sc), round(gs.H * sc)
        img = _blank(W, H)
        p = QPainter(img)
        p.scale(sc, sc)
        book.draw_fold_side(QtCanvas(p, gs.W, gs.H), s, v.pages, v.index)
        p.end()
        g = Geometry(gs.w, gs.h, PREVIEW_DPI, W, H, Box(0, 0, W, H))
    elif v.kind == "poster":
        one = poster.poster_geometry(s, 1)
        dpi = min(s.dpi, POSTER_PREVIEW_PX / max(one.w, one.h))
        P = poster.poster_geometry(s, dpi)
        img = _blank(P.W, P.H)
        p = QPainter(img)
        draw_page(QtCanvas(p, P.W, P.H), P, single_page(s, state.photo), s)
        p.end()
        g = P
    else:
        g = geometry(s, PREVIEW_DPI)
        spec = v.pages[v.index] if v.pages else single_page(s, state.photo)
        img = _blank(g.W, g.H)
        p = QPainter(img)
        draw_page(QtCanvas(p, g.W, g.H), g, spec, s)
        p.end()
    paper = _paper_name(s)
    if v.kind == "testpage":
        info = [[("Printer test page", True), (f" {_num(g.w)} × {_num(g.h)} in", False)],
                [(str(s.dpi), True), (" dpi · print at 100%", False)]]
    else:
        cov = ink_coverage(img)
        if v.kind == "poster":
            info = [[("Poster", True), (f" {_num(P.w)} × {_num(P.h)} in", False)],
                    [(f"{P.cols} × {P.rows}", True), (f" {paper} sheets · {s.dpi} dpi", False)]]
        else:
            pg = geometry(s)
            info = [[(paper, True), (f" {_num(g.w)} × {_num(g.h)} in", False)],
                    [(str(s.dpi), True), (f" dpi · {pg.W} × {pg.H} px", False)]]
        info.append([("ink coverage ", False), (f"{cov:.1f}%", True)])
    note = _word_note(s) if s.mode == "make" and s.gen == "words" and v.kind == "page" else ""
    return Rendered(img, v, info, poster=P, scale=PREVIEW_DPI / s.dpi, note=note)


def _word_note(s):
    """What 2.x's word search note says about words left out, for this page's word search."""
    from inkengine.canvas import RecordingCanvas
    from inkengine.page import design_box
    from inkengine.patterns import words
    from inkengine.rng import mulberry32
    g = geometry(s)
    ws = words.draw(RecordingCanvas(), design_box(g, single_page(s), s), mulberry32(s.seed), s.complexity, s, dpi=g.dpi)
    return words.note(ws)


def _blank(w, h):
    img = QImage(max(1, w), max(1, h), QImage.Format.Format_RGB32)
    img.fill(QColor("#fff"))
    return img


class Renderer(QObject):
    """Runs one job at a time on a worker thread. submit() replaces a job that hasn't started yet."""

    finished = Signal(int, object)     # request number, result
    failed = Signal(int, str)          # request number, what went wrong
    busy = Signal(bool)
    converting = Signal()              # a photo conversion started (it wasn't cached)

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._pending = None
        self._running = False
        self._seq = 0

    def submit(self, fn):
        """Run fn() on the worker; its result arrives through finished, with this request's number."""
        with self._lock:
            self._seq += 1
            self._pending = (self._seq, fn)
            start = not self._running
            self._running = True
        if start:
            self.busy.emit(True)
            threading.Thread(target=self._loop, daemon=True).start()
        return self._seq

    @property
    def latest(self):
        return self._seq

    def _loop(self):
        while True:
            with self._lock:
                job, self._pending = self._pending, None
                if job is None:
                    self._running = False
                    break
            n, fn = job
            from inkengine import photo as photo_mod
            photo_mod.set_on_convert(self.converting.emit)   # this worker thread's own hook
            try:
                result = fn()
                try:
                    self.finished.emit(n, result)
                except RuntimeError:   # the window closed while this was drawing
                    return
            except Exception:   # noqa: BLE001 — reported in the status line, never a crash
                traceback.print_exc()   # the details, for a bug report
                try:
                    self.failed.emit(n, traceback.format_exc(limit=1).strip().splitlines()[-1])
                except RuntimeError:
                    return
            finally:
                photo_mod.set_on_convert(None)
        try:
            self.busy.emit(False)
        except RuntimeError:
            pass
