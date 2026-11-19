"""Kakuro (cross sums): fill the white squares with 1 to 9 so each run adds up to its clue, with no
number repeated in a run. A few squares come filled in as starters.

A layout of white and black squares is laid out with 180-degree symmetry (no run of one square, all
white squares joined up) and filled with digits that don't repeat in any run; the runs' sums become
the clues. Sums alone almost never pin down one filling: any 2 x 2 block of white squares can trade
+1/-1 round its corners without changing a sum. So where the solver still finds two fillings, a
square they disagree on is printed as a starter, until only one filling fits; then each starter is
taken back if the puzzle still comes out one way without it. Easier settings keep a few more.
Complexity sets the grid: 4 x 4 white squares at 1 up to 8 x 8 at 10.

Cells are (row, col) on the whole grid, clue row and column included; masks are digit sets over bits
1..9, as in sudoku.py.
"""

from functools import lru_cache
from itertools import combinations

from ..rng import pick

INSTRUCTIONS = "Fill each white square with 1 to 9 so every run adds up to its clue. No number repeats in a run."


def size(c):
    """White-square grid side: 4 at complexity 1, 8 at 10."""
    return 4 + round((max(1, min(10, c)) - 1) * 4 / 9)


def _combo_masks():
    masks = {}
    for k in range(1, 10):
        for combo in combinations(range(1, 10), k):
            masks.setdefault((k, sum(combo)), []).append(sum(1 << d for d in combo))
    return masks


_COMBOS = _combo_masks()


@lru_cache(maxsize=None)
def _allowed(k, rest, used):
    """Digits that can still go in a run with k squares left to fill, adding up to rest, given the
    digits already in it (used)."""
    out = 0
    for m in _COMBOS.get((k, rest), ()):
        if not m & used:
            out |= m
    return out


def _runs(white, N):
    """The across and down runs: lists of [(r, c), ...] of two squares or more, with the clue square
    just before each run."""
    runs = []
    for across in (True, False):
        for a in range(N):
            run = []
            for b in range(N + 1):
                r, c = (a, b) if across else (b, a)
                if b < N and white[r][c]:
                    run.append((r, c))
                else:
                    if len(run) >= 2:
                        runs.append((across, run))
                    run = []
    return runs


def _tidy(white, n, least=0.45):
    """Make a layout valid in place: no lone squares (every white square sits in an across and a down
    run of 2 or more), keeping the 180-degree symmetry. True if what's left is joined up, big enough
    and has no run longer than 9 squares."""
    N = n + 1
    changed = True
    while changed:
        changed = False
        for r in range(1, N):
            for c in range(1, N):
                if not white[r][c]:
                    continue
                h = (c > 1 and white[r][c - 1]) or (c < n and white[r][c + 1])
                v = (r > 1 and white[r - 1][c]) or (r < n and white[r + 1][c])
                if not (h and v):
                    white[r][c] = white[N - r][N - c] = False
                    changed = True
    cells = [(r, c) for r in range(N) for c in range(N) if white[r][c]]
    if len(cells) < n * n * least:
        return False
    seen, todo = {cells[0]}, [cells[0]]   # all joined up
    while todo:
        r, c = todo.pop()
        for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if q not in seen and 0 <= q[0] < N and 0 <= q[1] < N and white[q[0]][q[1]]:
                seen.add(q)
                todo.append(q)
    return len(seen) == len(cells) and all(len(run) <= 9 for _a, run in _runs(white, N))


def _layout(rnd, n):
    """A symmetric layout on an (n+1) x (n+1) grid whose first row and column are clue squares."""
    N = n + 1
    for _attempt in range(200):
        white = [[r > 0 and c > 0 for c in range(N)] for r in range(N)]
        for r in range(1, N):
            for c in range(1, N):
                rr, cc = N - r, N - c   # the 180-degree twin, in the white area
                if (r, c) <= (rr, cc) and rnd() < 0.22:
                    white[r][c] = white[rr][cc] = False
        if _tidy(white, n) and sum(map(sum, white)) >= n * n * 0.6:
            return white
    raise RuntimeError("no kakuro layout")   # not reached in practice: 200 tries is plenty


