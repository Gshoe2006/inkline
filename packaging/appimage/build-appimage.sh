#!/bin/sh
# Builds Inkline as an AppImage into ../../dist: inkline-<version>-<arch>.AppImage (x86_64, or aarch64 when built on
# ARM64), one file that runs on most Linux distributions without installing anything (chmod +x it, then run it).
# The aarch64 one needs glibc 2.39 or newer (PySide6's ARM64 build): Ubuntu 24.04, Debian 13, Raspberry Pi OS 13.
#
#   sh packaging/appimage/build-appimage.sh
#
# Inside: a standalone Python (fetched by uv), PySide6's Essentials and numpy (from PyPI), and Inkline. Needs
# curl and uv (pip install uv); downloads appimagetool the first time. Runs anywhere, even without FUSE.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$(cd "$HERE/../.." && pwd)
VERSION=$(cat "$SRC/VERSION")
DIST="$SRC/dist"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/inkline-build"
PYTHON=3.12
PINS="PySide6-Essentials==6.12.0 shiboken6==6.12.0 numpy==2.3.5"
ARCH=$(uname -m)
case "$ARCH" in x86_64|aarch64) ;; arm64) ARCH=aarch64 ;; *) echo "build-appimage.sh: not for '$ARCH'"; exit 1 ;; esac
TOOL="$CACHE/appimagetool-$ARCH.AppImage"

command -v uv >/dev/null || { echo "build-appimage.sh: uv is needed: pip install uv"; exit 1; }
mkdir -p "$CACHE" "$DIST"
if [ ! -f "$TOOL" ]; then
  curl -fsSL -o "$TOOL.part" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage
  mv "$TOOL.part" "$TOOL"
  chmod 755 "$TOOL"
fi

B=$(mktemp -d)
trap 'rm -rf "$B"' EXIT
D="$B/Inkline.AppDir"
mkdir -p "$D/usr/share/inkline"

# a standalone, relocatable Python, with PySide6 and numpy in it
uv python install "$PYTHON" --install-dir "$B/py" --no-bin >/dev/null   # nothing put in ~/.local/bin
PYDIR=$(find "$B/py" -maxdepth 1 -type d -name "cpython-$PYTHON.*" | head -1)
[ -n "$PYDIR" ] || { echo "build-appimage.sh: uv didn't provide Python $PYTHON"; exit 1; }
cp -a "$PYDIR" "$D/usr/python"
PY="$D/usr/python/bin/python3"
rm -f "$D/usr/python/lib/python$PYTHON/EXTERNALLY-MANAGED"   # this copy is the AppImage's own: pip may fill it
# shellcheck disable=SC2086
"$PY" -m pip install --quiet --no-cache-dir --no-compile --only-binary=:all: $PINS
rm -rf "$D/usr/python/include" "$D/usr/python/share" "$D/usr/python/lib/python$PYTHON/test" \
       "$D/usr/python/lib/python$PYTHON/idlelib" "$D/usr/python/lib/python$PYTHON/tkinter" \
       "$D/usr/python/lib/python$PYTHON/ensurepip"
find "$D/usr/python" -name __pycache__ -prune -exec rm -rf {} +

# Inkline itself
(cd "$SRC" && cp -r inkengine inkapp "$D/usr/share/inkline/" && cp inkline.py inkline.svg VERSION LICENSE CHANGELOG.md "$D/usr/share/inkline/")
find "$D/usr/share/inkline" -name __pycache__ -prune -exec rm -rf {} +

cat > "$D/AppRun" <<'RUN'
#!/bin/sh
# Inkline's AppImage: its own Python, never the system's (and no compiled caches written into the image)
HERE=$(dirname "$(readlink -f "$0")")
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH PYTHONHOME
exec "$HERE/usr/python/bin/python3" "$HERE/usr/share/inkline/inkline.py" "$@"
RUN
chmod 755 "$D/AppRun"

# what appimagetool and desktop integrations (AppImageLauncher, Gear Lever) read: the app's menu entry, icon,
# app details, and the .inkline file type
sed 's|^Exec=.*|Exec=inkline %f|' "$SRC/inkline.desktop" > "$D/io.github.gshoe2006.Inkline.desktop"
sed -i 's|^Icon=.*|Icon=io.github.gshoe2006.Inkline|' "$D/io.github.gshoe2006.Inkline.desktop"
cp "$SRC/inkline.svg" "$D/io.github.gshoe2006.Inkline.svg"
ln -s io.github.gshoe2006.Inkline.svg "$D/.DirIcon"
install -Dm644 "$SRC/inkline.svg" "$D/usr/share/icons/hicolor/scalable/apps/io.github.gshoe2006.Inkline.svg"
install -Dm644 "$SRC/packaging/flatpak/io.github.gshoe2006.Inkline.metainfo.xml" \
  "$D/usr/share/metainfo/io.github.gshoe2006.Inkline.appdata.xml"
install -Dm644 "$SRC/inkline-mime.xml" "$D/usr/share/mime/packages/io.github.gshoe2006.Inkline.xml"

OUT="$DIST/inkline-$VERSION-$ARCH.AppImage"
# extract-and-run: appimagetool is itself an AppImage, and build machines (containers, CI) often lack FUSE
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=$ARCH "$TOOL" --no-appstream "$D" "$OUT" >"$B/tool.log" 2>&1 ||
  { cat "$B/tool.log"; exit 1; }
echo "built $OUT"
