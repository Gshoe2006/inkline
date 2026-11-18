"""Pattern generators. Each one draws into a box on a Canvas from a seeded random function.

GENERATORS maps a pattern name to draw(ctx, box, rnd, complexity, settings, lw=, seed=, dpi=, **opts):
the line width, the design's seed (some patterns seed their noise with it) and the page's dpi. Patterns not yet
ported from index.html aren't listed.
"""

from . import contour, dots, flow, mandala, maze, name, nonogram, sudoku, truchet, words

GENERATORS = {
    "contour": contour.draw,
    "dots": dots.draw,
    "flow": flow.draw,
    "mandala": mandala.draw,
    "maze": maze.draw,
    "name": name.draw,
    "nonogram": nonogram.draw,
    "sudoku": sudoku.draw,
    "truchet": truchet.draw,
    "words": words.draw,
}

NAMES = {"contour": "Contours", "dots": "Dot-to-dot", "flow": "Flow lines", "mandala": "Mandala", "maze": "Maze", "name": "Name page", "nonogram": "Nonogram", "sudoku": "Sudoku", "truchet": "Woven tiles", "words": "Word search"}

# Puzzles that have a solution to show on answer pages.
HAS_ANSWER = {"maze", "dots", "sudoku", "words", "nonogram"}
