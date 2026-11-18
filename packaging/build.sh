#!/bin/sh
# Builds Inkline's installers into ../dist:
#   inkline-<version>.run                 universal self-extracting installer (any distro)
#   inkline-<version>-1-any.pkg.tar.zst   Arch / CachyOS / Manjaro package (needs makepkg)
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(dirname "$HERE")"
DIST="$SRC/dist"
VERSION="$(cat "$SRC/VERSION")"
FILES="inkline.py inkline.svg inkline.desktop VERSION"
PKGS="inkengine inkapp"   # the engine and the window, as Python packages
mkdir -p "$DIST"

# --- icons (regenerate if the generator is newer than the SVG) ---
if [ "$HERE/make_icon.py" -nt "$SRC/inkline.svg" ] || [ ! -d "$SRC/icons/hicolor" ]; then python3 "$HERE/make_icon.py"; fi

# --- universal .run installer ---
RUN="$DIST/inkline-$VERSION.run"
sed "s/@VERSION@/$VERSION/g" "$HERE/installer-stub.sh" > "$RUN"
(cd "$SRC" && tar -czf - --exclude=__pycache__ $FILES $PKGS icons/hicolor) >> "$RUN"
chmod 755 "$RUN"
echo "built $RUN"

# --- Arch package ---
if command -v makepkg >/dev/null 2>&1; then
  B="$(mktemp -d)"
  trap 'rm -rf "$B"' EXIT
  for f in $FILES; do cp "$SRC/$f" "$B/"; done
  (cd "$SRC" && tar -czf "$B/inkline-app.tar.gz" --exclude=__pycache__ $PKGS)
  (cd "$SRC/icons" && tar -czf "$B/inkline-icons.tar.gz" hicolor)
  sed "s/@VERSION@/$VERSION/" "$HERE/arch/PKGBUILD" > "$B/PKGBUILD"
  (cd "$B" && SUMS="$(makepkg -g 2>/dev/null)" && \
     awk -v sums="$SUMS" '/^sha256sums=\(\)$/ { print sums; next } { print }' PKGBUILD > PKGBUILD.new && mv PKGBUILD.new PKGBUILD && \
     PKGDEST="$DIST" makepkg -f --nodeps >/dev/null)
  cp "$B/PKGBUILD" "$DIST/PKGBUILD"
  echo "built $(ls -t "$DIST"/inkline-"$VERSION"-*.pkg.tar.zst | head -1)"
else
  echo "makepkg not found, skipped the Arch package"
fi
