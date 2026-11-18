"""Inkline's drawing engine in plain Python and Qt (no HTML or JavaScript).

It is being ported from index.html one pattern at a time for Inkline 3.0. The 2.x app does not use it
yet. What it covers so far:

- rng.py       mulberry32, the same seeded generator as index.html, so a seed draws the same design
- canvas.py    one drawing API with two back ends: QPainter (screen, PNG, PDF, printer) and SVG
- page.py      paper sizes, settings and page layout (title, name line, page number, border)
- patterns/    the generators; maze.py is the first one ported
- output.py    write a page as PNG, PDF or SVG
"""

__all__ = ["rng", "canvas", "page", "output"]
