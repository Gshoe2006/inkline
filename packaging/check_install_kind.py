#!/usr/bin/env python3
"""Checks an installed copy of Inkline says how it was installed, as Help → Check for updates goes by.

Usage: python3 packaging/check_install_kind.py APP_DIR KIND
APP_DIR is where inkline.py was installed (/usr/share/inkline, ~/.local/share/inkline…); KIND is what it should
say (arch, deb, run-user, run-system). Runs that copy's own updater code, so it needs no Qt.
"""
import os
import sys

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    root, want = os.path.abspath(sys.argv[1]), sys.argv[2]
    sys.path.insert(0, root)
    from inkapp import updater   # the installed copy's, not this checkout's
    if os.path.dirname(os.path.dirname(os.path.abspath(updater.__file__))) != root:
        sys.exit(f"check_install_kind: imported the updater from {updater.__file__}, not {root}")
    said = updater.install_kind(env={}, frozen=False, root=root)
    if said != want:
        sys.exit(f"check_install_kind: {root} says it was installed as '{said}', expected '{want}'")
    print(f"check_install_kind: {root} is '{said}'")
