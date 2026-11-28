"""The optional Rust module (rust/inkline_fast) gives exactly what the Python code gives.

Skipped when inkline_fast isn't installed (the packages that ship it are listed in docs/performance.md): build it with
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


# --- the photo loops added after the trial: stipple, engraving, blur, despeckle, chamfer distances ----------

def _picture(seed, ww, wh, holes=0.05):
    """Tones with a gradient, a dark blob and noise (some below 0 and above 255, which get clamped), and a mask
    with holes and a blank margin on the left, as a photo fitted inside its box has."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:wh, 0:ww]
    v = x / max(1, ww) * 255 - 120 * np.exp(-(((x - ww * 0.6) / (ww * 0.2 + 1)) ** 2 + ((y - wh * 0.4) / (wh * 0.25 + 1)) ** 2))
    lum = (v + rng.normal(0, 25, (wh, ww)) + 10).astype(np.float32).ravel()
    mask = (rng.random(ww * wh) > holes).astype(np.uint8)
    mask.reshape(wh, ww)[:, : ww // 9] = 0
    return lum, mask


def _conversion(lum, mask, ww, wh):
    return photo.Conversion(ww, wh, lum, mask)


SIZES = [(1, 173, 121), (2, 64, 300), (3, 401, 7), (4, 2, 2), (5, 1, 9), (6, 250, 250)]


@pytest.mark.parametrize("seed,ww,wh", SIZES)
@pytest.mark.parametrize("inv", [False, True])
def test_stipple_sites_same(monkeypatch, seed, ww, wh, inv):
    lum, mask = _picture(seed, ww, wh)
    fast = photo.stipple_sites(_conversion(lum, mask, ww, wh), inv)
    monkeypatch.setattr(photo, "inkline_fast", None)
    slow = photo.stipple_sites(_conversion(lum, mask, ww, wh), inv)
    assert fast == slow and all(type(i) is int for i in fast)
    if ww * wh > 1000:
        assert len(slow) > 50


@pytest.mark.parametrize("seed,ww,wh", SIZES)
@pytest.mark.parametrize("inv", [False, True])
def test_engrave_bands_same(seed, ww, wh, inv):
    lum, mask = _picture(seed, ww, wh)
    lum64 = lum.astype(np.float64)
    total = 0
    for band in range((wh + photo.ENGRAVE_PITCH - 1) // photo.ENGRAVE_PITCH):
        pts, lens = inkline_fast.engrave_band(lum, mask, ww, wh, inv, band, photo.ENGRAVE_PITCH, photo.ENGRAVE_STEP)
        fast = [s.tolist() for s in np.split(pts, np.cumsum(lens)[:-1])] if len(lens) else []
        slow = [[list(p) for p in s] for s in photo._engrave_band(lum64, mask, ww, wh, inv, band)]
        assert fast == slow
        total += len(slow)
    if ww * wh > 1000:
        assert total > 0


@pytest.mark.parametrize("seed,ww,wh", SIZES[:3] + SIZES[5:])
@pytest.mark.parametrize("inv", [False, True])
def test_engraving_and_stipple_drawn_the_same(monkeypatch, seed, ww, wh, inv):
    lum, mask = _picture(seed, ww, wh)
    box = Box(37.5, 52.5, ww * 4.3, wh * 4.1)
    view = Box(box.x + box.w * 0.3, box.y, box.w * 0.4, box.h * 0.5)   # a poster sheet: lines off it are skipped

    def ops(draw, v):
        ctx = RecordingCanvas()
        draw(ctx, box, _conversion(lum, mask, ww, wh), inv, v)
        return ctx.ops
    for v in (None, view):
        fast = [ops(photo._draw_engraving, v), ops(photo._draw_stipple, v)]
        with monkeypatch.context() as m:
            m.setattr(photo, "inkline_fast", None)
            slow = [ops(photo._draw_engraving, v), ops(photo._draw_stipple, v)]
        assert fast == slow


@pytest.mark.parametrize("seed,w,h", [(1, 173, 121), (2, 3, 50), (3, 90, 1), (4, 1, 1), (5, 300, 200)])
@pytest.mark.parametrize("sigma", [0.8, 1.28, 2.4, 5.0])
def test_gauss_blur_same(monkeypatch, seed, w, h, sigma):
    src, _ = _picture(seed, w, h)
    fast = photo.gauss_blur(src, w, h, sigma)
    monkeypatch.setattr(photo, "inkline_fast", None)
    slow = photo.gauss_blur(src, w, h, sigma)
    assert fast.dtype == slow.dtype == np.float32 and np.array_equal(fast, slow)


@pytest.mark.parametrize("seed,w,h,min_size", [(1, 173, 121, 12), (2, 50, 50, 1), (3, 200, 9, 40), (4, 1, 1, 12)])
def test_despeckle_same(monkeypatch, seed, w, h, min_size):
    rng = np.random.default_rng(seed)
    img = bytearray(np.where(rng.random(w * h) < 0.35, 0, 255).astype(np.uint8).tobytes())
    fast, slow = bytearray(img), bytearray(img)
    photo.despeckle(fast, w, h, min_size)
    monkeypatch.setattr(photo, "inkline_fast", None)
    photo.despeckle(slow, w, h, min_size)
    assert fast == slow
    if min_size > 1 and w * h > 100:
        assert fast != img   # something was cleared


@pytest.mark.parametrize("seed,w,h,k", [(1, 120, 90, 6), (2, 300, 40, 3), (3, 3, 30, 2), (4, 40, 2, 4), (5, 2, 2, 2)])
def test_cbn_distance_same(monkeypatch, seed, w, h, k):
    from inkengine import cbn
    rng = np.random.default_rng(seed)
    val = rng.integers(0, k, w * h)
    val[rng.random(w * h) < 0.03] = -1
    for _ in range(3):   # blobs of a fair size, so the distances get deep
        val = cbn.mode_filter(val, w, h, k)
    label, _ = cbn.components(val, w, h)
    fast = cbn.distance(label, w, h)
    monkeypatch.setattr(cbn, "inkline_fast", None)
    slow = cbn.distance(label, w, h)
    assert fast.dtype == slow.dtype == np.float32 and np.array_equal(fast, slow)


@pytest.mark.parametrize("style", ["stipple", "engrave", "cbn", "line"])
def test_whole_photo_page_same(monkeypatch, style):
    """A made-up photo through every step to the page's drawing calls, with and without the module."""
    from inkapp.benchmark import made_up_photo
    from inkengine import cbn
    from inkengine.page import Settings
    pic = made_up_photo(480, 360, seed=11)
    s = Settings(mode="convert", style=style, paper="letter", dpi=100)
    box = Box(50, 50, 750, 1000)

    def ops():
        photo.clear_cache()
        ctx = RecordingCanvas()
        e = photo.convert(ctx, box, 100, s, pic)
        return ctx.ops, None if e.grey is None else e.grey.tobytes()
    fast = ops()
    monkeypatch.setattr(photo, "inkline_fast", None)
    monkeypatch.setattr(cbn, "inkline_fast", None)
    slow = ops()
    photo.clear_cache()
    assert fast == slow and (len(slow[0]) > 20 or 0 in slow[1])   # line drawing is one image of black and white


def test_new_functions_reject_wrong_sizes():
    f, b = np.zeros(10, np.float32), np.ones(10, np.uint8)
    with pytest.raises(ValueError):
        inkline_fast.stipple_sites(f, b, 4, 4, False, photo._STIPPLE_F32)
    with pytest.raises(ValueError):
        inkline_fast.stipple_sites(f, b, 5, 2, False, np.zeros(10, np.float32))
    with pytest.raises(ValueError):
        inkline_fast.engrave_band(f, b, 4, 4, False, 0, 4, 2)
    with pytest.raises(ValueError):
        inkline_fast.engrave_band(f, b, 5, 2, False, 0, 0, 2)
    with pytest.raises(ValueError):
        inkline_fast.gauss_blur(f, 4, 4, np.ones(3))
    with pytest.raises(ValueError):
        inkline_fast.gauss_blur(f, 5, 2, np.ones(4))
    with pytest.raises(ValueError):
        inkline_fast.despeckle(bytes(10), 4, 4, 3)
    with pytest.raises(ValueError):
        inkline_fast.chamfer(f, 4, 4)
