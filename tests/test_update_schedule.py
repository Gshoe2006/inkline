"""Checking for updates while Inkline is closed: the timer or task Inkline sets up, the check it runs
(`--check-updates`), and the Help menu that chooses when. Nothing here reaches the network, the real systemd or the
real Windows registry."""

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
from PySide6.QtWidgets import QApplication

from inkapp import config, update_check, update_schedule, updater

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def app():
    QApplication.instance() or QApplication([])


class Runner:
    """Records the commands run, as subprocess.run would get them."""
    def __init__(self, check=None):
        self.calls, self.check = [], check

    def __call__(self, cmd, **_kw):
        self.calls.append(cmd)
        if self.check:
            self.check(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")


# --- what is set up ----------------------------------------------------------------------------------------------
def test_supported():
    assert update_schedule.supported("deb", "linux") and update_schedule.supported("windows", "win32")
    assert not update_schedule.supported("flatpak", "linux") and not update_schedule.supported("source", "freebsd14")


def test_the_command_starts_this_copy(tmp_path):
    env = {"APPIMAGE": "/home/a/Inkline.AppImage", "HOME": "/home/a"}
    assert update_schedule.command("appimage", env) == ["/home/a/Inkline.AppImage"]
    assert update_schedule.command("run-system", {}) == ["/usr/local/bin/inkline"]
    assert update_schedule.command("source", {}, root="/src/inkline") == [sys.executable, "/src/inkline/inkline.py"]
    assert update_schedule.command("windows", {}) == [sys.executable]
    tool = tmp_path / "inkline"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    assert update_schedule.command("deb", {"PATH": str(tmp_path)}) == [str(tool)]
    assert update_schedule.command("arch", {"PATH": str(tmp_path / "none")}) == ["/usr/bin/inkline"]


@pytest.mark.parametrize("schedule", update_schedule.BACKGROUND)
def test_systemd_units(schedule):
    units = update_schedule.systemd_units(schedule, ["/opt/my apps/Inkline.AppImage"])
    service, timer = units["inkline-update.service"], units["inkline-update.timer"]
    assert 'ExecStart="/opt/my apps/Inkline.AppImage" --check-updates' in service
    assert "ConditionPathExists=/opt/my apps/Inkline.AppImage" in service   # skipped once Inkline is gone
    assert "Type=oneshot" in service and "WantedBy=timers.target" in timer
    assert ("OnStartupSec=" in timer) == (schedule != "weekly")
    assert ("Persistent=true" in timer) == (schedule != "login")           # a missed day is caught up
    assert {"daily": "OnCalendar=daily", "weekly": "OnCalendar=weekly"}.get(schedule, "[Timer]") in timer


@pytest.mark.skipif(not shutil.which("systemd-analyze"), reason="systemd-analyze isn't installed")
@pytest.mark.parametrize("schedule", update_schedule.BACKGROUND)
def test_systemd_accepts_the_units(schedule, tmp_path):
    for name, text in update_schedule.systemd_units(schedule, [sys.executable, "/x/inkline.py"]).items():
        (tmp_path / name).write_text(text)
    runtime = tmp_path / "rt"
    runtime.mkdir(mode=0o700)
    p = subprocess.run(["systemd-analyze", "verify", "--user", str(tmp_path / "inkline-update.timer"),
                        str(tmp_path / "inkline-update.service")], capture_output=True, text=True,
                       env={**os.environ, "XDG_RUNTIME_DIR": str(runtime)}, timeout=60)
    ours = [line for line in (p.stdout + p.stderr).splitlines() if "inkline-update" in line]
    assert ours == [], ours


def test_linux_apply_sets_up_changes_and_removes_the_timer(tmp_path):
    env = {"XDG_CONFIG_HOME": str(tmp_path), "APPIMAGE": "/a/Inkline.AppImage"}
    run = Runner()
    folder = tmp_path / "systemd" / "user"
    assert update_schedule.apply("daily", "appimage", env, run, "linux") == ""
    assert "OnCalendar=daily" in (folder / "inkline-update.timer").read_text()
    assert run.calls == [["systemctl", "--user", "daemon-reload"], ["systemctl", "--user", "enable", "inkline-update.timer"],
                         ["systemctl", "--user", "restart", "inkline-update.timer"]]
    again = Runner()
    assert update_schedule.apply("daily", "appimage", env, again, "linux") == ""
    assert again.calls == [["systemctl", "--user", "is-enabled", "--quiet", "inkline-update.timer"]]   # already so
    update_schedule.apply("weekly", "appimage", env, Runner(), "linux")
    assert "OnCalendar=weekly" in (folder / "inkline-update.timer").read_text()
    off = Runner()
    assert update_schedule.apply("start", "appimage", env, off, "linux") == ""
    assert not (folder / "inkline-update.timer").exists() and not (folder / "inkline-update.service").exists()
    assert ["systemctl", "--user", "disable", "--now", "inkline-update.timer"] in off.calls
    update_schedule.apply("login", "appimage", env, Runner(), "linux")
    update_schedule.apply("daily", "flatpak", env, Runner(), "linux")          # a Flatpak can't: none left behind
    assert not (folder / "inkline-update.timer").exists()


def test_linux_apply_says_what_went_wrong(tmp_path):
    def fail(cmd, **_kw):
        return subprocess.CompletedProcess(cmd, 1, "", "Failed to connect to bus")
    err = update_schedule.apply("daily", "deb", {"XDG_CONFIG_HOME": str(tmp_path), "PATH": ""}, fail, "linux")
    assert "Failed to connect to bus" in err
    missing = update_schedule.apply("daily", "deb", {"XDG_CONFIG_HOME": str(tmp_path), "PATH": ""},
                                    lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("systemctl")), "linux")
    assert "systemctl" in missing   # the files were written last time, but the timer isn't on: tried again


