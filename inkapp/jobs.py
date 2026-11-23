"""What Print and Save produce, for whatever the state shows (2.x's job, runBook, runPoster...).

A Job is a run of pages at true paper size, each drawn with the engine at the settings' dpi: the page,
every page of a booklet or photo book, the sides of a fold-and-staple book, or a poster's sheets.
run() draws a job onto a QPdfWriter or QPrinter, page by page, on whatever thread calls it.
"""

import re
from dataclasses import dataclass, replace

from PySide6.QtCore import QMarginsF, QRectF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPicture
from PySide6.QtPrintSupport import QPrinter

from inkengine import book, output, poster
from inkengine.canvas import QtCanvas
from inkengine.page import PANELS, PageSpec, draw_page, geometry, has_answer, panel_specs, single_page
from inkengine.testpage import draw_test_page

from .classset import (MAX_COPIES, ClassSet, copies_have_answers, copies_vary, copy_labels, copy_seed,  # noqa: F401
                       copy_settings, named_pages, parse_names)
from .render import shown_copy, view

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
    answers: int = 0       # copies: answer pages after them; booklets: the answer book's pages (counted in count)
    copies: int = 0        # booklets: how many booklets the pages make up

    @property
    def unit(self):
        return "sheet" if self.label == "poster" else "page"

    def amount(self):
        """ "14-page booklet", "2 sheets (both sides)": what the job prints, for the status line."""
        if self.duplex:   # a fold-and-staple book: two printed sides per sheet
            n = self.count // 2
            sheets = f"{n} sheet{'s' if n != 1 else ''} (both sides)"
            books = f"{self.copies} booklet{'s' if self.copies != 1 else ''}" + (" and an answer book" if self.answers else "")
            return f"{books}, {sheets}" if self.label == "booklets" else sheets
        if self.label == "booklets":
            kids = f"{self.copies} booklet{'s' if self.copies != 1 else ''}"
            if self.answers:
                n = self.answers
                return f"{kids} ({self.count - n} pages) and a {n}-page answer book"
            return f"{kids} ({self.count} pages)"
        if self.label == "copies":
            n = self.count - self.answers
            keys = f" and {self.answers} answer page{'s' if self.answers != 1 else ''}" if self.answers else ""
            return f"{n} copies{keys}"
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





def job(state, only="", copies=1, vary=False, answers=False, names=(), answer_book=False):
    """What Print and Save PDF produce. only: a choice of pages as parse_pages() reads it (booklets and photo
    books; empty for all). copies: how many of a single page, each with its own design when vary (Make one up),
    then with answers their answer pages, each copy numbered to match. Raises ValueError when the choice of
    pages doesn't make sense. names: a class set, one copy per name, each name on its copy's "Name" line (only
    with the Name line on); they replace copies."""
    s, v = state.settings, view(state)
    if v.kind == "testpage":
        st = replace(s, orient="portrait")
        return Job("inkline-printer-test", "test page", 1, "portrait", geometry(st), lambda ctx, i: draw_test_page(ctx, st))
    if v.kind == "poster":
        P, spec = poster.poster_geometry(s), single_page(s, state.photo)
        return Job(f"{base_name(state)}-poster-{P.cols}x{P.rows}", "poster", P.sheets, s.orient, geometry(s),
                   lambda ctx, i: poster.draw_sheet(ctx, s, P, spec, i))
    photo_book = s.mode == "convert" and s.photobook and state.photos
    named = list(names)[:MAX_COPIES] if s.name_line else []
    if v.kind in ("booklet", "fold") and not photo_book and (named or int(copies or 1) > 1):
        return _booklets(state, only, copies, vary, named, answer_book and s.key)
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
    names = list(names)[:MAX_COPIES] if s.name_line else []
    copies = len(names) if names else max(1, min(MAX_COPIES, int(copies or 1)))
    if copies == 1 and not names:
        return Job(base_name(state), "page", 1, s.orient, g, lambda ctx, i: draw_page(ctx, g, spec, s))
    vary = vary and copies_vary(s)[0]   # a photo has one look, a plain name page one design: their copies are alike
    name = f"{base_name(state)}-{copies}{'-designs' if vary else '-copies'}{'-named' if names else ''}"
    answers = answers and copies_have_answers(s)
    labels = copy_labels(names) if names else [f"Copy {i + 1}" for i in range(copies)]

    def copy_spec(i):
        si = replace(spec, seed=copy_seed(s.seed, i)) if vary else spec
        return replace(si, filled_name=names[i]) if names else si
    if not answers:
        return Job(name, "copies", copies, s.orient, g, lambda ctx, i: draw_page(ctx, g, copy_spec(i), s))
    # each answer is called by its copy's name, or "Copy 7", which unnamed copies carry under them (in the
    # margin: a page number's band would shrink the design, and copy 1 would no longer be the one shown); alike
    # copies share one answer
    designs = [replace(copy_spec(i), stamp="" if names else labels[i],
                       key_label=labels[i] if vary else "Every copy") for i in range(copies)]
    solved = designs if vary else designs[:1]
    if PANELS.get(s.sheet, 1) > 1:   # a sheet of several designs: an answer for each puzzle on it
        solved = [p for d in solved for p in panel_specs(g, d, s) if has_answer(p.gen, s)]
    keys = [PageSpec(kind="answers", header=True, title="Answers", items=solved[k:k + 4])
            for k in range(0, len(solved), 4)]
    pages = designs + keys
    return Job(name + "-with-answers", "copies", len(pages), s.orient, g,
               lambda ctx, i: draw_page(ctx, g, pages[i], s), answers=len(keys))


