"""Coordinate grids: plot the points to draw a picture, or Battleships for two players.

- Plot the points: a numbered grid and lists of points, (x, y). Joining each list's points in order, with a ruler,
  draws a picture (a house, a star, a cat... from inkengine/pictures.py), picked by the seed. Complexity 1-3 has the
  pictures with fewest points on a 0-10 grid; 4-7 any picture; 8-10 four quadrants, -5 to 5, so some points are
  negative. The answer page draws the picture joined up on the grid; so does the page itself with "Draw the picture
  joined up" (to show a class what the points make, and the gallery's picture of the pattern).
- Battleships: two grids, "My ships" to place your fleet on and "Their ships" to mark your shots, letters across and
  numbers down; 6 x 6 with three ships at 1-3, 8 x 8 with four at 4-7, 10 x 10 with five at 8-10, listed beside or under the
  grids with a box to tick when each is sunk. There's nothing to solve, so no answer page.

Upright pages put the grids one above the other, the fleet beside them. Sideways pages put "Their ships" as tall
as the page and "My ships" smaller beside it, the fleet under that.
"""

from .. import pictures
from ..i18n import tr
from ..rng import pick

KINDS = {"plot": "Plot the points (a picture)", "battle": "Battleships (two grids)"}
INSTRUCTIONS = {"plot": "Plot each point, then join them in order with a ruler. Start again at each new line.",
                "battle": "Place your ships on your grid. Take turns to call a square: mark a hit with ✕ and a miss "
                          "with •."}
GRID_NAMES = {"mine": "My ships", "theirs": "Their ships"}
SHIP_NAMES = {5: "Carrier", 4: "Battleship", 3: "Cruiser", 2: "Destroyer"}


def kind_of(settings):
    k = getattr(settings, "coord_kind", "plot")
    return k if k in KINDS else "plot"


# --- plot the points -------------------------------------------------------------------------------------------------

def plot_range(c):
    """The grid's lowest and highest number at complexity c."""
    return (-5, 5) if c >= 8 else (0, 10)


def make_plot(rnd, c):
    """(picture name, strokes as whole-number points on the page's grid)."""
    pool = sorted(pictures.SIMPLE if c <= 3 else pictures.PICTURES)
    name = pool[pick(rnd, len(pool))]
    lo, _hi = plot_range(c)
    strokes = [[(x + lo, y + lo) for x, y in stroke] for stroke in pictures.PICTURES[name]["strokes"]]
    return name, strokes


def num(v):
    """A number as printed: a real minus sign for negatives."""
    return f"−{-v}" if v < 0 else str(v)


def _point(p):
    return f"({num(p[0])}, {num(p[1])})"


def _wrap_points(ctx, label, pts, width):
    """A list of points as lines of text, wrapped at width: the first headed by its label."""
    lines, line = [], label
    for p in pts:
        bit = _point(p)
        trial = f"{line}  {bit}" if line else bit
        if line and ctx.measure_text(trial) > width:
            lines.append(line)
            line = "      " + bit
        else:
            line = trial
    return lines + [line]


def _grid(ctx, x, y, size, lo, hi, lw, fs):
    """A square coordinate grid from lo to hi on both axes, its axes darker and numbered."""
    n = hi - lo
    cell = size / n
    ctx.save()
    for i in range(n + 1):
        axis = lo + i == 0
        ctx.stroke_style = "#000" if axis else "#999"
        ctx.line_width = max(1.0, lw * (1.0 if axis else 0.4))
        ctx.begin_path()
        ctx.move_to(x + i * cell, y)
        ctx.line_to(x + i * cell, y + size)
        ctx.move_to(x, y + i * cell)
        ctx.line_to(x + size, y + i * cell)
        ctx.stroke()
    ctx.stroke_style = "#000"
    ctx.line_width = max(1.0, lw * 0.9)
    ctx.stroke_rect(x, y, size, size)
    ctx.fill_style = "#000"
    ctx.set_font(fs, 500)
    # the numbers along the bottom and down the left, outside the grid (clear of its lines, in every quadrant)
    for i in range(n + 1):
        v = num(lo + i)
        if lo == 0 and i == 0:   # one 0, at the corner where the axes meet
            ctx.text_align, ctx.text_baseline = "right", "top"
            ctx.fill_text(v, x - fs * 0.2, y + size + fs * 0.55)
            continue
        ctx.text_align, ctx.text_baseline = "center", "top"
        ctx.fill_text(v, x + i * cell, y + size + fs * 0.55)   # (low enough to clear the lowest number up the side)
        ctx.text_align, ctx.text_baseline = "right", "middle"
        ctx.fill_text(v, x - fs * 0.3, y + size - i * cell)
    ctx.restore()
    return cell


