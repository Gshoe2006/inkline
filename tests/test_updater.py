"""Updates: finding a newer release on GitHub, downloading it checked against its SHA-256, and installing it the
way this copy was installed. No test reaches the network: GitHub's answers and the downloads are made up here."""

import hashlib
import io
import json
import os

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from inkapp import config, update_ui, updater

PAYLOAD = b"new inkline " * 50000   # about 600 KB: a few chunks


class Answer(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def release_json(tag="v9.1.0", digest=True):
    sha = hashlib.sha256(PAYLOAD).hexdigest()
    names = [updater.asset_name(k, tag.lstrip("v")) for k in ("windows", "appimage", "run-user", "deb", "arch")]
    return {"tag_name": tag, "body": "Notes", "html_url": "https://example.invalid/r",
            "assets": [{"name": n, "browser_download_url": f"https://example.invalid/{n}", "size": len(PAYLOAD),
                        "digest": f"sha256:{sha}" if digest else None} for n in names]}


def opener_for(data, headers=None, seen=None):
    def opener(req, timeout=None):
        if seen is not None:
            seen.append(req)
        return Answer(data, headers)
    return opener


# --- how this copy was installed ---------------------------------------------------------------------------
def test_install_kind(tmp_path):
    assert updater.install_kind(env={}, frozen="windows", root=str(tmp_path)) == "windows"
    assert updater.install_kind(env={"APPIMAGE": "/x/Inkline.AppImage"}, frozen=False, root=str(tmp_path)) == "appimage"
    assert updater.install_kind(env={"FLATPAK_ID": "io.github.gshoe2006.Inkline"}, frozen=False,
                                root=str(tmp_path)) == "flatpak"
    assert updater.install_kind(env={}, frozen=False, root=str(tmp_path)) == "source"
    for kind in ("deb", "arch", "run-user", "run-system"):
        (tmp_path / "install-kind").write_text(kind + "\n")
        assert updater.install_kind(env={}, frozen=False, root=str(tmp_path)) == kind
    (tmp_path / "install-kind").write_text("something else")
    assert updater.install_kind(env={}, frozen=False, root=str(tmp_path)) == "source"


def test_the_packages_say_how_they_were_installed():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    read = lambda p: open(os.path.join(root, p), encoding="utf-8").read()
    assert 'echo deb > "$APP/install-kind"' in read("packaging/debian/build-deb.sh")
    assert "echo arch" in read("packaging/arch/PKGBUILD") and "install-kind" in read("packaging/arch/PKGBUILD")
    assert 'echo "run-$MODE" > "$APP/install-kind"' in read("packaging/installer-stub.sh")
    assert not os.path.exists(os.path.join(root, "install-kind"))   # a source checkout stays "source"


# --- versions and releases -----------------------------------------------------------------------------------
def test_versions():
    assert updater.parse_version("v5.4.0") == (5, 4, 0) == updater.parse_version("5.4.0")
    assert updater.parse_version("dev") == () == updater.parse_version("5.4") == updater.parse_version(None)
    assert updater.newer("5.10.0", "5.9.3") and not updater.newer("5.5.0", "5.5.0")
    assert not updater.newer("5.4.0", "5.5.0") and not updater.newer("6.0.0", "dev")


def test_asset_names_match_the_release_workflow():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    flow = open(os.path.join(root, ".github/workflows/release.yml"), encoding="utf-8").read()
    v = "${{ needs.check.outputs.version }}"
    for kind in ("windows", "appimage", "deb"):
        assert updater.asset_name(kind, v) in flow, kind
    assert updater.asset_name("run-user", "1.2.3") == updater.asset_name("run-system", "1.2.3") == "inkline-1.2.3.run"
    assert updater.asset_name("arch", "1.2.3") == "inkline-1.2.3-1-any.pkg.tar.zst"
    assert updater.asset_name("flatpak", "1.2.3") is None and updater.asset_name("source", "1.2.3") is None


def test_fetch_latest_reads_the_release():
    seen = []
    rel = updater.fetch_latest(opener=opener_for(json.dumps(release_json()).encode(), seen=seen))
    assert rel["version"] == "9.1.0" and rel["notes"] == "Notes" and rel["page"] == "https://example.invalid/r"
    url, sha, size = rel["assets"]["inkline_9.1.0-1_amd64.deb"]
    assert url.endswith(".deb") and sha == hashlib.sha256(PAYLOAD).hexdigest() and size == len(PAYLOAD)
    assert seen[0].full_url == updater.API
    assert seen[0].get_header("User-agent") == "Inkline-update-check"   # nothing about the person
    assert updater.fetch_latest(opener=opener_for(json.dumps(release_json(digest=False)).encode())
                                )["assets"]["inkline-9.1.0.run"][1] == ""
    with pytest.raises(ValueError):
        updater.fetch_latest(opener=opener_for(json.dumps({"message": "Not Found"}).encode()))


def test_https_trusts_the_system_bundle_when_python_knows_none(tmp_path, monkeypatch):
    import ssl
    real = ssl.create_default_context
    empty = lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)   # verifies, but trusts no one yet
    monkeypatch.setattr(ssl, "create_default_context", empty)
    found = [p for p in updater.CA_BUNDLES if os.path.exists(p)]
    if not found:
        pytest.skip("no system certificate bundle here")
    ctx = updater.tls_context(bundles=[str(tmp_path / "missing.pem"), found[0]])
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.cert_store_stats()["x509_ca"] > 0
    monkeypatch.setattr(ssl, "create_default_context", real)
    assert updater.tls_context().verify_mode == ssl.CERT_REQUIRED


