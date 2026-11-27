"""The optional Rust module (rust/inkline_fast) gives exactly what the Python code gives.

Skipped when inkline_fast isn't installed (it isn't part of any package yet): build it with
`pip install ./rust/inkline_fast` or `maturin develop` in that folder. docs/performance.md has more.
"""

import numpy as np
import pytest

inkline_fast = pytest.importorskip("inkline_fast")

from inkengine import photo  # noqa: E402
from inkengine.box import Box  # noqa: E402
from inkengine.canvas import RecordingCanvas  # noqa: E402
from inkengine.patterns import contour  # noqa: E402
from inkengine.rng import mulberry32  # noqa: E402


def _contour_calls(monkeypatch, fast, seed, c, box, dpi):
    monkeypatch.setattr(contour, "inkline_fast", inkline_fast if fast else None)
    ctx = RecordingCanvas()
    r = contour.draw(ctx, box, mulberry32(seed), c, lw=2.0, seed=seed, dpi=dpi)
    return ctx.ops, r


@pytest.mark.parametrize("seed,c,box,dpi", [(1, 5, Box(150, 210, 2250, 2880), 300), (42, 10, Box(37.5, 52.5, 1050, 700), 150),
                                             (7, 1, Box(0, 0, 300, 200), 72)])
def test_contour_same_segments(monkeypatch, seed, c, box, dpi):
    slow, r_slow = _contour_calls(monkeypatch, False, seed, c, box, dpi)
    fast, r_fast = _contour_calls(monkeypatch, True, seed, c, box, dpi)
    assert r_fast == r_slow and r_slow["segments"] > 0
    assert fast == slow   # every move and line, bit for bit


@pytest.mark.parametrize("atkinson", [False, True])
@pytest.mark.parametrize("t", [128, 90.5])
def test_dither_same_bytes(monkeypatch, atkinson, t):
    rng = np.random.default_rng(3)
    ww, wh = 173, 121   # odd sizes: the serpentine scan and the edges both matter
    y, x = np.mgrid[0:wh, 0:ww]
    lum = np.clip(x / ww * 255 + rng.normal(0, 30, (wh, ww)), 0, 255).astype(np.float32).ravel()
    mask = (rng.random(ww * wh) > 0.05).astype(np.uint8)   # some holes, which take no part
    fast = photo._error_diffusion(lum, mask, ww, wh, t, atkinson)
    monkeypatch.setattr(photo, "inkline_fast", None)
    slow = photo._error_diffusion(lum, mask, ww, wh, t, atkinson)
    assert isinstance(fast, bytearray) and fast == slow


def test_dither_rejects_wrong_size():
    with pytest.raises(ValueError):
        inkline_fast.error_diffusion(np.zeros(10, np.float32), np.ones(10, np.uint8), 4, 4, 128.0, False)