class _Puzzle:
    def __init__(self, white, N):
        self.N, self.white = N, white
        self.runs = _runs(white, N)
        self.cells = [(r, c) for r in range(N) for c in range(N) if white[r][c]]
        self.of = {q: [] for q in self.cells}   # each square's two runs
        for k, (_across, run) in enumerate(self.runs):
            for q in run:
                self.of[q].append(k)

    def fill(self, rnd):
        """Digits with no repeat in any run, chosen at random (backtracking)."""
        val = {}
        used = [0] * len(self.runs)

        def go(i):
            if i == len(self.cells):
                return True
            q = self.cells[i]
            free = [d for d in range(1, 10) if not any(used[k] & (1 << d) for k in self.of[q])]
            for j in range(len(free) - 1, 0, -1):   # shuffle
                s = pick(rnd, j + 1)
                free[j], free[s] = free[s], free[j]
            for d in free:
                val[q] = d
                for k in self.of[q]:
                    used[k] |= 1 << d
                if go(i + 1):
                    return True
                for k in self.of[q]:
                    used[k] &= ~(1 << d)
            val.pop(q, None)
            return False

        go(0)
        return val

    def count(self, sums, limit=2, givens=None):
        """How many fillings fit the run sums (stops at limit), with any given squares filled in."""
        left = [len(run) for _a, run in self.runs]
        rest = list(sums)
        used = [0] * len(self.runs)
        for q, d in (givens or {}).items():
            for k in self.of[q]:
                left[k] -= 1
                rest[k] -= d
                used[k] |= 1 << d
        return self.count_from(left, rest, used, set(self.cells) - set(givens or {}), limit)

    def count_from(self, left, rest, used, open_, limit=2, budget=20000):
        """Counts as count() does. Gives up after budget guesses and says limit (not one way): the
        same answer every time, so a seed still gives the same puzzle."""
        runs, of = self.runs, self.of
        found = [0]
        steps = [budget]
        val = {}
        self.solutions = []

        def cand(q):
            m = 0x3FE
            for k in of[q]:
                m &= _allowed(left[k], rest[k], used[k]) & ~used[k]
            return m

        def go():
            if not open_:
                found[0] += 1
                self.solutions.append(dict(val))
                return found[0] >= limit
            best, bm, bn = None, 0, 10
            for q in open_:   # the square with the fewest digits left
                m = cand(q)
                n = bin(m).count("1")
                if n < bn:
                    best, bm, bn = q, m, n
                    if n <= 1:
                        break
            if bn == 0:
                return False
            steps[0] -= 1
            if steps[0] < 0:
                found[0] = limit
                return True
            open_.discard(best)
            for d in range(1, 10):
                if bm & (1 << d):
                    for k in of[best]:
                        left[k] -= 1
                        rest[k] -= d
                        used[k] |= 1 << d
                    val[best] = d
                    stop = go()
                    del val[best]
                    for k in of[best]:
                        left[k] += 1
                        rest[k] += d
                        used[k] &= ~(1 << d)
                    if stop:
                        open_.add(best)
                        return True
            open_.add(best)
            return False

        go()
        return found[0]


