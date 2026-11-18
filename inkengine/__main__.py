"""Command line for the 3.0 engine (a preview of what's ported so far).

    python3 -m inkengine maze -o maze.pdf
    python3 -m inkengine maze --shape heart --complexity 7 --seed 42 -o heart.svg
    python3 -m inkengine maze --shape word --word Maya --answers -o maya.pdf
    python3 -m inkengine mandala --complexity 8 -o mandala.svg
"""

import argparse
import random
import sys

from .page import PageSpec, Settings, answer_page, single_page
from .patterns import GENERATORS, HAS_ANSWER, maze


def main(argv=None):
    ap = argparse.ArgumentParser(prog="inkengine", description="Draw an Inkline page without the HTML app.")
    ap.add_argument("pattern", choices=sorted(GENERATORS))
    ap.add_argument("-o", "--out", required=True, help="output file: .pdf, .png or .svg")
    ap.add_argument("--seed", type=int, help="design number (default: random)")
    ap.add_argument("--complexity", type=int, default=5, choices=range(1, 11), metavar="1-10")
    ap.add_argument("--weight", type=int, default=4, choices=range(1, 11), metavar="1-10", help="line weight")
    ap.add_argument("--shape", default="rect", choices=maze.SHAPES, help="maze shape")
    ap.add_argument("--word", default="Maze", help="word or name for --shape word (up to 12 letters)")
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
                 maze_shape=a.shape, maze_word=a.word[:12])
    from . import output   # imported here so --help works without starting Qt
    if a.answers:
        if s.gen not in HAS_ANSWER:
            ap.error(f"--answers: {s.gen} pages have no answers")
        if not a.out.lower().endswith(".pdf"):
            ap.error("--answers needs a .pdf output (the answer is a second page)")
        puzzle = single_page(s)
        key = answer_page([PageSpec(gen=puzzle.gen, seed=puzzle.seed, c=puzzle.c, title=puzzle.title,
                                    name=puzzle.name, label=f"{s.gen.title()} {s.seed}")])
        output.write_pdf(a.out, s, [puzzle, key])
    else:
        output.write(a.out, s)
    print(f"wrote {a.out} (seed {s.seed})")


if __name__ == "__main__":
    sys.exit(main())
