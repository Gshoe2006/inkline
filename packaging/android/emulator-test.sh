#!/bin/sh
# Installs Inkline's APK on a running emulator, starts it (a screenshot of the window, after a minute), then runs the
# self-test there and copies its files out (packaging/android/build.py's main.py looks for the "inkline-selftest"
# file). The emulator's log goes with them.
#
#   sh packaging/android/emulator-test.sh APK OUTDIR
set -u
APK=$1
OUT=$2
PKG=io.github.gshoe2006.inkline
mkdir -p "$OUT"
adb install -r "$APK" || exit 1
adb logcat -c

echo "starting Inkline"
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null
sleep 60
adb exec-out screencap -p > "$OUT/window.png"
adb shell pidof "$PKG" >/dev/null && echo "Inkline is running after a minute" || echo "Inkline isn't running after a minute"
adb shell am force-stop "$PKG"

echo "running the self-test"
for d in files files/app; do adb shell "run-as $PKG sh -c 'mkdir -p $d && touch $d/inkline-selftest'"; done
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null
done=""
for _ in $(seq 1 60); do   # up to ten minutes
  sleep 10
  for d in files files/app; do
    if adb shell run-as "$PKG" cat "$d/selftest/selftest.log" 2>/dev/null | grep -q "selftest: \(done\|FAILED\)"; then
      done=$d
      break 2
    fi
  done
done
adb logcat -d > "$OUT/logcat.txt"
if [ -z "$done" ]; then
  echo "the self-test didn't finish; the end of the log:"
  grep -iE "python|inkline|qt|traceback|error" "$OUT/logcat.txt" | tail -80
  exit 1
fi
adb exec-out run-as "$PKG" tar -cf - -C "$done" selftest | tar -xf - -C "$OUT"
cat "$OUT/selftest/selftest.log"
grep -q "selftest: done" "$OUT/selftest/selftest.log" || exit 1

echo "pressing Print: Android's print dialog should open"
adb shell am force-stop "$PKG"
for d in files files/app; do
  adb shell "run-as $PKG sh -c 'rm -f $d/inkline-selftest; touch $d/inkline-printtest'"
done
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null
shown=""
for _ in $(seq 1 18); do   # up to three minutes
  sleep 10
  if adb shell dumpsys activity activities | grep -qi "printspooler"; then
    shown=yes
    break
  fi
done
sleep 5
adb exec-out screencap -p > "$OUT/print-dialog.png"
adb logcat -d > "$OUT/logcat-print.txt"
if [ -z "$shown" ]; then
  echo "Android's print dialog didn't open; the end of the log:"
  grep -iE "python|inkline|print|jnius|traceback|error" "$OUT/logcat-print.txt" | tail -60
  exit 1
fi
echo "Android's print dialog opened"