def test_due_and_worth_offering():
    now = 1_000_000.0
    assert not updater.due({}, now)                                    # the person hasn't said yes
    assert not updater.due({"update_check": False}, now)
    assert updater.due({"update_check": True}, now)
    assert not updater.due({"update_check": True, "update_checked": now - 3600}, now)
    assert updater.due({"update_check": True, "update_checked": now - updater.DAY}, now)
    rel = {"version": "9.1.0"}
    assert updater.worth_offering(rel, "5.5.0", {})
    assert not updater.worth_offering(rel, "9.1.0", {}) and not updater.worth_offering(None, "5.5.0", {})
    assert not updater.worth_offering(rel, "5.5.0", {"update_skip": "9.1.0"})
    assert updater.worth_offering({"version": "9.2.0"}, "5.5.0", {"update_skip": "9.1.0"})


# --- downloading ---------------------------------------------------------------------------------------------
def test_download_checks_the_sha256(tmp_path):
    sha = hashlib.sha256(PAYLOAD).hexdigest()
    steps = []
    path = updater.download("https://example.invalid/inkline-9.1.0.run?x=1", sha, dest_dir=str(tmp_path),
                            progress=lambda a, b: steps.append((a, b)),
                            opener=opener_for(PAYLOAD, {"Content-Length": str(len(PAYLOAD))}))
    assert path == str(tmp_path / "inkline-9.1.0.run") and open(path, "rb").read() == PAYLOAD
    assert steps[-1] == (len(PAYLOAD), len(PAYLOAD)) and len(steps) > 1

    with pytest.raises(OSError, match="SHA-256"):
        updater.download("https://example.invalid/bad.run", "0" * 64, dest_dir=str(tmp_path),
                         opener=opener_for(PAYLOAD))
    assert not (tmp_path / "bad.run").exists()          # a file that doesn't match isn't left to be run
    with pytest.raises(OSError, match="SHA-256"):
        updater.download("https://example.invalid/none.run", "", dest_dir=str(tmp_path), opener=opener_for(PAYLOAD))
    assert not (tmp_path / "none.run").exists()


def test_download_can_be_cancelled(tmp_path):
    calls = []
    out = updater.download("https://example.invalid/c.run", hashlib.sha256(PAYLOAD).hexdigest(),
                           dest_dir=str(tmp_path), opener=opener_for(PAYLOAD),
                           progress=lambda a, b: calls.append(a), cancelled=lambda: len(calls) >= 1)
    assert out is None and not (tmp_path / "c.run").exists()


# --- installing ----------------------------------------------------------------------------------------------
def fake_path(tmp_path, *tools):
    for t in tools:
        p = tmp_path / t
        p.write_text("#!/bin/sh\n")
        p.chmod(0o755)
    return {"PATH": str(tmp_path)}


def test_install_steps(tmp_path):
    env = fake_path(tmp_path, "pkexec", "apt", "pacman")
    pk = str(tmp_path / "pkexec")
    assert updater.install_steps("windows", "C:/s.exe", env) == (["C:/s.exe", "/SILENT", "/SUPPRESSMSGBOXES",
                                                                  "/NORESTART"], "quit")
    assert updater.install_steps("appimage", "/t/a", env) == (None, "replace")
    assert updater.install_steps("run-user", "/t/i.run", env) == (["sh", "/t/i.run"], "restart")
    assert updater.install_steps("run-system", "/t/i.run", env) == ([pk, "sh", "/t/i.run", "--system"], "restart")
    assert updater.install_steps("deb", "/t/i.deb", env) == ([pk, str(tmp_path / "apt"), "install", "-y", "/t/i.deb"],
                                                             "restart")
    assert updater.install_steps("arch", "/t/i.zst", env)[0] == [pk, str(tmp_path / "pacman"), "-U", "--noconfirm",
                                                                "/t/i.zst"]
    empty = tmp_path / "empty"
    empty.mkdir()
    for kind in ("run-system", "deb", "arch"):   # no pkexec: the person runs the command
        assert updater.install_steps(kind, "/t/f", {"PATH": str(empty)}) == (None, "manual")
        assert updater.manual_command(kind, "/t/f").startswith("sudo ")
    assert updater.install_steps("run-user", "/t/i.run", {"PATH": str(empty)})[1] == "restart"   # needs no admin


