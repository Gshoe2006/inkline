# Performance

How long Inkline takes to start, draw a page and convert a photo, how to measure it, and what a trial with Rust
showed. Written for deciding what 8.0 should do about speed.

## Run the benchmark

```sh
python3 inkline.py --benchmark                      # prints a table, slowest first
python3 inkline.py --benchmark out.json --runs 5    # also writes the numbers and the machine's details as JSON
python3 inkline.py --benchmark --patterns contour,maze --no-startup --dpi 150
```

No window is shown. It times:

- **start-up:** importing PySide6's widgets, importing `inkengine` and `inkapp.window`, and building the window
  (offscreen). Each run starts a fresh Python, because imports are only slow the first time.
- **page: _pattern_:** every pattern as one US Letter page at 300 dpi (default settings, a fixed seed, complexity 5),
  drawn onto an image and saved as PNG in memory. This is what a PNG save costs.
- **page: blank sheet:** filling a blank Letter page and saving it as PNG. Every page above includes this cost, so a
  pattern's own drawing is its time minus this one.
- **pdf: _pattern_:** the same page written as a vector PDF.
- **photo: _style_:** six photo styles on a made-up 2000 × 1500 picture (a gradient, a soft circle and noise), on a
  Letter page, with the conversion cache cleared each run.
- **booklet:** a 30-page sudoku booklet as one PDF.

Each item is the median of `--runs` runs (3 by default), in seconds. The code is `inkapp/benchmark.py`.

## In CI

`.github/workflows/benchmark.yml` runs the benchmark on ubuntu-latest (x86-64), ubuntu-24.04-arm, windows-latest and
macos-15, by hand (Actions → Benchmark → Run workflow) and on every push to main that changes `inkengine/`. Each
machine's JSON is kept as an artifact `benchmark-<os>` for 30 days, and the run's summary page shows one table with
every machine side by side (`packaging/benchmark_summary.py`).

Android isn't timed in CI. To time it by hand: install the Android build on a phone, and with a stopwatch time
three times each from tapping the icon to the first preview, saving a contour page as PNG, and saving a photo in the
smooth dither style. Note the phone's model next to the numbers.

## Numbers from this container

Measured on the Linux container this work was done in: 4 CPUs (Intel Xeon, 2.10 GHz), Python 3.13, Qt 6.12.0,
numpy 2.5, offscreen Qt. A shared cloud machine: runs vary by about 10–15%. Median of 3 runs, seconds.

| item | seconds |
|---|---:|
| photo: stipple | 3.80 |
| photo: atkinson | 1.81 |
| photo: cbn | 1.80 |
| photo: engrave | 1.65 |
| photo: fs (smooth dither) | 1.40 |
| build the window | 1.02 |
| page: truchet | 0.75 |
| photo: halftone | 0.67 |
| page: contour | 0.64 |
| photo: line | 0.55 |
| page: spot | 0.44 |
| page: mandala | 0.39 |
| page: flow | 0.35 |
| page: maze | 0.29 |
| booklet: 30 pages of sudoku (PDF) | 0.29 |
| page: blank sheet (fill + PNG only) | 0.22 |
| other 20 patterns, each | 0.16–0.25 |
| import inkengine + inkapp.window | 0.20 |
| pdf: contour | 0.19 |
| pdf: spot | 0.13 |
| import PySide6.QtWidgets | 0.09 |
| pdf: every other pattern | under 0.06 |

What the numbers say:

- **Most pattern pages are fast, and most of their time is the PNG.** A blank page costs 0.22 s to fill and save;
  20 of the 25 patterns take 0.16–0.25 s in all, so their own drawing is a few hundredths of a second. PDFs are
  vector and take under 0.06 s for all but contour and spot.
- **The slowest pattern is slow in Qt, not in Python.** Truchet (0.75 s) spends 0.44 s in one `QPainter.drawPath`
  call. Spot (0.44 s) has about 0.2 s of its own, mostly numpy working out the regions to colour. Contour (0.64 s): 0.22 s PNG, about 0.14 s Qt drawing its lines,
  and about 0.2 s of Python (the noise grid, marching squares, and one canvas call per segment).
- **Photos are the slow part.** The two dithers spend about 1 s in one pixel-by-pixel Python loop. Stipple spends
  2.2 s in Qt filling its dots and 1 s in Python placing them; engrave 0.7 s in Qt and 1.5 s in Python.
- **Start-up** was about 1.3 s here: 0.1 s importing Qt, 0.2 s importing Inkline, 1 s building the window. It's
  now about 0.65 s; see Start-up below.

## Start-up

Profiled with cProfile and timers round each part of `Window(...)`, and `python -X importtime` for the imports.
Before (median of 5 fresh processes, offscreen, this container): import PySide6 0.09 s, import Inkline 0.23 s,
build the window 0.85 s. The window's 0.85 s was:

