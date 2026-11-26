#!/bin/sh
# Builds Inkline's Fedora / openSUSE package into ../../dist: inkline-<version>-1.x86_64.rpm
#
#   sh packaging/rpm/build-rpm.sh
#
# Like the .deb: the system's Python and numpy, with PySide6's own build (the same wheels) in /usr/lib/inkline/vendor,
# as Fedora and openSUSE package different PySide6 versions, or none. Needs rpmbuild (Fedora: dnf install rpm-build;
# Debian: apt install rpm), python3 and curl; downloads the two PySide6 wheels the first time, checked against their
# sha256. The libraries it needs are listed by file (libEGL.so.1, …), which Fedora and openSUSE both understand.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$(cd "$HERE/../.." && pwd)
VERSION=$(cat "$SRC/VERSION")
REL=1
DIST="$SRC/dist"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/inkline-build"
WHEELS="
https://files.pythonhosted.org/packages/7b/3c/7597d8dcb36aa8315427635ec6ec9d850ffbad4ce78b9118ac854889f2d3/pyside6_essentials-6.12.0-cp310-abi3-manylinux_2_34_x86_64.whl 16f4b5e41daf49235ae048458243da9efe5f3d8040f9cc5aa454ce69893d3bd9
https://files.pythonhosted.org/packages/49/c2/a04fa003b4360e99d8e3fc2829abacf37396ace63ea1cd616402209ec7c6/shiboken6-6.12.0-cp310-abi3-manylinux_2_34_x86_64.whl 3bde565bb0890044b5c7f63808adddede5abc241e9395a2bfed61919884d6240
"

command -v rpmbuild >/dev/null || { echo "build-rpm.sh: rpmbuild is needed (Fedora: sudo dnf install rpm-build)"; exit 1; }
mkdir -p "$CACHE" "$DIST"
echo "$WHEELS" | while read -r url sum; do
  [ -n "$url" ] || continue
  f="$CACHE/$(basename "$url")"
  [ -f "$f" ] || curl -fsSL -o "$f" "$url"
  echo "$sum  $f" | sha256sum -c --quiet - || { rm -f "$f"; echo "build-rpm.sh: $f didn't match its sha256"; exit 1; }
done

B=$(mktemp -d)
trap 'rm -rf "$B"' EXIT
R="$B/tree"
APP="$R/usr/share/inkline"
mkdir -p "$APP" "$R/usr/lib/inkline/vendor" "$R/usr/bin"

# the app, laid out as in the .deb
(cd "$SRC" && cp -r inkengine inkapp "$APP/" && cp inkline.py inkline.svg VERSION CHANGELOG.md "$APP/")
echo rpm > "$APP/install-kind"   # Help → Check for updates: how to install a newer one
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
install -Dm644 "$SRC/LICENSE" "$R/usr/share/licenses/inkline/LICENSE"

for url in $(echo "$WHEELS" | while read -r u _s; do [ -n "$u" ] && echo "$u"; done); do
  python3 -m zipfile -e "$CACHE/$(basename "$url")" "$R/usr/lib/inkline/vendor"
done
find "$R/usr/lib/inkline/vendor" -type d -exec chmod 755 {} +
find "$R/usr/lib/inkline/vendor" -type f -exec chmod 644 {} +

cat > "$R/usr/bin/inkline" <<'RUN'
#!/bin/sh
# Inkline, with the PySide6 it was built with (ahead of any other on the system)
PYTHONPATH="/usr/lib/inkline/vendor${PYTHONPATH:+:$PYTHONPATH}" exec python3 /usr/share/inkline/inkline.py "$@"
RUN
chmod 755 "$R/usr/bin/inkline"

mkdir -p "$B/rpmbuild/SPECS"
sed -e "s|@VERSION@|$VERSION|" -e "s|@REL@|$REL|" -e "s|@TREE@|$R|" "$HERE/inkline.spec" > "$B/rpmbuild/SPECS/inkline.spec"
rpmbuild --quiet -bb --target x86_64 --define "_topdir $B/rpmbuild" "$B/rpmbuild/SPECS/inkline.spec"
cp "$B/rpmbuild/RPMS/x86_64/inkline-$VERSION-$REL.x86_64.rpm" "$DIST/"
echo "built $DIST/inkline-$VERSION-$REL.x86_64.rpm"
