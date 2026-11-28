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
PATTERNS = ["mandala", "maze", "truchet", "contour", "flow", "dots", "sudoku", "words", "nonogram", "spot", "kakuro",
            "maths", "trace", "crossword", "clock", "scramble", "spelltest", "fractions", "symmetry", "ruled", "reward", "reading", "bingo", "early",
            "logic", "cryptogram", "ladder", "calendar", "lscwc", "speed", "drawread", "coords", "memory"]


def _silhouette():
    """A photo of one dark shape (a cat's head) on a pale background, for the photo dot-to-dot."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF
    from inkengine.photo import Photo
    img = QImage(1200, 900, QImage.Format.Format_ARGB32)
    img.fill(QColor("#e8e2d6"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QColor("#2a2a2a"))
    p.setBrush(QColor("#2a2a2a"))
    p.drawEllipse(QPointF(600, 520), 270, 240)
    for ear in ([(370, 420), (400, 120), (560, 300)], [(830, 420), (800, 120), (640, 300)]):
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in ear]))
    p.end()
    return Photo(img, name="cat.png")


EXPECT_FAST_ENV = "INKLINE_EXPECT_FAST"   # set to 1 by the release for the packages that ship inkline_fast


def fast_module_status():
    """"yes (<where>)" when the optional Rust module inkline_fast is loaded by the engine and gives the Python code's
    answer on a small picture; "no (<why>)" otherwise. Inkline works either way: without it, only slower."""
    import numpy as np
    from inkengine import cbn
    try:
        import inkline_fast
    except ImportError as e:
        return f"no ({e})"
    if photo.inkline_fast is None or cbn.inkline_fast is None:
        return "no (installed, but the engine didn't load it)"
    try:   # one real call each way: an extension that imports but can't run (numpy too old or new) shows here
        rng = np.random.default_rng(1)
        lum = (rng.random(40 * 30) * 255).astype(np.float32)
        mask = np.ones(40 * 30, np.uint8)
        fast = photo._error_diffusion(lum, mask, 40, 30, 128, False)
        e = photo.Conversion(40, 30, lum, mask)
        sites = photo.stipple_sites(e, False)
        photo.inkline_fast = None
        try:
            slow = photo._error_diffusion(lum, mask, 40, 30, 128, False)
            slow_sites = photo.stipple_sites(photo.Conversion(40, 30, lum, mask), False)
        finally:
            photo.inkline_fast = inkline_fast
        if fast != slow or sites != slow_sites:
            return "no (loaded, but it gave different results from the Python code)"
    except Exception as e:   # noqa: BLE001 — reported, not raised: the caller decides whether it matters
        return f"no (loaded, but failed: {e})"
    return f"yes ({getattr(inkline_fast, '__file__', None) or 'built in'})"


def check_fast_module(outdir, env=None):
    """Write whether inkline_fast works to inkline-fast.txt. Only informational, unless INKLINE_EXPECT_FAST=1 (the
    release sets it for each package that ships the module): then a package without a working one fails."""
    env = os.environ if env is None else env
    found = fast_module_status()
    with open(os.path.join(outdir, "inkline-fast.txt"), "w", encoding="utf-8") as f:
        f.write(found + "\n")
    print(f"selftest: inkline_fast: {found}")
    if env.get(EXPECT_FAST_ENV) == "1" and not found.startswith("yes"):
        raise RuntimeError(f"this package should ship the Rust module inkline_fast ({EXPECT_FAST_ENV}=1): {found}")
    return found


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
    step("battleships", lambda: page("battleships", replace(base, gen="coords", coord_kind="battle")))

    def memorybacks():   # cards, then their backs: two pages
        n = _pdf(os.path.join(outdir, "memorybacks.pdf"), State(replace(base, gen="memory", memory_backs=True)))
        if n != 2:
            raise RuntimeError(f"the memory cards have {n} pages, expected 2 (the cards and their backs)")
    step("memorybacks", memorybacks)
    photo_s = replace(base, mode="convert")
    step("convert", lambda: page("convert", replace(photo_s, style="fs"), sample, svg=False))
    for style in ("engrave", "stipple", "cbn"):
        step(style, lambda style=style: page(style, replace(photo_s, style=style), sample))
    step("nonophoto", lambda: page("nonophoto", replace(photo_s, style="nono"), sample))
    # a dot-to-dot needs a photo with one clear shape in it (the sample is a landscape): a cat's head on a pale wall
    step("dotsphoto", lambda: page("dotsphoto", replace(photo_s, style="dots"), _silhouette()))

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

    def install_kind():   # how this package says it was installed: what Help → Check for updates goes by
        from . import updater
        with open(os.path.join(outdir, "install-kind.txt"), "w", encoding="utf-8") as f:
            f.write(updater.install_kind() + "\n")
    step("install kind", install_kind)

    step("inkline_fast", lambda: check_fast_module(outdir))

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