def test_windows_task_and_login(tmp_path):
    reg = []
    seen = {}

    def check(cmd):
        if "/XML" in cmd:   # the task file is there while schtasks reads it
            seen["xml"] = open(cmd[cmd.index("/XML") + 1], encoding="utf-16").read()
    run = Runner(check)
    store = lambda value: reg.append(value) or ""
    assert update_schedule.apply("login", "windows", {}, run, "win32", store) == ""
    assert reg[-1] == f'"{sys.executable}" "--check-updates"'
    assert run.calls[-1] == ["schtasks", "/Delete", "/TN", "Inkline update check", "/F"]
    assert update_schedule.apply("daily", "windows", {}, run, "win32", store) == ""
    assert reg[-1] is None and run.calls[-1][:4] == ["schtasks", "/Create", "/TN", "Inkline update check"]
    assert "<ScheduleByDay>" in seen["xml"] and "<StartWhenAvailable>true</StartWhenAvailable>" in seen["xml"]
    assert not os.path.exists(run.calls[-1][5])                             # the file is tidied away
    update_schedule.apply(None, "windows", {}, run, "win32", store)
    assert reg[-1] is None and run.calls[-1][1] == "/Delete"


def test_the_task_is_well_formed():
    xml = update_schedule.task_xml("weekly", [r"C:\Program Files\R&D\Inkline.exe"])
    root = ET.fromstring(xml.replace('encoding="UTF-16"', ""))
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    assert root.find(".//t:Command", ns).text == r"C:\Program Files\R&D\Inkline.exe"
    assert root.find(".//t:Arguments", ns).text == '"--check-updates"'
    assert root.find(".//t:ScheduleByWeek", ns) is not None
    assert root.find(".//t:RunLevel", ns).text == "LeastPrivilege"            # no administrator


def test_uninstalling_removes_it():
    stub = open(os.path.join(ROOT, "packaging", "installer-stub.sh"), encoding="utf-8").read()
    assert "systemctl --user disable --now inkline-update.timer" in stub
    iss = open(os.path.join(ROOT, "packaging", "windows", "inkline.iss"), encoding="utf-8").read()
    assert '/Delete /TN ""Inkline update check""' in iss and '/v ""Inkline update check""' in iss
    assert update_schedule.TASK == update_schedule.RUN_VALUE == "Inkline update check"


# --- the check it runs ---------------------------------------------------------------------------------------------
REL = {"version": "9.1.0", "notes": "", "page": "https://example.invalid/r", "assets": {}}


def test_find():
    on = {"update_check": True}
    assert update_check.find("5.7.0", on, lambda: REL) == REL
    assert update_check.find("5.7.0", {}, lambda: REL) is None                 # turned off since
    assert update_check.find("9.1.0", on, lambda: REL) is None
    assert update_check.find("5.7.0", {**on, "update_skip": "9.1.0"}, lambda: REL) is None

    def offline():
        raise OSError("no network")
    assert update_check.find("5.7.0", on, offline) is None


