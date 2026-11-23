# Changelog

What changed in each Inkline release, newest first.

To release a new version, add a section headed `## <version>` (the same text as `VERSION`) in the
pull request that bumps `VERSION`. When it merges, `.github/workflows/release.yml` builds the packages
and publishes a GitHub Release with that section as its notes.

## 4.7.1 - 2026-11-23

Inkline 4.7.1 prints a class set of a page, and fixes the sidebar with your desktop's style.

### What's new

- **Several copies of a page.** **Paper → Copies** (1 to 100) makes Print and Save PDF give that many copies of a single page. With **A new design on each copy** (on by default), each copy has its own design: the first is the one shown, and printing again gives the same set. Turn it off for copies that are all alike. Copies isn't remembered, so a later print is one copy again.

### Fixed

- **The sidebar was cut off with View → Use my desktop's style.** Breeze's buttons and drop-downs are wider than Inkline's own, so the right edge of the sidebar (Delete, New design, the Pattern list) was hidden. The sidebar now widens to fit them.

### Good to know

- **Some pages have only a few designs.** Dot-to-dot has a handful of pictures and the smallest nonograms repeat sometimes, so with many copies some come out alike; the hint under Copies says so. A name page with nothing underneath has one design, so its copies are alike.
- **The print dialog's own Copies** prints the whole set again: 25 copies there set to 3 is 75 sheets. The status line says so.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-4.7.1-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_4.7.1-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.7.1-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-4.7.1-x86_64.AppImage && ./inkline-4.7.1-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-4.7.1.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.7.1.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 4.7.0 - 2026-11-23

Inkline 4.7 runs on Windows, and on Linux it can look like the rest of your desktop.

### What's new

- **Inkline for Windows.** `inkline-4.7.0-windows-setup.exe` installs Inkline on Windows 10 or 11 (64-bit), for you alone without needing an administrator, or for everyone on the computer. It adds Inkline to the Start menu, opens `.inkline` projects with a double-click, and uninstalls from Settings → Apps. Settings are kept in `%APPDATA%\Inkline`, and pages print with Windows' own fonts.
- **Use my desktop's style.** **View → Use my desktop's style** makes Inkline look like your other apps (Breeze, for example) instead of its own style; it's remembered. It works where Inkline uses your system's Qt: the Arch package and the `.run` installer. The Flatpak, the AppImage and the `.deb` bring their own Qt, which can't load your desktop's style, so the item is greyed out there and says why.

### Good to know

- **The Windows installer isn't signed yet,** so Windows SmartScreen may say it's from an unknown publisher. Choose **More info → Run anyway**.
- **Every release now has six packages,** each checked by running Inkline's self-test with it before anything is published.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-4.7.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_4.7.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.7.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-4.7.0-x86_64.AppImage && ./inkline-4.7.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-4.7.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.7.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 4.6.1 - 2026-11-22

Inkline 4.6.1 lets you edit a booklet's page list from the keyboard.

### What's new

- **Keys for the page list.** In a booklet built page by page, with the page list selected: **Delete** removes the selected page, **Ctrl+D** duplicates it with a new design, and **Alt+↑** / **Alt+↓** move it. They do just what the page's buttons do, each as one Undo step, and nothing where a button would be greyed out (the first page can't move up, the last page can't be removed). The buttons' tooltips name their keys, and after clicking one the keys keep working.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_4.6.1-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.6.1-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-4.6.1-x86_64.AppImage && ./inkline-4.6.1-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-4.6.1.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.6.1.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 4.6.0 - 2026-11-22

Inkline 4.6 comes in two new packages: a `.deb` for Debian and Ubuntu, and an AppImage that runs on almost any Linux system without installing anything.

### What's new

