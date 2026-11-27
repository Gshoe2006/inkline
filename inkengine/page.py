"""Paper, settings and page layout, ported from index.html (geometry, designBox, drawBands, drawPage).

A page is described by a PageSpec and drawn on any Canvas by draw_page(), so the preview, PNG, PDF,
SVG and printing all lay a page out the same way.
"""

import math
import re
from dataclasses import dataclass, field, fields, replace

from .box import Box
from .patterns import GENERATORS, HAS_ANSWER, NAMES
from .patterns import maze
from .rng import mulberry32
from .i18n import tr

PAPER = {"letter": (8.5, 11.0), "a4": (8.27, 11.69)}
CREAM = "#fbf3df"   # Paper → Cream paper: easier on some readers' eyes on a screen; never sent to the printer


def js_round(x):
    return int(math.floor(x + 0.5))


def _coerce(v, kind):
    try:
        if kind is bool:
            return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
        if kind is int:
            return int(float(v))
        if kind is float:
            f = float(v)
            return f if math.isfinite(f) else None
        return v if isinstance(v, str) else str(v) if isinstance(v, (int, float)) else None
    except (TypeError, ValueError, OverflowError):
        return None


# What each setting may be, for settings read from a file (remembered settings, presets, projects): a number
# outside its range is brought into it; text that isn't one of its choices, or is too long, falls back.
RANGES = {"seed": (0, 4294967295), "complexity": (1, 10), "weight": (1, 10), "margin": (0, 2), "dpi": (36, 1200),
          "pages": (2, 40), "overlap": (0, 1), "brightness": (-100, 100), "contrast": (20, 300), "threshold": (1, 254),
          "dot": (1, 8), "pnono_size": (10, 30), "pcbn_colours": (4, 16), "cbn_colours": (3, 12),
          "cal_month": (0, 12), "cal_year": (0, 2100), "pdots_n": (20, 150)}
LENGTHS = {"title": 80, "pack_words": 600, "pack_days": 200, "reward_text": 60, "bingo_words": 600, "crypto_text": 120, "speed_tables": 40, "draw_text": 600, "memory_words": 600, "maze_word": 12, "ws_words": 300, "name_text": 40, "trace_text": 300, "cross_words": 2000, "panel_gens": 200}


def _choices():
    from . import pack, poster
    from .patterns import (bingo, clock, coords, drawread, early, crossword, cryptogram, fractions, ladder, maths, memory, money, planner,
                           reward, ruled, name, scramble, speed, spot, trace, words)
    try:
        from .photo import STYLES
    except ImportError:      # the engine without Qt: no photo styles to check against
        STYLES = None
    return {"gen": set(NAMES), "paper": set(PAPER), "orient": {"portrait", "landscape"}, "maze_shape": set(maze.SHAPE_NAMES),
            "spot_base": set(spot.BASES), "ws_theme": set(words.THEME_NAMES) | {"custom"}, "name_bg": set(name.BACKGROUNDS),
            "age": {"any", "4-6", "7-9", "10+"}, "sheet": set(SHEETS), "maths_kind": set(maths.KINDS), "clock_task": set(clock.TASKS), "frac_kind": set(fractions.KINDS), "ruled_kind": set(ruled.KINDS), "reward_kind": set(reward.KINDS), "bingo_kind": set(bingo.KINDS), "early_kind": set(early.KINDS), "bingo_theme": set(words.THEME_NAMES) | {"custom"}, "money": set(money.CURRENCIES), "pack_theme": set(pack.THEME_NAMES), "trace_source": set(trace.SOURCES), "trace_style": set(trace.LETTERS), "trace_hand": set(trace.HANDS), "cross_theme": set(crossword.THEME_NAMES),
            "crypto_code": set(cryptogram.KINDS), "crypto_source": set(cryptogram.SOURCES), "ladder_kind": set(ladder.KINDS),
            "cal_kind": set(planner.KINDS), "cal_art": set(planner.BACKGROUNDS), "cal_start": set(planner.WEEK_STARTS),
            "scramble_kind": set(scramble.KINDS), "speed_count": set(dict(speed.COUNTS)), "speed_order": set(speed.ORDERS),
            "speed_op": set(speed.OPS), "draw_source": set(drawread.SOURCES), "coord_kind": set(coords.KINDS),
            "memory_kind": set(memory.KINDS),
            "grid": set(poster.GRIDS), "mode": {"make", "convert"}, "fit": {"contain", "cover"},
            **({"style": set(STYLES)} if STYLES else {})}


