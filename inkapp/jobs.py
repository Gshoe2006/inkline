"""What Print and Save produce, for whatever the state shows (2.x's job, runBook, runPoster...).

A Job is a run of pages at true paper size, each drawn with the engine at the settings' dpi: the page,
every page of a booklet or photo book, the sides of a fold-and-staple book, or a poster's sheets.
run() draws a job onto a QPdfWriter or QPrinter, page by page, on whatever thread calls it.
"""

import re
from dataclasses import dataclass, replace

from PySide6.QtCore import QMarginsF, QRectF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter

from inkengine import book, output, poster
from inkengine.canvas import QtCanvas
from inkengine.page import draw_page, geometry, single_page
from inkengine.testpage import draw_test_page

from .render import view

PAPER_IDS = {"letter": QPageSize.PageSizeId.Letter, "a4": QPageSize.PageSizeId.A4}


@dataclass
class Job:
    name: str              # file name without extension
    label: str             # page, booklet, photo book, poster, test page
    count: int
    orient: str
    geometry: object       # the page geometry at the settings' dpi
    draw: object           # draw(ctx, i): page i onto a canvas of that geometry
    duplex: bool = False   # fold-and-staple: double-sided, flipping on the short edge

    @property
    def unit(self):
        return "sheet" if self.label == "poster" else "page"


def base_name(state):
    """2.x's file names: inkline-maze-12345, or inkline-<photo name>."""
    s = state.settings
    if s.mode == "make":
        return f"inkline-{s.gen}-{s.seed}"
    nm = state.photo.name if state.photo else "photo"
    nm = re.sub(r"\.[^.]+$", "", nm.rsplit("/", 1)[-1])
    return "inkline-" + re.sub(r"[^\w-]+", "-", nm).lower()


def job(state):
    s, v = state.settings, view(state)
    if v.kind == "testpage":
        st = replace(s, orient="portrait")
        return Job("inkline-printer-test", "test page", 1, "portrait", geometry(st), lambda ctx, i: draw_test_page(ctx, st))
    if v.kind == "poster":
        P, spec = poster.poster_geometry(s), single_page(s, state.photo)
        return Job(f"{base_name(state)}-poster-{P.cols}x{P.rows}", "poster", P.sheets, s.orient, geometry(s),
                   lambda ctx, i: poster.draw_sheet(ctx, s, P, spec, i))
    photo_book = s.mode == "convert" and s.photobook and state.photos
    if v.kind in ("booklet", "photobook", "fold"):
        pages = book.photo_book_pages(s, state.photos) if photo_book else book.book_pages(s)
        name = f"inkline-photobook-{len(pages)}p" if photo_book else f"inkline-booklet-{s.seed}"
        label = "photo book" if photo_book else "booklet"
        if s.fold:
            pages = book.fold_pages(pages)
            return Job(f"{name}-fold", label, len(pages) // 2, "landscape", book.sheet_geometry(s),
                       lambda ctx, i: book.draw_fold_side(ctx, s, pages, i), duplex=True)
        g = geometry(s)
        return Job(name, label, len(pages), s.orient, g, lambda ctx, i: draw_page(ctx, g, pages[i], s))
    g, spec = geometry(s), single_page(s, state.photo)
    return Job(base_name(state), "page", 1, s.orient, g, lambda ctx, i: draw_page(ctx, g, spec, s))


def printed_orient(s, kind):
    """Which way round the sheet goes through the printer for a view: as job() prints it."""
    if kind == "testpage":
        return "portrait"
    if kind == "fold":
        return "landscape"
    return s.orient


_margin_cache = {}


def printer_margins(name, s, orient):
    """What a printer can't reach on this paper: (name shown to people, (left, top, right, bottom) in inches,
    (width, height) of the paper in inches). name "" is the system's default printer. None with no printer."""
    from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
    key = (name, s.paper, orient)
    if key not in _margin_cache:
        info = QPrinterInfo.printerInfo(name) if name else QPrinterInfo.defaultPrinter()
        if info.isNull():
            return None
        printer = QPrinter(info, QPrinter.PrinterMode.HighResolution)
        printer.setPageLayout(page_layout(s, orient))
        layout = printer.pageLayout()
        layout.setUnits(QPageLayout.Unit.Inch)
        m, full = layout.minimumMargins(), layout.fullRect(QPageLayout.Unit.Inch)
        _margin_cache[key] = (info.description() or info.printerName(),
                              (m.left(), m.top(), m.right(), m.bottom()), (full.width(), full.height()))
    return _margin_cache[key]


def page_layout(s, orient):
    o = QPageLayout.Orientation.Landscape if orient == "landscape" else QPageLayout.Orientation.Portrait
    return QPageLayout(QPageSize(PAPER_IDS[s.paper]), o, QMarginsF(0, 0, 0, 0))


def run(j, device, progress=None, cancelled=lambda: False):
    """Draw every page of the job onto a QPdfWriter or QPrinter (already set up). True when finished."""
    p = QPainter()
    if not p.begin(device):
        return False
    try:
        g = j.geometry
        for i in range(j.count):
            if cancelled():
                return False
            if i and not device.newPage():
                return False
            if progress:
                progress(i)
            # page pixels at the settings' dpi onto the device's whole page
            p.save()
            p.setWindow(0, 0, g.W, g.H)
            vp = p.viewport()
            sc = min(vp.width() / g.W, vp.height() / g.H)
            w, h = round(g.W * sc), round(g.H * sc)
            p.setViewport(vp.x() + (vp.width() - w) // 2, vp.y() + (vp.height() - h) // 2, w, h)
            j.draw(QtCanvas(p, g.W, g.H), i)
            p.restore()
        return True
    finally:
        p.end()


def svg(state):
    """The page shown as SVG (a poster: the whole poster), and the file name to suggest."""
    s, v = state.settings, view(state)
    if v.kind in ("fold", "testpage"):
        raise ValueError("fold-and-staple sides and the test page don't save as SVG")
    spec = v.pages[v.index] if v.pages else single_page(s, state.photo)
    suffix = "-poster" if v.kind == "poster" else f"-page{v.index + 1}" if v.pages else ""
    return output.svg_text(s, spec), base_name(state) + suffix


def png(state):
    """The page shown, at full resolution, and the file name to suggest."""
    s, v = state.settings, view(state)
    j = job(state)
    if v.kind == "testpage":
        return output_image(j, 0), j.name
    spec = v.pages[v.index] if v.pages and v.kind != "fold" else single_page(s, state.photo)
    if v.kind == "fold":
        return output_image(j, v.index), base_name(state)
    return output.render_image(s, spec), base_name(state)   # 2.x's PNG name, whichever page is shown


def output_image(j, i):
    from PySide6.QtGui import QColor, QImage
    g = j.geometry
    img = QImage(g.W, g.H, QImage.Format.Format_RGB32)
    img.fill(QColor("#fff"))
    img.setDotsPerMeterX(round(g.dpi / 0.0254))
    img.setDotsPerMeterY(round(g.dpi / 0.0254))
    p = QPainter(img)
    j.draw(QtCanvas(p, g.W, g.H), i)
    p.end()
    return img
