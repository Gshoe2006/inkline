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
    python3 -m inkengine nonogram --complexity 6 --answers -o picture.pdf
    python3 -m inkengine name --text "Happy Birthday Maya" --background flow -o card.pdf    (name page)
    python3 -m inkengine maze --booklet 10 --title "Rainy Day Mazes" -o mazes.pdf
    python3 -m inkengine mandala --booklet 12 --mix --fold -o book.pdf    (fold-and-staple)
    python3 -m inkengine mandala --poster 3x3 -o poster.pdf    (nine sheets to tape together)
    python3 -m inkengine photo --image cat.jpg --style halftone -o cat.pdf
    python3 -m inkengine photo --image cat.jpg --style cbn --crayons 10 -o colour-me.pdf
    python3 -m inkengine mandala --cbn 6 --booklet 4 -o numbers.pdf    (colour-by-number booklet with shaded answers)
    python3 -m inkengine testpage -o test.pdf    (printer test page)
"""

import argparse
import random
import sys

from .page import PageSpec, Settings, answer_page, single_page
from . import photo, poster
from .patterns import GENERATORS, HAS_ANSWER, NAMES, maze, name, words


def main(argv=None):
    ap = argparse.ArgumentParser(prog="inkengine", description="Draw an Inkline page without the HTML app.")
    ap.add_argument("pattern", choices=sorted(GENERATORS) + ["photo", "testpage"],
                    help="a pattern, photo to convert --image, or testpage for the printer test page")
    ap.add_argument("-o", "--out", required=True, help="output file: .pdf, .png or .svg")
    ap.add_argument("--seed", type=int, help="design number (default: random)")
    ap.add_argument("--complexity", type=int, default=5, choices=range(1, 11), metavar="1-10")
    ap.add_argument("--weight", type=int, default=4, choices=range(1, 11), metavar="1-10", help="line weight")
    ap.add_argument("--shape", default="rect", choices=maze.SHAPES, help="maze shape")
    ap.add_argument("--word", default="Maze", help="word or name for --shape word (up to 12 letters)")
    ap.add_argument("--theme", default="animals", choices=sorted(words.THEME_NAMES), help="word search words")
    ap.add_argument("--words", default="", help='word search: your own words, e.g. "mum, dad, pizza" (sets --theme custom)')
    ap.add_argument("--text", default="Hello", help="name page: the name or word (up to 40 characters)")
    ap.add_argument("--background", default="none", choices=sorted(name.BACKGROUNDS), help="name page: pattern under the letters")
    ph = ap.add_argument_group("photos (pattern: photo)")
    ph.add_argument("--image", help="the picture to convert (PNG, JPEG...)")
    ph.add_argument("--style", default="fs", choices=photo.STYLES, help="photo style")
    ph.add_argument("--brightness", type=int, default=0, metavar="-100..100")
    ph.add_argument("--contrast", type=int, default=110, metavar="20..300")
    ph.add_argument("--threshold", type=int, default=128, metavar="1..254", help="threshold, or detail for line drawings")
    ph.add_argument("--dot", type=int, default=2, choices=range(1, 9), metavar="1-8", help="dot size")
    ph.add_argument("--fill", action="store_true", help="fill the page (crop) instead of fitting inside")
    ph.add_argument("--invert", action="store_true")
    ph.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270])
    ph.add_argument("--zoom", type=int, default=100, metavar="100..400")
    ph.add_argument("--squares", type=int, default=15, metavar="10..30", help="photo nonogram squares across")
    ph.add_argument("--crayons", type=int, default=8, metavar="4..16", help="colour by number (--style cbn): crayons to use")
    ph.add_argument("--solved", action="store_true", help="photo nonogram: draw it solved")
    ap.add_argument("--title", default="")
    ap.add_argument("--name-line", action="store_true", help='add a "Name ____" line')
    ap.add_argument("--frame", action="store_true", help="draw a border around the design")
    ap.add_argument("--cbn", type=int, metavar="CRAYONS", help="colour by number with 3-12 crayons (mandala, truchet, contour, name)")
    ap.add_argument("--paper", default="letter", choices=["letter", "a4"])
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--margin", type=float, default=0.5, choices=[0.25, 0.5, 0.75, 1.0])
    ap.add_argument("--dpi", type=int, default=300, choices=[150, 300])
    ap.add_argument("--answers", action="store_true", help="PDF only: add an answer page")
    bk = ap.add_argument_group("booklets (PDF only)")
    bk.add_argument("--booklet", type=int, metavar="PAGES", help="a booklet of 2-40 design pages")
    bk.add_argument("--mix", action="store_true", help="every pattern in turn (the pattern argument is ignored)")
    bk.add_argument("--same-difficulty", action="store_true", help="don't ramp difficulty up page by page")
    bk.add_argument("--no-cover", action="store_true")
    bk.add_argument("--no-page-numbers", action="store_true")
    bk.add_argument("--no-answers", action="store_true", help="leave out the answer pages")
    bk.add_argument("--fold", action="store_true", help="fold-and-staple: two half-size pages per side, print double-sided")
    po = ap.add_argument_group("posters")
    po.add_argument("--poster", choices=poster.GRIDS, metavar="GRID",
                    help="print big across sheets: " + ", ".join(poster.GRIDS) + " (across x down); PDF gives the sheets, SVG the whole poster")
    po.add_argument("--overlap", type=float, default=0.25, choices=[0, 0.25, 0.5], help="inches neighbouring sheets share")
    a = ap.parse_args(argv)

    s = Settings(gen=a.pattern if a.pattern in GENERATORS else "maze", seed=a.seed if a.seed is not None else random.randrange(10**9),
                 complexity=a.complexity, weight=a.weight, frame=a.frame, title=a.title, name_line=a.name_line,
                 paper=a.paper, orient="landscape" if a.landscape else "portrait", margin=a.margin, dpi=a.dpi,
                 maze_shape=a.shape, maze_word=a.word[:12],
                 ws_theme="custom" if a.words else a.theme, ws_words=a.words[:300],
                 name_text=a.text[:40], name_bg=a.background,
                 pages=max(2, min(40, a.booklet or 10)), mix=a.mix, ramp=not a.same_difficulty, cover=not a.no_cover,
                 page_nums=not a.no_page_numbers, key=not a.no_answers, fold=a.fold,
                 poster=bool(a.poster), grid=a.poster or "2x2", overlap=a.overlap,
                 mode="convert" if a.pattern == "photo" else "make", style=a.style, brightness=a.brightness,
                 contrast=a.contrast, threshold=a.threshold, dot=a.dot, fit="cover" if a.fill else "contain",
                 invert=a.invert, pnono_size=a.squares, pnono_answer=a.solved,
                 pcbn_colours=max(4, min(16, a.crayons)), cbn=bool(a.cbn), cbn_colours=max(3, min(12, a.cbn or 6)))
    from . import output   # imported here so --help works without starting Qt
    if a.pattern == "testpage":
        import os
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
        version = open(version_file).read().strip() if os.path.exists(version_file) else ""
        output.write_test_page(a.out, s, version)
        print(f"wrote {a.out}: print it at 100% (actual size) to check your printer")
        return
    pic = None
    if a.pattern == "photo":
        if not a.image:
            ap.error("photo needs --image PICTURE")
        if a.booklet or a.answers:
            ap.error("photo can't make booklets or answer pages (photo books come later)")
        pic = photo.load_photo(a.image)
        pic.rot, pic.zoom = a.rotate, max(100, min(400, a.zoom))
    if a.poster:
        if a.booklet or a.answers:
            ap.error("--poster can't be combined with --booklet or --answers")
        if a.out.lower().endswith(".pdf"):
            n = output.write_poster_pdf(a.out, s, single_page(s, pic))
            print(f"wrote {a.out}: {n} sheets (seed {s.seed})")
        elif a.out.lower().endswith(".svg"):
            output.write_svg(a.out, s, single_page(s, pic))
            print(f"wrote {a.out}: the whole poster (seed {s.seed})")
        else:
            ap.error("--poster needs a .pdf (the sheets) or .svg (the whole poster) output")
        print(poster.size_note(s))
        return
    if a.booklet:
        if not a.out.lower().endswith(".pdf"):
            ap.error("--booklet needs a .pdf output")
        n = output.write_book_pdf(a.out, s)
        print(f"wrote {a.out}: {n} {'printed sides' if s.fold else 'pages'} (seed {s.seed})")
        if s.fold:
            print("Print double-sided, flipping on the short edge, then stack, fold and staple.")
        return
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
        output.write(a.out, s, single_page(s, pic))
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
