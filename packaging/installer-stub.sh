#!/bin/sh
# Inkline @VERSION@ installer — self-extracting. The app files are appended below the marker line.
set -eu
VERSION="@VERSION@"
MODE=user
ACTION=install

usage() {
  cat <<EOF
Inkline $VERSION — black & white images for printing

Usage: sh $(basename "$0") [option]
  (no option)   Install for your user only (~/.local). No password needed.
  --system      Install for everyone (/usr/local). Run with sudo.
  --uninstall   Remove Inkline. Add --system to remove a system-wide install.
  --help        Show this help.
EOF
}

for a in "$@"; do
  case "$a" in
    --system) MODE=system ;;
    --user) MODE=user ;;
    --uninstall) ACTION=uninstall ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $a"; usage; exit 2 ;;
  esac
done

if [ "$MODE" = system ]; then
  if [ "$(id -u)" != 0 ]; then echo "This needs root. Run: sudo sh $0 $*"; exit 1; fi
  PREFIX=/usr/local
else
  PREFIX="$HOME/.local"
fi
APP="$PREFIX/share/inkline"
BIN="$PREFIX/bin"
DESK="$PREFIX/share/applications"
ICONS="$PREFIX/share/icons/hicolor"

refresh_menus() {
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESK" >/dev/null 2>&1 || true
  command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t -f "$ICONS" >/dev/null 2>&1 || true
}

if [ "$ACTION" = uninstall ]; then
  if [ ! -d "$APP" ]; then echo "Inkline isn't installed in $PREFIX."; exit 0; fi
  rm -rf "$APP"
  rm -f "$BIN/inkline" "$DESK/inkline.desktop" "$ICONS/scalable/apps/inkline.svg" "$ICONS"/*/apps/inkline.png
  refresh_menus
  echo "Inkline has been removed from $PREFIX."
  exit 0
fi

# --- dependency check ---
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import PySide6.QtWidgets, PySide6.QtPrintSupport, numpy" >/dev/null 2>&1; then
  echo "Inkline needs Python 3 with PySide6 and numpy. Install them, then run this installer again:"
  echo "  Arch / CachyOS / Manjaro:  sudo pacman -S pyside6 python-numpy"
  echo "  Debian / Ubuntu:           sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtprintsupport python3-numpy"
  echo "  Fedora:                    sudo dnf install python3-pyside6 python3-numpy"
  echo "  Any distro (user only):    pip install --user PySide6 numpy"
  exit 1
fi

if [ "$MODE" = user ] && [ -d /usr/share/inkline ]; then
  echo "Note: an Inkline system package is already installed. You may see two entries in the app menu."
fi

# --- unpack payload ---
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
LINE=$(awk '/^__INKLINE_PAYLOAD__$/ { print NR + 1; exit }' "$0")
tail -n +"$LINE" "$0" | tar -xz -C "$TMP"

mkdir -p "$APP" "$BIN" "$DESK" "$ICONS/scalable/apps"
rm -rf "$APP/inkengine" "$APP/inkapp" "$APP/index.html"   # 2.x's page goes; 3.0 is native
cp "$TMP/inkline.py" "$TMP/inkline.svg" "$TMP/VERSION" "$APP/"
cp -R "$TMP/inkengine" "$TMP/inkapp" "$APP/"
cp "$TMP/inkline.svg" "$ICONS/scalable/apps/inkline.svg"
for png in "$TMP"/icons/hicolor/*/apps/inkline.png; do
  size="$(basename "$(dirname "$(dirname "$png")")")"
  mkdir -p "$ICONS/$size/apps" && cp "$png" "$ICONS/$size/apps/inkline.png"
done

printf '#!/bin/sh\nexec python3 "%s/inkline.py" "$@"\n' "$APP" > "$BIN/inkline"
chmod 755 "$BIN/inkline"
sed "s|^Exec=.*|Exec=$BIN/inkline|" "$TMP/inkline.desktop" > "$DESK/inkline.desktop"

# A copy of this installer stays with the app, so it can uninstall itself later.
cp "$0" "$APP/installer.run"
cat > "$APP/uninstall.sh" <<EOF
#!/bin/sh
exec sh "$APP/installer.run" --uninstall $( [ "$MODE" = system ] && echo --system )
EOF
chmod 755 "$APP/uninstall.sh"

refresh_menus
echo "Inkline $VERSION installed in $PREFIX."
echo "Open it from your application menu, or run: inkline"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "($BIN isn't on your PATH, so use the app menu or run $BIN/inkline)";; esac
echo "To uninstall later: sh $APP/uninstall.sh"
exit 0
__INKLINE_PAYLOAD__
