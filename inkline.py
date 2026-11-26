#!/usr/bin/env python3
"""Inkline: photos to, or generated, black & white images for printing.

Starts the native window (inkapp) over the drawing engine (inkengine). No browser engine: 3.0 draws
everything with Qt and Python.

    python3 inkline.py                     the app
    python3 inkline.py FILE.inkline        the app, with that project open
    python3 inkline.py --selftest DIR      headless check: writes every kind of output into DIR
    python3 inkline.py --version           prints the version
    python3 inkline.py --check-updates     no window: looks for a new version and says so in a notification
                                           (what Help → Check for updates automatically runs while Inkline is closed)
    python3 inkline.py --update            the app, with its update box open (that notification's button)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def app_version():
    """The VERSION file shipped next to this script (installed by both installers), or "dev"."""
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "dev"
    except OSError:
        return "dev"


def startup_project(args):
    """The project to open at start: the first .inkline file named (a double-click in the file manager runs
    `inkline FILE`), or None."""
    return next((a for a in args if a.lower().endswith(".inkline") and not a.startswith("-")), None)


def main():
    if sys.stdout is None:   # the Windows app has no console: messages (the self-test's) go nowhere, not to a crash
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "--version":   # what this copy is, and that it finds its own files
        print(f"Inkline {app_version()}")
        return
    if os.name == "nt":      # its own taskbar button and icon on Windows, not Python's
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Gshoe2006.Inkline")
        except (AttributeError, OSError):
            pass
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtWidgets import QApplication

    QApplication.setApplicationName("Inkline")
    QGuiApplication.setDesktopFileName(os.environ.get("FLATPAK_ID") or "inkline")   # a Flatpak names it by its app ID
    app = QApplication(sys.argv)
    icon = os.path.join(HERE, "inkline.svg")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        from inkapp import selftest
        sys.exit(selftest.main(sys.argv[2]))
    from inkapp import config, theme
    from inkengine import i18n
    from PySide6.QtCore import QLocale
    # the language: View → Language's choice, else the system's (Spanish if it's Spanish), before any window is built
    chosen = config.read("preferences.json").get("language")
    i18n.set_language(chosen if chosen in i18n.LANGUAGES else i18n.system_language(QLocale.system().name()))
    if i18n.LANG != "en":   # Qt's own words too (Save and Cancel buttons, a text field's right-click menu)
        from PySide6.QtCore import QLibraryInfo, QTranslator
        qt_words = QTranslator(app)
        if qt_words.load(f"qtbase_{i18n.LANG}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(qt_words)
    if "--check-updates" in sys.argv[1:]:
        from inkapp import update_check
        sys.exit(update_check.main(app_version()))
    from inkapp.window import Window
    theme.remember_desktop(app)   # the desktop's own look, for View → Use my desktop's style
    prefs = config.read("preferences.json")
    theme.DESKTOP["on"] = bool(theme.desktop_style_name()) and prefs.get("desktop_style") is True
    theme.restore(prefs)   # Edit → Settings → Appearance
    theme.apply(app)
    win = Window(app_version())
    win.show()
    recovered = win.offer_recovery()   # work from a session that closed without saving, if there is any
    path = startup_project(sys.argv[1:])
    if not recovered and not path:
        win.offer_whats_new()          # the first start after an update (not when opening a project): what's changed
        win.offer_tour()               # the first start of 6.0: a short tour of the window
        win.updates.at_start()   # ask once whether to check for updates; then at most once a day, in the background
    if path and not recovered:   # recovered work isn't put aside for the project named: it can be opened next
        win.open_project(path)
    if "--update" in sys.argv[1:]:   # from the update notification's button
        win.updates.check(asked=True)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