- **A package for Debian, Ubuntu and their relatives** (Linux Mint, Pop!_OS and others): `inkline_4.6.0-1_amd64.deb`. Install it with `sudo apt install ./inkline_4.6.0-1_amd64.deb`, and apt fetches what it needs. It works on Debian 12 and newer, and Ubuntu 22.04 and newer. Those systems don't package a new enough PySide6, so the `.deb` brings its own copy and uses your system's Python and numpy.
- **An AppImage:** `inkline-4.6.0-x86_64.AppImage`, one file with everything inside, Python included. Make it executable and run it. To have it in your app menu and open `.inkline` projects with a double-click, use an AppImage manager such as Gear Lever or AppImageLauncher.
- **Every release now has five packages,** and the release builds them all and checks the `.deb` and the AppImage by running Inkline's self-test with them before anything is published.

Nothing changes in how Inkline looks or works.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_4.6.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.6.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-4.6.0-x86_64.AppImage && ./inkline-4.6.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-4.6.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.6.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

Use one kind of package at a time: if you switch, remove the old one first, or you may see Inkline twice in your app menu.

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 4.5.0 - 2026-11-22

Inkline 4.5 lets you reuse pages between booklets, and tells you what's new after an update.

### What's new

- **Copy and paste booklet pages.** In a booklet built page by page, press Ctrl+C in the page list, or choose **Edit → Copy page**, to copy the selected page; **Edit → Copy all pages** copies them all. Then press Ctrl+V, or **Edit → Paste**, in this booklet or another Inkline window's: the pages go after the selected page, exactly as copied (same designs, same words), as one Undo step. A booklet still holds up to 40 design pages. A picture on the clipboard still pastes as a photo.
- **What's new after an update.** From the next update on, the first start of a new version shows what changed since the version you used last. **Help → What's new** shows it any time.

### Good to know

- **Copied pages paste while Inkline is open.** When you close Inkline, pages it copied stay on the clipboard as a plain list of their names.

### Fixed

- Inkline could crash as it quit after something had been copied to the clipboard.

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy. Your presets, settings, projects, recent files and printer carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.5.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-4.5.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.5.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 4.4.0 - 2026-11-22

Inkline 4.4 lets you choose a design from several, instead of trying New design one guess at a time.

### What's new

- **More designs…** Under **New design** in the Design section (or **View → More designs…**, Ctrl+Shift+N), it shows six designs side by side. Click the one you like, or press **Show six more** for another six. Choosing is one Undo step.
  - It offers whatever New design would change: a single page; a quick booklet, each option shown on the page you're looking at; or, in a booklet built page by page, just the page you're editing. A poster's design is shown on one page.
  - The designs are drawn in the background and appear as they're ready; colour-by-number pages take a moment and say "Drawing…" until then.
  - Use Tab to move between designs, and Enter or Space to choose one.

### Fixed

- **New design is always called "New design" in Undo,** even when it also resets pages you'd swapped in a booklet (it used to say "Changes").

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy. Your presets, settings, projects, recent files and printer carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.4.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-4.4.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.4.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 4.3.0 - 2026-11-22

Inkline 4.3 gives you more say over what a booklet prints: which answers go in the back, and which pages come out of the printer.

### What's new

- **Leave a page's answer out.** In a booklet built page by page, choose a puzzle or colour-by-number page and untick **Include its answer in the answer pages** in the Design section. That page's solution stays out of the answer pages, which is handy for a hard puzzle without its solution, or a teacher's copy. The page's row in the list ends "· no answer", and the switch is saved in projects.
- **Print or save only some pages.** For booklets and photo books, **Paper → Print or save only** takes pages as the pager counts them, such as `3-5, 8`, `cover` or `answers`. Leave it empty for every page.
  - A line under it says what will print, such as "Prints and saves pages 3–5 and 8 of 14", or what's wrong with what you typed.
  - Fold-and-staple books print the whole sheets that hold those pages, both sides.
  - A PDF of some pages is named for them (…`-p3-5_8.pdf`).
  - The choice isn't remembered: it's cleared when you switch to another book, so a reprint can't quietly shorten a later print.

### Changed

