#!/bin/sh
# Builds Inkline's Debian / Ubuntu package into ../../dist: inkline_<version>-1_amd64.deb
#
#   sh packaging/debian/build-deb.sh
#
# Debian 12 and Ubuntu 22.04/24.04 don't package PySide6 (or not a new enough one), so the package carries
# PySide6's own build (the same wheels the Flatpak uses, which work with any Python 3.10 or newer) in
# /usr/lib/inkline/vendor, and uses the system's Python and numpy. Needs dpkg-deb, python3 and curl;
# downloads the two PySide6 wheels the first time, checked against their sha256.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$(cd "$HERE/../.." && pwd)
VERSION=$(cat "$SRC/VERSION")
REL=1
DIST="$SRC/dist"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/inkline-build"

# PySide6's Essentials (QtCore, QtGui, QtWidgets, QtPrintSupport: all Inkline uses), as in the Flatpak
WHEELS="
https://files.pythonhosted.org/packages/7b/3c/7597d8dcb36aa8315427635ec6ec9d850ffbad4ce78b9118ac854889f2d3/pyside6_essentials-6.12.0-cp310-abi3-manylinux_2_34_x86_64.whl 16f4b5e41daf49235ae048458243da9efe5f3d8040f9cc5aa454ce69893d3bd9
https://files.pythonhosted.org/packages/49/c2/a04fa003b4360e99d8e3fc2829abacf37396ace63ea1cd616402209ec7c6/shiboken6-6.12.0-cp310-abi3-manylinux_2_34_x86_64.whl 3bde565bb0890044b5c7f63808adddede5abc241e9395a2bfed61919884d6240
"

command -v dpkg-deb >/dev/null || { echo "build-deb.sh: dpkg-deb is needed (Debian/Ubuntu: sudo apt install dpkg)"; exit 1; }
mkdir -p "$CACHE" "$DIST"
echo "$WHEELS" | while read -r url sum; do
  [ -n "$url" ] || continue
  f="$CACHE/$(basename "$url")"
  [ -f "$f" ] || curl -fsSL -o "$f" "$url"
  echo "$sum  $f" | sha256sum -c --quiet - || { rm -f "$f"; echo "build-deb.sh: $f didn't match its sha256"; exit 1; }
done

B=$(mktemp -d)
trap 'rm -rf "$B"' EXIT
R="$B/root"
APP="$R/usr/share/inkline"
mkdir -p "$APP" "$R/usr/lib/inkline/vendor" "$R/usr/bin" "$R/DEBIAN"

# the app, as the Arch package installs it
(cd "$SRC" && cp -r inkengine inkapp "$APP/" && cp inkline.py inkline.svg VERSION CHANGELOG.md "$APP/")
find "$APP" -name __pycache__ -prune -exec rm -rf {} +
install -Dm644 "$SRC/inkline.desktop" "$R/usr/share/applications/inkline.desktop"
install -Dm644 "$SRC/inkline-mime.xml" "$R/usr/share/mime/packages/inkline.xml"
install -Dm644 "$SRC/inkline.svg" "$R/usr/share/icons/hicolor/scalable/apps/inkline.svg"
install -Dm644 "$SRC/icons/hicolor/scalable/mimetypes/application-x-inkline-project.svg" \
  "$R/usr/share/icons/hicolor/scalable/mimetypes/application-x-inkline-project.svg"
for png in "$SRC"/icons/hicolor/*/apps/inkline.png; do
  size=$(basename "$(dirname "$(dirname "$png")")")
  install -Dm644 "$png" "$R/usr/share/icons/hicolor/$size/apps/inkline.png"
done
install -Dm644 "$SRC/packaging/flatpak/io.github.gshoe2006.Inkline.metainfo.xml" \
  "$R/usr/share/metainfo/inkline.metainfo.xml"
sed -i 's|<launchable type="desktop-id">io.github.gshoe2006.Inkline.desktop</launchable>|<launchable type="desktop-id">inkline.desktop</launchable>|' \
  "$R/usr/share/metainfo/inkline.metainfo.xml"
install -Dm644 "$SRC/LICENSE" "$R/usr/share/doc/inkline/LICENSE"
cat > "$R/usr/share/doc/inkline/copyright" <<COPY
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Inkline
Source: https://github.com/Gshoe2006/inkline

Files: *
License: GPL-3.0-or-later
 The full text is in /usr/share/doc/inkline/LICENSE and /usr/share/common-licenses/GPL-3.

Files: usr/lib/inkline/vendor/*
License: LGPL-3.0-only or GPL-2.0-only or GPL-3.0-only
 PySide6 and Shiboken6 (Qt for Python), from their official wheels.
COPY

# PySide6, unpacked where only Inkline finds it
# (wheels are zip files, and these two hold only their packages: unpacking them is installing them, with no
# pip needed, which some systems keep away from their own Python)
for w in "$CACHE"/pyside6_essentials-6.12.0-*.whl "$CACHE"/shiboken6-6.12.0-*.whl; do
  python3 -m zipfile -e "$w" "$R/usr/lib/inkline/vendor"
done
find "$R/usr/lib/inkline/vendor" -type d -exec chmod 755 {} +
find "$R/usr/lib/inkline/vendor" -type f -exec chmod 644 {} +

cat > "$R/usr/bin/inkline" <<'RUN'
#!/bin/sh
# Inkline, with the PySide6 it was built with (ahead of any other on the system)
PYTHONPATH="/usr/lib/inkline/vendor${PYTHONPATH:+:$PYTHONPATH}" exec python3 /usr/share/inkline/inkline.py "$@"
RUN
chmod 755 "$R/usr/bin/inkline"

# Python writes compiled caches beside the code the first time it runs: remove them with the package
cat > "$R/DEBIAN/prerm" <<'PRERM'
#!/bin/sh
set -e
find /usr/share/inkline /usr/lib/inkline -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
PRERM
chmod 755 "$R/DEBIAN/prerm"

SIZE=$(du -sk "$R" | cut -f1)
cat > "$R/DEBIAN/control" <<CTRL
Package: inkline
Version: $VERSION-$REL
Architecture: amd64
Maintainer: Inkline <Gshoe2006@users.noreply.github.com>
Installed-Size: $SIZE
Depends: python3 (>= 3.10), python3-numpy, libc6 (>= 2.34), libegl1, libgl1, libfontconfig1, libfreetype6, libxkbcommon0, libxkbcommon-x11-0, libdbus-1-3, libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcb-xkb1, libwayland-client0, libwayland-cursor0, libwayland-egl1
Recommends: cups
Section: graphics
Priority: optional
Homepage: https://github.com/Gshoe2006/inkline
Description: black & white images for printing
 Inkline makes colouring pages, puzzles and black and white photo prints,
 ready to print at true paper size: mandalas, mazes, dot-to-dots, sudoku,
 kakuro, nonograms, spot the difference, word search and name pages;
 dithered, halftone, engraved and stippled photos; booklets, photo books
 and posters. Print, or save as PDF, PNG or SVG.
CTRL

OUT="$DIST/inkline_${VERSION}-${REL}_amd64.deb"
dpkg-deb --root-owner-group -Zxz --build "$R" "$OUT" >/dev/null
echo "built $OUT"
