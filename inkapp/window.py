"""The main window: menu bar, the sidebar on the left, the preview on the right.

Every change draws the preview again (after a short pause, on the renderer's worker) and is remembered
in ~/.config/inkline/last-settings.json, as 2.x did. Print and Save run their pages on a worker too,
with progress in the footer. Messages are 2.x's.
"""

import json
import math
import threading
import uuid
import os
import time
from dataclasses import replace

from PySide6.QtCore import QEvent, QMimeData, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QImage, QKeySequence, QShortcut, QUndoCommand, QUndoStack
from PySide6.QtPrintSupport import QAbstractPrintDialog, QPrintDialog, QPrinter
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSlider, QAbstractSpinBox, QApplication, QComboBox, QDialog,
                               QFileDialog, QHBoxLayout, QInputDialog, QLineEdit, QMainWindow, QMenu, QMenuBar, QMessageBox,
                               QUndoView, QVBoxLayout, QWidget)
from PySide6.QtGui import QPdfWriter

from inkengine import book, photo
from inkengine.page import PAGE_KEYS, Settings, clean_page, design_box, geometry, single_page
from inkengine.patterns import NAMES

from . import config, jobs, project, recovery, theme, whatsnew
from .preview import Preview
from .render import PREVIEW_DPI, Renderer, render_view, view
from .sample import sample_photo
from .sidebar import MARGINS, MAX_BOOK_PAGES, MAX_PHOTOS, Sidebar
from .state import BUILTIN_PRESETS, State, new_seed

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)"
MAX_RECENT = 10      # File → Open recent lists this many photos

# What Edit → Undo says for a change to each setting ("Undo Complexity"); others use the setting's name.
STEP_NAMES = {"gen": "Pattern", "complexity": "Complexity", "weight": "Line weight", "frame": "Border", "cbn": "Colour by number",
              "cbn_colours": "Colours", "seed": "New design", "page_seeds": "New design for this page", "booklet": "Booklet",
              "pages": "Design pages", "ramp": "Get harder", "mix": "Mix every pattern", "cover": "Cover page",
              "page_nums": "Page numbers", "key": "Answer pages", "maze_shape": "Maze shape", "maze_word": "Word or name", "spot_base": "Picture",
              "ws_theme": "Words from", "ws_words": "Your words", "name_text": "Name or word", "name_bg": "Around the letters",
              "mode": "Mode", "style": "Style", "brightness": "Brightness", "contrast": "Contrast", "threshold": "Threshold",
              "dot": "Dot size", "fit": "Placement", "invert": "Invert", "pnono_size": "Squares across",
              "pnono_answer": "Show the answer", "pcbn_colours": "Colours", "photobook": "Photo book", "pcover": "Cover page",
              "ppage_nums": "Page numbers", "title": "Title", "name_line": "Name line", "poster": "Poster", "grid": "Sheets",
              "overlap": "Overlap", "testpage": "Printer test page", "fold": "Fold-and-staple", "paper": "Paper size",
              "orient": "Orientation", "margin": "Margin", "dpi": "Resolution", "page_list": "Pages"}
KEEP_SECONDS = 60     # unsaved work is copied for recovery at most this often
PAGES_MIME = "application/x-inkline-pages"   # booklet pages on the clipboard: {"app": "Inkline", "pages": [...]}
MERGE_SECONDS = 1.5   # changes to the same thing this close together (a slider drag, typing) are one step
BOOKLET_LOOK = ("weight", "frame", "title", "name_line", "paper", "orient", "margin", "fold")   # drawn on every page


class _Snapshot:
    """The part of the state Undo restores: settings, which photos and in what order, and each one's crop.
    Which page is shown and which photo is being cropped aren't edits, so they don't count as changes."""

    def __init__(self, state):
        self.settings = state.settings
        self.photos = list(state.photos)
        self.crops = [(p.rot, p.zoom, p.panx, p.pany) for p in state.photos]
        self.sel = state.sel
        self.book_sel = state.book_sel

    def edits(self):
        """The settings that count as edits. In a booklet built page by page the Design section's top-level
        values only show the selected page (State.mirror), so choosing another page isn't a change."""
        d = self.settings.to_dict()
        s = self.settings
        if s.page_list and s.booklet and s.mode == "make" and not s.poster:
            d = {k: v for k, v in d.items() if k not in PAGE_KEYS or k == "seed"}
        return d

    def same(self, other):
        return (self.edits() == other.edits() and [id(p) for p in self.photos] == [id(p) for p in other.photos]
                and self.crops == other.crops)

    def what(self, before):
        """A name for the change from before to this, for "Undo …"."""
        if self.settings.mode != before.settings.mode:
            return STEP_NAMES["mode"]
        if [id(p) for p in self.photos] != [id(p) for p in before.photos]:
            n, m = len(self.photos), len(before.photos)
            return "Add photos" if n > m else "Remove photo" if n < m else "Move photo"
        if self.crops != before.crops:
            return "Crop"
        a, b = self.settings.to_dict(), before.settings.to_dict()
        changed = [k for k in a if a[k] != b[k]]
        if "page_list" in changed and self.settings.page_list and before.settings.page_list:
            # a page's own setting changed: its top-level copy changed with it, and names the step
            pa, pb = self.settings.page_list, before.settings.page_list
            if len(pa) == len(pb):
                keys = {k for x, y in zip(pa, pb) for k in set(x) | set(y) if x.get(k) != y.get(k)}
                changed = sorted(keys) if keys else changed
        if len(changed) == 1:
            return STEP_NAMES.get(changed[0], changed[0].replace("_", " ").capitalize())
        return "Changes"


class _Step(QUndoCommand):
    """One undo step. gesture is what the change belongs to (a slider held down, one drag of the photo,
    typing in one field): changes in the same gesture are one step however slow. timed steps (a
    slider's arrow keys, the wheel) join when they come within MERGE_SECONDS. Clicks never join."""

    def __init__(self, window, before, after, text, gesture=None, timed=False):
        super().__init__(text)
        self.window, self.before, self.after = window, before, after
        self.gesture, self.timed = gesture, timed
        self.when = time.monotonic()
        self._first = True

    def id(self):
        return hash(self.text()) & 0x7FFFFFFF

    def mergeWith(self, other):
        if other.text() != self.text():
            return False
        if self.gesture is not None and other.gesture == self.gesture:
            pass
        elif not (self.gesture is None and other.gesture is None and self.timed and other.timed
                  and other.when - self.when <= MERGE_SECONDS):
            return False
        self.after, self.when = other.after, other.when
        if self.after.same(self.before):   # back where it started (on and off again): no step at all
            self.setObsolete(True)
        return True

    def redo(self):
        if self._first:      # pushed after the change was made: nothing to do the first time
            self._first = False
            return
        self.window._restore_snapshot(self.after)

    def undo(self):
        self.window._restore_snapshot(self.before)