def make_kakuro(rnd, c):
    """(white, runs as [(across, cells, sum)], solution {(r, c): digit}, starters {(r, c): digit}, N)."""
    n = size(c)
    N = n + 1
    while True:
        p = _Puzzle(_layout(rnd, n), N)
        val = p.fill(rnd)
        if not val:
            continue
        sums = [sum(val[q] for q in run) for _a, run in p.runs]
        given = {}
        while p.count(sums, givens=given) != 1:
            open_ = [q for q in p.cells if q not in given]
            if len(p.solutions) >= 2:   # a square the two fillings disagree on
                a, b = p.solutions
                open_ = [q for q in open_ if a[q] != b[q]]
            q = open_[pick(rnd, len(open_))]
            given[q] = val[q]
        for q in sorted(given, key=lambda q: (rnd(), q)):   # take back the ones it doesn't need
            d = given.pop(q)
            if p.count(sums, givens=given) != 1:
                given[q] = d
        extra = round(len(p.cells) * 0.12 * (10 - c) / 9)   # easier settings get a little more help
        spare = [q for q in p.cells if q not in given]
        for _k in range(min(extra, len(spare))):
            q = spare.pop(pick(rnd, len(spare)))
            given[q] = val[q]
        return p.white, [(a, run, s) for (a, run), s in zip(p.runs, sums)], val, given, N


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The puzzle (or, with solve=True, every square filled in)."""
    white, runs, solution, given, N = make_kakuro(rnd, c)
    # draw only the puzzle: from the clue row and column just before the first white squares to the
    # last white squares, so no rows or columns of empty grey are printed
    rows = [r for r, _c in solution]
    cols = [c2 for _r, c2 in solution]
    r0, r1, c0, c1 = min(rows) - 1, max(rows), min(cols) - 1, max(cols)
    nr, nc = r1 - r0 + 1, c1 - c0 + 1
    cap = 0 if solve else min(box.h * 0.08, dpi * 0.35)
    cs = min(box.w / nc, (box.h - cap) / nr) * 0.94
    gw, gh = nc * cs, nr * cs
    x0 = box.x + (box.w - gw) / 2 - c0 * cs   # so square (r, c) sits at x0 + c * cs, y0 + r * cs
    y0 = box.y + (box.h - cap - gh) / 2 - r0 * cs
    left, top = x0 + c0 * cs, y0 + r0 * cs
    ctx.save()
    ctx.fill_style = "#d4d4d4"   # clue squares: light grey, so a page doesn't drink the ink
    for r in range(r0, r1 + 1):
        for c2 in range(c0, c1 + 1):
            if not white[r][c2]:
                ctx.fill_rect(x0 + c2 * cs, y0 + r * cs, cs, cs)
    ctx.stroke_style, ctx.line_cap = "#000", "square"
    ctx.line_width = lw * 0.6
    ctx.begin_path()
    for k in range(nc + 1):
        ctx.move_to(left + k * cs, top)
        ctx.line_to(left + k * cs, top + gh)
    for k in range(nr + 1):
        ctx.move_to(left, top + k * cs)
        ctx.line_to(left + gw, top + k * cs)
    ctx.stroke()
    clue = {}
    for across, run, s in runs:
        r, c2 = run[0]
        key = (r, c2 - 1) if across else (r - 1, c2)
        clue.setdefault(key, {})["across" if across else "down"] = s
    ctx.line_width = lw * 0.5
    ctx.begin_path()
    for r, c2 in clue:   # the diagonal that splits a clue square
        ctx.move_to(x0 + c2 * cs, y0 + r * cs)
        ctx.line_to(x0 + (c2 + 1) * cs, y0 + (r + 1) * cs)
    ctx.stroke()
    ctx.line_width = lw * 1.3
    ctx.stroke_rect(left, top, gw, gh)
    fs = cs * 0.3
    ctx.set_font(fs, 700)
    ctx.fill_style, ctx.text_baseline = "#000", "alphabetic"
    for (r, c2), sums in clue.items():
        x, y = x0 + c2 * cs, y0 + r * cs
        if "across" in sums:   # top right: the run to the right
            ctx.text_align = "right"
            ctx.fill_text(str(sums["across"]), x + cs * 0.92, y + cs * 0.38)
        if "down" in sums:     # bottom left: the run below
            ctx.text_align = "left"
            ctx.fill_text(str(sums["down"]), x + cs * 0.08, y + cs * 0.9)
    ctx.text_align = "center"
    for (r, c2), d in solution.items():   # starters in bold; the answer fills in the rest in grey
        if (r, c2) in given or solve:
            ctx.set_font(cs * 0.6, 700 if (r, c2) in given else 400)
            ctx.fill_style = "#000" if (r, c2) in given else "#777"
            ctx.fill_text(str(d), x0 + (c2 + 0.5) * cs, y0 + (r + 0.5) * cs + cs * 0.21)
    if not solve:
        ctx.set_font(min(dpi * 0.13, cap * 0.5), 400)
        ctx.text_align, ctx.fill_style = "center", "#555"
        ctx.fill_text(INSTRUCTIONS, box.x + box.w / 2, top + gh + cap * 0.7, box.w)
    ctx.restore()
    return {"white": white, "runs": runs, "solution": solution, "starters": given}
