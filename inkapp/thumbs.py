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
from inkengine.page import draw_page, geometry

from .theme import PAPER_COLOUR

THUMB_H = 36         # px: the row's picture is a page this tall (and as wide as the paper's shape makes it)
DRAW_DPI = 30        # drawn at this resolution, then scaled down smoothly
CACHE = 200          # thumbnails kept
# At this size a page's lines are a fraction of a pixel wide and come out faint grey. Drawn twice as thick (so a
# heavier line weight still shows heavier), then darkened (grey ** 2), every pattern stays recognisable
# without dense ones (mandalas, contours) filling in.
THICKEN = 2
DARKEN = 2


def thumb_size(s):
    """The thumbnail's (width, height) for the settings' paper and orientation."""
    g = geometry(replace(s, dpi=72))
    return (max(1, round(THUMB_H * g.W / g.H)), THUMB_H) if g.H >= g.W else (THUMB_H, max(1, round(THUMB_H * g.H / g.W)))


def key(s, spec):
    """What a design page's thumbnail shows: equal keys, equal pictures (its page number isn't drawn)."""
    booklet = (s.weight, s.frame, s.title, s.name_line, s.paper, s.orient, s.margin)
    return (spec.gen, spec.seed, spec.c, tuple(sorted(spec.opts.items())), booklet)


def draw(s, spec):
    """A design page as a thumbnail QImage (any thread)."""
    ss = replace(s, dpi=DRAW_DPI, page_nums=False, weight=s.weight * THICKEN)
    g = geometry(ss)
    img = QImage(g.W, g.H, QImage.Format.Format_RGB32)
    img.fill(QColor(PAPER_COLOUR))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    draw_page(QtCanvas(p, g.W, g.H), g, replace(spec, page_no=0), ss)
    p.end()
    w, h = thumb_size(s)
    small = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_Grayscale8)
    a = np.frombuffer(small.constBits(), np.uint8, small.sizeInBytes()).reshape(h, small.bytesPerLine())[:, :w]
    dark = np.ascontiguousarray((a / 255.0) ** DARKEN * 255, dtype=np.uint8)
    return QImage(dark.data, w, h, w, QImage.Format.Format_Grayscale8).copy()


class Thumbnails(QObject):
    ready = Signal(object)   # a thumbnail's key: it's in the cache now
    _done = Signal(object, object)   # (key, image) from the worker; stored on the UI thread, which owns the cache

    def __init__(self):
        super().__init__()
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
                img = draw(s, spec)
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