def test_reading_gdbus():
    assert update_check.notification_id("(uint32 17,)\n") == 17 and update_check.notification_id("") is None
    sig = "/org/freedesktop/Notifications: org.freedesktop.Notifications."
    assert update_check.outcome(sig + "ActionInvoked (uint32 17, 'update')", 17) == "update"
    assert update_check.outcome(sig + "ActionInvoked (uint32 17, 'default')", 17) == "closed"
    assert update_check.outcome(sig + "NotificationClosed (uint32 17, uint32 2)", 17) == "closed"
    assert update_check.outcome(sig + "NotificationClosed (uint32 171, uint32 2)", 17) is None   # someone else's
    assert update_check.outcome(sig + "ActionInvoked (uint32 3, 'update')", 17) is None
    args = update_check.gdbus_notify_args("It's 9.1.0", "42", "L'actualiser")
    assert "'It\\'s 9.1.0'" in args and "'42'" in args and "['update', 'L\\'actualiser']" in args
    assert "uint32 0" in args and "int32 0" in args


class Monitor:
    def __init__(self, lines):
        self.stdout = iter(lines)
        self.killed = False

    def kill(self):
        self.killed = True


@pytest.mark.parametrize("lines,pressed", [
    (["x NotificationClosed (uint32 4, uint32 1)", "x ActionInvoked (uint32 9, 'update')"], True),
    (["x NotificationClosed (uint32 9, uint32 2)"], False),
    ([], False)])
def test_notify_linux(monkeypatch, lines, pressed):
    monkeypatch.setattr(update_check.shutil, "which", lambda name: "/usr/bin/" + name)
    mon = Monitor(lines)
    sent = []

    def run(cmd, **_kw):
        sent.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "(uint32 9,)\n", "")
    assert update_check.notify_linux("T", "B", "Update now", popen=lambda *a, **k: mon, run=run) is pressed
    assert mon.killed and sent[0][:2] == ["gdbus", "call"]


def test_without_gdbus_a_plain_notification(monkeypatch):
    monkeypatch.setattr(update_check.shutil, "which", lambda name: "/usr/bin/notify-send" if name == "notify-send" else None)
    sent = []
    assert update_check.notify_linux("T", "B", "U", run=lambda cmd, **k: sent.append(cmd)) is False
    assert sent == [["notify-send", "--app-name=Inkline", "--icon=inkline", "T", "B"]]


