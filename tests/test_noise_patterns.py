"""Contours and flow lines against recordings of index.html (tests/fixtures/contour_js.json.gz, flow_js.json.gz).

Small boxes are compared step for step. A full page has too many steps to keep, so it is compared by
the number of steps of each kind, the sums of all coordinates, and its first and last 200 steps.
"""


import numpy as np
import pytest
from recording import load_fixture, same_ops

from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.noise import Noise
from inkengine.patterns import contour, flow
from inkengine.rng import mulberry32

CASES = {name: load_fixture(name) for name in ("contour", "flow")}

DEFAULT_BOX = Box(150, 150, 2250, 3000)


def run(name, k):
    ctx = RecordingCanvas()
    ctx.line_width = k["lw"]
    box = Box(**k["box"])
    if name == "contour":
        info = contour.draw(ctx, box, mulberry32(k["seed"]), k["c"], lw=k["lw"], seed=k["seed"], dpi=k["dpi"])
    else:
        info = flow.draw(ctx, box, mulberry32(k["seed"]), k["c"], lw=k["lw"], seed=k["seed"])
    return ctx, info


def ids(k):
    return f"seed{k['seed']}-c{k['c']}" + (f"-{k['dpi']}dpi" if "dpi" in k else "") + ("-full-page" if k.get("summary") else "")


@pytest.mark.parametrize("name,k", [(n, k) for n in CASES for k in CASES[n]], ids=lambda v: v if isinstance(v, str) else ids(v))
def test_matches_javascript(name, k):
    ctx, _ = run(name, k)
    if not k.get("summary"):
        same_ops(ctx.ops, k["ops"])
        return
    kinds = {}
    sums = {"M": 0.0, "L": 0.0}
    for o in ctx.ops:
        kinds[o[0]] = kinds.get(o[0], 0) + 1
        if o[0] in sums:
            sums[o[0]] += o[1] + o[2]
    assert kinds == k["kinds"]
    for kind, total in k["sums"].items():
        assert sums[kind] == pytest.approx(total, rel=1e-9)
    same_ops(ctx.ops[:200], k["first"])
    same_ops(ctx.ops[-200:], k["last"])


def test_noise_grid_matches_point_by_point():
    """Contours use the numpy grid, flow lines the one-point version: they must agree exactly."""
    n = Noise(20261117)
    xs = np.array([-3.7, -0.2, 0.0, 0.31, 1.0, 2.5, 255.9, 256.1, 1000.25])
    ys = np.array([0.0, 4.2, -1.5, 0.99, 7.0, 3.3, 255.5, -256.7, 12.5])
    assert n.grid(xs, ys).tolist() == [n(x, y) for x, y in zip(xs.tolist(), ys.tolist())]


def test_recordings_cover_index_contours_and_both_resolutions():
    k = CASES["contour"][0]
    widths = {o[1] for o in k["ops"] if o[0] == "stroke"}
    assert widths == {k["lw"], k["lw"] * 2}
    assert {c.get("dpi") for c in CASES["contour"]} == {150, 300}


def test_contour_levels_follow_complexity():
    for c in (1, 5, 10):
        info = contour.draw(RecordingCanvas(), Box(0, 0, 300, 400), mulberry32(c), c, lw=4, seed=c, dpi=300)
        assert info["levels"] == 8 + 3 * c and info["step"] == 7 and info["segments"] > 0


def test_flow_lines_get_denser_with_complexity():
    lines = [flow.draw(RecordingCanvas(), Box(0, 0, 400, 520), mulberry32(9), c, seed=9)["lines"] for c in (1, 5, 10)]
    assert lines[0] < lines[1] < lines[2]


@pytest.mark.parametrize("gen", ["contour", "flow"])
def test_full_page_is_quick(gen):
    """A full Letter page at 300 dpi and the highest complexity, well inside a second or two."""
    import time
    from inkengine.page import Settings, draw_page, geometry, single_page
    s = Settings(gen=gen, complexity=10, seed=5)
    t = time.perf_counter()
    draw_page(RecordingCanvas(), geometry(s), single_page(s), s)
    assert time.perf_counter() - t < 6
