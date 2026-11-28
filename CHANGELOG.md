# Changelog

What changed in each Inkline release, newest first.

To release a new version, add a section headed `## <version>` (the same text as `VERSION`) in the
pull request that bumps `VERSION`. When it merges, `.github/workflows/release.yml` builds the packages
and publishes a GitHub Release with that section as its notes.

## 6.3.0 - 2026-11-28

Inkline 6.3 opens twice as fast, draws photo styles up to four times faster, adds six new things to make for the classroom, and makes it easy for native speakers to improve the translations.

### What's new

- **Faster.** The window opens in about half the time it did. Photo styles are drawn up to four times faster (stippling 3.3 s → 1 s, the dithers about 4×, line drawings 1.5×) by a small built-in Rust module in every package that brings its own Python (Windows, macOS, `.deb`, `.rpm`, AppImage, Snap, Flatpak); pages come out exactly the same.
- **Look, say, cover, write, check.** A spelling practice sheet from your own words or a theme, with three tries to write and tick.
- **Missing letters.** Unscramble has a second sheet: the words with letters left out to fill in.
- **A spelling week.** A worksheet pack on spelling now makes the week from one word list: Monday look, say, cover, write, check; Tuesday a word search; Wednesday missing letters; Thursday a crossword; Friday the spelling test, with answers at the end.
- **Times-table speed test.** 25, 50 or 100 numbered facts (times, sharing or both, chosen tables or by age), a time and score box, an optional chart to track progress, and an answer page laid out like the sheet.
- **Draw what you read.** Short sentences at three reading levels, in all seven languages (or your own), each with a box to draw it in.
- **Coordinate grids.** Plot the points to draw a picture (0 to 10, or four quadrants for older children), with the picture as the answer; or Battleships, with a grid for your ships and one for theirs.
- **Memory cards.** Pairs to cut out and match: pictures, words and pictures, numbers and dots, or your own pairs, with an optional page of backs lined up for double-sided printing.
- **Help translate Inkline.** Every translation is marked until a native speaker has read it; **Help → Help translate Inkline…** explains how to review them on a simple web page and suggest better wording.

### Fixed

- The first-start tour was see-through with **View → Use my desktop's style** on; it has its own background now.
- A spelling pack's Wednesday is called Missing letters everywhere, and the speed test's options and undo steps use the same names.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over. If you have 5.6 or later, Inkline offers this update itself (**Help → Check for updates…**); otherwise, install it as below.

**Windows**
Run `inkline-6.3.0-windows-setup.exe`, or unzip `inkline-6.3.0-windows-portable.zip` and run `Inkline\Inkline.exe`.

**macOS**
Open `inkline-6.3.0-macos.dmg` and drag Inkline to Applications. It isn't signed by Apple yet, so the first time, Control-click Inkline and choose **Open**.

**Debian / Ubuntu / Linux Mint / Pop!_OS / Raspberry Pi OS**
```sh
sudo apt install ./inkline_6.3.0-1_amd64.deb     # or _arm64.deb on ARM64
```

**Fedora / openSUSE**
```sh
sudo dnf install ./inkline-6.3.0-1.x86_64.rpm    # or .aarch64.rpm; openSUSE: sudo zypper install --allow-unsigned-rpm …
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-6.3.0-1-any.pkg.tar.zst
```

**Snap**
```sh
sudo snap install --dangerous ./inkline_6.3.0_amd64.snap   # or _arm64.snap
```

**Any distro, nothing installed**
```sh
chmod +x inkline-6.3.0-x86_64.AppImage && ./inkline-6.3.0-x86_64.AppImage   # or -aarch64.AppImage
```

