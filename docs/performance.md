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

These are 6.1's numbers, before the photo work below (which has its own table). Measured on the Linux container this work was done in: 4 CPUs (Intel Xeon, 2.10 GHz), Python 3.13, Qt 6.12.0,
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
- **Photos were the slow part.** The two dithers spent about 1 s in one pixel-by-pixel Python loop. Stipple spent
  2.2 s in Qt filling its dots and 1 s in Python placing them; engrave 0.7 s in Qt and 1.5 s in Python. The next two
  sections say what changed.
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

## The Rust module

`rust/inkline_fast` is a small Rust module (PyO3, built with maturin) with the slowest loops of the photo styles
and one of contour's:

| function | what it does | used by |
|---|---|---|
| `error_diffusion` | the Floyd–Steinberg and Atkinson dithers | photo: fs, atkinson |
| `stipple_sites` | which work pixels get a dot (error diffusion with a wobble) | photo: stipple |
| `engrave_band` | one engraving line's stretches (darkness per column, the wave) | photo: engrave |
| `gauss_blur` | separable Gaussian blur | photo: line, cbn |
| `despeckle` | clearing away black blobs too small to colour | photo: line |
| `chamfer` | the two passes of a region's distance map | photo: cbn, page: spot |
| `contour_level` | marching squares for one contour level | page: contour |

`inkengine/photo.py`, `cbn.py` and `patterns/contour.py` use it when `import inkline_fast` works, and otherwise run
the Python code. The output is identical, not just close: the Rust does the same operations in the same order with
the same 32-bit rounding (and calls the same C library `sin` as Python's `math.sin`), so every dot, line, region and
pixel is the same, and so is every PNG, PDF and SVG. `tests/test_inkline_fast.py` compares both paths on several
seeds and sizes (odd sizes, one-pixel strips, holes in the picture, inverted tones): each function's numbers, every
drawing call of a whole photo page, and the dithered bytes (skipped when the module isn't installed). The
JavaScript-recording tests for contour and photos pass with it too.

It's an abi3 wheel (any CPython 3.9 or newer), so one wheel per processor serves every package. To build and try it:

```sh
python3 packaging/build_fast.py --install     # needs Rust (https://rustup.rs); fetches maturin if it isn't there
```

The benchmark's JSON says whether it was loaded (`inkline_fast: true`), and so does the self-test
(`inkline-fast.txt` in its folder).

### Stipple's dots in Qt

Stipple drew each row of dots as one filled path (one `<path>` per row keeps the SVG small), and Qt's raster painter
fills one long path of a few hundred circles about ten times slower than the same circles a few at a time: 2.2 s of
the page was `fillPath`. On the raster painter (PNG, the preview) `QtCanvas.fill` now splits a path made only of
whole circles into groups that share no pixel column and fills each group on its own. The pixels are exactly the
same (circles filled with the nonzero rule only interact where they overlap, and groups with a free pixel column
between them touch no common pixel), checked pixel for pixel by `tests/test_stipple_fill.py`; PDFs and SVGs still
get one vector path per row, as before. Stipple's dot centres are also worked out with numpy in one go (the same
32-bit hash, the same order of operations, so the same numbers). Both help with or without the Rust module.

Other ways were tried and left: drawing each dot with `drawEllipse` is as fast but shades the overlap of two dots'
edges differently (up to 64 levels on 0.5% of pixels); Engrave's `fillPath` (0.65 s for 486 long, thin polygons)
didn't get faster with `drawPolygon`, the odd-even rule or without the clip, and splitting its polygons would
change the antialiased pixels at the seams.

### Results

The benchmark's photo items on the same container (made-up 2000 × 1500 photo, Letter at 300 dpi, PNG; median of 5
runs, seconds; runs vary by about 10%):

| photo style | 6.1 | now, Python only | now, with Rust | faster than 6.1 |
|---|---:|---:|---:|---:|
| stipple | 3.34 | 1.41 | 0.97 | 3.4× |
| atkinson | 1.58 | 1.58 | 0.40 | 4.0× |
| fs (smooth dither) | 1.31 | 1.29 | 0.35 | 3.7× |
| cbn | 1.52 | 1.55 | 1.21 | 1.25× |
| engrave | 1.53 | 1.38 | 1.13 | 1.35× |
| line | 0.48 | 0.49 | 0.31 | 1.55× |
| halftone | 0.63 | 0.60 | 0.66 | (unchanged) |

Each loop on its own (Python, then Rust):

| loop | Python | Rust | faster |
|---|---:|---:|---:|
| the dither loop, 1125 × 1500 pixels, Floyd–Steinberg | 1.75 s | 0.018 s | ~95× |
| the dither loop, Atkinson | 2.31 s | 0.025 s | ~90× |
| stipple dot placement, 563 × 750 sites | 0.49 s | 0.008 s | ~60× |
| engraving: building the lines and the canvas calls (no painting) | 0.42 s | 0.12 s | 3.6× |
| despeckle, 1125 × 1500 | 0.58 s | 0.027 s | ~20× |
| Gaussian blur, 1125 × 1500 (numpy before) | 0.08 s | 0.012 s | 6.6× |
| chamfer distance map, 1125 × 1462 (numpy before) | 0.12 s | 0.05 s | 2.5× |
| contour drawing, no painting (noise, squares, canvas calls) | 0.087 s | 0.058 s | 1.5× |