- **The print dialog's own page range is switched off.** Choose pages under **Paper → Print or save only** instead.
- **Fold-and-staple messages count sheets,** for example "Saved 2 sheets (both sides)".

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy. Your presets, settings, projects, recent files and printer carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.3.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-4.3.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.3.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 4.2.0 - 2026-11-22

Inkline 4.2 gets your work back if it closes unexpectedly, and makes word search pages in a booklet easier to work with.

### What's new

- **Get unsaved work back after a crash.** While you have unsaved work that isn't remembered anywhere else (photos, a booklet's own pages, or changes to an open project), Inkline quietly keeps a copy, at most once a minute.
  - If Inkline closes unexpectedly, the next start asks whether to recover it, showing when it was saved and what it holds, such as "16:09 · Maya's book · 12 pages · 3 photos". Choose **Recover** or **Discard**.
  - Recovered work counts as unsaved, so Inkline asks before closing, and **Save project** goes back to the project it came from.
  - Saving, or closing Inkline normally, removes the copy. With two Inklines open at once, neither mistakes the other for a crash.
- **Words that didn't fit, in booklets too.** The "Left out: …" note, which names words too long for the grid, now appears for a word search page in a booklet, not only for a single page.
- **Pages you can tell apart.** In a booklet built page by page, each row says what makes its page different: a word search's words ("Ocean", "Your words"), a word maze's word, or a name page's name. Hover over "Your words" to see them.

### Good to know

- **Where the copy lives:** in the settings folder (`~/.config/inkline`, or `~/.var/app/io.github.gshoe2006.Inkline/config/inkline` for the Flatpak), as an ordinary `.inkline` project file. It's removed as soon as it isn't needed.
- **Settings on their own aren't copied:** they're already remembered between runs, as before.

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy. Your presets, settings, projects, recent files and printer carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.2.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-4.2.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.2.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 4.1.0 - 2026-11-22

Inkline 4.1 makes a booklet's page list easier to find your way around, and lets your file manager open projects.

### What's new

- **A picture of each page.** In a booklet built page by page, every row of the page list now shows a small picture of that page: its pattern, design and complexity, with the booklet's line weight, border, title and paper. Pictures are drawn in the background, so the list never waits, and editing a page redraws only its own picture.
- **Drag pages to reorder them.** Drag any page in the list to a new place, any distance, and drop it. A line shows where it will land, the whole move is one Undo step, and the page you're editing stays selected. ↑ ↓ still move a page one place.
- **Open projects from your file manager.** `.inkline` projects now have their own icon, and double-clicking one opens it in Inkline, as does *Open with → Inkline*. This works with the Arch package, the `.run` installer and the Flatpak.

### Fixed

- After Undo or Redo in a booklet built page by page, the preview now shows the page the list highlights.
- Releases now attach only the three packages. Inkline 4.0.0 also had the self-test's sample files attached by mistake.

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy. Your presets, settings, projects, recent files and printer carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.1.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-4.1.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.1.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

If project files don't show their icon straight away, log out and back in, so your desktop picks up the new file type.

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 4.0.0 - 2026-11-22

Inkline 4.0 lets you build a booklet page by page, and keep your work in a project file to open again later.

### What's new

- **Booklets built page by page.** Turn on **Make a multi-page booklet**, then press **Edit pages one by one**. The booklet becomes a list of its pages, and nothing about it changes until you do.
  - Click a page to change it in the **Design** section: its pattern, that pattern's options (maze shape, word search words, name text and so on), complexity and colour by number. Line weight, border, title and paper stay the same for every page.
  - Each row shows the page's pattern and complexity, such as "3. Maze · 5/10", with buttons to move it up or down, duplicate it with a new design, or remove it. **Add page** adds one like the last, with a new design. A booklet holds up to 40 design pages.
  - **New design** changes only the page you're editing, and turning pages with ← → picks the page shown.
  - Every change to the list can be undone. **Back to quick booklet**, or choosing a preset, goes back to Design pages, Get harder and Mix.
