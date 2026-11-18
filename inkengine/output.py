"""Write a page as PNG, PDF or SVG, all drawn by the same draw_page() code.

PDFs are vector (lines stay sharp at any zoom and print at the printer's full resolution), unlike
2.x, which placed a picture of the page in the PDF.
"""

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QPdfWriter

from .canvas import QtCanvas, SvgCanvas
from .page import draw_page, geometry, single_page
from .qt import ensure_app


def render_image(s, spec=None):
    """The page as a QImage at the settings' dpi (preview and PNG)."""
    ensure_app()
    g = geometry(s)
    img = QImage(g.W, g.H, QImage.Format.Format_RGB32)
    img.setDotsPerMeterX(round(g.dpi / 0.0254))
    img.setDotsPerMeterY(round(g.dpi / 0.0254))
    p = QPainter(img)
    try:
        draw_page(QtCanvas(p, g.W, g.H), g, spec or single_page(s), s)
    finally:
        p.end()
    return img


def write_png(path, s, spec=None):
    if not render_image(s, spec).save(str(path), "PNG"):
        raise OSError(f"couldn't write {path}")


def _page_layout(g):
    size = QPageSize(QSizeF(g.w, g.h), QPageSize.Unit.Inch, "", QPageSize.SizeMatchPolicy.FuzzyMatch)
    orient = QPageLayout.Orientation.Landscape if g.w > g.h else QPageLayout.Orientation.Portrait
    if orient == QPageLayout.Orientation.Landscape:
        size = QPageSize(QSizeF(g.h, g.w), QPageSize.Unit.Inch, "", QPageSize.SizeMatchPolicy.FuzzyMatch)
    return QPageLayout(size, orient, QMarginsF(0, 0, 0, 0))


def write_pdf(path, s, specs=None):
    """A vector PDF; specs is a list of pages (default: the single page the settings describe)."""
    ensure_app()
    g = geometry(s)
    pdf = QPdfWriter(str(path))
    pdf.setCreator("Inkline")
    pdf.setTitle(s.title.strip() or "Inkline")
    pdf.setResolution(g.dpi)          # one painter unit = one page pixel, as on screen
    pdf.setPageLayout(_page_layout(g))
    p = QPainter()
    if not p.begin(pdf):
        raise OSError(f"couldn't write {path}")
    try:
        for i, spec in enumerate(specs or [single_page(s)]):
            if i:
                pdf.newPage()
            draw_page(QtCanvas(p, g.W, g.H), g, spec, s)
    finally:
        p.end()


def write_book_pdf(path, s, photos=None):
    """A whole booklet, or with photos a photo book, as one PDF: a page per page, or for a fold-and-staple
    book (s.fold) one landscape sheet side per PDF page, to print double-sided (flip on the short edge)."""
    from .book import book_pages, draw_fold_side, fold_order, fold_pages, photo_book_pages, sheet_geometry
    ensure_app()
    pages = photo_book_pages(s, photos) if photos else book_pages(s)
    if s.fold:
        pages = fold_pages(pages)
        g = sheet_geometry(s)
        sides = range(len(fold_order(len(pages))))
    else:
        g = geometry(s)
    pdf = QPdfWriter(str(path))
    pdf.setCreator("Inkline")
    pdf.setTitle(s.title.strip() or ("Inkline photo book" if photos else "Inkline booklet"))
    pdf.setResolution(g.dpi)
    pdf.setPageLayout(_page_layout(g))
    p = QPainter()
    if not p.begin(pdf):
        raise OSError(f"couldn't write {path}")
    try:
        for i in (sides if s.fold else range(len(pages))):
            if i:
                pdf.newPage()
            ctx = QtCanvas(p, g.W, g.H)
            if s.fold:
                draw_fold_side(ctx, s, pages, i)
            else:
                draw_page(ctx, g, pages[i], s)
    finally:
        p.end()
    return len(sides) if s.fold else len(pages)


def write_poster_pdf(path, s, spec=None):
    """Every sheet of the poster, one per PDF page, at true paper size."""
    from .poster import draw_sheet, poster_geometry
    ensure_app()
    g, P = geometry(s), poster_geometry(s)
    spec = spec or single_page(s)
    pdf = QPdfWriter(str(path))
    pdf.setCreator("Inkline")
    pdf.setTitle(s.title.strip() or "Inkline poster")
    pdf.setResolution(g.dpi)
    pdf.setPageLayout(_page_layout(g))
    p = QPainter()
    if not p.begin(pdf):
        raise OSError(f"couldn't write {path}")
    try:
        for i in range(P.sheets):
            if i:
                pdf.newPage()
            draw_sheet(QtCanvas(p, g.W, g.H), s, P, spec, i)
    finally:
        p.end()
    return P.sheets


def write_test_page(path, s, version=""):
    """The printer test page as PNG, PDF or SVG (always portrait)."""
    from dataclasses import replace
    from .testpage import draw_test_page
    ensure_app()
    s = replace(s, orient="portrait")
    g = geometry(s)
    ext = str(path).lower().rsplit(".", 1)[-1]
    if ext == "svg":
        ctx = SvgCanvas(g.W, g.H, g.w, g.h)
        draw_test_page(ctx, s, version)
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(ctx))
        return
    if ext == "pdf":
        dev = QPdfWriter(str(path))
        dev.setCreator("Inkline")
        dev.setTitle("Printer test page")
        dev.setResolution(g.dpi)
        dev.setPageLayout(_page_layout(g))
    elif ext == "png":
        dev = QImage(g.W, g.H, QImage.Format.Format_RGB32)
        dev.setDotsPerMeterX(round(g.dpi / 0.0254))
        dev.setDotsPerMeterY(round(g.dpi / 0.0254))
    else:
        raise ValueError(f"{path}: use a .png, .pdf or .svg file name")
    p = QPainter()
    if not p.begin(dev):
        raise OSError(f"couldn't write {path}")
    try:
        draw_test_page(QtCanvas(p, g.W, g.H), s, version)
    finally:
        p.end()
    if ext == "png" and not dev.save(str(path), "PNG"):
        raise OSError(f"couldn't write {path}")


def svg_text(s, spec=None):
    """The page as SVG; for a poster (s.poster), the whole poster as one big vector page."""
    if s.poster:
        from .poster import poster_geometry
        g = poster_geometry(s)
        ctx = SvgCanvas(g.W, g.H, g.w, g.h)
        draw_page(ctx, g, spec or single_page(s), s)
        return str(ctx)
    g = geometry(s)
    ctx = SvgCanvas(g.W, g.H, g.w, g.h)
    draw_page(ctx, g, spec or single_page(s), s)
    return str(ctx)


def write_svg(path, s, spec=None):
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_text(s, spec))


def write(path, s, spec=None):
    """Pick the format from the file name: .png, .pdf or .svg."""
    ext = str(path).lower().rsplit(".", 1)[-1] if "." in str(path) else ""
    if ext == "pdf":
        return write_pdf(path, s, [spec] if spec else None)
    if ext == "png":
        return write_png(path, s, spec)
    if ext == "svg":
        return write_svg(path, s, spec)
    raise ValueError(f"{path}: use a .png, .pdf or .svg file name")
