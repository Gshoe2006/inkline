"""The optional Rust module (rust/inkline_fast) in the release packages: built for each processor by
packaging/build_fast.py (or inside the Flatpak's and the Snap's own builders), installed beside numpy, and proved
to load by each package's self-test. The .run and the Arch package use their Python code instead. (Android builds
it with a python-for-android recipe: tests/test_android.py.)"""

import importlib.util
import os
import re
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


def _load(name, *p):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bf = _load("build_fast", "packaging", "build_fast.py")


# --- the wheel ---------------------------------------------------------------------------------------------------

def test_the_module_is_built_for_every_python_from_3_9():
    cargo = _read("rust", "inkline_fast", "Cargo.toml")
    assert re.search(r'pyo3 = \{[^}]*"abi3-py39"', cargo)       # one wheel per processor, whatever the Python
    assert 'requires-python = ">=3.9"' in _read("rust", "inkline_fast", "pyproject.toml")


def _wheel(tmp_path, name, files=("inkline_fast/__init__.py", "inkline_fast/inkline_fast.abi3.so")):
    p = tmp_path / name
    with zipfile.ZipFile(p, "w") as z:
        for f in files:
            z.writestr(f, "")
    return str(p)


def test_wheels_are_checked_for_abi3_the_module_and_glibc(tmp_path):
    good = _wheel(tmp_path, "inkline_fast-0.1.0-cp39-abi3-manylinux_2_34_x86_64.whl")
    assert bf.glibc_needed(good) == (2, 34)
    assert bf.check_wheel(good) == [] and bf.check_wheel(good, "2.34") == [] and bf.check_wheel(good, "2.39") == []
    assert "newer than the package's 2.31" in bf.check_wheel(good, "2.31")[0]
    both = _wheel(tmp_path, "inkline_fast-0.1.0-cp39-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl")
    assert bf.glibc_needed(both) == (2, 17)
    not_abi3 = _wheel(tmp_path, "inkline_fast-0.1.0-cp312-cp312-manylinux_2_34_x86_64.whl")
    assert "isn't an abi3 wheel" in bf.check_wheel(not_abi3)[0]
    empty = _wheel(tmp_path, "inkline_fast-0.1.0-cp39-abi3-win_amd64.whl", files=("inkline_fast/__init__.py",))
    assert "holds no inkline_fast extension module" in bf.check_wheel(empty)[0]
    mac = _wheel(tmp_path, "inkline_fast-0.1.0-cp39-abi3-macosx_10_12_universal2.whl",
                 files=("inkline_fast/inkline_fast.abi3.so",))
    assert bf.glibc_needed(mac) is None and bf.check_wheel(mac, "2.34") == []
    plain = _wheel(tmp_path, "inkline_fast-0.1.0-cp39-abi3-linux_x86_64.whl")
    assert "glibc it needs isn't known" in bf.check_wheel(plain, "2.34")[0]


def test_build_asks_maturin_for_a_locked_release_build(tmp_path):
    calls = []

    def run(cmd, check, cwd=None):
        calls.append((cmd, cwd))
        if cmd[1] == "build":
            out = cmd[cmd.index("--out") + 1]
            _wheel(tmp_path / "out", "inkline_fast-0.1.0-cp39-abi3-macosx_10_12_universal2.whl")
            assert out == str(tmp_path / "out")
    (tmp_path / "out").mkdir()
    _wheel(tmp_path / "out", "inkline_fast-0.0.9-cp39-abi3-macosx_11_0_arm64.whl")   # an old one: removed first
    which = {"cargo": "/bin/cargo", "rustup": "/bin/rustup", "maturin": "/bin/maturin"}.get
    wheel = bf.build(str(tmp_path / "out"), "universal2-apple-darwin", "/py/bin/python3", run=run, which=which)
    assert os.path.basename(wheel) == "inkline_fast-0.1.0-cp39-abi3-macosx_10_12_universal2.whl"
    assert [c for c, _ in calls[:2]] == [["rustup", "target", "add", "aarch64-apple-darwin"],
                                         ["rustup", "target", "add", "x86_64-apple-darwin"]]
    cmd, cwd = calls[2]
    assert cmd[:4] == ["/bin/maturin", "build", "--release", "--locked"] and cwd == bf.CRATE
    assert cmd[cmd.index("--interpreter") + 1] == "/py/bin/python3"
    assert cmd[cmd.index("--target") + 1] == "universal2-apple-darwin"
    with pytest.raises(SystemExit, match="Rust is needed"):
        bf.build(str(tmp_path / "out"), run=run, which=lambda name: None)


