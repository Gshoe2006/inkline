# Manual tests

What CI can't see: a real desktop, a real notification, a timer firing at login, a real printer. Run these on a
release candidate (or after changing the area), on the systems you have. Each takes a minute or two.

Start Inkline from the package you're testing, not from the source checkout, unless the step says so.

## The window (6.0 layout)

- [ ] **First start:** with a fresh settings folder (`INKLINE_CONFIG_DIR=$(mktemp -d) inkline`), the tour opens.
      Next goes through five steps, each outline round the part it's about; Escape closes it; a second start doesn't
      show it. Help → Tour of the window shows it again.
- [ ] **Rail:** Create, Photo, Booklet, Poster and Print each show their page with no scroll bar at your usual
      window size. Ctrl+1 to Ctrl+5 do the same. The arrow keys on the rail don't change the mode.
- [ ] **Gallery:** the six pictures appear within a few seconds; clicking one changes the pattern and the picture
      stays where it is. All patterns… shows every pattern; typing "maze" or "colouring" narrows it.
- [ ] **Presets:** Presets ▾ opens a panel; Tab reaches the list, Delete, the name field and Save; Escape closes it.
- [ ] **Booklet built page by page:** double-click a page: its design opens on the Booklet page; ‹ All pages goes
      back; Create also brings the controls back.
- [ ] **HiDPI:** at 150% or 200% scaling nothing is cut off (rail labels, toolbar buttons, the tour card).

## Themes

- [ ] Edit → Settings → Appearance: turn on High contrast, Warm paper and Slate; choose each, and View → Theme
      switches between them. Text is readable everywhere in each, including disabled controls and tooltips.
- [ ] Follow the system: switching the desktop between light and dark switches Inkline while it's open.
- [ ] Use my desktop's style (Arch package or .run, which use the system's Qt): the controls look like your other
      apps; the theme then only colours the preview.

## Updates

- [ ] **Notification:** `inkline --check-updates --demo` shows "Inkline X is available" with a **Show the update**
      button; pressing it opens Inkline with the update box. On GNOME and KDE (Linux) and on Windows 10/11.
      Note any desktop that shows no button: the version is then offered when Inkline next opens.
- [ ] **Schedule:** Help → Check for updates automatically → Every day. On Linux,
      `systemctl --user list-timers inkline-update.timer` lists it; `systemctl --user start inkline-update.service`
      runs a check now. On Windows, Task Scheduler shows "Inkline update check". Choose Never: both are gone.
- [ ] **At login:** choose At login, log out and in: about two minutes later a check runs (Linux:
      `journalctl --user -u inkline-update.service`).
- [ ] **Updating:** with an older version of each package installed (Windows, AppImage, .deb, Arch, .run), Help →
      Check for updates… → Update now installs the latest and Restart now opens it. The .deb and Arch package ask for
      the administrator password.

## macOS

- [ ] Open `inkline-<version>-macos.dmg`, drag Inkline to Applications, Control-click → Open: it starts, and the
      self-test's checks (`/Applications/Inkline.app/Contents/MacOS/Inkline --selftest /tmp/st`) pass.
- [ ] Help → Check for updates automatically → Every day: `launchctl print gui/$(id -u)/io.github.gshoe2006.Inkline.update`
      shows it; `inkline --check-updates --demo` (the app's program) shows a notification.
- [ ] With an older version installed, Update now replaces /Applications/Inkline.app and Restart now opens the new one.
- [ ] Printing through the macOS print dialog; Retina display: nothing blurry or cut off.

## Printing

- [ ] Edit → Settings → Printer: choose a printer; File → Print… starts with it. Its dead edges show on the preview
      after the first print.
- [ ] Print a class set (Copies 3, Names) and a fold-and-staple booklet (double-sided, short edge) on paper.

## Languages

- [ ] View → Language → each language, restart: no English left in the window, the menus' underlined letters are
      different in each menu, and nothing is cut off (Booklet and Create on the rail, toolbar buttons, Settings).
