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

from PySide6.QtCore import QEvent, QMimeData, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QGuiApplication, QImage, QKeySequence, QShortcut, QUndoCommand, QUndoStack
from PySide6.QtPrintSupport import QAbstractPrintDialog, QPrintDialog, QPrinter
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSlider, QAbstractSpinBox, QApplication, QComboBox, QDialog,
                               QFileDialog, QHBoxLayout, QInputDialog, QLineEdit, QMainWindow, QMenu, QMenuBar, QMessageBox,
                               QStackedWidget, QUndoView, QVBoxLayout, QWidget)
from PySide6.QtGui import QPdfWriter

from inkengine import ages, book, pack, photo
from inkengine import i18n
from inkengine.i18n import tr
from inkengine.page import PAGE_KEYS, Settings, clean_page, design_box, geometry, single_page
from inkengine.patterns import NAMES

from . import android_print, config, jobs, project, recovery, settings, theme, update_ui, whatsnew
from .layout import BottomBar, MenuButton
from .preview import ZOOM_STEP, Preview
from .render import PREVIEW_DPI, Renderer, render_view, view
from .sample import sample_photo
from .sidebar import MARGINS, MAX_BOOK_PAGES, MAX_PHOTOS, Sidebar
from .state import BUILTIN_PRESETS, State, new_seed

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)"
MAX_RECENT = 10      # File → Open recent lists this many photos
TRANSLATE_URL = "https://github.com/Gshoe2006/inkline/blob/main/docs/translating.md"   # Help → Help translate Inkline

