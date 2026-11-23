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


def test_every_release_has_all_six_packages():
    wf = _read(".github", "workflows", "release.yml")
    assert "sh packaging/debian/build-deb.sh" in wf and "sh packaging/appimage/build-appimage.sh" in wf
    assert "python packaging/windows/build.py" in wf
    assert "needs: [check, selftest, run-and-arch, flatpak, deb, appimage, windows, windows-check]" in wf
    for name in ("run-and-arch", "flatpak", "deb", "appimage", "windows"):
        assert f"name: {name}\n          path: dist" in wf
    assert 'test "$(ls dist | wc -l)" = 6' in wf
    assert "python3 packaging/check_selftest.py windows-selftest" in wf     # Inkline.exe's output, checked


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
