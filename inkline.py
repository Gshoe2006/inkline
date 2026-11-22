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
    from inkapp import theme
    from inkapp.window import Window
    theme.apply(app)
    win = Window(app_version())
    win.show()
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".inkline"):
        win.open_project(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
