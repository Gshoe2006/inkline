"""PDFs with text come out the same every run, with the weight each piece of text asks for embedded.

Qt seeds its hash tables randomly per process, and its PDF engine wrote a document's fonts in hash
order, so the same page embedded its weights in a different order (different object numbers and subset
tags) each run. That only shows across processes, so each render here runs in a fresh one.
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Draws text in several weights onto one PDF page through the engine's own QtCanvas, plus one PDF per
# weight for regular and bold, and reports what it wrote and which font Qt matched for each weight.
RENDER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtGui import QFontInfo, QPainter, QPdfWriter
from inkengine.canvas import QtCanvas
from inkengine.qt import ensure_app, make_font
ensure_app()
out = sys.argv[2]

def page(path, weights):
    pdf = QPdfWriter(path)
    pdf.setResolution(300)
    p = QPainter(pdf)
    ctx = QtCanvas(p, 2550, 3300)
    ctx.fill_style = "#000"
    for i, w in enumerate(weights):
        ctx.set_font(60, w)
        ctx.fill_text(f"Weight {w} text 0123", 200, 300 + 150 * i)
    p.end()

page(out + "/mixed.pdf", [400, 500, 600, 700, 900, 400, 700])
matched = {}
for w in (400, 700):
    page(out + f"/w{w}.pdf", [w])
    fi = QFontInfo(make_font(60, w))
    matched[w] = {"family": fi.family(), "style": fi.styleName(), "weight": fi.weight()}
print(json.dumps(matched))
"""

FONT_NAME = re.compile(rb"/FontName\s*/([A-Z]{6})\+([^\s/>\]]+)")


def render(tmp_path, n):
    out = tmp_path / f"run{n}"
    out.mkdir()
    env = {k: v for k, v in os.environ.items() if k != "QT_HASH_SEED"}
    env["QT_QPA_PLATFORM"] = "offscreen"
    r = subprocess.run([sys.executable, "-c", RENDER, ROOT, str(out)], env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    matched = json.loads(r.stdout.strip().splitlines()[-1])
    return out, {int(w): m for w, m in matched.items()}


def fonts(path):
    """The (subset tag, PostScript name) of every embedded font, in file order."""
    return [(t.decode(), n.decode()) for t, n in FONT_NAME.findall(path.read_bytes())]


def without_dates_and_ids(data):
    data = re.sub(rb"/(CreationDate|ModDate)\s*\(D:[^)]*\)", rb"/\1()", data)
    data = re.sub(rb"/ID\s*\[[^\]]*\]", b"/ID[]", data)
    data = re.sub(rb'xmp:(CreateDate|ModifyDate|MetadataDate)="[^"]*"', rb'xmp:\1=""', data)
    return re.sub(rb"uuid:[0-9a-fA-F-]+", b"uuid:", data)


def style_weight(ps_name):
    """The CSS weight a PostScript name's style part says (Inter-SemiBold -> 600, DejaVuSans -> 400)."""
    style = ps_name.rpartition("-")[2].lower() if "-" in ps_name else ""
    style = style.replace("italic", "").replace("oblique", "")
    return {"": 400, "regular": 400, "book": 400, "roman": 400, "normal": 400, "thin": 100,
            "extralight": 200, "ultralight": 200, "light": 300, "medium": 500, "semibold": 600,
            "demibold": 600, "bold": 700, "extrabold": 800, "ultrabold": 800, "black": 900,
            "heavy": 900}.get(style)


def test_pdf_fonts_are_the_same_every_run_and_the_weight_asked_for(tmp_path):
    runs = [render(tmp_path, n) for n in range(3)]

    first = fonts(runs[0][0] / "mixed.pdf")
    assert len(first) >= 2, f"expected several weights embedded, got {first}"
    for out, _ in runs[1:]:
        assert fonts(out / "mixed.pdf") == first
        for name in ("mixed.pdf", "w400.pdf", "w700.pdf"):
            assert without_dates_and_ids((out / name).read_bytes()) == \
                without_dates_and_ids((runs[0][0] / name).read_bytes()), f"{name} differs between runs"

    out, matched = runs[0]
    for w in (400, 700):
        embedded = fonts(out / f"w{w}.pdf")
        assert len(embedded) == 1, f"{w}: {embedded}"
        name = embedded[0][1]
        assert style_weight(name) == w, f"asked for {w}, embedded {name} (Qt matched {matched[w]})"
        assert matched[w]["family"].replace(" ", "") in name, f"embedded {name}, Qt matched {matched[w]}"
