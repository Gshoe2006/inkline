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

- [ ] **Zoom:** Ctrl+wheel over the preview zooms where the pointer is; dragging moves round the zoomed page;
      a double click shows the whole page. View → Zoom in, Zoom out and Whole page (Ctrl++, Ctrl+-, Ctrl+0) do the
      same. On a trackpad (macOS, or Wayland), pinching zooms. With a photo open, the plain wheel still zooms the photo.

## Accessibility

- [ ] **Keyboard only:** with the mouse unplugged, Tab from the rail through Create's options to the toolbar and
      the preview: every stop is outlined. Choose a pattern in the gallery with the arrow keys and Enter; open All
      patterns…, type "maze", press Down and Enter. Build a booklet page by page and, in its page list, move a page
      with Alt+↑ / Alt+↓, duplicate it with Ctrl+D and remove it with Delete. Print with Ctrl+P.
- [ ] **Orca (Linux):** turn it on (Super+Alt+S) and Tab round the window: the rail says "Create, push button" (and
      its Ctrl+1 tooltip), each list says its label and its value ("Pattern, Mandala"), each slider its label and
      value, the page list's buttons "Move up", "Move down", "Duplicate with a new design", "Remove". The preview
      says "Page preview" and the page shown ("Page 2 of 5: Maze") after you turn a booklet's page.
- [ ] **NVDA (Windows) and VoiceOver (macOS):** the same walk; check the Menu button ("Menu"), Presets, and the
      Settings dialog (each list read with its label).
- [ ] **TalkBack (Android):** swipe through the bottom bar, the options and the toolbar: each is read by name;
      double-tap activates. Pinch the preview to zoom, drag to move round, double-tap to fit.
- [ ] **High contrast:** Edit → Settings → Appearance → turn on High contrast and choose it: the focus outline,
      the selected rail entry and the page list's selection are all clearly visible. On Windows, with a contrast
      theme on, Inkline (in its own theme) is still readable, and its High contrast theme matches it well enough.
- [ ] **Larger text:** at 150% display scaling (or with the touch-screen layout), nothing in the rail, toolbar
      or Settings is cut off.

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

## Other packages

- [ ] **Intel Mac:** `inkline-<version>-macos-intel.dmg` and the universal `inkline-<version>-macos.dmg` both start
      on an Intel Mac; the universal one on Apple silicon too.
- [ ] **Fedora and openSUSE:** `sudo dnf install ./inkline-<version>-1.x86_64.rpm` (openSUSE: `sudo zypper install
      --allow-unsigned-rpm …`): Inkline is in the app menu, opens `.inkline` files, and Update now asks for the
      administrator password and installs the newer .rpm.
- [ ] **Snap:** `sudo snap install --dangerous ./inkline_<version>_amd64.snap`: it starts, prints (the printer list
      shows your printers), opens and saves files in your home folder and on a USB stick; Check for updates offers
      only the release page, and Check for updates automatically offers only When Inkline starts.
- [ ] **Raspberry Pi (4 or 5, Raspberry Pi OS 13):** the arm64 .deb installs with apt and starts; the aarch64
      AppImage runs; Update now from an older arm64 .deb installs the arm64 one.
- [ ] **Windows portable:** unzip `inkline-<version>-windows-portable.zip` on a USB stick and run
      `Inkline\Inkline.exe` on a PC where it's never been installed: it starts, and Update now downloads the new .zip
      and opens its folder.

## Android (a phone and a tablet)

- [ ] Install `inkline-<version>-android-aarch64.apk` (allow installs from this source when asked): Inkline starts in
      a minute or less, in the one-column layout on a phone, the rail layout on a tablet held sideways.
- [ ] **Touch:** every button, list and slider is easy to hit with a finger; the bottom bar switches pages; Preview
      shows the page; turning the tablet switches layouts without losing what you'd typed.
- [ ] **Tablet sideways** (about 1024×600 to 1366×1024): the rail, the options and the preview side by side; the
      page as tall as the preview; nothing cut off in the toolbar or the booklet's page list; More designs… in the
      toolbar on the wider tablets.
- [ ] **Pinch:** two fingers zoom the preview round where they are, one finger then drags the zoomed page, a double
      tap shows the whole page; with a photo open and not zoomed, one finger still moves the photo.
- [ ] **Menu:** the Menu button opens File, Edit, View, Help; on a phone it has Presets too.
- [ ] **Files:** Open image picks a photo from the gallery or Files; Save PDF and Save PNG save where you choose, and
      the file opens in another app.
- [ ] **Print:** Print opens Android's print dialog; Save as PDF there writes the pages; a Wi-Fi printer (or the
      Mopria plugin) prints them in grey, a fold-and-staple booklet double-sided.
- [ ] **Speed:** a 10-page booklet and a photo conversion finish in reasonable time on an older phone.
- [ ] **Update:** with an older APK installed, Check for updates offers the release page.
- [ ] **Icon:** the home screen and app drawer show Inkline's page on its dark background, whole, in the
      launcher's shape (circle, squircle or rounded square), not the Python or Qt logo.
- [ ] **Google Play** (a closed test's opt-in link): Inkline installs from Play and starts as the APK does; a newer
      bundle uploaded to the track arrives as a Play update.

## Printing

- [ ] Edit → Settings → Printer: choose a printer; File → Print… starts with it. Its dead edges show on the preview
      after the first print.
- [ ] Print a class set (Copies 3, Names) and a fold-and-staple booklet (double-sided, short edge) on paper.

## Languages

- [ ] View → Language → each language, restart: no English left in the window, the menus' underlined letters are
      different in each menu, and nothing is cut off (Booklet and Create on the rail, toolbar buttons, Settings).
