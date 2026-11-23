# Inkline

A desktop app for Linux and Windows that converts photos to, or generates, black & white images for printing.

- **Make one up:** mandala colouring pages, mazes (rectangular, or shaped like a heart, star, fish, house or any word or name), dot-to-dots, sudoku and nonograms (each with exactly one solution), spot the difference (two copies of a mandala, woven tiles or contours, 5 to 10 changes to find), kakuro (cross sums, with a few starter numbers and exactly one solution), word search (themes or your own words, each word hidden exactly once), name pages in bubble letters, woven tiles, topographic contours, flow lines; mandalas, woven tiles, contours and name pages can also be colour-by-number, with repeated spaces sharing a number, a crayon key, and shaded answer pages in booklets.
- **Convert a photo:** Floyd–Steinberg, Atkinson and ordered dithering, halftone dots, engraving lines and stippling dots (both also save as SVG), solid black & white, a line drawing (colouring page), colour by number (regions of similar colour, each numbered, with a key naming the crayon to use; also saves as SVG), or a nonogram puzzle that reveals the photo (always solvable by logic alone), with rotate, zoom and pan to crop.
- **Photo books:** turn several photos into one colouring-book PDF, one page each with its own crop, plus an optional cover, title, name line and page numbers.
- **Fold-and-staple books:** booklets and photo books can print two half-size pages per side, double-sided, so the sheets fold and staple into a real little book in page order.
- **Worksheet packs:** *Booklet → Worksheet pack* makes a booklet of five worksheets, one for each school day, set for the age chosen under *Age*, with a cover, name line and answer pages. On a theme (animals, food, space, ocean, weather or sports) it's a maths drill, handwriting, a crossword, a word search and a maze; on this week's spelling words it's a maths drill and the words four ways: traced, in a crossword whose clues are the words' letters mixed up, in a word search and to unscramble. With *Paper → Copies* or *Names* it makes a pack for every child, and the answers can go in one teacher's book.
- **Classroom worksheets:** maths drills (adding, taking away, times tables, number bonds, sharing, missing numbers), telling the time (clock faces to read, or to draw the hands on), handwriting to trace, crosswords, and unscramble sheets, each with an answer page.
- **Booklets:** turn any pattern (or every pattern but name pages, mixed) into a multi-page PDF with a cover, a title and name line, page numbers, difficulty that ramps up page by page, a *New design for this page* button to swap any single page (answers follow), and answer pages for mazes, dot-to-dots, sudoku, word search, nonograms, spot the difference and kakuro. Or build a booklet page by page: *Edit pages one by one* lists its pages, each with a small picture and its own pattern, options and complexity (so each word search page can have its own words, and each name page its own name), to add, drag into order, duplicate (with a new design) or remove.
- **Projects:** *File → Save project* (Ctrl+S) keeps everything you're making in one `.inkline` file, with the photos inside it, so it opens again later or on another computer even if the original pictures have moved. *File → Open project…* (Ctrl+Shift+O) and *Open recent project* bring it back; the window title shows the project's name and whether it has unsaved changes. Installed from a package, project files get their own icon in your file manager and open in Inkline with a double-click; `python3 inkline.py book.inkline` does the same from a terminal. If Inkline closes unexpectedly, the next start offers to bring back the work you hadn't saved: while there's unsaved work, a copy is kept in the settings folder at most once a minute.
- **Presets:** twenty-one built-in starting points (start fresh, a week's worksheet pack, colouring page, name page, maze worksheet, maze booklet, name maze, word search booklet, sudoku booklet, nonogram booklet, dot-to-dot booklet, spot the difference booklet, kakuro booklet, colour-by-number mandala, halftone photo, engraved photo, stippled photo, colour-by-number photo, photo nonogram, photo colouring page, wall poster) plus your own saved settings.
- **Picks up where you left off:** settings and the current design are restored on the next start (*Presets → Start fresh* resets them). Shortcuts: Ctrl+P print, Ctrl+S save project, Ctrl+Shift+S save project as, Ctrl+E save PDF, Ctrl+Shift+E save PNG, Ctrl+O open image, Ctrl+Shift+O open project, Ctrl+N new design, Ctrl+Shift+N more designs (six to choose from), Ctrl+Z undo, Ctrl+Shift+Z redo, Ctrl+H undo history, ←/→ booklet pages. Recently opened photos are under *File → Open recent image*.
- **Printer test page:** true-size squares and rulers, edge-margin marks, every dither style and dot size, and every line weight, to check your printer at a glance.
- **Print-ready output:** Letter or A4 at 150/300 dpi, with Print, Save PNG and Save PDF at true paper size. Booklets and photo books can print or save only some pages (*Paper → Print or save only*, e.g. `3-5, 8, cover`). The preview hatches the edge your printer can't reach and warns if the design runs into it.
- **Posters:** print any design or photo big across 2×1 up to 4×4 sheets, with overlap strips, trim marks and sheet labels (A1, A2…) for assembly.
- **English, Spanish and French:** Inkline uses your system's language, or choose one under *View → Language*. The window and everything printed are translated; word searches, crosswords and handwriting sheets use words and an alphabet in that language.
- **SVG export:** generated designs save as true vector lines at real paper size, for Inkscape, Cricut/Silhouette cutting machines and laser cutters.

## Install

Each [release](https://github.com/Gshoe2006/inkline/releases) has a package for most Linux systems:

| You use | Download | Install |
| --- | --- | --- |
| Debian 12+, Ubuntu 22.04+, Linux Mint, Pop!_OS | `inkline_<version>-1_amd64.deb` | `sudo apt install ./inkline_<version>-1_amd64.deb` |
| Arch, CachyOS, Manjaro | `inkline-<version>-1-any.pkg.tar.zst` | `sudo pacman -U inkline-<version>-1-any.pkg.tar.zst` |
| Any distro, nothing installed | `inkline-<version>-x86_64.AppImage` | `chmod +x inkline-*.AppImage`, then run it |
| Any distro, sandboxed | `inkline-<version>.flatpak` | `flatpak install --user inkline-<version>.flatpak` |
| Any distro, your own Python | `inkline-<version>.run` | `sh inkline-<version>.run` |
| Windows 10 or 11 (64-bit) | `inkline-<version>-windows-setup.exe` | Run it; no administrator needed |

The Windows installer isn't signed yet, so Windows SmartScreen may warn that it's from an unknown publisher: choose **More info → Run anyway**. It adds Inkline to the Start menu, opens `.inkline` projects with a double-click, and uninstalls from Settings → Apps. Settings are kept in `%APPDATA%\Inkline`.

The `.deb` brings its own PySide6 (Debian and Ubuntu don't package a new enough one) and uses the system's Python and numpy. The AppImage brings everything, Python included; for it to appear in your app menu and open `.inkline` projects with a double-click, use an AppImage manager such as Gear Lever or AppImageLauncher.

## Flatpak

One package for any distro, with PySide6 and numpy inside (about 300 MB with the shared freedesktop runtime). With `flatpak` and `flatpak-builder` installed, build and install it from a copy of the repository:

```sh
sh packaging/flatpak/build.sh            # sets up Flathub and the runtime the first time, then builds and installs
flatpak run io.github.gshoe2006.Inkline  # or start Inkline from your app menu
```

`sh packaging/flatpak/build.sh --bundle` also writes `dist/inkline-<version>.flatpak`, one file anyone can install with `flatpak install --user inkline-<version>.flatpak` (they need Flathub added for the runtime). `packaging/flatpak/inkline.sh` is the launcher inside the Flatpak; it doesn't run on its own.

The Flatpak keeps its own settings and presets, in `~/.var/app/io.github.gshoe2006.Inkline/config/inkline`. Files are opened and saved through your desktop's file dialogs, and printing goes through CUPS as usual.

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

The Debian package and the AppImage have scripts of their own (both download what they bundle, checked):

```sh
sh packaging/debian/build-deb.sh          # dist/inkline_<version>-1_amd64.deb (needs dpkg-deb)
sh packaging/appimage/build-appimage.sh   # dist/inkline-<version>-x86_64.AppImage (needs uv: pip install uv)
```

The Windows installer is built on Windows, with Python, `pip install PySide6-Essentials numpy pyinstaller` and [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```sh
python packaging/windows/build.py         # dist/Inkline/ and dist/inkline-<version>-windows-setup.exe
```

`packaging/build.sh` outputs to `dist/`:

- `inkline-<version>-<rel>-any.pkg.tar.zst` — Arch / CachyOS / Manjaro package: `sudo pacman -U dist/inkline-*.pkg.tar.zst`
- `inkline-<version>.run` — universal installer for any distro: `sh dist/inkline-*.run` (`--system`, `--uninstall`, `--help`)

## Translations

Inkline is in English, Spanish (`es`) and French (`fr`). Each translation is `inkengine/locale/<code>.json`: the
English text as written in the code, and its translation. Word search themes, crossword words and clues, and the
default handwriting words are written in each language in `inkengine/patterns/words.py`, `crossword.py` and
`trace.py`.

**Check a translation.** The Spanish and French were written without a native speaker's review, so corrections are
very welcome. Open a [translation fix](https://github.com/Gshoe2006/inkline/issues/new?template=translation.yml)
issue for a single string, or check the lot in a spreadsheet:

```sh
python3 packaging/translation_sheet.py fr      # writes inkline-fr-review.csv: English, French, Better wording, Comment
```

**Add a language.**

1. Copy `es.json` to `<code>.json` and translate each value. Keep every `{placeholder}`, and keep one `&` before a
   letter in menu items (letters must differ within a menu).
2. Add the language to `LANGUAGES` in `inkengine/i18n.py`. If its alphabet has letters of its own (Spanish Ñ), add
   them to `KEEP_LETTERS` and `ALPHABETS`.
3. Add its word lists to `THEMES_BY_LANGUAGE` in `words.py` and `crossword.py`, and to `DEFAULT_WORDS` in
   `trace.py`.
4. Add two sample words to `SAMPLES` in `tests/test_i18n.py`, then run it. It checks the file covers every string,
   and drives the window through every pattern and mode in the new language, failing on anything left in English.

`python3 packaging/i18n_strings.py <code>` lists strings a translation is missing.

## Project layout

| Path | What it is |
| --- | --- |
| `inkline.py` | Starts the app (with a project: `inkline.py FILE.inkline`; or `--selftest DIR`) |
| `inkapp/` | The window: sidebar, preview, menus, saving and printing, presets, project files (Qt Widgets) |
| `inkengine/` | The drawing engine: every pattern, photo style, booklet and poster, as PNG, PDF and SVG (also a command line) |
| `tests/` | Tests for `inkengine/`, with recordings of what Inkline 2.5 drew to match |
| `inkline.svg`, `icons/` | App icon; regenerate with `python3 packaging/make_icon.py` |
| `inkline.desktop` | Application menu entry |
| `inkline-mime.xml` | The `.inkline` project file type, so file managers open projects in Inkline |
| `packaging/` | Build script, Arch PKGBUILD, self-extracting installer stub, release notes script |
| `CHANGELOG.md` | What changed in each release; each section becomes that release's notes |
| `VERSION` | App version used by both installers |

## Releasing a new version

In one pull request:

1. Bump `VERSION`.
2. Add a section to the top of `CHANGELOG.md` headed `## <version>` (for example `## 3.4.3 - 2026-11-21`) saying what changed. It becomes the release notes word for word, with its `###` headings shown as `##`.
3. Add `<release version="<version>" date="<date>"/>` to `packaging/flatpak/io.github.gshoe2006.Inkline.metainfo.xml`.

When it merges, `.github/workflows/release.yml` checks there are notes for the version, runs the self-test, builds the `.run` installer, the Arch package, the `.flatpak`, the `.deb`, the AppImage and the Windows installer (self-testing the `.deb`, the AppImage and `Inkline.exe` with each), and publishes the GitHub Release "Inkline <version>" with all six attached. It then tells the app portal, so the release shows there within a minute or two (this needs the `PORTAL_TOKEN` secret, otherwise the portal shows it on its next 3-hourly run). If any step fails nothing is published: fix it and press *Run workflow* on the Release workflow. `python3 packaging/release_notes.py` prints the notes the release will get.

To check the release builds without publishing anything, open the Release workflow on the Actions tab, press *Run workflow*, tick *Test build only* and run it: the packages it builds are kept for 7 days under the run's *Artifacts*.

For a packaging-only change, bump `pkgrel` in `packaging/arch/PKGBUILD`, run `packaging/build.sh` and install with `sudo pacman -U dist/inkline-*.pkg.tar.zst`; no release is made.

## Code signing policy

Free code signing provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org).

This covers the Windows installer (`inkline-<version>-windows-setup.exe`). It's signed from the first release
after SignPath Foundation accepts Inkline; until then the installer is unsigned, and Windows SmartScreen may
say it's from an unknown publisher.

- Committers and reviewers: [Gshoe2006](https://github.com/Gshoe2006)
- Approvers: [Gshoe2006](https://github.com/Gshoe2006)

Every installer is built from this repository's source by the release workflow
(`.github/workflows/release.yml`) on GitHub's own runners, and each release is approved for signing by hand.
How it's set up: [docs/code-signing.md](docs/code-signing.md).

**Privacy:** this program will not transfer any information to other networked systems unless specifically
requested by the user or the person installing or operating it.

## Licence

Inkline is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version (GPL-3.0-or-later). See [LICENSE](LICENSE).

The joined-up handwriting fonts in `inkengine/fonts` are Playwrite GB J, Playwrite ES and Playwrite FR Trad (copyright 2023 The Playwrite Project Authors), under the SIL Open Font License 1.1; see [inkengine/fonts/OFL.txt](inkengine/fonts/OFL.txt).
