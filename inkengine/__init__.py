"""Inkline's drawing engine in plain Python and Qt (no HTML or JavaScript).

It is being ported from index.html one pattern at a time for Inkline 3.0. The 2.x app does not use it
yet. What it covers so far:

- noise.py     smooth value noise (contours, flow lines), matching index.html's makeNoise
- rng.py       mulberry32, the same seeded generator as index.html, so a seed draws the same design
- shapes.py    outlines and details for dot-to-dots and shaped mazes
- canvas.py    one drawing API with two back ends: QPainter (screen, PNG, PDF, printer) and SVG
- page.py      paper sizes, settings and page layout (title, name line, page number, border)
- patterns/    the generators ported so far: maze.py, mandala.py, truchet.py (woven tiles),
               contour.py, flow.py, dots.py (dot-to-dot), sudoku.py,
               words.py (word search), nonogram.py, name.py (name pages)
- book.py      booklets and photo books: covers, pages, answer pages, fold-and-staple sheets
- photo.py     photos to black & white: dithers, line drawing, halftone, engraving, stippling, nonograms
- cbn.py       colour by number, for photos and patterns
- testpage.py  the printer test page
- poster.py    posters: one design across several sheets, with trim marks and labels
- output.py    write a page as PNG, PDF or SVG, a booklet or poster as PDF
"""

__all__ = ["rng", "canvas", "page", "output"]
