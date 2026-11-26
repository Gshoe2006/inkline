"""Builds Inkline for macOS, on a Mac: dist/Inkline.app and dist/inkline-<version>-macos.dmg.

    python3 packaging/macos/build.py            the app and the disk image
    python3 packaging/macos/build.py --no-dmg   only the app

Needs Python 3.10+ with PySide6-Essentials, numpy and pyinstaller (pip install PySide6-Essentials numpy
pyinstaller), and macOS's own iconutil, hdiutil and codesign. The app is built for the Mac it's built on (the
release builds on Apple silicon). It isn't signed with a Developer ID or notarized: PyInstaller signs it ad hoc,
so the first time it's opened macOS asks (Control-click → Open, or System Settings → Privacy & Security → Open
Anyway); see README.md.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build", "macos")
BUNDLE_ID = "io.github.gshoe2006.Inkline"


def version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


ICON_SIZES = [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"), (128, "128x128"),
              (256, "128x128@2x"), (256, "256x256"), (512, "256x256@2x"), (512, "512x512")]


def make_icns(out):
    """macOS's icon (.icns) from the PNGs the Linux packages install, with iconutil."""
    iconset = os.path.join(BUILD, "inkline.iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset)
    found = 0
    for px, name in ICON_SIZES:
        src = os.path.join(ROOT, "icons", "hicolor", f"{px}x{px}", "apps", "inkline.png")
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(iconset, f"icon_{name}.png"))
            found += 1
    if not found:
        raise SystemExit("build.py: no icons in icons/hicolor (run packaging/make_icon.py)")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
    return out


def app():
    os.makedirs(BUILD, exist_ok=True)
    icns = make_icns(os.path.join(BUILD, "inkline.icns"))
    data = [f"{os.path.join(ROOT, name)}:." for name in ("VERSION", "CHANGELOG.md", "inkline.svg", "LICENSE")]
    for sub in ("locale", "reading", "fonts"):   # translations, reading passages, handwriting and reading fonts
        data.append(f"{os.path.join(ROOT, 'inkengine', sub)}:inkengine/{sub}")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "Inkline",
           "--icon", icns, "--osx-bundle-identifier", BUNDLE_ID,
           "--distpath", DIST, "--workpath", BUILD, "--specpath", BUILD,
           "--collect-submodules", "inkengine", "--collect-submodules", "inkapp",
           "--exclude-module", "tkinter", "--exclude-module", "unittest", "--exclude-module", "pydoc"]
    for d in data:
        cmd += ["--add-data", d]
    cmd.append(os.path.join(ROOT, "inkline.py"))
    subprocess.run(cmd, check=True, cwd=ROOT)
    bundle = os.path.join(DIST, "Inkline.app")
    plist = os.path.join(bundle, "Contents", "Info.plist")
    v = version()
    for key, value in (("CFBundleShortVersionString", v), ("CFBundleVersion", v),
                       ("NSHighResolutionCapable", "true"), ("LSMinimumSystemVersion", "12.0")):
        kind = "-bool" if value == "true" else "-string"
        subprocess.run(["defaults", "write", plist, key, kind, value], check=True)
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", bundle], check=True)   # ad hoc, after editing
    return bundle


def dmg(bundle):
    """A disk image with the app and a link to Applications, to drag it across."""
    v = version()
    stage = os.path.join(BUILD, "dmg")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    subprocess.run(["ditto", bundle, os.path.join(stage, "Inkline.app")], check=True)
    os.symlink("/Applications", os.path.join(stage, "Applications"))
    out = os.path.join(DIST, f"inkline-{v}-macos.dmg")
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["hdiutil", "create", "-volname", f"Inkline {v}", "-srcfolder", stage, "-ov", "-format", "UDZO",
                    out], check=True)
    return out


def main(argv):
    if sys.platform != "darwin":
        raise SystemExit("build.py: build the macOS app on a Mac")
    bundle = app()
    print(f"built {bundle}")
    if "--no-dmg" not in argv:
        print(f"built {dmg(bundle)}")


if __name__ == "__main__":
    main(sys.argv[1:])
