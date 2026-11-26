"""How long things take: `inkline.py --benchmark [OUT.json] [--runs N] [--dpi D] [--patterns a,b] [--no-startup]`.

No window is shown. It times:

  start-up   importing PySide6's widgets, importing inkengine and inkapp.window, building the window (offscreen),
             each in a fresh Python process, as a real start would be
  patterns   every pattern drawn as one US Letter page (default settings, a fixed seed, complexity 5), rasterised
             and saved as PNG in memory; and the same page written as a vector PDF
  photos     a few photo styles on a made-up 2000 x 1500 picture (a gradient with noise), uncached each run
  booklet    a 30-page booklet of one fast pattern, as a PDF

Each item is the median of N runs (3 by default), in seconds. It prints a table, slowest first, and with OUT.json
also writes the numbers and what machine they came from. docs/performance.md says what the numbers mean.
"""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 20261117
PHOTO_STYLES = ["fs", "atkinson", "halftone", "engrave", "stipple", "line", "cbn"]
BOOKLET_GEN = "sudoku"   # fast, and every page different
BOOKLET_PAGES = 30

# One fresh interpreter per run: imports are only slow the first time in a process.
_STARTUP = r"""
import os, sys, time
sys.path.insert(0, sys.argv[1])
t = time.perf_counter()
from PySide6.QtWidgets import QApplication
t1 = time.perf_counter()
import inkengine.page, inkengine.output, inkengine.patterns
import inkapp.window
t2 = time.perf_counter()
app = QApplication([])
from inkapp import theme
theme.apply(app, dark=False)
win = inkapp.window.Window("benchmark", remember=False)
app.processEvents()
t3 = time.perf_counter()
print("BENCH", t1 - t, t2 - t1, t3 - t2)
"""
STARTUP_ITEMS = ["import PySide6.QtWidgets", "import inkengine + inkapp.window", "build the window"]


def median_time(fn, runs):
    """fn timed `runs` times: (median, every run), in seconds."""
    times = []
    for _ in range(max(1, runs)):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return statistics.median(times), times


def startup_times(runs):
    """{item: [seconds per run]} for the three start-up pieces, each run in a fresh process."""
    out = {k: [] for k in STARTUP_ITEMS}
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    with tempfile.TemporaryDirectory() as cfg:
        env["INKLINE_CONFIG_DIR"] = cfg   # never the person's own settings
        for _ in range(max(1, runs)):
            r = subprocess.run([sys.executable, "-c", _STARTUP, HERE], env=env, capture_output=True, text=True,
                               timeout=300)
            line = next((ln for ln in r.stdout.splitlines() if ln.startswith("BENCH ")), None)
            if r.returncode or line is None:
                raise RuntimeError(f"start-up run failed: {r.stderr.strip()[-500:]}")
            for k, v in zip(STARTUP_ITEMS, line.split()[1:]):
                out[k].append(float(v))
    return out


def made_up_photo(w=2000, h=1500, seed=SEED):
    """A made-up photo: a diagonal gradient, a soft circle and noise, so every style has something to do."""
    import numpy as np
    from PySide6.QtGui import QImage
    from inkengine import photo
    from inkengine.qt import ensure_app
    ensure_app()
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 255 * (x / w * 0.6 + y / h * 0.4)
    v -= 90 * np.exp(-(((x - w * 0.6) / (w * 0.2)) ** 2 + ((y - h * 0.45) / (h * 0.25)) ** 2))
    v += rng.normal(0, 18, (h, w))
    g = np.clip(v, 0, 255).astype(np.uint8)
    argb = np.empty((h, w, 4), np.uint8)   # QImage ARGB32 is B, G, R, A in memory on little-endian machines
    argb[..., 0] = g
    argb[..., 1] = np.clip(g.astype(np.int16) + 20, 0, 255)
    argb[..., 2] = np.clip(g.astype(np.int16) - 20, 0, 255)
    argb[..., 3] = 255
    img = QImage(argb.data, w, h, w * 4, QImage.Format.Format_ARGB32).copy()   # copy: own the pixels
    return photo.Photo(img, name="benchmark")


def _png_bytes(img):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    if not img.save(buf, "PNG"):
        raise RuntimeError("couldn't encode PNG")
    buf.close()
    return data.size()


