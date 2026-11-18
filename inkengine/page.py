"""Paper, settings and page layout, ported from index.html (geometry, designBox, drawBands, drawPage).

A page is described by a PageSpec and drawn on any Canvas by draw_page(), so the preview, PNG, PDF,
SVG and printing all lay a page out the same way.
"""

import math
import re
from dataclasses import dataclass, field, fields

from .box import Box
from .patterns import GENERATORS, HAS_ANSWER, NAMES
from .patterns import maze
from .rng import mulberry32

PAPER = {"letter": (8.5, 11.0), "a4": (8.27, 11.69)}


def js_round(x):
    return int(math.floor(x + 0.5))


@dataclass
class Settings:
    """The options a page is drawn with. Defaults match index.html's controls."""
    gen: str = "maze"
    seed: int = 20261117
    complexity: int = 5          # 1..10
    weight: int = 4              # line weight 1..10
    frame: bool = False          # border around the design
    title: str = ""
    name_line: bool = False
    paper: str = "letter"        # letter | a4
    orient: str = "portrait"     # portrait | landscape
    margin: float = 0.5          # inches
    dpi: int = 300
    maze_shape: str = "rect"
    maze_word: str = "Maze"
    ws_theme: str = "animals"    # word search: a theme from patterns.words.THEMES, or "custom"
    ws_words: str = ""           # word search: your own words, for ws_theme "custom"
    name_text: str = "Hello"     # name page: the name or word (up to 40 characters)
    name_bg: str = "none"        # name page: none | flow | contour | truchet underneath
    # booklets (book.py)
    pages: int = 10              # design pages, 2..40
    ramp: bool = True            # difficulty rises page by page
    mix: bool = False            # every pattern in turn, instead of only gen
    cover: bool = True
    page_nums: bool = True
    key: bool = True             # answer pages for the puzzles
    fold: bool = False           # print as a fold-and-staple book: two half-size pages per side
    page_seeds: dict = field(default_factory=dict)   # pages swapped for a new design: {index or "cover": seed}
    # posters (poster.py)
    poster: bool = False
    grid: str = "2x2"            # sheets across x down: 2x2, 3x3, 4x4, 2x1, 3x2, 1x2, 2x3
    overlap: float = 0.25        # inches shared by neighbouring sheets: 0, 0.25 or 0.5
    # photos (photo.py)
    mode: str = "make"           # make (a pattern) | convert (a photo)
    style: str = "fs"            # see photo.STYLES
    brightness: int = 0          # -100..100
    contrast: int = 110          # 20..300 (%)
    threshold: int = 128         # 1..254 (also "detail" for line drawings)
    dot: int = 2                 # 1..8 work pixels per dot
    fit: str = "contain"         # contain (fit inside) | cover (fill the page)
    invert: bool = False
    pnono_size: int = 15         # photo nonogram squares across, 10..30
    pnono_answer: bool = False   # draw the photo nonogram solved
    pcbn_colours: int = 8        # colour by number crayons, 4..16
    cbn: bool = False            # mandalas, woven tiles, contours and name pages as colour by number
    cbn_colours: int = 6         # their crayons, 3..12
    # photo books (book.py)
    pcover: bool = True          # a cover page with the title, page count and first photo
    ppage_nums: bool = True

    @classmethod
    def from_dict(cls, d):
        """Settings from a dict. 2.x names (mazeShape, nameLine) are read as maze_shape, name_line;
        keys this version doesn't know are ignored."""
        names = {f.name for f in fields(cls)}
        snake = {re.sub(r"(?<!^)([A-Z])", r"_\1", k).lower(): v for k, v in d.items()}
        return cls(**{k: v for k, v in snake.items() if k in names})


@dataclass
class Geometry:
    w: float          # paper size in inches
    h: float
    dpi: int
    W: int            # paper size in pixels
    H: int
    box: Box          # inside the margins
    scale: float = 1.0


def geometry(s):
    w, h = PAPER[s.paper]
    if s.orient == "landscape":
        w, h = h, w
    m = s.margin * s.dpi
    W, H = js_round(w * s.dpi), js_round(h * s.dpi)
    return Geometry(w, h, s.dpi, W, H, Box(m, m, W - 2 * m, H - 2 * m))


