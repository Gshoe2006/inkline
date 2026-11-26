"""Python's garbage collector, run only on the window's thread.

Inkline draws previews, page thumbnails and recovery copies on worker threads. Python collects cyclic garbage on
whichever thread happens to be allocating, so a worker could be the one to free a closed window's widgets, which
Qt objects must never be (the test run crashed that way, in a thumbnail thread). So automatic collection is
turned off and a timer on the UI thread collects every few seconds instead; reference counting still frees almost
everything at once, as before.
"""

import gc

from PySide6.QtCore import QTimer

EVERY_MS = 2000


def install(app, every_ms=EVERY_MS):
    """Collect on app's thread only, every every_ms; returns the timer (kept on the app so it lives as long)."""
    gc.disable()
    timer = QTimer(app)
    timer.setInterval(every_ms)
    timer.timeout.connect(collect)
    timer.start()
    app.aboutToQuit.connect(collect)
    app._inkline_gc_timer = timer
    return timer


def collect():
    gc.collect()
