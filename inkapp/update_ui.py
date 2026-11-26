"""The window's side of updates (inkapp/updater.py does the work): ask once whether to check, check in the
background at most daily, offer a newer version, download it with a progress bar and install it.

The network and the installing run on worker threads; their results come back to the window as signals.
"""

import subprocess
import threading
import time

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from inkengine.i18n import tr

from . import config, updater

NOTIFY_ONLY = ("flatpak", "source")


class Updates(QObject):
    found = Signal(object, bool)         # the latest release (or None), and whether the person asked
    failed = Signal(str, bool)           # what went wrong, and whether the person asked
    progress = Signal(int, int)
    downloaded = Signal(object, str)     # the downloaded file (None if cancelled), or what went wrong
    installed = Signal(bool, str)

    def __init__(self, window, version, kind=None):
        super().__init__(window)
        self.window, self.version = window, version
        self.kind = kind or updater.install_kind()
        self.release = None
        self._cancel = False
        self.found.connect(self._found)
        self.failed.connect(self._failed)
        self.downloaded.connect(self._downloaded)
        self.installed.connect(self._installed)
        self._progress_dialog = None
        self.progress.connect(self._show_progress)

    def _save(self, **changes):
        """Keep update preferences (not when the window remembers nothing); a failed write is said."""
        if not self.window.remember:
            return
        err = config.write("preferences.json", {**config.read("preferences.json"), **changes}, "Preferences")
        if err:
            self.window._msg(err)

    def _box(self, icon, title, text, informative=""):
        box = QMessageBox(icon, title, text, QMessageBox.StandardButton.NoButton, self.window)
        if informative:
            box.setInformativeText(informative)
        return box

    # --- checking --------------------------------------------------------------------------------------
    def at_start(self):
        """At start: ask once whether to check for updates; then check if a day has passed since the last."""
        if not self.window.remember:
            return
        prefs = config.read("preferences.json")
        if prefs.get("update_check") is None:
            box = QMessageBox(QMessageBox.Icon.Question, tr("Check for updates?"),
                              tr("Should Inkline check once a day for a new version, and tell you when there is one?"),
                              QMessageBox.StandardButton.NoButton, self.window)
            box.setInformativeText(tr("It asks GitHub, where Inkline is published; nothing about you or your work is "
                                      "sent. You can change this under Help."))
            yes = box.addButton(tr("Check for updates"), QMessageBox.ButtonRole.AcceptRole)
            box.addButton(tr("Don't check"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(yes)
            box.exec()
            self._save(update_check=box.clickedButton() is yes)
            prefs = config.read("preferences.json")
            self.window.act_updates_auto.setChecked(prefs.get("update_check") is True)
        if updater.due(prefs):
            self.check(asked=False)

    def check(self, asked=True):
        """Ask GitHub for the latest release, on a worker thread."""
        if asked:
            self.window._msg(tr("Checking for updates…"))

        def work():
            try:
                release = updater.fetch_latest()
            except (OSError, ValueError) as e:
                self.failed.emit(str(e), asked)
                return
            self.found.emit(release, asked)
        threading.Thread(target=work, daemon=True).start()

    def set_automatic(self, on):
        self._save(update_check=bool(on))

    def _failed(self, why, asked):
        if asked:
            self.window._msg(tr("Couldn't check for updates ({why}). Check the internet connection and try again.")
                             .format(why=why))

    def _found(self, release, asked):
        prefs = config.read("preferences.json")
        self._save(update_checked=time.time())
        self.release = release
        if not release or not updater.newer(release["version"], self.version):
            if asked:
                self.window._msg(tr("Inkline {version} is the latest version.").format(version=self.version))
            return
        if not asked and not updater.worth_offering(release, self.version, prefs):
            return   # skipped by the person: only Help → Check for updates shows it again
        self.offer(release)

    # --- offering ----------------------------------------------------------------------------------------
    def offer(self, release):
        version = release["version"]
        box = QMessageBox(QMessageBox.Icon.Information, tr("Update available"),
                          tr("Inkline {new} is available. You have {old}.").format(new=version, old=self.version),
                          QMessageBox.StandardButton.NoButton, self.window)
        name = updater.asset_name(self.kind, version)
        can = self.kind not in NOTIFY_ONLY and name in release["assets"]
        if not can:
            box.setInformativeText(tr("This copy of Inkline is updated by Flatpak or from its source code, not by "
                                      "itself. The release page has the new version.") if self.kind in NOTIFY_ONLY
                                   else tr("The release doesn't have a package for this copy of Inkline yet. The "
                                           "release page has the new version."))
        elif self.kind in updater.NEEDS_ADMIN:
            box.setInformativeText(tr("Installing it asks for an administrator password, as installing any program "
                                      "does."))
        update = box.addButton(tr("Update now") if can else tr("Open the release page"), QMessageBox.ButtonRole.AcceptRole)
        notes = box.addButton(tr("What's new"), QMessageBox.ButtonRole.HelpRole)
        box.addButton(tr("Later"), QMessageBox.ButtonRole.RejectRole)
        skip = box.addButton(tr("Skip this version"), QMessageBox.ButtonRole.ActionRole)
        box.setDefaultButton(update)
        box.exec()
        chosen = box.clickedButton()
        if chosen is notes:
            QDesktopServices.openUrl(QUrl(release["page"]))
        elif chosen is skip:
            self._save(update_skip=version)
        elif chosen is update:
            if can:
                self.start_download(release)
            else:
                QDesktopServices.openUrl(QUrl(release["page"]))

    # --- downloading and installing ----------------------------------------------------------------------
    def start_download(self, release):
        url, sha, _size = release["assets"][updater.asset_name(self.kind, release["version"])]
        self._cancel = False
        d = QProgressDialog(tr("Downloading Inkline {version}…").format(version=release["version"]), tr("Cancel"),
                            0, 100, self.window)
        d.setWindowTitle(tr("Update available"))
        d.setMinimumDuration(0)
        d.canceled.connect(lambda: setattr(self, "_cancel", True))
        d.show()
        self._progress_dialog = d

        def work():
            try:
                path = updater.download(url, sha, progress=lambda a, b: self.progress.emit(a, b),
                                        cancelled=lambda: self._cancel)
            except OSError as e:
                self.downloaded.emit(None, str(e))
                return
            self.downloaded.emit(path, "")
        threading.Thread(target=work, daemon=True).start()

    def _show_progress(self, done, total):
        d = self._progress_dialog
        if d is not None and total:
            d.setValue(min(99, done * 100 // total))

    def _downloaded(self, path, why):
        if self._progress_dialog is not None:
            self._progress_dialog.reset()
            self._progress_dialog = None
        if path is None:
            if why:
                self.window._msg(tr("The update couldn't be downloaded ({why}). Try again from Help → Check for "
                                    "updates.").format(why=why))
            return
        self.install(path)

    def install(self, path):
        cmd, after = updater.install_steps(self.kind, path)
        version = self.release["version"] if self.release else ""
        if after == "manual":   # no way to ask for the administrator password here: the person installs it
            QDesktopServices.openUrl(QUrl.fromLocalFile(path.rsplit("/", 1)[0]))
            box = self._box(QMessageBox.Icon.Information, tr("Update downloaded"), tr(
                "The new version is downloaded. To install it, open a terminal and run:\n\n{command}").format(
                command=updater.manual_command(self.kind, path)))
            box.addButton(QMessageBox.StandardButton.Ok)
            box.exec()
            return
        if after == "quit":     # Windows: the installer takes over once Inkline has closed
            if self.window.close():
                subprocess.Popen(cmd, close_fds=True)
                QApplication.quit()
            return
        self.window._msg(tr("Installing Inkline {version}…").format(version=version))

        def work():   # off the window's thread: an AppImage is a large file to copy
            if after == "replace":
                try:
                    updater.replace_appimage(path)
                except OSError as e:
                    self.installed.emit(False, str(e))
                    return
                self.installed.emit(True, "")
                return
            ok, out = updater.run(cmd)
            self.installed.emit(ok, out)
        threading.Thread(target=work, daemon=True).start()

    def _installed(self, ok, out):
        version = self.release["version"] if self.release else ""
        if not ok:
            # a box, not the status bar: the installer's own words are what tells what went wrong
            box = self._box(QMessageBox.Icon.Warning, tr("Update not installed"), tr(
                "Inkline {version} couldn't be installed. This version still works; try again from Help → Check for "
                "updates, or install it from the release page.").format(version=version))
            if out:
                box.setDetailedText(out)
            box.addButton(QMessageBox.StandardButton.Ok)
            box.exec()
            return
        box = self._box(QMessageBox.Icon.Information, tr("Restart Inkline?"),
                        tr("Inkline {version} is installed. Restart Inkline to use it.").format(version=version))
        restart = box.addButton(tr("Restart now"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("Later"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(restart)
        box.exec()
        if box.clickedButton() is restart and self.window.close():
            subprocess.Popen(updater.relaunch_command(self.kind), close_fds=True, start_new_session=True)
            QApplication.quit()