def _allowed(k, v, choices):
    """v brought into what setting k allows, or None for its default."""
    if k in RANGES:
        lo, hi = RANGES[k]
        return type(v)(max(lo, min(hi, v)))
    if k in LENGTHS:
        return v[:LENGTHS[k]]
    if k in choices and v not in choices[k]:
        return None
    return v


@dataclass
class Settings:
    """The options a page is drawn with. Defaults match index.html's controls, except gen: the engine
    defaults to maze, while the window opens on mandala as 2.x did (inkapp.state)."""
    gen: str = "maze"
    seed: int = 20261117
    complexity: int = 5          # 1..10
    age: str = "any"             # ages.AGES: a starting point for complexity and options (any, 4-6, 7-9, 10+)
    weight: int = 4              # line weight 1..10
    frame: bool = False          # border around the design
    title: str = ""
    name_line: bool = False
    paper: str = "letter"        # letter | a4
    orient: str = "portrait"     # portrait | landscape
    margin: float = 0.5          # inches
    dpi: int = 300
    maze_shape: str = "rect"
    spot_base: str = "mandala"   # spot the difference: the picture drawn twice
    maze_word: str = "Maze"
    ws_theme: str = "animals"    # word search: a theme from patterns.words.THEMES, or "custom"
    ws_words: str = ""           # word search: your own words, for ws_theme "custom"
    name_text: str = "Hello"     # name page: the name or word (up to 40 characters)
    name_bg: str = "none"        # name page: none | flow | contour | truchet underneath
    maths_kind: str = "add"      # maths drill: patterns.maths.KINDS (add, sub, addsub, times, bonds, mixed)
    pack_theme: str = "animals"  # worksheet pack (pack.py): a theme from pack.THEME_NAMES, or "spelling"
    pack_words: str = ""         # worksheet pack: this week's spelling words, for pack_theme "spelling"
    easy_read: bool = False      # Page text → Easier to read: Atkinson Hyperlegible, letters and words spaced wider
    cream: bool = False          # Paper → Cream paper for screens and PDFs (Print always sends white)
    pack_days: str = ""          # worksheet pack: the five days' sheets ("maths,trace,..."), or "" for the usual ones
    money: str = "auto"          # maths drill money sums: patterns.money.CURRENCIES (auto, GBP, EUR, USD)
    ruled_kind: str = "squared"  # graph and lined paper: patterns.ruled.KINDS
    reward_kind: str = "chart"   # rewards: patterns.reward.KINDS (sticker chart, certificate)
    reward_text: str = ""        # rewards: what it's for ("reading every day")
    bingo_kind: str = "numbers"  # bingo: patterns.bingo.KINDS (numbers, words, sums)
    early_kind: str = "tenframe" # early maths: patterns.early.KINDS (ten frames, bonds, place value, counting)
    bingo_theme: str = "animals" # bingo words: a word search theme (patterns.words.THEME_NAMES), or "custom"
    bingo_words: str = ""        # bingo words: your own list, for bingo_theme "custom"
    crypto_code: str = "numbers" # cryptogram: patterns.cryptogram.KINDS (numbers, symbols)
    crypto_source: str = "sayings"   # cryptogram: a saying, or "custom" for crypto_text
    crypto_text: str = ""        # cryptogram: your own text to put in code
    ladder_kind: str = "plain"   # word ladder: patterns.ladder.KINDS (plain, or the letter that changes marked)
    cal_kind: str = "month"      # calendar: patterns.planner.KINDS (month, week)
    cal_month: int = 0           # calendar: 1-12, or 0 for next month
    cal_year: int = 0            # calendar: the year, or 0 for the next time cal_month comes round
    cal_start: str = "auto"      # calendar: the first day of the week (auto, mon, sun)
    cal_art: str = "mandala"     # calendar: the picture above it (patterns.planner.BACKGROUNDS)
    scramble_kind: str = "mixed" # unscramble: patterns.scramble.KINDS (mixed-up letters, or missing letters)
    speed_count: int = 50        # times-table speed test: how many facts (patterns.speed.COUNTS: 25, 50, 100)
    speed_tables: str = ""       # times-table speed test: the tables ("3, 4, 8"), or "" for Complexity's
    speed_order: str = "mixed"   # times-table speed test: patterns.speed.ORDERS (mixed, order)
    speed_op: str = "times"      # times-table speed test: patterns.speed.OPS (times, divide, both)
    speed_chart: bool = False    # times-table speed test: a progress chart to fill in
    draw_source: str = "sentences"   # draw what you read: patterns.drawread.SOURCES (Inkline's, or "custom")
    draw_text: str = ""          # draw what you read: your own sentences, separated by ;
    coord_kind: str = "plot"     # coordinate grid: patterns.coords.KINDS (plot the points, battleships)
    memory_kind: str = "pictures"    # memory cards: patterns.memory.KINDS (pictures, words, dots, custom)
    memory_words: str = ""       # memory cards: your own pairs ("cat: chat; dog: chien")
    memory_backs: bool = False   # memory cards: a page of card backs after the cards, for double-sided printing
    frac_kind: str = "fractions" # fractions and number lines: patterns.fractions.KINDS
    clock_task: str = "read"     # telling the time: patterns.clock.TASKS (read, draw, mixed)
    trace_style: str = "print"   # handwriting: patterns.trace.LETTERS (print, or joined-up in the language's school style)
    trace_hand: str = "auto"     # joined-up handwriting: patterns.trace.HANDS (auto: the language's school style)
    trace_source: str = "upper"  # handwriting: patterns.trace.SOURCES (upper, lower, numbers, words, name)
    trace_text: str = ""         # handwriting: your own words, for trace_source "words"
    cross_theme: str = "animals" # crossword: a theme from patterns.crossword.THEMES, or "custom"
    cross_words: str = ""        # crossword: your own "word: clue" lines, for cross_theme "custom"
    sheet: str = "one"           # several designs on one sheet: SHEETS (one, halves, sides, quarters, banner)
    panel_gens: str = "words,maze,dots"   # the other designs on the sheet, in order (the first is gen)
    # booklets (book.py)
    booklet: bool = False        # several pages: cover, designs, answers
    pages: int = 10              # design pages, 2..40
    ramp: bool = True            # difficulty rises page by page
    mix: bool = False            # every pattern in turn, instead of only gen
    cover: bool = True
    page_nums: bool = True
    key: bool = True             # answer pages for the puzzles
    fold: bool = False           # print as a fold-and-staple book: two half-size pages per side
    page_seeds: dict = field(default_factory=dict)   # pages swapped for a new design: {index or "cover": seed}
    # a booklet built page by page: each a dict of PAGE_KEYS; empty means generate it from pages/ramp/mix
    page_list: list = field(default_factory=list)
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
    pdots_n: int = 60            # photo dot-to-dot: how many dots, 20..150
    pdots_answer: bool = False   # draw the photo dot-to-dot joined up
    pcbn_colours: int = 8        # colour by number crayons, 4..16
    cbn: bool = False            # mandalas, woven tiles, contours and name pages as colour by number
    cbn_colours: int = 6         # their crayons, 3..12
    cbn_maths: bool = False      # colour by maths: a sum in each space instead of its number
    # photo books (book.py)
    photobook: bool = False      # several photos, a page each
    testpage: bool = False       # show the printer test page instead
    pcover: bool = True          # a cover page with the title, page count and first photo
    ppage_nums: bool = True

    @classmethod
    def from_dict(cls, d):
        """Settings from a dict. 2.x names (mazeShape, nameLine) are read as maze_shape, name_line;
        keys this version doesn't know are ignored."""
        types = {f.name: type(f.default) for f in fields(cls) if not isinstance(f.default, type(field()))}
        choices = _choices()
        out = {}
        for k, v in d.items():
            k = re.sub(r"(?<!^)([A-Z])", r"_\1", k).lower()
            if k == "page_seeds" and isinstance(v, dict):
                out[k] = {pk: s for pk, s in ((pk, _coerce(s, int)) for pk, s in v.items())
                          if s is not None and (pk == "cover" or str(pk).isdigit())}
            elif k == "page_list" and isinstance(v, list):
                out[k] = [clean_page(p, types, choices) for p in v[:40] if isinstance(p, dict)]
            elif k in types:
                v = _coerce(v, types[k])   # 2.x's form stores everything as text: "5", "0.25", "true"
                out[k] = None if v is None else _allowed(k, v, choices)
        return cls(**{k: v for k, v in out.items() if v is not None})

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in fields(self)}


