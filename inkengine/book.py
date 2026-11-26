"""Booklets: many pages in one PDF, ported from index.html (bookPages, foldOrder, drawFoldSide).

A booklet is a cover, the design pages and answer pages, described as a list of PageSpecs that the
preview, PDF and printing all walk. Difficulty can ramp up page by page, a mixed booklet cycles
through every pattern but name pages, and any one page (or the cover) can be swapped for a new
design without changing the others (Settings.page_seeds). Answer pages show four puzzles each.

Fold-and-staple books print two half-size pages on each side of a landscape sheet, double-sided,
so that stacking the sheets, folding them and stapling the fold puts every page in reading order.
"""

from dataclasses import replace

from .box import Box
from .page import PAGE_ONLY, PAPER, Geometry, PageSpec, draw_page, has_answer, js_round, page_settings
from .patterns import NAMES
from .i18n import tr

# The order a mixed booklet cycles through. Name pages stay out: a booklet shouldn't repeat one word.
GENS = ["mandala", "maze", "truchet", "contour", "flow", "dots", "sudoku", "words", "nonogram"]


def _page_seed(s, key, default):
    seeds = s.page_seeds or {}
    for k in (key, str(key)):     # keys read back from a JSON settings file are strings
        if k in seeds:
            return int(seeds[k]) & 0xFFFFFFFF
    return default


WORKSHEETS = {"maths", "trace", "clock", "scramble", "spelltest", "fractions", "symmetry", "reading"}   # a booklet with these among other kinds is a set of worksheets


def calendar_months(s, n):
    """A month calendar's booklet: [(year, month)] for its n pages, a month each from the one chosen (a twelve-page
    booklet is a year); [] for anything else."""
    if s.gen != "calendar" or getattr(s, "cal_kind", "month") != "month" or not n:
        return []
    from .patterns import planner
    year, month = planner.month_shown(s)
    return [planner.month_after(year, month, i) for i in range(n)]


def _calendar_title(months):
    """The cover of a booklet of months: "January 2027 – December 2027"."""
    from .patterns import planner
    first, last = planner.title(*months[0]), planner.title(*months[-1])
    return first if len(months) == 1 else f"{first} – {last}"


def book_pages(s):
    """Every page of the booklet, in order."""
    n, c, title, mix, ramp = s.pages, s.complexity, s.title.strip(), s.mix, s.ramp
    pages, designs = [], []
    for i, p in enumerate(s.page_list or []):   # built page by page: each page brings its own settings
        gen = p.get("gen", s.gen)
        gen = gen if gen in NAMES else s.gen
        opts = {k: v for k, v in p.items() if k not in ("gen", "seed", "complexity") + PAGE_ONLY}
        designs.append(PageSpec(kind="design", idx=i, gen=gen, seed=int(p.get("seed", s.seed)) & 0xFFFFFFFF,
                                c=max(1, min(10, int(p.get("complexity", c)))), title=title, name=s.name_line,
                                label=f"{tr(NAMES[gen])} {i + 1}", opts=opts))
    months = calendar_months(s, 0 if s.page_list or mix else n)
    for i in range(0 if s.page_list else n):
        gen = GENS[i % len(GENS)] if mix else s.gen
        cx = js_round(1 + (max(c, 2) - 1) * i / (n - 1)) if ramp and n > 1 else c
        # each page's seed comes from the booklet seed, unless that one page was swapped
        seed = _page_seed(s, i, (s.seed + i * 7919) & 0xFFFFFFFF)
        opts = {"cal_month": months[i][1], "cal_year": months[i][0]} if months else {}   # a calendar: the next month
        designs.append(PageSpec(kind="design", idx=i, gen=gen, seed=seed, c=cx, title=title, name=s.name_line,
                                label=f"{tr(NAMES[gen])} {i + 1}", opts=opts))
    if s.cover:
        kinds = {d.gen for d in designs}
        cover_title = title or (_calendar_title(months) if months else
                                tr("Worksheets") if len(kinds) > 1 and kinds & WORKSHEETS else
                                tr("Colouring & puzzle book") if mix or len(kinds) > 1 else
                                tr("{pattern} book").format(pattern=tr(NAMES[designs[0].gen])))
        pages.append(PageSpec(kind="cover", title=cover_title, designs=designs,
                              art_seed=_page_seed(s, "cover", (s.seed ^ 0x5BD1E995) & 0xFFFFFFFF)))
    pages.extend(designs)
    # puzzles, and colour by number (a shaded answer); a page built page by page can leave its answer out
    puzzles = [d for d in designs if has_answer(d.gen, page_settings(s, d))]
    if s.page_list:
        puzzles = [d for d in puzzles if s.page_list[d.idx].get("answer", True) is not False]
    if s.key:
        for i in range(0, len(puzzles), 4):
            pages.append(PageSpec(kind="answers", header=True, title=tr("Answers"), items=puzzles[i:i + 4]))
    no = 1
    for p in pages:
        if p.kind != "cover" and s.page_nums:
            p.page_no = no
            no += 1
    return pages