# What Edit → Undo says for a change to each setting ("Undo Complexity"); others use the setting's name.
STEP_NAMES = {"gen": "Pattern", "complexity": "Complexity", "weight": "Line weight", "frame": "Border", "cbn": "Colour by number",
              "cbn_colours": "Colours", "seed": "New design", "page_seeds": "New design for this page", "booklet": "Booklet",
              "pages": "Design pages", "ramp": "Get harder", "mix": "Mix every pattern", "cover": "Cover page",
              "page_nums": "Page numbers", "key": "Answer pages", "maze_shape": "Maze shape", "maze_word": "Word or name", "spot_base": "Picture",
              "ws_theme": "Words from", "ws_words": "Your words", "name_text": "Name or word", "name_bg": "Around the letters",
              "maths_kind": "Sums", "money": "Money", "clock_task": "Clocks", "frac_kind": "Worksheet", "ruled_kind": "Paper", "reward_kind": "Reward", "reward_text": "Reward for", "bingo_kind": "Bingo", "early_kind": "Early maths", "bingo_theme": "Bingo words from", "bingo_words": "Your bingo words", "crypto_code": "Code", "crypto_source": "Put in code", "crypto_text": "Text in code", "ladder_kind": "Ladder help", "cal_kind": "Calendar", "cal_month": "Month", "cal_year": "Year", "cal_start": "Week starts on", "cal_art": "Picture", "scramble_kind": "Unscramble sheet", "speed_count": "Facts", "speed_tables": "Tables", "speed_order": "Order", "speed_op": "Facts to answer", "speed_chart": "Progress chart", "draw_source": "Sentences", "draw_text": "Your sentences", "coord_kind": "Coordinate grid", "memory_kind": "Cards", "memory_words": "Your pairs", "memory_backs": "Card backs", "pack_theme": "Worksheet pack", "pack_words": "Spelling words", "pack_days": "Worksheet pack days", "easy_read": "Easier to read", "cream": "Cream paper", "trace_source": "Trace", "trace_style": "Letters", "trace_hand": "Handwriting style", "trace_text": "Words to trace",
              "cbn_maths": "Colour by maths", "age": "Age", "sheet": "On the sheet", "panel_gens": "Designs on the sheet", "cross_theme": "Crossword words", "cross_words": "Crossword words and clues",
              "mode": "Mode", "style": "Style", "brightness": "Brightness", "contrast": "Contrast", "threshold": "Threshold",
              "dot": "Dot size", "fit": "Placement", "invert": "Invert", "pnono_size": "Squares across",
              "pnono_answer": "Show the answer", "pdots_n": "Dots", "pdots_answer": "Show the answer", "pcbn_colours": "Colours", "photobook": "Photo book", "pcover": "Cover page",
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
            return tr(STEP_NAMES["mode"])
        if [id(p) for p in self.photos] != [id(p) for p in before.photos]:
            n, m = len(self.photos), len(before.photos)
            return tr("Add photos") if n > m else tr("Remove photo") if n < m else tr("Move photo")
        if self.crops != before.crops:
            return tr("Crop")
        a, b = self.settings.to_dict(), before.settings.to_dict()
        changed = [k for k in a if a[k] != b[k]]
        if "page_list" in changed and self.settings.page_list and before.settings.page_list:
            # a page's own setting changed: its top-level copy changed with it, and names the step
            pa, pb = self.settings.page_list, before.settings.page_list
            if len(pa) == len(pb):
                keys = {k for x, y in zip(pa, pb) for k in set(x) | set(y) if x.get(k) != y.get(k)}
                changed = sorted(keys) if keys else changed
        if len(changed) == 1:
            return tr(STEP_NAMES.get(changed[0], changed[0].replace("_", " ").capitalize()))
        return tr("Changes")


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
        printers = config.read("printer.json") if remember else {}
        self.printer_name = printers.get("name", "")   # the printer last printed to: its edges show on the preview
        if not isinstance(self.printer_name, str):
            self.printer_name = ""
        self.print_with = printers.get("default", "")  # Edit → Settings' printer, which Print starts with
        if not isinstance(self.print_with, str):
            self.print_with = ""
        self._view = None
        recent = config.read("recent.json") if remember else {}
        self.recent = [p for p in recent.get("photos", []) if isinstance(p, str)][:MAX_RECENT]
        self.recent_projects = [p for p in recent.get("projects", []) if isinstance(p, str)][:MAX_RECENT]
        self.project_path = None   # the .inkline file open, if any
        self._clip_id = uuid.uuid4().hex   # marks the booklet pages this window puts on the clipboard
        restored = self._restore()
        if not restored:   # a first start: Edit → Settings' paper defaults, if chosen
            self.state.settings = replace(self.state.settings, **(settings.defaults() if remember else {}))
        self.state.mirror()
        self.last_dir = os.path.expanduser("~/Pictures") if os.path.isdir(os.path.expanduser("~/Pictures")) else os.path.expanduser("~")

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.sidebar = Sidebar(self.state, version)
        self.preview = Preview()
        # 6.0: the rail, the options it chooses, then the toolbar, the preview and the status line
        lay.addWidget(self.sidebar.rail)
        lay.addWidget(self.sidebar)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self.sidebar.toolbar)
        right.addWidget(self.preview, 1)
        right.addWidget(self.sidebar.statusbar)
        lay.addLayout(right, 1)
        if self.remember:   # the gallery's patterns: those used last
            used = config.read("preferences.json").get("recent_patterns")
            self.sidebar.recent_gens = [g for g in used if isinstance(g, str)] if isinstance(used, list) else []
            self.sidebar._fill_gallery(self.state.settings)
        self.sidebar.fill_presets(self.saved_presets)

        self.renderer = Renderer()
        self.renderer.finished.connect(self._rendered)
        self.renderer.failed.connect(self._render_failed)
        self.shown = 0   # the last preview request whose result reached the window (tests wait for it)
        self.renderer.busy.connect(lambda on: None if on or not self.renderer.idle else self.preview.set_busy(""))
        self.renderer.converting.connect(lambda: self.preview.set_busy(tr("converting photo…")))
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
        self._pending_save = None          # a PNG or SVG being drawn, before its file is chosen
        self._pan_start = None
        self.history = QUndoStack(self)
        self._history_view = None   # Edit → History…, made the first time it's opened
        self._drags = 0      # counts finished slider and photo drags, so the next drag is a new step
        self._focus_moves = 0   # leaving a field and coming back starts a new typing step
        QApplication.instance().focusChanged.connect(self._focus_moved)
        self._last = _Snapshot(self.state)
        self._restoring = False

        self._wire()
        self.updates = update_ui.Updates(self, version)
        self._menus()
        self.apply_save_format()
        # touch screens: the menus from a toolbar button, and in a phone-width window one column with a bottom bar
        self.bottom = BottomBar()
        self.bottom.setParent(self.centralWidget())   # hidden until one column: never a window of its own
        self.bottom.hide()
        self.bottom.chosen.connect(self._bottom_chosen)
        self.menu_btn = MenuButton(self._top_menus)
        self.menu_btn.presets.triggered.connect(lambda: self.sidebar.presets_btn.open(under=self.menu_btn))
        self.sidebar.toolbar.layout().addWidget(self.menu_btn)
        # Tab: the rail, the options, then the toolbar left to right and the preview (New design and More designs
        # are made with the options: put them where they're shown)
        sb = self.sidebar
        tab = [sb.presets_btn, sb.new_design, sb.more_btn, sb.pdf_btn, sb.png_btn, sb.svg_btn, sb.print_btn,
               self.menu_btn, self.preview.page]
        for a, b in zip(tab, tab[1:]):
            QWidget.setTabOrder(a, b)
        self.sidebar.page_shown.connect(self._page_shown)
        self.sidebar.synced.connect(self._match_bottom)
        self._narrow = False   # built wide, above
        self.turns = None      # the options page and the preview, taking turns (phone width)
        self.set_touch(theme.TOUCH["on"], save=False)
        # Ctrl+1 to Ctrl+5: the rail's Create, Photo, Booklet, Poster and Print, as clicking them does
        from .layout import RAIL
        for i, (key, _text) in enumerate(RAIL):
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda k=key: self._rail_key(k))
        QApplication.instance().installEventFilter(self)
        theme.follow_system(QApplication.instance(), self.preview.page.update)
        if self.state.settings.mode == "convert" and not self.state.photos:
            self.state.photos = [sample_photo()]
            self.sidebar.fill_photos()
        if restored:
            self._msg(tr("Reopened with your last settings. Presets → Start fresh resets them."))
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
        esc.activated.connect(self._escape)
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
        sb.copy_step.connect(self.step_copy)
        sb.photo_selected.connect(self._select_photo)
        sb.photo_moved.connect(self._move_photo)
        sb.photo_removed.connect(self._remove_photo)
        sb.pages_edit.connect(self._edit_pages)
        sb.book_page_selected.connect(self._select_book_page)
        sb.book_page_added.connect(self._add_book_page)
        sb.pack_make.connect(lambda: self._make_pack(tr("Make a week of worksheets")))
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
            a = QAction(tr(text), self)
            if keys:
                a.setShortcut(QKeySequence(keys))
            a.triggered.connect(fn)
            menu.addAction(a)
            return a

        f = mb.addMenu(tr("&File"))
        self._top_menus = [f]   # File, Edit, View, Help: the toolbar's Menu button holds them on a touch screen
        act(f, "Ne&w project", self.new_project)
        act(f, "Open pro&ject…", lambda: self.open_project(), "Ctrl+Shift+O")
        self.recent_projects_menu = f.addMenu(tr("Open recen&t project"))
        self.recent_projects_menu.aboutToShow.connect(self._fill_recent_projects)
        self.recent_projects_menu.setEnabled(bool(self.recent_projects))
        act(f, "Sa&ve project", self.save_project, "Ctrl+S")
        act(f, "Save project &as…", self.save_project_as, "Ctrl+Shift+S")
        f.addSeparator()
        act(f, "&Open image…", lambda: self.open_images(self.state.settings.photobook), "Ctrl+O")
        self.recent_menu = f.addMenu(tr("Open &recent image"))
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
        e = mb.addMenu(tr("&Edit"))
        self._top_menus.append(e)
        undo = self.history.createUndoAction(self, tr("&Undo"))
        undo.setShortcuts(QKeySequence.StandardKey.Undo)
        redo = self.history.createRedoAction(self, tr("&Redo"))
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
        e.addSeparator()
        act(e, "&Settings…", self.show_settings, "Ctrl+,")
        v = mb.addMenu(tr("&View"))
        self._top_menus.append(v)
        act(v, "&New design", self.new_design, "Ctrl+N")
        act(v, "&More designs…", self.more_designs, "Ctrl+Shift+N")
        act(v, "Pre&vious page\t←", lambda: self.step_page(-1))
        act(v, "Ne&xt page\t→", lambda: self.step_page(1))
        v.addSeparator()
        # the preview's own zoom, to look closer (pinching it, or Ctrl+wheel, does the same)
        page = self.preview.page
        zoom_in = act(v, "Zoom &in", lambda: page.zoom_by(ZOOM_STEP), "Ctrl++")
        zoom_in.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])   # + is shifted on most keyboards
        act(v, "Zoom &out", lambda: page.zoom_by(1 / ZOOM_STEP), "Ctrl+-")
        act(v, "&Whole page", page.reset_view, "Ctrl+0")
        v.addSeparator()
        self.act_test = act(v, "Printer &test page", self._toggle_test_page)
        self.act_test.setCheckable(True)
        v.addSeparator()
        lang_menu = v.addMenu(tr("&Language"))
        self.lang_actions = {}
        for code, name in i18n.LANGUAGES.items():   # each in its own language, so anyone can find theirs
            a = lang_menu.addAction(name)
            a.setCheckable(True)
            a.setChecked(code == i18n.LANG)
            a.triggered.connect(lambda _on=False, code=code: self._choose_language(code))
            self.lang_actions[code] = a
        self.theme_menu = v.addMenu(tr("T&heme"))   # the themes turned on in Edit → Settings → Appearance
        self.theme_menu.aboutToShow.connect(self._fill_theme_menu)
        self._fill_theme_menu()
        self.act_desktop = act(v, "Use my &desktop's style", self._toggle_desktop_style)
        self.act_desktop.setCheckable(True)
        self.act_desktop.setChecked(theme.DESKTOP["on"])
        name = theme.desktop_style_name()
        if name:
            self.act_desktop.setToolTip(tr("Look like your other apps ({name}) instead of Inkline's own style").format(
                name=name.capitalize()))
        else:   # the Flatpak, AppImage and .deb bring their own Qt, without the desktop's style plugins
            self.act_desktop.setEnabled(False)
            self.act_desktop.setToolTip(tr("This copy of Inkline brings its own Qt, which can't load your desktop's "
                                           "style. The Arch package and the .run installer use your system's Qt and can."))
        v.setToolTipsVisible(True)
        h = mb.addMenu(tr("&Help"))
        self._top_menus.append(h)
        act(h, "&What's new", lambda: self.show_whats_new())
        act(h, "T&our of the window", lambda: self.show_tour())
        act(h, "Check for &updates…", lambda: self.updates.check(asked=True))
        self.updates.add_menu(h.addMenu(tr("Check for updates au&tomatically")))
        self.act_translate = act(h, "Help t&ranslate Inkline…", self._help_translate)
        act(h, "&About Inkline", self._about)

    # --- state changes -------------------------------------------------------------------------------
    def _changed(self, key=""):
        control = self.sidebar._binds.get(key, (None,))[0]
        self._timed = isinstance(control, QAbstractSlider)   # a slider's arrow keys join; clicks don't
        self._typed = control if isinstance(control, QLineEdit) and control.hasFocus() else None
        st = self.state
        s = st.settings
        if key == "gen":   # the gallery shows the patterns used last
            self.sidebar.note_pattern(s.gen)
            if self.remember:
                config.write("preferences.json", {**config.read("preferences.json"),
                                                  "recent_patterns": self.sidebar.recent_gens[:12]}, "Preferences")
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
        more = {}
        if key == "age":   # an age: complexity and options to suit (one step with the age itself)
            more = ages.for_age(st.settings)
        elif key == "gen" and s.age != "any":   # another pattern at the age chosen: its complexity for that age
            more = ages.for_pattern(st.settings)
        if more:
            st.update(**more)
            self.sidebar.load()
            self._step_name = tr(STEP_NAMES.get(key, key))   # "Undo Age", not "Undo Changes"
        if st.book_page is not None and (key in PAGE_KEYS or more) and key != "seed":
            # the Design section edits the selected page
            st.write_page(**{k: getattr(st.settings, k) for k in [key, *more] if k in PAGE_KEYS})
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
                    and not (focus is not None and focus.objectName() == "galleryItem")   # its arrows: layout.ArrowKeys
                    and not (focus is self.preview.page and self.preview.page.zoomed()   # the arrows move the zoomed
                             and e.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right))      # view; Page Up/Down still turn
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
        self._step_name = tr("New design")   # however many settings that changed
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
                self._step_name = tr("New design")
                self._changed("seed")
            return (lambda seed: (s, replace(spec, seed=seed))), chosen, tr("page {n}").format(n=i + 1)
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
                self._step_name = tr("New design")
                self._changed("seed")
            return candidate, chosen, tr("the whole booklet (each shows page {n})").format(n=i + 1 + (1 if s.cover else 0))

        def chosen(seed):
            st.update(seed=seed, page_seeds={})   # as New design does
            self._step_name = tr("New design")
            self._changed("seed")
        # a single page, or a poster's design, shown on one page (a poster's sheets would be too small to judge)
        one = replace(s, poster=False, fold=False, booklet=False)
        return (lambda seed: (replace(one, seed=seed), single_page(replace(one, seed=seed)))), chosen, \
            tr("the poster's design (shown on one page)") if s.poster else tr("this page")

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
            self._step_name = tr("Edit pages one by one")
            st.update(page_list=[{**base, "gen": d.gen, "seed": d.seed, "complexity": d.c} for d in designs])
            st.book_sel = p.idx if p is not None and p.kind == "design" else 0
        else:
            self._step_name = tr("Back to quick booklet")
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
        self._step_name = tr("Include its answer") if on else tr("Leave its answer out")
        self.state.write_page(answer=on)
        self.sidebar.fill_pages()
        self.sidebar.sync()
        self.schedule()
        self.remember_soon()

    def _add_book_page(self):
        pl = self.state.settings.page_list
        if not pl or len(pl) >= MAX_BOOK_PAGES:
            return
        self._step_name = tr("Add page")
        new = {k: v for k, v in pl[-1].items() if k != "answer"}   # a new page has its answer, like any new page
        self.state.update(page_list=[*pl, {**new, "seed": new_seed()}])
        self.state.book_sel = len(pl)
        self._list_changed()

    def _copy_book_page(self, i):
        pl = self.state.settings.page_list
        if len(pl) >= MAX_BOOK_PAGES:
            return
        self._step_name = tr("Duplicate page")
        self.state.update(page_list=[*pl[:i + 1], {**pl[i], "seed": new_seed()}, *pl[i + 1:]])   # same settings, a new design
        self.state.book_sel = i + 1
        self._list_changed()

    def copy_pages(self, everything=False):
        """The selected page (or every page) onto the clipboard, to paste into this or another booklet."""
        if not self._listing():
            self._msg(tr("Copying pages works in a booklet built page by page: turn on Edit pages one by one."))
            return
        pl = self.state.settings.page_list
        pages = list(pl) if everything else [pl[self.state.book_sel]]
        md = QMimeData()
        # "from": this window, so closing it only touches pages it put there itself, not another Inkline's
        md.setData(PAGES_MIME, json.dumps({"app": "Inkline", "from": self._clip_id, "pages": pages}).encode("utf-8"))
        names = [NAMES.get(p.get("gen"), "page") for p in pages]
        md.setText(tr("Inkline booklet pages:") + " " + ", ".join(tr(n) for n in names))
        QGuiApplication.clipboard().setMimeData(md)
        self._msg(tr("Copied {n} pages. Paste them into a booklet with Ctrl+V.").format(n=len(pages)) if len(pages) > 1 else
                  tr("Copied page {n} ({name}). Paste it into a booklet with Ctrl+V.").format(
                      n=self.state.book_sel + 1, name=tr(names[0])))

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
            self._msg(tr("There are no pages to paste."))
            return
        if not self._listing():
            self._msg(tr("To paste pages, turn on Make a multi-page booklet, then Edit pages one by one."))
            return
        pl = self.state.settings.page_list
        room = MAX_BOOK_PAGES - len(pl)
        if room <= 0:
            self._msg(tr("A booklet holds up to {n} design pages, so there's no room to paste.").format(n=MAX_BOOK_PAGES))
            return
        kept = pages[:room]
        at = self.state.book_sel + 1
        self._step_name = tr("Paste pages") if len(kept) > 1 else tr("Paste page")
        self.state.update(page_list=[*pl[:at], *kept, *pl[at:]])
        self.state.book_sel = at
        self._list_changed()
        left = len(pages) - len(kept)
        self._msg(tr("Pasted {n} of {m} pages: a booklet holds up to {top}.").format(n=len(kept), m=len(pages), top=MAX_BOOK_PAGES)
                  if left else (tr("Pasted {n} pages after page {at}.") if len(kept) > 1 else
                                tr("Pasted 1 page after page {at}.")).format(n=len(kept), at=at))

    def _move_book_page(self, i, d):
        """Move page i by d places (↑ ↓ are ±1; a drag can be any distance)."""
        pl = list(self.state.settings.page_list)
        j = i + d
        if d == 0 or not (0 <= i < len(pl) and 0 <= j < len(pl)):
            return
        order = list(range(len(pl)))
        order.insert(j, order.pop(i))
        self._step_name = tr("Move page")
        self.state.update(page_list=[pl[k] for k in order])
        old = max(0, min(self.state.book_sel, len(pl) - 1))
        self.state.book_sel = order.index(old)   # the page being edited stays selected, wherever it went
        self._list_changed()

    def _remove_book_page(self, i):
        pl = self.state.settings.page_list
        if len(pl) < 2:
            return
        self._step_name = tr("Remove page")
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
            # Ctrl+E saves Edit → Settings' format, or PDF when that can't save this page (SVG of a photo)
            buttons = {"pdf": sb.pdf_btn, "png": sb.png_btn, "svg": sb.svg_btn}
            fmt = getattr(self, "_save_format", "pdf")
            fmt = fmt if buttons[fmt].isEnabled() else "pdf"
            second = "pdf" if fmt == "png" else "png"
            for kind, a in (("pdf", self.act_pdf), ("png", self.act_png), ("svg", self.act_svg)):
                a.setShortcut(QKeySequence("Ctrl+E" if kind == fmt else "Ctrl+Shift+E" if kind == second else ""))
            if sb.save_format != fmt:
                sb.save_format = fmt
                sb.save_tips(self.state.settings)
            for a, b in ((self.act_pdf, sb.pdf_btn), (self.act_png, sb.png_btn), (self.act_svg, sb.svg_btn)):
                a.setEnabled(b.isEnabled())
                a.setToolTip(b.toolTip())

    def _rail_key(self, key):
        b = self.sidebar.rail.buttons[key]
        if b.isEnabled():
            b.click()
        else:   # Booklet with a photo: say why nothing happened
            self._msg(tr("A photo book is made on the Photo page (Ctrl+2)."))

    # --- touch screens -------------------------------------------------------------------------------------
    def set_touch(self, on, save=True):
        """Larger controls for a finger, the menus in the toolbar, and one column below theme.ONE_COLUMN_WIDTH (Edit →
        Settings → Appearance; always on Android)."""
        theme.TOUCH["on"] = bool(on)
        self.menuBar().setVisible(not on)
        self.menu_btn.setVisible(bool(on))
        self.sidebar.keys.setVisible(not on)   # the keyboard shortcuts: no keyboard
        if on:
            self.setMinimumSize(360, 480)   # the bottom bar's six entries
        else:
            self.setMinimumSize(900, 600)
        theme.apply(QApplication.instance())
        self.preview.set_pad(theme.TOUCH_STAGE_PAD if on else theme.STAGE_PAD)
        self.preview.page.update()
        if self.state.photos:   # the lists' rows as tall as their buttons now are
            self.sidebar.fill_photos()
        if self.state.listing:
            self.sidebar.fill_pages()
        self._arrange(bool(on) and self.width() < theme.ONE_COLUMN_WIDTH)
        self._fit_tablet()
        self._fit_toolbar()
        if save and self.remember:
            err = config.write("preferences.json", {**config.read("preferences.json"), "touch": bool(on)}, "Preferences")
            if err:
                self._msg(err)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if theme.TOUCH["on"]:
            narrow = self.width() < theme.ONE_COLUMN_WIDTH
            if narrow != self._narrow:
                self._arrange(narrow)
            self._fit_tablet()
            self._fit_toolbar()

    def _arrange(self, narrow):
        """Put the same rail, options, toolbar, preview and status line in the wide layout (rail | page | preview)
        or, phone width, in one column: the toolbar, the page or the preview, the status line, the bottom bar."""
        if narrow == self._narrow:   # laid out so already (the window is built wide)
            return
        sb = self.sidebar
        focused = QApplication.focusWidget()   # moving the widgets hides them for a moment: keep the focus where it was
        parts = (sb.rail, sb, sb.toolbar, self.preview, sb.statusbar, self.bottom)
        central = QWidget()
        central.setObjectName("central")
        for w in parts:
            w.setParent(central)   # out of the old layout (the old central goes, without them)
        if narrow:
            col = QVBoxLayout(central)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(0)
            self.turns = QStackedWidget()
            self.turns.addWidget(sb)
            self.turns.addWidget(self.preview)
            col.addWidget(sb.toolbar)
            col.addWidget(self.turns, 1)
            col.addWidget(sb.statusbar)
            col.addWidget(self.bottom)
            sb.rail.hide()
            self.bottom.show()
        else:
            lay = QHBoxLayout(central)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)
            lay.addWidget(sb.rail)
            lay.addWidget(sb)
            right = QVBoxLayout()
            right.setContentsMargins(0, 0, 0, 0)
            right.setSpacing(0)
            right.addWidget(sb.toolbar)
            right.addWidget(self.preview, 1)
            right.addWidget(sb.statusbar)
            lay.addLayout(right, 1)
            self.turns = None
            self.bottom.hide()
            sb.rail.show()
        for w in (sb, sb.toolbar, self.preview, sb.statusbar):
            w.show()
        sb.set_full_width(narrow)
        self._narrow = narrow
        self._fit_toolbar()
        self.setCentralWidget(central)
        self._page_shown(sb.page_key())
        self._match_bottom()
        if focused is not None and focused.isVisible():
            focused.setFocus()

    def _fit_toolbar(self):
        """Touch-sized buttons don't all fit: the toolbar keeps what's used most, the rest being in the menus (the
        brand; Save PNG and SVG and More designs in File and View; in one column, Save PDF too)."""
        sb = self.sidebar
        touch = theme.TOUCH["on"]
        for w in (sb.brand, sb.png_btn, sb.svg_btn, sb.more_btn):
            w.setVisible(not touch)
        phone = touch and self._narrow
        sb.pdf_btn.setVisible(not phone)
        sb.presets_btn.setVisible(not phone)   # in the Menu button instead
        self.menu_btn.presets.setVisible(phone)
        m = 8 if touch and self._narrow else 14
        sb.toolbar.layout().setContentsMargins(m, 8, m, 8)
        if touch and not phone:   # a tablet: More designs too, when the toolbar has room for it
            room = self.width() - sb.rail.width() - sb.width()
            sb.toolbar.layout().invalidate()   # measured without it (hidden above)
            sb.more_btn.setVisible(sb.toolbar.sizeHint().width() + theme.PAIR_GAP + sb.more_btn.sizeHint().width() <= room)

    def _fit_tablet(self):
        """Touch, wide (a tablet held sideways): a portrait page is as tall as the window lets it be, so the room
        beside it that it can't use goes to the options, up to theme.TOUCH_SIDEBAR_WIDTH; a landscape page keeps it."""
        sb, page = self.sidebar, self.preview.page
        least = theme.SIDEBAR_WIDTH
        if theme.TOUCH["on"] and not self._narrow:
            img = page.image
            aspect = img.width() / img.height() if img is not None and img.height() else 8.5 / 11
            pad = self.preview.pad()
            needs = page.height() * aspect + 2 * pad   # the preview's width that shows the page as tall as it can be
            spare = self.width() - sb.rail.width() - theme.SIDEBAR_WIDTH - needs
            least += int(max(0, min(theme.TOUCH_SIDEBAR_WIDTH - theme.SIDEBAR_WIDTH, spare)))
        if sb.least != least:
            sb.least = least
            sb.fit_width()

    def _bottom_chosen(self, key):
        if key == "preview":
            if self.turns is not None:
                self.turns.setCurrentWidget(self.preview)
            self.bottom.show_key("preview")
            return
        self.sidebar._rail_chosen(key)

    def _page_shown(self, key):
        """A page of options shown (the bottom bar, the Ctrl+1 to 5 keys, a field revealed): in one column, the page
        rather than the preview."""
        if self.turns is not None:
            self.turns.setCurrentWidget(self.sidebar)
        self.bottom.show_key(key)

    def _match_bottom(self):
        for key, b in self.sidebar.rail.buttons.items():
            self.bottom.buttons[key].setEnabled(b.isEnabled())
            self.bottom.buttons[key].setToolTip(b.toolTip())

    # --- themes ----------------------------------------------------------------------------------------
    def themes_offered(self):
        shown = config.read("preferences.json").get("themes_offered") if self.remember else None
        return [k for k in theme.EXTRA_THEMES if isinstance(shown, list) and k in shown]

    def _fill_theme_menu(self):
        """View → Theme: following the system, light, dark, and the extras turned on in Settings."""
        self.theme_menu.clear()
        self.theme_actions = {}
        for key in theme.offered(self.themes_offered()):
            a = self.theme_menu.addAction(tr(theme.THEME_NAMES[key]))
            a.setCheckable(True)
            a.setChecked(key == theme.CHOSEN["name"])
            a.triggered.connect(lambda _on=False, k=key: self.set_theme(k))
            self.theme_actions[key] = a

    def set_theme(self, key):
        """Use a theme now, and from the next start."""
        theme.use_theme(QApplication.instance(), key)
        self.preview.page.update()
        for k, a in getattr(self, "theme_actions", {}).items():
            a.setChecked(k == key)
        if self.remember:
            err = config.write("preferences.json", {**config.read("preferences.json"), "theme": key}, "Preferences")
            if err:
                self._msg(err)
        self._msg(tr("Using the {theme} theme.").format(theme=tr(theme.THEME_NAMES[key])) if key != "system" else
                  tr("Following the system's light or dark look."))
        if theme.DESKTOP["on"]:
            self._msg(tr("Your desktop's style is on, so the theme only colours the preview. Turn it off under View to "
                         "see the theme everywhere."))

    def offer_theme(self, key, on):
        """Turn an extra theme on or off in the theme lists; turning off the one in use goes back to the system's."""
        shown = [k for k in self.themes_offered() if k != key] + ([key] if on else [])
        if self.remember:
            err = config.write("preferences.json", {**config.read("preferences.json"),
                                                    "themes_offered": [k for k in theme.EXTRA_THEMES if k in shown]},
                               "Preferences")
            if err:
                self._msg(err)
        if not on and theme.CHOSEN["name"] == key:
            self.set_theme("system")
        self._fill_theme_menu()

    def _toggle_desktop_style(self, on):
        theme.use_desktop(QApplication.instance(), on)
        self.preview.page.update()
        if self.remember:
            err = config.write("preferences.json", {**config.read("preferences.json"), "desktop_style": bool(on)},
                               "Preferences")
            if err:
                self._msg(err)
        self._msg(tr("Using your desktop's style ({name}).").format(name=theme.desktop_style_name().capitalize()) if on
                  else tr("Using Inkline's own style."))

    def _choose_language(self, code):
        """View → Language: remembered, and used from the next start (the window is built in its language)."""
        for c, a in self.lang_actions.items():
            a.setChecked(c == code)
        err = config.write("preferences.json", {**config.read("preferences.json"), "language": code}, "Preferences")
        if err:
            self._msg(err)
            return
        if code == i18n.LANG:
            self._msg(tr("Inkline is in {language}.").format(language=i18n.LANGUAGES[code]))
        else:   # said in the language chosen, which the person can read
            i18n_next = i18n.catalog(code)
            text = "Restart Inkline to use {language}."
            self._msg(i18n_next.get(text, text).format(language=i18n.LANGUAGES[code]))

    def _toggle_test_page(self):
        self.state.update(testpage=not self.state.settings.testpage)
        self.sidebar.load()
        self._changed("testpage")

    # --- photos --------------------------------------------------------------------------------------
    def open_images(self, append=False):
        files, _ = QFileDialog.getOpenFileNames(self, tr("Add photos" if append else "Open image"), self.last_dir,
                                                tr(IMAGE_FILTER))
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
            self._msg(tr("Couldn't read {files} as an image. Try PNG, JPEG or WebP.").format(files=", ".join(bad)))
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

    def step_copy(self, d):
        """The copy pager: show the class set's next or previous copy in the preview."""
        cs = self.sidebar.class_set_view()
        if cs is None:
            return
        self.state.copy = max(0, min(self.state.copy + d, cs.count - 1))
        self.schedule()

    def _class_set_changed(self):
        """Copies, Names or their switches changed: the preview (it shows one of the copies), the title's unsaved
        mark, and a recovery copy as for any change."""
        self.schedule()
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
        box = QMessageBox(QMessageBox.Icon.Question, tr("Save changes?"),
                          tr("Save the changes to “{name}”?").format(name=name) if name else tr("Save your work as a project first?"),
                          QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                          | QMessageBox.StandardButton.Cancel, self)
        box.button(QMessageBox.StandardButton.Discard).setText(tr("Don't save"))
        box.setInformativeText(tr("Your changes will be lost if you don't save them."))
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        answer = box.exec()
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def _use_project(self, proj, path):
        """Make what the project holds the work in the window, with a fresh history."""
        st = self.state
        st.settings, st.photos, st.sel, st.book_sel, st.page = proj.settings, list(proj.photos), proj.sel, proj.book_sel, 0
        st.copy = 0   # another class set: its first copy
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
        fresh = replace(State().settings, **(settings.defaults() if self.remember else {}))
        self._use_project(project.Project(fresh), None)
        self._msg(tr("New project, with your paper settings from Edit → Settings.") if self.remember and settings.defaults()
                  else tr("New project. Settings are back to their defaults."))

    def open_project(self, path=None):
        asked = path is None
        if asked:   # asked before the file is chosen, as other apps do
            if not self._ask_to_save():
                return False
            path, _ = QFileDialog.getOpenFileName(self, tr("Open project"), self.last_dir, tr(project.FILTER))
            if not path:
                return False
        name = os.path.basename(path)
        if not os.path.isfile(path):   # found missing before asking about the work open now
            self._msg(tr("Couldn't find {name}. It may have been moved or deleted.").format(name=name))
            if path in self.recent_projects:
                self._set_recent_projects([p for p in self.recent_projects if p != path])
            return False
        if not asked and not self._ask_to_save():
            return False
        try:
            proj = project.load(path)
        except project.ProjectError as why:
            self._msg(tr("Couldn't open {name}: it {why}. Choose another project, or a copy of this one.").format(
                name=name, why=tr(str(why))))
            return False
        except OSError:
            self._msg(tr("Couldn't open {name}. Check that you're allowed to read it.").format(name=name))
            return False
        self.last_dir = os.path.dirname(os.path.abspath(path))
        self._use_project(proj, os.path.abspath(path))
        self._add_recent_project(self.project_path)
        lost = proj.skipped
        self._msg(((tr("Opened {name}, without {n} damaged photos.") if lost > 1 else
                    tr("Opened {name}, without 1 damaged photo.")) if lost else tr("Opened {name}.")).format(name=name, n=lost))
        return True

    def save_project(self):
        if self.project_path is None:
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self):
        name = project.title(self.project_path) if self.project_path else tr("My project")
        path = self._ask_path(tr("Save project"), name, project.EXT, project.FILTER)
        return self._write_project(path) if path else False

    def _write_project(self, path):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)   # big photos take a moment to pack
        try:
            cs = self.sidebar.class_set()
            project.save(path, self.state, self.version, project.class_set_json(cs))
        except (OSError, ValueError):
            self._msg(tr("Couldn't save {name}. Check that the folder exists and you can write to it.").format(
                name=os.path.basename(path)))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.project_path = os.path.abspath(path)
        self._saved_class_set = project.class_set(cs)
        self.history.setClean()
        self._keep_copy()           # saved: the recovery copy goes
        self._update_title()
        self._add_recent_project(self.project_path)
        self._msg(tr("Saved {name}.").format(name=os.path.basename(path)))
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
            box = QMessageBox(QMessageBox.Icon.Question, tr("Recover unsaved work?"),
                              tr("Inkline closed before your work was saved. Recover it?"),
                              QMessageBox.StandardButton.Discard, self)
            recover = box.addButton(tr("Recover"), QMessageBox.ButtonRole.AcceptRole)
            box.setInformativeText(recovery.describe(path, data))
            box.setDefaultButton(recover)
            box.exec()
            if box.clickedButton() is recover:
                src = (data.get("recovery") or {}).get("project")
                self._use_project(proj, src if isinstance(src, str) and src else None)
                self.history.resetClean()   # recovered, not saved: the title shows it and closing asks
                self._update_title()
                self._keep_copy()           # this session keeps it now
                self._msg(tr("Recovered your unsaved work. Save it as a project to keep it."))
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
            self._msg(tr("Couldn't find {name}. It may have been moved or deleted.").format(name=os.path.basename(path)))
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
                self._msg(tr("A photo book holds up to {n} photos.").format(n=MAX_PHOTOS))
                return
            if len(new) > room:
                self._msg(tr("Added {n} photos; a photo book holds up to {top}.").format(n=room, top=MAX_PHOTOS))
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
        self.preview.set_busy(tr("rendering…"))
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
        snap = State(replace(st.settings), [replace(p) for p in st.photos], st.sel, st.page,
                     copy=st.copy, class_set=self.sidebar.class_set_view())
        self.renderer.submit(lambda: render_view(snap))

    def _render_failed(self, n, _why):
        self.shown = max(self.shown, n)
        self._msg(tr("The preview couldn't be drawn. Try another setting, or start fresh from Presets."))

    @property
    def preview_settled(self):
        """Every preview asked for has been drawn and shown: nothing scheduled, drawing or on its way."""
        return not self._render_timer.isActive() and self.renderer.idle and self.shown == self.renderer.latest

    def _rendered(self, n, r):
        self.shown = max(self.shown, n)
        if n != self.renderer.latest:
            return
        self.state.page = r.view.index
        self.state.copy = r.view.copy
        what = (self.state.settings.mode, self.state.settings.gen, self.project_path)
        if what != getattr(self, "_zoomed_on", what):   # another mode, pattern or project: the whole page again
            self.preview.page.reset_view()
        self._zoomed_on = what
        self.preview.page.set_image(r.image, r.poster)
        self.preview.page.set_pannable(self.state.settings.mode == "convert" and bool(self.state.photos)
                                       and r.view.kind not in ("fold", "testpage"))
        self.preview.set_info(r.info)
        self.preview.page.setAccessibleDescription(self._page_description(r.view))
        if theme.TOUCH["on"]:   # a page of another shape: the room beside it changes
            self._fit_tablet()
            self._fit_toolbar()
        self.preview.set_busy("")
        self.sidebar.ws_note.setText(r.note)
        self.sidebar.cross_note.setText(r.note)
        self.sidebar.sync(r.view)
        self._view = r.view
        self._show_printer_edges()

    def _page_description(self, v):
        """What a screen reader says the preview shows: "Page 2 of 10: Maze", or the design's (or photo's) name."""
        s, ph = self.state.settings, self.state.photo
        if v.kind == "testpage":
            return tr("Printer test page")
        if v.kind in ("booklet", "photobook") and v.pages:
            p = v.pages[v.index]
            what = (os.path.basename(getattr(p.photo, "name", "")) if p.kind == "photo"
                    else tr(NAMES.get(p.gen, p.gen)) if p.kind == "design" else "")   # a cover's label says so
            return tr("{page}: {what}").format(page=v.label, what=what) if what else v.label
        if v.kind == "fold":
            return v.label
        what = os.path.basename(ph.name) if s.mode == "convert" and ph else tr(NAMES.get(s.gen, s.gen))
        return tr("{page}: {what}").format(page=tr("Poster"), what=what) if v.kind == "poster" else what

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
        fix = tr("Choose a {margin} margin or more.").format(margin=tr(enough)) if enough else \
            tr("No margin choice is wide enough for it.")
        self.sidebar.set_margin_warning(tr("{printer} can't print the outer {reach} in of the page, so the design will be "
                                           "cut off.").format(printer=name, reach=reach) + " " + fix)

    # --- presets and remembered settings -------------------------------------------------------------
    def _apply_preset(self, group, name):
        p = BUILTIN_PRESETS.get(name) if group == "b" else self.saved_presets.get(name)
        if p is None:
            return
        self._step_name = tr("“{name}”").format(name=tr(name) if group == "b" else name)   # Edit → Undo “Maze booklet with answers”
        if p.get("pack"):   # a worksheet pack: its pages are made for the age and theme chosen now
            self._make_pack(self._step_name)
            return
        self.state.apply_preset(p)
        self.state.mirror()
        self.sidebar.only_pages.clear()
        self.sidebar.load()
        self.sidebar.fill_pages()
        if self.state.settings.mode == "convert" and not self.state.photos:
            self.state.photos = [sample_photo()]
            self.sidebar.fill_photos()
        self._msg(tr("Applied “{name}”.").format(name=tr(name)))
        self.schedule()
        self.remember_soon()

    def _make_pack(self, step):
        """Booklet → Make a week of worksheets (or its preset): five pages for the age and theme chosen, one undo step."""
        self._step_name = step
        self.state.update(**pack.week(self.state.settings, [new_seed() for _ in pack.DAYS]))
        self.state.page = self.state.book_sel = 0
        self.state.mirror()
        self.sidebar.only_pages.clear()
        self.sidebar.load()
        self.sidebar.fill_pages()
        s = self.state.settings
        self._msg(tr("Made a week of worksheets for {age}: {theme}. Change any page in the page list.").format(
            age=tr(ages.AGES[s.age]).lower(), theme=tr(pack.THEME_NAMES[s.pack_theme]).lower()))
        self.schedule()
        self.remember_soon()

    def _save_preset(self, name):
        if not name:
            self._msg(tr("Type a name for the preset first."))
            phone = self.sidebar.presets_btn.isHidden()   # in the Menu button, in one column
            self.sidebar.presets_btn.open(under=self.menu_btn if phone else None)   # the panel the name is typed in
            self.sidebar.preset_name.setFocus()
            return
        if name in BUILTIN_PRESETS:
            self._msg(tr("That name belongs to a built-in preset. Choose another."))
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
        self._msg((tr("Updated preset “{name}”.") if existed else tr("Saved preset “{name}”.")).format(name=name))

    def _save_class_list(self, chosen):
        """Paper → Names → Save…: keep the names typed as a list, under a name (the chosen list's, to update it)."""
        names = self.sidebar.copies_names.text().strip()
        if not jobs.parse_names(names):
            self._msg(tr("Type or paste the names first, then save them as a list."))
            self.sidebar.reveal(self.sidebar.copies_names)
            self.sidebar.copies_names.setFocus()
            return
        name, ok = QInputDialog.getText(self, tr("Save class list"), tr("Name for this list:"), text=chosen)
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
        self._msg((tr("Updated the list “{name}”.") if existed else tr("Saved the list “{name}”.")).format(name=name))

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
        self._msg(tr("Deleted the list “{name}”. The names typed stay until you clear them.").format(name=name))

    def _delete_preset(self, name):
        nxt = {k: v for k, v in self.saved_presets.items() if k != name}
        err = config.write("presets.json", nxt, "Presets")
        if err:
            self._msg(err)
            return
        self.saved_presets = nxt
        self.sidebar.fill_presets(nxt)
        self._msg(tr("Deleted preset “{name}”.").format(name=name))

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
        path, _ = QFileDialog.getSaveFileName(self, title, os.path.join(self.last_dir, f"{name}.{ext}"), tr(filt))
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
                self._msg(tr("Photos are made of pixels, so they save as PNG or PDF. Choose Engraving, Stippling, Colour by number or Nonogram for SVG."))
            elif kind == "png" and s.poster:
                self._msg(tr("Posters save as PDF (one page per sheet) or print directly."))
            return
        snap = State(replace(s), [replace(p) for p in st.photos], st.sel, st.page,
                     copy=st.copy, class_set=self.sidebar.class_set_view())   # PNG and SVG: the copy shown
        if kind == "pdf":
            j = self._job(snap)
            if j is None:
                return
            what = (tr("Save PDF of {what}").format(what=j.amount()) if j.label in ("copies", "booklets") or j.backs
                    else tr("Save {what} PDF").format(what=tr(j.label))) if j.count > 1 else tr("Save PDF")
            path = self._ask_path(what, j.name, "pdf", "PDF document (*.pdf)")
            if not path:
                self._msg(tr("Save cancelled."))
                return
            dev = QPdfWriter(path)
            dev.setPageLayout(jobs.page_layout(s, j.orient))
            dev.setResolution(j.geometry.dpi)
            dev.setTitle(j.name)
            dev.setCreator("Inkline")
            done = (tr("Saved {what} as {name}") if j.count > 1 else tr("Saved {name}")).format(
                what=j.amount(), name=os.path.basename(path))
            self._start(j, dev, done, tr("Couldn't write {path}. Check the folder permissions.").format(path=path),
                        stopped=tr("Save cancelled: the PDF wasn't kept."), path=path)
            return
        ext, filt = ("png", "PNG image (*.png)") if kind == "png" else ("svg", "SVG vector image (*.svg)")

        def work():
            if kind == "png":
                img, nm = jobs.png(snap)
                return ("png", img, nm)
            text, nm = jobs.svg(snap)
            return ("svg", text, nm)
        self._pending_save = (kind, ext, filt)
        self._busy(True, tr("Rendering page {i} of {n}…").format(i=1, n=1))
        self.worker.submit(work)

    def _job(self, snap):
        """What Print and Save PDF produce, with the Paper section's choice of pages; None (and why, in the status
        line) when that choice doesn't make sense."""
        sb = self.sidebar
        only = sb.only_pages.text() if sb.shown(sb.only_row) else ""
        copies = sb.copies_count() if sb.shown(sb.copies_row) else 1
        try:
            names = sb.copies_names_list() if sb.shown(sb.copies_row) else []
            # a switch that isn't shown doesn't count (one copy has no answer pages)
            answers = sb.shown(sb.copies_answers) and sb.copies_answers.isChecked()
            book = sb.shown(sb.copies_answer_book) and sb.copies_answer_book.isChecked()
            return jobs.job(snap, only, copies, sb.copies_vary.isChecked(), answers, names, book)
        except ValueError as why:
            self._msg(tr("{why} Fix the pages under Paper → Print or save only, or clear it to use every page.").format(
                why=why))
            self.sidebar.reveal(self.sidebar.only_pages)   # Print is in the toolbar: the field may be out of view
            self.sidebar.only_pages.setFocus()
            return None

    def print_(self):
        if self._busy_saving:
            return
        st = self.state
        # cream paper is for screens and PDFs: a printer gets white (no ink spent colouring the page)
        snap = State(replace(st.settings, cream=False), [replace(p) for p in st.photos], st.sel, st.page)
        j = self._job(snap)
        if j is None:
            return
        if android_print.available():   # no Qt print dialog on Android: a PDF, for Android's own
            return self._print_android(j, snap)
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageLayout(jobs.page_layout(snap.settings, j.orient))
        printer.setFullPage(True)
        printer.setDocName(j.name)
        printer.setColorMode(QPrinter.ColorMode.GrayScale)
        if self.print_with and self.print_with in settings.printers():   # Edit → Settings' choice
            printer.setPrinterName(self.print_with)
        if j.duplex:   # fold-and-staple books: double-sided, flipping on the short edge
            printer.setDuplex(QPrinter.DuplexMode.DuplexShortSide)
        elif j.backs:  # memory cards and their backs: double-sided, flipping on the long edge
            printer.setDuplex(QPrinter.DuplexMode.DuplexLongSide)
        self._msg(tr("Opening the print dialog…"))
        dialog = QPrintDialog(printer, self)
        # which pages print is chosen under Paper → Print or save only: the dialog's own range would be ignored
        dialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintPageRange, False)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            self._msg(tr("Print cancelled."))
            return
        self._remember_printer(printer.printerName())
        sent = j.amount()
        times = printer.copyCount()   # the dialog's own Copies prints the whole job that many times
        if times > 1:
            done = (tr("Sent {what} to the printer, {times} times over (Copies in the print dialog).") if j.count > 1
                    else tr("Sent to the printer, {times} copies (Copies in the print dialog).")).format(what=sent, times=times)
        else:
            done = tr("Sent {what} to the printer.").format(what=sent) if j.count > 1 else tr("Sent to the printer.")
        self._start(j, printer, done, tr("The printer didn't accept the job. Check that it's connected."),
                    stopped=tr("Printing cancelled: nothing was sent to the printer."))

    def _print_android(self, j, snap):
        """Write the job as a PDF (as Save PDF does), then open Android's print dialog for it."""
        path = android_print.job_path(j.name)
        dev = QPdfWriter(path)
        dev.setPageLayout(jobs.page_layout(snap.settings, j.orient))
        dev.setResolution(j.geometry.dpi)
        dev.setTitle(j.name)
        dev.setCreator("Inkline")

        def opened():
            try:
                android_print.print_pdf(path, j.name, duplex=j.duplex)
            except OSError as e:
                self._msg(tr("Android's print dialog didn't open ({why}). Save a PDF and print it from another app.").format(
                    why=e))
                return
            self._msg(tr("Choose a printer in Android's print dialog."))
        self._start(j, dev, tr("Opening Android's print dialog…"),
                    tr("Couldn't write {path}. Check the folder permissions.").format(path=path),
                    stopped=tr("Printing cancelled: nothing was sent to the printer."), path=path, then=opened)

    # --- Edit → Settings ------------------------------------------------------------------------------
    def show_settings(self):
        settings.SettingsDialog(self).exec()

    def set_printer(self, name):
        """The printer Print starts with ("" for the system's default); its margins show on the preview until
        another is printed to."""
        jobs.forget_printer_margins()
        self.print_with = name or ""
        self.printer_name = self.print_with
        if self.remember:
            err = config.write("printer.json", {"name": self.printer_name, "default": self.print_with}, "Printer")
            if err:
                self._msg(err)
        self._show_printer_edges()

    def set_save_format(self, fmt):
        if self.remember:
            err = config.write("preferences.json", {**config.read("preferences.json"), "save_format": fmt}, "Preferences")
            if err:
                self._msg(err)
                return
        self.apply_save_format(fmt)
        self._msg(tr("Ctrl+E now saves {format}.").format(format=tr(settings.FORMATS[fmt])))

    def apply_save_format(self, fmt=None):
        """Ctrl+E saves fmt (PDF unless Settings says otherwise); Ctrl+Shift+E saves PNG, or PDF when PNG has Ctrl+E."""
        self._save_format = fmt or (settings.save_format() if self.remember else "pdf")
        self._sync_actions()

    def use_paper(self, values):
        """Put Settings' paper defaults on the design open now, as if chosen in the Paper section (Undo takes it
        back)."""
        changed = [k for k, v in values.items() if getattr(self.state.settings, k) != v]
        if changed:   # one step, however many of them change
            self.state.update(**{k: values[k] for k in changed})
            self.sidebar.load()
            self._step_name = tr("Use my paper settings")
            self._changed(changed[0])
        self._msg(tr("The design now uses your paper settings.") if changed else
                  tr("The design already uses your paper settings."))

    def _remember_printer(self, name):
        jobs.forget_printer_margins()   # the printers, or the system's default, may have changed
        if self.remember and name and name != self.printer_name:
            self.printer_name = name
            err = config.write("printer.json", {"name": name, "default": self.print_with}, "Printer")
            if err:
                self._msg(err)
        self._show_printer_edges()

    def _start(self, j, device, done, failed, stopped="", path=None, then=None):
        """Draw a print or PDF job on the worker. stopped: the status line if it's cancelled; path: the PDF being
        written, deleted then; then(): what to do once it's written (Android: open its print dialog)."""
        self._device = device   # kept alive while the worker draws on it
        self._job_then = then
        self._cancel.clear()
        self._job_path, self._job_stopped = path, stopped or tr("Cancelled.")
        sb = self.sidebar
        bar = sb.progress
        bar.setRange(0, j.count)
        bar.setValue(0)
        sb.cancel_btn.setEnabled(True)
        sb.progress_row.setVisible(j.count > 1)
        rendering = tr("Rendering sheet {i} of {n}…") if j.unit == "sheet" else tr("Rendering page {i} of {n}…")
        self._busy(True, rendering.format(i=1, n=j.count))
        self._pending_save = None
        cancel = self._cancel

        def progress(i):
            if i >= j.count:   # a print: every page drawn, now it goes to the printer (and can't be stopped)
                self.status.emit(tr("Sending to the printer…"))
                QTimer.singleShot(0, lambda: sb.cancel_btn.setEnabled(False))
            elif not cancel.is_set():
                self.status.emit(rendering.format(i=i + 1, n=j.count))
            QTimer.singleShot(0, lambda: bar.setValue(i + 1))
        self.worker.submit(lambda: ("job", jobs.run(j, device, progress, cancel.is_set), done, failed))

    def _escape(self):
        """Esc: closes the tour if it's showing, else cancels a print or save."""
        t = getattr(self, "_tour", None)
        if t is not None and t.isVisible():
            t.finish()
            return
        self.cancel_job()

    def cancel_job(self):
        """Cancel (or Esc): stop the print or save after the page being drawn."""
        # only a job with a Cancel button: a single page is done in a moment (and a PNG or SVG save can't stop)
        if not self._busy_saving or self._cancel.is_set() or self._pending_save is not None \
                or not self.sidebar.progress_row.isVisible() or not self.sidebar.cancel_btn.isEnabled():
            return
        self._cancel.set()
        self.sidebar.cancel_btn.setEnabled(False)
        self._msg(tr("Cancelling after this page…"))

    def _job_done(self, _n, r):
        kind = r[0]
        if kind == "job":
            _k, ok, done, failed = r
            device, self._device = self._device, None
            stopped = not ok and self._cancel.is_set()
            message = self._job_stopped if stopped else done if ok else failed
            path = self._job_path
            if stopped and not path and isinstance(device, QPrinter) and device.outputFileName():
                path = device.outputFileName()   # the print dialog's "Print to file": nothing written, or not kept
                message = tr("Printing cancelled: no file was written.")
            if stopped and path and os.path.exists(path):   # a half-written PDF isn't kept
                try:
                    os.remove(path)
                except OSError:
                    pass
            self._job_path = None
            self._busy(False, message)
            then, self._job_then = getattr(self, "_job_then", None), None
            if ok and then is not None:
                then()
            return
        _k, data, name = r
        k, ext, filt = self._pending_save
        self._busy(False, "")
        path = self._ask_path(tr("Save {kind}").format(kind=ext.upper()), name, ext, filt)
        if not path:
            self._msg(tr("Save cancelled."))
            return
        try:
            if k == "png":
                if not data.save(path, "PNG"):
                    raise OSError
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
            self._msg(tr("Saved {name}").format(name=os.path.basename(path)))
        except OSError:
            self._msg(tr("Couldn't write {path}. Check the folder permissions.").format(path=path))

    def _job_failed(self, _why):
        self._job_path = None
        self._cancel.clear()
        self._busy(False, tr("That couldn't be finished. Check the folder permissions or the printer, then try again."))
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
            d.setWindowTitle(tr("History"))
            view = QUndoView(self.history, d)
            view.setEmptyLabel(tr("Start"))    # the top row: how things were before the first step
            lay = QVBoxLayout(d)
            lay.setContentsMargins(8, 8, 8, 8)
            lay.addWidget(view)
            d.resize(260, 360)
            self._history_view = d
        self._history_view.show()
        self._history_view.raise_()
        self._history_view.activateWindow()

    def show_tour(self, first=False):
        """The window's tour; the first time, finishing or skipping it is remembered."""
        from . import tour
        if getattr(self, "_tour", None) is not None and self._tour.isVisible():
            return self._tour
        self._tour = tour.Tour(self, done=(tour.mark_seen if first and self.remember else None))
        self._tour.start()
        return self._tour

    def offer_tour(self):
        """At start: the tour, the first time 6.0 opens."""
        from . import tour
        if tour.due(self.remember):
            self.show_tour(first=True)
            return True
        return False

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
                self._msg(tr("There are no release notes for this version of Inkline."))
            return False
        whatsnew.WhatsNew(self, self.version, text).exec()
        return True

    def _help_translate(self):
        """The guide to checking and improving the translations, on GitHub, in the browser."""
        QDesktopServices.openUrl(QUrl(TRANSLATE_URL))

    def _about(self):
        QMessageBox.about(self, tr("About Inkline"), f"<b>Inkline {self.version}</b><br>" + tr(
            "Black &amp; white images for printing: colouring pages, puzzles, booklets, posters and photo conversions."))

    def closeEvent(self, e):
        if self._busy_saving:   # a PDF or print job is still drawing from the work
            self._msg(tr("Cancel the save or print (or wait for it to finish), then close Inkline."))
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