**Any other distro**
```sh
sh inkline-6.3.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-6.3.0.flatpak
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, Windows or macOS version), and the printer if it's about printing.

## 6.2.0 - 2026-11-27

Inkline 6.2 adds five new things to make (logic puzzles, cryptograms, word ladders, calendars and photo dot-to-dots), zoom for the preview, a better layout for tablets, and works better with screen readers and the keyboard. It also gets ready for Google Play and for signed Windows and Mac apps.

### What's new

- **Logic puzzle.** Einstein-style grids for children: three to five children, pets, colours, fruit or sports, and clues to work out who has what. Each puzzle has exactly one answer and can be solved with ticks and crosses; the answer page fills the grid.
- **Cryptogram.** A saying (or your own text) in a secret code of numbers or symbols, with a few letters given in the key; fewer as it gets harder.
- **Word ladder.** Change one letter at a time to get from one word to another (CAT → DOG), in all seven languages; optionally marks the letter that changes.
- **Calendar.** A month to colour in, with a mandala, woven tiles, flow lines or contours above it, or a weekly planner with lines to write on. Weeks start on Monday or Sunday; a booklet steps through the months, so twelve pages make a year.
- **Photo dot-to-dot.** A photo style that turns the outline of a photo's subject into 20–150 numbered dots, with the joined line as its answer.
- **Zoom the preview.** Pinch it, use a trackpad, Ctrl+scroll wheel, or **View → Zoom in / Zoom out / Whole page** (Ctrl++ / Ctrl+- / Ctrl+0). Drag to look around; double-click or double-tap to zoom in or show the whole page again. The page itself doesn't change.
- **Tablets.** Held sideways, the options get more room and the page is drawn larger; More designs appears in the touch toolbar when it fits.
- **Screen readers and the keyboard.** Every list, slider and field is read out with its label; the preview can be reached with Tab and says which page it shows; the gallery and All patterns work with the arrow keys and Enter; the photo list has Delete and Alt+↑/↓ like the page list; focused lists and the preview show an outline.
- **Three new presets:** Logic puzzle booklet with answers, Calendar for next month, Photo dot-to-dot.
- **For packagers and app stores:** an Android App Bundle for Google Play (when the signing key is set up), signed Windows and notarized Mac apps (once their certificates are added), corrected winget, Flathub and Homebrew files, and `inkline.py --benchmark` to time every pattern ([docs/performance.md](https://github.com/Gshoe2006/inkline/blob/main/docs/performance.md)).

### Fixed

- The Android app's launcher icon, and its target Android version (API 36, as Google Play asks).

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over. If you have 5.6 or later, Inkline offers this update itself (**Help → Check for updates…**); otherwise, install it as below.

**Windows**
Run `inkline-6.2.0-windows-setup.exe`, or unzip `inkline-6.2.0-windows-portable.zip` and run `Inkline\Inkline.exe`.

**macOS**
Open `inkline-6.2.0-macos.dmg` and drag Inkline to Applications. It isn't signed by Apple yet, so the first time, Control-click Inkline and choose **Open**.

**Debian / Ubuntu / Linux Mint / Pop!_OS / Raspberry Pi OS**
```sh
sudo apt install ./inkline_6.2.0-1_amd64.deb     # or _arm64.deb on ARM64
```

**Fedora / openSUSE**
```sh
sudo dnf install ./inkline-6.2.0-1.x86_64.rpm    # or .aarch64.rpm; openSUSE: sudo zypper install --allow-unsigned-rpm …
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-6.2.0-1-any.pkg.tar.zst
```

**Snap**
```sh
sudo snap install --dangerous ./inkline_6.2.0_amd64.snap   # or _arm64.snap
```

**Any distro, nothing installed**
```sh
chmod +x inkline-6.2.0-x86_64.AppImage && ./inkline-6.2.0-x86_64.AppImage   # or -aarch64.AppImage
```

**Any other distro**
```sh
sh inkline-6.2.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-6.2.0.flatpak
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, Windows or macOS version), and the printer if it's about printing.
## 6.1.0 - 2026-11-26

Inkline 6.1 comes in sixteen packages: on Fedora and openSUSE, on Intel Macs, on Raspberry Pi and other ARM computers, as a Snap and as a portable Windows app. It adds a layout for touch screens, and fixes a rare crash.

### What's new

