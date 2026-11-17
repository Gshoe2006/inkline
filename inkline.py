#!/usr/bin/env python3
"""Inkline — a Linux desktop app that converts photos to, or generates, black & white images for printing.

The image engine lives in index.html (canvas + JavaScript). This Qt shell hosts it and adds what a
web page can't do on its own: native Save dialogs, PDF output at the true paper size, and printing.
"""
import base64
import json
import os
import sys

from PySide6.QtCore import QFile, QIODevice, QMarginsF, QObject, QRect, QTimer, QUrl, Slot
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_IDS = {"letter": QPageSize.PageSizeId.Letter, "a4": QPageSize.PageSizeId.A4}


def page_layout(job):
    orient = QPageLayout.Orientation.Landscape if job["orient"] == "landscape" else QPageLayout.Orientation.Portrait
    return QPageLayout(QPageSize(PAPER_IDS[job["paper"]]), orient, QMarginsF(0, 0, 0, 0))


def draw_fitted(painter, img, target):
    """Draw img into target rect, keeping its aspect ratio (the image already includes the margins)."""
    s = min(target.width() / img.width(), target.height() / img.height())
    w, h = int(img.width() * s), int(img.height() * s)
    painter.drawImage(QRect(target.x() + (target.width() - w) // 2, target.y() + (target.height() - h) // 2, w, h), img)


def write_png(img, path, dpi):
    dpm = round(dpi / 0.0254)          # store the DPI so other apps print it at the right size
    img.setDotsPerMeterX(dpm)
    img.setDotsPerMeterY(dpm)
    return img.save(path, "PNG")


def write_pdf(img, path, job):
    writer = QPdfWriter(path)
    writer.setPageLayout(page_layout(job))
    writer.setResolution(job["dpi"])
    writer.setTitle(job["name"])
    writer.setCreator("Inkline")
    painter = QPainter(writer)
    draw_fitted(painter, img, QRect(0, 0, writer.width(), writer.height()))
    return painter.end()


class Bridge(QObject):
    """Exposed to the page as `inkline` through QWebChannel."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.last_dir = os.path.expanduser("~/Pictures") if os.path.isdir(os.path.expanduser("~/Pictures")) else os.path.expanduser("~")

    def _ask_path(self, title, name, ext, filt):
        path, _ = QFileDialog.getSaveFileName(self.window, title, os.path.join(self.last_dir, f"{name}.{ext}"), filt)
        if not path:
            return None
        if not path.lower().endswith("." + ext):
            path += "." + ext
        self.last_dir = os.path.dirname(path)
        return path

    @Slot(str, result=str)
    def request(self, payload):
        job = json.loads(payload)
        img = QImage.fromData(base64.b64decode(job["png"]), "PNG")
        if img.isNull():
            return "The image couldn't be prepared. Try again."
        kind = job["kind"]
        if kind == "png":
            path = self._ask_path("Save PNG", job["name"], "png", "PNG image (*.png)")
            if not path:
                return "Save cancelled."
            return f"Saved {os.path.basename(path)}" if write_png(img, path, job["dpi"]) else f"Couldn't write {path}. Check the folder permissions."
        if kind == "pdf":
            path = self._ask_path("Save PDF", job["name"], "pdf", "PDF document (*.pdf)")
            if not path:
                return "Save cancelled."
            return f"Saved {os.path.basename(path)}" if write_pdf(img, path, job) else f"Couldn't write {path}. Check the folder permissions."
        if kind == "print":
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPageLayout(page_layout(job))
            printer.setFullPage(True)
            printer.setDocName(job["name"])
            printer.setColorMode(QPrinter.ColorMode.GrayScale)
            dlg = QPrintDialog(printer, self.window)
            if dlg.exec() != QPrintDialog.DialogCode.Accepted:
                return "Print cancelled."
            painter = QPainter(printer)
            draw_fitted(painter, img, painter.viewport())
            ok = painter.end()
            return "Sent to the printer." if ok else "The printer didn't accept the job. Check that it's connected."
        return "Unknown request."


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inkline")
        self.resize(1280, 860)
        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        # Make qwebchannel.js available before the page's own script runs.
        f = QFile(":/qtwebchannel/qwebchannel.js")
        if f.open(QIODevice.OpenModeFlag.ReadOnly):
            script = QWebEngineScript()
            script.setSourceCode(bytes(f.readAll()).decode())
            script.setName("qwebchannel")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            self.view.page().scripts().insert(script)
            f.close()

        self.bridge = Bridge(self)
        self.channel = QWebChannel(self)
        self.channel.registerObject("inkline", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.view.load(QUrl.fromLocalFile(os.path.join(HERE, "index.html")))


def selftest(win, outdir):
    """Headless check: render each generator, export PNG + PDF without dialogs, then quit."""
    os.makedirs(outdir, exist_ok=True)
    page = win.view.page()
    steps = ["mandala", "maze", "truchet", "contour", "flow", "convert"]

    def run(i=0):
        if i == len(steps):
            print("selftest: done")
            QApplication.quit()
            return
        name = steps[i]
        js = ("setMode('convert');" if name == "convert" else f"setMode('make'); $('gen').value='{name}';") + " 0"
        page.runJavaScript(js, lambda _r: QTimer.singleShot(1500, lambda: grab(i)))

    def grab(i):
        name = steps[i]
        page.runJavaScript("render(); job('pdf')", lambda payload: save(i, name, payload))

    def save(i, name, payload):
        job = json.loads(payload)
        img = QImage.fromData(base64.b64decode(job["png"]), "PNG")
        write_png(img, os.path.join(outdir, f"{name}.png"), job["dpi"])
        write_pdf(img, os.path.join(outdir, f"{name}.pdf"), job)
        print(f"selftest: {name} {img.width()}x{img.height()}")
        run(i + 1)

    win.view.loadFinished.connect(lambda ok: QTimer.singleShot(800, run) if ok else (print("selftest: load failed"), QApplication.quit()))


def main():
    QApplication.setApplicationName("Inkline")
    QGuiApplication.setDesktopFileName("inkline")
    app = QApplication(sys.argv)
    icon = os.path.join(HERE, "inkline.svg")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    win = Window()
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        selftest(win, sys.argv[2])
    else:
        win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