def photo_book_pages(s, photos):
    """A photo book: an optional cover, then one page per photo, each converted with its own crop."""
    title = s.title.strip()
    pages = [PageSpec(kind="photo", photo=ph, title=title, name=s.name_line) for ph in photos]
    if s.pcover and photos:
        pages.insert(0, PageSpec(kind="pcover", title=title or tr("My colouring book"), photo=photos[0], count=len(photos)))
    no = 1
    for pg in pages:
        if pg.kind != "pcover" and s.ppage_nums:
            pg.page_no = no
            no += 1
    return pages


def page_label(pages, i):
    """What the preview's pager shows, e.g. "Page 3 of 14" or "Page 1 of 14 · cover"."""
    kind = pages[i].kind
    return tr("Page {i} of {n}").format(i=i + 1, n=len(pages)) + (
        " · " + tr("cover") if kind in ("cover", "pcover") else " · " + tr("answers") if kind == "answers" else "")


# --- fold-and-staple ---------------------------------------------------------------------------------

def fold_pages(pages):
    """The pages padded with blanks to a multiple of 4."""
    pages = list(pages)
    while len(pages) % 4:
        pages.append(PageSpec(kind="blank"))
    return pages


def fold_order(n):
    """Which two pages (0-based) each printed side carries, for an n-page book: sheet s front, then its
    back. The outermost sheet holds the first and last pages; the innermost holds the middle spread."""
    sides = []
    for sheet in range(n // 4):
        sides.append((n - 1 - 2 * sheet, 2 * sheet))        # front (outside of the fold)
        sides.append((2 * sheet + 1, n - 2 - 2 * sheet))    # back (inside)
    return sides


def sheet_geometry(s):
    """The landscape sheet a fold-and-staple side is printed on."""
    pw, ph = PAPER[s.paper]
    W, H = js_round(ph * s.dpi), js_round(pw * s.dpi)
    return Geometry(ph, pw, s.dpi, W, H, Box(0, 0, W, H))


def half_geometry(s):
    """One half of a landscape sheet: Letter gives 5.5 x 8.5 in pages, A4 gives A5."""
    pw, ph = PAPER[s.paper]
    dpi, m = s.dpi, s.margin * s.dpi
    sheet_w, H = js_round(ph * dpi), js_round(pw * dpi)
    W = sheet_w // 2
    return Geometry(round(W / dpi, 2), round(H / dpi, 2), dpi, W, H, Box(m, m, W - 2 * m, H - 2 * m))


def draw_fold_side(ctx, s, pages, side):
    """Printed side `side` of the folded book: two half pages on a landscape sheet, and on each sheet's
    outside, dashed fold marks at the top and bottom edge."""
    gs, hg = sheet_geometry(s), half_geometry(s)
    left, right = fold_order(len(pages))[side]
    ctx.fill_style = "#fff"
    ctx.fill_rect(0, 0, gs.W, gs.H)
    for idx, x in ((left, 0), (right, gs.W - hg.W)):
        ctx.save()
        ctx.begin_path()
        ctx.rect(x, 0, hg.W, hg.H)      # a design never spills onto its neighbour
        ctx.clip()
        ctx.translate(x, 0)
        draw_page(ctx, hg, pages[idx], s)
        ctx.restore()
    if side % 2 == 0:
        k, L = gs.dpi / 150, gs.dpi * 0.2
        ctx.save()
        ctx.stroke_style, ctx.line_width, ctx.line_dash = "#999", k, [k * 3, k * 3]
        ctx.line_cap = "butt"
        ctx.begin_path()
        ctx.move_to(gs.W / 2, 0)
        ctx.line_to(gs.W / 2, L)
        ctx.move_to(gs.W / 2, gs.H)
        ctx.line_to(gs.W / 2, gs.H - L)
        ctx.stroke()
        ctx.restore()


def fold_side_label(pages, side):
    left, right = fold_order(len(pages))[side]
    name = lambda i: tr("blank") if pages[i].kind == "blank" else str(i + 1)
    return (tr("Sheet {i} of {n} · back (pages {a} & {b})") if side % 2 else
            tr("Sheet {i} of {n} · front (pages {a} & {b})")).format(i=side // 2 + 1, n=len(pages) // 4, a=name(left), b=name(right))


def swap_page(s, index, seed):
    """Settings with one booklet page (or "cover") given a new design; the other pages stay the same."""
    return replace(s, page_seeds={**(s.page_seeds or {}), index: seed})
