"""Builds Inkline for Android (the desktop window, in its touch layout, on a phone or tablet), on Linux:
dist/inkline-<version>-android-<arch>-debug.apk, a debug build to install by hand (adb install, or open it on the
device); with --release, a signed dist/inkline-<version>-android-<arch>.apk; with --release --aab, an Android App
Bundle for Google Play as well: dist/inkline-<version>-android.aab (arm64, the one Play gets) or
-android-x86_64.aab.

    python3 packaging/android/build.py --arch aarch64 --wheel-pyside PYSIDE.whl --wheel-shiboken SHIBOKEN.whl
                                       [--release [--aab]] [--target-api N] [--ndk PATH] [--sdk PATH]

arch is aarch64 (phones and tablets) or x86_64 (the emulator, Chromebooks). The wheels are Qt's PySide6 and
shiboken6 builds for Android and that arch (download.qt.io/official_releases/QtForPython/, the same version as the
PySide6 this Python has). Uses Qt's pyside6-android-deploy (from that PySide6) with buildozer and
python-for-android; needs JDK 17, the Android SDK and NDK r28c (or it uses ~/.pyside6_android_deploy), git and the
usual build tools, and Rust (cargo, with rustup's aarch64-linux-android or x86_64-linux-android target) for
the optional module inkline_fast. deploy.py adds what the tool doesn't know Inkline needs: numpy, inkline_fast,
and its data files.

One bundle holds one ABI: python-for-android's Qt bootstrap builds a single arch per run (each arch has its own
PySide6 wheel), and the per-arch bundles can't simply be merged (each has its own list of Qt libraries to load in
its resources). Play takes an arm64-only bundle; see docs/publishing.md.

The versionCode (version_code()) comes from VERSION and the arch, and rises with every release.

On the device, a file named "inkline-selftest" in the app's private folder makes it run the self-test into
selftest/ there instead of opening the window (with "inkline-expect-fast" beside it, the self-test fails unless
the Rust module inkline_fast loads and gives the Python code's results), one named "inkline-printtest" makes it press Print a few seconds
after it opens, and one named "inkline-screens" makes it show its pages in turn for screenshots, with Print's
dialog last (inkline_screens.py, below; CI does all three on an emulator, with adb run-as).
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")

MAIN = '''"""Inkline on Android (written by packaging/android/build.py)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PRIVATE = os.environ.get("ANDROID_PRIVATE") or HERE   # the app's own folder (python-for-android sets it)
if os.path.exists(os.path.join(PRIVATE, "inkline-selftest")):   # CI: the self-test, its words in selftest.log
    out = os.path.join(PRIVATE, "selftest")
    os.makedirs(out, exist_ok=True)
    sys.stdout = sys.stderr = open(os.path.join(out, "selftest.log"), "w", encoding="utf-8", buffering=1)
    sys.argv = [sys.argv[0], "--selftest", out]   # on Android's own display: the APK has no "offscreen" plugin
if os.path.exists(os.path.join(PRIVATE, "inkline-expect-fast")):   # CI: the self-test requires inkline_fast
    os.environ["INKLINE_EXPECT_FAST"] = "1"
if os.path.exists(os.path.join(PRIVATE, "inkline-printtest")):   # CI: press Print once the window is up
    os.environ["INKLINE_PRINT_TEST"] = "1"
if os.path.exists(os.path.join(PRIVATE, "inkline-screens")):   # CI: each page in turn, for screenshots
    import inkline_screens
    inkline_screens.install(os.path.join(PRIVATE, "screens"))
import inkline  # noqa: E402