What's left in each page is mostly Qt and PNG: about 0.2–0.3 s of every photo page is the PNG save; stipple has
0.2 s of Qt filling and 0.3 s of canvas calls (82,000 dots); engrave 0.65 s of Qt filling its lines and 0.25 s of
canvas calls; colour by number a dozen numpy passes over the regions (merging, region details, tracing borders),
each already vectorised. Halftone has no loop worth moving: it's one canvas call per dot and the PNG.

### Which packages ship it

The release (`.github/workflows/release.yml`) builds the module for each package's processor with
`packaging/build_fast.py`, which checks the wheel is abi3 and, on Linux, needs no newer glibc than the package
already does. Each package's self-test runs with `INKLINE_EXPECT_FAST=1`, which fails it unless the module loads
and gives the Python code's answer.

| package | Python | how it's built and installed |
|---|---|---|
| Windows installer and portable zip | 3.12 (setup-python) | wheel built on the runner, pip-installed, bundled by PyInstaller |
| macOS arm64 / Intel | 3.12 (setup-python) | wheel built natively on each runner, bundled by PyInstaller |
| macOS universal | 3.12 universal2 (python.org) | a universal2 wheel (`--target universal2-apple-darwin`) |
| .deb amd64 / arm64 | the system's (3.10+) | wheel unpacked into `/usr/lib/inkline/vendor` beside PySide6 (glibc 2.34 / 2.39 at most) |
| .rpm x86_64 / aarch64 | the system's (3.10+) | the same, built with Fedora's Rust (glibc 2.34 / 2.39 at most) |
| AppImage x86_64 / aarch64 | 3.12 (uv's standalone) | wheel pip-installed beside numpy |
| Snap amd64 / arm64 | core24's 3.12 | its own part: Rust from rustup, `cargo build`, the library put in the venv's site-packages |
| Flatpak | the freedesktop 26.08 SDK's | built offline with the SDK's Rust extension from the crates in Cargo.lock, listed in the manifest by `packaging/flatpak/cargo_sources.py` |
| Android APK / Play bundle (arm64-v8a, x86_64) | python-for-android's 3.14 | a local python-for-android recipe (`packaging/android/inkline_fast_recipe.py`): `cargo build --locked` for `aarch64-linux-android` or `x86_64-linux-android`, linked by the NDK's clang (API 28) against python-for-android's libpython3.14, put in site-packages as `inkline_fast.abi3.so` |

On Android the module travels inside `libpybundle.so` (python-for-android's tar of the Python files, unpacked on the
device) rather than in the APK's `lib/<abi>/`, so the recipe checks its 16 KB page alignment as it builds, and the
workflows check it again in the APK and the bundle (`check_16kb.py --bundled inkline_fast.abi3.so`). The emulator
self-test runs with `INKLINE_EXPECT_FAST=1` (`emulator-test.sh` leaves an `inkline-expect-fast` file beside
`inkline-selftest`, which main.py turns into the variable), and the workflow checks its `inkline-fast.txt` says
yes. Only the x86_64 build runs on the emulator; the arm64 one is built the same way, from the same crate, but is
proved to load only on a real phone.

Not shipped, and why:

- **The `.run` installer and the Arch package** run on the system's own Python and numpy, which differ from machine
  to machine, and they carry no compiled code at all (the .run works on any processor). They use the Python code:
  the same pages, slower photos. (An Arch user can still `pip install` the module from `rust/inkline_fast`.)
- **Running from source** uses it if it's installed (`packaging/build_fast.py --install`).

## Recommendation for 8.0

- **Don't rewrite the engine in Rust.** Patterns are already fast in Python; where they're slow, the time is in Qt's
  painting and PNG encoding, which Rust in the engine wouldn't touch. A rewrite would also lose the line-for-line
  match with the recordings the tests check against.
- **Do move a few pixel loops to Rust, behind the same optional import.** Done for the dithers, stipple, engrave,
  line drawing and colour by number's blur and distances (above); each keeps its Python fallback and a test that
  both give the same output. What's left in the photo pages is mostly Qt painting and PNG encoding.
- **Look at Qt painting for engrave and truchet.** Stipple's 2.2 s of path filling is now 0.2 s (above); engrave's
  0.65 s and truchet's 0.44 s are still one `fillPath`/`drawPath` each.
- **Shipping the module** is done for every package with its own Python, Android included (above).
- **Start-up**: profiled and roughly halved (Start-up, above). What's left is Qt polishing about a thousand widgets.