| part | seconds |
|---|---:|
| the stylesheet set a second time, once every widget existed (`set_touch` → `theme.apply`) | ~0.45 |
| the sidebar put into the central widget: Qt polishes its ~1,000 widgets against the stylesheet | ~0.11 |
| building the sidebar's controls (`Sidebar._build`, mostly Qt creating and polishing widgets) | ~0.13 |
| the central widget put into the window: the same polish, all over again | ~0.05 |
| `Sidebar.load()`, events waiting, everything else | ~0.10 |

The gallery's six pictures and the first preview were already drawn on worker threads; the window doesn't wait for
them. What changed:

- `theme.apply` does nothing when asked for the look the application already has (same style, palette and
  stylesheet; the desktop's style likewise). `main()` styles the application before building the window, and the
  window's touch set-up asked for the same look again: Qt then restyled every widget for nothing.
- The window sets its (empty) central widget first and fills it after, so the widgets are polished once, not twice.
- `inkapp/updater.py` imports `urllib` and `ssl` when it goes online, not at start-up (about 0.02 s).

After, same machine, median of 5: import PySide6 0.09 s, import Inkline 0.21 s, **build the window 0.33 s**
(0.79–0.99 s before, 0.28–0.39 s after): about 60% less, and the whole start about 1.2 s → 0.65 s. Showing the
window and its first paint takes about 0.06 s more either way. Screenshots of every rail page, in light, dark and
touch, are pixel-for-pixel the same before and after. `tests/test_startup.py` checks that building the window
restyles nothing and that the central widget goes in empty.

Not done, and what it could save: about half of the 1,054 widgets are hidden, the options of patterns not chosen
(each combo box alone brings nine of Qt's own widgets for its popup). Building each pattern's options the first time
it's chosen could save roughly another 0.1–0.15 s, but every control is referenced by `Sidebar.sync()`, presets,
undo, projects and many tests, so it's a larger change, best made when the sidebar isn't also being extended.
Most of Inkline's import time is numpy (0.05 s, used by the engine everywhere) and PySide6 binding its types.

## The Rust trial

`rust/inkline_fast` is a small Rust module (PyO3, built with maturin) with two functions:

- `contour_level`: marching squares for one contour level, the loop asked about first (contour was the slowest
  pattern with real Python work in it);
- `error_diffusion`: the Floyd–Steinberg and Atkinson dithers, which the profile showed are the biggest single
  Python loop in the app.

`inkengine/patterns/contour.py` and `inkengine/photo.py` use it when `import inkline_fast` works, and otherwise run
the Python code as before. The output is identical, not just close: the Rust does the same operations in the same
order with the same 32-bit rounding. `tests/test_inkline_fast.py` compares both paths move by move and byte by byte
(skipped when the module isn't installed), and the JavaScript-recording tests for contour and photos pass with it.

To build and try it:

```sh
python3 -m pip install maturin
cd rust/inkline_fast && maturin build --release && python3 -m pip install target/wheels/inkline_fast-*.whl
```

It isn't in any release package. The benchmark's JSON says whether it was loaded (`inkline_fast: true`).

Results on the same container (median of 3 or 5 runs):

| what | Python | with Rust | faster |
|---|---:|---:|---:|
| the dither loop alone, 1125 × 1500 pixels, Floyd–Steinberg | 1.75 s | 0.018 s | ~95× |
| the dither loop alone, Atkinson | 2.31 s | 0.025 s | ~90× |
| photo: fs, whole page | 1.40 s | 0.39 s | 3.6× |
| photo: atkinson, whole page | 1.81 s | 0.35 s | 5.2× |
| contour drawing, no painting (noise, squares, canvas calls) | 0.087 s | 0.058 s | 1.5× |
| page: contour, whole page | 0.64 s | 0.59 s | within noise |

The dithers' whole-page time is now mostly the PNG save and Qt cropping the photo. Contour hardly changes because
numpy was already doing the squares; what's left is a Python call per segment and Qt drawing the lines.

## Recommendation for 8.0

- **Don't rewrite the engine in Rust.** Patterns are already fast in Python; where they're slow, the time is in Qt's
  painting and PNG encoding, which Rust in the engine wouldn't touch. A rewrite would also lose the line-for-line
  match with the recordings the tests check against.
- **Do move a few pixel loops to Rust, behind the same optional import.** The dithers gain 3.6–5× on a whole page for
  60 lines of Rust. Next in line, from the numbers above: stipple's dot placement (`stipple_sites`, 1 s), engraving's
  line building (1.5 s), and colour by number's blur and distance passes. Each can keep its Python fallback and a
  test that both give the same output.
- **Look at Qt painting for stipple, engrave and truchet.** 2.2 s of stipple is Qt filling paths; fewer, simpler
  paths (or drawing dots as a pre-rendered image at print resolution) may gain more than any Rust.
- **Shipping the module** means a wheel per platform in the packages (Linux x86-64 and ARM64, Windows, both Macs,
  Android). `benchmark.yml`'s rust job shows the build is simple on Linux; do the others before relying on it.
- **Start-up**: profiled and roughly halved (Start-up, above). What's left is Qt polishing about a thousand widgets.
