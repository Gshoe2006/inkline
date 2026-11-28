#!/bin/sh
# Installs Inkline's APK on a running emulator, starts it (a screenshot of the window, after a minute), then runs the
# self-test there and copies its files out (packaging/android/build.py's main.py looks for the "inkline-selftest"
# file). The emulator's log goes with them.
#
#   [INKLINE_EXPECT_FAST=1] sh packaging/android/emulator-test.sh APK OUTDIR
#
# With INKLINE_EXPECT_FAST=1 the self-test must find the Rust module inkline_fast working (an "inkline-expect-fast"
# file beside "inkline-selftest" tells main.py), and its inkline-fast.txt must say so.
set -u
APK=$1
OUT=$2
EXPECT_FAST=${INKLINE_EXPECT_FAST:-}
PKG=io.github.gshoe2006.inkline
mkdir -p "$OUT"
adb install -r "$APK" || exit 1
adb logcat -c

echo "starting Inkline"
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null
sleep 60
adb exec-out screencap -p > "$OUT/window.png"
if adb shell pidof "$PKG" >/dev/null; then
  echo "Inkline is running after a minute"
else
  echo "Inkline isn't running after a minute; what it said:"
  adb logcat -d | grep -iE "python|inkline|AndroidRuntime|FATAL|has died|dlopen|cannot locate|Qt|libc " | grep -v ImeTracker | tail -60
fi
adb shell am force-stop "$PKG"

echo "running the self-test"
for d in files files/app; do
  adb shell "run-as $PKG sh -c 'mkdir -p $d && touch $d/inkline-selftest'"
  if [ "$EXPECT_FAST" = 1 ]; then adb shell "run-as $PKG touch $d/inkline-expect-fast"; fi
done
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
echo "inkline_fast: $(cat "$OUT/selftest/inkline-fast.txt" 2>/dev/null || echo 'no inkline-fast.txt')"
if [ "$EXPECT_FAST" = 1 ] && ! grep -q "^yes" "$OUT/selftest/inkline-fast.txt" 2>/dev/null; then
  echo "the APK should ship the Rust module inkline_fast, but the self-test didn't find it working"
  exit 1
fi

echo "pressing Print: Android's print dialog should open"
adb shell am force-stop "$PKG"
for d in files files/app; do
  adb shell "run-as $PKG sh -c 'rm -f $d/inkline-selftest $d/inkline-expect-fast; touch $d/inkline-printtest'"
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