def _plot(ctx, box, rnd, c, lw, dpi, solve):
    name, strokes = make_plot(rnd, c)
    lo, hi = plot_range(c)
    landscape = box.w > box.h
    fs = min(dpi * 0.2, box.h / 30)
    gap = fs * 1.5
    text = tr(INSTRUCTIONS["plot"])
    labels = [tr("Line {n}:").format(n=k + 1) for k in range(len(strokes))]

    def lay_text(size_fs, tw):
        """The instructions and the lists of points at size_fs, wrapped at tw: (lines, the lists' lines, height)."""
        ctx.set_font(size_fs, 400)
        head = _wrap_text(ctx, text, tw)
        ctx.set_font(size_fs, 600)
        lists = [_wrap_points(ctx, label, stroke, tw) for label, stroke in zip(labels, strokes)]
        return head, lists, size_fs * (len(head) * 1.5 + 0.6 + sum(len(ls) * 1.5 + 0.5 for ls in lists))

    size_fs = min(fs * 1.25, dpi * 0.24)
    if landscape:   # the grid as tall as the page, the points beside it, as large as fit
        size = min(box.h - fs * 2.2, box.w * 0.58)
        gx, gy = box.x + fs * 2.4, box.y + (box.h - size - fs * 1.6) / 2
        tx, ty, tw, th = gx + size + gap, box.y, box.x + box.w - (gx + size + gap), box.h
        head, lists, height = lay_text(size_fs, tw)
        while height > th and size_fs > dpi * 0.08:
            size_fs *= 0.92
            head, lists, height = lay_text(size_fs, tw)
    else:           # the points under the grid, the grid as big as leaves them room
        tw = box.w
        head, lists, height = lay_text(size_fs, tw)
        while box.h - height - fs * 2.2 < box.h * 0.5 and size_fs > dpi * 0.08:
            size_fs *= 0.92
            head, lists, height = lay_text(size_fs, tw)
        size = min(box.w - fs * 2.6, box.h - height - fs * 2.6)
        room = box.h - size - fs * 2.6   # the grid is as wide as the page: the points take any height left over
        while size_fs < dpi * 0.3:
            bigger = lay_text(size_fs * 1.06, tw)
            if bigger[2] > room:
                break
            size_fs *= 1.06
            head, lists, height = bigger
        gx, gy = box.x + (box.w - size) / 2 + fs * 0.8, box.y
        tx, ty, th = box.x, gy + size + fs * 2.2, box.y + box.h - (gy + size + fs * 2.2)
    lh = size_fs * 1.5
    lines = lists
    ctx.save()
    cell = _grid(ctx, gx, gy, size, lo, hi, lw, fs * 0.8)
    if solve:
        ctx.stroke_style = "#000"
        ctx.line_width = max(1.5, lw * 1.6)
        for stroke in strokes:
            ctx.begin_path()
            for k, (px, py) in enumerate(stroke):
                (ctx.move_to if k == 0 else ctx.line_to)(gx + (px - lo) * cell, gy + size - (py - lo) * cell)
            ctx.stroke()
    ctx.fill_style = "#000"
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    y = ty
    ctx.set_font(size_fs, 400)
    for line in head:
        y += lh
        ctx.fill_text(line, tx, y)
    y += size_fs * 0.6
    ctx.set_font(size_fs, 600)
    for ls in lines:
        for line in ls:
            y += lh
            ctx.fill_text(line, tx, y)
        y += size_fs * 0.5
    ctx.restore()
    return {"kind": "plot", "picture": name, "strokes": strokes, "range": (lo, hi)}


