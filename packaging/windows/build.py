"""Builds Inkline for Windows, on Windows: dist/Inkline/ (the app folder) and dist/inkline-<version>-windows-setup.exe.

    python packaging/windows/build.py              the app folder and the installer
    python packaging/windows/build.py --no-setup   only the app folder (no Inno Setup needed)

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


def main(argv):
    folder = app_folder()
    print("built", folder)
    if "--no-setup" not in argv:
        print("built", installer(folder))


if __name__ == "__main__":
    main(sys.argv[1:])
