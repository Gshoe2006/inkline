#!/bin/sh
# Builds Inkline as a Flatpak and installs it for you. Run it from anywhere:
#
#   sh packaging/flatpak/build.sh            build and install
#   sh packaging/flatpak/build.sh --bundle   also write dist/inkline-<version>.flatpak, one file to share
#   sh packaging/flatpak/build.sh --run      start Inkline when it's done
#
# The first run sets up Flathub and the freedesktop 25.08 runtime (about 1 GB). Afterwards start
# Inkline from your app menu or with: flatpak run io.github.gshoe2006.Inkline
# (packaging/flatpak/inkline.sh is the launcher inside the Flatpak; it doesn't run on its own.)
set -eu

APP=io.github.gshoe2006.Inkline
RUNTIME=25.08

say() { printf '%s\n' "$*"; }
fail() { say "build.sh: $*" >&2; exit 1; }

BUNDLE=0
RUN=0
for arg in "$@"; do
  case "$arg" in
    --bundle) BUNDLE=1 ;;
    --run) RUN=1 ;;
    -h|--help) sed -n '2,10s/^# \{0,1\}//p' "$0"; exit 0 ;;
    *) fail "unknown option $arg (try --help)" ;;
  esac
done

# Work from the repository, wherever this is run from, and never from inside build-flatpak: a
# terminal left in a folder that --force-clean deletes gets "getcwd: cannot access parent
# directories" on every command. (Run by its full path, this works even from such a folder.)
HERE=$(cd "$(dirname "$0")" 2>/dev/null && pwd) ||
  fail "can't find this script's folder. If you see 'getcwd' errors, your terminal's current folder was deleted: cd into the inkline folder and run this again."
ROOT=$(cd "$HERE/../.." && pwd)
MANIFEST="$HERE/$APP.yml"
[ -f "$MANIFEST" ] && [ -f "$ROOT/inkline.py" ] || fail "run this from a copy of the Inkline repository (missing $MANIFEST)."
cd "$ROOT"
VERSION=$(cat VERSION)

if ! command -v flatpak >/dev/null 2>&1 || ! command -v flatpak-builder >/dev/null 2>&1; then
  say "Flatpak and flatpak-builder are needed. Install them, then run this again:"
  say "  Arch / CachyOS / Manjaro:  sudo pacman -S flatpak flatpak-builder"
  say "  Debian / Ubuntu:           sudo apt install flatpak flatpak-builder"
  say "  Fedora:                    sudo dnf install flatpak flatpak-builder"
  exit 1
fi

say "Setting up Flathub and the freedesktop $RUNTIME runtime (only downloads the first time)..."
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive -y flathub "org.freedesktop.Platform//$RUNTIME" "org.freedesktop.Sdk//$RUNTIME"

# Without FUSE (some containers), flatpak-builder needs telling not to use it.
EXTRA=""
[ -e /dev/fuse ] || EXTRA="--disable-rofiles-fuse"

say "Building Inkline $VERSION..."
# shellcheck disable=SC2086
flatpak-builder --user --install --force-clean $EXTRA build-flatpak "$MANIFEST"

if [ "$BUNDLE" = 1 ]; then
  mkdir -p dist
  flatpak build-export repo-flatpak build-flatpak
  flatpak build-bundle repo-flatpak "dist/inkline-$VERSION.flatpak" "$APP"
  say "Wrote dist/inkline-$VERSION.flatpak. Install it elsewhere with: flatpak install --user inkline-$VERSION.flatpak"
fi

say ""
say "Inkline $VERSION is installed. Start it from your app menu, or with:"
say "  flatpak run $APP"
[ "$RUN" = 0 ] || exec flatpak run "$APP"
