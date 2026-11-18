"""Photo styles against recordings of index.html (tests/fixtures/photo_js.json.gz, nonopic_js.json.gz).

The recordings hold the JavaScript's own work image (the cropped photo, one pixel per dot), so the
comparison starts from identical pixels: tones must match to the bit, dithers pixel for pixel, and
the halftone, engraving, stippling and nonogram drawings step for step.
"""

import base64

import numpy as np
import pytest
from recording import load_fixture, same_ops

from inkengine import photo
from inkengine.box import Box
from inkengine.canvas import RecordingCanvas
from inkengine.patterns import nonogram

CASES = load_fixture("photo")
PICS = load_fixture("nonopic")


def ident(k):
    return f"{k['style']}-br{k['brightness']}-ct{k['contrast']}-t{k['threshold']}{'-inv' if k['invert'] else ''}-dot{k['dot']}-{k['fit']}"


def run(k):
    rgba = np.frombuffer(base64.b64decode(k["rgba"]), np.uint8)
    p = dict(k["p"])
    return photo.process_pixels(rgba, k["ww"], k["wh"], p)


@pytest.mark.parametrize("k", CASES, ids=ident)
def test_tones_and_mask_match_javascript(k):
    r = run(k)
    want = np.frombuffer(base64.b64decode(k["lum"]), np.float32)
    assert np.array_equal(r["lum"], want)
    assert "".join(map(str, r["mask"].tolist())) == k["mask"]


@pytest.mark.parametrize("k", [k for k in CASES if k["bits"]], ids=ident)
def test_dithers_match_javascript_pixel_for_pixel(k):
    r = run(k)
    got = "".join("1" if v else "0" for v in r["grey"].tolist())
    differ = sum(a != b for a, b in zip(got, k["bits"]))
    assert differ == 0, f"{differ} of {len(got)} pixels differ"


@pytest.mark.parametrize("k", [k for k in CASES if k["style"] in ("halftone", "engrave", "stipple", "nono")], ids=ident)
def test_drawn_styles_match_javascript(k):
    r = run(k)
    e = photo.Conversion(k["ww"], k["wh"], r["lum"], r["mask"], r["grey"], r["nono"])
    box, inv = Box(**k["box"]), k["invert"]
    ctx = RecordingCanvas()
    ctx.line_width = 8
    if k["style"] == "halftone":
        photo._draw_halftone(ctx, box, e, inv, None)
    elif k["style"] == "engrave":
        photo._draw_engraving(ctx, box, e, inv, None)
    elif k["style"] == "stipple":
        photo._draw_stipple(ctx, box, e, inv, None)
    else:
        n = k["nono"]
        assert (e.nono["w"], e.nono["h"], e.nono["flips"]) == (n["w"], n["h"], n["flips"])
        assert "".join(map(str, e.nono["pic"])) == n["pic"] and e.nono["rows"] == n["rows"] and e.nono["cols"] == n["cols"]
        nonogram.draw_nonogram(ctx, box, 300, 8, e.nono, False)
    same_ops(ctx.ops, k["ops"])


def test_recordings_cover_every_style():
    assert {k["style"] for k in CASES} == set(photo.STYLES) - {"cbn"}   # colour by number: tests/test_cbn.py
    assert any(k["nono"] and k["nono"]["flips"] for k in CASES)


@pytest.mark.parametrize("k", PICS, ids=lambda k: f"{k['w']}x{k['h']}-seed{k['seed']}")
def test_nonogram_from_picture_matches_javascript(k):
    pic = [int(c) for c in k["pic"]]
    out = photo.from_picture(pic, k["lum"], k["w"], k["h"], 128)
    want = k["out"]
    assert out["flips"] == want["flips"]
    assert "".join(map(str, out["pic"])) == want["pic"] and out["rows"] == want["rows"] and out["cols"] == want["cols"]
    assert (None if out["givens"] is None else "".join(map(str, out["givens"]))) == want["givens"]
    # and what's printed solves by logic alone
    start = [1 if g else -1 for g in (out["givens"] or [0] * len(pic))]
    assert nonogram.solve(out["rows"], out["cols"], start) == out["pic"]


def test_recordings_include_pre_shaded_squares():
    assert any(k["out"]["givens"] and "1" in k["out"]["givens"] for k in PICS)


def test_tables():
    assert photo.HALFTONE_R[0] == pytest.approx(0, abs=1e-6) and photo.HALFTONE_R[255] == pytest.approx(0.7071, abs=1e-4)
    assert photo.STIPPLE_F[0] == 0 and photo.STIPPLE_F[255] == 1
    assert sorted(v for row in photo.BAYER for v in row) == list(range(64))


def test_work_image_pixels_outlive_the_qimage():
    """conversion_input's pixels must be a copy: a view of the QImage's memory crashed once Qt freed it."""
    from PySide6.QtGui import QColor, QImage
    from inkengine.page import Settings
    from inkengine.qt import ensure_app
    ensure_app()
    img = QImage(64, 48, QImage.Format.Format_ARGB32)
    img.fill(QColor("#808080"))
    ww, wh, data, _p, _o = photo.conversion_input(Box(0, 0, 200, 150), 2, "fs", photo.Photo(img), Settings())
    owner = data if data.base is None else data.base
    assert owner.flags.owndata and (ww, wh) == (100, 75)
    assert int(data.reshape(-1, 4)[:, 3].min()) == 255        # the photo fills it (64x48 is 4:3, like the box)
