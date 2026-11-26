#!/usr/bin/env python3
"""Writes what each app store needs for a released version of Inkline, ready to submit (docs/publishing.md says how):

    python3 packaging/stores/make_manifests.py 6.1.0 --commit <the tag's commit> [--out store-manifests]

- winget (Windows Package Manager): Gshoe2006.Inkline's three manifests, for the Windows installer
- Homebrew: a cask for the universal macOS disk image (for a tap of Inkline's own: homebrew/cask takes only apps
  signed by Apple's Developer ID)
- AUR (Arch User Repository): a PKGBUILD that builds from the release's source tarball, and its .SRCINFO
- Flathub: the Flathub manifest, pinned to the release's tag and commit

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
def winget(version, setup_sha):
    pid, mv = "Gshoe2006.Inkline", "1.6.0"
    head = f"# yaml-language-server: $schema=https://aka.ms/winget-manifest.{{}}.{mv}.schema.json\n\n"
    files = {}
    files[f"{pid}.yaml"] = head.format("version") + (
        f"PackageIdentifier: {pid}\nPackageVersion: {version}\nDefaultLocale: en-US\nManifestType: version\n"
        f"ManifestVersion: {mv}\n")
    files[f"{pid}.installer.yaml"] = head.format("installer") + (
        f"PackageIdentifier: {pid}\nPackageVersion: {version}\nInstallerType: inno\nScope: user\n"
        "InstallModes:\n  - interactive\n  - silent\nUpgradeBehavior: install\n"
        "FileExtensions:\n  - inkline\n"
        "Installers:\n  - Architecture: x64\n"
        f"    InstallerUrl: {download_url(version, f'inkline-{version}-windows-setup.exe')}\n"
        f"    InstallerSha256: {setup_sha.upper()}\n"
        f"ManifestType: installer\nManifestVersion: {mv}\n")
    files[f"{pid}.locale.en-US.yaml"] = head.format("defaultLocale") + (
        f"PackageIdentifier: {pid}\nPackageVersion: {version}\nPackageLocale: en-US\nPublisher: Inkline\n"
        f"PublisherUrl: {HOMEPAGE}\nPackageName: Inkline\nPackageUrl: {HOMEPAGE}\nLicense: GPL-3.0-or-later\n"
        f"LicenseUrl: {HOMEPAGE}/blob/main/LICENSE\nShortDescription: {SUMMARY}\nDescription: {DESCRIPTION}\n"
        "Moniker: inkline\nTags:\n  - colouring\n  - printing\n  - puzzles\n  - worksheets\n  - education\n"
        f"ReleaseNotesUrl: {HOMEPAGE}/releases/tag/{version}\n"
        f"ManifestType: defaultLocale\nManifestVersion: {mv}\n")
    return files


# --- Homebrew ---------------------------------------------------------------------------------------------------
def homebrew(version, dmg_sha):
    return f'''cask "inkline" do
  version "{version}"
  sha256 "{dmg_sha}"

  url "https://github.com/{REPO}/releases/download/#{{version}}/inkline-#{{version}}-macos.dmg"
  name "Inkline"
  desc "{SUMMARY}"
  homepage "{HOMEPAGE}"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: ">= :sonoma"

  app "Inkline.app"

  zap trash: [
    "~/.config/inkline",
    "~/Library/LaunchAgents/io.github.gshoe2006.Inkline.update.plist",
  ]
end
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
def flathub(version, commit, manifest=None):
    """The Flathub manifest with Inkline's source pinned to this release's tag and commit."""
    if manifest is None:
        with open(os.path.join(ROOT, "packaging", "flatpak", "flathub", "io.github.gshoe2006.Inkline.yml"),
                  encoding="utf-8") as f:
            manifest = f.read()
    out, n = re.subn(r"(url: https://github\.com/Gshoe2006/inkline\.git\n\s+tag: )\S+(\n\s+commit: )\S+",
                     lambda m: f"{m.group(1)}{version}{m.group(2)}{commit}", manifest)
    if n != 1:
        raise SystemExit("make_manifests.py: the Flathub manifest's Inkline source (git url, tag, commit) wasn't found")
    return out


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


def write_all(out, version, commit, digests, tarball_sha):
    need = {"setup": f"inkline-{version}-windows-setup.exe", "dmg": f"inkline-{version}-macos.dmg"}
    missing = [n for n in need.values() if n not in digests]
    if missing:
        raise SystemExit(f"make_manifests.py: the release has no SHA-256 digest for {', '.join(missing)}")
    files = {f"winget/{k}": v for k, v in winget(version, digests[need["setup"]]).items()}
    files["homebrew/inkline.rb"] = homebrew(version, digests[need["dmg"]])
    files.update({f"aur/{k}": v for k, v in aur(version, tarball_sha).items()})
    files["flathub/io.github.gshoe2006.Inkline.yml"] = flathub(version, commit)
    for rel, text in files.items():
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return sorted(files)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("version")
    p.add_argument("--commit", help="the tag's commit (default: git rev-list -n 1 <version>)")
    p.add_argument("--out", default="store-manifests")
    a = p.parse_args(argv)
    commit = a.commit or subprocess.run(["git", "rev-list", "-n", "1", a.version], cwd=ROOT, check=True,
                                        capture_output=True, text=True).stdout.strip()
    for rel in write_all(a.out, a.version, commit, release_digests(a.version), tarball_digest(a.version)):
        print(os.path.join(a.out, rel))


if __name__ == "__main__":
    main(sys.argv[1:])
