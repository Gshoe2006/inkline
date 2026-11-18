"""Mazes: rectangular, or shaped like a heart, star, fish, house or a word.

Ported line for line from index.html (mazeMask, mazeGrid, genMaze, genShapedMaze), so a seed draws
the same maze as Inkline 2.x. tests/test_maze.py checks this against recordings of the JavaScript.

Every maze is carved by a depth-first walk over a grid, so there is exactly one route between any two
cells. The answer is that route from the entrance to the exit, drawn in grey under the walls.
"""

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QImage, QPainter, QPainterPath

from ..qt import ensure_app, make_font
from ..rng import mulberry32, pick
from ..shapes import OUTLINES, dense_outline

SHAPES = ["rect", "heart", "star", "fish", "house", "word"]
SHAPE_NAMES = {"rect": "Rectangle", "heart": "Heart", "star": "Star", "fish": "Fish", "house": "House", "word": "A word or name"}
SOLUTION_GREY = "#8a8a8a"


def _word(word):
    return (word or "").strip() or "Maze"


def grid_size(box, c, shape="rect", word="Maze"):
    """(cols, rows) for a maze in a box. Answer pages reuse the puzzle page's grid so they draw the same maze.
    Shaped mazes use part of the box, so they get a finer grid; words the finest, growing with their
    length, so each letter's strokes stay at least three paths wide."""
    n = max(4, len(_word(word)))
    if shape == "word":
        cols = _js_round(max(48, (8 + c * 5) * 1.4) * n / 4)
    else:
        cols = _js_round((8 + c * 5) * (1.3 if shape and shape != "rect" else 1))
    rows = max(2, math.floor(box.h / (box.w / cols)))
    return cols, rows


def _js_round(x):
    """Math.round: halves round up (Python's round() goes to the even number)."""
    return int(math.floor(x + 0.5))