# What each page of a booklet built page by page keeps for itself; the rest is the booklet's.
PAGE_KEYS = ("gen", "seed", "complexity", "cbn", "cbn_colours", "cbn_maths", "maze_shape", "maze_word", "ws_theme", "ws_words",
             "name_text", "name_bg", "spot_base", "maths_kind", "money", "frac_kind", "ruled_kind", "reward_kind", "reward_text", "bingo_kind", "bingo_theme", "bingo_words", "early_kind", "crypto_code", "crypto_source", "crypto_text", "ladder_kind",
             "cal_kind", "cal_month", "cal_year", "cal_start", "cal_art", "scramble_kind", "speed_count", "speed_tables",
             "speed_order", "speed_op", "speed_chart", "draw_source", "draw_text", "coord_kind", "memory_kind", "memory_words", "clock_task", "trace_source", "trace_style", "trace_hand", "trace_text",
             "cross_theme", "cross_words")


# Page-only keys: not settings of their own (nothing at the top level mirrors them). "answer": False leaves
# that page's solution off the answer pages.
PAGE_ONLY = ("answer",)


def has_answer(gen, s):
    """Whether a design of this pattern, drawn with these settings, has a solution for the answer pages."""
    from .cbn import is_cbn_design
    if gen == "coords" and getattr(s, "coord_kind", "plot") == "battle":   # Battleships: a game, nothing to solve
        return False
    return gen in HAS_ANSWER or is_cbn_design(gen, s)