def run(runs=3, dpi=300, patterns=None, photo_styles=None, booklet_pages=BOOKLET_PAGES, startup=True, pdf=True,
        log=print):
    """Time everything; returns {"machine": {...}, "settings": {...}, "results": [{name, group, seconds, runs}]}.
    patterns None means every pattern; photo_styles None means PHOTO_STYLES ([] for none); booklet_pages 0 skips it."""
    from inkengine import output, photo
    from PySide6.QtGui import QImage
    from inkengine.page import Settings, geometry, single_page
    from inkengine.patterns import GENERATORS
    from inkengine.qt import ensure_app
    ensure_app()
    results = []

    def add(name, group, med, times):
        results.append({"name": name, "group": group, "seconds": round(med, 4), "runs": [round(t, 4) for t in times]})
        log(f"  {med:8.3f} s  {name}")

    if startup:
        if getattr(sys, "frozen", False):
            log("start-up: skipped (a packaged copy can't start a plain Python)")
        else:
            for k, times in startup_times(runs).items():
                add(k, "startup", statistics.median(times), times)

    with tempfile.TemporaryDirectory(prefix="inkline-bench-") as tmp:
        if patterns is None or patterns:   # the floor under every page: a blank sheet, filled and saved as PNG
            g = geometry(Settings(paper="letter", dpi=dpi))

            def blank():
                img = QImage(g.W, g.H, QImage.Format.Format_RGB32)
                img.fill(0xFFFFFF)
                _png_bytes(img)
            med, times = median_time(blank, runs)
            add("page: blank sheet (fill + PNG only)", "pattern", med, times)
        for gen in (patterns if patterns is not None else list(GENERATORS)):
            s = Settings(gen=gen, seed=SEED, complexity=5, paper="letter", dpi=dpi)
            med, times = median_time(lambda: _png_bytes(output.render_image(s)), runs)
            add(f"page: {gen}", "pattern", med, times)
            if pdf:
                path = os.path.join(tmp, f"{gen}.pdf")
                med, times = median_time(lambda: output.write_pdf(path, s), runs)
                add(f"pdf: {gen}", "pdf", med, times)

        styles = PHOTO_STYLES if photo_styles is None else photo_styles
        if styles:
            pic = made_up_photo()
            for style in styles:
                s = Settings(mode="convert", style=style, paper="letter", dpi=dpi)

                def once():
                    photo.clear_cache()   # the real conversion every time, not the cached one
                    _png_bytes(output.render_image(s, single_page(s, pic)))
                med, times = median_time(once, runs)
                add(f"photo: {style}", "photo", med, times)
            photo.clear_cache()

        if booklet_pages:
            s = Settings(gen=BOOKLET_GEN, seed=SEED, complexity=5, paper="letter", dpi=dpi, pages=booklet_pages)
            path = os.path.join(tmp, "booklet.pdf")
            med, times = median_time(lambda: output.write_book_pdf(path, s), runs)
            add(f"booklet: {booklet_pages} pages of {BOOKLET_GEN} (PDF)", "booklet", med, times)
    return {"machine": machine(), "settings": {"runs": runs, "dpi": dpi, "seed": SEED, "complexity": 5,
                                               "paper": "letter"}, "results": results}


def machine():
    import numpy
    import PySide6
    from PySide6.QtCore import qVersion
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            version = f.read().strip()
    except OSError:
        version = "dev"
    from inkengine.patterns import contour
    return {"inkline": version, "platform": platform.platform(), "system": platform.system(),
            "machine": platform.machine(), "processor": platform.processor(), "python": platform.python_version(),
            "pyside6": PySide6.__version__, "qt": qVersion(), "numpy": numpy.__version__, "cpu_count": os.cpu_count(),
            "inkline_fast": getattr(contour, "inkline_fast", None) is not None}


def table(report):
    """The results as a plain-text table, slowest first."""
    rows = sorted(report["results"], key=lambda r: -r["seconds"])
    width = max([len(r["name"]) for r in rows] + [4])
    lines = [f"{'item':<{width}}  {'median s':>9}  runs", "-" * (width + 24)]
    lines += [f"{r['name']:<{width}}  {r['seconds']:9.3f}  {' '.join(f'{t:.3f}' for t in r['runs'])}" for r in rows]
    total = sum(r["seconds"] for r in rows)
    lines.append("-" * (width + 24))
    lines.append(f"{'total of medians':<{width}}  {total:9.3f}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="inkline.py --benchmark", description="Time start-up, every pattern and photos.")
    ap.add_argument("out", nargs="?", help="write the results as JSON here")
    ap.add_argument("--runs", type=int, default=3, help="runs per item; the median is reported (default 3)")
    ap.add_argument("--dpi", type=int, default=300, help="page resolution (default 300)")
    ap.add_argument("--patterns", help="comma-separated patterns to time (default: all)")
    ap.add_argument("--no-startup", action="store_true", help="skip the start-up timings")
    a = ap.parse_args(argv)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pats = [p.strip() for p in a.patterns.split(",") if p.strip()] if a.patterns else None
    from inkengine.patterns import GENERATORS
    bad = [p for p in pats or [] if p not in GENERATORS]
    if bad:
        ap.error(f"unknown pattern(s): {', '.join(bad)}")
    m = machine()
    print(f"Inkline {m['inkline']} benchmark: {m['platform']}, {m['cpu_count']} CPUs, Python {m['python']}, "
          f"Qt {m['qt']}, inkline_fast {'on' if m['inkline_fast'] else 'off'}; median of {a.runs} run(s) at {a.dpi} dpi")
    report = run(runs=a.runs, dpi=a.dpi, patterns=pats, startup=not a.no_startup)
    print()
    print(table(report))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print(f"\nwrote {a.out}")
    return 0
