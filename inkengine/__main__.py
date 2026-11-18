"""Command line for the 3.0 engine (a preview of what's ported so far).

    python3 -m inkengine maze -o maze.pdf
    python3 -m inkengine maze --shape heart --complexity 7 --seed 42 -o heart.svg
    python3 -m inkengine maze --shape word --word Maya --answers -o maya.pdf
    python3 -m inkengine mandala --complexity 8 -o mandala.svg
    python3 -m inkengine truchet --complexity 6 --frame -o tiles.pdf    (woven tiles)
    python3 -m inkengine contour --complexity 8 -o map.pdf
    python3 -m inkengine flow -o flow.png
    python3 -m inkengine dots --complexity 6 --answers -o dots.pdf    (dot-to-dot)
    python3 -m inkengine sudoku --complexity 8 --answers -o sudoku.pdf
    python3 -m inkengine words --theme ocean --answers -o words.pdf    (word search)
    python3 -m inkengine words --words "mum, dad, grandma, pizza" -o ours.pdf
"""

import argparse
import random
import sys

from .page import PageSpec, Settings, answer_page, single_page
from .patterns import GENERATORS, HAS_ANSWER, NAMES, maze, words


def main(argv=None):
    ap = argparse.ArgumentParser(prog="inkengine", description="Draw an Inkline page without the HTML app.")
    ap.add_argument("pattern", choices=sorted(GENERATORS))
    ap.add_argument("-o", "--out", required=True, help="output file: .pdf, .png or .svg")
    ap.add_argument("--seed", type=int, help="design number (default: random)")
    ap.add_argument("--complexity", type=int, default=5, choices=range(1, 11), metavar="1-10")
    ap.add_argument("--weight", type=int, default=4, choices=range(1, 11), metavar="1-10", help="line weight")
    ap.add_argument("--shape", default="rect", choices=maze.SHAPES, help="maze shape")
    ap.add_argument("--word", default="Maze", help="word or name for --shape word (up to 12 letters)")
    ap.add_argument("--theme", default="animals", choices=sorted(words.THEME_NAMES), help="word search words")
    ap.add_argument("--words", default="", help='word search: your own words, e.g. "mum, dad, pizza" (sets --theme custom)')
    ap.add_argument("--title", default="")
    ap.add_argument("--name-line", action="store_true", help='add a "Name ____" line')
    ap.add_argument("--frame", action="store_true", help="draw a border around the design")
    ap.add_argument("--paper", default="letter", choices=["letter", "a4"])
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--margin", type=float, default=0.5, choices=[0.25, 0.5, 0.75, 1.0])
    ap.add_argument("--dpi", type=int, default=300, choices=[150, 300])
    ap.add_argument("--answers", action="store_true", help="PDF only: add an answer page")
    a = ap.parse_args(argv)

    s = Settings(gen=a.pattern, seed=a.seed if a.seed is not None else random.randrange(10**9),
                 complexity=a.complexity, weight=a.weight, frame=a.frame, title=a.title, name_line=a.name_line,
                 paper=a.paper, orient="landscape" if a.landscape else "portrait", margin=a.margin, dpi=a.dpi,
                 maze_shape=a.shape, maze_word=a.word[:12],
                 ws_theme="custom" if a.words else a.theme, ws_words=a.words[:300])
    from . import output   # imported here so --help works without starting Qt
    if a.answers:
        if s.gen not in HAS_ANSWER:
            ap.error(f"--answers: {s.gen} pages have no answers")
        if not a.out.lower().endswith(".pdf"):
            ap.error("--answers needs a .pdf output (the answer is a second page)")
        puzzle = single_page(s)
        key = answer_page([PageSpec(gen=puzzle.gen, seed=puzzle.seed, c=puzzle.c, title=puzzle.title,
                                    name=puzzle.name, label=f"{NAMES[s.gen]} {s.seed}")])
        output.write_pdf(a.out, s, [puzzle, key])
    else:
        output.write(a.out, s)
    print(f"wrote {a.out} (seed {s.seed})")
    if s.gen == "words":   # tell the person about words that didn't fit, as the 2.x app does
        from .box import Box
        from .canvas import RecordingCanvas
        from .page import design_box, geometry
        from .rng import mulberry32
        g = geometry(s)
        ws = words.draw(RecordingCanvas(), design_box(g, single_page(s), s), mulberry32(s.seed), s.complexity, s, dpi=g.dpi)
        if words.note(ws):
            print(words.note(ws))


if __name__ == "__main__":
    sys.exit(main())
