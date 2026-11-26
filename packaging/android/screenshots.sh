#!/bin/sh
# Screenshots for Google Play from a running emulator: installs Inkline's APK, starts it with the "inkline-screens"
# file in its private folder (build.py's main.py then runs screens.py, which shows Create, the preview, Booklet,
# Print's options and Android's print dialog in turn), and takes a screenshot of each when the app says it's
# showing (screens/now), answering in screens/ack. Android's status bar is put in demo mode (10:00, full battery,
# no notifications) for tidy pictures. Checks the pictures fit Play's size rules.
#
#   sh packaging/android/screenshots.sh APK OUTDIR
set -u
APK=$1
OUT=$2
PKG=io.github.gshoe2006.inkline
HERE=$(dirname "$0")
mkdir -p "$OUT"
adb install -r "$APK" || exit 1

adb shell settings put global sysui_demo_allowed 1
demo() { adb shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
demo enter
demo clock -e hhmm 1000
demo battery -e level 100 -e plugged false
demo network -e wifi show -e level 4 -e mobile hide
demo notifications -e visible false

adb shell am force-stop "$PKG"
for d in files files/app; do
  adb shell "run-as $PKG sh -c 'mkdir -p $d && rm -rf $d/screens $d/inkline-selftest $d/inkline-printtest && touch $d/inkline-screens'"
done
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null

last=""
taken=0
for _ in $(seq 1 300); do   # up to ten minutes
  sleep 2
  now=""
  for d in files files/app; do
    now=$(adb shell run-as "$PKG" cat "$d/screens/now" 2>/dev/null | tr -d '\r\n')
    [ -n "$now" ] && break
  done
  [ -z "$now" ] || [ "$now" = "$last" ] && continue
  [ "$now" = "done" ] && break
  case "$now" in
    *print-dialog)   # Android's own dialog takes a moment to open
      for _ in $(seq 1 30); do
        adb shell dumpsys activity activities | grep -qi printspooler && break
        sleep 2
      done
      sleep 3 ;;
  esac
  adb exec-out screencap -p > "$OUT/$now.png"
  echo "screenshot: $now"
  taken=$((taken + 1))
  adb shell "run-as $PKG sh -c 'echo $now > $d/screens/ack'"
  last=$now
done
adb logcat -d > "$OUT-logcat.txt"
demo exit
adb shell am force-stop "$PKG"
for d in files files/app; do adb shell "run-as $PKG rm -f $d/inkline-screens"; done
if [ "$taken" -lt 5 ]; then
  echo "only $taken of 5 screenshots; the end of the log:"
  grep -iE "python|inkline|traceback|error" "$OUT-logcat.txt" | tail -60
  exit 1
fi
python3 "$HERE/play/check_screenshots.py" "$OUT"