def test_main_notifies_remembers_and_opens(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    config.write("preferences.json", {"update_check": True, "update_schedule": "daily"}, "Preferences")
    monkeypatch.setattr(updater, "fetch_latest", lambda: REL)
    monkeypatch.setattr(update_check, "find", lambda version, prefs: REL if prefs.get("update_check") else None)
    shown, opened = [], []
    monkeypatch.setattr(update_check, "notify_linux", lambda *a: shown.append(a) or True)
    monkeypatch.setattr(update_check, "notify_windows", lambda *a: shown.append(a) or True)
    monkeypatch.setattr(update_check, "open_update", lambda: opened.append(True))
    assert update_check.main("5.7.0") == 0
    assert "9.1.0" in shown[0][0] and opened == [True]
    prefs = config.read("preferences.json")
    assert prefs["update_found"] == "9.1.0" and prefs["update_checked"] > 0


def test_the_command_line_check_runs(tmp_path):
    """`inkline.py --check-updates` with checking off: nothing fetched, nothing shown, done at once."""
    p = subprocess.run([sys.executable, os.path.join(ROOT, "inkline.py"), "--check-updates"], capture_output=True,
                       text=True, timeout=60, env={**os.environ, "INKLINE_CONFIG_DIR": str(tmp_path),
                                                   "QT_QPA_PLATFORM": "offscreen"})
    assert p.returncode == 0, p.stderr


def wait_for(cond, timeout=5.0):
    import time
    end = time.time() + timeout
    while time.time() < end and not cond():
        QApplication.processEvents()
        time.sleep(0.01)
    return cond()


# --- the Help menu ---------------------------------------------------------------------------------------------------
@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    asked = []
    monkeypatch.setattr(update_schedule, "apply", lambda schedule, kind=None, **kw: asked.append(schedule) or "")
    from inkapp.window import Window
    w = Window("5.7.0", remember=True)
    w.updates.kind = "deb"
    w.asked = asked
    return w


def test_choosing_when_to_check(win):
    acts = win.updates.schedule_actions
    acts["daily"].trigger()
    prefs = config.read("preferences.json")
    assert prefs["update_check"] is True and prefs["update_schedule"] == "daily"
    assert wait_for(lambda: win.asked == ["daily"])               # set up off the window's thread
    assert acts["daily"].isChecked() and win.updates.schedule() == "daily"
    acts["start"].trigger()
    assert wait_for(lambda: win.asked[-1] == "start") and config.read("preferences.json")["update_schedule"] == "start"
    acts["off"].trigger()
    assert config.read("preferences.json")["update_check"] is False and wait_for(lambda: win.asked[-1] is None)
    assert win.updates.schedule() == "off" and acts["off"].isChecked()


def test_a_flatpak_only_checks_when_open(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(updater, "install_kind", lambda *a, **k: "flatpak")
    from inkapp.window import Window
    w = Window("5.7.0", remember=True)
    acts = w.updates.schedule_actions
    assert acts["start"].isEnabled() and acts["off"].isEnabled()
    assert not any(acts[k].isEnabled() for k in update_schedule.BACKGROUND)
    assert "Flatpak" in acts["daily"].toolTip()


def test_elsewhere_only_while_open(tmp_path, monkeypatch):
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(update_schedule, "supported", lambda kind=None, platform=None: False)
    from inkapp.window import Window
    w = Window("5.7.0", remember=True)
    w.updates.kind = "source"
    acts = w.updates.schedule_actions
    assert not acts["weekly"].isEnabled() and "Flatpak" not in acts["weekly"].toolTip()


def test_a_failure_to_set_it_up_is_said(win, monkeypatch):
    monkeypatch.setattr(update_schedule, "apply", lambda *a, **k: "Failed to connect to bus")
    msgs = []
    monkeypatch.setattr(win, "_msg", msgs.append)
    win.updates.schedule_actions["weekly"].trigger()
    assert wait_for(lambda: any("Failed to connect to bus" in m and "choose it again under Help" in m for m in msgs))


def test_a_version_found_while_closed_is_offered_at_start(win, monkeypatch):
    import time
    config.write("preferences.json", {"update_check": True, "update_schedule": "daily", "update_checked": time.time(),
                                      "update_found": "9.1.0"}, "Preferences")
    checks = []
    monkeypatch.setattr(win.updates, "check", lambda asked=True: checks.append(asked))
    win.updates.at_start()
    assert checks == [False]                      # not due, but found: checked (and offered) now
    assert wait_for(lambda: win.asked == ["daily"])   # and the timer pointed at this copy again
    config.write("preferences.json", {**config.read("preferences.json"), "update_found": "5.7.0"}, "Preferences")
    win.updates.at_start()
    assert checks == [False]                      # this version: nothing to offer


def test_an_offered_version_is_forgotten_once_current(win, monkeypatch):
    config.write("preferences.json", {"update_check": True, "update_found": "9.1.0"}, "Preferences")
    msgs = []
    monkeypatch.setattr(win, "_msg", msgs.append)
    win.updates._found({**REL, "version": "5.7.0"}, True)
    assert not config.read("preferences.json").get("update_found")


def test_the_demo_notification(monkeypatch):
    assert update_check.demo_version("5.8.0") == "5.8.1" and update_check.demo_version("dev") == "99.0.0"
    shown, opened, fetched = [], [], []
    monkeypatch.setattr(update_check, "notify_linux", lambda *a: shown.append(a) or True)
    monkeypatch.setattr(update_check, "notify_windows", lambda *a: shown.append(a) or True)
    monkeypatch.setattr(update_check, "open_update", lambda: opened.append(True))
    monkeypatch.setattr(update_check, "find", lambda *a: fetched.append(a))
    assert update_check.main("5.8.0", demo=True) == 0
    assert "5.8.1" in shown[0][0] and opened == [True] and fetched == []   # nothing fetched or remembered


def test_the_manual_tests_cover_what_ci_cant():
    text = open(os.path.join(ROOT, "docs", "manual-tests.md"), encoding="utf-8").read()
    for must in ("--check-updates --demo", "list-timers inkline-update.timer", "Task Scheduler", "tour", "High contrast"):
        assert must in text, must


# --- macOS --------------------------------------------------------------------------------------------------------
def test_macos_is_recognised_and_updates_from_its_disk_image():
    assert updater.install_kind(env={}, frozen=True, platform="darwin") == "macos"
    assert updater.install_kind(env={}, frozen="macos") == "macos"
    assert updater.asset_name("macos", "6.0.0") == "inkline-6.0.0-macos.dmg"
    assert updater.app_bundle(executable="/Applications/Inkline.app/Contents/MacOS/Inkline") == "/Applications/Inkline.app"
    assert updater.app_bundle(executable="/Users/a/Apps/Inkline.app/Contents/MacOS/Inkline") == "/Users/a/Apps/Inkline.app"
    cmd, after = updater.install_steps("macos", "/tmp/new.dmg")
    assert cmd[:2] == ["sh", "-c"] and cmd[-2:] == ["/tmp/new.dmg", updater.app_bundle()] and after == "restart"
    assert updater.relaunch_command("macos")[:2] == ["open", "-n"]
    assert update_schedule.command("macos", {}) == [sys.executable]
    assert update_schedule.supported("macos", "darwin") and not update_schedule.supported("flatpak", "darwin")


def test_the_swap_script_puts_the_new_app_in_place(tmp_path):
    """The real script, with stand-ins for macOS's hdiutil and ditto (the disk image is a folder here)."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "hdiutil").write_text('#!/bin/sh\nif [ "$1" = attach ]; then for a; do last="$a"; done; '
                                  'mnt=""; while [ $# -gt 0 ]; do [ "$1" = -mountpoint ] && mnt="$2"; shift; done; '
                                  'cp -R "$last"/. "$mnt"/; fi\n')
    (bin_ / "ditto").write_text('#!/bin/sh\ncp -R "$1" "$2"\n')
    for f in bin_.iterdir():
        f.chmod(0o755)
    dmg = tmp_path / "dmg"
    (dmg / "Inkline.app" / "Contents").mkdir(parents=True)
    (dmg / "Inkline.app" / "Contents" / "VERSION").write_text("6.1.0")
    app = tmp_path / "Applications" / "Inkline.app"
    (app / "Contents").mkdir(parents=True)
    (app / "Contents" / "VERSION").write_text("6.0.0")
    cmd, _after = updater.install_steps("macos", str(dmg))
    cmd[-1] = str(app)
    p = subprocess.run(cmd, env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}"}, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert (app / "Contents" / "VERSION").read_text() == "6.1.0"
    assert not (tmp_path / "Applications" / "Inkline.app.new").exists()
    assert not (tmp_path / "Applications" / "Inkline.app.old").exists()


@pytest.mark.parametrize("schedule", update_schedule.BACKGROUND)
def test_the_launchd_agent(schedule):
    import plistlib
    job = plistlib.loads(update_schedule.launchd_plist(schedule, ["/Applications/Inkline.app/Contents/MacOS/Inkline"]))
    assert job["Label"] == update_schedule.AGENT
    assert job["ProgramArguments"] == ["/Applications/Inkline.app/Contents/MacOS/Inkline", "--check-updates"]
    assert job.get("RunAtLoad") == (True if schedule == "login" else None)
    cal = job.get("StartCalendarInterval")
    assert (cal is None) == (schedule == "login") and (cal or {}).get("Weekday") == (1 if schedule == "weekly" else None)


def test_macos_apply_and_remove(tmp_path):
    run = Runner()
    env = {"HOME": str(tmp_path)}
    assert update_schedule.apply("daily", "macos", env, run, "darwin") == ""
    path = update_schedule.agent_path(env)
    assert os.path.exists(path) and run.calls[-1][:2] == ["launchctl", "bootstrap"]
    assert update_schedule.apply("start", "macos", env, run, "darwin") == ""
    assert not os.path.exists(path) and ["launchctl", "bootout"] == run.calls[-1][:2]


def test_macos_notification():
    seen = []
    assert update_check.notify_macos('Inkline "6.1.0"', "You have 6.0.0", run=lambda c, **k: seen.append(c)) is False
    assert seen[0][:2] == ["osascript", "-e"] and 'with title "Inkline \\"6.1.0\\""' in seen[0][2]


def test_the_release_builds_and_checks_macos():
    flow = open(os.path.join(ROOT, ".github", "workflows", "release.yml"), encoding="utf-8").read()
    assert "packaging/macos/build.py --arch" in flow and "--install-kind macos" in flow
    assert "runner: macos-15 }" in flow and "runner: macos-15-intel }" in flow and "arch -x86_64" in flow
    assert '= 15 ||' in flow and "name: pkg-macos-${{ matrix.arch }}\n" in flow