def test_replace_appimage(tmp_path):
    old, new = tmp_path / "Inkline.AppImage", tmp_path / "dl" / "inkline-9.1.0-x86_64.AppImage"
    old.write_bytes(b"old")
    new.parent.mkdir()
    new.write_bytes(b"new")
    env = {"APPIMAGE": str(old)}
    assert updater.replace_appimage(str(new), env) == str(old)
    assert old.read_bytes() == b"new" and os.access(old, os.X_OK) and not (tmp_path / "Inkline.AppImage.new").exists()
    assert updater.relaunch_command("appimage", env) == [str(old)]


def test_run_reports_failure():
    assert updater.run(["sh", "-c", "echo hi"]) == (True, "hi")
    ok, out = updater.run(["sh", "-c", "echo nope >&2; exit 3"])
    assert not ok and out == "nope"
    assert updater.run(["/no/such/program"])[0] is False


# --- the window ----------------------------------------------------------------------------------------------
@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("5.5.0", remember=True)
    w.updates.kind = "deb"
    return w


def wait_for(cond, timeout=5.0):
    import time
    end = time.time() + timeout
    while time.time() < end and not cond():
        QApplication.processEvents()
        time.sleep(0.01)
    return cond()


def boxes(monkeypatch, pick):
    """Answer each question box with the button whose text pick(texts) gives; returns the texts each showed."""
    shown = []

    def exec_(box):
        texts = [b.text() for b in box.buttons()]
        shown.append((box.text(), texts))
        want = pick(texts)
        for b in box.buttons():
            if b.text() == want:
                box._clicked = b
        return 0
    monkeypatch.setattr(QMessageBox, "exec", exec_)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: getattr(box, "_clicked", None))
    return shown


def test_help_menu_has_the_update_items(win):
    texts = [a.text() for m in win.menuBar().actions() for a in m.menu().actions()]
    assert "Check for &updates…" in texts and "Check for updates au&tomatically" in texts
    assert not win.act_updates_auto.isChecked()
    win.act_updates_auto.trigger()
    assert config.read("preferences.json")["update_check"] is True


def test_first_start_asks_once(win, monkeypatch):
    checks = []
    monkeypatch.setattr(win.updates, "check", lambda asked=True: checks.append(asked))
    shown = boxes(monkeypatch, lambda texts: "Check for updates")
    win.updates.at_start()
    assert len(shown) == 1 and config.read("preferences.json")["update_check"] is True
    assert win.act_updates_auto.isChecked() and checks == [False]   # yes: the first check straight away
    config.write("preferences.json", {**config.read("preferences.json"), "update_checked": __import__("time").time()},
                 "Preferences")
    win.updates.at_start()
    assert len(shown) == 1 and checks == [False]                    # not asked again, and not due for a day


def test_saying_no_means_no_checks(win, monkeypatch):
    checks = []
    monkeypatch.setattr(win.updates, "check", lambda asked=True: checks.append(asked))
    boxes(monkeypatch, lambda texts: "Don't check")
    win.updates.at_start()
    win.updates.at_start()
    assert config.read("preferences.json")["update_check"] is False and checks == []


