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


def svg_text(s, spec=None):
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