- **Project files.** **File → Save project** (Ctrl+S) keeps everything you're making in one `.inkline` file: the settings, a booklet's own pages, and every photo with its crop.
  - The photos are stored inside the file, so a project still opens when the original pictures have moved, or on another computer.
  - **File → Open project…** (Ctrl+Shift+O) and **Open recent project** bring it back. You can also drop a project on the window. Installed from the Arch package or the `.run` installer, `inkline book.inkline` starts Inkline with that project open.
  - The window title shows the project's name, with a mark when it has unsaved changes. Inkline asks before unsaved work is lost, when you start a new project, open another, or close the window.

### Changed

- **New save shortcuts.** Ctrl+S now saves the project, and Ctrl+Shift+S saves it under a new name, as in most apps. **Save PDF is now Ctrl+E, and Save PNG is Ctrl+Shift+E.**
- **File → Open recent** is now **Open recent image**, next to **Open recent project**.
- **Settings read from files are checked.** Values from remembered settings, presets and projects are brought into their usual ranges, so a damaged file can't freeze or crash Inkline.

### Good to know

- **Work that isn't a project is remembered as before:** your settings come back the next time you open Inkline. Photos don't, so closing with unsaved photos now asks whether to save them as a project.
- **Projects with photos can be large,** because the photos are stored at full size.
- **Opening a project starts a fresh undo history.**

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy. Your presets, settings, recent photos and printer carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.0.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-4.0.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.0.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 3.4.2 - 2026-11-19

Inkline is now free software, and its Flatpak is ready for Flathub.

### What's new

- **Free software under the GPL.** Inkline is now licensed under the GNU General Public License, version 3 or (at your option) any later version. You're free to use it, study it, share it and change it; if you share a changed version, it stays free under the same licence. The full text is in `LICENSE`, and every package now includes it.
- **Flatpak on a newer runtime.** The Flatpak now builds on the freedesktop 26.08 runtime, the latest, with Python 3.14.
- **Getting ready for Flathub.** The Flatpak's app details now include screenshots and links, and the repository has a manifest for Flathub. Once Inkline is accepted there, you'll be able to install it from GNOME Software, KDE Discover and other app stores, with updates arriving automatically.

