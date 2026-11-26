import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# One QApplication for the whole run: the engine only needs a QGuiApplication, but the window tests
# need widgets, and Qt allows one application object per process.
from PySide6.QtWidgets import QApplication  # noqa: E402

_APP = QApplication.instance() or QApplication([])

from inkapp import gcguard  # noqa: E402

gcguard.install(_APP)   # as the app does: garbage collected on this thread, never in a worker thread

import pytest  # noqa: E402
from PySide6.QtWidgets import QMessageBox  # noqa: E402


@pytest.fixture(autouse=True)
def _no_modal_questions(monkeypatch):
    """A question box ("Save changes?") would wait forever offscreen: tests that close a window with unsaved work
    get "Don't save". Tests about the question patch it themselves."""
    monkeypatch.setattr(QMessageBox, "exec", lambda _box: QMessageBox.StandardButton.Discard)


@pytest.fixture(autouse=True)
def _no_windows_left():
    """After each test, close and delete every window it opened. Left alive, they pile up through the run, and
    every restyle or palette change repolishes them all: the late tests in a run got minutes slower."""
    yield
    from PySide6.QtCore import QEvent
    for w in _APP.topLevelWidgets():
        w.close()
        w.deleteLater()
    _APP.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)
    _APP.processEvents()
    gcguard.collect()   # what the closed windows left in cycles, freed here, on the UI thread


def settle(window, timeout=20):
    """Wait until the window's preview has been drawn and shown, and its recovery copy written: a fixed wait
    passes on a quiet machine and fails on a busy one (the result reaches the window after the worker is idle)."""
    import time
    end = time.time() + timeout
    while time.time() < end:
        _APP.processEvents()
        keeper = getattr(window, "keeper", None)
        if window.preview_settled and (keeper is None or keeper.idle):
            _APP.processEvents()
            return
        time.sleep(0.01)
    raise AssertionError("the window didn't settle")
