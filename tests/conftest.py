import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# One QApplication for the whole run: the engine only needs a QGuiApplication, but the window tests
# need widgets, and Qt allows one application object per process.
from PySide6.QtWidgets import QApplication  # noqa: E402

_APP = QApplication.instance() or QApplication([])

import pytest  # noqa: E402
from PySide6.QtWidgets import QMessageBox  # noqa: E402


@pytest.fixture(autouse=True)
def _no_modal_questions(monkeypatch):
    """A question box ("Save changes?") would wait forever offscreen: tests that close a window with unsaved work
    get "Don't save". Tests about the question patch it themselves."""
    monkeypatch.setattr(QMessageBox, "exec", lambda _box: QMessageBox.StandardButton.Discard)
