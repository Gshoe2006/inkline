"""Screenshots for Google Play, on the Android build (staged as inkline_screens.py; main.py installs it when the app's
private folder has a file named "inkline-screens"): Inkline opens with fresh settings (no first-start questions),
then shows each of STEPS in turn. For each it writes the step's name to screens/now and waits until the screenshot
script (screenshots.sh, over adb) writes the same name to screens/ack, or WAIT ms pass; "done" when all are shown.
"""

import json
import os
import time

SETTLE = 4000    # ms for a page to be drawn after it's shown
WAIT = 90000     # ms to wait for the screenshot before going on without it
POLL = 500

# (name, what to do to the window): Create with the mandala Inkline opens on, the preview (its own page on a
# phone), Booklet, Print's options, then Print itself, which opens Android's print dialog
STEPS = [
    ("1-create", lambda w: w._rail_key("make")),
    ("2-preview", lambda w: w._bottom_chosen("preview")),
    ("3-booklet", lambda w: w._rail_key("booklet")),
    ("4-print-options", lambda w: w._rail_key("print")),
    ("5-print-dialog", lambda w: w.print_()),
]


def fresh_settings(folder):
    """A settings folder of its own, set up as if the questions Inkline asks on a first start were answered."""
    cfg = os.path.join(folder, "config")
    os.makedirs(cfg, exist_ok=True)
    with open(os.path.join(cfg, "preferences.json"), "w", encoding="utf-8") as f:
        json.dump({"tour_seen": True, "update_check": False}, f)
    os.environ["INKLINE_CONFIG_DIR"] = cfg
    return cfg


def _write(path, text):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    os.replace(path + ".tmp", path)


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


class Driver:
    def __init__(self, window, folder, steps=None, settle=SETTLE, wait=WAIT, poll=POLL):
        self.w, self.folder = window, folder
        self.steps = STEPS if steps is None else steps
        self.settle, self.wait, self.poll = settle, wait, poll
        self.i = 0
        self.deadline = 0
        self.shown = []   # (name, whether the screenshot was acknowledged)
        os.makedirs(folder, exist_ok=True)
        for f in ("now", "ack"):
            if os.path.exists(os.path.join(folder, f)):
                os.remove(os.path.join(folder, f))

    def start(self):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(self.settle, self._next)

    def _next(self):
        from PySide6.QtCore import QTimer
        if self.i >= len(self.steps):
            _write(os.path.join(self.folder, "now"), "done")
            return
        name, act = self.steps[self.i]
        try:
            act(self.w)
        except Exception as e:   # noqa: BLE001 - a step that fails still gets its screenshot, and the rest go on
            print(f"inkline_screens: {name}: {e}")
        QTimer.singleShot(self.settle, self._announce)

    def _announce(self):
        _write(os.path.join(self.folder, "now"), self.steps[self.i][0])
        self.deadline = time.monotonic() + self.wait / 1000
        self._poll()

    def _poll(self):
        from PySide6.QtCore import QTimer
        name = self.steps[self.i][0]
        acked = _read(os.path.join(self.folder, "ack")) == name
        if acked or time.monotonic() > self.deadline:
            self.shown.append((name, acked))
            self.i += 1
            self._next()
        else:
            QTimer.singleShot(self.poll, self._poll)


def install(folder):
    """Fresh settings, then the driver starts once Inkline's window is first shown."""
    fresh_settings(folder)
    from inkapp import window
    show = window.Window.show
    drivers = []

    def show_then_drive(self):
        show(self)
        if not drivers:
            drivers.append(Driver(self, folder))
            drivers[0].start()

    window.Window.show = show_then_drive
    return drivers