- **More ways to install.** Each release now has a Fedora / openSUSE `.rpm` (x86-64 and ARM64), a Snap (x86-64 and ARM64), a `.deb` and an AppImage for ARM64 (Raspberry Pi 4 and 5, ARM laptops: Ubuntu 24.04, Debian 13, Raspberry Pi OS 13 or newer), and a portable Windows `.zip` that runs from a folder or a USB stick without installing.
- **Every Mac.** `inkline-<version>-macos.dmg` is now one app for both Apple silicon and Intel Macs; `-macos-arm64.dmg` and `-macos-intel.dmg` are smaller, each for one kind. Inkline needs macOS 14 (Sonoma) or newer (6.0 said 12, wrongly: the Qt it's built on needs 14).
- **Touch screens.** **Edit → Settings → Appearance → Touch-screen layout** makes every control big enough for a finger and puts the menus in a **Menu** button; in a narrow window (a tablet held upright), the options and the preview take turns over a bar along the bottom.
- **Updates** install the right package for each of these (with `dnf` or `zypper` for the `.rpm`, the ARM64 package on ARM64), and point the Snap and the portable app to the release page.
- **App stores.** Each release now writes what Flathub, winget, Homebrew and the AUR need ([docs/publishing.md](https://github.com/Gshoe2006/inkline/blob/main/docs/publishing.md)).

### Fixed

- A rare crash when a window closed while its page pictures were being drawn.
- Settings fits a small screen again in every language.

### Upgrading

Nothing changes in what Inkline needs on Windows and Linux; on a Mac, macOS 14 or newer. Your presets, settings, projects, recent files and printer carry over. If you have 5.6 or later, Inkline offers this update itself (**Help → Check for updates…**); otherwise, install it as below.

**Windows**
Run `inkline-6.1.0-windows-setup.exe`, or unzip `inkline-6.1.0-windows-portable.zip` and run `Inkline\Inkline.exe`.

**macOS**
Open `inkline-6.1.0-macos.dmg` and drag Inkline to Applications. It isn't signed by Apple yet, so the first time, Control-click Inkline and choose **Open**.

**Debian / Ubuntu / Linux Mint / Pop!_OS / Raspberry Pi OS**
```sh
sudo apt install ./inkline_6.1.0-1_amd64.deb     # or _arm64.deb on ARM64
```

**Fedora / openSUSE**
```sh
sudo dnf install ./inkline-6.1.0-1.x86_64.rpm    # or .aarch64.rpm; openSUSE: sudo zypper install --allow-unsigned-rpm …
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-6.1.0-1-any.pkg.tar.zst
```

**Snap**
```sh
sudo snap install --dangerous ./inkline_6.1.0_amd64.snap   # or _arm64.snap
```

**Any distro, nothing installed**
```sh
chmod +x inkline-6.1.0-x86_64.AppImage && ./inkline-6.1.0-x86_64.AppImage   # or -aarch64.AppImage
```

**Any other distro**
```sh
sh inkline-6.1.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-6.1.0.flatpak
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, Windows or macOS version), and the printer if it's about printing.

## 6.0.0 - 2026-11-26

Inkline 6.0 has a new window: one place to pick a design, short pages instead of a long side panel, and themes to choose from. It also comes to the Mac, speaks Italian and Dutch, and adds early maths with pictures and an easier-to-read option.

### What's new

- **A new window.** A rail down the left switches between **Create**, **Photo**, **Booklet**, **Poster** and **Print** (Ctrl+1 to Ctrl+5), and each shows only its own settings, in sections that open one at a time. A toolbar across the top has **Presets**, **New design**, **More designs**, saving as PDF, PNG or SVG, and **Print**.
- **Pick a pattern by its picture.** **Create** starts with the six patterns you used last; **All patterns** shows every one, grouped (art, puzzles, maths, literacy, classroom), with a search box that finds them by name or description.
- **Themes.** **View → Theme** and **Edit → Settings → Appearance** offer Light, Dark, High contrast, Warm paper and Slate (or following the system), and Settings chooses which of them the menu shows.
- **A tour.** The first time Inkline opens, a short tour points out the rail, the gallery, the toolbar and the preview. **Help → Tour of the window** shows it again.
- **Edit booklet pages where they are.** On the **Booklet** page, double-click a page (or press Enter) to change its pattern and settings there, then go back to the list.
- **Early maths with pictures.** **Early maths** (under maths in **All patterns**), for ages 4–6: ten frames, number bonds, tens and ones as rods and cubes, and shapes to count, each with a box to write in, and the answers on the answer page.
- **Choose the worksheet pack's days.** Each day of the **Worksheet pack** can be any of 16 sheets, not only the usual week.
- **Easier to read.** **Print → Page text → Easier to read** sets the text in Atkinson Hyperlegible, spaced wider, for children who find reading hard; **Print → Paper → Cream paper** tints the page on screen and in PDFs (printing stays white).
- **Italian and Dutch.** Inkline is now also in Italiano and Nederlands: the window, reading passages, word searches, crosswords, bingo, sight words and handwriting (with Italian and Dutch school handwriting), with euros and decimal commas.
- **Inkline for macOS.** A disk image for Macs with Apple silicon (M1 and later, macOS 14 or newer). It updates itself like the other packages and can check for updates while it's closed.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over; the new window opens on **Create**. If you have 5.6 or later, Inkline offers this update itself (**Help → Check for updates…**); from 5.5 or earlier, install it as below.

**Windows**
Run `inkline-6.0.0-windows-setup.exe`.

**macOS**
Open `inkline-6.0.0-macos.dmg` and drag Inkline to Applications. It isn't signed by Apple yet, so the first time, Control-click Inkline and choose **Open** (or **System Settings → Privacy & Security → Open Anyway**).

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_6.0.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-6.0.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-6.0.0-x86_64.AppImage && ./inkline-6.0.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-6.0.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-6.0.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, Windows or macOS version), and the printer if it's about printing.

## 5.8.0 - 2026-11-26

Inkline 5.8 adds a Settings window, and can check for updates while it's closed.

### What's new

- **Settings.** **Edit → Settings…** (Ctrl+,) keeps what Inkline starts with in one place: the printer **Print** starts with; the paper size, orientation, margin and resolution new projects begin with (**Use for this design** puts them on the one open now); what **Ctrl+E** saves (PDF, PNG or SVG); when to check for updates; and the language.
- **Updates while Inkline is closed.** **Help → Check for updates automatically** now offers **Never**, **When Inkline starts**, **At login**, **Every day** or **Every week**. The last three check even while Inkline isn't open, and a notification's **Show the update** button opens the update box; a version found while Inkline was closed is offered when you next open it. It's set up for you alone, with no administrator password (a systemd user timer on Linux, a scheduled task on Windows); a Flatpak checks only while it's open.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over. If you have 5.6 or 5.7, Inkline offers this update itself (**Help → Check for updates…**); from 5.5 or earlier, install it as below.

**Windows**
Run `inkline-5.8.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.8.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.8.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.8.0-x86_64.AppImage && ./inkline-5.8.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.8.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.8.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.7.0 - 2026-11-26

Inkline 5.7 adds bingo cards, a different one for every child, and shows what's new in an update before you install it.

### What's new

- **Bingo cards.** **Pattern → Bingo cards** makes a card to mark as things are called: numbers (1–20, 1–40, or the classic 1–75 under B I N G O with a free square), words (any word theme, sight words, or your own list) or sums, where the card has the answers and the caller reads out the sums. Complexity sets the card, from 3 × 3 to 5 × 5. With **Paper → Copies** or **Names**, every child gets a different card, and **Answer pages** adds one caller's sheet for the whole class, with everything that can be called in boxes to tick off or cut out.
- **What's new before updating.** When Inkline offers an update, **What's new** now shows that version's notes in Inkline, then asks again whether to update.
- **Steadier updates.** Every package is now checked, before it's published, to say correctly how it was installed, so **Update now** always installs a newer version the right way.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over. If you have 5.6, Inkline offers this update itself (**Help → Check for updates…**); from 5.5 or earlier, install it as below.

**Windows**
Run `inkline-5.7.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.7.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.7.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.7.0-x86_64.AppImage && ./inkline-5.7.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.7.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.7.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.6.0 - 2026-11-26

Inkline 5.6 can update itself: it tells you when there's a new version, and downloads and installs it when you say so.

### What's new

- **Updates.** The first time Inkline 5.6 starts, it asks whether to check for updates. If you say yes, it checks once a day, and when there's a newer version it offers **Update now**, **What's new**, **Later** or **Skip this version**. **Help → Check for updates…** checks at any time, and **Help → Check for updates automatically** turns the daily check on or off.
- **Update now** downloads the package for how you installed Inkline and checks it against the checksum GitHub lists for the release; a file that doesn't match is deleted, not installed. The Windows installer, the AppImage and the `.run` install themselves. The `.deb`, the Arch package and `.run --system` ask for an administrator password first (or, without one, show the command to run). The Flatpak and copies run from source open the release page.
- **Privacy.** The check asks GitHub for the latest release and sends nothing about you or your work. It happens only if you said yes.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over. Install 5.6.0 by hand this once; from then on Inkline offers each new version itself.

**Windows**
Run `inkline-5.6.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.6.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.6.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.6.0-x86_64.AppImage && ./inkline-5.6.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.6.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.6.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.5.0 - 2026-11-26

Inkline 5.5 adds reading comprehension, sight words, graph and lined paper, and reward charts and certificates.

### What's new

- **Reading comprehension.** **Pattern → Reading comprehension** prints a short original passage for the age with questions about it: multiple choice for ages 5–7, then written answers too, with a "why" question for ages 9–11. Complexity picks the level. The answer page ticks the right answers and writes a model answer on the lines. There are 30 passages in each of Inkline's five languages.
- **Sight words.** Word searches, unscramble sheets and spelling tests can use the most common words children learn to read, in three stages (**Sight words: first**, **next** and **harder**), in every language. Choose a stage under **Booklet → Worksheet pack** for a week of twelve of its words: traced, in a crossword, a word search, an unscramble sheet and a spelling test.
- **Graph and lined paper.** **Pattern → Graph and lined paper** fills the page with squared paper, a dot grid, isometric dots, lined paper, handwriting lines or music staves. Complexity sets the spacing, from an inch apart down to 5 mm.
- **Reward charts and certificates.** **Pattern → Reward charts and certificates** makes a sticker chart (10 to 40 stickers to a star) or a "Well done!" certificate, with what it's for. With **Paper → Names**, each child gets their own with their name on it.

### Upgrading

Nothing changes in what Inkline needs (the joined-up handwriting fonts come with it). Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-5.5.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.5.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.5.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.5.0-x86_64.AppImage && ./inkline-5.5.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.5.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.5.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.4.0 - 2026-11-24

Inkline 5.4 speaks Portuguese and German, adds seasonal themes, fractions, number lines, times grids and symmetry, and opens long booklets faster.

### What's new

- **Inkline in Portuguese and German.** Choose **Português** (Brazil) or **Deutsch** under **View → Language**, or Inkline uses it when your system does. Everything in the window and on printed pages is translated, word searches and crosswords use words in that language (German grids write Ä as AE and ß as SS, as German crosswords do), and joined-up handwriting follows Brazil's or Germany's school style. Brazil, Portugal and Germany are also choices under **Handwriting → Style**. Corrections to the translations are welcome.
- **Seasonal themes.** Word searches, crosswords and worksheet packs have **Autumn**, **Halloween**, **Winter**, **Spring** and **Summer** themes, in every language.
- **Fractions, number lines and times grids.** **Pattern → Fractions, number lines and times grids**, with a **Worksheet** choice:
  - **Fractions of shapes:** circles, bars and squares cut into equal parts, to say what fraction is shaded, and at higher complexity to shade a fraction;
  - **Number lines:** marks to fill in, from counting in ones up to negative numbers and tenths;
  - **Times grid:** a multiplication square, from 5 × 5 to 12 × 12, with answers to fill in.

  Each has an answer page.
- **Symmetry.** **Pattern → Symmetry** shows half a picture of shaded squares and a mirror line, for the child to shade the other half. From complexity 7 there are two mirror lines, and one quarter to complete into four.

### Fixed

- **Long booklets open faster.** The page list now draws the pictures of the pages you can see first and the rest as you scroll, so a 40-page booklet is ready in about half the time.
- **The sidebar keeps its width** in every language with wider desktop fonts. Before, a label beside a button could push it wider.

### Upgrading

Nothing changes in what Inkline needs (the joined-up handwriting fonts come with it). Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-5.4.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.4.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.4.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.4.0-x86_64.AppImage && ./inkline-5.4.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.4.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.4.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.3.0 - 2026-11-23

Inkline 5.3 writes joined-up handwriting the way your country's schools teach it, and makes its SVGs look right everywhere.

### What's new

- **Your country's handwriting style.** With **Handwriting → Letters → Joined-up**, a new **Style** choice picks the school style:
  - your language's (as before);
  - England;
  - the United States (traditional or modern cursive);
  - Australia (New South Wales);
  - New Zealand;
  - Ireland;
  - Canada;
  - Spain;
  - Mexico;
  - France.

### Fixed

- **Joined-up letters in SVGs.** An SVG of a joined-up handwriting sheet now carries the letters' shapes, so it looks the same on any computer and in cutting machines' software, which don't have the handwriting fonts. Before, it came out in print letters there.

### Upgrading

Nothing changes in what Inkline needs (the joined-up handwriting fonts come with it). Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-5.3.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.3.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.3.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.3.0-x86_64.AppImage && ./inkline-5.3.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.3.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.3.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.2.0 - 2026-11-23

Inkline 5.2 turns this week's spelling words into a week of worksheets, and adds telling the time, money sums, division and joined-up handwriting.

### What's new

- **Worksheet packs in the Booklet section.** Choose a theme under **Booklet → Worksheet pack** (animals, food, space, ocean, weather or sports) and press **Make a week of worksheets**: five worksheets for the age chosen under **Age**, with a cover, a name line and the answers at the end. Crosswords now have ocean, weather and sports themes too. The preset still works.
- **This week's spelling words.** Choose **Spelling words (your own list)** as the pack's theme and type the words: Monday traces them, Tuesday is a crossword whose clues are each word's letters mixed up, Wednesday a word search, Thursday an unscramble sheet, and Friday a spelling test.
- **Unscramble** and **Spelling test** are new patterns of their own. Unscramble shows each word's letters mixed up in boxes, with a line to write the word on. Spelling test is a numbered line for each word you read aloud, in a new order each time, with the words on the answer page.
- **Telling the time.** **Pattern → Telling the time** draws clock faces to read (write the time under each) or to draw the hands on, or both. Complexity goes from o'clock and half past to quarters, five minutes and any minute.
- **Money, sharing and missing numbers.** The maths drill has three new kinds of sum:
  - **Money:** coins to count at first, then adding, taking away and change from a note, in pounds, euros or dollars, written the way each is written where it's used;
  - **Sharing (division):** every answer a whole number;
  - **Missing numbers:** "_ × 4 = 20".
- **Joined-up handwriting.** **Handwriting → Letters → Joined-up (cursive)** writes the sheet in the school handwriting style of Inkline's language (England's, Spain's or France's), with the guide lines set to the letters' loops.

### Fixed

- The booklet page list no longer tries to translate the names and words you type.

### Upgrading

Nothing changes in what Inkline needs (the joined-up handwriting fonts come with it). Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-5.2.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.2.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.2.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.2.0-x86_64.AppImage && ./inkline-5.2.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.2.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.2.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.1.0 - 2026-11-23

Inkline 5.1 adds a week of worksheets in one click, and Inkline in French.

### What's new

- **A week of worksheets.** **Presets → Worksheet pack: a week, with answers** makes a booklet with one worksheet for each school day: a maths drill, handwriting, a crossword, a word search and a maze. Each is set for the age chosen under **Age**, the crossword and word search share a theme (animals, food or space), and the booklet has a cover, a name line on every page and the answers at the end. With **Paper → Copies** or **Names** every child gets a pack, and the answers can go in one teacher's book. Change any page in the page list. For another age, or another theme (on the crossword or word search page), pick the preset again.
- **Inkline in French.** Choose **Français** under **View → Language**, or Inkline uses it when your system does. Everything in the window and on printed pages is in French, and word searches, crosswords and handwriting sheets use French words.
- **Help improve the translations.** The Spanish and French haven't been checked by a native speaker yet. If you spot something wrong, use the **Translation fix** form on the issues page. To check a whole translation, `python3 packaging/translation_sheet.py es` (or `fr`) writes it as a spreadsheet with a column for better wording.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-5.1.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.1.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.1.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.1.0-x86_64.AppImage && ./inkline-5.1.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.1.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.1.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 5.0.0 - 2026-11-23

Inkline 5.0 is made for the classroom: maths drills, handwriting, crosswords and colour by maths, several puzzles on one sheet, an answer book for the teacher, age levels, and Inkline in Spanish.

### What's new

- **Maths drills.** **Pattern → Maths drill** makes a sheet of sums: adding, taking away, both, times tables, number bonds ("7 + _ = 10"), or all of them mixed. **Complexity** goes from sums within 10 up to 1,000, and from the 2, 5 and 10 times tables up to the 12. No answer goes below zero, no sum appears twice, and the answer page writes each answer in its blank.
- **Handwriting.** **Pattern → Handwriting** draws rows of handwriting lines: the text once in ink, dotted copies to trace, then room to write it alone. Trace capital letters, small letters, numbers, your own words or a name. With **Paper → Names**, each child traces their own name.
- **Crosswords.** **Pattern → Crossword** builds a crossword from a theme with clues for children, or from your own list (`word: clue`, one per line). Words only cross, never sit side by side, and the answer page fills the grid in.
- **Colour by maths.** Under colour by number, **Colour by maths** puts a small sum in each space ("2+3"). Its answer is the colour to use.
- **Several puzzles on one sheet.** **On the sheet** fits one design, two halves or four quarters on a page, each with its own pattern, and each puzzle gets its own answer.
- **An answer book for the teacher.** With copies of a booklet, **Answers in a separate teacher's book** moves every booklet's answer pages into one book at the end, each headed with the child's name (or "Booklet 3").
- **Age levels.** **Age** (4–6, 7–9, or 10 and up) sets each pattern's complexity and options to suit that age in one step.
- **Inkline in Spanish.** Inkline uses Spanish when your system does, or choose it under **View → Language** (it takes effect next time Inkline starts). Everything in the window and on printed pages is in Spanish, word searches and crosswords use Spanish words with Ñ, and handwriting uses the Spanish alphabet. Corrections to the translation are welcome.

### Fixed

- A recovery copy of unsaved work always goes to the same folder for the whole session.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-5.0.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_5.0.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-5.0.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-5.0.0-x86_64.AppImage && ./inkline-5.0.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-5.0.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-5.0.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 4.10.0 - 2026-11-23

Inkline 4.10 makes class sets something to keep: booklets for every child, saved class lists, and a class set that's saved with the project.

### What's new

- **A booklet for every child.** **Paper → Copies** and **Names** now work for booklets too. Each booklet has its own designs, and with names each child's name goes on their booklet's cover, on every "Name ____" line and over their answer pages. Fold-and-staple folds each booklet on its own, and **Print or save only** picks the same pages from every booklet.
- **Look through the copies.** A pager under Copies ("Copy 2 of 25 · Ana") shows any copy in the preview, with its own designs and name. **Save PNG** and **Save SVG** save the copy you're looking at.
- **Saved class lists.** Under **Names**, save a list ("Class 3B") with **Save names as a list…** and choose it again from the drop-down next time. Lists are kept in Inkline's settings folder, never in projects.
- **A project keeps its class set.** Copies, the names and their switches are saved with the project, so opening it prints the same class set again: the same designs, names and answers. The project file holds the names, so anyone you share it with sees them.

### Fixed

- **Cancelling a print sends nothing, on Linux too.** Print now draws every page first and only then sends the job to the printer, so **Cancel** while it's drawing leaves nothing printed. The printer starts once every page is drawn, and the status line says "Sending to the printer…" while the pages go.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-4.10.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_4.10.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.10.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-4.10.0-x86_64.AppImage && ./inkline-4.10.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-4.10.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.10.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 4.9.0 - 2026-11-23

Inkline 4.9 puts a name on each copy of a class set, and lets you stop a long print or save.

### What's new

- **A name on each copy.** Type or paste a class list into **Paper → Names** (separated by commas or new lines) and Print or Save PDF makes one copy per name, up to 100, with each name written on its copy's "Name ____" line. With answer pages on, each answer is labelled with its copy's name, so the right answer sheet is easy to find. It needs **Page text → Add a "Name ______" line** turned on. It works for photo pages too. The names aren't saved: paste the list again next time.
- **Cancel a long print or save.** A **Cancel** button beside the progress bar (or **Esc**) stops a print or PDF after the page being drawn. A half-finished PDF isn't kept.

### Good to know

- **Cancelling a print on Linux:** the system's printing can't call off a job once it's started, so the pages already drawn still go to the printer. Inkline says how many, and you can cancel them in your system's print queue. On Windows the whole job is called off.
- **A long name** is written smaller to fit on the line.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-4.9.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_4.9.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.9.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-4.9.0-x86_64.AppImage && ./inkline-4.9.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-4.9.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.9.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

## 4.8.0 - 2026-11-23

Inkline 4.8 adds answer pages to a class set of puzzles.

### What's new

- **Answer pages for copies.** When you print or save several copies of a puzzle (Paper → Copies), **Answer pages at the end** (on by default) adds their answers after the copies, four to a page as in a booklet. Each copy has "Copy 7" printed small under it, and its answer is labelled the same, so the sheets are easy to mark. Copies that are all alike share one answer. It works for mazes, word searches, sudoku, kakuro, nonograms, spot the difference, dot-to-dot and colour by number.

### Good to know

- **The copy's label sits in the bottom margin,** so each copy's design is exactly the one you'd get without answers, and the first copy is still the design shown. On a printer that can't print close to the edge, the label may be cut off at the ¼ in margin; a wider margin keeps it.
- **Getting ready for a signed Windows installer.** Releases can now be signed through SignPath Foundation's free code signing for open source, once SignPath accepts Inkline. Until then the installer stays unsigned, and Windows SmartScreen may say it's from an unknown publisher: choose **More info → Run anyway**. The README's **Code signing policy** says how signing works.

### Upgrading

Nothing changes in what Inkline needs. Your presets, settings, projects, recent files and printer carry over.

**Windows**
Run `inkline-4.8.0-windows-setup.exe`.

**Debian / Ubuntu / Linux Mint / Pop!_OS**
```sh
sudo apt install ./inkline_4.8.0-1_amd64.deb
```

**Arch / CachyOS / Manjaro**
```sh
sudo pacman -U inkline-4.8.0-1-any.pkg.tar.zst
```

**Any distro, nothing installed**
```sh
chmod +x inkline-4.8.0-x86_64.AppImage && ./inkline-4.8.0-x86_64.AppImage
```

**Any other distro**
```sh
sh inkline-4.8.0.run            # or --system for every user
```

**Flatpak**
```sh
flatpak install --user inkline-4.8.0.flatpak     # if a .flatpak file is attached to this release
sh packaging/flatpak/build.sh                    # or build it from a copy of the source
```

### Found a problem?

Please open an issue saying what you did, what you expected, and what happened. Include your system (distro, or Windows version), and the printer if it's about printing.

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
