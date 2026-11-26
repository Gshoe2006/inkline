"""Builds Inkline for Android (a first test: the desktop window as it is, on a phone or tablet), on Linux:
dist/inkline-<version>-android-<arch>.apk, a debug build to install by hand (adb install, or open it on the device).

    python3 packaging/android/build.py --arch aarch64 --wheel-pyside PYSIDE.whl --wheel-shiboken SHIBOKEN.whl
                                       [--ndk PATH] [--sdk PATH]

arch is aarch64 (phones and tablets) or x86_64 (the emulator, Chromebooks). The wheels are Qt's PySide6 and
shiboken6 builds for Android and that arch (download.qt.io/official_releases/QtForPython/, the same version as the
PySide6 this Python has). Uses Qt's pyside6-android-deploy (from that PySide6) with buildozer and
python-for-android; needs JDK 17, the Android SDK and NDK r28c (or it uses ~/.pyside6_android_deploy), git and the
usual build tools. deploy.py adds what the tool doesn't know Inkline needs: numpy, and its data files.

On the device, a file named "inkline-selftest" in the app's private folder makes it run the self-test into
selftest/ there instead of opening the window (CI does this on an emulator, with adb run-as).
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
    sys.argv = [sys.argv[0], "--selftest", out]
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import inkline  # noqa: E402

inkline.main()
'''


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
    return app


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--arch", choices=("aarch64", "x86_64"), required=True)
    p.add_argument("--wheel-pyside", required=True)
    p.add_argument("--wheel-shiboken", required=True)
    p.add_argument("--ndk")
    p.add_argument("--sdk")
    a = p.parse_args(argv)
    if not sys.platform.startswith("linux"):
        raise SystemExit("build.py: build the Android app on Linux")
    app = stage(a.arch)
    cmd = [sys.executable, os.path.join(HERE, "deploy.py"), "--version", version(), "--",
           "--name", "Inkline", "--force", "--verbose", "--keep-deployment-files",
           "--wheel-pyside", os.path.abspath(a.wheel_pyside), "--wheel-shiboken", os.path.abspath(a.wheel_shiboken)]
    if a.ndk:
        cmd += ["--ndk-path", os.path.abspath(a.ndk)]
    if a.sdk:
        cmd += ["--sdk-path", os.path.abspath(a.sdk)]
    subprocess.run(cmd, check=True, cwd=app)
    built = sorted(glob.glob(os.path.join(app, "**", "*.apk"), recursive=True), key=os.path.getmtime)
    if not built:
        raise SystemExit("build.py: the deploy tool made no .apk (see its output above)")
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, f"inkline-{version()}-android-{a.arch}.apk")
    shutil.copyfile(built[-1], out)
    print("built", out)


if __name__ == "__main__":
    main(sys.argv[1:])
