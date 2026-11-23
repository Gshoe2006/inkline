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

    def amount(self):
        """ "14-page booklet", "2 sheets (both sides)": what the job prints, for the status line."""
        if self.duplex:   # a fold-and-staple book: two printed sides per sheet
            n = self.count // 2
            return f"{n} sheet{'s' if n != 1 else ''} (both sides)"
        if self.label == "copies":
            return f"{self.count} copies"
        return f"{self.count}-{self.unit} {self.label}"


def base_name(state):
    """2.x's file names: inkline-maze-12345, or inkline-<photo name>."""
    s = state.settings
    if s.mode == "make":
        return f"inkline-{s.gen}-{s.seed}"
    nm = state.photo.name if state.photo else "photo"
    nm = re.sub(r"\.[^.]+$", "", re.split(r"[\\/]", nm)[-1])   # a path from Linux or Windows
    return "inkline-" + re.sub(r"[^\w-]+", "-", nm).lower()


def parse_pages(text, pages):
    """Which pages (0-based, in order) a list like "3-5, 8, cover, answers" picks, counting as the pager does
    (the cover, when there is one, is page 1). Empty text picks every page. Raises ValueError with a message
    to show when the text doesn't make sense."""
    text = (text or "").strip().lower().replace("–", "-").replace("—", "-")
    if not text:
        return list(range(len(pages)))
    n, chosen = len(pages), set()
    for token in [t.strip() for t in re.split(r"[,;]", text) if t.strip()]:
        if token in ("cover", "the cover"):
            found = [i for i, p in enumerate(pages) if p.kind in ("cover", "pcover")]
            if not found:
                raise ValueError("This book has no cover page.")
            chosen.update(found)
        elif token in ("answers", "answer", "answer pages"):
            found = [i for i, p in enumerate(pages) if p.kind == "answers"]
            if not found:
                raise ValueError("This book has no answer pages.")
            chosen.update(found)
        elif m := re.fullmatch(r"(\d+)\s*(?:-\s*(\d+))?", token):
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            if a > b:
                a, b = b, a
            if a < 1 or b > n:
                raise ValueError(f"There's no page {b if b > n else a}: this book has {n} page{'s' if n != 1 else ''}.")
            chosen.update(range(a - 1, b))
        else:
            raise ValueError(f"“{token}” isn't a page. Use page numbers, ranges like 3-5, “cover” or “answers”.")
    if not chosen:
        raise ValueError("No pages there. Use page numbers, ranges like 3-5, “cover” or “answers”.")
    return sorted(chosen)


def describe_pages(indices, total):
    """ "pages 3–5 and 8": a short name for a choice of pages (1-based, ranges joined)."""
    runs, start = [], None
    for k, i in enumerate(indices):
        if start is None:
            start = i
        if k + 1 == len(indices) or indices[k + 1] != i + 1:
            runs.append(f"{start + 1}" if start == i else f"{start + 1}–{i + 1}")
            start = None
    names = ", ".join(runs[:-1]) + (" and " if len(runs) > 1 else "") + runs[-1] if runs else ""
    return f"page{'s' if len(indices) > 1 else ''} {names}"


def fold_sheets(indices, n):
    """The sheets (0-based) of an n-page fold-and-staple book that carry any of these pages."""
    sides = book.fold_order(n)
    return sorted({k // 2 for k, side in enumerate(sides) if set(side) & set(indices)})


MAX_COPIES = 100


def copy_seed(seed, i):
    """The design of copy i (0 is the design shown): a fixed step from it, so the same set prints again alike."""
    return seed if i == 0 else (seed + i * 104729) & 0xFFFFFFFF


def copies_vary(s):
    """(whether copies of this single page can each have their own design, a note when some of them repeat or
    none can differ, or "")."""
    if s.mode != "make":
        return False, ""
    if s.gen == "name" and s.name_bg == "none":
        return False, "A name page with nothing underneath has no design to change, so its copies are alike."
    if s.gen == "dots":
        return True, "Dot-to-dot has only a handful of pictures, so some copies repeat."
    if s.gen == "nonogram" and s.complexity <= 1:
        return True, "The smallest nonograms sometimes repeat: raise Complexity for more variety."
    return True, ""


def job(state, only="", copies=1, vary=False):
    """What Print and Save PDF produce. only: a choice of pages as parse_pages() reads it (booklets and photo
    books; empty for all). copies: how many of a single page, each with its own design when vary (Make one up).
    Raises ValueError when the choice of pages doesn't make sense."""
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
        picked = parse_pages(only, pages)
        part = bool((only or "").strip()) and len(picked) < len(pages)
        if part:   # inkline-booklet-123-p1_3-5_8
            name += "-p" + describe_pages(picked, len(pages)).split(" ", 1)[1].replace("–", "-") \
                .replace(", ", "_").replace(" and ", "_")
        if s.fold:
            pages = book.fold_pages(pages)
            sides = [k for sheet in (fold_sheets(picked, len(pages)) if part else range(len(pages) // 4))
                     for k in (2 * sheet, 2 * sheet + 1)]
            return Job(f"{name}-fold", label, len(sides), "landscape", book.sheet_geometry(s),
                       lambda ctx, i: book.draw_fold_side(ctx, s, pages, sides[i]), duplex=True)
        g = geometry(s)
        return Job(name, label, len(picked), s.orient, g, lambda ctx, i: draw_page(ctx, g, pages[picked[i]], s))
    g, spec = geometry(s), single_page(s, state.photo)
    copies = max(1, min(MAX_COPIES, int(copies or 1)))
    if copies == 1:
        return Job(base_name(state), "page", 1, s.orient, g, lambda ctx, i: draw_page(ctx, g, spec, s))
    vary = vary and copies_vary(s)[0]   # a photo has one look, a plain name page one design: their copies are alike
    name = f"{base_name(state)}-{copies}{'-designs' if vary else '-copies'}"

    def draw(ctx, i):
        if not vary:
            return draw_page(ctx, g, spec, s)
        si = replace(s, seed=copy_seed(s.seed, i))
        return draw_page(ctx, g, single_page(si, state.photo), si)
    return Job(name, "copies", copies, s.orient, g, draw)


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


def forget_printer_margins():
    _margin_cache.clear()


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