def clean_page(p, types=None, choices=None):
    """A page_list entry with only PAGE_KEYS (and PAGE_ONLY), each of the right type and allowed (as read
    from a file)."""
    if types is None:
        types = {f.name: type(f.default) for f in fields(Settings) if not isinstance(f.default, type(field()))}
    choices = _choices() if choices is None else choices
    out = {}
    for k in PAGE_KEYS:
        if k in p:
            v = _coerce(p[k], types[k])
            v = None if v is None else _allowed(k, v, choices)
            if v is not None:
                out[k] = v
    if "answer" in p:   # only a clear yes or no: anything else is dropped (the answer stays on)
        v = p["answer"]
        v = v if isinstance(v, bool) else {"true": True, "false": False}.get(str(v).strip().lower())
        if v is not None:
            out["answer"] = v
    return out


def page_settings(s, spec):
    """The settings a design page is drawn with: the booklet's, with the page's own on top."""
    return replace(s, **spec.opts) if getattr(spec, "opts", None) else s


@dataclass
class Geometry:
    w: float          # paper size in inches
    h: float
    dpi: int
    W: int            # paper size in pixels
    H: int
    box: Box          # inside the margins
    scale: float = 1.0


def geometry(s, dpi=None):
    """The page at the settings' dpi, or at another (the preview draws at screen resolution)."""
    dpi = s.dpi if dpi is None else dpi
    w, h = PAPER[s.paper]
    if s.orient == "landscape":
        w, h = h, w
    m = s.margin * dpi
    W, H = js_round(w * dpi), js_round(h * dpi)
    return Geometry(w, h, dpi, W, H, Box(m, m, W - 2 * m, H - 2 * m))