def _wrap_text(ctx, text, width):
    lines, line = [], ""
    for w in text.split():
        trial = f"{line} {w}".strip()
        if line and ctx.measure_text(trial) > width:
            lines.append(line)
            line = w
        else:
            line = trial
    return lines + ([line] if line else [])


# --- battleships -------------------------------------------------------------------------------------------------------

def battle_size(c):
    """(squares across and down, the fleet as ship lengths) at complexity c."""
    if c <= 3:
        return 6, [3, 2, 2]
    if c <= 7:
        return 8, [4, 3, 3, 2]
    return 10, [5, 4, 3, 3, 2]


def _battle_grid(ctx, x, y, size, n, lw, fs, title, label_fs=None):
    """One grid: its title above, letters across the top, numbers down the left (at label_fs, fs unless given), size
    the squares' side."""
    lfs = label_fs or fs
    cell = size / n
    ctx.save()
    ctx.fill_style = "#000"
    ctx.set_font(fs * 1.25, 700)
    ctx.text_align, ctx.text_baseline = "center", "alphabetic"
    ctx.fill_text(title, x + size / 2, y - fs * 1.75)
    ctx.set_font(lfs, 600)
    ctx.text_baseline = "middle"
    letters = "ABCDEFGHIJ"
    for i in range(n):
        ctx.text_align = "center"
        ctx.fill_text(letters[i], x + (i + 0.5) * cell, y - lfs * 0.6)
        ctx.text_align = "right"
        ctx.fill_text(str(i + 1), x - lfs * 0.35, y + (i + 0.5) * cell)
    ctx.line_width = max(1.0, lw * 0.5)
    ctx.stroke_style = "#000"
    for i in range(1, n):
        ctx.begin_path()
        ctx.move_to(x + i * cell, y)
        ctx.line_to(x + i * cell, y + size)
        ctx.move_to(x, y + i * cell)
        ctx.line_to(x + size, y + i * cell)
        ctx.stroke()
    ctx.line_width = max(1.0, lw * 1.2)
    ctx.stroke_rect(x, y, size, size)
    ctx.restore()


