"""Print on Android: Qt's print dialog isn't there, so Inkline writes the job as a PDF (as Save PDF does) and hands it
to Android's own print service, whose dialog chooses a printer (Wi-Fi and Mopria printers, a maker's plugin) or Save
as PDF. The Java side is packaging/android/java/io/github/gshoe2006/inkline/PdfPrint.java, reached through pyjnius.
"""

import os
import sys
import tempfile

JAVA_CLASS = "io.github.gshoe2006.inkline.PdfPrint"
ACTIVITY = "org.kivy.android.PythonActivity"   # python-for-android's activity, which the APK starts


def available(platform=None):
    return (platform or sys.platform) == "android"


def job_path(name):
    """Where the PDF for the print service is written: a folder of the app's own, emptied at each print."""
    folder = os.path.join(tempfile.gettempdir(), "inkline-print")
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        try:
            os.remove(os.path.join(folder, old))
        except OSError:
            pass
    safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in name).strip() or "Inkline"
    return os.path.join(folder, safe + ".pdf")


def print_pdf(path, name, duplex=False, autoclass=None):
    """Open Android's print dialog for the PDF at path (named name). Raises OSError when it can't be reached."""
    print(f"inkline: opening Android's print dialog for {path}")   # python-for-android puts this in logcat
    try:
        if autoclass is None:
            from jnius import autoclass
        activity = autoclass(ACTIVITY).mActivity
        autoclass(JAVA_CLASS).start(activity, path, name, bool(duplex))
    except Exception as e:   # noqa: BLE001 — pyjnius raises its own Java exceptions
        print(f"inkline: Android's print dialog didn't open: {e!r}")
        raise OSError(str(e)) from e
