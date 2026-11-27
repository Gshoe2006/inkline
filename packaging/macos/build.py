"""Builds Inkline for macOS, on a Mac: dist/Inkline.app and its disk image.

    python3 packaging/macos/build.py --arch arm64       Apple silicon: inkline-<version>-macos-arm64.dmg
    python3 packaging/macos/build.py --arch intel       Intel Macs:    inkline-<version>-macos-intel.dmg
    python3 packaging/macos/build.py --arch universal   both, in one app: inkline-<version>-macos.dmg
    python3 packaging/macos/build.py --arch … --no-dmg  only the app

Needs Python 3.10+ with PySide6-Essentials, numpy and pyinstaller (pip install PySide6-Essentials numpy
pyinstaller), and macOS's own iconutil, hdiutil, lipo and codesign. arm64 and intel are built with a Python for
that processor (the release builds each on a Mac of that kind). universal needs a universal2 Python (python.org's
installer) and a universal2 numpy (PyPI has only one processor's in each wheel: the release joins the two with
delocate-merge; PySide6's wheels are universal2 already). The universal one is what Inkline's updater installs.
PySide6 6.12 needs macOS 14 (Sonoma) or newer.

The optional Rust module (faster photo styles) goes in when it's installed in that Python: packaging/build_fast.py
--install builds it for this Mac, or with --target universal2-apple-darwin for the universal app.

Signing (docs/code-signing.md): with MACOS_SIGN_IDENTITY set (a Developer ID Application identity in a keychain;
MACOS_KEYCHAIN names the keychain if it isn't the default one), packaging/macos/sign.py signs everything in the app
inside out with the hardened runtime, then signs, notarizes and staples the disk image (when it finds Apple's
notarization credentials). Without it the app is signed ad hoc, so the first time it's opened macOS asks
(Control-click → Open, or System Settings → Privacy & Security → Open Anyway); see README.md.
"""

import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sign  # noqa: E402  (packaging/macos/sign.py)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build", "macos")
BUNDLE_ID = "io.github.gshoe2006.Inkline"
ARCHES = {"arm64": ("arm64", "-arm64"), "intel": ("x86_64", "-intel"), "universal": ("universal2", "")}   # target, name
LIPO = {"arm64": {"arm64"}, "intel": {"x86_64"}, "universal": {"arm64", "x86_64"}}   # what the app's program holds
MIN_MACOS = "14.0"   # PySide6 6.12's wheels are built for macOS 14


def dmg_name(arch, version):
    return f"inkline-{version}-macos{ARCHES[arch][1]}.dmg"


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


def signing(env=None):
    """(identity, keychain) for Developer ID signing, or (None, None) to sign ad hoc."""
    env = os.environ if env is None else env
    identity = env.get("MACOS_SIGN_IDENTITY", "").strip()
    return (identity, env.get("MACOS_KEYCHAIN") or None) if identity else (None, None)


def ad_hoc_command(bundle):
    return ["codesign", "--force", "--deep", "--sign", "-", bundle]


def app(arch="arm64"):
    os.makedirs(BUILD, exist_ok=True)
    icns = make_icns(os.path.join(BUILD, "inkline.icns"))
    data = [f"{os.path.join(ROOT, name)}:." for name in ("VERSION", "CHANGELOG.md", "inkline.svg", "LICENSE")]
    for sub in ("locale", "reading", "fonts"):   # translations, reading passages, handwriting and reading fonts
        data.append(f"{os.path.join(ROOT, 'inkengine', sub)}:inkengine/{sub}")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "Inkline",
           "--icon", icns, "--osx-bundle-identifier", BUNDLE_ID, "--target-arch", ARCHES[arch][0],
           "--distpath", DIST, "--workpath", BUILD, "--specpath", BUILD,
           "--collect-submodules", "inkengine", "--collect-submodules", "inkapp",
           # the optional Rust module, when it's installed (packaging/build_fast.py --install); only a warning if not
           "--hidden-import", "inkline_fast",
           "--exclude-module", "tkinter", "--exclude-module", "unittest", "--exclude-module", "pydoc"]
    for d in data:
        cmd += ["--add-data", d]
    cmd.append(os.path.join(ROOT, "inkline.py"))
    subprocess.run(cmd, check=True, cwd=ROOT)
    bundle = os.path.join(DIST, "Inkline.app")
    plist = os.path.join(bundle, "Contents", "Info.plist")
    v = version()
    for key, value in (("CFBundleShortVersionString", v), ("CFBundleVersion", v),
                       ("NSHighResolutionCapable", "true"), ("LSMinimumSystemVersion", MIN_MACOS)):
        kind = "-bool" if value == "true" else "-string"
        subprocess.run(["defaults", "write", plist, key, kind, value], check=True)
    identity, keychain = signing()   # after editing Info.plist, which changes what the signature covers
    if identity:
        sign.sign_app(bundle, identity, keychain)
    else:
        print("Not signed with a Developer ID (no MACOS_SIGN_IDENTITY): signing ad hoc; see docs/code-signing.md")
        subprocess.run(ad_hoc_command(bundle), check=True)
    program = os.path.join(bundle, "Contents", "MacOS", "Inkline")
    held = set(subprocess.run(["lipo", "-archs", program], check=True, capture_output=True, text=True).stdout.split())
    if held != LIPO[arch]:
        raise SystemExit(f"build.py: Inkline.app's program is for {sorted(held)}, not {sorted(LIPO[arch])}")
    return bundle


def dmg(bundle, arch="arm64"):
    """A disk image with the app and a link to Applications, to drag it across."""
    v = version()
    stage = os.path.join(BUILD, "dmg")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    subprocess.run(["ditto", bundle, os.path.join(stage, "Inkline.app")], check=True)
    os.symlink("/Applications", os.path.join(stage, "Applications"))
    out = os.path.join(DIST, dmg_name(arch, v))
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["hdiutil", "create", "-volname", f"Inkline {v}", "-srcfolder", stage, "-ov", "-format", "UDZO",
                    out], check=True)
    identity, keychain = signing()
    if identity:
        sign.sign_and_notarize_dmg(out, identity, keychain)
    return out


def main(argv):
    if sys.platform != "darwin":
        raise SystemExit("build.py: build the macOS app on a Mac")
    arch = argv[argv.index("--arch") + 1] if "--arch" in argv[:-1] else None
    if arch not in ARCHES:
        raise SystemExit(f"build.py: say which Macs it's for: --arch {' | '.join(ARCHES)}")
    bundle = app(arch)
    print(f"built {bundle}")
    if "--no-dmg" not in argv:
        print(f"built {dmg(bundle, arch)}")


if __name__ == "__main__":
    main(sys.argv[1:])
