"""When Inkline checks for updates while it isn't running: at login, every day or every week, as the person chose
under Help → Check for updates automatically. Inkline sets it up itself, for the person only (no administrator
password), whichever way it was installed:

- Linux: a systemd user timer, ~/.config/systemd/user/inkline-update.{timer,service}. It runs `inkline
  --check-updates` at login and/or on the interval, catching up after the computer was off; the service is
  skipped once the Inkline it runs is gone (a package removed leaves the files in the person's home folder).
- Windows: "At login" is a value under the user's Run key; every day or week, a Task Scheduler task of the user's
  own, started late if the computer was off when it was due.
- Flatpak: none (a sandbox can't set either up, and Flatpak updates come through Flathub); Inkline still checks
  when it starts.

`--check-updates` (check.py) looks for a newer version and, if there is one, shows a desktop notification whose
Update button opens Inkline's update box. Nothing is installed without the person.
"""

import os
import shutil
import subprocess
import sys

from . import updater

SCHEDULES = {"start": "When Inkline starts", "login": "At login", "daily": "Every day", "weekly": "Every week"}
BACKGROUND = ("login", "daily", "weekly")   # need a timer or task: Inkline isn't running when they're due
UNIT = "inkline-update"
TASK = "Inkline update check"
RUN_VALUE = "Inkline update check"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def supported(kind=None, platform=None):
    """Whether this copy can check while it isn't running (not in a Flatpak, and only on Linux or Windows)."""
    kind = kind or updater.install_kind()
    platform = platform or sys.platform
    return kind != "flatpak" and (platform.startswith("linux") or platform == "win32")


def command(kind=None, env=None, root=updater.ROOT):
    """How the timer or task starts this Inkline: an absolute program first (the timer checks it's still there)."""
    env = os.environ if env is None else env
    kind = kind or updater.install_kind(env=env)
    if kind == "windows":
        return [sys.executable]
    if kind == "source":
        return [sys.executable, os.path.join(root, "inkline.py")]
    cmd = updater.relaunch_command(kind, env)
    if not os.path.isabs(cmd[0]):   # the .deb and Arch package's /usr/bin/inkline
        cmd = [shutil.which(cmd[0], path=env.get("PATH")) or "/usr/bin/inkline"] + cmd[1:]
    return cmd


def _quote(arg):
    """An argument as systemd's ExecStart= reads it."""
    return '"' + arg.replace("\\", "\\\\").replace('"', '\\"') + '"' if any(c in arg for c in ' "\\\'') else arg


def systemd_units(schedule, cmd):
    """{file name: contents} for the user timer and the service it starts."""
    program = cmd[0]
    service = ("[Unit]\nDescription=Check for a new version of Inkline\n"
               f"ConditionPathExists={program}\n\n"
               "[Service]\nType=oneshot\n"
               f"ExecStart={' '.join(_quote(a) for a in cmd + ['--check-updates'])}\n")
    when = {"login": "OnStartupSec=2min\n",   # the user's systemd starts at login
            "daily": "OnStartupSec=5min\nOnCalendar=daily\nPersistent=true\nRandomizedDelaySec=1h\n",
            "weekly": "OnCalendar=weekly\nPersistent=true\nRandomizedDelaySec=1h\n"}[schedule]
    timer = (f"[Unit]\nDescription=Check for a new version of Inkline ({SCHEDULES[schedule].lower()})\n\n"
             f"[Timer]\n{when}\n[Install]\nWantedBy=timers.target\n")
    return {f"{UNIT}.service": service, f"{UNIT}.timer": timer}


def unit_dir(env=None):
    env = os.environ if env is None else env
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME") or os.path.expanduser("~"), ".config")
    return os.path.join(base, "systemd", "user")


def task_xml(schedule, cmd, start="2026-01-01T12:00:00"):
    """A Task Scheduler task for the user: every day or week at noon, run late if the computer was off."""
    trigger = ("<ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>" if schedule == "daily" else
               "<ScheduleByWeek><WeeksInterval>1</WeeksInterval><DaysOfWeek><Monday /></DaysOfWeek></ScheduleByWeek>")
    args = " ".join(f'"{a}"' for a in cmd[1:] + ["--check-updates"])
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Checks for a new version of Inkline</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>{start}</StartBoundary><Enabled>true</Enabled>{trigger}</CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <StartWhenAvailable>true</StartWhenAvailable>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
  </Settings>
  <Actions Context="Author"><Exec><Command>{esc(cmd[0])}</Command><Arguments>{esc(args)}</Arguments></Exec></Actions>
</Task>
"""


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _run(cmd, runner):
    try:
        p = runner(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return str(e)
    return "" if p.returncode == 0 else (p.stderr or p.stdout or f"exit {p.returncode}").strip()


def apply(schedule, kind=None, env=None, runner=subprocess.run, platform=None, registry=None):
    """Set up (or remove, for "start" or None: checks only when Inkline starts, or none) the check while Inkline
    isn't running. Returns what went wrong, or ""."""
    env = os.environ if env is None else env
    platform = platform or sys.platform
    kind = kind or updater.install_kind(env=env)
    want = schedule if schedule in BACKGROUND and supported(kind, platform) else None
    if platform == "win32":
        return _apply_windows(want, kind, env, runner, registry)
    if not platform.startswith("linux"):
        return ""
    folder = unit_dir(env)
    if want is None:
        if os.path.exists(os.path.join(folder, f"{UNIT}.timer")):
            _run(["systemctl", "--user", "disable", "--now", f"{UNIT}.timer"], runner)
        for name in (f"{UNIT}.timer", f"{UNIT}.service"):
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass
        _run(["systemctl", "--user", "daemon-reload"], runner)
        return ""
    units = systemd_units(want, command(kind, env))
    if all(_read(os.path.join(folder, n)) == text for n, text in units.items()) and \
            not _run(["systemctl", "--user", "is-enabled", "--quiet", f"{UNIT}.timer"], runner):
        return ""   # already so (Inkline sets it again at each start, in case it has moved)
    try:
        os.makedirs(folder, exist_ok=True)
        for name, text in units.items():
            with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
                f.write(text)
    except OSError as e:
        return str(e)
    return _run(["systemctl", "--user", "daemon-reload"], runner) or \
        _run(["systemctl", "--user", "enable", f"{UNIT}.timer"], runner) or \
        _run(["systemctl", "--user", "restart", f"{UNIT}.timer"], runner)


def _apply_windows(want, kind, env, runner, registry):
    import tempfile
    cmd = command(kind, env)
    reg = registry or _winreg_run_key
    err = ""
    if want == "login":
        err = reg(" ".join(f'"{a}"' for a in cmd + ["--check-updates"]))
    else:
        reg(None)
    if want in ("daily", "weekly"):
        path = os.path.join(tempfile.mkdtemp(prefix="inkline-task-"), "task.xml")
        with open(path, "w", encoding="utf-16") as f:
            f.write(task_xml(want, cmd))
        err = err or _run(["schtasks", "/Create", "/TN", TASK, "/XML", path, "/F"], runner)
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    else:
        _run(["schtasks", "/Delete", "/TN", TASK, "/F"], runner)   # none there is fine
    return err


def _winreg_run_key(value):
    """Set (or with None, remove) Inkline's value under the user's Run key; returns what went wrong, or ""."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if value is None:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, value)
    except OSError as e:
        return str(e)
    return ""
