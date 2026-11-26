"""Pattern generators. Each one draws into a box on a Canvas from a seeded random function.

GENERATORS maps a pattern name to draw(ctx, box, rnd, complexity, settings, lw=, seed=, dpi=, **opts):
the line width, the design's seed (some patterns seed their noise with it) and the page's dpi. Patterns not yet
ported from index.html aren't listed.
"""

from . import bingo, clock, contour, crossword, dots, flow, fractions, reward, ruled, kakuro, mandala, maths, maze, name, nonogram, reading, scramble, spelltest, spot, symmetry, sudoku, trace, truchet, words

GENERATORS = {
    "contour": contour.draw,
    "dots": dots.draw,
    "flow": flow.draw,
    "kakuro": kakuro.draw,
    "mandala": mandala.draw,
    "maze": maze.draw,
    "name": name.draw,
    "nonogram": nonogram.draw,
    "spot": spot.draw,
    "sudoku": sudoku.draw,
    "truchet": truchet.draw,
    "words": words.draw,
    "maths": maths.draw,
    "trace": trace.draw,
    "crossword": crossword.draw,
    "clock": clock.draw,
    "scramble": scramble.draw,
    "spelltest": spelltest.draw,
    "fractions": fractions.draw,
    "symmetry": symmetry.draw,
    "ruled": ruled.draw,
    "reward": reward.draw,
    "reading": reading.draw,
    "bingo": bingo.draw,
}

NAMES = {"contour": "Contours", "dots": "Dot-to-dot", "flow": "Flow lines", "kakuro": "Kakuro", "mandala": "Mandala", "maze": "Maze", "name": "Name page", "nonogram": "Nonogram", "spot": "Spot the difference", "sudoku": "Sudoku", "truchet": "Woven tiles", "words": "Word search", "maths": "Maths drill", "trace": "Handwriting", "crossword": "Crossword", "clock": "Telling the time", "scramble": "Unscramble", "spelltest": "Spelling test", "fractions": "Fractions and number lines", "symmetry": "Symmetry", "ruled": "Graph and lined paper", "reward": "Reward chart", "reading": "Reading comprehension", "bingo": "Bingo"}

# Puzzles that have a solution to show on answer pages.
HAS_ANSWER = {"maze", "dots", "sudoku", "words", "nonogram", "spot", "kakuro", "maths", "crossword", "clock", "scramble", "spelltest", "fractions", "symmetry", "reading", "bingo"}
