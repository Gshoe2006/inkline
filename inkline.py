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
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

HERE = os.path.dirname(os.path.abspath(__file__))
def config_dir():
    """Where saved presets live: $INKLINE_CONFIG_DIR (used by the self-test), else ~/.config/inkline."""
    return os.environ.get("INKLINE_CONFIG_DIR") or os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "inkline")


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

    def __init__(self, window, test_mode=False):
        super().__init__()
        self.window = window
        self.test_mode = test_mode     # only the headless self-test may pass a save path from the page
        self.book = None
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
        if job["kind"] == "svg":
            path = self._ask_path("Save SVG", job["name"], "svg", "SVG vector image (*.svg)")
            if not path:
                return "Save cancelled."
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(job["svg"])
            except OSError:
                return f"Couldn't write {path}. Check the folder permissions."
            return f"Saved {os.path.basename(path)}"
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

    # --- presets, kept as JSON in the config folder ---
    @Slot(result=str)
    def loadPresets(self):
        try:
            with open(os.path.join(config_dir(), "presets.json"), encoding="utf-8") as f:
                data = json.load(f)
            return json.dumps(data if isinstance(data, dict) else {})
        except (OSError, ValueError):
            return "{}"

    @Slot(str, result=str)
    def savePresets(self, payload):
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                return "Presets weren't in the expected format."
            os.makedirs(config_dir(), exist_ok=True)
            path = os.path.join(config_dir(), "presets.json")
            with open(path + ".tmp", "w", encoding="utf-8") as f:   # write then rename, so a crash never leaves half a file
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(path + ".tmp", path)
            return "ok"
        except (OSError, ValueError):
            return f"Couldn't save presets to {config_dir()}. Check the folder permissions."

    # --- multi-page booklets: the page streams pages one at a time between begin and end ---
    @Slot(str, result=str)
    def bookBegin(self, payload):
        if self.book:
            return "A booklet is already being made. Wait for it to finish."
        job = json.loads(payload)
        if job["kind"] == "pdf":
            path = job.get("path") if self.test_mode and job.get("path") else \
                self._ask_path(f"Save {job.get('label', 'booklet')} PDF", job["name"], "pdf", "PDF document (*.pdf)")
            if not path:
                return "Save cancelled."
            device = QPdfWriter(path)
            device.setPageLayout(page_layout(job))
            device.setResolution(job["dpi"])
            device.setTitle(job["name"])
            device.setCreator("Inkline")
            painter = QPainter(device)
            target = lambda: QRect(0, 0, device.width(), device.height())
            done = f"Saved {job['count']}-page {job.get('label', 'booklet')} as {os.path.basename(path)}"
        elif job["kind"] == "print":
            device = QPrinter(QPrinter.PrinterMode.HighResolution)
            device.setPageLayout(page_layout(job))
            device.setFullPage(True)
            device.setDocName(job["name"])
            device.setColorMode(QPrinter.ColorMode.GrayScale)
            if QPrintDialog(device, self.window).exec() != QPrintDialog.DialogCode.Accepted:
                return "Print cancelled."
            painter = QPainter(device)
            target = painter.viewport
            done = f"Sent {job['count']} {'sheets' if job.get('label') == 'poster' else 'pages'} to the printer."
        else:
            return "Unknown booklet request."
        if not painter.isActive():
            return "Couldn't start the booklet. Check the folder permissions or the printer."
        self.book = {"device": device, "painter": painter, "target": target, "first": True, "done": done}
        return "ok"

    @Slot(str, result=str)
    def bookPage(self, b64):
        if not self.book:
            return "No booklet in progress."
        img = QImage.fromData(base64.b64decode(b64), "PNG")
        if img.isNull():
            return "A page couldn't be prepared."
        b = self.book
        if not b["first"] and not b["device"].newPage():
            return "The printer or PDF stopped accepting pages."
        b["first"] = False
        draw_fitted(b["painter"], img, b["target"]())
        return "ok"

    @Slot(result=str)
    def bookEnd(self):
        if not self.book:
            return "No booklet in progress."
        b, self.book = self.book, None
        return b["done"] if b["painter"].end() else "The booklet couldn't be finished."

    @Slot()
    def bookAbort(self):
        if self.book:
            if isinstance(self.book["device"], QPrinter):
                self.book["device"].abort()
            self.book["painter"].end()
            self.book = None


