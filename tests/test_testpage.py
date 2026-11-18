"""The printer test page against recordings of index.html's drawTestPage (tests/fixtures/testpage_js.json.gz).

The grey ramps come from a gradient scaled into each strip, which Qt and Chromium resample a little
differently, so their dots aren't compared; everything else is, step for step: the corner marks,
rulers, squares, labels, every text, where each ramp goes, and the line weights.
"""

import pytest
from recording import load_fixture, same_ops

from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings
from inkengine.testpage import draw_test_page

CASES = load_fixture("testpage")


def without_ramp_dots(ops):
    """Keep strokes, texts, rectangles and image positions; drop filled paths (the ramps' dots and lines)."""
    keep, group = [], []
    for o in ops:
        if o[0] in ("save", "restore", "clip", "rect"):
            group = []
            continue
        group.append(o)
        if o[0] in ("stroke", "fill"):
            if o[0] == "stroke":
                keep.extend(g for g in group if g[0] != "begin")
            group = []
        elif o[0] in ("text", "stroke_rect", "image", "fill_rect"):
            keep.append(o)
            group = []
    return keep


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"{k['paper']}-{k['dpi']}dpi-dot{k['dot']}")
def test_matches_javascript_apart_from_ramp_dots(k):
    ctx = RecordingCanvas()
    info = draw_test_page(ctx, Settings(paper=k["paper"], dpi=k["dpi"], dot=k["dot"]))
    assert info == pytest.approx(k["info"])
    same_ops(without_ramp_dots(ctx.ops), without_ramp_dots(k["ops"]))


def test_everything_fits_on_the_page():
    for paper in ("letter", "a4"):
        info = draw_test_page(RecordingCanvas(), Settings(paper=paper, dpi=150))
        assert info["bottom"] <= info["limit"] + 0.5