inkline.main()
'''

SCREENS = os.path.join(HERE, "screens.py")   # staged as inkline_screens.py
ABI_DIGIT = {"aarch64": 1, "x86_64": 2}       # x86_64 higher: a device that runs both gets it
CODE_BASE = 1_000_000_000   # above the 102860100 python-for-android gave 6.1.0 (10, min API 28, 60100), so those update


def version_code(version, arch):
    """Android's versionCode for VERSION X.Y.Z on arch: 1 000 000 000 + XYYZZ × 10 + the arch's digit (6.1.0 on
    arm64: 1000601001). It rises with every release while Y and Z stay under 100, and leaves room for X up to
    10999 under Play's limit of 2 100 000 000."""
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"version {version!r} isn't X.Y.Z")
    major, minor, patch = (int(p) for p in parts)
    if minor > 99 or patch > 99:
        raise ValueError(f"version {version!r}: the versionCode has room for minor and patch up to 99")
    return CODE_BASE + (major * 10000 + minor * 100 + patch) * 10 + ABI_DIGIT[arch]


def outputs(version, arch, release=False, aab=False):
    """(the APK's name, the bundle's name or None) in dist/."""
    apk = f"inkline-{version}-android-{arch}{'' if release else '-debug'}.apk"
    bundle = None
    if aab:
        bundle = f"inkline-{version}-android.aab" if arch == "aarch64" else f"inkline-{version}-android-{arch}.aab"
    return apk, bundle


def _load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def icons(arch):
    """The launcher icons, drawn from inkline.svg (play/make_graphics.py), beside the app folder (not in it: the app
    folder's .png files would be packed as app files)."""
    out = os.path.join(ROOT, "build", "android", arch, "icons")
    _load("make_graphics", os.path.join(HERE, "play", "make_graphics.py")).app_icons(out)
    return out


def version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


def stage(arch):
    """The app folder the deploy tool packs: Inkline's code and files, with main.py (the tool's required name)."""
    app = os.path.join(ROOT, "build", "android", arch, "app")
    shutil.rmtree(app, ignore_errors=True)
    os.makedirs(app)
    for name in ("inkengine", "inkapp"):
        shutil.copytree(os.path.join(ROOT, name), os.path.join(app, name),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("inkline.py", "inkline.svg", "VERSION", "LICENSE", "CHANGELOG.md"):
        shutil.copy2(os.path.join(ROOT, name), app)
    with open(os.path.join(app, "main.py"), "w", encoding="utf-8") as f:
        f.write(MAIN)
    shutil.copy2(SCREENS, os.path.join(app, "inkline_screens.py"))
    return app


def newest(app, ext):
    found = sorted(glob.glob(os.path.join(app, "**", f"*.{ext}"), recursive=True), key=os.path.getmtime)
    return found[-1] if found else None


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--arch", choices=("aarch64", "x86_64"), required=True)
    p.add_argument("--wheel-pyside", required=True)
    p.add_argument("--wheel-shiboken", required=True)
    p.add_argument("--release", action="store_true", help="a signed release APK (the key: see deploy.py)")
    p.add_argument("--aab", action="store_true", help="with --release: a signed .aab for Google Play as well")
    p.add_argument("--target-api", help="the targetSdk (default: deploy.py's ANDROID_API)")
    p.add_argument("--ndk")
    p.add_argument("--sdk")
    a = p.parse_args(argv)
    if a.aab and not a.release:
        p.error("--aab needs --release")
    if not sys.platform.startswith("linux"):
        raise SystemExit("build.py: build the Android app on Linux")
    app = stage(a.arch)
    v = version()
    cmd = [sys.executable, os.path.join(HERE, "deploy.py"), "--version", v,
           "--numeric-version", str(version_code(v, a.arch)), "--icons", icons(a.arch),
           *(["--release"] if a.release else []), *(["--aab"] if a.aab else []),
           *(["--target-api", a.target_api] if a.target_api else []),
           "--",
           "--name", "Inkline", "--force", "--verbose", "--keep-deployment-files",
           "--wheel-pyside", os.path.abspath(a.wheel_pyside), "--wheel-shiboken", os.path.abspath(a.wheel_shiboken)]
    if a.ndk:
        cmd += ["--ndk-path", os.path.abspath(a.ndk)]
    if a.sdk:
        cmd += ["--sdk-path", os.path.abspath(a.sdk)]
    subprocess.run(cmd, check=True, cwd=app)
    apk_name, aab_name = outputs(v, a.arch, a.release, a.aab)
    built = newest(app, "apk")
    if not built:
        raise SystemExit("build.py: the deploy tool made no .apk (see its output above)")
    os.makedirs(DIST, exist_ok=True)
    shutil.copyfile(built, os.path.join(DIST, apk_name))
    print("built", os.path.join(DIST, apk_name))
    if aab_name:
        bundle = newest(app, "aab")
        if not bundle:
            raise SystemExit("build.py: the deploy tool made no .aab (see its output above)")
        shutil.copyfile(bundle, os.path.join(DIST, aab_name))
        print("built", os.path.join(DIST, aab_name))


if __name__ == "__main__":
    main(sys.argv[1:])
