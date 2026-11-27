#!/bin/sh
# Builds Inkline's Fedora / openSUSE package into ../../dist: inkline-<version>-1.<arch>.rpm
#
#   sh packaging/rpm/build-rpm.sh            for this machine (x86_64, or aarch64 on ARM64)
#   (on an ARM64 machine: aarch64. rpmbuild only builds for the machine it runs on)
#
# Like the .deb: the system's Python and numpy, with PySide6's own build (the same wheels) in /usr/lib/inkline/vendor,
# as Fedora and openSUSE package different PySide6 versions, or none. Needs rpmbuild (Fedora: dnf install rpm-build;
# Debian: apt install rpm), python3 and curl; downloads the two PySide6 wheels the first time, checked against their
# sha256. The libraries it needs are listed by file (libEGL.so.1, …), which Fedora and openSUSE both understand.
#
# With INKLINE_FAST_WHEEL set to a wheel of the optional Rust module for this ARCH (packaging/build_fast.py makes
# one), it goes in the vendor folder too and photos convert faster; without it Inkline uses its Python code.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$(cd "$HERE/../.." && pwd)
VERSION=$(cat "$SRC/VERSION")
REL=1
ARCH=${1:-$(uname -m)}
DIST="$SRC/dist"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/inkline-build"
# PySide6's ARM64 build needs glibc 2.39 (Fedora 40, openSUSE Tumbleweed or newer)
case "$ARCH" in
  x86_64) GLIBC=2.34 WHEELS="
https://files.pythonhosted.org/packages/7b/3c/7597d8dcb36aa8315427635ec6ec9d850ffbad4ce78b9118ac854889f2d3/pyside6_essentials-6.12.0-cp310-abi3-manylinux_2_34_x86_64.whl 16f4b5e41daf49235ae048458243da9efe5f3d8040f9cc5aa454ce69893d3bd9
https://files.pythonhosted.org/packages/49/c2/a04fa003b4360e99d8e3fc2829abacf37396ace63ea1cd616402209ec7c6/shiboken6-6.12.0-cp310-abi3-manylinux_2_34_x86_64.whl 3bde565bb0890044b5c7f63808adddede5abc241e9395a2bfed61919884d6240
" ;;
  aarch64|arm64) ARCH=aarch64 GLIBC=2.39 WHEELS="
https://files.pythonhosted.org/packages/5e/4e/f4fd4c016719be832ec49d3c87940459e87fd666179a0a199a3998d07916/pyside6_essentials-6.12.0-cp310-abi3-manylinux_2_39_aarch64.whl 08c5841063fc1df69b7fa1ee405f539e66576a83fc48004be3e2c5e35ccbfa69
https://files.pythonhosted.org/packages/97/ca/a4415e6218e0dff764fe2b2d30db2fc8f499a08ace07634232ade3f73adc/shiboken6-6.12.0-cp310-abi3-manylinux_2_39_aarch64.whl ff72a72b3277b418902d562b987b33a6f6818bed9fe40a49d634d09bc67f620e
" ;;
  *) echo "build-rpm.sh: no PySide6 for '$ARCH' (x86_64 or aarch64)"; exit 1 ;;
esac

command -v rpmbuild >/dev/null || { echo "build-rpm.sh: rpmbuild is needed (Fedora: sudo dnf install rpm-build)"; exit 1; }
FAST=${INKLINE_FAST_WHEEL:-}
if [ -n "$FAST" ]; then
  [ -f "$FAST" ] || { echo "build-rpm.sh: INKLINE_FAST_WHEEL=$FAST isn't a file"; exit 1; }
  case "$ARCH:$(basename "$FAST")" in
    x86_64:*-abi3-*x86_64.whl|aarch64:*-abi3-*aarch64.whl) ;;
    *) echo "build-rpm.sh: $FAST isn't an abi3 wheel for $ARCH"; exit 1 ;;
  esac
fi
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
if [ -n "$FAST" ]; then   # the optional Rust module, the same way (an abi3 wheel: any Python 3.9 or newer)
  python3 -m zipfile -e "$FAST" "$R/usr/lib/inkline/vendor"
  echo "build-rpm.sh: with inkline_fast ($(basename "$FAST"))"
else
  echo "build-rpm.sh: without inkline_fast (set INKLINE_FAST_WHEEL to include it)"
fi
find "$R/usr/lib/inkline/vendor" -type d -exec chmod 755 {} +
find "$R/usr/lib/inkline/vendor" -type f -exec chmod 644 {} +

cat > "$R/usr/bin/inkline" <<'RUN'
#!/bin/sh
# Inkline, with the PySide6 it was built with (ahead of any other on the system)
PYTHONPATH="/usr/lib/inkline/vendor${PYTHONPATH:+:$PYTHONPATH}" exec python3 /usr/share/inkline/inkline.py "$@"
RUN
chmod 755 "$R/usr/bin/inkline"

mkdir -p "$B/rpmbuild/SPECS"
sed -e "s|@VERSION@|$VERSION|" -e "s|@REL@|$REL|" -e "s|@TREE@|$R|" -e "s|@ARCH@|$ARCH|" -e "s|@GLIBC@|$GLIBC|" \
  "$HERE/inkline.spec" > "$B/rpmbuild/SPECS/inkline.spec"
rpmbuild --quiet -bb --target "$ARCH" --define "_topdir $B/rpmbuild" "$B/rpmbuild/SPECS/inkline.spec"
cp "$B/rpmbuild/RPMS/$ARCH/inkline-$VERSION-$REL.$ARCH.rpm" "$DIST/"
echo "built $DIST/inkline-$VERSION-$REL.$ARCH.rpm"
