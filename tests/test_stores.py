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


def _flatpak_manifest():
    with open(mm.FLATPAK_MANIFEST, encoding="utf-8") as f:
        return f.read()


def test_the_winget_manifests_are_valid_yaml_with_both_scopes():
    yaml = pytest.importorskip("yaml")
    files = {k: yaml.safe_load(v) for k, v in mm.winget(V, "ab" * 32).items()}
    loc = files["Gshoe2006.Inkline.locale.en-US.yaml"]
    assert loc["Description"] == mm.DESCRIPTION and loc["ShortDescription"] == mm.SUMMARY   # ": " needs quoting
    assert len(loc["ShortDescription"]) <= 256 and loc["License"] == "GPL-3.0-or-later"
    inst = files["Gshoe2006.Inkline.installer.yaml"]
    for f in files.values():
        assert f["PackageIdentifier"] == "Gshoe2006.Inkline" and f["PackageVersion"] == V
        assert f["ManifestVersion"] == mm.WINGET_SCHEMA
    assert inst["InstallerType"] == "inno" and inst["UpgradeBehavior"] == "install"
    assert [(i["Scope"], i["InstallerSwitches"]["Custom"]) for i in inst["Installers"]] == \
        [("user", "/CURRENTUSER"), ("machine", "/ALLUSERS")]
    assert {i["InstallerSha256"] for i in inst["Installers"]} == {"AB" * 32}
    # winget finds an Inkline installed without it by Inno Setup's uninstall key, made from the installer's AppId
    iss = open(os.path.join(ROOT, "packaging", "windows", "inkline.iss"), encoding="utf-8").read()
    app_id = iss.split("AppId={", 1)[1].split("\n", 1)[0]
    assert inst["ProductCode"] == f"{app_id}_is1" == "{6F1B7F0A-3C2E-4E9B-9C55-1D2B7A4E8C31}_is1"
    assert "PrivilegesRequiredOverridesAllowed=commandline dialog" in iss   # /ALLUSERS and /CURRENTUSER work


def test_the_cask_passes_brews_rules():
    cask = mm.homebrew(V, "cd" * 32)
    desc = cask.split('desc "', 1)[1].split('"', 1)[0]
    assert len(desc) <= 80 and not desc.endswith(".") and not desc.lower().startswith(("inkline", "a ", "an "))
    assert 'depends_on macos: ">= :sonoma"' in cask
    assert 'uninstall launchctl: "io.github.gshoe2006.Inkline.update"' in cask
    assert '"~/.config/inkline",' in cask and "Saved Application State/io.github.gshoe2006.Inkline.savedState" in cask
    assert "caveats <<~EOS" in cask and "Open Anyway" in cask and "  EOS\nend\n" in cask   # unsigned: how to open it
    signed = mm.homebrew(V, "cd" * 32, notarized=True)
    assert "caveats" not in signed and signed.endswith("  ]\nend\n")


def test_the_flathub_manifest_is_the_flatpak_one_pinned_to_the_release():
    yaml = pytest.importorskip("yaml")
    out = mm.flathub(V, "f" * 40)
    fh, local = yaml.safe_load(out), yaml.safe_load(_flatpak_manifest())
    assert "type: dir" not in out and out.startswith("# Inkline for Flathub")
    assert fh["modules"][-1]["sources"][0] == {"type": "git", "url": "https://github.com/Gshoe2006/inkline.git",
                                                "tag": V, "commit": "f" * 40}
    # after Inkline's own source, the Rust crates for inkline_fast, as in the local manifest
    assert fh["modules"][-1]["sources"][1:] == local["modules"][-1]["sources"][1:]
    assert all(x["type"] in ("archive", "inline") for x in fh["modules"][-1]["sources"][1:])
    for key in ("id", "runtime", "runtime-version", "sdk", "command", "finish-args"):
        assert fh[key] == local[key], key
    assert "--share=network" not in fh["finish-args"] and "--filesystem=host" not in fh["finish-args"]
    assert len(fh["modules"]) == len(local["modules"])
    for a, b in zip(fh["modules"], local["modules"]):
        assert a["build-commands"] == b["build-commands"]                # never drifts from what the release tests
    assert fh["modules"][0]["sources"] == local["modules"][0]["sources"]
    with pytest.raises(SystemExit):
        mm.flathub("6.1", "f" * 40)
    with pytest.raises(SystemExit):
        mm.flathub(V, "main")
    with pytest.raises(SystemExit):
        mm.flathub(V, "f" * 40, manifest="id: x\nmodules: []\n")