def test_maturin_comes_from_beside_the_python_then_path_then_its_own_venv(tmp_path, monkeypatch):
    py = tmp_path / "bin" / "python3"
    py.parent.mkdir()
    py.write_text("")
    beside = tmp_path / "bin" / ("maturin.exe" if os.name == "nt" else "maturin")
    beside.write_text("")
    assert bf.find_maturin(str(py), which=lambda n: "/elsewhere/maturin") == str(beside)
    beside.unlink()
    assert bf.find_maturin(str(py), which=lambda n: "/elsewhere/maturin") == "/elsewhere/maturin"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    calls = []
    got = bf.find_maturin(str(py), which=lambda n: None, run=lambda cmd, check: calls.append(cmd))
    assert got.startswith(str(tmp_path / "cache" / "inkline-build" / "maturin-venv"))
    assert calls[0][:3] == [str(py), "-m", "venv"] and bf.MATURIN in calls[1]


# --- each package ------------------------------------------------------------------------------------------------

def test_the_deb_rpm_and_appimage_take_the_wheel_for_their_processor():
    for script, arches in ((("debian", "build-deb.sh"), ("amd64:*-abi3-*x86_64.whl", "arm64:*-abi3-*aarch64.whl")),
                           (("rpm", "build-rpm.sh"), ("x86_64:*-abi3-*x86_64.whl", "aarch64:*-abi3-*aarch64.whl")),
                           (("appimage", "build-appimage.sh"), ('*-abi3-*"$ARCH".whl',))):
        sh = _read("packaging", *script)
        assert "FAST=${INKLINE_FAST_WHEEL:-}" in sh, script
        assert "isn't an abi3 wheel for $ARCH" in sh and "without inkline_fast" in sh, script
        for a in arches:
            assert a in sh, (script, a)
    for script in (("debian", "build-deb.sh"), ("rpm", "build-rpm.sh")):   # unpacked beside PySide6, like it
        assert 'python3 -m zipfile -e "$FAST" "$R/usr/lib/inkline/vendor"' in _read("packaging", *script)
    assert '"$PY" -m pip install --quiet --no-cache-dir --no-compile --no-deps "$FAST"' in \
        _read("packaging", "appimage", "build-appimage.sh")
    deb = _read("packaging", "debian", "build-deb.sh")
    assert "Files: usr/lib/inkline/vendor/inkline_fast*\nLicense: GPL-3.0-or-later" in deb   # not PySide6's licence


def test_the_windows_and_mac_apps_bundle_it():
    for p in (("windows", "build.py"), ("macos", "build.py")):
        assert '"--hidden-import", "inkline_fast"' in _read("packaging", *p)


def test_the_flatpak_builds_it_offline_from_crates_pinned_by_cargo_lock():
    yaml = pytest.importorskip("yaml")
    m = yaml.safe_load(_read("packaging", "flatpak", "io.github.gshoe2006.Inkline.yml"))
    assert m["sdk-extensions"] == ["org.freedesktop.Sdk.Extension.rust-stable"]
    app = m["modules"][-1]
    assert app["build-options"]["append-path"] == "/usr/lib/sdk/rust-stable/bin"
    assert app["build-options"]["env"]["CARGO_HOME"] == f"/run/build/{app['name']}/cargo"
    cmds = app["build-commands"]
    assert cmds[0] == "cargo build --release --offline --locked --manifest-path rust/inkline_fast/Cargo.toml"
    assert "inkline_fast.abi3.so" in cmds[1] and "platlib" in cmds[1]
    assert "rust/inkline_fast/target" in app["sources"][0]["skip"]   # a local build's target folder stays out
    cs = _load("cargo_sources", "packaging", "flatpak", "cargo_sources.py")
    assert cs.main(["--check"]) == 0                                  # in step with Cargo.lock
    lock = cs.crates(_read("rust", "inkline_fast", "Cargo.lock"))
    archives = [s for s in app["sources"] if s["type"] == "archive"]
    assert len(archives) == len(lock) > 20
    for (name, version, sha), a in zip(lock, archives):
        assert a["url"] == f"https://static.crates.io/crates/{name}/{name}-{version}.crate" and a["sha256"] == sha
    config = app["sources"][-1]
    assert config["dest"] == "cargo" and 'replace-with = "vendored-sources"' in config["contents"]
    assert 'directory = "cargo/vendor"' in config["contents"]
    assert '"org.freedesktop.Sdk.Extension.rust-stable//$RUNTIME"' in _read("packaging", "flatpak", "build.sh")


