"""Small pictures of a booklet's pages, for the page list, drawn off the UI thread.

Each thumbnail is the page itself (pattern, options, complexity, seed, and the booklet's line weight, border,
title and paper) drawn at a low resolution and scaled down. They're cached by what they show, so a page moved
or a booklet-wide change undone shows its picture again at once. A new request replaces what hasn't been drawn
yet, so editing quickly never queues up work.
"""

import threading

import numpy as np
import traceback
from collections import OrderedDict
from dataclasses import replace

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter

from inkengine.canvas import QtCanvas
from inkengine.book import half_geometry
from inkengine.page import draw_page, geometry

from .theme import PAPER_COLOUR

# the settings the gallery draws a pattern's picture with, where its plain page would look like another pattern's (a
# coordinate grid's empty grid is graph paper; joined up, it's a picture)
GALLERY_OPTS = {"coords": {"coord_answer": True}}


def gallery_spec(base, gen):
    """The page the gallery shows for a pattern."""
    from inkengine.page import single_page
    spec = single_page(replace(base, gen=gen))
    return replace(spec, opts=dict(GALLERY_OPTS[gen])) if gen in GALLERY_OPTS else spec


THUMB_H = 34         # px: the row's picture is a page this tall (and as wide as its shape makes it), plus a
                     # 1 px edge all round: 36, the photo list's picture slot
DRAW_DPI = 30        # drawn at this resolution, then scaled down smoothly
CACHE = 200          # thumbnails kept
# At this size a page's lines are a fraction of a pixel wide and come out faint grey. Drawn twice as thick (so a
# heavier line weight still shows heavier), then darkened (grey ** 2), every pattern stays recognisable
# without dense ones (mandalas, contours) filling in.
THICKEN = 2
DARKEN = 2


def _page_geometry(s):
    """A design page's geometry: the paper, or for a fold-and-staple book half a sheet (always portrait)."""
    return half_geometry(s) if s.fold else geometry(s)


def thumb_size(s, h=THUMB_H):
    """The thumbnail's (width, height) for the page's shape: its long side is h."""
    g = _page_geometry(replace(s, dpi=72))
    return (max(1, round(h * g.W / g.H)), h) if g.H >= g.W else (h, max(1, round(h * g.H / g.W)))


class Look:
    """How thumbnails of one size are drawn: their long side, the resolution they're drawn at, and how much
    thicker and darker their lines are made so they read at that size."""

    def __init__(self, h=THUMB_H, dpi=DRAW_DPI, thicken=THICKEN, darken=DARKEN):
        self.h, self.dpi, self.thicken, self.darken = h, dpi, thicken, darken




def key(s, spec):
    """What a design page's thumbnail shows: equal keys, equal pictures. Its page number isn't drawn; its label
    ("Maze 3") is, in the title band, only when there is one."""
    booklet = (s.weight, s.frame, s.title, s.name_line, s.paper, s.orient, s.margin, s.fold)
    label = spec.label if spec.header else ""
    return (spec.gen, spec.seed, spec.c, tuple(sorted(spec.opts.items())), label, booklet)


def draw(s, spec, look=None):
    """A design page as a thumbnail QImage (any thread)."""
    look = look or Look(THUMB_H, DRAW_DPI, THICKEN, DARKEN)   # read now, so tests can change the module's values
    ss = replace(s, dpi=look.dpi, page_nums=False, weight=s.weight * look.thicken)
    g = _page_geometry(ss)
    img = QImage(g.W, g.H, QImage.Format.Format_RGB32)
    img.fill(QColor(PAPER_COLOUR))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    draw_page(QtCanvas(p, g.W, g.H), g, replace(spec, page_no=0), ss)
    p.end()
    w, h = thumb_size(s, look.h)
    small = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_Grayscale8)
    a = np.frombuffer(small.constBits(), np.uint8, small.sizeInBytes()).reshape(h, small.bytesPerLine())[:, :w]
    dark = np.ascontiguousarray((a / 255.0) ** look.darken * 255, dtype=np.uint8)
    return QImage(dark.data, w, h, w, QImage.Format.Format_Grayscale8).copy()


class Thumbnails(QObject):
    ready = Signal(object)   # a thumbnail's key: it's in the cache now
    _done = Signal(object, object)   # (key, image) from the worker; stored on the UI thread, which owns the cache

    def __init__(self, look=None):
        super().__init__()
        self.look = look   # None: the page list's size
        self._done.connect(self._put)
        self._cache = OrderedDict()
        self._lock = threading.Lock()
        self._queue = []
        self._running = False

    def get(self, k):
        img = self._cache.get(k)
        if img is not None:
            self._cache.move_to_end(k)
        return img

    def request(self, s, specs):
        """Draw these design pages' thumbnails that aren't cached yet, in order, instead of any still waiting."""
        jobs, seen = [], set()
        for spec in specs:
            k = key(s, spec)
            if k not in self._cache and k not in seen:
                seen.add(k)
                jobs.append((k, s, spec))
        with self._lock:
            self._queue = jobs
            start = bool(jobs) and not self._running
            if start:
                self._running = True
        if start:
            threading.Thread(target=self._loop, daemon=True).start()

    def cancel(self):
        """Drop the drawings not started yet (the one being drawn finishes)."""
        with self._lock:
            self._queue = []

    @property
    def idle(self):
        with self._lock:
            return not self._running and not self._queue

    def _loop(self):
        while True:
            with self._lock:
                if not self._queue:
                    self._running = False
                    return
                k, s, spec = self._queue.pop(0)
            try:
                img = draw(s, spec, self.look)
            except Exception:   # noqa: BLE001 — that row keeps its blank page; never a crash
                traceback.print_exc()
                continue
            try:
                self._done.emit(k, img)
            except RuntimeError:   # the window closed while this was drawing
                with self._lock:
                    self._running = False
                return

    def _put(self, k, img):
        self._cache[k] = img
        self._cache.move_to_end(k)
        while len(self._cache) > CACHE:
            self._cache.popitem(last=False)
        self.ready.emit(k)
