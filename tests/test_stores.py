"""packaging/stores/make_manifests.py: what each app store needs for a release (docs/publishing.md)."""
import importlib.util
import io
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("make_manifests", os.path.join(ROOT, "packaging", "stores", "make_manifests.py"))
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

V = "6.1.0"
DIGESTS = {f"inkline-{V}-windows-setup.exe": "ab" * 32, f"inkline-{V}-macos.dmg": "cd" * 32}


def test_every_store_gets_its_files(tmp_path):
    files = mm.write_all(str(tmp_path), V, "f" * 40, DIGESTS, "ef" * 32)
    assert files == ["aur/.SRCINFO", "aur/PKGBUILD", "flathub/io.github.gshoe2006.Inkline.yml", "homebrew/inkline.rb",
                     "winget/Gshoe2006.Inkline.installer.yaml", "winget/Gshoe2006.Inkline.locale.en-US.yaml",
                     "winget/Gshoe2006.Inkline.yaml"]
    read = lambda rel: (tmp_path / rel).read_text(encoding="utf-8")
    inst = read("winget/Gshoe2006.Inkline.installer.yaml")
    assert f"InstallerSha256: {'AB' * 32}" in inst and f"/releases/download/{V}/inkline-{V}-windows-setup.exe" in inst
    assert "InstallerType: inno" in inst and "Scope: user" in inst
    assert "License: GPL-3.0-or-later" in read("winget/Gshoe2006.Inkline.locale.en-US.yaml")
    cask = read("homebrew/inkline.rb")
    assert f'version "{V}"' in cask and f'sha256 "{"cd" * 32}"' in cask and "-macos.dmg" in cask
    assert 'depends_on macos: ">= :sonoma"' in cask and 'app "Inkline.app"' in cask
    pkg = read("aur/PKGBUILD")
    assert f"pkgver={V}" in pkg and f"sha256sums=('{'ef' * 32}')" in pkg and "depends=('python' 'pyside6' 'python-numpy')" in pkg
    assert f"sha256sums = {'ef' * 32}" in read("aur/.SRCINFO") and f"pkgver = {V}" in read("aur/.SRCINFO")
    fh = read("flathub/io.github.gshoe2006.Inkline.yml")
    assert f"tag: {V}\n" in fh and f"commit: {'f' * 40}" in fh and "tag: 3.4.2" not in fh


def test_the_checksums_come_from_the_release():
    seen = []

    def opener(req, timeout=30):
        seen.append(req.full_url)
        if "api.github.com" in req.full_url:
            body = json.dumps({"assets": [{"name": n, "digest": f"sha256:{d}"} for n, d in DIGESTS.items()] +
                              [{"name": "x.txt", "digest": None}]}).encode()
        else:
            body = b"tarball bytes"
        return io.BytesIO(body)
    assert mm.release_digests(V, opener=opener) == DIGESTS
    import hashlib
    assert mm.tarball_digest(V, opener=opener) == hashlib.sha256(b"tarball bytes").hexdigest()
    assert seen == [f"https://api.github.com/repos/Gshoe2006/inkline/releases/tags/{V}", mm.tarball_url(V)]


def test_a_release_without_a_digest_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        mm.write_all(str(tmp_path), V, "f" * 40, {}, "ef" * 32)


def test_ci_writes_them_after_each_release():
    flow = open(os.path.join(ROOT, ".github", "workflows", "stores.yml"), encoding="utf-8").read()
    assert "workflows: [Release]" in flow and "make_manifests.py" in flow and "name: store-manifests" in flow
    guide = open(os.path.join(ROOT, "docs", "publishing.md"), encoding="utf-8").read()
    for store in ("Flathub", "winget", "Homebrew", "AUR", "Google Play"):
        assert f"## {store}" in guide
