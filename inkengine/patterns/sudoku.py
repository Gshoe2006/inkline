"""Sudoku: a 9x9 grid where every row, column and 3x3 box holds 1 to 9 once.

Ported from index.html (makeSudoku, genSudoku), so a seed gives the same puzzle as Inkline 2.x.
tests/test_sudoku.py checks this against recordings of the JavaScript.

A full grid is filled at random, then givens are removed in symmetric pairs (cell i with 80 - i),
keeping a removal only if the puzzle still has exactly one solution. Complexity aims for 48 givens
at 1 down to 25 at 10; the hardest finish with single cells, trading perfect symmetry for the
difficulty the slider promises.

Grids are 81-cell lists (row by row), 0 = empty; candidates are bit masks over bits 1..9. The seed
is only used by the fill and the shuffles, which follow the JavaScript exactly; the solution counter
just has to give the same count, so it keeps row, column and box masks up to date instead of
rescanning, which is several times faster in Python.
"""

from ..rng import pick

_ROW = [i // 9 for i in range(81)]
_COL = [i % 9 for i in range(81)]
_BOX = [(i // 27) * 3 + (i % 9) // 3 for i in range(81)]
_BITS = [bin(m).count("1") for m in range(1024)]
_DIGITS = [[d for d in range(1, 10) if m & (1 << d)] for m in range(1024)]
FULL = 0x3FE   # bits 1..9


class _Grid:
    """A grid with the digits used in each row, column and box kept as bit masks."""

    def __init__(self, cells):
        self.g = list(cells)
        self.rows, self.cols, self.boxes = [0] * 9, [0] * 9, [0] * 9
        for i, d in enumerate(self.g):
            if d:
                self._mark(i, d)

    def _mark(self, i, d):
        b = 1 << d
        self.rows[_ROW[i]] |= b
        self.cols[_COL[i]] |= b
        self.boxes[_BOX[i]] |= b

    def set(self, i, d):
        self.g[i] = d
        self._mark(i, d)

    def clear(self, i):
        b = ~(1 << self.g[i])
        self.rows[_ROW[i]] &= b
        self.cols[_COL[i]] &= b
        self.boxes[_BOX[i]] &= b
        self.g[i] = 0

    def candidates(self, i):
        return ~(self.rows[_ROW[i]] | self.cols[_COL[i]] | self.boxes[_BOX[i]]) & FULL

    def pick(self):
        """The empty cell with the fewest candidates (the first on ties), its mask and their count;
        (-1, 0, 10) when the grid is full. Stops early at a cell with none, as index.html does."""
        g, best, mask, n = self.g, -1, 0, 10
        for i in range(81):
            if not g[i]:
                m = self.candidates(i)
                k = _BITS[m]
                if k < n:
                    best, mask, n = i, m, k
                    if n == 0:
                        break
        return best, mask, n


def count_solutions(cells, limit=2):
    """Number of solutions, counting no further than limit."""
    grid = _Grid(cells)

    def count(limit):
        best, mask, n = grid.pick()
        if best < 0:
            return 1
        if n == 0:
            return 0
        total = 0
        for d in _DIGITS[mask]:
            if total >= limit:
                break
            grid.set(best, d)
            total += count(limit - total)
            grid.clear(best)
        return total

    return count(limit)


def _fill(grid, rnd):
    best, mask, _n = grid.pick()
    if best < 0:
        return True
    ds = list(_DIGITS[mask])
    for i in range(len(ds) - 1, 0, -1):
        j = pick(rnd, i + 1)
        ds[i], ds[j] = ds[j], ds[i]
    for d in ds:
        grid.set(best, d)
        if _fill(grid, rnd):
            return True
        grid.clear(best)
    return False


def _shuffle(items, rnd):
    for i in range(len(items) - 1, 0, -1):
        j = pick(rnd, i + 1)
        items[i], items[j] = items[j], items[i]


def make_sudoku(rnd, c):
    """(puzzle, solution, clues) for complexity c."""
    grid = _Grid([0] * 81)
    _fill(grid, rnd)
    solution = list(grid.g)
    puzzle = list(solution)
    target = int(48 - (c - 1) * 2.6 + 0.5)   # Math.round
    order = list(range(41))                  # cell i pairs with 80 - i (180 degree symmetry); 40 is the centre
    _shuffle(order, rnd)
    clues = 81
    for i in order:
        if clues <= target:
            break
        cells = [40] if i == 40 else [i, 80 - i]
        keep = [puzzle[k] for k in cells]
        for k in cells:
            puzzle[k] = 0
        if count_solutions(puzzle, 2) == 1:
            clues -= len(cells)
        else:
            for k, d in zip(cells, keep):
                puzzle[k] = d
    # Pairs often can't both go near the top of the range even when one can, so finish with single cells.
    if clues > target:
        singles = [i for i in range(81) if puzzle[i]]
        _shuffle(singles, rnd)
        for k in singles:
            if clues <= target:
                break
            keep, puzzle[k] = puzzle[k], 0
            if count_solutions(puzzle, 2) == 1:
                clues -= 1
            else:
                puzzle[k] = keep
    return puzzle, solution, clues


def level(clues):
    return "Easy" if clues >= 42 else "Medium" if clues >= 34 else "Hard" if clues >= 28 else "Expert"


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The puzzle (or, with solve=True, the answer: givens in black, the rest filled in grey)."""
    puzzle, solution, clues = make_sudoku(rnd, c)
    cap = 0 if solve else min(box.h * 0.08, dpi * 0.35)
    side = min(box.w, box.h - cap) * 0.94
    cs = side / 9
    x0, y0 = box.x + (box.w - side) / 2, box.y + (box.h - cap - side) / 2
    ctx.save()
    ctx.line_cap, ctx.stroke_style = "square", "#000"
    for k in range(10):   # thin cell lines, thicker 3x3 box lines, thickest border
        ctx.line_width = lw * 0.35 if k % 3 else lw * 1.3 if k in (0, 9) else lw
        ctx.begin_path()
        ctx.move_to(x0 + k * cs, y0)
        ctx.line_to(x0 + k * cs, y0 + side)
        ctx.move_to(x0, y0 + k * cs)
        ctx.line_to(x0 + side, y0 + k * cs)
        ctx.stroke()
    fs = cs * 0.62
    ctx.text_align, ctx.text_baseline = "center", "alphabetic"
    for i in range(81):
        given = bool(puzzle[i])
        if not given and not solve:
            continue
        ctx.set_font(fs, 700 if given else 400)
        ctx.fill_style = "#000" if given else "#777"
        ctx.fill_text(str(puzzle[i] if given else solution[i]), x0 + (i % 9 + 0.5) * cs, y0 + (i // 9 + 0.5) * cs + fs * 0.36)
    if not solve:
        ctx.set_font(min(dpi * 0.13, cap * 0.5), 400)
        ctx.fill_style = "#555"
        ctx.fill_text(f"{level(clues)} · {clues} clues", box.x + box.w / 2, y0 + side + cap * 0.7)
    ctx.restore()
    return {"clues": clues, "level": level(clues), "puzzle": puzzle, "solution": solution}