@dataclass
class PageSpec:
    kind: str = "design"         # design | answers | cover | blank | photo | pcover
    gen: str = "maze"
    seed: int = 0
    c: int = 5
    title: str = ""
    name: bool = False
    page_no: int = 0
    label: str = ""
    items: list = field(default_factory=list)     # answers: the PageSpecs whose solutions this page shows
    header: bool = None          # title band at the top; by default when there's a title or name line
    idx: int = -1                # booklets: which design page this is (0-based)
    designs: list = field(default_factory=list)   # cover: the booklet's design pages
    art_seed: int = 0            # cover: the seed for its picture
    photo: object = None         # photo, pcover: the photo.Photo to convert
    count: int = 0               # pcover: how many photo pages follow

    def __post_init__(self):
        if self.header is None:
            self.header = self.kind == "answers" or (self.kind in ("design", "photo") and bool(self.title or self.name))


def single_page(s, photo=None):
    """The page the settings describe: a design, or with s.mode "convert" the photo."""
    if s.mode == "convert":
        return PageSpec(kind="photo", photo=photo, title=s.title.strip(), name=s.name_line)
    return PageSpec(kind="design", gen=s.gen, seed=s.seed, c=s.complexity, title=s.title.strip(), name=s.name_line)


def line_width(s, g):
    return s.weight * g.dpi / 150 * g.scale


def design_box(g, spec, s, frame=None):
    """Where the design goes once the header and footer bands are taken out."""
    frame = s.frame if frame is None else frame
    band = g.dpi * 0.5 * g.scale
    x, y, w, h = g.box
    if spec.header:
        y, h = y + band, h - band
    if spec.page_no:
        h -= band * 0.6
    b = Box(x, y, w, h)
    return b.inset(s.weight * g.dpi / 150 * 7.6 * g.scale) if frame else b


def draw_bands(ctx, g, spec):
    """Title, "Name ____" line, small label and page number."""
    b, fs = g.box, g.dpi * 0.22 * g.scale
    ctx.save()
    ctx.fill_style, ctx.text_baseline, ctx.text_align = "#000", "alphabetic", "left"
    if spec.header:
        y = b.y + fs
        if spec.title:
            ctx.set_font(fs, 700)
            ctx.fill_text(spec.title, b.x, y, b.w * (0.55 if spec.name else 1))
        if spec.name:
            ctx.set_font(fs * 0.75, 400)
            lx, label = b.x + b.w * 0.6, "Name"
            ctx.fill_text(label, lx, y)
            ctx.line_width = g.dpi / 150
            ctx.begin_path()
            ctx.move_to(lx + ctx.measure_text(label) + fs * 0.3, y + 2)
            ctx.line_to(b.x + b.w, y + 2)
            ctx.stroke()
        if spec.label:
            ctx.set_font(fs * 0.6, 400)
            ctx.fill_style = "#555"
            ctx.fill_text(spec.label, b.x, y + fs * 0.85)
    if spec.page_no:
        ctx.set_font(fs * 0.6, 400)
        ctx.fill_style, ctx.text_align = "#333", "center"
        ctx.fill_text(str(spec.page_no), b.x + b.w / 2, b.y + b.h - fs * 0.1)
    ctx.restore()


def draw_design(ctx, g, box, gen, seed, c, s, lw, **opts):
    if gen not in GENERATORS:
        raise ValueError(f"{gen!r} isn't ported to the Python engine yet (have: {', '.join(GENERATORS)})")
    return GENERATORS[gen](ctx, box, mulberry32(seed), c, s, lw=lw, seed=seed, dpi=g.dpi, **opts)