def _booklets(state, only, copies, vary, names, answer_book=False):
    """A class set of booklets: each its own (with vary, its own designs; with names, the child's name on the
    cover, on every Name line and over its answers), one after another, each with only the pages chosen. With
    answer_book, the answer pages leave the children's booklets and follow them all as the teacher's answer book,
    each headed with its child's name (or "Booklet 3", which that booklet's cover then says too)."""
    s = state.settings
    copies = len(names) if names else max(1, min(MAX_COPIES, int(copies or 1)))
    vary = vary and s.mode == "make"

    def whose(i):
        return names[i] if names else f"Booklet {i + 1}" if answer_book else ""
    books = [(si, named_pages(book.book_pages(si), whose(i)))
             for i, si in enumerate(copy_settings(s, i, vary) for i in range(copies))]
    keys = []
    if answer_book:   # the answers, in booklet order, without the booklet's page numbers
        keys = [replace(p, page_no=0) for _si, ps in books for p in ps if p.kind == "answers"]
        books = [(si, [p for p in ps if p.kind != "answers"]) for si, ps in books]
    first = books[0][1]
    picked = parse_pages(only, first)   # every booklet has the same pages, so they're chosen once
    part = bool((only or "").strip()) and len(picked) < len(first)
    name = f"inkline-booklet-{s.seed}-{copies}-booklets{'-named' if names else ''}{'-answer-book' if keys else ''}"
    if part:
        name += "-p" + describe_pages(picked, len(first)).split(" ", 1)[1].replace("–", "-") \
            .replace(", ", "_").replace(" and ", "_")
    if s.fold:   # each booklet folds and staples on its own: its sheets, one booklet after another
        sides = []
        for si, pages in books:
            folded = book.fold_pages(pages)
            sheets = fold_sheets(picked, len(folded)) if part else range(len(folded) // 4)
            sides += [(si, folded, k) for sheet in sheets for k in (2 * sheet, 2 * sheet + 1)]
        if keys:   # the answer book folds as a booklet of its own
            folded = book.fold_pages(keys)
            sides += [(s, folded, k) for sheet in range(len(folded) // 4) for k in (2 * sheet, 2 * sheet + 1)]
        return Job(f"{name}-fold", "booklets", len(sides), "landscape", book.sheet_geometry(s),
                   lambda ctx, i: book.draw_fold_side(ctx, *sides[i]), duplex=True, copies=copies, answers=len(keys))
    g = geometry(s)
    pages = [(si, ps[k]) for si, ps in books for k in picked] + [(s, p) for p in keys]
    return Job(name, "booklets", len(pages), s.orient, g, lambda ctx, i: draw_page(ctx, g, pages[i][1], pages[i][0]),
               copies=copies, answers=len(keys))


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
    """Draw every page of the job onto a QPdfWriter or QPrinter (already set up). True when finished.
    A printer gets the job only once every page is drawn (see _print), so cancelling never prints anything."""
    if isinstance(device, QPrinter):
        return _print(j, device, progress, cancelled)
    return _draw(j, device, progress, cancelled)


def _page_window(p, g):
    """Page pixels at the settings' dpi onto the device's whole page."""
    p.setWindow(0, 0, g.W, g.H)
    vp = p.viewport()
    sc = min(vp.width() / g.W, vp.height() / g.H)
    w, h = round(g.W * sc), round(g.H * sc)
    p.setViewport(vp.x() + (vp.width() - w) // 2, vp.y() + (vp.height() - h) // 2, w, h)


def _print(j, printer, progress, cancelled):
    """Print a job: every page is drawn first (recorded as a QPicture), and only then is the printer started
    and the pages played onto it. Not every printer system can call a job off once it's started (Qt can't on
    Linux), so a cancel while drawing leaves nothing sent; once sending starts it's quick and isn't stopped."""
    g, pages = j.geometry, []
    for i in range(j.count):
        if cancelled():
            return False
        if progress:
            progress(i)
        pic = QPicture()
        p = QPainter(pic)
        try:
            j.draw(QtCanvas(p, g.W, g.H), i)
        finally:
            p.end()
        pages.append(pic)
    if cancelled():
        return False
    if progress:
        progress(j.count)   # every page drawn: now they go to the printer
    p = QPainter()
    if not p.begin(printer):
        return False
    try:
        for i, pic in enumerate(pages):
            if i and not printer.newPage():
                return False
            p.save()
            _page_window(p, g)
            # a picture plays back scaled from the resolution it was recorded at to the printer's: undo that,
            # so it lands where the page's own coordinates say
            p.scale(pic.logicalDpiX() / printer.logicalDpiX(), pic.logicalDpiY() / printer.logicalDpiY())
            p.drawPicture(0, 0, pic)
            p.restore()
        return True
    finally:
        p.end()


def _draw(j, device, progress=None, cancelled=lambda: False):
    """Draw every page of the job straight onto a PDF (a QPdfWriter). cancelled() is asked before each page:
    when it says so, False is returned and the half-written PDF is left for the caller to delete."""
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
            p.save()
            _page_window(p, g)
            j.draw(QtCanvas(p, g.W, g.H), i)
            p.restore()
        return True
    finally:
        p.end()


def _shown(state):
    """The settings and page the preview shows, with a class set's copy (its designs and name) when it shows one;
    and what to add to the file name for it ("-copy2")."""
    s, v = state.settings, view(state)
    c = shown_copy(state)
    if c is not None:
        s = c[0]
    spec = v.pages[v.index] if v.pages and v.kind != "fold" else single_page(s, state.photo)
    if c is not None and not v.pages and c[1]:
        spec = replace(spec, filled_name=c[1])
    return s, v, spec, (f"-copy{c[2] + 1}" if c is not None and c[2] else "")


def _shown_name(state):
    c = shown_copy(state)
    return c[1] if c is not None else ""


def svg(state):
    """The page shown as SVG (a poster: the whole poster), and the file name to suggest."""
    s, v, spec, more = _shown(state)
    if v.kind in ("fold", "testpage"):
        raise ValueError("fold-and-staple sides and the test page don't save as SVG")
    suffix = "-poster" if v.kind == "poster" else f"-page{v.index + 1}" if v.pages else ""
    return output.svg_text(s, spec), base_name(state) + more + suffix


def png(state):
    """The page shown, at full resolution, and the file name to suggest."""
    s, v, spec, more = _shown(state)
    if v.kind == "testpage":
        j = job(state)
        return output_image(j, 0), j.name
    if v.kind == "fold":   # the side shown, of the copy shown (its designs)
        names = [c_name] if (c_name := _shown_name(state)) else []
        return output_image(job(replace(state, settings=s, class_set=None), names=names), v.index), base_name(state) + more
    return output.render_image(s, spec), base_name(state) + more   # 2.x's PNG name, whichever page is shown


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
