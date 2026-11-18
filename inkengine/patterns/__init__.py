"""Pattern generators. Each one draws into a box on a Canvas from a seeded random function.

GENERATORS maps a pattern name to draw(ctx, box, rnd, complexity, settings, **opts). Patterns not yet
ported from index.html aren't listed.
"""

from . import maze

GENERATORS = {
    "maze": maze.draw,
}

NAMES = {"maze": "Maze"}

# Puzzles that have a solution to show on answer pages.
HAS_ANSWER = {"maze"}