def _raster_mask(shape, cols, rows, word):
    """Draw the shape or word one pixel per cell; a cell is in the maze if it is more than half covered."""
    ensure_app()
    img = QImage(cols, rows, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    if shape == "word":
        text = _word(word)
        width100 = QFontMetricsF(make_font(100, 900)).horizontalAdvance(text)
        fs = min(cols * 0.86 / width100 * 100, rows * 0.62)
        font = make_font(fs, 900)
        fm = QFontMetricsF(font)
        x = cols / 2 - fm.horizontalAdvance(text) / 2
        y = rows / 2 + (fm.ascent() - fm.descent()) / 2   # canvas textBaseline "middle"
        path.addText(QPointF(x, y), font, text)
    else:
        line = dense_outline(OUTLINES[shape](mulberry32(7)))
        xs, ys = [q[0] for q in line], [q[1] for q in line]
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        sc = min(cols * 0.96 / bw, rows * 0.96 / bh)
        ox = cols / 2 - (min(xs) + bw / 2) * sc
        oy = rows / 2 - (min(ys) + bh / 2) * sc
        for i, (px, py, _c) in enumerate(line):
            (path.lineTo if i else path.moveTo)(ox + px * sc, oy + py * sc)
        path.closeSubpath()
    p.fillPath(path, QColor("#000"))
    p.end()
    mask = bytearray(cols * rows)
    for y in range(rows):
        for x in range(cols):
            if img.pixelColor(x, y).alpha() > 127:
                mask[y * cols + x] = 1
    return mask


def maze_mask(shape, cols, rows, word="Maze"):
    """Which grid cells a shaped maze may use, as a bytearray of 0/1 (None for the plain rectangle).
    Separate pieces (letters) are joined by the shortest corridors, so the maze is always one piece."""
    if not shape or shape == "rect":
        return None
    return join_pieces(_raster_mask(shape, cols, rows, word), cols, rows)


def join_pieces(mask, cols, rows):
    """Join the mask's pieces to the biggest one, nearest first, until there is one piece."""
    N = cols * rows

    def nbrs(i):
        x0, o = i % cols, []
        if x0 > 0:
            o.append(i - 1)
        if x0 < cols - 1:
            o.append(i + 1)
        if i >= cols:
            o.append(i - cols)
        if i < N - cols:
            o.append(i + cols)
        return o

    for _guard in range(64):
        comp, sizes, n = [-1] * N, [], 0
        for i in range(N):
            if mask[i] and comp[i] < 0:
                st, k = [i], 0
                comp[i] = n
                while st:
                    q = st.pop()
                    k += 1
                    for j in nbrs(q):
                        if mask[j] and comp[j] < 0:
                            comp[j] = n
                            st.append(j)
                sizes.append(k)
                n += 1
        if n <= 1:
            break
        main = sizes.index(max(sizes))
        frm = [-2] * N
        queue = []
        for i in range(N):
            if comp[i] == main:
                frm[i] = -1
                queue.append(i)
        hit, h = -1, 0
        while h < len(queue) and hit < 0:
            for j in nbrs(queue[h]):
                if frm[j] != -2:
                    continue
                frm[j] = queue[h]
                if mask[j]:
                    hit = j
                    break
                queue.append(j)
            h += 1
        if hit < 0:
            break
        i = frm[hit]
        while i >= 0 and comp[i] != main:
            mask[i] = 1
            i = frm[i]
    return mask


def _carve(rnd, cols, rows, start, inside):
    """Depth-first walk from start. Returns (east walls, south walls, seen, parent); parent leads back to start."""
    N = cols * rows
    E, S, seen, parent = bytearray(b"\x01" * N), bytearray(b"\x01" * N), bytearray(N), [-1] * N
    stack = [start]
    seen[start] = 1
    while stack:
        cur = stack[-1]
        x = cur % cols
        nb = []
        if x > 0 and inside(cur - 1) and not seen[cur - 1]:
            nb.append(cur - 1)
        if x < cols - 1 and inside(cur + 1) and not seen[cur + 1]:
            nb.append(cur + 1)
        if inside(cur - cols) and not seen[cur - cols]:
            nb.append(cur - cols)
        if inside(cur + cols) and not seen[cur + cols]:
            nb.append(cur + cols)
        if not nb:
            stack.pop()
            continue
        nx = nb[pick(rnd, len(nb))]
        if nx == cur + 1:
            E[cur] = 0
        elif nx == cur - 1:
            E[nx] = 0
        elif nx == cur + cols:
            S[cur] = 0
        else:
            S[nx] = 0
        seen[nx] = 1
        parent[nx] = cur
        stack.append(nx)
    return E, S, seen, parent


def draw(ctx, box, rnd, c, settings=None, grid=None, solve=False):
    """Draw a maze filling box. settings supplies maze_shape and maze_word; grid=(cols, rows) forces a grid
    (answer pages); solve=True draws the route from entrance to exit."""
    shape = getattr(settings, "maze_shape", "rect")
    word = getattr(settings, "maze_word", "Maze")
    cols, rows = grid or grid_size(box, c, shape, word)
    cs = min(box.w / cols, box.h / rows)
    ox, oy = box.x + (box.w - cols * cs) / 2, box.y + (box.h - rows * cs) / 2
    mask = maze_mask(shape, cols, rows, word)
    if mask:
        return _draw_shaped(ctx, rnd, cols, rows, cs, ox, oy, mask, solve)

    N = cols * rows
    E, S, _seen, parent = _carve(rnd, cols, rows, 0, lambda i: 0 <= i < N)
    centre = lambda i: (ox + (i % cols + 0.5) * cs, oy + (i // cols + 0.5) * cs)
    if solve:
        ctx.save()
        ctx.stroke_style, ctx.line_width, ctx.line_cap, ctx.line_join = SOLUTION_GREY, cs * 0.38, "round", "round"
        ctx.begin_path()
        ctx.move_to(ox + cs * 1.5 + cols * cs - cs, oy + rows * cs - cs / 2)   # off the exit edge
        i = N - 1
        while i != -1:
            ctx.line_to(*centre(i))
            i = parent[i]
        ctx.line_to(ox + cs / 2, oy - cs / 2)                                  # off the entrance edge
        ctx.stroke()
        ctx.restore()
    ctx.line_cap = "square"
    ctx.begin_path()
    ctx.move_to(ox + cs, oy)                         # outer wall; gap at the top-left is the entrance
    ctx.line_to(ox + cols * cs, oy)
    ctx.line_to(ox + cols * cs, oy + rows * cs - cs)   # gap at the bottom-right is the exit
    ctx.move_to(ox + cols * cs - cs, oy + rows * cs)
    ctx.line_to(ox, oy + rows * cs)
    ctx.line_to(ox, oy + cs)
    for y in range(rows):
        for x in range(cols):
            i, X, Y = y * cols + x, ox + x * cs, oy + y * cs
            if E[i] and x < cols - 1:
                ctx.move_to(X + cs, Y)
                ctx.line_to(X + cs, Y + cs)
            if S[i] and y < rows - 1:
                ctx.move_to(X, Y + cs)
                ctx.line_to(X + cs, Y + cs)
    ctx.stroke()
    return {"cols": cols, "rows": rows, "cells": N, "reached": N}


def _draw_shaped(ctx, rnd, cols, rows, cs, ox, oy, mask, solve):
    """A maze inside a mask: entrance at the top-most cell (opening upward), exit at the bottom-most
    (opening downward)."""
    N = cols * rows
    inside = lambda i: 0 <= i < N and mask[i]
    cells = [i for i in range(N) if mask[i]]
    entrance, exit_ = cells[0], cells[-1]
    E, S, seen, parent = _carve(rnd, cols, rows, entrance, inside)
    centre = lambda i: (ox + (i % cols + 0.5) * cs, oy + (i // cols + 0.5) * cs)
    if solve:
        ctx.save()
        ctx.stroke_style, ctx.line_width, ctx.line_cap, ctx.line_join = SOLUTION_GREY, cs * 0.38, "round", "round"
        ex, ey = centre(exit_)
        nx0, ny0 = centre(entrance)
        ctx.begin_path()
        ctx.move_to(ex, ey + cs)   # out of the exit gap
        i = exit_
        while i != -1:
            ctx.line_to(*centre(i))
            i = parent[i]
        ctx.line_to(nx0, ny0 - cs)   # out of the entrance gap
        ctx.stroke()
        ctx.restore()
    ctx.line_cap = "square"
    ctx.begin_path()

    def wall(x1, y1, x2, y2):
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)

    for i in cells:
        x, y = i % cols, i // cols
        X, Y = ox + x * cs, oy + y * cs
        if not inside(i - cols) and i != entrance:
            wall(X, Y, X + cs, Y)
        if x == 0 or not mask[i - 1]:
            wall(X, Y, X, Y + cs)
        if x == cols - 1 or not mask[i + 1] or E[i]:
            wall(X + cs, Y, X + cs, Y + cs)
        if (not inside(i + cols) and i != exit_) or (inside(i + cols) and S[i]):
            wall(X, Y + cs, X + cs, Y + cs)
    ctx.stroke()
    return {"cols": cols, "rows": rows, "cells": len(cells), "reached": sum(seen), "entrance": entrance, "exit": exit_}
