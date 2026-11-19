# Inkline

A Linux desktop app that converts photos to, or generates, black & white images for printing.

- **Make one up:** mandala colouring pages, mazes (rectangular, or shaped like a heart, star, fish, house or any word or name), dot-to-dots, sudoku and nonograms (each with exactly one solution), word search (themes or your own words, each word hidden exactly once), name pages in bubble letters, woven tiles, topographic contours, flow lines; mandalas, woven tiles, contours and name pages can also be colour-by-number, with repeated spaces sharing a number, a crayon key, and shaded answer pages in booklets.
- **Convert a photo:** Floyd–Steinberg, Atkinson and ordered dithering, halftone dots, engraving lines and stippling dots (both also save as SVG), solid black & white, a line drawing (colouring page), colour by number (regions of similar colour, each numbered, with a key naming the crayon to use; also saves as SVG), or a nonogram puzzle that reveals the photo (always solvable by logic alone), with rotate, zoom and pan to crop.
- **Photo books:** turn several photos into one colouring-book PDF, one page each with its own crop, plus an optional cover, title, name line and page numbers.
- **Fold-and-staple books:** booklets and photo books can print two half-size pages per side, double-sided, so the sheets fold and staple into a real little book in page order.
- **Booklets:** turn any pattern (or every pattern but name pages, mixed) into a multi-page PDF with a cover, a title and name line, page numbers, difficulty that ramps up page by page, a *New design for this page* button to swap any single page (answers follow), and answer pages for mazes, dot-to-dots, sudoku, word search and nonograms.
- **Presets:** eighteen built-in starting points (start fresh, colouring page, name page, maze worksheet, maze booklet, name maze, word search booklet, sudoku booklet, nonogram booklet, dot-to-dot booklet, colour-by-number mandala, halftone photo, engraved photo, stippled photo, colour-by-number photo, photo nonogram, photo colouring page, wall poster) plus your own saved settings.
- **Picks up where you left off:** settings and the current design are restored on the next start (*Presets → Start fresh* resets them). Shortcuts: Ctrl+P print, Ctrl+S PDF, Ctrl+Shift+S PNG, Ctrl+N new design, Ctrl+Z undo, Ctrl+Shift+Z redo, Ctrl+H undo history, ←/→ booklet pages. Recently opened photos are under *File → Open recent*.
- **Printer test page:** true-size squares and rulers, edge-margin marks, every dither style and dot size, and every line weight, to check your printer at a glance.
- **Print-ready output:** Letter or A4 at 150/300 dpi, with Print, Save PNG and Save PDF at true paper size.
- **Posters:** print any design or photo big across 2×1 up to 4×4 sheets, with overlap strips, trim marks and sheet labels (A1, A2…) for assembly.
- **SVG export:** generated designs save as true vector lines at real paper size, for Inkscape, Cricut/Silhouette cutting machines and laser cutters.

## Run from source

Needs Python 3, PySide6 and numpy (Arch: `sudo pacman -S pyside6 python-numpy`). No browser engine: since 3.0 Inkline is a native Qt app.

```sh
python3 inkline.py
```

## Test

```sh
QT_QPA_PLATFORM=offscreen python3 inkline.py --selftest /tmp/inkline-test
python3 packaging/check_selftest.py /tmp/inkline-test
```

The self-test opens the window, then writes every pattern, the photo styles, the printer test page, a booklet (plain and folded), two posters and a photo book through the app's own save code, and exits non-zero if anything fails. The unit tests (`python3 -m pip install pytest && QT_QPA_PLATFORM=offscreen python3 -m pytest -q tests`) check the engine against recordings of what Inkline 2.5 drew. GitHub runs both commands on every pull request (`.github/workflows/selftest.yml`) and keeps the rendered files for 7 days.

## Command line

Everything the window makes can also be made from the command line, with the same engine:

```sh
python3 -m inkengine maze -o maze.pdf
python3 -m inkengine mandala --complexity 8 --title "Colour me" -o mandala.pdf
python3 -m inkengine truchet --complexity 6 --frame -o tiles.svg
python3 -m inkengine contour --complexity 8 -o map.pdf
python3 -m inkengine flow -o flow.png
python3 -m inkengine dots --complexity 6 --answers -o dots.pdf
python3 -m inkengine sudoku --complexity 8 --answers -o sudoku.pdf
python3 -m inkengine words --theme ocean --answers -o words.pdf
python3 -m inkengine words --words "mum, dad, grandma, pizza" -o ours.pdf
python3 -m inkengine nonogram --complexity 6 --answers -o picture.pdf
python3 -m inkengine name --text "Happy Birthday Maya" --background flow -o card.pdf
python3 -m inkengine maze --booklet 10 --title "Rainy Day Mazes" -o mazes.pdf
python3 -m inkengine mandala --booklet 12 --mix --fold -o book.pdf
python3 -m inkengine mandala --poster 3x3 -o poster.pdf
python3 -m inkengine photo --image cat.jpg --style halftone -o cat.pdf
python3 -m inkengine photo --image cat.jpg --style cbn --crayons 10 -o colour-me.pdf
python3 -m inkengine photo --image a.jpg b.jpg c.jpg --style line --title "Our holiday" -o book.pdf
python3 -m inkengine mandala --cbn 6 --booklet 4 -o numbers.pdf
python3 -m inkengine testpage -o test.pdf
python3 -m inkengine maze --shape heart --complexity 7 --seed 42 --answers -o heart.pdf
python3 -m inkengine maze --shape word --word Maya --title "Maya's maze" --name-line -o maya.svg
```

The tests check every pattern and photo style against recordings of what Inkline 2.5 drew (`tests/fixtures/`). `tests/fixtures/make_fixtures.js` made them from 2.5's `index.html` in a headless browser; to record again, check that file out from the 2.5.0 release (commit `ea92479`) and pass it as `INDEX_HTML=path/to/index.html`.

## Build the installers

```sh
packaging/build.sh
```

Outputs to `dist/`:

- `inkline-<version>-<rel>-any.pkg.tar.zst` — Arch / CachyOS / Manjaro package: `sudo pacman -U dist/inkline-*.pkg.tar.zst`
- `inkline-<version>.run` — universal installer for any distro: `sh dist/inkline-*.run` (`--system`, `--uninstall`, `--help`)

## Project layout

| Path | What it is |
| --- | --- |
| `inkline.py` | Starts the app (or `--selftest DIR`) |
| `inkapp/` | The window: sidebar, preview, menus, saving and printing, presets (Qt Widgets) |
| `inkengine/` | The drawing engine: every pattern, photo style, booklet and poster, as PNG, PDF and SVG (also a command line) |
| `tests/` | Tests for `inkengine/`, with recordings of what Inkline 2.5 drew to match |
| `inkline.svg`, `icons/` | App icon; regenerate with `python3 packaging/make_icon.py` |
| `inkline.desktop` | Application menu entry |
| `packaging/` | Build script, Arch PKGBUILD, self-extracting installer stub |
| `VERSION` | App version used by both installers |

## Releasing a new version

1. Bump `VERSION` (or `pkgrel` in `packaging/arch/PKGBUILD` for packaging-only changes).
2. Run `packaging/build.sh`.
3. Install with `sudo pacman -U dist/inkline-*.pkg.tar.zst`.
