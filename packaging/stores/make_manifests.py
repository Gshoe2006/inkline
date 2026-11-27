#!/usr/bin/env python3
"""Writes what each app store needs for a released version of Inkline, ready to submit (docs/publishing.md says how):

    python3 packaging/stores/make_manifests.py 6.1.0 --commit <the tag's commit> [--out store-manifests]

- winget (Windows Package Manager): Gshoe2006.Inkline's three manifests, for the Windows installer
- Homebrew: a cask for the universal macOS disk image (for a tap of Inkline's own: homebrew/cask takes only apps
  signed by Apple's Developer ID)
- AUR (Arch User Repository): a PKGBUILD that builds from the release's source tarball, and its .SRCINFO
- Flathub: the Flathub manifest, made from packaging/flatpak's own, pinned to the release's tag and commit

Each store's README in packaging/stores/ says how to submit what's written here.

The checksums come from the release itself: each file's SHA-256 digest from GitHub's API, and the source tarball's
by downloading it. Nothing is uploaded anywhere. The CI runs this after each release (stores.yml) and keeps the
files as the run's "store-manifests" download.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

REPO = "Gshoe2006/inkline"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AGENT = {"User-Agent": "Inkline-store-manifests"}
SUMMARY = "Colouring pages, puzzles and black & white photo prints, ready to print at true paper size"
DESCRIPTION = ("Inkline makes colouring pages, puzzles and black and white photo prints, ready to print at true paper "
               "size: mandalas, mazes, dot-to-dots, sudoku, word searches, crosswords, worksheets and name pages; "
               "dithered, halftone, engraved and stippled photos; booklets, photo books and posters. Print, or save as "
               "PDF, PNG or SVG.")
HOMEPAGE = f"https://github.com/{REPO}"


def download_url(version, name):
    return f"https://github.com/{REPO}/releases/download/{version}/{name}"


def tarball_url(version):
    return f"https://github.com/{REPO}/archive/refs/tags/{version}.tar.gz"


# --- winget ---------------------------------------------------------------------------------------------------
WINGET_ID = "Gshoe2006.Inkline"
WINGET_SCHEMA = "1.6.0"
# Inno Setup's uninstall key for the installer's AppId (packaging/windows/inkline.iss): how winget sees it's installed
INNO_PRODUCT_CODE = "{6F1B7F0A-3C2E-4E9B-9C55-1D2B7A4E8C31}_is1"


def yq(text):
    """A YAML double-quoted string (JSON's quoting is valid YAML): a plain one can't hold ": " or start with "{"."""
    return json.dumps(text, ensure_ascii=False)


def winget(version, setup_sha):
    pid, mv = WINGET_ID, WINGET_SCHEMA
    head = f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.{{}}.{mv}.schema.json\n\n"
    url = download_url(version, f"inkline-{version}-windows-setup.exe")
    files = {}
    files[f"{pid}.yaml"] = head.format("version") + (
        f"PackageIdentifier: {pid}\nPackageVersion: {version}\nDefaultLocale: en-US\nManifestType: version\n"
        f"ManifestVersion: {mv}\n")
    # the one installer, for one person (as it installs by default) or, with /ALLUSERS, for everyone (as an admin)
    installers = "".join(
        f"  - Architecture: x64\n    Scope: {scope}\n    InstallerUrl: {url}\n    InstallerSha256: {setup_sha.upper()}\n"
        f"    InstallerSwitches:\n      Custom: {switch}\n"
        for scope, switch in (("user", "/CURRENTUSER"), ("machine", "/ALLUSERS")))
    files[f"{pid}.installer.yaml"] = head.format("installer") + (
        f"PackageIdentifier: {pid}\nPackageVersion: {version}\nInstallerType: inno\n"
        "InstallModes:\n  - interactive\n  - silent\n  - silentWithProgress\nUpgradeBehavior: install\n"
        f"ProductCode: {yq(INNO_PRODUCT_CODE)}\n"
        "FileExtensions:\n  - inkline\n"
        f"Installers:\n{installers}"
        f"ManifestType: installer\nManifestVersion: {mv}\n")
    files[f"{pid}.locale.en-US.yaml"] = head.format("defaultLocale") + (
        f"PackageIdentifier: {pid}\nPackageVersion: {version}\nPackageLocale: en-US\nPublisher: Inkline\n"
        f"PublisherUrl: {HOMEPAGE}\nPublisherSupportUrl: {HOMEPAGE}/issues\nPackageName: Inkline\n"
        f"PackageUrl: {HOMEPAGE}\nLicense: GPL-3.0-or-later\nLicenseUrl: {HOMEPAGE}/blob/main/LICENSE\n"
        f"ShortDescription: {yq(SUMMARY)}\nDescription: {yq(DESCRIPTION)}\n"
        "Moniker: inkline\nTags:\n  - colouring\n  - printing\n  - puzzles\n  - worksheets\n  - education\n"
        f"ReleaseNotesUrl: {HOMEPAGE}/releases/tag/{version}\n"
        f"ManifestType: defaultLocale\nManifestVersion: {mv}\n")
    return files


# --- Homebrew ---------------------------------------------------------------------------------------------------
CASK_DESC = "Make colouring pages, puzzles and black-and-white photo prints"   # brew audit: 80 characters at most
BUNDLE_ID = "io.github.gshoe2006.Inkline"


UNSIGNED_CAVEAT = '''
  caveats <<~EOS
    Until Inkline is signed with an Apple Developer ID and notarized, macOS asks before
    opening it the first time: Control-click Inkline in Applications and choose Open, or
    use System Settings > Privacy & Security > Open Anyway.
  EOS
'''


def homebrew(version, dmg_sha, notarized=False):
    """The cask. Until the disk image is notarized (docs/code-signing.md) it says how to open the app the first time."""
    caveat = "" if notarized else UNSIGNED_CAVEAT
    return f'''cask "inkline" do
  version "{version}"
  sha256 "{dmg_sha}"

  url "https://github.com/{REPO}/releases/download/#{{version}}/inkline-#{{version}}-macos.dmg"
  name "Inkline"
  desc "{CASK_DESC}"
  homepage "{HOMEPAGE}"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: ">= :sonoma"

  app "Inkline.app"

  # the update check Inkline sets up when asked to check while it's closed (Help > Check for updates)
  uninstall launchctl: "{BUNDLE_ID}.update"

  zap trash: [
    "~/.config/inkline",
    "~/Library/LaunchAgents/{BUNDLE_ID}.update.plist",
    "~/Library/Preferences/{BUNDLE_ID}.plist",
    "~/Library/Saved Application State/{BUNDLE_ID}.savedState",
  ]
{caveat}end
'''


# --- AUR --------------------------------------------------------------------------------------------------------
def aur(version, tarball_sha):
    pkgbuild = f'''# Maintainer: Inkline <https://github.com/{REPO}>
pkgname=inkline
pkgver={version}
pkgrel=1
pkgdesc="{SUMMARY}"
arch=('any')
url="{HOMEPAGE}"
license=('GPL-3.0-or-later')
depends=('python' 'pyside6' 'python-numpy')
optdepends=('cups: printing to local and network printers')
source=("$pkgname-$pkgver.tar.gz::{HOMEPAGE}/archive/refs/tags/$pkgver.tar.gz")
sha256sums=('{tarball_sha}')

package() {{
  cd "$srcdir/$pkgname-$pkgver"
  for f in $(find inkengine inkapp -name '*.py' -o -name '*.json' -o -name '*.ttf' -o -name 'OFL*.txt' | grep -v __pycache__); do
    install -Dm644 "$f" "$pkgdir/usr/share/inkline/$f"
  done
  install -Dm755 inkline.py      "$pkgdir/usr/share/inkline/inkline.py"
  install -Dm644 inkline.svg     "$pkgdir/usr/share/inkline/inkline.svg"
  install -Dm644 VERSION         "$pkgdir/usr/share/inkline/VERSION"
  install -Dm644 CHANGELOG.md    "$pkgdir/usr/share/inkline/CHANGELOG.md"
  echo arch | install -Dm644 /dev/stdin "$pkgdir/usr/share/inkline/install-kind"
  install -Dm644 LICENSE         "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 inkline.svg     "$pkgdir/usr/share/icons/hicolor/scalable/apps/inkline.svg"
  install -Dm644 inkline.desktop "$pkgdir/usr/share/applications/inkline.desktop"
  install -Dm644 inkline-mime.xml "$pkgdir/usr/share/mime/packages/inkline.xml"
  install -Dm644 icons/hicolor/scalable/mimetypes/application-x-inkline-project.svg \\
    "$pkgdir/usr/share/icons/hicolor/scalable/mimetypes/application-x-inkline-project.svg"
  for png in icons/hicolor/*/apps/inkline.png; do
    install -Dm644 "$png" "$pkgdir/usr/share/${{png#icons/}}"
  done
  install -dm755 "$pkgdir/usr/bin"
  printf '#!/bin/sh\\nexec python3 /usr/share/inkline/inkline.py "$@"\\n' > "$pkgdir/usr/bin/inkline"
  chmod 755 "$pkgdir/usr/bin/inkline"
}}
'''
    srcinfo = f'''pkgbase = inkline
\tpkgdesc = {SUMMARY}
\tpkgver = {version}
\tpkgrel = 1
\turl = {HOMEPAGE}
\tarch = any
\tlicense = GPL-3.0-or-later
\tdepends = python
\tdepends = pyside6
\tdepends = python-numpy
\toptdepends = cups: printing to local and network printers
\tsource = inkline-{version}.tar.gz::{HOMEPAGE}/archive/refs/tags/{version}.tar.gz
\tsha256sums = {tarball_sha}

pkgname = inkline
'''
    return {"PKGBUILD": pkgbuild, ".SRCINFO": srcinfo}


# --- Flathub ----------------------------------------------------------------------------------------------------
FLATPAK_MANIFEST = os.path.join(ROOT, "packaging", "flatpak", "io.github.gshoe2006.Inkline.yml")
FLATHUB_HEAD = """# Inkline for Flathub (https://github.com/flathub/flathub), written by packaging/stores/make_manifests.py from
# packaging/flatpak/io.github.gshoe2006.Inkline.yml: the same build, with Inkline's source taken from GitHub at the
# release's tag, pinned to its commit. PySide6 and numpy are PyPI's wheels, pinned by sha256, so nothing is
# downloaded while it builds. packaging/stores/flathub/README.md says how to submit it.
"""


def flathub(version, commit, manifest=None):
    """The Flathub manifest: the local Flatpak manifest (so the two never drift apart), with Inkline's source
    (there the repository folder) replaced by its git repository at this release's tag and commit."""
    if manifest is None:
        with open(FLATPAK_MANIFEST, encoding="utf-8") as f:
            manifest = f.read()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SystemExit(f"make_manifests.py: '{version}' / '{commit}' isn't a release tag and its full commit hash")
    body = manifest[manifest.index("\nid: ") + 1:] if "\nid: " in manifest else manifest
    source = (f"      - type: git\n        url: https://github.com/{REPO}.git\n"
              f"        tag: {version}\n        commit: {commit}\n")
    out, n = re.subn(r"      - type: dir\n        path: \.\./\.\.\n(?:        .*\n)*", lambda m: source,
                     body)
    if n != 1:
        raise SystemExit("make_manifests.py: the Flatpak manifest's own source (type: dir, path: ../..) wasn't found")
    return FLATHUB_HEAD + out


# --- the release's checksums -------------------------------------------------------------------------------------
def release_digests(version, opener=urllib.request.urlopen):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/tags/{version}",
                                 headers={**AGENT, "Accept": "application/vnd.github+json"})
    with opener(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = {}
    for a in data.get("assets", []):
        d = str(a.get("digest") or "")
        if d.startswith("sha256:"):
            out[a["name"]] = d.split(":", 1)[1]
    return out


def tarball_digest(version, opener=urllib.request.urlopen):
    h = hashlib.sha256()
    with opener(urllib.request.Request(tarball_url(version), headers=AGENT), timeout=120) as r:
        for chunk in iter(lambda: r.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(out, files):
    for rel, text in files.items():
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return sorted(files)


FLATHUB_FILE = "flathub/io.github.gshoe2006.Inkline.yml"


def write_all(out, version, commit, digests, tarball_sha, macos_notarized=False):
    need = {"setup": f"inkline-{version}-windows-setup.exe", "dmg": f"inkline-{version}-macos.dmg"}
    missing = [n for n in need.values() if n not in digests]
    if missing:
        raise SystemExit(f"make_manifests.py: the release has no SHA-256 digest for {', '.join(missing)}")
    files = {f"winget/{k}": v for k, v in winget(version, digests[need["setup"]]).items()}
    files["homebrew/inkline.rb"] = homebrew(version, digests[need["dmg"]], notarized=macos_notarized)
    files.update({f"aur/{k}": v for k, v in aur(version, tarball_sha).items()})
    files[FLATHUB_FILE] = flathub(version, commit)
    return _write(out, files)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("version")
    p.add_argument("--commit", help="the tag's commit (default: git rev-list -n 1 <version>)")
    p.add_argument("--out", default="store-manifests")
    p.add_argument("--flathub-only", action="store_true",
                   help="only the Flathub manifest (needs no network: for checking it with flatpak-builder-lint)")
    p.add_argument("--macos-notarized", action="store_true",
                   help="the macOS disk image is notarized: the cask needn't say how to open an unsigned app")
    a = p.parse_args(argv)
    commit = a.commit or subprocess.run(["git", "rev-list", "-n", "1", a.version], cwd=ROOT, check=True,
                                        capture_output=True, text=True).stdout.strip()
    if a.flathub_only:
        written = _write(a.out, {FLATHUB_FILE: flathub(a.version, commit)})
    else:
        written = write_all(a.out, a.version, commit, release_digests(a.version), tarball_digest(a.version),
                            macos_notarized=a.macos_notarized)
    for rel in written:
        print(os.path.join(a.out, rel))


if __name__ == "__main__":
    main(sys.argv[1:])