@dataclass
class PageSpec:
    kind: str = "design"         # design | answers | cover | blank | photo | pcover | backs (memory cards)
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
    opts: dict = field(default_factory=dict)      # design: this page's own settings (a booklet built page by page)
    key_label: str = ""          # design: what its answer is called on the answer pages, instead of label · page
    stamp: str = ""              # design: a small note in the bottom margin ("Copy 7"), leaving the design as it is
    filled_name: str = ""        # written on the "Name ____" line (a class set with a name on each copy)
    panel_box: object = None     # one of several designs on a sheet: its place on the page (a Box)

    def __post_init__(self):
        if self.header is None:
            self.header = self.kind == "answers" or (self.kind in ("design", "photo") and bool(self.title or self.name))


def single_page(s, photo=None):
    """The page the settings describe: a design, or with s.mode "convert" the photo."""
    if s.mode == "convert":
        return PageSpec(kind="photo", photo=photo, title=s.title.strip(), name=s.name_line)
    return PageSpec(kind="design", gen=s.gen, seed=s.seed, c=s.complexity, title=s.title.strip(), name=s.name_line)


SHEETS = {"one": "One design", "halves": "Two, one above the other", "sides": "Two, side by side",
          "quarters": "Four", "banner": "One wide, two below"}
PANELS = {"one": 1, "halves": 2, "sides": 2, "quarters": 4, "banner": 3}


def sheet_gens(s):
    """The patterns on the sheet, in order: the Design section's, then panel_gens (unknown ones skipped,
    missing ones taken from the defaults)."""
    n = PANELS.get(s.sheet, 1)
    rest = [x.strip() for x in (s.panel_gens or "").split(",") if x.strip() in GENERATORS]
    defaults = ["words", "maze", "dots"]
    while len(rest) < 3:
        rest.append(defaults[len(rest)])
    return ([s.gen] + rest)[:n]


def sheet_boxes(box, sheet, gap):
    """Each design's place on a sheet laid out as sheet."""
    x, y, w, h = box
    if sheet == "halves":
        hh = (h - gap) / 2
        return [Box(x, y, w, hh), Box(x, y + hh + gap, w, hh)]
    if sheet == "sides":
        ww = (w - gap) / 2
        return [Box(x, y, ww, h), Box(x + ww + gap, y, ww, h)]
    if sheet == "quarters":
        ww, hh = (w - gap) / 2, (h - gap) / 2
        return [Box(x + i * (ww + gap), y + j * (hh + gap), ww, hh) for j in range(2) for i in range(2)]
    if sheet == "banner":
        top = (h - gap) * 0.45
        ww = (w - gap) / 2
        low = y + top + gap
        return [Box(x, y, w, top), Box(x, low, ww, h - top - gap), Box(x + ww + gap, low, ww, h - top - gap)]
    return [box]


def panel_specs(g, spec, s):
    """A design page with several designs on it: one PageSpec for each, with its own pattern, its own seed (the
    first keeps the page's, so one design alone looks as before) and its place on the page. [] for one design."""
    if spec.kind != "design" or spec.idx >= 0 or s.poster or PANELS.get(s.sheet, 1) < 2:
        return []   # (a single page only: not a booklet's pages, nor a poster)
    box = design_box(g, spec, s)
    out = []
    for k, (gen, b) in enumerate(zip(sheet_gens(s), sheet_boxes(box, s.sheet, g.dpi * 0.3))):
        out.append(replace(spec, gen=gen, seed=(spec.seed + k * 7919) & 0xFFFFFFFF, header=False, page_no=0,
                           title="", name=False, stamp="", panel_box=b, label=tr(NAMES[gen]),
                           key_label=f"{spec.key_label} · {tr(NAMES[gen])}" if spec.key_label else ""))
    return out


