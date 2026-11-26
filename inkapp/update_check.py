"""`inkline --check-updates`: the check the update schedule runs while Inkline isn't open (update_schedule.py).

No window: it asks GitHub for the latest release (as Help → Check for updates does) and, if there's a newer
version the person hasn't skipped, shows a desktop notification. Its Update button starts Inkline with
`--update`, which opens the update box; nothing is installed without the person. The version found is kept in
the preferences too, so Inkline offers it when it next starts even if the notification was missed (or its button
isn't shown, as on some Linux desktops).

Linux notifications go through the desktop's notification service (org.freedesktop.Notifications) with `gdbus`,
or `notify-send` without a button where there's no gdbus; Windows shows Qt's tray notification.
"""

import os
import re
import shutil
import subprocess
import sys
import time

from inkengine.i18n import tr

from . import config, update_schedule, updater

WAIT = 3600   # how long a notification's button is listened for, in seconds
BUS = ["--session", "--dest", "org.freedesktop.Notifications", "--object-path", "/org/freedesktop/Notifications"]


def find(version, prefs, fetch=updater.fetch_latest):
    """The newer release to tell the person about, or None (none, skipped, checking off, or no network)."""
    if prefs.get("update_check") is not True:
        return None   # turned off since the schedule was set up (or a schedule left behind)
    try:
        release = fetch()
    except (OSError, ValueError):
        return None
    return release if updater.worth_offering(release, version, prefs) else None


def remember_found(release):
    prefs = config.read("preferences.json")
    config.write("preferences.json", {**prefs, "update_checked": time.time(),
                                      **({"update_found": release["version"]} if release else {})}, "Preferences")


def texts(new, old):
    return (tr("Inkline {new} is available").format(new=new),
            tr("You have {old}. Open Inkline to see what's new and update.").format(old=old), tr("Show the update"))


# --- Linux: the desktop's notification service ------------------------------------------------------------------
def gv(text):
    """A string as GVariant text, which gdbus reads each argument as (so a quote or a number stays a string)."""
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def gdbus_notify_args(title, body, button, icon="inkline"):
    return ["gdbus", "call", *BUS, "--method", "org.freedesktop.Notifications.Notify", gv("Inkline"), "uint32 0",
            gv(icon), gv(title), gv(body), f"[{gv('update')}, {gv(button)}]", "@a{sv} {}", "int32 0"]


def notification_id(reply):
    """The id in gdbus's answer to Notify, "(uint32 7,)", or None."""
    m = re.search(r"uint32 (\d+)", reply or "")
    return int(m.group(1)) if m else None


def outcome(line, nid):
    """What a line of `gdbus monitor` says about notification nid: "update", "closed" or None."""
    if f"uint32 {nid}," not in line and f"uint32 {nid})" not in line:
        return None
    if "ActionInvoked" in line:
        return "update" if "'update'" in line else "closed"
    if "NotificationClosed" in line:
        return "closed"
    return None


def notify_linux(title, body, button, wait=WAIT, popen=subprocess.Popen, run=subprocess.run):
    """Show the notification; True if its Update button was pressed."""
    if not shutil.which("gdbus"):
        if shutil.which("notify-send"):   # no button: Inkline offers the update when it next starts
            run(["notify-send", "--app-name=Inkline", "--icon=inkline", title, body], timeout=30)
        return False
    monitor = popen(["gdbus", "monitor", *BUS], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        reply = run(gdbus_notify_args(title, body, button), capture_output=True, text=True, timeout=30)
        nid = notification_id(reply.stdout)
        if nid is None:
            return False
        end = time.time() + wait
        for line in monitor.stdout:
            said = outcome(line, nid)
            if said:
                return said == "update"
            if time.time() > end:
                break
        return False
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        monitor.kill()


# --- Windows: a tray notification ------------------------------------------------------------------------------
def notify_windows(title, body, wait=WAIT):
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon
    app = QApplication.instance()
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return False
    tray = QSystemTrayIcon(app.windowIcon() if not app.windowIcon().isNull() else QIcon())
    tray.setToolTip("Inkline")
    clicked = []
    tray.messageClicked.connect(lambda: (clicked.append(True), app.quit()))
    tray.show()
    tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 30000)
    QTimer.singleShot(wait * 1000, app.quit)
    app.exec()
    tray.hide()
    return bool(clicked)


def open_update(kind=None):
    """Start Inkline with its update box open."""
    cmd = update_schedule.command(kind) + ["--update"]
    kw = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000008}   # DETACHED_PROCESS
    subprocess.Popen(cmd, close_fds=True, **kw)


def main(version):
    """The whole check: returns 0 (nothing to say is not a failure)."""
    release = find(version, config.read("preferences.json"))
    remember_found(release)
    if not release:
        return 0
    title, body, button = texts(release["version"], version)
    pressed = notify_windows(title, body) if sys.platform == "win32" else notify_linux(title, body, button)
    if pressed:
        open_update()
    return 0
