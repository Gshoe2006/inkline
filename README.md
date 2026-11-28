# Inkline

A desktop app for Linux and Windows that converts photos to, or generates, black & white images for printing.

- **Make one up:** mandala colouring pages, mazes (rectangular, or shaped like a heart, star, fish, house or any word or name), dot-to-dots, sudoku and nonograms (each with exactly one solution), spot the difference (two copies of a mandala, woven tiles or contours, 5 to 10 changes to find), kakuro (cross sums, with a few starter numbers and exactly one solution), word search (themes or your own words, each word hidden exactly once), name pages in bubble letters, woven tiles, topographic contours, flow lines; mandalas, woven tiles, contours and name pages can also be colour-by-number, with repeated spaces sharing a number, a crayon key, and shaded answer pages in booklets.
- **Convert a photo:** Floyd–Steinberg, Atkinson and ordered dithering, halftone dots, engraving lines and stippling dots (both also save as SVG), solid black & white, a line drawing (colouring page), colour by number (regions of similar colour, each numbered, with a key naming the crayon to use; also saves as SVG), a nonogram puzzle that reveals the photo (always solvable by logic alone), or a dot-to-dot of the photo's main outline (20–150 numbered dots, with the joined-up answer), with rotate, zoom and pan to crop.
- **Photo books:** turn several photos into one colouring-book PDF, one page each with its own crop, plus an optional cover, title, name line and page numbers.
- **Fold-and-staple books:** booklets and photo books can print two half-size pages per side, double-sided, so the sheets fold and staple into a real little book in page order.
- **Worksheet packs:** *Booklet → Worksheet pack* makes a booklet of five worksheets, one for each school day, set for the age chosen under *Age*, with a cover, name line and answer pages. On a theme (animals, food, space, ocean, weather or sports) it's a maths drill, handwriting, a crossword, a word search and a maze; on this week's spelling words (or a week of sight words) it's a spelling week: look, say, cover, write, check on Monday, a word search, missing letters, a crossword whose clues are the words' letters mixed up, and Friday's spelling test. With *Paper → Copies* or *Names* it makes a pack for every child, and the answers can go in one teacher's book. Choose each day's sheet yourself (Monday to Friday, from maths, early maths, handwriting, puzzles, clocks, reading, bingo and more); the week you choose is kept with your presets.
- **Classroom worksheets:** maths drills (adding, taking away, times tables, number bonds, sharing, missing numbers, money), fractions of shapes, number lines and times grids, telling the time (clock faces to read, or to draw the hands on), symmetry (shade the mirror half), handwriting to trace, crosswords, unscramble sheets, spelling tests and reading comprehension (an original passage for the age with questions), each with an answer page. Word searches, crosswords and worksheet packs have seasonal themes (autumn, Halloween, winter, spring, summer) as well as animals, food, space, ocean, weather and sports, and word searches, unscramble sheets, spelling tests and worksheet packs can use sight words for three stages of early reading.
- **Classroom paper and rewards:** squared, dot and isometric grid paper, lined paper, handwriting lines and music staves at any spacing; sticker charts and certificates, with each child's name from *Paper → Names*.
- **Easier to read:** *Print → Page text → Easier to read* sets the worksheets' text in Atkinson Hyperlegible (made for readers with low vision, and recommended for dyslexia), with letters and words spaced wider; *Paper → Cream paper* tints the page on screen and in PDFs, while Print still uses white paper.
- **Early maths with pictures:** ten frames to count, number bonds to complete, tens rods and ones cubes, and shapes to count, for ages 4–6, with the answers on an answer page.
- **Bingo:** number (1–75 under B I N G O, or smaller cards for younger children), word (any theme, sight words, or your own list) and sums bingo, a different card for every child with *Paper → Copies* or *Names*, and a caller's sheet on the answer page.
- **Logic puzzles, cryptograms and word ladders:** grid logic puzzles (who has which pet, colour, fruit or sport: 3, 4 or 5 of each, with just enough clues for one answer), cryptograms (a saying, or your own text, with each letter as a number or a symbol and a few letters given in the key) and word ladders (change one letter at a time, every step a real word), each with an answer page and words in every language Inkline speaks.
- **Spelling, speed tests and drawing:** look, say, cover, write, check sheets (fold along the line to cover the words), unscramble sheets with mixed-up or missing letters, times-table speed tests (25, 50 or 100 facts from the tables you choose, mixed up or in order, times, sharing or both, a time and score box and a progress chart to colour in, with an answer page) and draw what you read (sentences for each age, or your own, each over a box to draw in).
- **Coordinates and memory cards:** plot the points to draw a picture (a house, a star, a cat… on a 0–10 grid, or in four quadrants for older children, joined up on the answer page), Battleships grids for two players, and memory cards to cut out (pictures, words and pictures, numbers and dots, or your own pairs, 8 to 24 a page) with an optional page of card backs that lands behind each card when printed double-sided.
- **Calendars and planners:** a month calendar for any month (next month to start with), weeks starting on Monday or Sunday, or a weekly planner with lines for each day, with a mandala, woven tiles, flow lines or contours to colour above it.
- **Booklets:** turn any pattern (or every pattern but name pages, mixed) into a multi-page PDF with a cover, a title and name line, page numbers, difficulty that ramps up page by page, a *New design for this page* button to swap any single page (answers follow), and answer pages for mazes, dot-to-dots, sudoku, word search, nonograms, spot the difference and kakuro. Or build a booklet page by page: *Edit pages one by one* lists its pages, each with a small picture and its own pattern, options and complexity (so each word search page can have its own words, and each name page its own name), to add, drag into order, duplicate (with a new design) or remove.
- **Projects:** *File → Save project* (Ctrl+S) keeps everything you're making in one `.inkline` file, with the photos inside it, so it opens again later or on another computer even if the original pictures have moved. *File → Open project…* (Ctrl+Shift+O) and *Open recent project* bring it back; the window title shows the project's name and whether it has unsaved changes. Installed from a package, project files get their own icon in your file manager and open in Inkline with a double-click; `python3 inkline.py book.inkline` does the same from a terminal. If Inkline closes unexpectedly, the next start offers to bring back the work you hadn't saved: while there's unsaved work, a copy is kept in the settings folder at most once a minute.
- **Presets:** twenty-seven built-in starting points (start fresh, a week's worksheet pack, colouring page, name page, maze worksheet, maze booklet, name maze, word search booklet, sudoku booklet, nonogram booklet, dot-to-dot booklet, spot the difference booklet, logic puzzle booklet, times-table speed test, memory cards with backs, Battleships, kakuro booklet, calendar for next month, colour-by-number mandala, halftone photo, engraved photo, stippled photo, colour-by-number photo, photo dot-to-dot, photo nonogram, photo colouring page, wall poster) plus your own saved settings.
- **Picks up where you left off:** settings and the current design are restored on the next start (*Presets → Start fresh* resets them). Shortcuts: Ctrl+P print, Ctrl+S save project, Ctrl+Shift+S save project as, Ctrl+E save PDF, Ctrl+Shift+E save PNG, Ctrl+O open image, Ctrl+Shift+O open project, Ctrl+N new design, Ctrl+Shift+N more designs (six to choose from), Ctrl+Z undo, Ctrl+Shift+Z redo, Ctrl+H undo history, ←/→ booklet pages. Recently opened photos are under *File → Open recent image*.
- **Printer test page:** true-size squares and rulers, edge-margin marks, every dither style and dot size, and every line weight, to check your printer at a glance.
- **Print-ready output:** Letter or A4 at 150/300 dpi, with Print, Save PNG and Save PDF at true paper size. Booklets and photo books can print or save only some pages (*Paper → Print or save only*, e.g. `3-5, 8, cover`). The preview hatches the edge your printer can't reach and warns if the design runs into it.
- **Posters:** print any design or photo big across 2×1 up to 4×4 sheets, with overlap strips, trim marks and sheet labels (A1, A2…) for assembly.
- **English, Spanish, French, Portuguese, German, Italian and Dutch:** Inkline uses your system's language, or choose one under *View → Language*. The window and everything printed are translated; word searches, crosswords and handwriting sheets use words and an alphabet in that language.
- **SVG export:** generated designs save as true vector lines at real paper size, for Inkscape, Cricut/Silhouette cutting machines and laser cutters.

## Install

Each [release](https://github.com/Gshoe2006/inkline/releases) has a package for Windows, macOS and most Linux systems:

| You use | Download | Install |
| --- | --- | --- |
| Debian 12+, Ubuntu 22.04+, Linux Mint, Pop!_OS | `inkline_<version>-1_amd64.deb` | `sudo apt install ./inkline_<version>-1_amd64.deb` |
| Fedora, openSUSE | `inkline-<version>-1.x86_64.rpm` | `sudo dnf install ./inkline-<version>-1.x86_64.rpm` (openSUSE: `sudo zypper install --allow-unsigned-rpm …`) |
| Arch, CachyOS, Manjaro | `inkline-<version>-1-any.pkg.tar.zst` | `sudo pacman -U inkline-<version>-1-any.pkg.tar.zst` |
| Any distro, nothing installed | `inkline-<version>-x86_64.AppImage` | `chmod +x inkline-*.AppImage`, then run it |
| Any distro, sandboxed | `inkline-<version>.flatpak` | `flatpak install --user inkline-<version>.flatpak` |
| Ubuntu and other distros with Snap | `inkline_<version>_amd64.snap` | `sudo snap install --dangerous ./inkline_<version>_amd64.snap` |
| Any distro, your own Python | `inkline-<version>.run` | `sh inkline-<version>.run` |
| Raspberry Pi 4 or 5, ARM laptops (64-bit) | `inkline_<version>-1_arm64.deb`, `inkline-<version>-1.aarch64.rpm`, `inkline-<version>-aarch64.AppImage` or `inkline_<version>_arm64.snap` | As above |
| Windows 10 or 11 (64-bit) | `inkline-<version>-windows-setup.exe` | Run it; no administrator needed |
| Windows, without installing | `inkline-<version>-windows-portable.zip` | Unzip it anywhere (a USB stick too) and run `Inkline\Inkline.exe` |
| macOS 14 (Sonoma) or later, any Mac | `inkline-<version>-macos.dmg` | Open it and drag Inkline to Applications |
| …only Apple silicon, or only Intel (smaller) | `inkline-<version>-macos-arm64.dmg`, `inkline-<version>-macos-intel.dmg` | The same |

The ARM64 packages need a system from 2024 or later (glibc 2.39: Ubuntu 24.04, Debian 13, Raspberry Pi OS 13 "trixie" or newer), as PySide6's ARM64 build does.

The `.snap` file isn't from the Snap Store yet, so it's installed with `--dangerous` (not checked by the Store) and doesn't update by itself: Inkline says when there's a new one. The portable `.zip` keeps your settings in your user profile, like the installed app; to update it, Help → Check for updates downloads the new `.zip` for you to unzip in place of the old folder.

The Windows installer isn't signed yet, so Windows SmartScreen may warn that it's from an unknown publisher: choose **More info → Run anyway**. It adds Inkline to the Start menu, opens `.inkline` projects with a double-click, and uninstalls from Settings → Apps. Settings are kept in `%APPDATA%\Inkline`.

The macOS app isn't signed with an Apple Developer ID or notarized yet, so the first time you open it macOS says it can't check it: Control-click Inkline in Applications and choose **Open** (or open it from System Settings → Privacy & Security → **Open Anyway**). `inkline-<version>-macos.dmg` holds one app for both Apple silicon and Intel Macs (and is the one Help → Check for updates installs); the `-arm64` and `-intel` disk images are smaller, each for one kind of Mac. Help → Check for updates installs a newer version in place of the app, and checking while Inkline is closed uses a launchd agent of your own (`~/Library/LaunchAgents/io.github.gshoe2006.Inkline.update.plist`); its notification has no button, so Inkline offers the update when you next open it.

The `.deb` brings its own PySide6 (Debian and Ubuntu don't package a new enough one) and uses the system's Python and numpy. The AppImage brings everything, Python included; for it to appear in your app menu and open `.inkline` projects with a double-click, use an AppImage manager such as Gear Lever or AppImageLauncher.

## The window

Since 6.0 the options come a page at a time. The rail on the left chooses what you're working on: **Create** (a pattern made up for you, chosen from pictures of the patterns you used last, or from the full list) or **Photo** (converting one), then **Booklet**, **Poster** and **Print** (paper, page text, copies and names). **Ctrl+1** to **Ctrl+5** choose them from the keyboard. Each page fits without scrolling, and its sections take turns: opening one closes the others. **All patterns…** shows every pattern as a picture, by kind, with a search box; and a booklet built page by page has its pages changed right on the Booklet page (double-click one, or **Change this page**). **Presets**, **New design**, **More designs…**, the PDF, PNG and SVG saves and **Print…** are in the toolbar over the preview, and what just happened shows under it.

The first time 6.0 opens, a short tour points at the rail, the gallery, the toolbar, the sections and Settings in turn (Back, Next, Skip, or Escape); **Help → Tour of the window** shows it again.

To look closer at the page, pinch the preview (a touch screen or a trackpad), use **Ctrl+wheel**, or **View → Zoom in** / **Zoom out** (Ctrl++ and Ctrl+-). While it's zoomed, drag it (one finger, or the mouse) to look round; a double tap, a double click or **View → Whole page** (Ctrl+0) shows the whole page again. The zoom only changes the view: what's printed stays the same, and with a photo open the wheel still zooms the photo.

With the touch-screen layout (always on Android, or **Edit → Settings → Appearance**), a window narrower than 1000 px shows one column with a bottom bar; a tablet held sideways keeps the rail, gives the page the window's height and the options the room beside it, and shows **More designs…** in the toolbar when there's room.

## Accessibility

- **Screen readers** (Orca, NVDA, VoiceOver, TalkBack): every button, list, slider and check box has a name, in your language, and a tooltip that explains a button is read as its description. Lists are named by their labels; the rail's, the toolbar's and the booklet page list's buttons by what they do ("Move up", "Remove"); the preview says which page it shows ("Page 2 of 10: Maze"). A test (`tests/test_accessibility.py`) checks every control in the window, Settings and All patterns.
- **Keyboard:** Tab goes from the rail through the options to the toolbar and the preview, and the focused control is outlined in every theme. Ctrl+1 to Ctrl+5 choose the rail's pages, ← → turn a booklet's pages. In the gallery and **All patterns…** the arrow keys move between the pictures and Enter chooses one (Down from the search box goes into them; Enter there chooses the first match). In the booklet's page list and the photo book's list, Delete removes the selected one and Alt+↑ / Alt+↓ move it (Ctrl+D duplicates a page, Enter changes it). With the preview focused, + and - zoom it, 0 fits it and the arrow keys move round it.
- **High contrast:** turn on **High contrast** in **Edit → Settings → Appearance** and choose it: black on white, its text at least 10:1. Every theme's text is at least 4.5:1, and **Follow the system** follows your desktop's light or dark setting. Inkline draws its own colours, so it doesn't take a system high-contrast scheme (Windows' contrast themes) by itself: choose High contrast in Inkline too.
- **Larger text and touch-sized controls:** the touch-screen layout (Edit → Settings → Appearance) makes every control at least 48 px tall and its text a step larger, on any computer. The whole window also follows the system's display scaling (125%, 150%, 200%).
- **Easier-to-read pages:** *Print → Page text → Easier to read* prints in Atkinson Hyperlegible (recommended for dyslexia), with wider letter and word spacing, and *Cream paper* tints the page.

## Settings

**Edit → Settings…** (Ctrl+,) keeps what Inkline starts with in one place, and each change applies at once:

- **Printing:** the printer **Print** starts with (its unprintable edges show on the preview), and the paper size, orientation, margin and resolution new projects start with. **Use for this design** puts them on the design open now (Undo takes it back).
- **Saving:** what **Ctrl+E** saves: PDF (the default), PNG or SVG. The other formats stay in the File menu and under the preview, and Ctrl+Shift+E saves PNG (or PDF, when PNG has Ctrl+E).
- **Updates:** when Inkline checks for a new version, as **Help → Check for updates automatically**, and **Check now**.
- **Language:** as **View → Language**, from the next start.
- **Appearance:** the theme: following the system's light or dark look, Light, Dark, or the extra themes you turn on there (High contrast, Warm paper, Slate); every theme's text is at least 4.5:1 against its background, and High contrast's at least 10:1. **View → Theme** switches between the ones offered. **Use my desktop's style** is here too.

## Updates

The first time Inkline starts, it asks whether to check for updates. If you say yes, it asks GitHub for the latest release at most once a day, and when there's a newer version it says so: **Update now**, **What's new**, **Later** or **Skip this version**. **What's new** shows that release's notes in Inkline before you decide. **Help → Check for updates…** checks at any time, and **Help → Check for updates automatically** chooses when Inkline checks by itself: **Never**, **When Inkline starts** (at most once a day), or also while Inkline is closed, **At login**, **Every day** or **Every week**.

Checking while Inkline is closed is set up for you alone, with no administrator password: on Linux a systemd user timer (`~/.config/systemd/user/inkline-update.timer`), on Windows a Task Scheduler task of your own (or, for **At login**, an entry under your user's Run key). It runs `inkline --check-updates`, which shows a notification when there's a new version; its **Update now** button opens Inkline's update box, and if you miss the notification Inkline offers the update when you next open it. Choosing **Never** or **When Inkline starts** removes the timer or task, and so does uninstalling the Windows app or the `.run`; after removing the `.deb` or Arch package, the timer stays in your home folder but does nothing. A Flatpak checks only while it's open.

**Update now** downloads the package for how you installed Inkline, checks it against the SHA-256 digest GitHub lists for the release (a file that doesn't match is deleted, not installed), and installs it:

| Installed from | Updating |
| --- | --- |
| Windows installer | Runs the new installer, which closes Inkline and starts the new version |
| AppImage | Puts the new AppImage in place of the old one, then offers to restart |
| `.run` (for you) | Runs the new `.run`, then offers to restart |
| `.deb`, `.rpm`, Arch package, `.run --system` | Asks for an administrator password (through `pkexec`), installs (with `apt`, `dnf` or `zypper`, or `pacman`), then offers to restart. Without `pkexec`, it downloads the package and shows the command to install it |
| Mac app | Puts the new app (the universal one) in place of the old one, then offers to restart |
| Portable `.zip` (Windows) | Downloads the new `.zip` and opens its folder, to unzip in place of the old one once Inkline is closed |
| Flatpak, Snap, or run from source | Says there's an update and opens the release page |

On an ARM64 computer, the `.deb` and AppImage update to the ARM64 package.

The request sends nothing about you or your work: GitHub sees an ordinary web request, with the user agent `Inkline-update-check`.

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


How fast it is: `python3 inkline.py --benchmark` times start-up, every pattern and the photo styles without opening a window; [docs/performance.md](docs/performance.md) has the numbers and a Rust trial.

[docs/manual-tests.md](docs/manual-tests.md) lists what CI can't check (a real desktop, notifications, the update timer, a printer), to run on a release candidate; `inkline --check-updates --demo` shows the update notification at once.
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
sh packaging/debian/build-deb.sh          # dist/inkline_<version>-1_amd64.deb (needs dpkg-deb); add arm64 for ARM64
sh packaging/appimage/build-appimage.sh   # dist/inkline-<version>-x86_64.AppImage, or -aarch64 on ARM64 (needs uv)
sh packaging/rpm/build-rpm.sh             # dist/inkline-<version>-1.<arch>.rpm, for this machine (needs rpmbuild)
snapcraft                                 # inkline_<version>_<arch>.snap, from snap/snapcraft.yaml (needs LXD)
```

The macOS app is built on a Mac (see the top of `packaging/macos/build.py` for the universal one):

```sh
python3 packaging/macos/build.py --arch arm64   # or intel, or universal: dist/inkline-<version>-macos[-arm64|-intel].dmg
```

The Windows installer is built on Windows, with Python, `pip install PySide6-Essentials numpy pyinstaller` and [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```sh
python packaging/windows/build.py         # dist/Inkline/, the -windows-setup.exe and the -windows-portable.zip
```

`packaging/build.sh` outputs to `dist/`:

- `inkline-<version>-<rel>-any.pkg.tar.zst` — Arch / CachyOS / Manjaro package: `sudo pacman -U dist/inkline-*.pkg.tar.zst`
- `inkline-<version>.run` — universal installer for any distro: `sh dist/inkline-*.run` (`--system`, `--uninstall`, `--help`)

## Translations

Inkline is in English, Spanish (`es`), French (`fr`), Brazilian Portuguese (`pt`), German (`de`), Italian (`it`) and Dutch (`nl`). Each translation is `inkengine/locale/<code>.json`: the
English text as written in the code, and its translation. Word search themes, crossword words and clues, and the
default handwriting words are written in each language in `inkengine/patterns/words.py`, `crossword.py` and
`trace.py`.

**Check a translation.** The translations were written without a native speaker's review, so corrections are
very welcome: see [docs/translating.md](docs/translating.md) (also *Help → Help translate Inkline…*). Open a
[Suggest a better translation](https://github.com/Gshoe2006/inkline/issues/new?template=translation.yml) issue,
or check the lot on the [review pages](https://gshoe2006.github.io/inkline/) (one per language, nothing to
install: type better wordings, then copy them into the issue). Maintainers can make the pages or a spreadsheet
themselves:

```sh
python3 packaging/translation_sheet.py all inkline-review.html   # every language: search, filter, type better wording
python3 packaging/translation_sheet.py fr --needs-review         # inkline-fr-review.csv: what nobody has checked yet
python3 packaging/translations/apply.py suggestions.csv          # maintainers: put suggestions in, mark them reviewed
```

Which strings a native speaker has checked is kept in `packaging/translations/review.json`.

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
| `inkline.py` | Starts the app (with a project: `inkline.py FILE.inkline`; or `--selftest DIR`, `--benchmark`) |
| `inkapp/` | The window: sidebar, preview, menus, saving and printing, presets, project files (Qt Widgets) |
| `inkengine/` | The drawing engine: every pattern, photo style, booklet and poster, as PNG, PDF and SVG (also a command line) |
| `tests/` | Tests for `inkengine/`, with recordings of what Inkline 2.5 drew to match |
| `inkline.svg`, `icons/` | App icon; regenerate with `python3 packaging/make_icon.py` |
| `inkline.desktop` | Application menu entry |
| `inkline-mime.xml` | The `.inkline` project file type, so file managers open projects in Inkline |
| `rust/inkline_fast/` | Optional Rust versions of the slowest photo loops, shipped in most packages and used when installed ([docs/performance.md](docs/performance.md)) |
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

**Today the Windows installer and the macOS app are unsigned.** Windows SmartScreen may say the installer is from
an unknown publisher, and macOS asks before opening the app the first time (see [Install](#install)). The release
workflow signs them as soon as signing is set up for the repository, and until then says in each run that it
built them unsigned:

- **Windows** (`inkline-<version>-windows-setup.exe`, and `Inkline.exe` in it and in the portable zip): signed
  through SignPath Foundation from the first release after it accepts Inkline (only the installer), or with Azure
  Trusted Signing or a code signing certificate if one of those is set up instead.
- **macOS** (the `.dmg` disk images and `Inkline.app` in them): signed with an Apple Developer ID and notarized by
  Apple once a Developer ID certificate is set up. Until then the app is signed ad hoc only.

- Committers and reviewers: [Gshoe2006](https://github.com/Gshoe2006)
- Approvers: [Gshoe2006](https://github.com/Gshoe2006)

Every installer and disk image is built from this repository's source by the release workflow
(`.github/workflows/release.yml`) on GitHub's own runners. Releases signed through SignPath are each approved for
signing by hand. The options, their costs, the secrets each one needs and how to check a signed file:
[docs/code-signing.md](docs/code-signing.md).

**Privacy:** this program will not transfer any information to other networked systems unless specifically
requested by the user or the person installing or operating it. The only network request it makes on its own is the daily
update check, and only after the person using it says yes to it ([Updates](#updates)).

## Licence

Inkline is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version (GPL-3.0-or-later). See [LICENSE](LICENSE).

The joined-up handwriting fonts in `inkengine/fonts` are Playwrite GB J, US Trad, US Modern, AU NSW, NZ, IE, CA, ES, MX, FR Trad, BR, PT and DE VA (copyright 2023 The Playwrite Project Authors), under the SIL Open Font License 1.1; see [inkengine/fonts/OFL.txt](inkengine/fonts/OFL.txt).
