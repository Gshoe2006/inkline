"""Colour by number against recordings of index.html (tests/fixtures/cbnphoto_js.json.gz, cbnpattern_js.json.gz).

Photos start from the JavaScript's own work image, so the crayons, regions, numbers, border lines and
the drawn page must all match. Patterns start from the JavaScript's coarse raster of the design (Qt
antialiases the raster a little differently, which is checked separately), and from there the
numbered spaces, the page and its answer page must match step for step.
"""

import base64

import numpy as np
import pytest
from recording import load_fixture, same_ops

from inkengine import cbn, photo
from inkengine.book import book_pages
from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings, design_box, draw_page, geometry

PHOTOS = load_fixture("cbnphoto")


def flat(rows):
    return [v for row in rows for v in row]
PATTERNS = load_fixture("cbnpattern")


def photo_id(k):
    return f"t{k['threshold']}-k{k['k']}-{k['fit']}"


@pytest.fixture(scope="module")
def photo_results():
    out = {}
    for k in PHOTOS:
        rgba = np.frombuffer(base64.b64decode(k["rgba"]), np.uint8)
        out[photo_id(k)] = photo.process_pixels(rgba, k["ww"], k["wh"], dict(k["p"]))
    return out


@pytest.mark.parametrize("k", PHOTOS, ids=photo_id)
def test_photo_regions_match_javascript(k, photo_results):
    r = photo_results[photo_id(k)]
    want = k["cbn"]
    assert r["cbn"]["pal"] == want["pal"]
    assert r["label"] == np.frombuffer(base64.b64decode(k["label"]), np.int32).tolist()
    assert r["cbn"]["colour"] == want["colour"]
    assert len(r["cbn"]["spots"]) == len(want["spots"])
    assert flat(r["cbn"]["spots"]) == pytest.approx(flat(want["spots"]), abs=1e-3)
    assert len(r["cbn"]["lines"]) == len(want["lines"])
    for got, line in zip(r["cbn"]["lines"], want["lines"]):
        assert got == pytest.approx(line, abs=1e-4)


@pytest.mark.parametrize("k", PHOTOS, ids=photo_id)
def test_photo_page_matches_javascript(k, photo_results, monkeypatch):
    r = photo_results[photo_id(k)]
    e = photo.Conversion(k["ww"], k["wh"], r["lum"], r["mask"], None, None, r["cbn"])
    monkeypatch.setattr(photo, "conversion", lambda *a: e)    # the JavaScript's work image, already converted
    s = Settings(mode="convert", style="cbn", pcbn_colours=k["k"], threshold=k["threshold"], dpi=300)
    ctx = RecordingCanvas(em_per_char=0.55)
    ctx.line_width = 8
    photo.convert(ctx, Box(**k["box"]), 300, s, photo.Photo(None))
    same_ops(ctx.ops, k["ops"])


def pattern_settings(k):
    return Settings(gen=k["gen"], seed=k["seed"], complexity=k["c"], cbn=True, cbn_colours=k["k"], name_text=k["text"],
                    name_bg=k["bg"], pages=2, ramp=False, cover=False, mix=False)


def js_raster(k):
    return [-1 if ch == "1" else 0 for ch in k["ink"]], k["w"], k["h"], k["s"]


@pytest.mark.parametrize("k", PATTERNS, ids=lambda k: f"{k['gen']}-{k['seed']}-k{k['k']}")
def test_pattern_spaces_and_pages_match_javascript(k, monkeypatch):
    s = pattern_settings(k)
    g = geometry(s)
    rasters = {k["seed"]: js_raster(k), k["seed2"]: ([-1 if ch == "1" else 0 for ch in k["ink2"]], k["w"], k["h"], k["s"])}
    monkeypatch.setattr(cbn, "pattern_raster", lambda g, box, spec, lw, s: rasters[spec.seed])
    cbn._pattern_cache.clear()
    pages = book_pages(s)
    assert [p.kind for p in pages] == k["kinds"]           # colour-by-number pages get an answer page
    page = pages[0]
    art, _kb = cbn.art_box(design_box(g, page, s), g.dpi, s.cbn_colours)
    assert tuple(art) == pytest.approx((k["art"]["x"], k["art"]["y"], k["art"]["w"], k["art"]["h"]))
    r = cbn.pattern(g, art, page, k["lw"], s)
    assert r["names"] == k["names"]
    assert len(r["spots"]) == len(k["spots"])
    assert flat(r["spots"]) == pytest.approx(flat(k["spots"]), abs=1e-3)
    for spec, want in ((page, k["pageOps"]), (pages[-1], k["answerOps"])):
        ctx = RecordingCanvas(em_per_char=0.55)
        draw_page(ctx, g, spec, s)
        same_ops(ctx.ops, want)
    cbn._pattern_cache.clear()


@pytest.mark.parametrize("k", PATTERNS[:3], ids=lambda k: f"{k['gen']}-{k['seed']}")
def test_qt_raster_agrees_with_chromium(k):
    """Qt draws the design onto the coarse grid with slightly different antialiasing than Chromium."""
    s = pattern_settings(k)
    g = geometry(s)
    page = book_pages(s)[0]
    val, w, h, _ = cbn.pattern_raster(g, Box(**k["art"]), page, k["lw"], s)
    assert (w, h) == (k["w"], k["h"])
    differ = sum((v < 0) != (ch == "1") for v, ch in zip(val, k["ink"]))
    assert differ < 0.02 * w * h, f"{differ} of {w * h} cells differ"


def test_mode_filter_ties_keep_their_own_value():
    val = [0, 0, 1,
           1, 2, 1,
           2, 2, 0]
    assert cbn.mode_filter(val, 3, 3, 3)[4] == 2        # 0, 1 and 2 have three votes each: the centre keeps 2
    val[4] = 1
    assert cbn.mode_filter(val, 3, 3, 3)[4] == 1        # 1 now has four


def test_key_layout():
    assert cbn.key_cols(2250, 300) == 4 and cbn.key_cols(1000, 300) == 3
    assert cbn.key_height(Box(0, 0, 2250, 3000), 300, 8) == pytest.approx(300 * (0.42 + 2 * 0.24))