def _battle_upright(ctx, box, n, fleet, lw, dpi):
    """An upright page: the two grids one above the other, as big as the page's height allows, and the instructions
    and the fleet in a column beside them, a ship's name over its squares."""
    fs = min(dpi * 0.2, box.h / 32)
    head = fs * 3.6     # a grid's title and letters
    ctx.set_font(fs, 600)   # its numbers, measured in the page's font (wider in some), with room to spare
    side = max(fs * 1.6, ctx.measure_text(str(n)) + fs * 0.6)
    gap = fs * 1.6      # between the grids and the column
    size = min((box.h - 2 * head - fs) / 2, box.w * 0.62 - side)
    gx = box.x + side
    spots = [(gx, box.y + head), (gx, box.y + head + size + fs + head)]
    cx = gx + size + gap
    cw = box.x + box.w - cx
    sunk = tr("Sunk")
    names = [tr(SHIP_NAMES[length]) for length in fleet]
    tfs = fs * 1.15

    def column(tfs):
        """The column's lines at text size tfs, and its height (a ship: its name, then its squares)."""
        ctx.set_font(tfs, 400)
        lines = _wrap_text(ctx, tr(INSTRUCTIONS["battle"]), cw)
        return lines, tfs * (1.4 * len(lines) + 1.0 + 2.9 * len(fleet))

    while True:
        lines, height = column(tfs)
        ctx.set_font(tfs, 600)
        widest = max([ctx.measure_text(nm) for nm in names] + [tfs * (max(fleet) + 1.2) + ctx.measure_text(sunk) + tfs * 1.3])
        if (height <= box.h - head and widest <= cw) or tfs < fs * 0.6:
            break
        tfs *= 0.94
    for (x, y), which in zip(spots, ("mine", "theirs")):
        _battle_grid(ctx, x, y, size, n, lw, fs, tr(GRID_NAMES[which]))
    ctx.save()
    ctx.fill_style = "#000"
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    y = box.y + head
    ctx.set_font(tfs, 400)
    for line in lines:
        y += tfs * 1.4
        ctx.fill_text(line, cx, y)
    y += tfs * 0.6
    cell = tfs
    ctx.line_width = max(1.0, lw * 0.6)
    for length, name in zip(fleet, names):
        y += tfs * 1.4
        ctx.set_font(tfs, 600)
        ctx.fill_text(name, cx, y)
        top = y + tfs * 0.35
        for k in range(length):
            ctx.fill_style = "#ccc"
            ctx.fill_rect(cx + cell * k, top, cell, cell)
            ctx.stroke_rect(cx + cell * k, top, cell, cell)
        ctx.fill_style = "#555"
        ctx.set_font(tfs, 400)
        tx = cx + cell * (length + 0.6)
        ctx.fill_text(sunk, tx, top + cell * 0.85)
        ctx.fill_style = "#000"
        ctx.stroke_rect(tx + ctx.measure_text(sunk) + tfs * 0.3, top, cell, cell)
        y = top + cell + tfs * 0.15
    ctx.restore()
    return {"kind": "battle", "size": n, "fleet": fleet, "grids": [(x, y, size) for x, y in spots]}


def _fleet_column(ctx, fleet, names, sunk, cw, tfs):
    """The instructions and the fleet in a column cw wide at text size tfs: (the instructions' lines, whether each
    ship takes one row - its squares, its name, its sunk box - or two - its name over the rest -, the column's width
    and its height). Measured in the page's font."""
    ctx.set_font(tfs, 400)
    lines = _wrap_text(ctx, tr(INSTRUCTIONS["battle"]), cw)
    text_w = max([ctx.measure_text(line) for line in lines] + [0])
    sunk_w = ctx.measure_text(sunk)
    ctx.set_font(tfs, 600)
    name_w = max(ctx.measure_text(nm) for nm in names)
    row_w = tfs * (max(fleet) + 0.5) + name_w + tfs * 0.8 + sunk_w + tfs * 1.3
    one_row = row_w <= cw
    if one_row:
        width, height = row_w, tfs * 1.6 * len(fleet)
    else:
        width, height = max(name_w, tfs * (max(fleet) + 0.6) + sunk_w + tfs * 1.3), tfs * 2.9 * len(fleet)
    return lines, one_row, max(text_w, width), tfs * (1.4 * len(lines) + 0.9) + height


