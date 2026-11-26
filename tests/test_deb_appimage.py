"""The Debian/Ubuntu package and the AppImage: built the same way as the other packages, and released with them."""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


def test_the_deb_carries_the_same_pyside6_as_the_flatpak():
    flatpak = _read("packaging", "flatpak", "io.github.gshoe2006.Inkline.yml")
    deb = _read("packaging", "debian", "build-deb.sh")
    for wheel in ("pyside6_essentials-6.12.0", "shiboken6-6.12.0"):
        url, sha = re.search(rf"url: (\S*{wheel}\S*)\s+sha256: (\w+)", flatpak).groups()
        assert f"{url} {sha}" in deb                    # same file, same checksum: update both together


def test_the_deb_installs_like_the_other_packages():
    deb = _read("packaging", "debian", "build-deb.sh")
    for path in ("usr/share/applications/inkline.desktop", "usr/share/mime/packages/inkline.xml",
                 "usr/share/icons/hicolor/scalable/apps/inkline.svg", "CHANGELOG.md", "usr/bin/inkline"):
        assert path in deb
    assert 'PYTHONPATH="/usr/lib/inkline/vendor' in deb and "python3-numpy" in deb
    assert "DEBIAN/prerm" in deb                         # removes Python's caches, so uninstalling leaves nothing


def test_the_appimage_runs_on_its_own_python_and_declares_its_file_type():
    ai = _read("packaging", "appimage", "build-appimage.sh")
    assert 'exec "$HERE/usr/python/bin/python3" "$HERE/usr/share/inkline/inkline.py" "$@"' in ai
    assert "unset PYTHONPATH PYTHONHOME" in ai and "PYTHONNOUSERSITE=1" in ai
    assert "usr/share/mime/packages/io.github.gshoe2006.Inkline.xml" in ai and "Exec=inkline %f" in ai
    assert "--no-bin" in ai                              # uv leaves the builder's ~/.local/bin alone
    for script in (("debian", "build-deb.sh"), ("appimage", "build-appimage.sh")):
        assert os.access(os.path.join(ROOT, "packaging", *script), os.X_OK)


def test_every_release_has_all_fifteen_packages():
    wf = _read(".github", "workflows", "release.yml")
    assert "sh packaging/debian/build-deb.sh ${{ matrix.arch }}" in wf and "sh packaging/appimage/build-appimage.sh" in wf
    assert "sh packaging/rpm/build-rpm.sh" in wf and "snapcore/action-build@v1" in wf
    assert "python packaging/windows/build.py" in wf and '"$PY" packaging/macos/build.py --arch ${{ matrix.arch }}' in wf
    needs = ("needs: [check, selftest, run-and-arch, flatpak, deb, appimage, rpm, rpm-opensuse, snap, windows, "
             "windows-check, macos, macos-check]")
    assert wf.count(needs) == 2                                              # the release, and a test build's summary
    for name in ("run-and-arch", "flatpak", "deb-${{ matrix.arch }}", "appimage-${{ matrix.arch }}", "rpm",
                 "snap-${{ matrix.arch }}", "windows", "macos-${{ matrix.arch }}"):
        assert f"name: pkg-{name}\n" in wf, name                           # each kept for the release (pkg-*)
    for arch, runner in (("arm64", "ubuntu-24.04-arm"), ("aarch64", "ubuntu-24.04-arm"), ("intel", "macos-15-intel"),
                         ("universal", "macos-15"), ("arm64", "macos-15")):
        assert f"{{ arch: {arch}, runner: {runner} }}" in wf, (arch, runner)
    assert "pattern: pkg-*" in wf and 'test "$(ls dist | wc -l)" = 15' in wf
    assert 'check_selftest.py "selftest/macos-$d" --install-kind macos' in wf and "arm64 intel universal rosetta" in wf
    assert "check_selftest.py windows-selftest/portable --install-kind windows-portable" in wf
    assert "check_selftest.py rpm-selftest --install-kind rpm" in wf and "container: opensuse/tumbleweed" in wf
    assert '--install-kind snap' in wf


def test_the_windows_installer_registers_the_app_and_its_file_type():
    import importlib.util
    iss = _read("packaging", "windows", "inkline.iss")
    assert "OutputBaseFilename=inkline-{#VERSION}-windows-setup" in iss and "ChangesAssociations=yes" in iss
    assert 'Subkey: "Software\\Classes\\.inkline"' in iss and '""{app}\\Inkline.exe"" ""%1""' in iss
    assert "PrivilegesRequired=lowest" in iss                                # no administrator needed
    spec = importlib.util.spec_from_file_location("win_build", os.path.join(ROOT, "packaging", "windows", "build.py"))
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    import struct
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "i.ico")
    build.make_ico(out)
    with open(out, "rb") as f:
        reserved, kind, count = struct.unpack("<HHH", f.read(6))
    assert (reserved, kind) == (0, 1) and count >= 5                         # a real icon with several sizes