def draw_page(ctx, g, spec, s, keep=False):
    """Draw one page on a white sheet. Returns what the generator reports (e.g. a maze's grid).
    keep=True draws onto what's there (a poster sheet's window onto the whole poster)."""
    if not keep:
        ctx.fill_style = "#fff"
        ctx.fill_rect(0, 0, g.W, g.H)
    ctx.stroke_style = ctx.fill_style = "#000"
    ctx.line_cap = ctx.line_join = "round"
    lw = line_width(s, g)
    ctx.line_width = lw
    if spec.kind == "pcover":   # a photo book's cover: title, how many pages, and the first photo
        from .photo import convert
        b, fs = g.box, g.dpi * 0.5
        ctx.save()
        ctx.set_font(fs, 700)
        ctx.text_align, ctx.fill_style = "center", "#000"
        ctx.fill_text(spec.title, b.x + b.w / 2, b.y + b.h * 0.12, b.w)
        ctx.set_font(fs * 0.4, 400)
        ctx.fill_style = "#444"
        ctx.fill_text(f"{spec.count} {'page' if spec.count == 1 else 'pages'} to colour", b.x + b.w / 2, b.y + b.h * 0.12 + fs * 0.8, b.w)
        ctx.restore()
        return convert(ctx, Box(b.x + b.w * 0.08, b.y + b.h * 0.24, b.w * 0.84, b.h * 0.7), g.dpi, s, spec.photo)
    if spec.kind == "photo":   # photos skip the pattern frame, but take the title, name line and page number
        from .photo import convert
        view = getattr(g, "view", None)
        if spec.header or spec.page_no:
            draw_bands(ctx, g, spec)
            return convert(ctx, design_box(g, spec, s, frame=False), g.dpi, s, spec.photo, view=view)
        return convert(ctx, g.box, g.dpi, s, spec.photo, view=view)
    draw_bands(ctx, g, spec)
    if spec.kind == "design":
        box = design_box(g, spec, s)
        if s.frame:
            ctx.line_width = lw * 1.6
            ctx.stroke_rect(*box.inset(-lw * 6))
            ctx.line_width = lw
        from . import cbn
        if cbn.is_cbn_design(spec.gen, s):   # colour by number: the crayon key takes a band under the design
            return cbn.draw_design_page(ctx, g, box, spec, s, lw)
        return draw_design(ctx, g, box, spec.gen, spec.seed, spec.c, s, lw)
    if spec.kind == "answers":
        area = design_box(g, spec, s)
        gap, fs = g.dpi * 0.3, g.dpi * 0.14
        cw, ch = (area.w - gap) / 2, (area.h - gap) / 2
        for k, d in enumerate(spec.items):
            cell = Box(area.x + (k % 2) * (cw + gap), area.y + (k // 2) * (ch + gap), cw, ch)
            ctx.save()
            ctx.set_font(fs, 600)
            ctx.fill_style, ctx.text_align = "#000", "left"
            ctx.fill_text(f"{d.label} · page {d.page_no}" if d.page_no else d.label, cell.x, cell.y + fs)
            ctx.restore()
            ctx.line_width = max(1, lw * 0.45)
            slot = Box(cell.x, cell.y + fs * 1.6, cell.w, cell.h - fs * 1.6).inset(fs * 0.6)
            from . import cbn
            if cbn.is_cbn_design(d.gen, s):   # shaded by number
                cbn.draw_answer(ctx, g, slot, d, s, lw)
            elif d.gen == "maze":   # same grid as the puzzle page, so it's the same maze
                grid = maze.grid_size(design_box(g, d, s), d.c, s.maze_shape, s.maze_word)
                draw_design(ctx, g, slot, "maze", d.seed, d.c, s, ctx.line_width, grid=grid, solve=True)
            elif d.gen == "dots":   # same seed draws the same shape, finished
                draw_design(ctx, g, slot, "dots", d.seed, d.c, s, ctx.line_width, connect=True)
            elif d.gen in HAS_ANSWER:
                draw_design(ctx, g, slot, d.gen, d.seed, d.c, s, lw, solve=True)
        return None
    if spec.kind == "cover":
        b, fs = g.box, g.dpi * 0.5
        ctx.save()
        ctx.set_font(fs, 700)
        ctx.text_align, ctx.fill_style = "center", "#000"
        ctx.fill_text(spec.title, b.x + b.w / 2, b.y + b.h * 0.14, b.w)
        kinds = list(dict.fromkeys(d.gen for d in spec.designs))
        n = len(spec.designs)
        what = (NAMES[kinds[0]].lower() + (" pages" if n > 1 else " page")) if len(kinds) == 1 else "pages"
        sub = f"{n} {what}" + (" · easy to hard" if s.ramp and n > 1 else "")
        ctx.set_font(fs * 0.4, 400)
        ctx.fill_style = "#444"
        ctx.fill_text(sub, b.x + b.w / 2, b.y + b.h * 0.14 + fs * 0.8, b.w)
        ctx.restore()
        art = Box(b.x + b.w * 0.12, b.y + b.h * 0.26, b.w * 0.76, b.h * 0.66)
        ctx.line_width = lw
        first = spec.designs[0].gen
        # a puzzle would give away a page's answer, so puzzle books get a mandala on the cover
        draw_design(ctx, g, art, "mandala" if first in HAS_ANSWER else first, spec.art_seed, 6, s, lw)
        return None
    if spec.kind == "blank":   # padding in a fold-and-staple book
        return None
    raise ValueError(f"unknown page kind {spec.kind!r}")


def answer_page(specs, title="Answers"):
    """An answer page for up to four puzzle pages."""
    items = [d for d in specs if d.gen in HAS_ANSWER][:4]
    for d in items:
        d.label = d.label or NAMES.get(d.gen, d.gen)
    return PageSpec(kind="answers", title=title, items=items)
