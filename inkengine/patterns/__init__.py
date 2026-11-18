"""Pattern generators. Each one draws into a box on a Canvas from a seeded random function.

GENERATORS maps a pattern name to draw(ctx, box, rnd, complexity, settings, lw=line width, **opts). Patterns not yet
ported from index.html aren't listed.
"""

from . import mandala, maze

GENERATORS = {
    "mandala": mandala.draw,
    "maze": maze.draw,
}

NAMES = {"mandala": "Mandala", "maze": "Maze"}

# Puzzles that have a solution to show on answer pages.
HAS_ANSWER = {"maze"}