def test_cargo_sources_notices_a_changed_lock(tmp_path, monkeypatch):
    cs = _load("cargo_sources2", "packaging", "flatpak", "cargo_sources.py")
    lock = _read("rust", "inkline_fast", "Cargo.lock").replace('version = "0.23.5"', 'version = "0.23.6"', 1)
    (tmp_path / "Cargo.lock").write_text(lock)
    monkeypatch.setattr(cs, "LOCK", str(tmp_path / "Cargo.lock"))
    assert cs.main(["--check"]) == 1
    with pytest.raises(SystemExit):
        cs.crates('[[package]]\nname = "x"\nversion = "1"\nsource = "git+https://example.com/x"\n')


def test_the_snap_builds_it_beside_numpy():
    yaml = pytest.importorskip("yaml")
    snap = yaml.safe_load(_read("snap", "snapcraft.yaml"))
    fast = snap["parts"]["fast"]
    assert fast["after"] == ["deps"] and fast["source"] == "rust/inkline_fast" and fast["plugin"] == "nil"
    assert "cargo build --release --locked" in fast["override-build"]
    assert '/lib/python$PYV/site-packages/inkline_fast.abi3.so"' in fast["override-build"]
    assert fast["prime"] == ["lib/python3*/site-packages/inkline_fast.abi3.so"]


def test_the_release_builds_it_for_each_package_and_their_self_tests_require_it():
    wf = _read(".github", "workflows", "release.yml")
    jobs = re.split(r"\n  (?=[a-z-]+:\n)", wf.split("\njobs:\n", 1)[1])
    job = {j.split(":", 1)[0]: j for j in jobs}
    for name in ("deb", "appimage", "rpm"):
        j = job[name]
        assert "python3 packaging/build_fast.py --out \"$RUNNER_TEMP/wheels\" --max-glibc" in j, name
        assert 'echo "INKLINE_FAST_WHEEL=$(ls "$RUNNER_TEMP"/wheels/inkline_fast-*.whl)" >> "$GITHUB_ENV"' in j, name
        assert "INKLINE_EXPECT_FAST=1" in j, name
    assert "--max-glibc ${{ matrix.arch == 'amd64' && '2.34' || '2.39' }}" in job["deb"]   # as the deb's libc6 (>= …)
    assert "--max-glibc ${{ matrix.arch == 'x86_64' && '2.34' || '2.39' }}" in job["rpm"]
    assert "dnf install" in job["rpm"] and " cargo rust gcc" in job["rpm"]
    for name in ("deb", "appimage", "windows", "macos"):
        assert "uses: dtolnay/rust-toolchain@stable" in job[name], name
    assert "INKLINE_EXPECT_FAST=1" in job["rpm-opensuse"] and "INKLINE_EXPECT_FAST=1" in job["snap"]
    assert 'python packaging/build_fast.py --out "$env:RUNNER_TEMP\\wheels" --install' in job["windows"]
    assert job["windows"].count('INKLINE_EXPECT_FAST: "1"') == 2           # the installed app and the portable one
    mac = job["macos"]
    assert '--target universal2-apple-darwin --install' in mac and "aarch64-apple-darwin,x86_64-apple-darwin" in mac
    assert mac.count('INKLINE_EXPECT_FAST: "1"') == 2                       # the app, and its Intel half under Rosetta
    assert mac.index("Build and install inkline_fast") < mac.index("packaging/macos/build.py --arch")
    assert job["windows"].index("build_fast.py") < job["windows"].index("build.py --stage app")
    assert "selftest.fast_module_status()" in job["flatpak"] and "flatpak-builder --run build-flatpak" in job["flatpak"]
    assert "INKLINE_EXPECT_FAST" not in job["run-and-arch"]                 # the system's Python: no Rust module


# --- the self-test -----------------------------------------------------------------------------------------------

def test_the_self_test_says_whether_the_module_works_and_fails_only_when_expected(tmp_path, monkeypatch):
    from inkapp import selftest
    from inkengine import cbn, photo
    monkeypatch.setitem(__import__("sys").modules, "inkline_fast", None)
    monkeypatch.setattr(photo, "inkline_fast", None)
    monkeypatch.setattr(cbn, "inkline_fast", None)
    found = selftest.check_fast_module(str(tmp_path), env={})
    assert found.startswith("no (") and (tmp_path / "inkline-fast.txt").read_text().startswith("no (")
    with pytest.raises(RuntimeError, match="should ship the Rust module"):
        selftest.check_fast_module(str(tmp_path), env={"INKLINE_EXPECT_FAST": "1"})


def test_the_self_test_finds_a_working_module_when_installed(tmp_path):
    pytest.importorskip("inkline_fast")
    from inkapp import selftest
    found = selftest.check_fast_module(str(tmp_path), env={"INKLINE_EXPECT_FAST": "1"})
    assert found.startswith("yes (")