Nothing changes in how Inkline looks or works.

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy. Your presets, settings, recent photos and printer carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-3.4.2-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-3.4.2.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-3.4.2.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```
If you built the Flatpak before, the first build of 3.4.2 downloads the 26.08 runtime (about 1 GB). Afterwards you can remove the old one with `flatpak uninstall --user --unused`.

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 3.1.0 - 2026-11-19

Inkline 3.1 lets you take back changes and get back to photos you've used before.

### What's new

- **Undo and Redo.** The new **Edit** menu has Undo (Ctrl+Z) and Redo (Ctrl+Shift+Z). They cover every change to a design: settings, New design, presets, switching between Make and Convert, crops, and adding, moving or removing photos. The menu names what it will undo, such as "Undo Line weight" or "Undo “Maze booklet with answers”".
  - A whole slider drag, or typing in one field, is one step, so a single Undo takes it all back.
  - Each click is its own step.
  - Turning pages, choosing a photo to crop, saving and printing aren't changes, so they don't add steps.
- **Undo history.** **Edit → History…** (Ctrl+H) opens a list of every step. Click any step to go straight back, or forward, to that point. The top row, "Start", is how things were before your first change.
- **Recent photos.** **File → Open recent** lists the last 10 photos you opened, newest first, and keeps them between runs. Hover over one to see where it is on disk, and choose one to open it again. If a photo has been moved or deleted, Inkline says so and takes it off the list. **Clear list** empties it.

### Good to know

- **The undo history lasts for one session.** It starts fresh each time you open Inkline. Your settings and designs are still restored as before.
- **Text fields keep their own Ctrl+Z** while you're typing in them.
- **The recent list is saved in `~/.config/inkline/recent.json`,** next to your presets.

### Upgrading

Nothing changes in what Inkline needs: Python 3 with PySide6 and numpy, as in 3.0. Your presets and settings carry over.

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-3.1.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-3.1.0.run            # or --system for every user
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it's about printing.

## 3.0.0 - 2026-11-18

Inkline is now a native Linux app. The web page and the browser engine it ran in are gone. A new Python drawing engine makes every design, and a native Qt window sits on top. Your designs, settings and presets come with you.

What’s new
A native window. It has the same layout as 2.x: options on the left, the true-to-scale page on the right. There’s a new File / View / Help menu bar, and light and dark follow your desktop as you switch.
Sharper PDFs. PDFs are now drawn as vector lines instead of a picture of the page, so they stay crisp at any zoom and print at your printer’s full resolution. Dithered photos (smooth, crisp, pattern and solid) are still made of pixels.
A smaller install. Inkline no longer needs Qt WebEngine. It needs PySide6 and numpy.
A command line. Everything the window makes can be made from a terminal, which is handy for batches and scripts:
python3 -m inkengine maze --shape heart --answers -o heart.pdf
python3 -m inkengine mandala --booklet 12 --mix --fold -o book.pdf
python3 -m inkengine photo --image cat.jpg --style halftone -o cat.pdf
python3 -m inkengine testpage -o test.pdf

Run python3 -m inkengine --help for every option.

The same designs as 2.x

Each pattern was checked against what Inkline 2.5 drew, line by line: mazes, mandalas, woven tiles, contours, flow lines, dot-to-dots, sudoku, word search, nonograms and colour by number. A design number (seed) from 2.x gives the same design in 3.0. Booklets, fold-and-staple books, posters, photo books, answer pages and the printer test page all carry over too.

A few small differences:

Photos are cropped and scaled by Qt, not a web browser, so a converted photo can differ from 2.x by the odd dot.
Word mazes and name pages use the fonts installed on your computer, as before, so their letters can look slightly different from one machine to another.
Colour-by-number photos take a few seconds to work out. The preview shows “converting photo…” meanwhile, and the window stays usable.
Upgrading

Your saved presets and last settings are read from ~/.config/inkline as before.

Arch / CachyOS / Manjaro

sudo pacman -U inkline-3.0.0-1-any.pkg.tar.zst

The package now depends on python-numpy instead of qt6-webengine and qt6-webchannel. If nothing else uses those two, you can remove them afterwards: sudo pacman -Rs qt6-webengine qt6-webchannel.

Any other distro

sh inkline-3.0.0.run            # or --system for every user

The installer replaces a 2.x install in place. It needs Python 3 with PySide6 and numpy, and it tells you how to install them if they’re missing:

Debian / Ubuntu: sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtprintsupport python3-numpy
Fedora: sudo dnf install python3-pyside6 python3-numpy
Any distro, for your user only: pip install --user PySide6 numpy
Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your distro, and the printer if it’s about printing.

## 2.3.0 - 2026-11-17

Inkline 2.3 makes real little books: fold them, fix single pages, fill them with word searches, and add a new engraved-photo look.

### New in 2.3

**Fold-and-staple books.** Booklets and photo books can print two half-size pages on each side of the paper (Letter → 5.5 × 8.5 in, A4 → A5). Print double-sided, flipping on the short edge, then stack, fold and staple: every page lands in reading order. The preview shows the actual printed sheets, and blank pages are added at the end when needed.

**Swap a single booklet page.** *New design for this page* redraws just the page you're looking at (or the cover art), and its answer page follows. *Back to original* undoes it, and swaps are remembered with your settings.

**Word search, with answers.** Themes (Animals, Ocean, Space, Food, Weather, Sports) or your own word list. Grids run from 8×8 with words across and down, to 16×16 with words in all eight directions. **Every word appears exactly once**, and if one of your words can't (too long, or hidden inside another like RAIN in RAINBOW), the app tells you why. Answer pages circle every word.

**Engraving-style photos.** A new photo style of parallel wavy lines that swell in dark areas, like a banknote portrait, with tone accurate to within 4%. It's the **first photo style that saves as SVG**, ready for laser engravers, cutting machines and pen plotters.

### Behind the scenes
Every pull request now has to pass a fold-order proof (books of 4–40 pages read in order), a word search proof (every word exactly once, checked independently), a page-swap check, and a tone check covering engraving, on top of the existing tests.

### Install

**Arch / CachyOS / Manjaro** (upgrades 2.2 in place)
```sh
sudo pacman -U inkline-2.3.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-2.3.0.run              # just for you
sudo sh inkline-2.3.0.run --system   # for everyone
```
Uninstall with `sh inkline-2.3.0.run --uninstall`. Needs Python 3 with PySide6 (Qt WebEngine); the installer prints the exact package to install if it's missing.

Verify a download with `sha256sum -c SHA256SUMS --ignore-missing`.

Full changes: #17 fold-and-staple books · #18 page swap · #19 word search · #20 engraving photos · #21 release

## 2.2.0 - 2026-11-17

Inkline 2.2 rounds out the puzzle book, makes printing checkable, and keeps the window responsive.

### New in 2.2

**Sudoku, with answers.** A new pattern where **every puzzle has exactly one solution**, from Easy (about 48 starting numbers) to Expert (about 25). Booklet answer pages show each solution, and a new preset makes a sudoku booklet in one click.

**Name colouring pages.** Type a name or phrase ("Maya", "Happy Birthday") and get big puffy bubble letters to colour, wrapped onto as many lines as fit best, with an optional flow-line, contour or woven background.

**Printer test page.** *Paper → Show the printer test page*, then print at 100%. It has true-size 2 in and 5 cm squares and rulers (is your printer shrinking pages?), corner marks showing how close to the edge it can print, every dither style and dot size, and every line weight.

**No more freezing on big jobs.** Photo conversion now runs in the background. The worst case, a 4×4 photo poster in line-drawing style, used to freeze the window for **5 seconds**. Now it's **0.05 s**, and it finishes in about half the time. Multi-page saves show a progress bar.

### Fixed
- **Halftone photos printed much too dark.** A 35% grey came out 55% inked, and everything past 65% printed solid black. Dot sizes now match each grey level to within 3%. *(Found by measuring the new test page.)*
- **Easy dot-to-dot flowers looked like cogs.** They now get enough dots per petal to read as rounded petals.

### Install

**Arch / CachyOS / Manjaro** (upgrades 2.1 in place)
```sh
sudo pacman -U inkline-2.2.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-2.2.0.run              # just for you
sudo sh inkline-2.2.0.run --system   # for everyone
```
Uninstall with `sh inkline-2.2.0.run --uninstall`. Needs Python 3 with PySide6 (Qt WebEngine); the installer prints the exact package to install if it's missing.

Verify a download with `sha256sum -c SHA256SUMS --ignore-missing`.

Full changes: #11 sudoku · #12 name pages · #13 printer test page and halftone fix · #14 background worker · #15 dot-to-dot flowers · #16 release

## 2.1.0 - 2026-11-17

Inkline 2.1 adds photo colouring books, dot-to-dot puzzles, and an app that picks up where you left off.

### New in 2.1

**Photo colouring books.** Turn several photos (family, pets, a holiday) into one colouring-book PDF. Add them in a batch, reorder them, and **crop each photo separately**. You also get an optional cover, a title and name line, and page numbers.

**Dot-to-dot puzzles.** A new pattern: star, heart, fish, house, flower or a mystery blob, with 18 to 90 dots. Numbers are placed so they never collide, and dot 1 is ringed. Booklet **answer pages** now show the finished picture next to solved mazes, and a new preset makes a dot-to-dot booklet in one click.

**Picks up where you left off.** Inkline reopens with your last settings and the same design. *Presets → Start fresh* resets everything.

**Keyboard shortcuts.** Ctrl+P print · Ctrl+S save PDF · Ctrl+Shift+S save PNG · Ctrl+N new design · ← / → turn booklet and photo book pages.

**Version shown in the app**, in the sidebar and the window title.

### Behind the scenes
- Every change is now tested automatically on GitHub: the full self-test (every pattern, photo conversion, booklets, posters, photo books), a check of every output file, and an install/uninstall of the universal installer.
- The Arch package now ships its `VERSION` file.

### Install

**Arch / CachyOS / Manjaro** (upgrades 2.0 in place)
```sh
sudo pacman -U inkline-2.1.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-2.1.0.run              # just for you
sudo sh inkline-2.1.0.run --system   # for everyone
```
Uninstall with `sh inkline-2.1.0.run --uninstall`. Needs Python 3 with PySide6 (Qt WebEngine); the installer prints the exact package to install if it's missing.

Verify a download with `sha256sum -c SHA256SUMS --ignore-missing`.

Full changes: #6 photo books · #7 GitHub checks · #8 dot-to-dot · #9 version, remembered settings, shortcuts · #10 release

## 2.0.0 - 2026-11-17

Inkline 2.0 goes from single pages to finished printables: whole books, posters, and vector files for cutting machines.

### New in 2.0

**Booklets.** Turn any pattern, or all five mixed, into one multi-page PDF: 2–40 pages, optional easy-to-hard difficulty, a cover, a title and "Name ____" line, and page numbers. Maze booklets get **answer pages** with the solution drawn on the same maze.

**Posters.** Print any design **or photo** big, across 2×1 up to 4×4 sheets. Sheets overlap (¼ in or ½ in) and carry trim marks and labels (A1, A2…) so they're easy to assemble. Lines and text scale up with the poster.

**SVG export.** Save generated designs as true vector lines at real paper size, for Inkscape, Cricut/Silhouette cutting machines and laser cutters.

**Photo cropping.** Rotate in 90° steps, zoom up to 400%, and move the photo with sliders, by dragging the preview, or by scrolling to zoom.

**Presets.** Six built-in starting points: colouring page, maze worksheet, maze booklet, halftone photo, photo colouring page, wall poster. Save your own settings too; they're kept in `~/.config/inkline/presets.json`.

### Improved
- **Cleaner line drawing** from photos: continuous outlines and no grain specks. On a grainy test photo, specks went from 111 to 0 and long strokes from 5 to 20.
- **Fixed** a white band and curved corners at the top of dithered photos when Contrast was above 100%.

### Install

**Arch / CachyOS / Manjaro** (upgrades 1.0 in place)
```sh
sudo pacman -U inkline-2.0.0-1-any.pkg.tar.zst
```

**Any other distro**
```sh
sh inkline-2.0.0.run              # just for you
sudo sh inkline-2.0.0.run --system   # for everyone
```
Uninstall with `sh inkline-2.0.0.run --uninstall`. Needs Python 3 with PySide6 (Qt WebEngine); the installer prints the exact package to install if it's missing.

Verify a download with `sha256sum -c SHA256SUMS --ignore-missing`.

Full changes: #1 booklets · #2 SVG export · #3 posters · #4 polish · #5 release

## 1.0.0 - 2026-11-17

First release of Inkline: a Linux desktop app that converts photos to, or generates, black & white images for printing.

### Install

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-1.0.0-2-any.pkg.tar.zst
```
Remove with `sudo pacman -R inkline`.

**Any other distro**
```sh
sh inkline-1.0.0.run            # just for you, no password
sudo sh inkline-1.0.0.run --system   # for everyone
```
Remove with `sh inkline-1.0.0.run --uninstall`. Needs Python 3 with PySide6 (Qt WebEngine); the installer tells you the exact package to install if it's missing.

Check a download with `sha256sum -c SHA256SUMS --ignore-missing`.

### What's in it
- **Make one up:** mandala colouring pages, mazes, woven tiles, topographic contours, flow lines
- **Convert a photo:** smooth, crisp and pattern dithering, halftone dots, solid black & white, line drawing
- Letter or A4 at 150/300 dpi, with Print, Save PNG and Save PDF at true paper size
- App icon in all standard sizes, with a simplified drawing for 16–32 px

Package release `-2` adds the new icon; the app itself is unchanged from `-1`.
