#!/usr/bin/env python3
"""Inkline: photos to, or generated, black & white images for printing.

Starts the native window (inkapp) over the drawing engine (inkengine). No browser engine: 3.0 draws
everything with Qt and Python.

    python3 inkline.py                     the app
    python3 inkline.py FILE.inkline        the app, with that project open
    python3 inkline.py --selftest DIR      headless check: writes every kind of output into DIR
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
    from inkapp.window import Window
    theme.remember_desktop(app)   # the desktop's own look, for View → Use my desktop's style
    theme.DESKTOP["on"] = bool(theme.desktop_style_name()) and config.read("preferences.json").get("desktop_style") is True
    theme.apply(app)
    win = Window(app_version())
    win.show()
    recovered = win.offer_recovery()   # work from a session that closed without saving, if there is any
    path = startup_project(sys.argv[1:])
    if not recovered and not path:
        win.offer_whats_new()          # the first start after an update (not when opening a project): what's changed
    if path and not recovered:   # recovered work isn't put aside for the project named: it can be opened next
        win.open_project(path)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
