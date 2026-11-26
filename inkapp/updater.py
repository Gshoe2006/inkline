"""Updates: Inkline asks GitHub for its latest release, says when there's a newer one, and on request downloads
the package for how this copy was installed, checks it against the release's SHA-256 digest, and installs it.

How each copy updates (install_kind):
- windows   (the installer's app; Python frozen by PyInstaller): run the new setup .exe, which closes Inkline.
- appimage  ($APPIMAGE): put the new AppImage in place of this one and start it.
- run-user  (the .run installer, for one person): run the new .run, then start Inkline again.
- run-system, deb, arch (installed for everyone): the same with an administrator password, through pkexec; without
  pkexec, the file is downloaded and its folder opened, with the command to install it.
- flatpak, source: say there's an update, and open the release page.

The packages say how they were installed in an "install-kind" file next to inkline.py. Nothing is sent but the
request itself (GitHub sees an IP address, as for any web page); the check is made at most once a day, and only
if the person said yes to checking when Inkline first asked.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = "Gshoe2006/inkline"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
PAGE = f"https://github.com/{REPO}/releases/latest"
DAY = 24 * 3600
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_KINDS = ("windows", "appimage", "run-user", "run-system", "deb", "arch", "flatpak", "source")
NEEDS_ADMIN = ("run-system", "deb", "arch")


def install_kind(env=None, frozen=None, root=ROOT):
    """How this copy of Inkline was installed (one of INSTALL_KINDS)."""
    env = os.environ if env is None else env
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if frozen and os.name == "nt" or frozen == "windows":
        return "windows"
    if env.get("APPIMAGE"):
        return "appimage"
    if env.get("FLATPAK_ID") or os.path.exists("/.flatpak-info") and root.startswith("/app/"):
        return "flatpak"
    try:
        with open(os.path.join(root, "install-kind"), encoding="utf-8") as f:
            kind = f.read().strip()
        if kind in INSTALL_KINDS:
            return kind
    except OSError:
        pass
    return "source"


def parse_version(text):
    """(5, 4, 0) from "5.4.0" or "v5.4.0"; () for anything else."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)$", (text or "").strip())
    return tuple(int(x) for x in m.groups()) if m else ()


def newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    return bool(a and b and a > b)


def asset_name(kind, version):
    """The release file for a kind of install, or None for those that don't update themselves."""
    return {"windows": f"inkline-{version}-windows-setup.exe", "appimage": f"inkline-{version}-x86_64.AppImage",
            "run-user": f"inkline-{version}.run", "run-system": f"inkline-{version}.run",
            "deb": f"inkline_{version}-1_amd64.deb", "arch": f"inkline-{version}-1-any.pkg.tar.zst"}.get(kind)


def fetch_latest(timeout=10, opener=None):
    """The latest release, from GitHub's API: {version, notes, page, assets: {name: (url, sha256, size)}}.
    Raises OSError (or ValueError for an answer that isn't a release)."""
    req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "Inkline-update-check"})
    with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    version = str(data.get("tag_name", "")).lstrip("v")
    if not parse_version(version):
        raise ValueError("not a release")
    assets = {}
    for a in data.get("assets", []):
        digest = str(a.get("digest") or "")
        assets[a.get("name")] = (a.get("browser_download_url"), digest.split(":", 1)[1] if digest.startswith("sha256:")
                                 else "", int(a.get("size") or 0))
    return {"version": version, "notes": data.get("body") or "", "page": data.get("html_url") or PAGE,
            "assets": assets}


def due(prefs, now=None):
    """Whether to check now: the person agreed, and the last check was a day ago or more."""
    now = time.time() if now is None else now
    return prefs.get("update_check") is True and now - float(prefs.get("update_checked", 0) or 0) >= DAY


def worth_offering(release, current, prefs):
    """Whether to tell the person about a release: newer than this copy, and not a version they chose to skip."""
    return bool(release) and newer(release["version"], current) and prefs.get("update_skip") != release["version"]


def download(url, sha256, dest_dir=None, progress=None, cancelled=None, opener=None, timeout=30):
    """The file at url, saved in dest_dir (a new temporary folder by default), checked against its SHA-256.
    progress(done, total) is called as it comes; cancelled() returning True stops it (None is returned).
    Raises OSError if it can't be fetched or doesn't match."""
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="inkline-update-")
    path = os.path.join(dest_dir, os.path.basename(url.split("?", 1)[0]))
    req = urllib.request.Request(url, headers={"User-Agent": "Inkline-update-check"})
    h = hashlib.sha256()
    with (opener or urllib.request.urlopen)(req, timeout=timeout) as r, open(path, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0) if hasattr(r, "headers") else 0
        done = 0
        while True:
            if cancelled and cancelled():
                f.close()
                os.remove(path)
                return None
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if not sha256:
        os.remove(path)
        raise OSError("the release didn't say what the download should contain (no SHA-256)")
    if h.hexdigest() != sha256.lower():
        os.remove(path)
        raise OSError("the download didn't match the release (its SHA-256 differs); nothing was installed")
    return path


def install_steps(kind, path, env=None):
    """What installing the downloaded file takes: (command to run or None, what to do after: "quit", "restart" or
    "replace"). For an AppImage the file is moved into place instead of run."""
    env = os.environ if env is None else env
    if kind == "windows":
        return [path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], "quit"
    if kind == "appimage":
        return None, "replace"
    if kind == "run-user":
        return ["sh", path], "restart"
    admin = shutil.which("pkexec", path=env.get("PATH"))
    if not admin:
        return None, "manual"
    if kind == "run-system":
        return [admin, "sh", path, "--system"], "restart"
    if kind == "deb":
        apt = shutil.which("apt", path=env.get("PATH")) or "apt"
        return [admin, apt, "install", "-y", path], "restart"
    if kind == "arch":
        pacman = shutil.which("pacman", path=env.get("PATH")) or "pacman"
        return [admin, pacman, "-U", "--noconfirm", path], "restart"
    return None, "manual"


def manual_command(kind, path):
    """The command to type, where Inkline can't install for the person."""
    return {"deb": f"sudo apt install {path}", "arch": f"sudo pacman -U {path}",
            "run-system": f"sudo sh {path} --system"}.get(kind, "")


def replace_appimage(new_path, env=None):
    """Put the downloaded AppImage where this one is ($APPIMAGE), executable; returns that path."""
    env = os.environ if env is None else env
    target = env["APPIMAGE"]
    os.chmod(new_path, 0o755)
    staged = target + ".new"
    shutil.copyfile(new_path, staged)
    os.chmod(staged, 0o755)
    os.replace(staged, target)   # the running copy stays mapped until it exits
    return target


def relaunch_command(kind, env=None):
    """How to start the updated Inkline."""
    env = os.environ if env is None else env
    if kind == "appimage":
        return [env["APPIMAGE"]]
    if kind == "run-user":
        return [os.path.expanduser("~/.local/bin/inkline")]
    if kind == "run-system":
        return ["/usr/local/bin/inkline"]
    return ["inkline"]


def run(cmd):
    """Run an install step and wait for it: (ok, its output)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return p.returncode == 0, (p.stdout + p.stderr).strip()[-2000:]