def item_box(g, d, s):
    """Where a puzzle was drawn on its page: its place on a sheet of several, else the page's design box."""
    return d.panel_box if d.panel_box is not None else design_box(g, d, s)


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
            lx, label = b.x + b.w * 0.6, tr("Name")
            ctx.fill_text(label, lx, y)
            ctx.line_width = g.dpi / 150
            ctx.begin_path()
            ctx.move_to(lx + ctx.measure_text(label) + fs * 0.3, y + 2)
            ctx.line_to(b.x + b.w, y + 2)
            ctx.stroke()
            if spec.filled_name:   # written on the line, as if by hand: a smaller size to fit, then narrower
                nx = lx + ctx.measure_text(label) + fs * 0.6
                room = max(1, b.x + b.w - nx)
                size = fs * 0.85
                ctx.set_font(size, 600)
                wide = ctx.measure_text(spec.filled_name)
                if wide > room:
                    ctx.set_font(max(fs * 0.45, size * room / wide), 600)
                ctx.fill_text(spec.filled_name, nx, y - fs * 0.05, room)
        if spec.label:
            ctx.set_font(fs * 0.6, 400)
            ctx.fill_style = "#555"
            ctx.fill_text(spec.label, b.x, y + fs * 0.85)
    if spec.page_no:
        ctx.set_font(fs * 0.6, 400)
        ctx.fill_style, ctx.text_align = "#333", "center"
        ctx.fill_text(str(spec.page_no), b.x + b.w / 2, b.y + b.h - fs * 0.1)
    if spec.stamp:   # under the design, in the margin (a quarter inch at least), so the design keeps its size
        ctx.set_font(g.dpi * 0.09, 400)
        ctx.fill_style, ctx.text_align = "#333", "right"
        ctx.fill_text(spec.stamp, b.x + b.w, b.y + b.h + g.dpi * 0.12)
    ctx.restore()


def draw_design(ctx, g, box, gen, seed, c, s, lw, **opts):
    if gen not in GENERATORS:
        raise ValueError(f"{gen!r} isn't ported to the Python engine yet (have: {', '.join(GENERATORS)})")
    return GENERATORS[gen](ctx, box, mulberry32(seed), c, s, lw=lw, seed=seed, dpi=g.dpi, **opts)