class Window(QMainWindow):
    status = Signal(str)

    def __init__(self, version="dev", remember=True):
        super().__init__()
        self.version, self.remember = version, remember
        self.setWindowTitle(f"Inkline {version}")
        self.resize(1280, 860)
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)
        self.state = State()
        self.saved_presets = config.read("presets.json")
        lists = config.read("class-lists.json").get("lists")
        self.class_lists = {k: v for k, v in lists.items() if isinstance(k, str) and isinstance(v, str)} \
            if isinstance(lists, dict) else {}
        self._saved_class_set = project.class_set({})   # what the open project's file holds
        # the printer last chosen in the Print dialog ("" is the system's default): its dead edges are shown
        self.printer_name = config.read("printer.json").get("name", "") if remember else ""
        if not isinstance(self.printer_name, str):
            self.printer_name = ""
        self._view = None
        recent = config.read("recent.json") if remember else {}
        self.recent = [p for p in recent.get("photos", []) if isinstance(p, str)][:MAX_RECENT]
        self.recent_projects = [p for p in recent.get("projects", []) if isinstance(p, str)][:MAX_RECENT]
        self.project_path = None   # the .inkline file open, if any
        self._clip_id = uuid.uuid4().hex   # marks the booklet pages this window puts on the clipboard
        restored = self._restore()
        self.state.mirror()
        self.last_dir = os.path.expanduser("~/Pictures") if os.path.isdir(os.path.expanduser("~/Pictures")) else os.path.expanduser("~")

        central = QWidget()
        central.setObjectName("central")
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.sidebar = Sidebar(self.state, version)
        self.preview = Preview()
        lay.addWidget(self.sidebar)
        lay.addWidget(self.preview, 1)
        self.setCentralWidget(central)
        self.sidebar.fill_presets(self.saved_presets)

        self.renderer = Renderer()
        self.renderer.finished.connect(self._rendered)
        self.renderer.failed.connect(lambda _n, _why: self._msg("The preview couldn't be drawn. Try another setting, or start fresh from Presets."))
        self.renderer.busy.connect(lambda on: None if on or not self.renderer.idle else self.preview.set_busy(""))
        self.renderer.converting.connect(lambda: self.preview.set_busy("converting photo…"))
        self.worker = Renderer()        # saving and printing
        self.worker.finished.connect(self._job_done)
        self.worker.failed.connect(lambda _n, why: self._job_failed(why))
        self.status.connect(self.sidebar.set_status)
        self._render_timer = QTimer(self, singleShot=True, interval=40, timeout=self._render)
        self._remember_timer = QTimer(self, singleShot=True, interval=400, timeout=self._save_settings)
        # a copy of unsaved work, to get it back if Inkline closes unexpectedly (not for windows that remember nothing)
        self.keeper = recovery.Keeper(version) if remember else None
        self._keep_timer = QTimer(self, singleShot=True, interval=KEEP_SECONDS * 1000, timeout=self._keep_copy)
        self._busy_saving = False
        self._cancel = threading.Event()   # set by Cancel (or Esc) while a print or save is drawing
        self._job_path = None              # the PDF being written, deleted if it's cancelled
        self._job_stopped = ""             # what the status line says when it's cancelled
        self._job_outcome = {}             # jobs.run's note of pages that went to the printer anyway
        self._pending_save = None          # a PNG or SVG being drawn, before its file is chosen
        self._job_unit = "page"
        self._pan_start = None
        self.history = QUndoStack(self)
        self._history_view = None   # Edit → History…, made the first time it's opened
        self._drags = 0      # counts finished slider and photo drags, so the next drag is a new step
        self._focus_moves = 0   # leaving a field and coming back starts a new typing step
        QApplication.instance().focusChanged.connect(self._focus_moved)
        self._last = _Snapshot(self.state)
        self._restoring = False

        self._wire()
        self._menus()
        QApplication.instance().installEventFilter(self)
        theme.follow_system(QApplication.instance(), self.preview.page.update)
        if self.state.settings.mode == "convert" and not self.state.photos:
            self.state.photos = [sample_photo()]
            self.sidebar.fill_photos()
        if restored:
            self._msg("Reopened with your last settings. Presets → Start fresh resets them.")
        self._last = _Snapshot(self.state)   # where the history starts: nothing to undo yet
        self.history.cleanChanged.connect(self._update_title)
        self.history.cleanChanged.connect(lambda clean: self._keep_copy() if clean else None)   # undone back to saved
        self._update_title()
        self.schedule()

    # --- wiring -------------------------------------------------------------------------------------
    def _wire(self):
        sb, pv = self.sidebar, self.preview
        sb.changed.connect(self._changed)
        sb.cancel_btn.clicked.connect(self.cancel_job)
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.cancel_job)
        sb.mode_changed.connect(self._set_mode)
        sb.reroll.connect(self.new_design)
        sb.more_designs.connect(self.more_designs)
        sb.page_step.connect(self.step_page)
        sb.swap_page.connect(self._swap_page)
        sb.open_images.connect(self.open_images)
        sb.sample.connect(lambda: self.add_photos([sample_photo()], self.state.settings.photobook))
        sb.preset_chosen.connect(self._apply_preset)
        sb.preset_save.connect(self._save_preset)
        sb.preset_delete.connect(self._delete_preset)
        sb.class_list_save.connect(self._save_class_list)
        sb.class_list_delete.connect(self._delete_class_list)
        sb.fill_class_lists(self.class_lists)
        sb.class_set_changed.connect(self._class_set_changed)
        sb.photo_selected.connect(self._select_photo)
        sb.photo_moved.connect(self._move_photo)
        sb.photo_removed.connect(self._remove_photo)
        sb.pages_edit.connect(self._edit_pages)
        sb.book_page_selected.connect(self._select_book_page)
        sb.book_page_added.connect(self._add_book_page)
        sb.book_page_moved.connect(self._move_book_page)
        sb.book_page_copied.connect(self._copy_book_page)
        sb.book_page_removed.connect(self._remove_book_page)
        sb.page_answer.connect(self._set_page_answer)
        sb.pages_copy.connect(lambda: self.copy_pages(False))
        sb.crop.connect(self._crop)
        sb.print_.connect(self.print_)
        sb.save.connect(self.save)
        sb.synced.connect(self._sync_actions)
        pv.page.pan.connect(self._pan)
        pv.page.zoom.connect(self._wheel_zoom)
        pv.page.pan_end.connect(self._drag_ended)
        for control, _write in sb._binds.values():
            if isinstance(control, QAbstractSlider):
                control.sliderReleased.connect(self._drag_ended)
        for s in (sb.zoom, sb.panx, sb.pany):
            s.sliderReleased.connect(self._drag_ended)

    def _menus(self):
        mb = self.menuBar()

        def act(menu, text, fn, keys=None):
            a = QAction(text, self)
            if keys:
                a.setShortcut(QKeySequence(keys))
            a.triggered.connect(fn)
            menu.addAction(a)
            return a

        f = mb.addMenu("&File")
        act(f, "Ne&w project", self.new_project)
        act(f, "Open pro&ject…", lambda: self.open_project(), "Ctrl+Shift+O")
        self.recent_projects_menu = f.addMenu("Open recen&t project")
        self.recent_projects_menu.aboutToShow.connect(self._fill_recent_projects)
        self.recent_projects_menu.setEnabled(bool(self.recent_projects))
        act(f, "Sa&ve project", self.save_project, "Ctrl+S")
        act(f, "Save project &as…", self.save_project_as, "Ctrl+Shift+S")
        f.addSeparator()
        act(f, "&Open image…", lambda: self.open_images(self.state.settings.photobook), "Ctrl+O")
        self.recent_menu = f.addMenu("Open &recent image")
        self.recent_menu.aboutToShow.connect(self._fill_recent)
        self.recent_menu.setEnabled(bool(self.recent))
        f.addSeparator()
        self.act_pdf = act(f, "Save &PDF…", lambda: self.save("pdf"), "Ctrl+E")
        self.act_png = act(f, "Save P&NG…", lambda: self.save("png"), "Ctrl+Shift+E")
        self.act_svg = act(f, "Save &SVG…", lambda: self.save("svg"))
        f.addSeparator()
        act(f, "&Print…", self.print_, "Ctrl+P")
        f.addSeparator()
        act(f, "&Quit", self.close, "Ctrl+Q")
        e = mb.addMenu("&Edit")
        undo = self.history.createUndoAction(self, "&Undo")
        undo.setShortcuts(QKeySequence.StandardKey.Undo)
        redo = self.history.createRedoAction(self, "&Redo")
        redo.setShortcuts(QKeySequence.StandardKey.Redo)
        e.addAction(undo)
        e.addAction(redo)
        e.addSeparator()
        # a booklet's pages through the clipboard (Ctrl+C in the page list; Ctrl+V pastes pages or a picture)
        act(e, "&Copy page\tCtrl+C", lambda: self.copy_pages(False))
        act(e, "Copy &all pages", lambda: self.copy_pages(True))
        act(e, "&Paste\tCtrl+V", self.paste)
        e.addSeparator()
        act(e, "&History…", self.show_history, "Ctrl+H")
        v = mb.addMenu("&View")
        act(v, "&New design", self.new_design, "Ctrl+N")
        act(v, "&More designs…", self.more_designs, "Ctrl+Shift+N")
        act(v, "Pre&vious page\t←", lambda: self.step_page(-1))
        act(v, "Ne&xt page\t→", lambda: self.step_page(1))
        v.addSeparator()
        self.act_test = act(v, "Printer &test page", self._toggle_test_page)
        self.act_test.setCheckable(True)
        v.addSeparator()
        self.act_desktop = act(v, "Use my &desktop's style", self._toggle_desktop_style)
        self.act_desktop.setCheckable(True)
        self.act_desktop.setChecked(theme.DESKTOP["on"])
        name = theme.desktop_style_name()
        if name:
            self.act_desktop.setToolTip(f"Look like your other apps ({name.capitalize()}) instead of Inkline's own style")
        else:   # the Flatpak, AppImage and .deb bring their own Qt, without the desktop's style plugins
            self.act_desktop.setEnabled(False)
            self.act_desktop.setToolTip("This copy of Inkline brings its own Qt, which can't load your desktop's style. "
                                        "The Arch package and the .run installer use your system's Qt and can.")
        v.setToolTipsVisible(True)
        h = mb.addMenu("&Help")
        act(h, "&What's new", lambda: self.show_whats_new())
        act(h, "&About Inkline", self._about)

    # --- state changes -------------------------------------------------------------------------------
    def _changed(self, key=""):
        control = self.sidebar._binds.get(key, (None,))[0]
        self._timed = isinstance(control, QAbstractSlider)   # a slider's arrow keys join; clicks don't
        self._typed = control if isinstance(control, QLineEdit) and control.hasFocus() else None
        st = self.state
        s = st.settings
        # one multi-page mode at a time, and the pager starts again where 2.x restarted it
        if key == "booklet":
            st.page = 0
            if s.booklet:
                st.update(poster=False)
        elif key == "poster" and s.poster:
            st.update(booklet=False, photobook=False)
        elif key == "photobook" and s.photobook:
            st.update(poster=False)
            st.page = (1 if s.pcover else 0) + st.sel
        elif key == "pcover":
            st.page = (1 if s.pcover else 0) + st.sel
        elif key == "fold":
            st.page = 0
        elif key == "cover" and st.book_page is not None:
            self._show_book_page()
        if st.book_page is not None and key in PAGE_KEYS and key != "seed":
            st.write_page(**{key: getattr(st.settings, key)})   # the Design section edits the selected page
            self.sidebar.fill_pages()
        elif st.listing and key in BOOKLET_LOOK:
            self.sidebar.refresh_thumbs()
        elif st.listing and key == "key":
            self.sidebar.fill_pages()   # rows say "no answer" only while there are answer pages   # every page's picture shows the booklet's line weight, border and paper
        if key in ("booklet", "poster", "photobook"):
            self.sidebar.only_pages.clear()   # a choice of pages was for that book: a different one starts with all
            st.mirror()   # back to a booklet built page by page: Design shows the page being edited again
            self.sidebar.load()
            self.sidebar.fill_pages()
        self.sidebar.sync()
        self.act_test.setChecked(s.testpage)
        self.schedule()
        self.remember_soon()

    def eventFilter(self, obj, e):
        """← → (and Page Up/Down) turn booklet and photo book pages wherever the keyboard is, except in a
        field, list or slider that uses them itself (2.x's rule), so a focused button doesn't stop them."""
        if e.type() == QEvent.Type.KeyPress and self.isActiveWindow():
            d = {Qt.Key.Key_Left: -1, Qt.Key.Key_PageUp: -1, Qt.Key.Key_Right: 1, Qt.Key.Key_PageDown: 1}.get(e.key())
            mods = e.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
            focus = QApplication.focusWidget()
            if (d and mods == Qt.KeyboardModifier.NoModifier and QApplication.activePopupWidget() is None
                    and not isinstance(obj, (QMenu, QMenuBar)) and not isinstance(
                        focus, (QLineEdit, QComboBox, QAbstractSlider, QAbstractSpinBox, QAbstractItemView, QMenuBar))
                    and self.step_page(d)):
                return True   # taken only when there were pages to turn; menus keep their arrow keys
        return super().eventFilter(obj, e)

    def _set_mode(self, mode):
        self.state.update(mode=mode)
        if self.state.listing:   # back to the booklet built page by page: its rows and their pictures
            self.state.mirror()
            self.sidebar.load()
            self.sidebar.fill_pages()
        if mode == "convert" and not self.state.photos:
            self.state.photos = [sample_photo()]
            self.state.sel = 0
            self.sidebar.fill_photos()
            self.sidebar.load_crop()
        self.sidebar.sync()
        self.schedule()
        self.remember_soon()

    def new_design(self):
        if self.state.settings.mode != "make":
            return
        if self._listing():   # a booklet built page by page: a new design for the page being edited
            self.state.write_page(seed=new_seed())
            self.sidebar.fill_pages()
        else:
            self.state.update(seed=new_seed(), page_seeds={})   # a fresh booklet drops any swapped pages
        self._step_name = "New design"   # however many settings that changed
        self._changed("seed")

    def design_options(self):
        """What More designs… offers, for whatever New design would change: (candidate(seed) -> (settings,
        spec), chosen(seed), what it changes), or None outside Make one up."""
        st = self.state
        s = st.settings
        if s.mode != "make":
            return None
        if self._listing():   # a booklet built page by page: the page being edited
            designs = [p for p in book.book_pages(s) if p.kind == "design"]
            i = max(0, min(st.book_sel, len(designs) - 1))
            spec = designs[i]

            def chosen(seed):
                st.write_page(seed=seed)
                self.sidebar.fill_pages()
                self._step_name = "New design"
                self._changed("seed")
            return (lambda seed: (s, replace(spec, seed=seed))), chosen, f"page {i + 1}"
        if s.booklet and not s.poster:   # a quick booklet: its seed, seen on the design page shown
            v = view(st)
            if v.kind == "fold" and v.pages:   # a folded side: the first design page on it
                shown = [v.pages[k] for k in book.fold_order(len(v.pages))[v.index]]
            else:
                shown = [v.pages[v.index]] if v.kind == "booklet" and v.pages else []
            i = next((p.idx for p in shown if p.kind == "design"), 0)

            def candidate(seed):
                s2 = replace(s, seed=seed, page_seeds={})
                return s2, [d for d in book.book_pages(s2) if d.kind == "design"][i]

            def chosen(seed):
                st.update(seed=seed, page_seeds={})
                self._step_name = "New design"
                self._changed("seed")
            return candidate, chosen, f"the whole booklet (each shows page {i + 1 + (1 if s.cover else 0)})"

        def chosen(seed):
            st.update(seed=seed, page_seeds={})   # as New design does
            self._step_name = "New design"
            self._changed("seed")
        # a single page, or a poster's design, shown on one page (a poster's sheets would be too small to judge)
        one = replace(s, poster=False, fold=False, booklet=False)
        return (lambda seed: (replace(one, seed=seed), single_page(replace(one, seed=seed)))), chosen, \
            "the poster's design (shown on one page)" if s.poster else "this page"

    def more_designs(self):
        offer = self.design_options()
        if offer is None:
            return
        from .options import Options
        Options(self, *offer).exec()

    # --- a booklet built page by page -----------------------------------------------------------------------
    def _listing(self):
        return self.state.listing

    def _show_book_page(self):
        """Turn the preview to the page being edited (a folded side holds several, so it stays put)."""
        s = self.state.settings
        if not s.fold:
            self.state.page = (1 if s.cover else 0) + self.state.book_sel

    def _edit_pages(self, on):
        st = self.state
        s = st.settings
        if on:
            # the booklet as it is now, page for page: each page keeps its pattern, design and complexity
            pages = book.book_pages(s)
            designs = [p for p in pages if p.kind == "design"]
            shown = view(st)
            p = shown.pages[shown.index] if shown.kind == "booklet" and shown.pages else None
            base = {k: getattr(s, k) for k in PAGE_KEYS}
            self._step_name = "Edit pages one by one"
            st.update(page_list=[{**base, "gen": d.gen, "seed": d.seed, "complexity": d.c} for d in designs])
            st.book_sel = p.idx if p is not None and p.kind == "design" else 0
        else:
            self._step_name = "Back to quick booklet"
            st.update(page_list=[], pages=max(2, min(MAX_BOOK_PAGES, len(s.page_list))))
            st.book_sel = 0
        self._list_changed()

    def _list_changed(self):
        """After the page list changed: show the page being edited, in the controls and the preview."""
        self.state.mirror()
        self._show_book_page()
        self.sidebar.load()
        self.sidebar.fill_pages()
        self.schedule()
        self.remember_soon()

    def _select_book_page(self, i):
        if not self._listing() or i == self.state.book_sel:
            return
        self.state.book_sel = i   # not an edit: the undo history doesn't change
        self.state.mirror()
        self._show_book_page()
        # the list isn't filled again, so a drag that starts with this click goes on
        self.sidebar.load()
        self.sidebar.show_selected_page()
        self.schedule()
        self.remember_soon()   # the remembered settings show the page being edited

    def _set_page_answer(self, on):
        if self.state.book_page is None:
            return
        self._step_name = "Include its answer" if on else "Leave its answer out"
        self.state.write_page(answer=on)
        self.sidebar.fill_pages()
        self.sidebar.sync()
        self.schedule()
        self.remember_soon()

    def _add_book_page(self):
        pl = self.state.settings.page_list
        if not pl or len(pl) >= MAX_BOOK_PAGES:
            return
        self._step_name = "Add page"
        new = {k: v for k, v in pl[-1].items() if k != "answer"}   # a new page has its answer, like any new page
        self.state.update(page_list=[*pl, {**new, "seed": new_seed()}])
        self.state.book_sel = len(pl)
        self._list_changed()

    def _copy_book_page(self, i):
        pl = self.state.settings.page_list
        if len(pl) >= MAX_BOOK_PAGES:
            return
        self._step_name = "Duplicate page"
        self.state.update(page_list=[*pl[:i + 1], {**pl[i], "seed": new_seed()}, *pl[i + 1:]])   # same settings, a new design
        self.state.book_sel = i + 1
        self._list_changed()

    def copy_pages(self, everything=False):
        """The selected page (or every page) onto the clipboard, to paste into this or another booklet."""
        if not self._listing():
            self._msg("Copying pages works in a booklet built page by page: turn on Edit pages one by one.")
            return
        pl = self.state.settings.page_list
        pages = list(pl) if everything else [pl[self.state.book_sel]]
        md = QMimeData()
        # "from": this window, so closing it only touches pages it put there itself, not another Inkline's
        md.setData(PAGES_MIME, json.dumps({"app": "Inkline", "from": self._clip_id, "pages": pages}).encode("utf-8"))
        names = [NAMES.get(p.get("gen"), "page") for p in pages]
        md.setText("Inkline booklet pages: " + ", ".join(names))
        QGuiApplication.clipboard().setMimeData(md)
        self._msg(f"Copied {len(pages)} pages. Paste them into a booklet with Ctrl+V." if len(pages) > 1 else
                  f"Copied page {self.state.book_sel + 1} ({names[0]}). Paste it into a booklet with Ctrl+V.")

    def _release_clipboard(self):
        """Closing: pages this window put on the clipboard stay there as their description (plain text). Data
        made in Python and still on the clipboard when Qt shuts down crashes PySide 6.12 as the app quits."""
        cb = QGuiApplication.clipboard()
        md = cb.mimeData()
        if md is None or not md.hasFormat(PAGES_MIME):
            return
        try:
            mine = json.loads(bytes(md.data(PAGES_MIME)).decode("utf-8")).get("from") == self._clip_id
        except (ValueError, AttributeError, UnicodeDecodeError):
            mine = False
        if mine:
            cb.setText(md.text())

    def paste_pages(self, raw):
        """Pages copied from Inkline, after the selected page: exactly as copied (same designs), one undo step."""
        try:
            data = json.loads(raw.decode("utf-8"))
            pages = [clean_page(p) for p in data.get("pages", []) if isinstance(p, dict)]
        except (ValueError, AttributeError, UnicodeDecodeError):
            pages = []
        pages = [p for p in pages if p.get("gen") in NAMES]
        if not pages:
            self._msg("There are no pages to paste.")
            return
        if not self._listing():
            self._msg("To paste pages, turn on Make a multi-page booklet, then Edit pages one by one.")
            return
        pl = self.state.settings.page_list
        room = MAX_BOOK_PAGES - len(pl)
        if room <= 0:
            self._msg(f"A booklet holds up to {MAX_BOOK_PAGES} design pages, so there's no room to paste.")
            return
        kept = pages[:room]
        at = self.state.book_sel + 1
        self._step_name = "Paste pages" if len(kept) > 1 else "Paste page"
        self.state.update(page_list=[*pl[:at], *kept, *pl[at:]])
        self.state.book_sel = at
        self._list_changed()
        left = len(pages) - len(kept)
        self._msg(f"Pasted {len(kept)} of {len(pages)} pages: a booklet holds up to {MAX_BOOK_PAGES}." if left else
                  f"Pasted {len(kept)} page{'s' if len(kept) > 1 else ''} after page {at}.")

    def _move_book_page(self, i, d):
        """Move page i by d places (↑ ↓ are ±1; a drag can be any distance)."""
        pl = list(self.state.settings.page_list)
        j = i + d
        if d == 0 or not (0 <= i < len(pl) and 0 <= j < len(pl)):
            return
        order = list(range(len(pl)))
        order.insert(j, order.pop(i))
        self._step_name = "Move page"
        self.state.update(page_list=[pl[k] for k in order])
        old = max(0, min(self.state.book_sel, len(pl) - 1))
        self.state.book_sel = order.index(old)   # the page being edited stays selected, wherever it went
        self._list_changed()

    def _remove_book_page(self, i):
        pl = self.state.settings.page_list
        if len(pl) < 2:
            return
        self._step_name = "Remove page"
        self.state.update(page_list=pl[:i] + pl[i + 1:])
        sel = self.state.book_sel
        self.state.book_sel = sel - 1 if sel > i else sel
        self._list_changed()

    def step_page(self, d):
        s, v = self.state.settings, view(self.state)
        if v.kind not in ("booklet", "photobook", "fold"):
            return False
        self.state.page = max(0, min(self.state.page + d, v.count - 1))
        if v.kind == "photobook" and self.state.photos:   # paging selects that page's photo, to crop what's shown
            self.state.sel = max(0, min(self.state.page - (1 if s.pcover else 0), len(self.state.photos) - 1))
            self.sidebar.fill_photos()
            self.sidebar.load_crop()
        p = v.pages[max(0, min(self.state.page, v.count - 1))] if v.kind == "booklet" and v.pages else None
        if p is not None and p.kind == "design" and self._listing() and p.idx != self.state.book_sel:
            self.state.book_sel = p.idx   # paging to a design page edits that page
            self.state.mirror()
            self.sidebar.load()
            self.sidebar.fill_pages()
        self.schedule()
        return True

    def _swap_page(self, new):
        key = getattr(self.sidebar, "current_key", None)
        if key is None:
            return
        seeds = {k: v for k, v in (self.state.settings.page_seeds or {}).items() if str(k) != str(key)}
        if new:
            import random
            seeds[key] = random.randrange(4294967296)
        self.state.update(page_seeds=seeds)
        self._changed("page_seeds")

    def _focus_moved(self, *_a):
        self._focus_moves += 1

    def _drag_ended(self):
        self._pan_start = None
        self._drags += 1

    def _sync_actions(self):
        """The File menu's saves are enabled exactly when the footer's buttons are (2.x clicked the button)."""
        if hasattr(self, "act_pdf"):
            sb = self.sidebar
            for a, b in ((self.act_pdf, sb.pdf_btn), (self.act_png, sb.png_btn), (self.act_svg, sb.svg_btn)):
                a.setEnabled(b.isEnabled())
                a.setToolTip(b.toolTip())

    def _toggle_desktop_style(self, on):
        theme.use_desktop(QApplication.instance(), on)
        self.preview.page.update()
        if self.remember:
            err = config.write("preferences.json", {**config.read("preferences.json"), "desktop_style": bool(on)},
                               "Preferences")
            if err:
                self._msg(err)
        self._msg(f"Using your desktop's style ({theme.desktop_style_name().capitalize()})." if on else
                  "Using Inkline's own style.")

    def _toggle_test_page(self):
        self.state.update(testpage=not self.state.settings.testpage)
        self.sidebar.load()
        self._changed("testpage")

    # --- photos --------------------------------------------------------------------------------------
    def open_images(self, append=False):
        files, _ = QFileDialog.getOpenFileNames(self, "Add photos" if append else "Open image", self.last_dir, IMAGE_FILTER)
        if files:
            self.last_dir = os.path.dirname(files[0])
            self._load_files(files, append)

    def _load_files(self, files, append):
        ok, bad, opened = [], [], []
        for f in (files if append else files[:1]):
            try:
                p = photo.load_photo(f)
                p.name = os.path.basename(f)
                ok.append(p)
                opened.append(os.path.abspath(f))
            except OSError:
                bad.append(os.path.basename(f))
        if bad:
            self._msg(f"Couldn't read {', '.join(bad)} as an image. Try PNG, JPEG or WebP.")
        st = self.state
        room = MAX_PHOTOS - len(st.photos) if append and st.photos else MAX_PHOTOS
        self._add_recent(opened[:max(0, room)])   # only the photos add_photos will keep
        if ok:
            self.add_photos(ok, append)

    # File → Open recent: the photos opened lately, newest first, kept in recent.json
    def _add_recent(self, paths):
        if not paths or not self.remember:
            return
        newest = list(dict.fromkeys(reversed(paths)))   # newest first, each file once
        self._set_recent(newest + [p for p in self.recent if p not in newest])

    def _set_recent(self, paths):
        self.recent = paths[:MAX_RECENT]
        self.recent_menu.setEnabled(bool(self.recent))
        self._write_recent("Recent photos")

    def _write_recent(self, what):
        if self.remember:
            err = config.write("recent.json", {"photos": self.recent, "projects": self.recent_projects}, what)
            if err:
                self._msg(err)

    # --- projects (.inkline files) ------------------------------------------------------------------------
    def _unsaved(self):
        """Changes the project file doesn't have: an undo step, or (in a project) its class set."""
        if not self.history.isClean():
            return True
        return self.project_path is not None and \
            project.class_set(self.sidebar.class_set()) != project.class_set(self._saved_class_set)

    def _class_set_changed(self):
        """Copies, Names or their switches changed: the title's unsaved mark, and a recovery copy as for any change."""
        self._update_title()
        if self.keeper is not None and self.project_path is not None and not self._keep_timer.isActive():
            self._keep_timer.start()

    def _update_title(self, *_a):
        name = project.title(self.project_path) if self.project_path else ""
        # untitled work shows no unsaved mark: it was never a file (and the settings are remembered anyway)
        self.setWindowTitle(f"{name}[*] — Inkline {self.version}" if name else f"Inkline {self.version}")
        if name:
            self.setWindowModified(self._unsaved())

    def _ask_to_save(self):
        """Before the work is replaced: True to go on (saved, or the changes aren't wanted), False to stop."""
        if not self._unsaved():
            return True
        name = project.title(self.project_path) if self.project_path else ""
        box = QMessageBox(QMessageBox.Icon.Question, "Save changes?",
                          f"Save the changes to “{name}”?" if name else "Save your work as a project first?",
                          QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                          | QMessageBox.StandardButton.Cancel, self)
        box.button(QMessageBox.StandardButton.Discard).setText("Don't save")
        box.setInformativeText("Your changes will be lost if you don't save them.")
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        answer = box.exec()
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def _use_project(self, proj, path):
        """Make what the project holds the work in the window, with a fresh history."""
        st = self.state
        st.settings, st.photos, st.sel, st.book_sel, st.page = proj.settings, list(proj.photos), proj.sel, proj.book_sel, 0
        st.mirror()
        self.project_path = path
        self.sidebar.load()
        self.sidebar.fill_photos()
        self.sidebar.fill_pages()
        self.sidebar.load_crop()
        self.act_test.setChecked(False)
        self.sidebar.only_pages.clear()   # another book: every page again
        self.sidebar.set_class_set(proj.class_set)   # the project's class set, or none
        self._saved_class_set = project.class_set(proj.class_set or {})
        self.history.clear()        # Undo doesn't reach back into the work that was open before
        self._last = _Snapshot(st)
        self.history.setClean()
        self._keep_copy()           # nothing unsaved now: no copy
        self._update_title()
        self.schedule()
        self.remember_soon()

    def new_project(self):
        if not self._ask_to_save():
            return
        self._use_project(project.Project(State().settings), None)
        self._msg("New project. Settings are back to their defaults.")

    def open_project(self, path=None):
        asked = path is None
        if asked:   # asked before the file is chosen, as other apps do
            if not self._ask_to_save():
                return False
            path, _ = QFileDialog.getOpenFileName(self, "Open project", self.last_dir, project.FILTER)
            if not path:
                return False
        name = os.path.basename(path)
        if not os.path.isfile(path):   # found missing before asking about the work open now
            self._msg(f"Couldn't find {name}. It may have been moved or deleted.")
            if path in self.recent_projects:
                self._set_recent_projects([p for p in self.recent_projects if p != path])
            return False
        if not asked and not self._ask_to_save():
            return False
        try:
            proj = project.load(path)
        except project.ProjectError as why:
            self._msg(f"Couldn't open {name}: it {why}. Choose another project, or a copy of this one.")
            return False
        except OSError:
            self._msg(f"Couldn't open {name}. Check that you're allowed to read it.")
            return False
        self.last_dir = os.path.dirname(os.path.abspath(path))
        self._use_project(proj, os.path.abspath(path))
        self._add_recent_project(self.project_path)
        lost = proj.skipped
        self._msg(f"Opened {name}, without {lost} damaged photo{'s' if lost > 1 else ''}." if lost else f"Opened {name}.")
        return True

    def save_project(self):
        if self.project_path is None:
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self):
        name = project.title(self.project_path) if self.project_path else "My project"
        path = self._ask_path("Save project", name, project.EXT, project.FILTER)
        return self._write_project(path) if path else False

    def _write_project(self, path):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)   # big photos take a moment to pack
        try:
            cs = self.sidebar.class_set()
            project.save(path, self.state, self.version, project.class_set_json(cs))
        except (OSError, ValueError):
            self._msg(f"Couldn't save {os.path.basename(path)}. Check that the folder exists and you can write to it.")
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.project_path = os.path.abspath(path)
        self._saved_class_set = project.class_set(cs)
        self.history.setClean()
        self._keep_copy()           # saved: the recovery copy goes
        self._update_title()
        self._add_recent_project(self.project_path)
        self._msg(f"Saved {os.path.basename(path)}.")
        return True

    # --- getting work back after Inkline closes unexpectedly -----------------------------------------------
    def _worth_keeping(self):
        """Unsaved work that isn't remembered anywhere else: settings are (last-settings.json), photos and a
        booklet's own pages aren't, and an open project's changes aren't in its file."""
        st = self.state
        return self._unsaved() and bool(st.photos or st.settings.page_list or self.project_path)

    def _keep_copy(self):
        if self.keeper is None:
            return
        if not self._worth_keeping():
            self._keep_timer.stop()
            self.keeper.forget()
            return
        st = self.state   # a snapshot, as the preview draws from: the worker never sees the work change under it
        snap = State(replace(st.settings), [replace(p) for p in st.photos], st.sel, st.page, st.book_sel)
        self.keeper.keep(snap, self.project_path, project.class_set_json(self.sidebar.class_set()))

    def offer_recovery(self):
        """At start: if a session closed without saving its work, offer to bring that work back."""
        if self.keeper is None:
            return False
        for path in recovery.leftovers():
            try:
                proj, data = project.read(path)
            except (project.ProjectError, OSError):
                recovery.discard(path)   # a damaged copy is no use to anyone
                continue
            box = QMessageBox(QMessageBox.Icon.Question, "Recover unsaved work?",
                              "Inkline closed before your work was saved. Recover it?",
                              QMessageBox.StandardButton.Discard, self)
            recover = box.addButton("Recover", QMessageBox.ButtonRole.AcceptRole)
            box.setInformativeText(recovery.describe(path, data))
            box.setDefaultButton(recover)
            box.exec()
            if box.clickedButton() is recover:
                src = (data.get("recovery") or {}).get("project")
                self._use_project(proj, src if isinstance(src, str) and src else None)
                self.history.resetClean()   # recovered, not saved: the title shows it and closing asks
                self._update_title()
                self._keep_copy()           # this session keeps it now
                self._msg("Recovered your unsaved work. Save it as a project to keep it.")
            recovery.discard(path)
            return box.clickedButton() is recover
        return False

    # File → Open recent project: the projects opened or saved lately, newest first, kept in recent.json
    def _add_recent_project(self, path):
        self._set_recent_projects([path] + [p for p in self.recent_projects if p != path])

    def _set_recent_projects(self, paths):
        self.recent_projects = paths[:MAX_RECENT]
        self.recent_projects_menu.setEnabled(bool(self.recent_projects))
        self._write_recent("Recent projects")

    def _fill_recent_projects(self):
        m = self.recent_projects_menu
        m.clear()
        for i, path in enumerate(self.recent_projects):
            label = project.title(path).replace("&", "&&")
            a = m.addAction(f"&{i + 1} {label}" if i < 9 else f"1&0 {label}")
            a.setToolTip(path)
            a.triggered.connect(lambda _c=False, p=path: self.open_project(p))
        m.setToolTipsVisible(True)
        m.addSeparator()
        m.addAction("&Clear list", lambda: self._set_recent_projects([]))

    def _fill_recent(self):
        m = self.recent_menu
        m.clear()
        for i, path in enumerate(self.recent):
            label = os.path.basename(path).replace("&", "&&")
            a = m.addAction(f"&{i + 1} {label}" if i < 9 else f"1&0 {label}")
            a.setToolTip(path)
            a.triggered.connect(lambda _c=False, p=path: self.open_recent(p))
        m.setToolTipsVisible(True)
        m.addSeparator()
        m.addAction("&Clear list", lambda: self._set_recent([]))

    def open_recent(self, path):
        if not os.path.isfile(path):
            self._msg(f"Couldn't find {os.path.basename(path)}. It may have been moved or deleted.")
            self._set_recent([p for p in self.recent if p != path])
            return
        self.last_dir = os.path.dirname(path)
        self._load_files([path], self.state.settings.photobook)

    def add_photos(self, new, append):
        st = self.state
        first = 0
        if append and st.photos:
            room = MAX_PHOTOS - len(st.photos)
            if room <= 0:
                self._msg(f"A photo book holds up to {MAX_PHOTOS} photos.")
                return
            if len(new) > room:
                self._msg(f"Added {room} photos; a photo book holds up to {MAX_PHOTOS}.")
            first = len(st.photos)
            st.photos.extend(new[:room])
        else:
            st.photos = new[:MAX_PHOTOS]
        self._select_photo(first)
        if st.settings.mode != "convert":
            self.state.update(mode="convert")
            self.sidebar.load()
        self.schedule()

    def _select_photo(self, i):
        st = self.state
        st.sel = max(0, min(i, len(st.photos) - 1))
        if st.settings.photobook:
            st.page = (1 if st.settings.pcover else 0) + st.sel
        self.sidebar.fill_photos()
        self.sidebar.load_crop()
        self.sidebar.sync()
        self.schedule()

    def _move_photo(self, i, d):
        st, j = self.state, i + d
        if 0 <= j < len(st.photos):
            st.photos[i], st.photos[j] = st.photos[j], st.photos[i]
            self._select_photo(j if st.sel == i else i if st.sel == j else st.sel)

    def _remove_photo(self, i):
        st = self.state
        if len(st.photos) >= 2:
            del st.photos[i]
            self._select_photo(st.sel - 1 if st.sel > i else st.sel)

    def _crop(self, kind):
        ph = self.state.photo
        if not ph:
            return
        if kind == "rotl":
            ph.rot = (ph.rot + 270) % 360
        elif kind == "rotr":
            ph.rot = (ph.rot + 90) % 360
        elif kind == "reset":
            ph.rot, ph.zoom, ph.panx, ph.pany = 0, 100, 0, 0
            self.sidebar.load_crop()
        else:
            sb = self.sidebar
            ph.zoom, ph.panx, ph.pany = sb.zoom.value(), sb.panx.value(), sb.pany.value()
            self._timed = True
        self.schedule()

    def _overhang(self):
        """How far the cropped photo overhangs its box on each side, in page pixels at the preview's dpi."""
        s, ph = self.state.settings, self.state.photo
        g = geometry(s, PREVIEW_DPI)
        spec = single_page(s, ph)
        box = design_box(g, spec, s, frame=False) if spec.header else g.box
        iw, ih = ph.image.width(), ph.image.height()
        rw, rh = (ih, iw) if ph.rot % 180 else (iw, ih)
        fit = max if s.fit == "cover" else min
        sc = fit(box.w / rw, box.h / rh) * ph.zoom / 100
        return max(0, rw * sc - box.w) / 2, max(0, rh * sc - box.h) / 2

    def _pan(self, dx, dy):
        ph = self.state.photo
        if not ph:
            return
        if self._pan_start is None:
            self._pan_start = (ph.panx, ph.pany)
        ex, ey = self._overhang()
        px, py = self._pan_start
        ph.panx = round(max(-100, min(100, px + dx / ex * 100))) if ex else px
        ph.pany = round(max(-100, min(100, py + dy / ey * 100))) if ey else py
        self.sidebar.load_crop()
        self.schedule()

    def _wheel_zoom(self, d):
        ph = self.state.photo
        if ph:
            ph.zoom = max(100, min(400, ph.zoom + 10 * d))
            self._timed = True
            self.sidebar.load_crop()
            self.schedule()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasImage():
            e.acceptProposedAction()
            self.preview.set_drop(True)

    def dragLeaveEvent(self, _e):
        self.preview.set_drop(False)

    def dropEvent(self, e):
        self.preview.set_drop(False)
        md = e.mimeData()
        files = [u.toLocalFile() for u in md.urls() if u.isLocalFile()]
        projects = [f for f in files if f.lower().endswith("." + project.EXT)]
        if projects:   # a project dropped on the window opens (only the first, as Open project opens one)
            self.open_project(projects[0])
        elif files:
            self._load_files(files, self.state.settings.photobook)
        elif md.hasImage():   # an image dragged straight from a browser or another app
            img = QImage(md.imageData())
            if not img.isNull():
                self.add_photos([photo.Photo(img.convertToFormat(QImage.Format.Format_ARGB32), name="dropped image")],
                                self.state.settings.photobook)

    def paste(self):
        """Ctrl+V: booklet pages copied from Inkline go into the booklet; a picture becomes the photo."""
        md = QGuiApplication.clipboard().mimeData()
        if md is not None and md.hasFormat(PAGES_MIME):
            self.paste_pages(bytes(md.data(PAGES_MIME)))
            return
        img = QGuiApplication.clipboard().image()
        if not img.isNull():
            self.add_photos([photo.Photo(img.convertToFormat(QImage.Format.Format_ARGB32), name="pasted image")],
                            self.state.settings.photobook)

    def keyReleaseEvent(self, e):
        if e.matches(QKeySequence.StandardKey.Paste) and not isinstance(QApplication.focusWidget(), QLineEdit):
            self.paste()
        super().keyReleaseEvent(e)

    # --- the preview ---------------------------------------------------------------------------------
    def schedule(self):
        self._record()
        self.preview.set_busy("rendering…")
        self._render_timer.start()

    # --- undo and redo ---------------------------------------------------------------------------------
    def _record(self):
        """After every change: one undo step if the edits differ from the last step (schedule() calls this)."""
        if self._restoring or not hasattr(self, "history"):
            return
        timed, self._timed = getattr(self, "_timed", False), False
        name, self._step_name = getattr(self, "_step_name", None), None
        now = _Snapshot(self.state)
        if now.same(self._last):
            self._last = now   # no edit, but the next step starts from the page and photo chosen now
            return
        self.history.push(_Step(self, self._last, now, name or now.what(self._last), self._gesture(), timed))
        if self.keeper is not None and not self._keep_timer.isActive():
            self._keep_timer.start()   # a copy within the minute, then again a minute after the next change
        self._last = now

    def _gesture(self):
        """What the change in progress belongs to: a slider held down, a drag of the photo, typing in one field."""
        if self._pan_start is not None:
            return ("drag", self._drags)
        for key, (control, _write) in self.sidebar._binds.items():
            if isinstance(control, QAbstractSlider) and control.isSliderDown():
                return ("slider", key, self._drags)
        if self.sidebar.zoom.isSliderDown() or self.sidebar.panx.isSliderDown() or self.sidebar.pany.isSliderDown():
            return ("crop", self._drags)
        typed, self._typed = getattr(self, "_typed", None), None
        if typed is not None:     # typed into that field, and the cursor has stayed in it since
            return ("typing", id(typed), self._focus_moves)
        return None

    def _restore_snapshot(self, snap):
        st = self.state
        self._restoring = True
        try:
            st.settings = snap.settings
            st.photos = list(snap.photos)
            for p, (rot, zoom, panx, pany) in zip(st.photos, snap.crops):
                p.rot, p.zoom, p.panx, p.pany = rot, zoom, panx, pany
            st.sel = max(0, min(snap.sel, len(st.photos) - 1))
            st.book_sel = snap.book_sel
            st.mirror()
            if st.listing:
                self._show_book_page()   # the preview shows the page the list highlights
            self._last = _Snapshot(st)
            self.sidebar.load()
            self.sidebar.fill_photos()
            self.sidebar.fill_pages()
            self.sidebar.load_crop()
            self.act_test.setChecked(st.settings.testpage)
            self.schedule()
        finally:
            self._restoring = False
        self.remember_soon()
        if self.keeper is not None and not self._keep_timer.isActive():
            self._keep_timer.start()   # undone or redone away from what's saved: a copy, as for any change

    def _render(self):
        st = self.state
        snap = State(replace(st.settings), [replace(p) for p in st.photos], st.sel, st.page)
        self.renderer.submit(lambda: render_view(snap))

    def _rendered(self, n, r):
        if n != self.renderer.latest:
            return
        self.state.page = r.view.index
        self.preview.page.set_image(r.image, r.poster)
        self.preview.page.set_pannable(self.state.settings.mode == "convert" and bool(self.state.photos)
                                       and r.view.kind not in ("fold", "testpage"))
        self.preview.set_info(r.info)
        self.preview.set_busy("")
        self.sidebar.ws_note.setText(r.note)
        self.sidebar.sync(r.view)
        self._view = r.view
        self._show_printer_edges()

    def _show_printer_edges(self):
        """Hatch what the printer can't reach, and say so when the design runs into it."""
        v, s = self._view, self.state.settings
        found = jobs.printer_margins(self.printer_name, s, jobs.printed_orient(s, v.kind)) if v else None
        if not found:
            self.preview.page.set_dead(None)
            self.sidebar.set_margin_warning("")
            return
        name, (left, top, right, bottom), (w, h) = found
        # a whole poster shows no sheet margins to hatch; the warning still applies to every sheet
        self.preview.page.set_dead(None if v.kind == "poster" else (left / w, top / h, right / w, bottom / h))
        worst = max(left, top, right, bottom)
        if v.kind == "testpage" or worst <= s.margin + 1e-6:   # the test page is there to measure the printer
            self.sidebar.set_margin_warning("")
            return
        reach = f"{math.ceil(round(worst * 100, 6)) / 100:g}"   # up to the next hundredth: 0.07 stays 0.07
        enough = next((label for m, label in MARGINS if m >= worst - 1e-6), None)
        fix = f"Choose a {enough} margin or more." if enough else "No margin choice is wide enough for it."
        self.sidebar.set_margin_warning(f"{name} can't print the outer {reach} in of the page, so the design will be cut off. {fix}")

    # --- presets and remembered settings -------------------------------------------------------------
    def _apply_preset(self, group, name):
        p = BUILTIN_PRESETS.get(name) if group == "b" else self.saved_presets.get(name)
        if p is None:
            return
        self._step_name = f"“{name}”"   # Edit → Undo “Maze booklet with answers”
        self.state.apply_preset(p)
        self.state.mirror()
        self.sidebar.only_pages.clear()
        self.sidebar.load()
        self.sidebar.fill_pages()
        if self.state.settings.mode == "convert" and not self.state.photos:
            self.state.photos = [sample_photo()]
            self.sidebar.fill_photos()
        self._msg(f"Applied “{name}”.")
        self.schedule()
        self.remember_soon()

    def _save_preset(self, name):
        if not name:
            self._msg("Type a name for the preset first.")
            self.sidebar.preset_name.setFocus()
            return
        if name in BUILTIN_PRESETS:
            self._msg("That name belongs to a built-in preset. Choose another.")
            return
        existed = name in self.saved_presets
        nxt = {**self.saved_presets, name: self.state.preset_values()}
        err = config.write("presets.json", nxt, "Presets")
        if err:
            self._msg(err)
            return
        self.saved_presets = nxt
        self.sidebar.preset_name.clear()
        self.sidebar.fill_presets(nxt, f"s:{name}")
        self._msg(f"Updated preset “{name}”." if existed else f"Saved preset “{name}”.")

    def _save_class_list(self, chosen):
        """Paper → Names → Save…: keep the names typed as a list, under a name (the chosen list's, to update it)."""
        names = self.sidebar.copies_names.text().strip()
        if not jobs.parse_names(names):
            self._msg("Type or paste the names first, then save them as a list.")
            self.sidebar.copies_names.setFocus()
            return
        name, ok = QInputDialog.getText(self, "Save class list", "Name for this list:", text=chosen)
        name = " ".join(name.split())[:40].strip()
        if not ok or not name:
            return
        existed = name in self.class_lists
        nxt = {**self.class_lists, name: names}
        err = config.write("class-lists.json", {"lists": nxt}, "Class lists")
        if err:
            self._msg(err)
            return
        self.class_lists = nxt
        self.sidebar.fill_class_lists(nxt, name)
        self._msg(f"Updated the list “{name}”." if existed else f"Saved the list “{name}”.")

    def _delete_class_list(self, name):
        if name not in self.class_lists:
            return
        nxt = {k: v for k, v in self.class_lists.items() if k != name}
        err = config.write("class-lists.json", {"lists": nxt}, "Class lists")
        if err:
            self._msg(err)
            return
        self.class_lists = nxt
        self.sidebar.fill_class_lists(nxt)
        self._msg(f"Deleted the list “{name}”. The names typed stay until you clear them.")

    def _delete_preset(self, name):
        nxt = {k: v for k, v in self.saved_presets.items() if k != name}
        err = config.write("presets.json", nxt, "Presets")
        if err:
            self._msg(err)
            return
        self.saved_presets = nxt
        self.sidebar.fill_presets(nxt)
        self._msg(f"Deleted preset “{name}”.")

    def _restore(self):
        if not self.remember:
            return False
        last = config.read("last-settings.json")
        if not last:
            return False
        s = Settings.from_dict({**Settings().to_dict(), **Settings.from_dict(last).to_dict()})
        if "seed" not in last and "seed" not in {k.lower() for k in last}:
            s = replace(s, seed=new_seed())
        self.state.settings = replace(s, testpage=False)
        return True

    def remember_soon(self):
        if self.remember:
            self._remember_timer.start()

    def _save_settings(self):
        config.write("last-settings.json", self.state.settings.to_dict(), "Settings")

    # --- saving and printing ----------------------------------------------------------------------------
    def _ask_path(self, title, name, ext, filt):
        path, _ = QFileDialog.getSaveFileName(self, title, os.path.join(self.last_dir, f"{name}.{ext}"), filt)
        if not path:
            return None
        if not path.lower().endswith("." + ext):
            path += "." + ext
        self.last_dir = os.path.dirname(path)
        return path

    def save(self, kind):
        if self._busy_saving:
            return
        s, st = self.state.settings, self.state
        btn = {"png": self.sidebar.png_btn, "pdf": self.sidebar.pdf_btn, "svg": self.sidebar.svg_btn}[kind]
        if not btn.isEnabled():   # the menu and shortcuts do what the button would: nothing, and say why
            if kind == "svg" and s.mode != "make" and s.style not in photo.VECTOR_STYLES:
                self._msg("Photos are made of pixels, so they save as PNG or PDF. Choose Engraving, Stippling, Colour by number or Nonogram for SVG.")
            elif kind == "png" and s.poster:
                self._msg("Posters save as PDF (one page per sheet) or print directly.")
            return
        snap = State(replace(s), [replace(p) for p in st.photos], st.sel, st.page)
        if kind == "pdf":
            j = self._job(snap)
            if j is None:
                return
            what = ("Save PDF of " + j.amount() if j.label == "copies" else f"Save {j.label} PDF") if j.count > 1 \
                else "Save PDF"
            path = self._ask_path(what, j.name, "pdf", "PDF document (*.pdf)")
            if not path:
                self._msg("Save cancelled.")
                return
            dev = QPdfWriter(path)
            dev.setPageLayout(jobs.page_layout(s, j.orient))
            dev.setResolution(j.geometry.dpi)
            dev.setTitle(j.name)
            dev.setCreator("Inkline")
            done = f"Saved {j.amount()} as {os.path.basename(path)}" if j.count > 1 else f"Saved {os.path.basename(path)}"
            self._start(j, dev, done, f"Couldn't write {path}. Check the folder permissions.",
                        stopped="Save cancelled: the PDF wasn't kept.", path=path)
            return
        ext, filt = ("png", "PNG image (*.png)") if kind == "png" else ("svg", "SVG vector image (*.svg)")

        def work():
            if kind == "png":
                img, nm = jobs.png(snap)
                return ("png", img, nm)
            text, nm = jobs.svg(snap)
            return ("svg", text, nm)
        self._pending_save = (kind, ext, filt)
        self._busy(True, "Rendering page 1 of 1…")
        self.worker.submit(work)

    def _job(self, snap):
        """What Print and Save PDF produce, with the Paper section's choice of pages; None (and why, in the status
        line) when that choice doesn't make sense."""
        sb = self.sidebar
        only = sb.only_pages.text() if sb.only_row.isVisibleTo(sb) else ""
        copies = sb.copies_count() if sb.copies_row.isVisibleTo(sb) else 1
        try:
            names = sb.copies_names_list() if sb.copies_row.isVisibleTo(sb) else []
            # a switch that isn't shown doesn't count (one copy has no answer pages)
            answers = sb.copies_answers.isVisibleTo(sb) and sb.copies_answers.isChecked()
            return jobs.job(snap, only, copies, sb.copies_vary.isChecked(), answers, names)
        except ValueError as why:
            self._msg(f"{why} Fix the pages under Paper → Print or save only, or clear it to use every page.")
            self.sidebar.only_pages.setFocus()
            return None

    def print_(self):
        if self._busy_saving:
            return
        st = self.state
        snap = State(replace(st.settings), [replace(p) for p in st.photos], st.sel, st.page)
        j = self._job(snap)
        if j is None:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageLayout(jobs.page_layout(snap.settings, j.orient))
        printer.setFullPage(True)
        printer.setDocName(j.name)
        printer.setColorMode(QPrinter.ColorMode.GrayScale)
        if j.duplex:   # fold-and-staple books: double-sided, flipping on the short edge
            printer.setDuplex(QPrinter.DuplexMode.DuplexShortSide)
        self._msg("Opening the print dialog…")
        dialog = QPrintDialog(printer, self)
        # which pages print is chosen under Paper → Print or save only: the dialog's own range would be ignored
        dialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintPageRange, False)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            self._msg("Print cancelled.")
            return
        self._remember_printer(printer.printerName())
        sent = j.amount() if j.duplex or j.label == "copies" else f"{j.count} {j.unit}s"
        done = f"Sent {sent} to the printer." if j.count > 1 else "Sent to the printer."
        times = printer.copyCount()   # the dialog's own Copies prints the whole job that many times
        if times > 1:
            done = done[:-1] + (f", {times} times over" if j.count > 1 else f", {times} copies") \
                + " (Copies in the print dialog)."
        self._start(j, printer, done, "The printer didn't accept the job. Check that it's connected.",
                    stopped="Printing cancelled: nothing was sent to the printer.")

    def _remember_printer(self, name):
        jobs.forget_printer_margins()   # the printers, or the system's default, may have changed
        if self.remember and name and name != self.printer_name:
            self.printer_name = name
            err = config.write("printer.json", {"name": name}, "Printer")
            if err:
                self._msg(err)
        self._show_printer_edges()

    def _start(self, j, device, done, failed, stopped="Cancelled.", path=None):
        """Draw a print or PDF job on the worker. stopped: the status line if it's cancelled; path: the PDF being
        written, deleted then."""
        self._device = device   # kept alive while the worker draws on it
        self._cancel.clear()
        self._job_path, self._job_stopped = path, stopped
        sb = self.sidebar
        bar = sb.progress
        bar.setRange(0, j.count)
        bar.setValue(0)
        sb.cancel_btn.setEnabled(True)
        sb.progress_row.setVisible(j.count > 1)
        self._busy(True, f"Rendering {j.unit} 1 of {j.count}…")
        self._pending_save = None
        cancel = self._cancel
        self._job_outcome = outcome = {}
        self._job_unit = j.unit

        def progress(i):
            if not cancel.is_set():
                self.status.emit(f"Rendering {j.unit} {i + 1} of {j.count}…")
            QTimer.singleShot(0, lambda: bar.setValue(i + 1))
        self.worker.submit(lambda: ("job", jobs.run(j, device, progress, cancel.is_set, outcome), done, failed))

    def cancel_job(self):
        """Cancel (or Esc): stop the print or save after the page being drawn."""
        # only a job with a Cancel button: a single page is done in a moment (and a PNG or SVG save can't stop)
        if not self._busy_saving or self._cancel.is_set() or self._pending_save is not None \
                or not self.sidebar.progress_row.isVisible():
            return
        self._cancel.set()
        self.sidebar.cancel_btn.setEnabled(False)
        self._msg("Cancelling after this page…")

    def _job_done(self, _n, r):
        kind = r[0]
        if kind == "job":
            _k, ok, done, failed = r
            device, self._device = self._device, None
            stopped = not ok and self._cancel.is_set()
            message = self._job_stopped if stopped else done if ok else failed
            path = self._job_path
            if stopped and not path and isinstance(device, QPrinter) and device.outputFileName():
                path = device.outputFileName()   # the print dialog's "Print to file": cancelled, so not kept
                message = "Printing cancelled: the file wasn't kept."
            elif stopped and "sent" in self._job_outcome:   # this printer system can't call a job off
                n, unit = self._job_outcome["sent"], self._job_unit
                message = ("Printing stopped. " + (f"The {n} {unit}{'s' if n != 1 else ''} already drawn still went"
                           if n else "An empty job still went") + " to the printer: cancel it in your system's "
                           "print queue if you don't want it.")
            if stopped and path:   # a half-written PDF isn't kept
                try:
                    os.remove(path)
                except OSError:
                    pass
            self._job_path = None
            self._busy(False, message)
            return
        _k, data, name = r
        k, ext, filt = self._pending_save
        self._busy(False, "")
        path = self._ask_path(f"Save {ext.upper()}", name, ext, filt)
        if not path:
            self._msg("Save cancelled.")
            return
        try:
            if k == "png":
                if not data.save(path, "PNG"):
                    raise OSError
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
            self._msg(f"Saved {os.path.basename(path)}")
        except OSError:
            self._msg(f"Couldn't write {path}. Check the folder permissions.")

    def _job_failed(self, _why):
        self._job_path = None
        self._cancel.clear()
        self._busy(False, "That couldn't be finished. Check the folder permissions or the printer, then try again.")
        self._device = None

    def _busy(self, on, text):
        self._busy_saving = on
        sb = self.sidebar
        for b in (sb.print_btn, sb.png_btn, sb.pdf_btn, sb.svg_btn):
            b.setEnabled(not on)
        if not on:
            sb.progress_row.hide()
            sb.sync()
        self._msg(text)

    def _msg(self, text):
        self.status.emit(text)

    def show_history(self):
        """Every undo step in a list beside the window: choosing one goes back (or forward) to it."""
        if self._history_view is None:
            d = QDialog(self)
            d.setWindowTitle("History")
            view = QUndoView(self.history, d)
            view.setEmptyLabel("Start")    # the top row: how things were before the first step
            lay = QVBoxLayout(d)
            lay.setContentsMargins(8, 8, 8, 8)
            lay.addWidget(view)
            d.resize(260, 360)
            self._history_view = d
        self._history_view.show()
        self._history_view.raise_()
        self._history_view.activateWindow()

    def offer_whats_new(self):
        """At start: the first time after an update, what's changed since the version used last."""
        seen = whatsnew.due(self.version, self.remember)
        if seen is None:
            return False
        return self.show_whats_new(seen or None)

    def show_whats_new(self, seen=None):
        text = whatsnew.notes(self.version, seen)
        if not text:
            if seen is None:   # from the Help menu: say so rather than show nothing
                self._msg("There are no release notes for this version of Inkline.")
            return False
        whatsnew.WhatsNew(self, self.version, text).exec()
        return True

    def _about(self):
        QMessageBox.about(self, "About Inkline", f"<b>Inkline {self.version}</b><br>Black &amp; white images for printing: "
                                                 "colouring pages, puzzles, booklets, posters and photo conversions.")

    def closeEvent(self, e):
        if self._busy_saving:   # a PDF or print job is still drawing from the work
            self._msg("Cancel the save or print (or wait for it to finish), then close Inkline.")
            e.ignore()
            return
        # unsaved changes to a project, or to photos (they aren't remembered), ask first; untitled settings
        # are remembered as before
        if (self.project_path is not None or self.state.photos) and not self._ask_to_save():
            e.ignore()
            return
        if self.remember and self._remember_timer.isActive():
            self._save_settings()
        self._release_clipboard()
        if self.keeper is not None:   # closed properly: nothing to recover
            self._keep_timer.stop()
            self.keeper.finish()
            recovery.release()
        super().closeEvent(e)
