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


def app_version():
    """The VERSION file shipped next to this script (installed by both installers), or "dev"."""
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "dev"
    except OSError:
        return "dev"


APP_VERSION = app_version()
def config_dir():
    """Where saved presets live: $INKLINE_CONFIG_DIR (used by the self-test), else ~/.config/inkline."""
    return os.environ.get("INKLINE_CONFIG_DIR") or os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "inkline")


def read_config(name):
    """A JSON object from the config folder, or {} if it's missing or unreadable."""
    try:
        with open(os.path.join(config_dir(), name), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_config(name, payload, what):
    """Write a JSON object to the config folder atomically (temp file + rename). Returns "ok" or a message."""
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            return f"{what} weren't in the expected format."
        os.makedirs(config_dir(), exist_ok=True)
        path = os.path.join(config_dir(), name)
        with open(path + ".tmp", "w", encoding="utf-8") as f:   # a crash never leaves half a file
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(path + ".tmp", path)
        return "ok"
    except (OSError, ValueError):
        return f"Couldn't save {what.lower()} to {config_dir()}. Check the folder permissions."


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

    def __init__(self, window, test_mode=False, remember=True):
        super().__init__()
        self.window = window
        self.remember = remember
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

    @Slot(result=str)
    def version(self):
        return APP_VERSION

    # --- presets, kept as JSON in the config folder ---
    @Slot(result=str)
    def loadPresets(self):
        return json.dumps(read_config("presets.json"))

    @Slot(str, result=str)
    def savePresets(self, payload):
        return write_config("presets.json", payload, "Presets")

    # --- last settings, restored at startup (never during the self-test, whose output must not depend on them) ---
    @Slot(result=str)
    def loadLastSettings(self):
        return json.dumps(read_config("last-settings.json")) if self.remember else "{}"

    @Slot(str, result=str)
    def saveLastSettings(self, payload):
        return write_config("last-settings.json", payload, "Settings") if self.remember else "ok"

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
            if job.get("duplex") == "short":   # fold-and-staple books: double-sided, flipping on the short edge
                device.setDuplex(QPrinter.DuplexMode.DuplexShortSide)
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
    """Used by the self-test so JavaScript errors show up in the terminal, and count as failures."""
    errors = []

    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"js[{level.name}] line {line}: {message}")
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            ConsolePage.errors.append(f"line {line}: {message}")