def draw_page(ctx, g, spec, s, keep=False):
    """Draw one page on a white sheet. Returns what the generator reports (e.g. a maze's grid).
    keep=True draws onto what's there (a poster sheet's window onto the whole poster)."""
    ctx.easy_read = bool(getattr(s, "easy_read", False))
    if not keep:   # white paper, or cream for screens and PDFs (Print sends white: jobs.for_printer)
        ctx.fill_style = CREAM if getattr(s, "cream", False) else "#fff"
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
        ctx.fill_text((tr("1 page to colour") if spec.count == 1 else tr("{n} pages to colour")).format(n=spec.count),
                      b.x + b.w / 2, b.y + b.h * 0.12 + fs * 0.8, b.w)
        ctx.restore()
        return convert(ctx, Box(b.x + b.w * 0.08, b.y + b.h * 0.24, b.w * 0.84, b.h * 0.7), g.dpi, s, spec.photo)
    if spec.kind == "photo":   # photos skip the pattern frame, but take the title, name line and page number
        from .photo import convert
        view = getattr(g, "view", None)
        if spec.header or spec.page_no:
            draw_bands(ctx, g, spec)
            return convert(ctx, design_box(g, spec, s, frame=False), g.dpi, s, spec.photo, view=view)
        return convert(ctx, g.box, g.dpi, s, spec.photo, view=view)
    if spec.kind == "backs":   # memory cards' backs: where the front's grid falls once the sheet flips on its long edge
        s = page_settings(s, spec)
        front = design_box(g, replace(spec, kind="design", header=spec.header), s)
        landscape = g.W > g.H
        box = (Box(front.x, g.H - front.y - front.h, front.w, front.h) if landscape else
               Box(g.W - front.x - front.w, front.y, front.w, front.h))
        return draw_design(ctx, g, box, spec.gen, spec.seed, spec.c, s, lw, backs=True, flip="rows" if landscape else "cols")
    draw_bands(ctx, g, spec)
    if spec.kind == "design":
        s = page_settings(s, spec)   # a page built page by page draws with its own pattern settings
        box = design_box(g, spec, s)
        if s.frame:
            ctx.line_width = lw * 1.6
            ctx.stroke_rect(*box.inset(-lw * 6))
            ctx.line_width = lw
        from . import cbn
        panels = panel_specs(g, spec, s)
        if panels:   # several designs on the sheet, a light line between them
            ctx.save()
            ctx.stroke_style, ctx.line_width = "#bbb", max(1.0, lw * 0.4)
            for a, b in zip(panels, panels[1:]):
                pa, pb = a.panel_box, b.panel_box
                ctx.begin_path()
                if abs(pa.y - pb.y) < 1:   # side by side: a line down between them
                    x = (pa.x + pa.w + pb.x) / 2
                    ctx.move_to(x, pb.y)
                    ctx.line_to(x, pb.y + pb.h)
                else:                      # one above the other: a line across
                    y = (pa.y + pa.h + pb.y) / 2
                    ctx.move_to(box.x, y)
                    ctx.line_to(box.x + box.w, y)
                ctx.stroke()
            ctx.restore()
            out = []
            for p in panels:
                ctx.save()
                ctx.stroke_style = ctx.fill_style = "#000"
                ctx.line_width = lw
                if cbn.is_cbn_design(p.gen, s):
                    out.append(cbn.draw_design_page(ctx, g, p.panel_box, p, s, lw))
                else:
                    out.append(draw_design(ctx, g, p.panel_box, p.gen, p.seed, p.c, s, lw, filled_name=spec.filled_name))
                ctx.restore()
            return {"panels": out}
        if cbn.is_cbn_design(spec.gen, s):   # colour by number: the crayon key takes a band under the design
            return cbn.draw_design_page(ctx, g, box, spec, s, lw)
        return draw_design(ctx, g, box, spec.gen, spec.seed, spec.c, s, lw, filled_name=spec.filled_name)
    if spec.kind == "answers":
        area = design_box(g, spec, s)
        gap, fs = g.dpi * 0.3, g.dpi * 0.14
        cw, ch = (area.w - gap) / 2, (area.h - gap) / 2
        for k, d in enumerate(spec.items):
            sd = page_settings(s, d)   # each puzzle with its own page's settings
            cell = Box(area.x + (k % 2) * (cw + gap), area.y + (k // 2) * (ch + gap), cw, ch)
            ctx.save()
            ctx.set_font(fs, 600)
            ctx.fill_style, ctx.text_align = "#000", "left"
            name = d.key_label or (tr("{label} · page {n}").format(label=d.label, n=d.page_no) if d.page_no else d.label)
            ctx.fill_text(name, cell.x, cell.y + fs)
            ctx.restore()
            ctx.line_width = max(1, lw * 0.45)
            slot = Box(cell.x, cell.y + fs * 1.6, cell.w, cell.h - fs * 1.6).inset(fs * 0.6)
            from . import cbn
            if cbn.is_cbn_design(d.gen, sd):   # shaded by number
                cbn.draw_answer(ctx, g, slot, d, sd, lw)
            elif d.gen == "maze":   # same grid as the puzzle page, so it's the same maze
                grid = maze.grid_size(item_box(g, d, sd), d.c, sd.maze_shape, sd.maze_word)
                draw_design(ctx, g, slot, "maze", d.seed, d.c, sd, ctx.line_width, grid=grid, solve=True)
            elif d.gen == "spot":   # the puzzle page's own picture and changes, scaled into the slot
                src = item_box(g, d, sd)
                k = min(slot.w / src.w, slot.h / src.h)
                ctx.save()
                ctx.translate(slot.x + (slot.w - src.w * k) / 2 - src.x * k, slot.y + (slot.h - src.h * k) / 2 - src.y * k)
                ctx.transform(k, 0, 0, k, 0, 0)
                draw_design(ctx, g, src, "spot", d.seed, d.c, sd, lw, solve=True, line=ctx.line_width / k)
                ctx.restore()
            elif d.gen == "dots":   # same seed draws the same shape, finished
                draw_design(ctx, g, slot, "dots", d.seed, d.c, sd, ctx.line_width, connect=True)
            elif d.gen in HAS_ANSWER:
                draw_design(ctx, g, slot, d.gen, d.seed, d.c, sd, lw, solve=True)
        return None
    if spec.kind == "cover":
        b, fs = g.box, g.dpi * 0.5
        ctx.save()
        ctx.set_font(fs, 700)
        ctx.text_align, ctx.fill_style = "center", "#000"
        ctx.fill_text(spec.title, b.x + b.w / 2, b.y + b.h * 0.14, b.w)
        kinds = list(dict.fromkeys(d.gen for d in spec.designs))
        n = len(spec.designs)
        if len(kinds) == 1:
            sub = (tr("{n} {pattern} pages") if n > 1 else tr("1 {pattern} page")).format(n=n, pattern=tr(NAMES[kinds[0]]).lower())
        else:
            sub = (tr("{n} pages") if n > 1 else tr("1 page")).format(n=n)
        sub += " · " + tr("easy to hard") if s.ramp and n > 1 else ""
        ctx.set_font(fs * 0.4, 400)
        ctx.fill_style = "#444"
        ctx.fill_text(sub, b.x + b.w / 2, b.y + b.h * 0.14 + fs * 0.8, b.w)
        if spec.filled_name:   # a class set's booklet: whose it is, between the title and the picture
            ctx.set_font(fs * 0.6, 700)
            ctx.fill_style = "#000"
            ctx.fill_text(spec.filled_name, b.x + b.w / 2, b.y + b.h * 0.14 + fs * 1.75, b.w)
        ctx.restore()
        art = Box(b.x + b.w * 0.12, b.y + b.h * 0.26, b.w * 0.76, b.h * 0.66)
        ctx.line_width = lw
        first = spec.designs[0].gen
        # a puzzle would give away a page's answer (and handwriting or a calendar is no picture), so their books get a
        # mandala
        draw_design(ctx, g, art, "mandala" if first in HAS_ANSWER or first in NO_COVER_ART else first,
                    spec.art_seed, 6, s, lw)
        return None
    if spec.kind == "blank":   # padding in a fold-and-staple book
        return None
    raise ValueError(f"unknown page kind {spec.kind!r}")


# patterns whose page is no picture for a cover (worksheets with nothing to solve): their books get a mandala
NO_COVER_ART = ("trace", "calendar", "lscwc", "drawread", "memory")


def backs_page(spec):
    """The page of card backs for a page of memory cards: printed on the other side of the sheet."""
    return replace(spec, kind="backs", stamp="", page_no=0)


def answer_page(specs, title=None):
    """An answer page for up to four puzzle pages."""
    items = [d for d in specs if d.gen in HAS_ANSWER][:4]
    for d in items:
        d.label = d.label or tr(NAMES.get(d.gen, d.gen))
    return PageSpec(kind="answers", title=title or tr("Answers"), items=items)
