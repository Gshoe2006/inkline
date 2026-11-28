#!/usr/bin/env python3
"""Builds the optional Rust module (rust/inkline_fast) as a wheel, for the packages that ship it.

    python3 packaging/build_fast.py                         a wheel for this machine, in dist/wheels
    python3 packaging/build_fast.py --install               ... and pip-installs it into this Python
    python3 packaging/build_fast.py --target universal2-apple-darwin --install    both Mac processors in one wheel
    python3 packaging/build_fast.py --max-glibc 2.34        fail if the wheel needs a newer glibc than the package

The wheel is abi3 (any CPython 3.9 or newer), so one per processor serves every package's Python. Its path is the
last line printed. Needs Rust (cargo; rustup to add a --target's standard library); uses maturin from PATH, or
installs it into a private virtual environment under ~/.cache/inkline-build the first time. Inkline runs the same
without the module (the Python code gives the same pages, only slower): see docs/performance.md.
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRATE = os.path.join(ROOT, "rust", "inkline_fast")
MATURIN = "maturin>=1.5,<2"
# the standard libraries each --target needs (universal2 is both Mac processors)
TARGETS = {"universal2-apple-darwin": ["aarch64-apple-darwin", "x86_64-apple-darwin"]}


def cache_dir(env=None):
    env = os.environ if env is None else env
    base = env.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "inkline-build")


def find_maturin(python=sys.executable, which=shutil.which, run=subprocess.run):
    """maturin beside the Python (pip-installed into it) or on PATH, or else from a virtual environment of our own
    (made, and maturin installed, the first time)."""
    beside = os.path.join(os.path.dirname(python), "maturin.exe" if os.name == "nt" else "maturin")
    if os.name == "nt" and not os.path.exists(beside):   # Windows keeps pip's commands in Scripts
        beside = os.path.join(os.path.dirname(python), "Scripts", "maturin.exe")
    if os.path.exists(beside):
        return beside
    found = which("maturin")
    if found:
        return found
    venv = os.path.join(cache_dir(), "maturin-venv")
    exe = os.path.join(venv, "Scripts", "maturin.exe") if os.name == "nt" else os.path.join(venv, "bin", "maturin")
    if not os.path.exists(exe):
        run([python, "-m", "venv", venv], check=True)
        pip = os.path.join(venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv, "bin", "python")
        run([pip, "-m", "pip", "install", "--disable-pip-version-check", "--quiet", MATURIN], check=True)
    return exe


def glibc_needed(wheel):
    """The glibc a Linux wheel needs, from its manylinux tag: (2, 34) for manylinux_2_34_x86_64; None otherwise."""
    tags = re.findall(r"manylinux_(\d+)_(\d+)_", os.path.basename(wheel))
    if not tags:
        old = {"manylinux1": (2, 5), "manylinux2010": (2, 12), "manylinux2014": (2, 17)}
        tags = [old[t] for t in re.findall(r"(manylinux1|manylinux2010|manylinux2014)_", os.path.basename(wheel))]
    return min((int(a), int(b)) for a, b in tags) if tags else None


def check_wheel(wheel, max_glibc=None):
    """Problems with a built wheel: not abi3, no extension module in it, or needing a newer glibc than allowed."""
    problems = []
    name = os.path.basename(wheel)
    if "-abi3-" not in name:
        problems.append(f"{name} isn't an abi3 wheel (rust/inkline_fast/Cargo.toml should ask PyO3 for abi3-py39)")
    with zipfile.ZipFile(wheel) as z:
        if not any(re.search(r"inkline_fast[^/]*\.(so|pyd)$", n) for n in z.namelist()):
            problems.append(f"{name} holds no inkline_fast extension module")
    if max_glibc:
        want = tuple(int(x) for x in max_glibc.split("."))
        got = glibc_needed(wheel)
        if got is None and "linux" in name:
            problems.append(f"{name} has no manylinux tag, so the glibc it needs isn't known")
        elif got and got > want:
            problems.append(f"{name} needs glibc {got[0]}.{got[1]}, newer than the package's {max_glibc}")
    return problems


def build(out, target=None, python=sys.executable, run=subprocess.run, which=shutil.which):
    if not which("cargo"):
        raise SystemExit("build_fast.py: Rust is needed (cargo): https://rustup.rs")
    if target and which("rustup"):
        for t in TARGETS.get(target, [target]):
            run(["rustup", "target", "add", t], check=True)
    os.makedirs(out, exist_ok=True)
    before = set(glob.glob(os.path.join(out, "inkline_fast-*.whl")))
    for old in before:   # only this build's wheel is left to find
        os.remove(old)
    cmd = [find_maturin(python, which, run), "build", "--release", "--locked", "--out", out, "--interpreter", python]
    if target:
        cmd += ["--target", target]
    run(cmd, check=True, cwd=CRATE)
    wheels = glob.glob(os.path.join(out, "inkline_fast-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"build_fast.py: expected one inkline_fast wheel in {out}, found {wheels}")
    return wheels[0]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="build_fast.py", description="Build rust/inkline_fast as an abi3 wheel.")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "wheels"), help="where the wheel goes")
    ap.add_argument("--target", help="a Rust target, e.g. universal2-apple-darwin (default: this machine)")
    ap.add_argument("--python", default=sys.executable, help="the Python to build for and --install into")
    ap.add_argument("--install", action="store_true", help="pip-install the wheel into --python")
    ap.add_argument("--max-glibc", help="Linux: the newest glibc the package may need, e.g. 2.34")
    a = ap.parse_args(argv)
    wheel = build(os.path.abspath(a.out), a.target, a.python)
    problems = check_wheel(wheel, a.max_glibc)
    if problems:
        raise SystemExit("build_fast.py: " + "; ".join(problems))
    if a.install:
        subprocess.run([a.python, "-m", "pip", "install", "--disable-pip-version-check", "--no-deps",
                        "--force-reinstall", wheel], check=True)
        subprocess.run([a.python, "-c", "import inkline_fast; print('inkline_fast', inkline_fast.__file__)"],
                       check=True, cwd=os.path.dirname(wheel))   # not from ROOT, which has a rust/ folder of its own
    print(wheel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
