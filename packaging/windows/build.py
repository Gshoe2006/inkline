"""Builds Inkline for Windows, on Windows: dist/Inkline/ (the app folder), dist/inkline-<version>-windows-setup.exe
and dist/inkline-<version>-windows-portable.zip (the app folder to unzip and run, without installing).

    python packaging/windows/build.py              the app folder, the installer and the portable zip
    python packaging/windows/build.py --no-setup   the app folder and the portable zip (no Inno Setup needed)

Needs Python 3.10+ with PySide6-Essentials, numpy and pyinstaller (pip install PySide6-Essentials numpy
pyinstaller), and for the installer Inno Setup 6 (its iscc.exe on PATH or in Program Files).
"""

import glob
import os
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build", "windows")


def version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


def make_ico(out):
    """A Windows icon holding the PNG sizes the Linux packages install (each stored as PNG, as Vista+ reads)."""
    images = []
    for n in (16, 24, 32, 48, 64, 128, 256):
        path = os.path.join(ROOT, "icons", "hicolor", f"{n}x{n}", "apps", "inkline.png")
        if os.path.exists(path):
            with open(path, "rb") as f:
                images.append((n, f.read()))
    if not images:
        raise SystemExit("build.py: no icons in icons/hicolor (run packaging/make_icon.py)")
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for n, png in images:
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    with open(out, "wb") as f:
        f.write(head + entries + data)
    return out


def app_folder():
    os.makedirs(BUILD, exist_ok=True)
    ico = make_ico(os.path.join(BUILD, "inkline.ico"))
    sep = ";" if os.name == "nt" else ":"
    data = [f"{os.path.join(ROOT, name)}{sep}." for name in ("VERSION", "CHANGELOG.md", "inkline.svg", "LICENSE")]
    data.append(f"{os.path.join(ROOT, 'inkengine', 'locale')}{sep}inkengine/locale")   # the translations
    data.append(f"{os.path.join(ROOT, 'inkengine', 'reading')}{sep}inkengine/reading")   # reading passages
    data.append(f"{os.path.join(ROOT, 'inkengine', 'fonts')}{sep}inkengine/fonts")     # joined-up handwriting
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "Inkline",
           "--icon", ico, "--distpath", DIST, "--workpath", BUILD, "--specpath", BUILD,
           "--collect-submodules", "inkengine", "--collect-submodules", "inkapp",
           # Qt for Python's Essentials are all Inkline uses; leave the rest of numpy's and Qt's extras out
           "--exclude-module", "tkinter", "--exclude-module", "unittest", "--exclude-module", "pydoc"]
    for d in data:
        cmd += ["--add-data", d]
    cmd.append(os.path.join(ROOT, "inkline.py"))
    subprocess.run(cmd, check=True, cwd=ROOT)
    return os.path.join(DIST, "Inkline")


def iscc():
    found = shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base and os.path.exists(os.path.join(base, "Inno Setup 6", "ISCC.exe")):
            return os.path.join(base, "Inno Setup 6", "ISCC.exe")
    raise SystemExit("build.py: Inno Setup 6 isn't installed (choco install innosetup, or --no-setup)")


def installer(folder):
    v = version()
    subprocess.run([iscc(), f"/DVERSION={v}", f"/DAPPDIR={folder}", f"/DOUTDIR={DIST}",
                    f"/DICON={os.path.join(BUILD, 'inkline.ico')}", f"/DLICENSE={os.path.join(ROOT, 'LICENSE')}",
                    os.path.join(HERE, "inkline.iss")], check=True)
    out = os.path.join(DIST, f"inkline-{v}-windows-setup.exe")
    if not os.path.exists(out):
        raise SystemExit(f"build.py: Inno Setup didn't write {out}")
    return out


PORTABLE_NOTE = """This copy of Inkline runs from this folder, without installing: start Inkline.exe.

This file tells Inkline it's the portable copy, so Help > Check for updates downloads the new .zip for you to
unzip in place of this folder, instead of running an installer. Your settings are kept in your user profile,
as for an installed Inkline.
"""


def portable_zip(folder):
    """The app folder as Inkline/ in a .zip, with a "portable" file beside Inkline.exe (see updater.install_kind)."""
    v = version()
    stage = os.path.join(BUILD, "portable")
    shutil.rmtree(stage, ignore_errors=True)
    shutil.copytree(folder, os.path.join(stage, "Inkline"))
    with open(os.path.join(stage, "Inkline", "portable"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(PORTABLE_NOTE)
    base = os.path.join(DIST, f"inkline-{v}-windows-portable")
    return shutil.make_archive(base, "zip", stage, "Inkline")


def main(argv):
    folder = app_folder()
    print("built", folder)
    if "--no-setup" not in argv:
        print("built", installer(folder))
    print("built", portable_zip(folder))


if __name__ == "__main__":
    main(sys.argv[1:])
