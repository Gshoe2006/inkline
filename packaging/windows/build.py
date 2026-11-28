"""Builds Inkline for Windows, on Windows: dist/Inkline/ (the app folder), dist/inkline-<version>-windows-setup.exe
and dist/inkline-<version>-windows-portable.zip (the app folder to unzip and run, without installing).

    python packaging/windows/build.py              the app folder, the installer and the portable zip
    python packaging/windows/build.py --no-setup   the app folder and the portable zip (no Inno Setup needed)
    python packaging/windows/build.py --stage app      only the app folder (dist/Inkline/)
    python packaging/windows/build.py --stage package  the installer and the zip, from the app folder built before

Needs Python 3.10+ with PySide6-Essentials, numpy and pyinstaller (pip install PySide6-Essentials numpy
pyinstaller), and for the installer Inno Setup 6 (its iscc.exe on PATH or in Program Files).
The optional Rust module (faster photo styles) goes in when it's installed in that Python
(python packaging/build_fast.py --install builds and installs it; it needs Rust).

Code signing is optional (docs/code-signing.md). With INKLINE_SIGN_CMD set to a command holding {file}, such as

    "C:\\...\\signtool.exe" sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 /sha1 <thumbprint> {file}

(`build.py --signtool-template <thumbprint>` prints that one), Inkline.exe is signed before it goes into the
installer and the zip, and Inno Setup signs the installer and its uninstaller with the same command. A signer that
isn't a command (the release's Azure Trusted Signing step) signs between --stage app and --stage package instead.
Without INKLINE_SIGN_CMD nothing is signed.
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
TIMESTAMP_URL = "http://timestamp.digicert.com"
SIGN_ENV = "INKLINE_SIGN_CMD"


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
           # the optional Rust module, when it's installed (packaging/build_fast.py --install); only a warning if not
           "--hidden-import", "inkline_fast",
           # Qt for Python's Essentials are all Inkline uses; leave the rest of numpy's and Qt's extras out
           "--exclude-module", "tkinter", "--exclude-module", "unittest", "--exclude-module", "pydoc"]
    for d in data:
        cmd += ["--add-data", d]
    cmd.append(os.path.join(ROOT, "inkline.py"))
    subprocess.run(cmd, check=True, cwd=ROOT)
    return os.path.join(DIST, "Inkline")


# --- code signing (optional) -------------------------------------------------------------------------------------
def sign_template(env=None):
    """The signing command from INKLINE_SIGN_CMD, or None when nothing is to be signed."""
    template = (os.environ if env is None else env).get(SIGN_ENV, "").strip()
    if not template:
        return None
    if "{file}" not in template:
        raise SystemExit(f"build.py: {SIGN_ENV} should say where the file goes, with {{file}}")
    return template


def sign_command(template, path):
    """The command that signs one file, with its path quoted for cmd.exe."""
    return template.replace("{file}", f'"{path}"')


def inno_sign_tool(template):
    """The same command for Inno Setup's /S option: there $f is the quoted file name, $q a quote (ISCC's command line
    can't hold quotes inside a quoted argument) and $$ a $ of our own."""
    return template.replace("$", "$$").replace('"', "$q").replace("{file}", "$f")


def find_signtool(env=None, which=shutil.which, exists=os.path.exists, listdir=os.listdir):
    """signtool.exe from PATH, or from the newest Windows 10/11 SDK (GitHub's Windows runners have several)."""
    env = os.environ if env is None else env
    found = which("signtool")
    if found:
        return found
    base = os.path.join(env.get("ProgramFiles(x86)") or r"C:\Program Files (x86)", "Windows Kits", "10", "bin")
    try:
        names = listdir(base)
    except OSError:
        names = []
    versions = [n for n in names if n.replace(".", "").isdigit() and n.count(".") == 3]
    for name in sorted(versions, key=lambda n: tuple(int(x) for x in n.split(".")), reverse=True):
        path = os.path.join(base, name, "x64", "signtool.exe")
        if exists(path):
            return path
    raise SystemExit("build.py: signtool.exe isn't installed (it comes with the Windows SDK)")


def signtool_template(thumbprint, signtool=None, timestamp=TIMESTAMP_URL):
    """INKLINE_SIGN_CMD for a certificate in the Windows certificate store, chosen by its SHA-1 thumbprint, so no
    password is ever on a command line (Inno Setup prints the commands it runs)."""
    thumbprint = "".join(thumbprint.split()).upper()
    if len(thumbprint) != 40 or any(c not in "0123456789ABCDEF" for c in thumbprint):
        raise SystemExit(f"build.py: '{thumbprint}' isn't a certificate's SHA-1 thumbprint")
    signtool = signtool or find_signtool()
    return (f'"{signtool}" sign /fd sha256 /tr {timestamp} /td sha256 /sha1 {thumbprint} '
            "/d Inkline /du https://github.com/Gshoe2006/inkline {file}")


def app_files_to_sign(folder):
    """What in the app folder is signed: Inkline.exe (the DLLs PyInstaller copies in keep their makers' signatures)."""
    return [os.path.join(folder, "Inkline.exe")]


def sign(path, template, run=subprocess.run):
    print("signing", os.path.basename(path))   # not the command itself
    run(sign_command(template, path), shell=True, check=True)


def iscc():
    found = shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base and os.path.exists(os.path.join(base, "Inno Setup 6", "ISCC.exe")):
            return os.path.join(base, "Inno Setup 6", "ISCC.exe")
    raise SystemExit("build.py: Inno Setup 6 isn't installed (choco install innosetup, or --no-setup)")


def iscc_args(compiler, v, folder, template=None):
    """Inno Setup's command line. With a signing command, Inno Setup signs the installer and its uninstaller too."""
    args = [compiler, f"/DVERSION={v}", f"/DAPPDIR={folder}", f"/DOUTDIR={DIST}",
            f"/DICON={os.path.join(BUILD, 'inkline.ico')}", f"/DLICENSE={os.path.join(ROOT, 'LICENSE')}"]
    if template:
        args += ["/DSIGNTOOL", f"/Sinkline={inno_sign_tool(template)}"]
    return args + [os.path.join(HERE, "inkline.iss")]


def installer(folder, template=None):
    v = version()
    if not os.path.exists(os.path.join(BUILD, "inkline.ico")):   # --stage package in a fresh build folder
        os.makedirs(BUILD, exist_ok=True)
        make_ico(os.path.join(BUILD, "inkline.ico"))
    subprocess.run(iscc_args(iscc(), v, folder, template), check=True)
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
    if "--signtool-template" in argv[:-1]:
        print(signtool_template(argv[argv.index("--signtool-template") + 1]))
        return
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv[:-1] else "all"
    if stage not in ("all", "app", "package"):
        raise SystemExit("build.py: --stage app | package")
    template = sign_template()
    folder = os.path.join(DIST, "Inkline")
    if stage in ("all", "app"):
        folder = app_folder()
        for exe in app_files_to_sign(folder) if template else []:
            sign(exe, template)
        print("built", folder)
    if stage in ("all", "package"):
        if not os.path.exists(os.path.join(folder, "Inkline.exe")):
            raise SystemExit("build.py: there's no dist/Inkline/Inkline.exe to package (run --stage app first)")
        if "--no-setup" not in argv:
            print("built", installer(folder, template))
        print("built", portable_zip(folder))


if __name__ == "__main__":
    main(sys.argv[1:])
