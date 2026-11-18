"""Posters against recordings of index.html's posterGeom and drawSheet (tests/fixtures/poster_js.json.gz)."""

import xml.etree.ElementTree as ET

import pytest
from recording import load_fixture, same_ops

from inkengine import output, poster
from inkengine.canvas import RecordingCanvas
from inkengine.page import Settings, single_page

CASES = load_fixture("poster")


def settings(k):
    return Settings(gen=k["gen"], poster=True, grid=k["grid"], overlap=float(k["overlap"]), title=k["title"],
                    name_line=k["nameLine"], seed=k["seed"], complexity=k["c"])


@pytest.mark.parametrize("k", CASES, ids=lambda k: f"{k['gen']}-{k['grid']}-overlap{k['overlap']}")
def test_geometry_and_sheets_match_javascript(k):
    s = settings(k)
    P = poster.poster_geometry(s)
    want = k["P"]
    assert (P.w, P.h, P.W, P.H) == (want["w"], want["h"], want["W"], want["H"])
    assert tuple(P.box) == (want["box"]["x"], want["box"]["y"], want["box"]["w"], want["box"]["h"])
    assert P.scale == pytest.approx(want["scale"], abs=1e-4)
    for i, ops in ((0, k["first"]), (P.sheets - 1, k["last"])):
        ctx = RecordingCanvas(em_per_char=0.55)
        ctx.line_width = 8
        poster.draw_sheet(ctx, s, P, single_page(s), i)
        same_ops(ctx.ops, ops)


def test_recordings_cover_overlaps_and_grids():
    assert {k["overlap"] for k in CASES} == {"0", "0.25", "0.5"}
    assert len({k["grid"] for k in CASES}) == len(CASES)


def test_sheets_tile_the_poster_with_the_overlap():
    s = Settings(poster=True, grid="3x2", overlap=0.5)
    P = poster.poster_geometry(s)
    rects = [poster.sheet_rect(P, i)[2] for i in range(P.sheets)]
    assert rects[0].x == 0 and rects[-1].x + rects[-1].w == pytest.approx(P.W, abs=1)
    assert rects[-1].y + rects[-1].h == pytest.approx(P.H, abs=1)
    assert rects[0].x + rects[0].w - rects[1].x == pytest.approx(0.5 * P.dpi)     # neighbours share the overlap
    assert [poster.sheet_label(P, i).split()[1] for i in range(6)] == ["A1", "A2", "A3", "B1", "B2", "B3"]


def test_size_note():
    assert poster.size_note(Settings(grid="2x2", overlap=0.25)) == "Finished poster: 14.75 × 19.75 in, from 4 Letter sheets."
    assert poster.size_note(Settings(grid="1x2", overlap=0, paper="a4")) == "Finished poster: 7.27 × 21.38 in, from 2 A4 sheets."


def test_poster_pdf_and_svg(tmp_path):
    from PySide6.QtPdf import QPdfDocument
    from inkengine.qt import ensure_app
    ensure_app()
    s = Settings(gen="mandala", poster=True, grid="2x3", overlap=0.25, dpi=150)
    assert output.write_poster_pdf(tmp_path / "p.pdf", s) == 6
    doc = QPdfDocument()
    doc.load(str(tmp_path / "p.pdf"))
    size = doc.pagePointSize(0)
    assert doc.pageCount() == 6 and (round(size.width()), round(size.height())) == (612, 792)
    root = ET.fromstring(output.svg_text(s))      # the SVG is the whole poster, at its finished size
    assert (root.get("width"), root.get("height")) == ("14.75in", "29.5in")   # 3 x 10 in, less two 1/4 in overlaps