class ConsolePage(QWebEnginePage):
    """Used by the self-test so JavaScript errors show up in the terminal."""

    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"js[{level.name}] line {line}: {message}")


class Window(QMainWindow):
    def __init__(self, test_mode=False):
        super().__init__()
        self.setWindowTitle("Inkline")
        self.resize(1280, 860)
        self.view = QWebEngineView(self)
        if test_mode:
            self.view.setPage(ConsolePage(self.view))
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

        self.bridge = Bridge(self, test_mode)
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
            booklet()
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
        if name == "convert":
            run(i + 1)
            return

        def wrote_svg(svg):
            with open(os.path.join(outdir, f"{name}.svg"), "w", encoding="utf-8") as f:
                f.write(svg)
            run(i + 1)
        page.runJavaScript("buildSvg()", wrote_svg)

    def wait_for(start_js, label, then):
        """Run start_js (which sets window.__job when done), poll until it finishes, then call then()."""
        tries = [0]

        def poll():
            def got(r):
                if not r and tries[0] < 240:      # Qt returns JS null as "" (not None) while it renders
                    tries[0] += 1
                    QTimer.singleShot(500, poll)
                    return
                print(f"selftest: {label} -> {r}")
                then()
            page.runJavaScript("window.__job || null", got)
        page.runJavaScript("window.__job = null; " + start_js + "; 0", lambda _r: QTimer.singleShot(500, poll))

    def booklet():
        path = os.path.join(outdir, "booklet.pdf")
        js = ("setMode('make'); $('gen').value='maze'; $('booklet').checked=true; $('pages').value='6';"
              "$('title').value='Rainy Day Mazes'; $('nameLine').checked=true; syncOutputs();"
              f"runBook('pdf', {json.dumps(path)}).then(r => {{ window.__job = r; }})")
        wait_for(js, "booklet", answers_svg)

    def answers_svg():
        def wrote(svg):
            with open(os.path.join(outdir, "answers.svg"), "w", encoding="utf-8") as f:
                f.write(svg)
            poster_design()
        page.runJavaScript("S.bookPage = 999; render(); buildSvg()", wrote)

    def poster_design():
        path = os.path.join(outdir, "poster-mandala-2x2.pdf")
        js = ("setMode('make'); $('title').value=''; $('nameLine').checked=false; $('gen').value='mandala';"
              "$('poster').checked=true; $('poster').dispatchEvent(new Event('input')); $('grid').value='2x2'; syncOutputs(); render();"
              f"runPoster('pdf', {json.dumps(path)}).then(r => {{ window.__job = r; }})")
        wait_for(js, "poster mandala 2x2", poster_photo)

    def poster_photo():
        path = os.path.join(outdir, "poster-photo-3x3.pdf")
        js = ("setMode('convert'); $('style').value='fs'; $('grid').value='3x3'; syncOutputs(); render();"
              f"runPoster('pdf', {json.dumps(path)}).then(r => {{ window.__job = r; }})")

        def preview():
            page.runJavaScript("render(); $('page').toDataURL('image/png').split(',')[1]", lambda b64: (
                open(os.path.join(outdir, "poster-preview.png"), "wb").write(base64.b64decode(b64)),
                print("selftest: done"), QApplication.quit()))
        wait_for(js, "poster photo 3x3", preview)

    win.view.loadFinished.connect(lambda ok: QTimer.singleShot(800, run) if ok else (print("selftest: load failed"), QApplication.quit()))


def main():
    QApplication.setApplicationName("Inkline")
    QGuiApplication.setDesktopFileName("inkline")
    app = QApplication(sys.argv)
    icon = os.path.join(HERE, "inkline.svg")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    testing = len(sys.argv) > 2 and sys.argv[1] == "--selftest"
    win = Window(test_mode=testing)
    if testing:
        selftest(win, sys.argv[2])
    else:
        win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
