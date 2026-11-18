"""The Python maze against recordings of index.html's maze (tests/fixtures/maze_js.json.gz).

Rectangular mazes must match the JavaScript line for line. Shaped mazes depend on how the shape is
rasterised, which differs slightly between Chromium and Qt, so: carving the JavaScript's own mask must
match line for line, and Qt's mask must agree with Chromium's for the outline shapes.
"""


import pytest

from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings
from inkengine.patterns import maze
from inkengine.rng import mulberry32

CASES = load_fixture("maze")


def case_id(k):
    return f"{k['shape']}-{k['seed']}-c{k['c']}{'-solved' if k['solve'] else ''}"


def recorder(k):
    ctx = RecordingCanvas()
    ctx.line_width = k["lw"]
    return ctx


@pytest.mark.parametrize("k", [k for k in CASES if k["shape"] == "rect"], ids=case_id)
def test_rectangle_matches_javascript(k):
    box = Box(**k["box"])
    s = Settings(maze_shape="rect")
    assert maze.grid_size(box, k["c"], "rect") == (k["grid"]["cols"], k["grid"]["rows"])
    ctx = recorder(k)
    maze.draw(ctx, box, mulberry32(k["seed"]), k["c"], s, solve=k["solve"])
    same_ops(ctx.ops, [tuple(o) for o in k["ops"]])


@pytest.mark.parametrize("k", [k for k in CASES if k["shape"] != "rect"], ids=case_id)
def test_shaped_carving_matches_javascript(k, monkeypatch):
    """Given Chromium's mask, the walls and route must be the JavaScript's exactly."""
    box = Box(**k["box"])
    cols, rows = k["grid"]["cols"], k["grid"]["rows"]
    assert maze.grid_size(box, k["c"], k["shape"], k["word"] or "Maze") == (cols, rows)
    js_mask = bytearray(int(ch) for ch in k["mask"])
    monkeypatch.setattr(maze, "maze_mask", lambda *a: bytearray(js_mask))
    ctx = recorder(k)
    info = maze.draw(ctx, box, mulberry32(k["seed"]), k["c"], Settings(maze_shape=k["shape"], maze_word=k["word"]),
                     grid=(cols, rows), solve=k["solve"])
    assert info["reached"] == info["cells"]          # every cell is part of the maze
    same_ops(ctx.ops, [tuple(o) for o in k["ops"]])


@pytest.mark.parametrize("shape", ["heart", "star", "fish", "house"])
def test_outline_masks_agree_with_chromium(shape):
    k = next(k for k in CASES if k["shape"] == shape)
    cols, rows = k["grid"]["cols"], k["grid"]["rows"]
    mine = maze.maze_mask(shape, cols, rows)
    differ = sum(1 for a, ch in zip(mine, k["mask"]) if a != int(ch))
    assert differ <= max(2, 0.01 * sum(mine)), f"{differ} cells differ from Chromium's {shape}"


@pytest.mark.parametrize("shape,word", [("heart", ""), ("star", ""), ("fish", ""), ("house", ""),
                                        ("word", "Maya"), ("word", "Hi Jo"), ("word", "Alexandrina")])
def test_every_shaped_maze_is_one_piece(shape, word):
    box = Box(150, 150, 2250, 3000)
    s = Settings(maze_shape=shape, maze_word=word)
    for seed in (1, 2, 3):
        info = maze.draw(RecordingCanvas(), box, mulberry32(seed), 5, s)
        assert info["cells"] > 50
        assert info["reached"] == info["cells"], "some cells can't be reached"
        assert info["entrance"] < info["exit"]


def test_word_mask_is_heavy_enough():
    """Each letter needs room for paths; Qt's font must give about as many cells as Chromium's did."""
    k = next(k for k in CASES if k["shape"] == "word")
    mine = maze.maze_mask("word", k["grid"]["cols"], k["grid"]["rows"], k["word"])
    assert sum(mine) >= 0.7 * k["mask"].count("1")