def _battle(ctx, box, c, lw, dpi):
    """A sideways page: "Their ships", where your shots go, as tall as the page; "My ships" smaller beside it, and the
    instructions and the fleet under that. (Two equal squares side by side are held to half the page's width: a
    sideways page is only about 1.3-1.5 times as wide as it is tall, so they left its bottom third empty.)"""
    n, fleet = battle_size(c)
    if box.w <= box.h:
        return _battle_upright(ctx, box, n, fleet, lw, dpi)
    fs = min(dpi * 0.2, box.h / 32)
    head = fs * 3.6     # a grid's title and letters
    ctx.set_font(fs, 600)   # its numbers, measured in the page's font (wider in some), with room to spare
    side = max(fs * 1.6, ctx.measure_text(str(n)) + fs * 0.6)
    gap = fs * 2.0      # between the big grid and the column beside it
    under = fs * 1.4    # between the small grid and the instructions
    sunk = tr("Sunk")
    names = [tr(SHIP_NAMES[length]) for length in fleet]

    def lay(big, tfs):
        """With the big grid big across and the column's text at tfs: (the small grid's size, the column, its x)."""
        cx = box.x + side + big + gap
        cw = box.x + box.w - cx
        col = _fleet_column(ctx, fleet, names, sunk, cw, tfs)
        small = min(cw - side, box.h - head - under - col[3])
        return small, col, cx

    # the big grid as tall as the page, unless that leaves the small one under about half its size: then the
    # column's text a little smaller (down to 85%), then the big grid a little smaller, until it does
    big = min(box.h - head, box.w - 2 * side - gap)
    while True:
        tfs = fs * 1.15
        while True:
            small, col, cx = lay(big, tfs)
            if small >= big * 0.45 or tfs < fs * 0.85:
                break
            tfs *= 0.95
        if small >= big * 0.45 or big < box.h * 0.4:
            break
        big *= 0.98
    lines, one_row, col_w, _col_h = col
    used = side + big + gap + max(side + small, col_w)
    shift = (box.w - used) / 2   # what's left over either side, when the page's height holds the grids
    top = box.y + head
    theirs = (box.x + shift + side, top)
    mine = (cx + shift + side, top)
    _battle_grid(ctx, *theirs, big, n, lw, fs, tr(GRID_NAMES["theirs"]))
    _battle_grid(ctx, *mine, small, n, lw, fs, tr(GRID_NAMES["mine"]), min(fs, small / n * 0.6))
    # the instructions and the fleet under "My ships": each ship as its squares (shaded), its name, and a box to
    # tick when it's sunk
    x0 = cx + shift
    cell = tfs
    ctx.save()
    ctx.fill_style = "#000"
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    ctx.line_width = max(1.0, lw * 0.6)
    y = top + small + under
    ctx.set_font(tfs, 400)
    for line in lines:
        y += tfs * 1.4
        ctx.fill_text(line, x0, y)
    y += tfs * 0.9
    ctx.set_font(tfs, 600)
    name_x = x0 + cell * (max(fleet) + 0.5)
    sunk_x = name_x + max(ctx.measure_text(nm) for nm in names) + tfs * 0.8
    for length, name in zip(fleet, names):
        if one_row:   # its squares, its name, then "Sunk" and its box, the names and boxes lined up
            sq_top = y + tfs * 0.3
            ctx.set_font(tfs, 600)
            ctx.fill_style = "#000"
            ctx.fill_text(name, name_x, sq_top + cell * 0.85)
            tx = sunk_x
        else:         # its name, then its squares and "Sunk" under it
            ctx.set_font(tfs, 600)
            ctx.fill_style = "#000"
            ctx.fill_text(name, x0, y + tfs * 1.1)
            sq_top = y + tfs * 1.45
            tx = x0 + cell * (length + 0.6)
        for k in range(length):
            ctx.fill_style = "#ccc"
            ctx.fill_rect(x0 + cell * k, sq_top, cell, cell)
            ctx.stroke_rect(x0 + cell * k, sq_top, cell, cell)
        ctx.fill_style = "#555"
        ctx.set_font(tfs, 400)
        ctx.fill_text(sunk, tx, sq_top + cell * 0.85)
        ctx.fill_style = "#000"
        ctx.stroke_rect(tx + ctx.measure_text(sunk) + tfs * 0.3, sq_top, cell, cell)
        y += tfs * (1.6 if one_row else 2.9)
    ctx.restore()
    return {"kind": "battle", "size": n, "fleet": fleet, "grids": [mine + (small,), theirs + (big,)]}


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    if kind_of(settings) == "battle":
        return _battle(ctx, box, c, lw, dpi)
    return _plot(ctx, box, rnd, c, lw, dpi, solve or bool(getattr(settings, "coord_answer", False)))
