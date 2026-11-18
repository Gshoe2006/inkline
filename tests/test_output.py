import xml.etree.ElementTree as ET

from PySide6.QtGui import QImage
from PySide6.QtPdf import QPdfDocument

from inkengine import output
from inkengine.page import PageSpec, Settings, answer_page, single_page
from inkengine.qt import ensure_app


def test_png_is_true_paper_size(tmp_path):
    ensure_app()
    s = Settings(paper="a4", dpi=150, title="Maze time", name_line=True)
    output.write_png(tmp_path / "m.png", s)
    img = QImage(str(tmp_path / "m.png"))
    assert (img.width(), img.height()) == (1241, 1754)        # 8.27 x 11.69 in at 150 dpi
    assert round(img.dotsPerMeterX() * 0.0254) == 150


def test_pdf_has_puzzle_and_answer_pages(tmp_path):
    ensure_app()
    s = Settings(maze_shape="heart", seed=5)
    puzzle = single_page(s)
    key = answer_page([PageSpec(gen="maze", seed=5, c=s.complexity, label="Maze 1")])
    output.write_pdf(tmp_path / "m.pdf", s, [puzzle, key])
    doc = QPdfDocument()
    doc.load(str(tmp_path / "m.pdf"))
    assert doc.pageCount() == 2
    size = doc.pagePointSize(0)
    assert (round(size.width()), round(size.height())) == (612, 792)   # Letter, in points


def test_landscape_pdf(tmp_path):
    ensure_app()
    output.write_pdf(tmp_path / "l.pdf", Settings(orient="landscape"))
    doc = QPdfDocument()
    doc.load(str(tmp_path / "l.pdf"))
    size = doc.pagePointSize(0)
    assert (round(size.width()), round(size.height())) == (792, 612)


def test_svg_is_vector_at_paper_size(tmp_path):
    s = Settings(maze_shape="star", frame=True, title="Star maze")
    output.write_svg(tmp_path / "m.svg", s)
    root = ET.parse(tmp_path / "m.svg").getroot()
    assert (root.get("width"), root.get("height"), root.get("viewBox")) == ("8.5in", "11in", "0 0 2550 3300")
    ns = "{http://www.w3.org/2000/svg}"
    assert len(list(root.iter(ns + "path"))) >= 1 and len(list(root.iter(ns + "rect"))) == 1
    assert next(root.iter(ns + "text")).text == "Star maze"


def test_svg_draws_every_wall_the_recording_does():
    """The SVG back end writes out each move the maze makes: same seed, same number of wall strokes."""
    from inkengine.canvas import RecordingCanvas
    from inkengine.page import draw_page, geometry
    s = Settings(seed=314)
    rec = RecordingCanvas()
    draw_page(rec, geometry(s), single_page(s), s)
    root = ET.fromstring(output.svg_text(s))
    moves = sum(p.get("d").count("M") for p in root.iter("{http://www.w3.org/2000/svg}path"))
    assert moves == sum(1 for o in rec.ops if o[0] == "M") > 500


def test_settings_read_2x_names():
    s = Settings.from_dict({"mazeShape": "fish", "nameLine": True, "complexity": 7, "style": "dither"})
    assert (s.maze_shape, s.name_line, s.complexity) == ("fish", True, 7)


def test_svg_clips_woven_tiles_to_the_design_box():
    """Edge tiles are cut off by a clip path round the design box, like the PNG and PDF."""
    s = Settings(gen="truchet", seed=3, frame=True)
    root = ET.fromstring(output.svg_text(s))
    ns = "{http://www.w3.org/2000/svg}"
    clip = next(root.iter(ns + "clipPath"))
    group = next(g for g in root.iter(ns + "g") if g.get("clip-path") == f"url(#{clip.get('id')})")
    assert len(list(group.iter(ns + "path"))) == 1          # all the arcs, inside the clip


def test_name_page_pdf_keeps_its_outline(tmp_path):
    """The white fill of bubble letters must not eat into the black outline in a PDF."""
    import shutil
    import subprocess
    import pytest
    if not shutil.which("pdftoppm"):
        pytest.skip("needs pdftoppm (poppler-utils)")
    ensure_app()
    s = Settings(gen="name", name_text="Maya", seed=1, dpi=150)
    output.write_pdf(tmp_path / "n.pdf", s)
    output.write_png(tmp_path / "n.png", s)
    subprocess.run(["pdftoppm", "-r", "150", "-png", "-singlefile", str(tmp_path / "n.pdf"), str(tmp_path / "p")], check=True)
    dark = lambda img: sum(img.pixelColor(x, y).lightness() < 128 for y in range(0, img.height(), 2) for x in range(0, img.width(), 2))
    png, pdf = dark(QImage(str(tmp_path / "n.png"))), dark(QImage(str(tmp_path / "p.png")))
    assert png > 1000 and abs(pdf - png) < 0.1 * png