class Window(QMainWindow):
    def __init__(self, test_mode=False, remember=True):
        super().__init__()
        self.setWindowTitle(f"Inkline {APP_VERSION}")
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

        self.bridge = Bridge(self, test_mode, remember)
        self.channel = QWebChannel(self)
        self.channel.registerObject("inkline", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.view.load(QUrl.fromLocalFile(os.path.join(HERE, "index.html")))


def selftest(win, outdir):
    """Headless check: render each generator, export PNG + PDF + SVG, booklets, posters and a photo book
    without dialogs, then exit 0 if every step worked and 1 if any failed (CI relies on that)."""
    os.makedirs(outdir, exist_ok=True)
    page = win.view.page()
    fails = []

    def fail(why):
        print(f"selftest: FAIL {why}")
        fails.append(why)

    def finish():
        fails.extend(f"JavaScript error {e}" for e in ConsolePage.errors)
        if fails:
            print(f"selftest: {len(fails)} failure(s)")
            for f in fails:
                print(f"  - {f}")
        print("selftest: done" if not fails else "selftest: FAILED")
        QApplication.instance().exit(1 if fails else 0)

    # a hung step (e.g. a promise that never resolves) must still end the run
    QTimer.singleShot(8 * 60 * 1000, lambda: (fail("whole run took longer than 8 minutes"), finish()))
    steps = ["mandala", "maze", "truchet", "contour", "flow", "dots", "sudoku", "name", "convert", "testpage"]

    def run(i=0):
        if i == len(steps):
            tone_check()
            return
        name = steps[i]
        js = "$('testpage').checked = false; "
        if name == "testpage":
            js += "setMode('make'); $('testpage').checked = true; syncOutputs();"
        else:
            js += "setMode('convert');" if name == "convert" else f"setMode('make'); $('gen').value='{name}';"
        if name == "name":   # outlined text over a real pattern, so the SVG check sees both
            js += " $('nameText').value='Inkline 2.2'; $('nameBg').value='flow';"
        js += " 0"
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
        if (img.width(), img.height()) != (2550, 3300):
            fail(f"{name}: expected a 2550x3300 page, got {img.width()}x{img.height()}")
        if name in ("convert", "testpage"):   # pixels only: no SVG
            run(i + 1)
            return

        def wrote_svg(svg):
            if not svg or "<path" not in svg:
                fail(f"{name}: SVG export was empty")
            with open(os.path.join(outdir, f"{name}.svg"), "w", encoding="utf-8") as f:
                f.write(svg or "")
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
                if not r:
                    fail(f"{label}: no result after 2 minutes")
                elif not str(r).startswith("Saved"):
                    fail(f"{label}: {r}")
                then()
            page.runJavaScript("window.__job || null", got)
        page.runJavaScript("window.__job = null; " + start_js + "; 0", lambda _r: QTimer.singleShot(500, poll))

    def tone_check():
        """The test page's grey ramps must match their grey level: catches halftone or dither tone drift."""
        js = r"""(() => {
          $('testpage').checked = true; syncOutputs(); render();
          const g = geometry('portrait'), I = g.dpi, d = pctx.getImageData(0, 0, g.W, g.H).data;
          const labelX = 0.75 * I + 1.75 * I, rampW = g.W - 1.5 * I - 1.75 * I, worst = {};
          let y = 0.75 * I + 0.55 * I + 0.5 * I + 0.6 * I + 2 * I + 0.35 * I + 0.12 * I;
          for (const name of ['Smooth', 'Crisp', 'Pattern', 'Halftone']) {
            let w = 0;
            for (let k = 1; k < 9; k++) {   // inner slices; the ends are pure white/black
              let ink = 0, n = 0; const xa = Math.round(labelX + rampW * k / 10 + 4), xb = Math.round(labelX + rampW * (k + 1) / 10 - 4);
              for (let yy = Math.round(y + 8); yy < y + 0.36 * I - 8; yy += 2) for (let xx = xa; xx < xb; xx += 2) { ink += d[(yy * g.W + xx) * 4] < 128; n++; }
              w = Math.max(w, Math.abs(ink / n * 100 - (k * 10 + 5)));
            }
            worst[name] = Math.round(w); y += 0.36 * I + 0.09 * I;
          }
          $('testpage').checked = false; syncOutputs();
          const bad = ['Smooth', 'Pattern', 'Halftone'].filter(n => worst[n] > 6);   // Crisp (Atkinson) adds contrast on purpose
          return (bad.length ? 'BAD ' : 'OK ') + Object.entries(worst).map(([n, w]) => `${n} ±${w}`).join(', ');
        })()"""

        def got(r):
            print(f"selftest: tone check -> {r}")
            if not str(r).startswith("OK"):
                fail(f"tone check: {r}")
            sudoku_proof()
        page.runJavaScript(js, got)

    def sudoku_proof():
        """Every generated sudoku must be a valid grid with exactly one solution, reproducible from its seed."""
        js = r"""(() => {
          const valid = s => { for (let k = 0; k < 9; k++) { const a = new Set(), b = new Set(), c = new Set();
            for (let j = 0; j < 9; j++) { a.add(s[k*9+j]); b.add(s[j*9+k]); c.add(s[(((k/3)|0)*3 + ((j/3)|0))*9 + (k%3)*3 + j%3]); }
            for (const t of [a, b, c]) if (t.size !== 9 || t.has(0)) return false; } return true; };
          const bad = [], clues = [];
          for (const c of [1, 5, 10]) for (const seed of [7, 8, 9]) {
            const p = makeSudoku(mulberry32(seed), c), q = makeSudoku(mulberry32(seed), c);
            if (!valid(p.solution)) bad.push(`c${c}/${seed} invalid grid`);
            if (!p.puzzle.every((v, i) => !v || v === p.solution[i])) bad.push(`c${c}/${seed} givens disagree`);
            if (countSolutions(p.puzzle.slice(), 2) !== 1) bad.push(`c${c}/${seed} not exactly one solution`);
            if (p.puzzle.join() !== q.puzzle.join()) bad.push(`c${c}/${seed} not reproducible`);
            clues.push(p.clues);
          }
          return bad.length ? "BAD " + bad.join("; ") : "OK 9 puzzles, clues " + clues.join(",");
        })()"""

        def got(r):
            print(f"selftest: sudoku proof -> {r}")
            if not str(r).startswith("OK"):
                fail(f"sudoku proof: {r}")
            booklet()
        page.runJavaScript(js, got)

    def booklet():
        path = os.path.join(outdir, "booklet.pdf")
        js = ("setMode('make'); $('gen').value='maze'; $('booklet').checked=true; $('pages').value='6';"
              "$('title').value='Rainy Day Mazes'; $('nameLine').checked=true; syncOutputs();"
              f"runBook('pdf', {json.dumps(path)}).then(r => {{ window.__job = r; }})")
        wait_for(js, "booklet", answers_svg)

    def answers_svg():
        def wrote(svg):
            if not svg or "<path" not in svg:
                fail("answers page: SVG export was empty")
            with open(os.path.join(outdir, "answers.svg"), "w", encoding="utf-8") as f:
                f.write(svg or "")
            fold_booklet()
        page.runJavaScript("S.bookPage = 999; render(); buildSvg()", wrote)

    def fold_booklet():
        """Fold-and-staple order: the formula must match a simulated fold for every book size, then the
        same 9-page booklet is saved as a folded book (12 pages with blanks -> 3 sheets -> 6 landscape sides)."""
        proof = r"""(() => {
          for (let n = 4; n <= 40; n += 4) {
            const sides = foldOrder(n), read = [];
            for (let s = 0; s < n / 4; s++) read.push(sides[2 * s].right, sides[2 * s + 1].left);
            for (let s = n / 4 - 1; s >= 0; s--) read.push(sides[2 * s + 1].right, sides[2 * s].left);
            if (read.join() !== [...Array(n).keys()].join()) return "BAD reading order for " + n + " pages: " + read.map(i => i + 1).join(",");
          }
          return "OK books of 4-40 pages read in order";
        })()"""

        def proved(r):
            print(f"selftest: fold proof -> {r}")
            if not str(r).startswith("OK"):
                fail(f"fold proof: {r}")
            path = os.path.join(outdir, "booklet-fold.pdf")
            js = ("$('fold').checked = true; $('fold').dispatchEvent(new Event('input')); syncOutputs();"
                  f"runBook('pdf', {json.dumps(path)}).then(r => {{ $('fold').checked = false; syncOutputs(); window.__job = r; }})")
            wait_for(js, "fold booklet", poster_design)
        page.runJavaScript(proof, proved)

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
                photo_book()))
        wait_for(js, "poster photo 3x3", preview)

    def photo_book():
        # three photos: the sample twice (the second zoomed and rotated) plus a drawn one, then a 4-page book
        path = os.path.join(outdir, "photobook.pdf")
        js = ("$('poster').checked=false; $('photobook').checked=true; $('photobook').dispatchEvent(new Event('input'));"
              "$('title').value='Photo book test'; $('style').value='line'; syncOutputs();"
              "(async () => { const c = document.createElement('canvas'); c.width = 600; c.height = 800; const x = c.getContext('2d');"
              "  x.fillStyle = '#fff'; x.fillRect(0, 0, 600, 800); x.fillStyle = '#222'; x.beginPath(); x.arc(300, 400, 200, 0, 7); x.fill();"
              "  const b = await new Promise(r => c.toBlob(r)); await addPhotos([{ blob: b, name: 'circle.png' }], true);"
              "  loadSample(); for (let i = 0; i < 30 && S.photos.length < 3; i++) await new Promise(r => setTimeout(r, 100));"
              "  selectPhoto(2); S.rot = 90; $('zoom').value = 180; selectPhoto(0);"
              f"  window.__job = await runPhotoBook('pdf', {json.dumps(path)}); }})()")
        wait_for(js, "photo book", finish)

    def start():   # a fixed design seed makes every run's output identical, so runs can be compared
        page.runJavaScript("S.seed = 20261117; syncOutputs(); 0", lambda _r: run())

    win.view.loadFinished.connect(lambda ok: QTimer.singleShot(800, start) if ok else (fail("index.html didn't load"), finish()))


def main():
    QApplication.setApplicationName("Inkline")
    QGuiApplication.setDesktopFileName("inkline")
    app = QApplication(sys.argv)
    icon = os.path.join(HERE, "inkline.svg")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    testing = len(sys.argv) > 2 and sys.argv[1] == "--selftest"
    win = Window(test_mode=testing, remember=not testing)
    if testing:
        selftest(win, sys.argv[2])
    else:
        win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
