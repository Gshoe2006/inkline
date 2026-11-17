# Inkline

A Linux desktop app that converts photos to, or generates, black & white images for printing.

- **Make one up:** mandala colouring pages, mazes, woven tiles, topographic contours, flow lines.
- **Convert a photo:** Floyd–Steinberg, Atkinson and ordered dithering, halftone dots, solid black & white, or a line drawing (colouring page).
- **Booklets:** turn any pattern (or all five mixed) into a multi-page PDF with a cover, a title and name line, page numbers, difficulty that ramps up page by page, and answer pages for mazes.
- **Print-ready output:** Letter or A4 at 150/300 dpi, with Print, Save PNG and Save PDF at true paper size.
- **SVG export:** generated designs save as true vector lines at real paper size, for Inkscape, Cricut/Silhouette cutting machines and laser cutters.

## Run from source

Needs Python 3 and PySide6 with Qt WebEngine (Arch: `sudo pacman -S pyside6 qt6-webengine qt6-webchannel`).

```sh
python3 inkline.py
```

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
