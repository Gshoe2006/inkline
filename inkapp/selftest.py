"""Headless self-test: `inkline.py --selftest DIR`.

Opens the window (offscreen in CI) and waits for its first preview, then writes every pattern, the
photo styles, the printer test page, a booklet (plain and folded), two posters and a photo book as
PNG, PDF and SVG through the same code Save and Print use. packaging/check_selftest.py then checks
the files. Exits 0 when every step worked, 1 otherwise. A fixed seed makes every run's output the same.
"""

import os
import sys
import time
import traceback
from dataclasses import replace

from PySide6.QtGui import QColor, QImage, QPainter, QPdfWriter

from inkengine import output, photo
from inkengine.page import Settings, single_page

from . import jobs
from .sample import sample_photo
from .state import State

SEED = 20261117
PATTERNS = ["mandala", "maze", "truchet", "contour", "flow", "dots", "sudoku", "words", "nonogram", "spot"]


def _pdf(path, state):
    j = jobs.job(state)
    dev = QPdfWriter(path)
    dev.setPageLayout(jobs.page_layout(state.settings, j.orient))
    dev.setResolution(j.geometry.dpi)
    dev.setTitle(j.name)
    dev.setCreator("Inkline")
    if not jobs.run(j, dev):
        raise RuntimeError(f"{os.path.basename(path)} couldn't be written")
    return j.count


def run(window, outdir, app):
    os.makedirs(outdir, exist_ok=True)
    fails = []

    def step(name, fn):
        try:
            fn()
            print(f"selftest: ok {name}")
        except Exception as e:   # noqa: BLE001 — every failure is reported, then the run goes on
            traceback.print_exc()
            fails.append(f"{name}: {e}")
            print(f"selftest: FAIL {name}: {e}")

    # the window starts and draws its first preview
    def first_preview():
        end = time.time() + 60
        while window.preview.page.image is None and time.time() < end:
            app.processEvents()
            time.sleep(0.02)
        if window.preview.page.image is None:
            raise RuntimeError("the window never drew its preview")
    step("window", first_preview)

    sample = sample_photo()
    base = Settings(seed=SEED)

    def page(name, s, pic=None, svg=True):
        st = State(s, [pic] if pic else [], 0, 0)
        spec = single_page(s, pic)
        output.write_png(os.path.join(outdir, f"{name}.png"), s, spec)
        _pdf(os.path.join(outdir, f"{name}.pdf"), st)
        if svg:
            output.write_svg(os.path.join(outdir, f"{name}.svg"), s, spec)

    for gen in PATTERNS:
        step(gen, lambda gen=gen: page(gen, replace(base, gen=gen)))
    step("mazeshape", lambda: page("mazeshape", replace(base, gen="maze", maze_shape="word", maze_word="Inkline")))
    step("name", lambda: page("name", replace(base, gen="name", name_text="Inkline 3.0", name_bg="flow")))
    step("cbnpattern", lambda: page("cbnpattern", replace(base, gen="mandala", cbn=True)))
    photo_s = replace(base, mode="convert")
    step("convert", lambda: page("convert", replace(photo_s, style="fs"), sample, svg=False))
    for style in ("engrave", "stipple", "cbn"):
        step(style, lambda style=style: page(style, replace(photo_s, style=style), sample))
    step("nonophoto", lambda: page("nonophoto", replace(photo_s, style="nono"), sample))

    def testpage():
        s = replace(base, testpage=True)
        st = State(s)
        img, _ = jobs.png(st)
        img.save(os.path.join(outdir, "testpage.png"), "PNG")
        _pdf(os.path.join(outdir, "testpage.pdf"), st)
    step("testpage", testpage)

    booklet = replace(base, gen="maze", booklet=True, pages=6, title="Rainy Day Mazes", name_line=True)

    def book():
        n = _pdf(os.path.join(outdir, "booklet.pdf"), State(booklet))
        if n != 9:
            raise RuntimeError(f"the booklet has {n} pages, expected 9")
        st = State(booklet, page=999)   # the last page: answers
        text, _name = jobs.svg(st)
        if "<path" not in text:
            raise RuntimeError("the answer page's SVG is empty")
        with open(os.path.join(outdir, "answers.svg"), "w", encoding="utf-8") as f:
            f.write(text)
        _pdf(os.path.join(outdir, "booklet-fold.pdf"), State(replace(booklet, fold=True)))
    step("booklet", book)
    step("poster mandala 2x2", lambda: _pdf(os.path.join(outdir, "poster-mandala-2x2.pdf"),
                                            State(replace(base, gen="mandala", poster=True, grid="2x2"))))
    step("poster photo 3x3", lambda: _pdf(os.path.join(outdir, "poster-photo-3x3.pdf"),
                                          State(replace(photo_s, style="fs", poster=True, grid="3x3"), [sample])))

    def photo_book():
        circle = QImage(600, 800, QImage.Format.Format_ARGB32)
        circle.fill(QColor("#fff"))
        p = QPainter(circle)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#222"))
        p.drawEllipse(100, 200, 400, 400)
        p.end()
        turned = replace(sample_photo(), rot=90, zoom=180)
        photos = [photo.Photo(circle, name="circle.png"), sample, turned]
        st = State(replace(photo_s, style="line", photobook=True, title="Photo book test"), photos)
        n = _pdf(os.path.join(outdir, "photobook.pdf"), st)
        if n != 4:
            raise RuntimeError(f"the photo book has {n} pages, expected 4")
    step("photo book", photo_book)

    if fails:
        print(f"selftest: {len(fails)} failure(s)")
        for f in fails:
            print(f"  - {f}")
    print("selftest: done" if not fails else "selftest: FAILED")
    return 1 if fails else 0


def main(outdir):
    from PySide6.QtWidgets import QApplication
    from . import theme
    from .window import Window
    app = QApplication.instance() or QApplication(sys.argv)
    theme.apply(app, dark=False)
    win = Window("selftest", remember=False)
    win.show()
    return run(win, outdir, app)