def test_flathub_gets_wheels_for_both_its_processors_and_builds_offline():
    yaml = pytest.importorskip("yaml")
    deps = yaml.safe_load(_flatpak_manifest())["modules"][0]
    assert all("--no-index" in c for c in deps["build-commands"] if "pip" in c)
    by_arch = {}
    for s in deps["sources"]:
        assert s["type"] == "file" and len(s["sha256"]) == 64 and s["url"].startswith("https://files.pythonhosted.org/")
        (arch,) = s["only-arches"]
        assert arch in s["url"]
        by_arch.setdefault(arch, set()).add(os.path.basename(s["url"]).split("-")[0])
    assert by_arch == {a: {"pyside6_essentials", "shiboken6", "numpy"} for a in ("x86_64", "aarch64")}


def test_the_metainfo_has_what_flathub_checks():
    meta = open(os.path.join(ROOT, "packaging", "flatpak", "io.github.gshoe2006.Inkline.metainfo.xml"),
                encoding="utf-8").read()
    summary = meta.split("<summary>", 1)[1].split("</summary>", 1)[0]
    assert len(summary) <= 35 and not summary.endswith(".")
    for need in ('<developer id="io.github.gshoe2006">',
                 '<launchable type="desktop-id">io.github.gshoe2006.Inkline.desktop</launchable>',
                 '<content_rating type="oars-1.1"', '<color type="primary" scheme_preference="light">',
                 '<color type="primary" scheme_preference="dark">', '<screenshot type="default">', "<caption>",
                 "<image>https://", "<metadata_license>CC0-1.0</metadata_license>", '<url type="homepage">'):
        assert need in meta, need


def test_the_flathub_manifest_can_be_written_without_the_network(tmp_path):
    mm.main([V, "--commit", "e" * 40, "--flathub-only", "--out", str(tmp_path)])
    assert sorted(os.listdir(tmp_path)) == ["flathub"]
    assert f"commit: {'e' * 40}" in (tmp_path / mm.FLATHUB_FILE).read_text(encoding="utf-8")


def test_the_tap_is_updated_only_with_a_token():
    flow = open(os.path.join(ROOT, ".github", "workflows", "stores.yml"), encoding="utf-8").read()
    assert "HAVE_TAP_TOKEN: ${{ secrets.TAP_TOKEN != '' }}" in flow and "No TAP_TOKEN secret" in flow
    assert flow.count("if: env.HAVE_TAP_TOKEN == 'true'") == 3 and "token: ${{ secrets.TAP_TOKEN }}" in flow
    assert "Gshoe2006/homebrew-inkline" in flow and "Casks/inkline.rb" in flow and "--macos-notarized" in flow


def test_each_store_has_its_steps():
    guide = open(os.path.join(ROOT, "docs", "publishing.md"), encoding="utf-8").read()
    read = lambda store: open(os.path.join(ROOT, "packaging", "stores", store, "README.md"), encoding="utf-8").read()
    for store in ("flathub", "winget", "homebrew", "aur"):
        assert f"packaging/stores/{store}/README.md" in guide and read(store), store
    assert "new-pr" in read("flathub") and "manifests/g/Gshoe2006/Inkline/" in read("winget")
    assert "git clone ssh://aur@aur.archlinux.org/inkline.git" in read("aur") and ".SRCINFO" in read("aur")
    assert "TAP_TOKEN" in read("homebrew")