def test_no_question_without_remembering(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("5.5.0", remember=False)
    shown = boxes(monkeypatch, lambda texts: texts[0])
    w.updates.at_start()
    assert shown == [] and "update_check" not in config.read("preferences.json")


REAL_FETCH = updater.fetch_latest


def released(monkeypatch, tag="v9.1.0"):
    """GitHub's answer, made up: a release with every package."""
    monkeypatch.setattr(updater, "fetch_latest", lambda **_: REAL_FETCH(
        opener=opener_for(json.dumps(release_json(tag)).encode())))


def test_a_newer_release_is_offered_and_can_be_skipped(win, monkeypatch):
    released(monkeypatch)
    shown = boxes(monkeypatch, lambda texts: "Skip this version")
    win.updates.check(asked=False)
    assert wait_for(lambda: shown)
    text, buttons = shown[0]
    assert "9.1.0" in text and "5.5.0" in text
    assert {"Update now", "What's new", "Later", "Skip this version"} <= set(buttons)
    prefs = config.read("preferences.json")
    assert prefs["update_skip"] == "9.1.0" and prefs["update_checked"] > 0
    win.updates.check(asked=False)                     # skipped: the daily check stays quiet about it
    assert not wait_for(lambda: len(shown) > 1, timeout=1.0)
    win.updates.check(asked=True)                      # asking shows it again
    assert wait_for(lambda: len(shown) > 1)


def test_asking_when_up_to_date_says_so(win, monkeypatch):
    released(monkeypatch, "v5.5.0")
    shown = boxes(monkeypatch, lambda texts: texts[0])
    msgs = []
    monkeypatch.setattr(win, "_msg", msgs.append)
    win.updates.check(asked=True)
    assert wait_for(lambda: any("latest version" in m for m in msgs)) and shown == []


def test_a_failed_check_is_only_reported_when_asked(win, monkeypatch):
    def broken(**_):
        raise OSError("no network")
    monkeypatch.setattr(updater, "fetch_latest", broken)
    msgs = []
    monkeypatch.setattr(win, "_msg", msgs.append)
    win.updates.check(asked=False)
    assert not wait_for(lambda: any("no network" in m for m in msgs), timeout=0.5)
    win.updates.check(asked=True)
    assert wait_for(lambda: any("no network" in m for m in msgs))


def test_flatpak_and_source_only_point_to_the_release_page(win, monkeypatch):
    released(monkeypatch)
    win.updates.kind = "flatpak"
    shown = boxes(monkeypatch, lambda texts: "Later")
    win.updates.check(asked=True)
    assert wait_for(lambda: shown)
    assert "Update now" not in shown[0][1] and "Open the release page" in shown[0][1]


def test_update_now_downloads_checks_and_installs(win, monkeypatch, tmp_path):
    released(monkeypatch)
    real_download = updater.download
    monkeypatch.setattr(updater, "download", lambda url, sha, **kw: real_download(
        url, sha, dest_dir=str(tmp_path), opener=opener_for(PAYLOAD), **kw))
    ran = []
    monkeypatch.setattr(updater, "install_steps", lambda kind, path: (["install", path], "restart"))
    monkeypatch.setattr(updater, "run", lambda cmd: (ran.append(cmd), (True, ""))[1])
    shown = boxes(monkeypatch, lambda texts: "Update now" if "Update now" in texts else "Later")
    win.updates.check(asked=True)
    assert wait_for(lambda: len(shown) >= 2, timeout=10)
    assert ran == [["install", str(tmp_path / "inkline_9.1.0-1_amd64.deb")]]
    assert "installed" in shown[1][0] and "Restart now" in shown[1][1]


def test_a_bad_download_installs_nothing(win, monkeypatch, tmp_path):
    released(monkeypatch)
    real_download = updater.download
    monkeypatch.setattr(updater, "download", lambda url, sha, **kw: real_download(
        url, sha, dest_dir=str(tmp_path), opener=opener_for(b"tampered"), **kw))
    ran = []
    monkeypatch.setattr(updater, "run", lambda cmd: (ran.append(cmd), (True, ""))[1])
    msgs = []
    monkeypatch.setattr(win, "_msg", msgs.append)
    boxes(monkeypatch, lambda texts: "Update now" if "Update now" in texts else "Later")
    win.updates.check(asked=True)
    assert wait_for(lambda: any("SHA-256" in m for m in msgs), timeout=10)
    assert ran == [] and "inkline_9.1.0-1_amd64.deb" not in os.listdir(tmp_path)


def test_checking_without_remembering_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    from inkapp.window import Window
    w = Window("5.5.0", remember=False)
    released(monkeypatch)
    shown = boxes(monkeypatch, lambda texts: "Skip this version")
    w.updates.check(asked=True)
    assert wait_for(lambda: shown)
    assert config.read("preferences.json") == {} and not w.act_updates_auto.isChecked()


def test_the_appimage_is_put_in_place_off_the_window_thread(win, monkeypatch, tmp_path):
    import threading
    win.updates.kind = "appimage"
    win.updates.release = {"version": "9.1.0"}
    where = []
    monkeypatch.setattr(updater, "replace_appimage", lambda path: where.append(threading.current_thread()))
    shown = boxes(monkeypatch, lambda texts: "Later")
    win.updates.install(str(tmp_path / "new.AppImage"))
    assert wait_for(lambda: shown)
    assert where and where[0] is not threading.main_thread() and "Restart now" in shown[0][1]
