#!/bin/sh
# Downloads Qt's PySide6 and shiboken6 6.12.0 Android wheels for one arch (aarch64 or x86_64) into DIR, from Qt's
# own download site, and prints WHEEL_PYSIDE6=… and WHEEL_SHIBOKEN6=… lines (the CI adds them to its environment).
#
#   sh packaging/android/fetch-wheels.sh ARCH DIR
set -eu
ARCH=$1
DIR=$2
VERSION=6.12.0
mkdir -p "$DIR"
for pkg in pyside6 shiboken6; do
  base="https://download.qt.io/official_releases/QtForPython/$pkg/"
  page=$(curl -fsSL "$base")
  name=$(printf '%s' "$page" | grep -oiE "href=\"[^\"]*$VERSION[^\"]*android_$ARCH\.whl\"" | head -1 | sed 's/^href="//; s/"$//')
  if [ -z "$name" ]; then
    echo "::error::No $VERSION Android $ARCH wheel for $pkg at $base. Android wheels there:" >&2
    printf '%s' "$page" | grep -oiE "href=\"[^\"]*android[^\"]*\"" | head -40 >&2
    exit 1
  fi
  case "$name" in http*) url="$name" ;; *) url="$base$name" ;; esac
  echo "$pkg: $url" >&2
  file="$DIR/$(basename "$name")"
  curl -fsSL -o "$file" "$url"
  echo "WHEEL_$(echo "$pkg" | tr a-z A-Z)=$(cd "$DIR" && pwd)/$(basename "$name")"
done
