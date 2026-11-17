# Inkline

A Linux desktop app that converts photos to, or generates, black & white images for printing.

- **Make one up:** mandala colouring pages, mazes, dot-to-dots, sudoku and nonograms (each with exactly one solution), word search (themes or your own words, each word hidden exactly once), name pages in bubble letters, woven tiles, topographic contours, flow lines; mandalas, woven tiles, contours and name pages can also be colour-by-number, with repeated spaces sharing a number, a crayon key, and shaded answer pages in booklets.
- **Convert a photo:** Floyd–Steinberg, Atkinson and ordered dithering, halftone dots, engraving lines and stippling dots (both also save as SVG), solid black & white, a line drawing (colouring page), colour by number (regions of similar colour, each numbered, with a key naming the crayon to use; also saves as SVG), or a nonogram puzzle that reveals the photo (always solvable by logic alone), with rotate, zoom and pan to crop.
- **Photo books:** turn several photos into one colouring-book PDF, one page each with its own crop, plus an optional cover, title, name line and page numbers.
- **Fold-and-staple books:** booklets and photo books can print two half-size pages per side, double-sided, so the sheets fold and staple into a real little book in page order.
- **Booklets:** turn any pattern (or every pattern but name pages, mixed) into a multi-page PDF with a cover, a title and name line, page numbers, difficulty that ramps up page by page, a *New design for this page* button to swap any single page (answers follow), and answer pages for mazes, dot-to-dots, sudoku, word search and nonograms.
- **Presets:** seventeen built-in starting points (start fresh, colouring page, name page, maze worksheet, maze booklet, word search booklet, sudoku booklet, nonogram booklet, dot-to-dot booklet, colour-by-number mandala, halftone photo, engraved photo, stippled photo, colour-by-number photo, photo nonogram, photo colouring page, wall poster) plus your own saved settings.
- **Picks up where you left off:** settings and the current design are restored on the next start (*Presets → Start fresh* resets them). Shortcuts: Ctrl+P print, Ctrl+S PDF, Ctrl+Shift+S PNG, Ctrl+N new design, ←/→ booklet pages.
- **Printer test page:** true-size squares and rulers, edge-margin marks, every dither style and dot size, and every line weight, to check your printer at a glance.
- **Print-ready output:** Letter or A4 at 150/300 dpi, with Print, Save PNG and Save PDF at true paper size.
- **Posters:** print any design or photo big across 2×1 up to 4×4 sheets, with overlap strips, trim marks and sheet labels (A1, A2…) for assembly.
- **SVG export:** generated designs save as true vector lines at real paper size, for Inkscape, Cricut/Silhouette cutting machines and laser cutters.

## Run from source

Needs Python 3 and PySide6 with Qt WebEngine (Arch: `sudo pacman -S pyside6 qt6-webengine qt6-webchannel`).

```sh
python3 inkline.py
```

## Test

```sh
QT_QPA_PLATFORM=offscreen python3 inkline.py --selftest /tmp/inkline-test
python3 packaging/check_selftest.py /tmp/inkline-test
```

The self-test renders every pattern, the photo converter, a booklet, two posters and a photo book, and exits non-zero if anything fails. GitHub runs both commands on every pull request (`.github/workflows/selftest.yml`) and keeps the rendered files for 7 days.

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
| `index.html` | The image engine and UI (canvas + JavaScript); also works in a plain browser |
| `inkline.py` | Qt desktop shell: native save dialogs, PDF export, printing |
| `inkline.svg`, `icons/` | App icon; regenerate with `python3 packaging/make_icon.py` |
| `inkline.desktop` | Application menu entry |
| `packaging/` | Build script, Arch PKGBUILD, self-extracting installer stub |
| `VERSION` | App version used by both installers |

## Releasing a new version

1. Bump `VERSION` (or `pkgrel` in `packaging/arch/PKGBUILD` for packaging-only changes).
2. Run `packaging/build.sh`.
3. Install with `sudo pacman -U dist/inkline-*.pkg.tar.zst`.
