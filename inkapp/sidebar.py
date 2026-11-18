"""The left rail (2.x's aside): brand row, a scrolling column of sections, and the footer.

Every control writes straight into the window's State and says so through changed(); sync() shows
and hides the sub-options and fills in the live values, as 2.x's syncOutputs did. Labels, ranges and
defaults are 2.x's. The sections, in 2.x's order: Presets, then Design and Booklet ("Make one up") or
Photo ("Convert a photo"), then Page text, Poster and Paper.
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QProgressBar,
                               QScrollArea, QTabBar, QVBoxLayout, QWidget)

from inkengine import book, cbn, photo
from inkengine.patterns import maze, name, words

from . import theme
from .state import BUILTIN_PRESETS
from .widgets import (Hint, OptionRow, Pager, Pair, Section, SubOptions, button, check, combo, label, line_edit,
                      slider_row)

GEN_OPTIONS = [("mandala", "Mandala (colouring page)"), ("maze", "Maze"), ("truchet", "Woven tiles"),
               ("contour", "Topographic contours"), ("flow", "Flow lines"), ("dots", "Dot-to-dot"), ("sudoku", "Sudoku"),
               ("name", "Name or word (bubble letters)"), ("words", "Word search"), ("nonogram", "Nonogram (picture logic)")]
GRID_OPTIONS = [("2x2", "2 × 2"), ("3x3", "3 × 3"), ("4x4", "4 × 4"), ("2x1", "2 across × 1"), ("3x2", "3 across × 2"),
                ("1x2", "1 across × 2"), ("2x3", "2 across × 3")]
CBN_PATTERN_NOTE = "Repeated spaces share a number, and spaces side by side get different colours."
MAX_PHOTOS = 60


class Sidebar(QFrame):
    changed = Signal(str)         # a setting changed (its name): draw again and remember
    reroll = Signal()             # New design
    page_step = Signal(int)       # the pager: -1 or +1
    swap_page = Signal(bool)      # New design for this page (True) / Back to original (False)
    open_images = Signal(bool)    # Open image… (False) / Add photos… (True)
    sample = Signal()
    preset_chosen = Signal(str, str)   # ("b" built-in or "s" saved, name)
    preset_save = Signal(str)
    preset_delete = Signal(str)
    photo_selected = Signal(int)
    photo_moved = Signal(int, int)
    photo_removed = Signal(int)
    crop = Signal(str)            # rotl | rotr | reset | zoom | pan
    print_ = Signal()
    save = Signal(str)            # png | pdf | svg
    mode_changed = Signal(str)
    synced = Signal()             # sync() ran: the window matches its menu actions to the footer buttons

    def __init__(self, state, version):
        super().__init__()
        self.state = state
        self.setObjectName("sidebar")
        self.setFixedWidth(theme.SIDEBAR_WIDTH)
        self._loading = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._brand(version))
        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        column = QWidget()
        column.setMinimumWidth(0)
        column.setObjectName("sidebarColumn")
        self.col = QVBoxLayout(column)
        self.col.setContentsMargins(theme.PAD_X, 14, theme.PAD_X, theme.PAD_X)
        self.col.setSpacing(theme.SECTION_GAP)
        scroll.setWidget(column)
        outer.addWidget(scroll, 1)
        self._build()
        self.col.addStretch(1)
        outer.addWidget(self._footer())
        self.load()

    # --- holders ------------------------------------------------------------------------------------
    def _brand(self, version):
        f = QFrame()
        f.setObjectName("brand")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(theme.PAD_X, 18, theme.PAD_X, 14)
        lay.setSpacing(10)
        n = QLabel("Inkline")
        n.setObjectName("brandName")
        t = QLabel("black & white for print")
        t.setObjectName("brandTag")
        v = QLabel("dev build" if version == "dev" else f"v{version}")
        v.setObjectName("brandVersion")
        v.setToolTip(f"Inkline {version}")
        lay.addWidget(n, 0, Qt.AlignmentFlag.AlignBaseline)
        lay.addWidget(t, 0, Qt.AlignmentFlag.AlignBaseline)
        lay.addStretch(1)
        lay.addWidget(v, 0, Qt.AlignmentFlag.AlignBaseline)
        return f

    def _footer(self):
        f = QFrame()
        f.setObjectName("footer")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(theme.PAD_X, 14, theme.PAD_X, 14)
        lay.setSpacing(theme.PAIR_GAP)
        self.print_btn = button("Print…", "primary", "Print (Ctrl+P)")
        self.print_btn.clicked.connect(self.print_)
        lay.addWidget(self.print_btn)
        trio = QHBoxLayout()
        trio.setSpacing(theme.PAIR_GAP)
        self.png_btn = button("PNG", tip="Save PNG (Ctrl+Shift+S)")
        self.pdf_btn = button("PDF", tip="Save PDF (Ctrl+S)")
        self.svg_btn = button("SVG", tip="Vector lines for Inkscape, Cricut, Silhouette or laser cutters")
        for b, kind in ((self.png_btn, "png"), (self.pdf_btn, "pdf"), (self.svg_btn, "svg")):
            b.clicked.connect(lambda _c=False, k=kind: self.save.emit(k))
            trio.addWidget(b)
        lay.addLayout(trio)
        self.status = label("", "status")
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(18)
        lay.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setAccessibleName("Saving progress")
        self.progress.hide()
        lay.addWidget(self.progress)
        keys = label("Ctrl+P print · Ctrl+S PDF · Ctrl+N new design · ← → pages", "keys")
        keys.setWordWrap(True)
        lay.addWidget(keys)
        return f

    # --- sections -----------------------------------------------------------------------------------
    def _build(self):
        s = self.state.settings
        self.tabs = QTabBar()
        self.tabs.setObjectName("modeTabs")
        self.tabs.addTab("Make one up")
        self.tabs.addTab("Convert a photo")
        self.tabs.setExpanding(True)
        self.tabs.setDrawBase(False)
        self.tabs.currentChanged.connect(lambda i: None if self._loading else self.mode_changed.emit("make" if i == 0 else "convert"))
        self.col.addWidget(self.tabs)

        # Presets
        sec = Section("Presets")
        self.preset = combo([("", "Choose a preset…")])
        self.preset.setAccessibleName("Apply a preset")
        self.preset_del = button("Delete")
        self.preset_del.setEnabled(False)
        sec.add(_row(self.preset, self.preset_del))
        self.preset_name = line_edit(placeholder="Name for current settings", max_length=40)
        self.preset_name.setAccessibleName("Preset name")
        save = button("Save")
        sec.add(_row(self.preset_name, save))
        self.preset.activated.connect(self._preset_picked)
        self.preset_del.clicked.connect(lambda: self.preset_delete.emit(self.preset.value()[2:]))
        save.clicked.connect(lambda: self.preset_save.emit(self.preset_name.text().strip()))
        self.preset_name.returnPressed.connect(save.click)
        self.col.addWidget(sec)

        # Make one up: Design
        self.make_panel = QWidget()
        mk = QVBoxLayout(self.make_panel)
        mk.setContentsMargins(0, 0, 0, 0)
        mk.setSpacing(theme.SECTION_GAP)
        sec = Section("Design")
        self.gen = self._combo("gen", GEN_OPTIONS)
        sec.add(OptionRow("Pattern", self.gen))
        self.words_opts = SubOptions()
        self.ws_theme = self._combo("ws_theme", list(words.THEME_NAMES.items()))
        self.words_opts.add(OptionRow("Words from", self.ws_theme))
        self.ws_words = self._text("ws_words", "e.g. mum, dad, grandma, pizza", 300)
        self.ws_words_row = self.words_opts.add(OptionRow("Your words", self.ws_words))
        self.ws_note = self.words_opts.add(Hint())
        self.maze_opts = SubOptions()
        self.maze_shape = self._combo("maze_shape", list(maze.SHAPE_NAMES.items()))
        self.maze_opts.add(OptionRow("Maze shape", self.maze_shape))
        self.maze_word = self._text("maze_word", "e.g. Maya", 12)
        self.maze_word_row = self.maze_opts.add(OptionRow("Word or name", self.maze_word))
        self.name_opts = SubOptions()
        self.name_text = self._text("name_text", "e.g. Maya, Happy Birthday", 40)
        self.name_opts.add(OptionRow("Name or word", self.name_text))
        self.name_bg = self._combo("name_bg", list(name.BACKGROUNDS.items()))
        self.name_opts.add(OptionRow("Around the letters", self.name_bg))
        sec.add(self.words_opts, self.maze_opts, self.name_opts)
        sec.add(self._slider("complexity", "Complexity", 1, 10, lambda v: f"{v} / 10"))
        sec.add(self._slider("weight", "Line weight", 1, 10, lambda v: f"{v / 150 * 25.4:.2f} mm"))
        sec.add(self._check("frame", "Draw a border around the design"))
        sec.add(self._check("cbn", "Colour by number (a number in each space, with a crayon key)"))
        self.cbn_opts = SubOptions()
        self.cbn_opts.add(self._slider("cbn_colours", "Colours", 3, 12))
        self.cbn_note = self.cbn_opts.add(Hint(CBN_PATTERN_NOTE))
        sec.add(self.cbn_opts)
        self.seed = label("", "seed")
        new = button("New design", "primary", "New design (Ctrl+N)")
        new.setObjectName("newDesign")
        new.clicked.connect(self.reroll)
        self.new_design = new
        sec.add(_row(self.seed, new, stretch_first=True))
        mk.addWidget(sec)

        # Make one up: Booklet
        sec = Section("Booklet")
        sec.add(self._check("booklet", "Make a multi-page booklet"))
        self.book_opts = SubOptions()
        self.book_opts.add(self._slider("pages", "Design pages", 2, 40))
        self.book_opts.add(self._check("ramp", "Get harder page by page"))
        self.book_opts.add(self._check("mix", "Mix every pattern (except name pages)"))
        self.book_opts.add(self._check("cover", "Cover page"))
        self.book_opts.add(self._check("page_nums", "Page numbers"))
        self.book_opts.add(self._check("key", "Answer pages for puzzles (mazes, dot-to-dots, sudoku, word search, nonograms) "
                                              "and colour-by-number pages"))
        self.pager = Pager()
        self.pager.prev.connect(lambda: self.page_step.emit(-1))
        self.pager.next.connect(lambda: self.page_step.emit(1))
        self.book_opts.add(self.pager)
        self.page_new = button("New design for this page", "mini")
        self.page_orig = button("Back to original", "mini")
        self.page_new.clicked.connect(lambda: self.swap_page.emit(True))
        self.page_orig.clicked.connect(lambda: self.swap_page.emit(False))
        self.page_orig.hide()   # shown once the page shown has been swapped
        tools = QWidget()
        tl = QHBoxLayout(tools)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(theme.PAIR_GAP)
        tl.addWidget(self.page_new)
        tl.addWidget(self.page_orig)
        tl.addStretch(1)
        self.book_opts.add(tools)
        self.book_opts.add(Hint("PDF and Print use every page. PNG and SVG save the page shown."))
        sec.add(self.book_opts)
        mk.addWidget(sec)
        self.col.addWidget(self.make_panel)

        # Convert a photo
        self.photo_panel = Section("Photo")
        drop = QFrame()
        drop.setObjectName("drop")
        dl = QVBoxLayout(drop)
        dl.setContentsMargins(14, 14, 14, 14)
        dl.setSpacing(theme.PAIR_GAP)
        self.src = QLabel("Drop an image anywhere, paste one, or")
        self.src.setObjectName("dropText")
        self.src.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.src.setWordWrap(True)
        dl.addWidget(self.src)
        op = button("Open image…")
        op.clicked.connect(lambda: self.open_images.emit(self.state.settings.photobook))   # adds to a photo book, as 2.x
        smp = button("Use sample")
        smp.clicked.connect(self.sample)
        dl.addWidget(Pair(op, smp))
        self.photo_panel.add(drop)
        self.photo_panel.add(self._check("photobook", "Make a photo book from several photos"))
        self.pbook_opts = SubOptions()
        self.photo_count = label("")
        add = button("Add photos…", "mini")
        add.clicked.connect(lambda: self.open_images.emit(True))
        self.pbook_opts.add(_row(self.photo_count, add, stretch_first=True))
        self.photo_list = QListWidget()
        self.photo_list.setObjectName("photoList")
        self.photo_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.photo_list.currentRowChanged.connect(lambda i: None if self._loading or i < 0 else self.photo_selected.emit(i))
        self.pbook_opts.add(self.photo_list)
        self.pbook_opts.add(self._check("pcover", "Cover page"))
        self.pbook_opts.add(self._check("ppage_nums", "Page numbers"))
        self.ppager = Pager()
        self.ppager.prev.connect(lambda: self.page_step.emit(-1))
        self.ppager.next.connect(lambda: self.page_step.emit(1))
        self.pbook_opts.add(self.ppager)
        self.pbook_opts.add(Hint("Click a photo to crop it; each photo keeps its own crop. PDF and Print use every page."))
        self.photo_panel.add(self.pbook_opts)
        rotl, rotr, reset = button("↺", tip="Rotate left 90°"), button("↻", tip="Rotate right 90°"), button("Reset")
        rotl.setAccessibleName("Rotate left")
        rotr.setAccessibleName("Rotate right")
        for b, kind in ((rotl, "rotl"), (rotr, "rotr"), (reset, "reset")):
            b.clicked.connect(lambda _c=False, k=kind: self.crop.emit(k))
        crop = QWidget()
        cl = QHBoxLayout(crop)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(theme.PAIR_GAP)
        cl.addWidget(rotl, 1)
        cl.addWidget(rotr, 1)
        cl.addWidget(reset, 2)
        self.photo_panel.add(OptionRow("Crop", crop))
        self.zoom_row, self.zoom = slider_row("Zoom", 100, 400, 100, lambda v: f"{v}%")
        self.panx_row, self.panx = slider_row("Move ↔", -100, 100, 0)
        self.pany_row, self.pany = slider_row("Move ↕", -100, 100, 0)
        self.panx_row.value.hide()
        self.pany_row.value.hide()
        for sl in (self.zoom, self.panx, self.pany):
            sl.valueChanged.connect(lambda _v: None if self._loading else self.crop.emit("sliders"))
        self.photo_panel.add(self.zoom_row, Pair(self.panx_row, self.pany_row))
        self.photo_panel.add(Hint("Drag the preview to move the photo; scroll over it to zoom."))
        self.style = self._combo("style", [(k, photo.STYLE_NAMES[k]) for k in photo.STYLES])
        self.photo_panel.add(OptionRow("Style", self.style))
        self.pcbn_opts = SubOptions()
        self.pcbn_opts.add(self._slider("pcbn_colours", "Colours", 4, 16))
        self.pcbn_opts.add(Hint("Threshold / detail sets how small the regions get. The key names the crayon for each number."))
        self.pnono_opts = SubOptions()
        self.pnono_opts.add(self._slider("pnono_size", "Squares across", 10, 30))
        self.pnono_opts.add(self._check("pnono_answer", "Show the answer"))
        self.pnono_opts.add(Hint("Threshold sets which squares are shaded. Where logic alone can't finish the picture, "
                                 "a few squares are changed, or shaded to start you off."))
        self.photo_panel.add(self.pcbn_opts, self.pnono_opts)
        self.photo_panel.add(self._slider("brightness", "Brightness", -100, 100, lambda v: f"+{v}" if v > 0 else str(v)))
        self.photo_panel.add(self._slider("contrast", "Contrast", 20, 300, lambda v: f"{v}%"))
        self.photo_panel.add(self._slider("threshold", "Threshold / detail", 1, 254))
        self.photo_panel.add(self._slider("dot", "Dot size", 1, 8, lambda v: f"{v} px"))
        fit = self._combo("fit", [("contain", "Fit inside"), ("cover", "Fill page")])
        inv = self._check("invert", "Invert")
        inv_row = OptionRow(" ", inv)
        self.photo_panel.add(Pair(OptionRow("Placement", fit), inv_row))
        self.col.addWidget(self.photo_panel)

        # Page text
        sec = Section("Page text")
        sec.add(OptionRow("Title", self._text("title", "e.g. Rainy Day Mazes", 60)))
        sec.add(self._check("name_line", 'Add a "Name ______" line'))
        self.col.addWidget(sec)

        # Poster
        sec = Section("Poster")
        sec.add(self._check("poster", "Print it big, across several sheets"))
        self.poster_opts = SubOptions()
        self.poster_opts.add(Pair(OptionRow("Sheets", self._combo("grid", GRID_OPTIONS)),
                                  OptionRow("Overlap", self._combo("overlap", [(0.25, "¼ in"), (0.5, "½ in"), (0.0, "None")]))))
        self.poster_size = self.poster_opts.add(Hint())
        self.poster_opts.add(Hint("Each sheet is labelled (A1, A2…) with trim marks. Cut along the marks, then line up "
                                  "neighbouring sheets using the shared overlap strip."))
        sec.add(self.poster_opts)
        self.col.addWidget(sec)

        # Paper
        sec = Section("Paper")
        sec.add(self._check("testpage", "Show the printer test page"))
        self.fold_check = self._check("fold", "Fold-and-staple book (2 pages per sheet)")
        self.fold_hint = Hint()
        sec.add(self.fold_check, self.fold_hint)
        self.testpage_hint = sec.add(Hint("Print it at 100% (“Actual size”), then check the squares with a ruler. Always portrait."))
        sec.add(Pair(OptionRow("Size", self._combo("paper", [("letter", "Letter"), ("a4", "A4")])),
                     OptionRow("Orientation", self._combo("orient", [("portrait", "Portrait"), ("landscape", "Landscape")]))))
        sec.add(Pair(OptionRow("Margin", self._combo("margin", [(0.25, "¼ in"), (0.5, "½ in"), (0.75, "¾ in"), (1.0, "1 in")])),
                     OptionRow("Resolution", self._combo("dpi", [(150, "150 dpi (draft)"), (300, "300 dpi")]))))
        self.col.addWidget(sec)

    # --- controls bound to a setting ----------------------------------------------------------------
    def _bind(self, key, control, read, write, signal):
        self._binds = getattr(self, "_binds", {})
        self._binds[key] = (control, write)

        def on_change(*_a):
            if self._loading:
                return
            self.state.update(**{key: read()})
            self.changed.emit(key)
        signal.connect(on_change)

    def _combo(self, key, options):
        c = combo(options)
        self._bind(key, c, c.value, c.set_value, c.currentIndexChanged)
        return c

    def _text(self, key, placeholder, max_length):
        e = line_edit(placeholder=placeholder, max_length=max_length)
        self._bind(key, e, e.text, e.setText, e.textChanged)
        return e

    def _check(self, key, text):
        c = check(text)
        self._bind(key, c, c.isChecked, c.setChecked, c.toggled)
        return c

    def _slider(self, key, text, lo, hi, fmt=str):
        row, s = slider_row(text, lo, hi, lo, fmt)
        self._bind(key, s, s.value, lambda v, s=s, row=row: (s.setValue(int(v)), row.update_value()), s.valueChanged)
        return row

    # --- from the state ------------------------------------------------------------------------------
    def load(self):
        """Put every control to the state's settings (start, presets, remembered settings)."""
        self._loading = True
        try:
            s = self.state.settings.to_dict()
            for key, (_control, write) in self._binds.items():
                write(s[key])
            self.tabs.setCurrentIndex(0 if self.state.settings.mode == "make" else 1)
            self.load_crop()
        finally:
            self._loading = False
        self.sync()

    def load_crop(self):
        ph = self.state.photo
        was, self._loading = self._loading, True
        self.zoom.setValue(int(ph.zoom) if ph else 100)
        self.panx.setValue(int(ph.panx) if ph else 0)
        self.pany.setValue(int(ph.pany) if ph else 0)
        self._loading = was

    def fill_presets(self, saved, selected=""):
        self._loading = True
        c = self.preset
        c.clear()
        c.addItem("Choose a preset…", "")
        c.addItem("— Built-in —", None)
        c.model().item(c.count() - 1).setEnabled(False)
        for n in BUILTIN_PRESETS:
            c.addItem(n, f"b:{n}")
        if saved:
            c.addItem("— Saved —", None)
            c.model().item(c.count() - 1).setEnabled(False)
            for n in sorted(saved, key=str.lower):
                c.addItem(n, f"s:{n}")
        c.setCurrentIndex(max(0, c.findData(selected)))
        self.preset_del.setEnabled(selected.startswith("s:"))
        self._loading = False

    def _preset_picked(self, _i):
        v = self.preset.value() or ""
        self.preset_del.setEnabled(v.startswith("s:"))
        if v:
            self.preset_chosen.emit(v[0], v[2:])

    def fill_photos(self):
        self._loading = True
        lst, st = self.photo_list, self.state
        lst.clear()
        row_h = 46
        for i, ph in enumerate(st.photos):
            item = QListWidgetItem()
            item.setToolTip(ph.name)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, f"Photo {i + 1}: {ph.name}")
            item.setSizeHint(QSize(0, row_h))
            lst.addItem(item)
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(4, 4, 4, 4)
            rl.setSpacing(6)
            thumb = QLabel()
            thumb.setPixmap(QPixmap.fromImage(ph.image.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                              Qt.TransformationMode.SmoothTransformation).copy(0, 0, 36, 36)))
            thumb.setFixedSize(36, 36)
            rl.addWidget(thumb)
            nm = _Elided(f"{i + 1}. {ph.name}")
            nm.setObjectName("photoName")
            rl.addWidget(nm, 1)
            for txt, tip, fn, off in (("↑", "Move up", lambda _c=False, i=i: self.photo_moved.emit(i, -1), i == 0),
                                      ("↓", "Move down", lambda _c=False, i=i: self.photo_moved.emit(i, 1), i == len(st.photos) - 1),
                                      ("✕", "Remove", lambda _c=False, i=i: self.photo_removed.emit(i), len(st.photos) < 2)):
                b = button(txt, "mini", tip)
                b.setAccessibleName(tip)
                b.setEnabled(not off)
                b.clicked.connect(fn)
                rl.addWidget(b)
            lst.setItemWidget(item, row)
        # as tall as its photos, up to 260 px (2.x's list), then it scrolls
        lst.setFixedHeight(min(260, max(1, len(st.photos)) * (row_h + 4) + 4))
        lst.setCurrentRow(st.sel)
        n = len(st.photos)
        self.photo_count.setText(f"{n} photo{'' if n == 1 else 's'}")
        if n:
            nm = st.photo.name if st.photo else ""
            self.src.setText(f"{n} photos · editing {nm}" if n > 1 else nm)
        else:
            self.src.setText("Drop images anywhere, paste one, or")
        self.src.setProperty("named", "true" if n else "false")   # the name in bold ink, as 2.x's <strong>
        self.src.style().unpolish(self.src)
        self.src.style().polish(self.src)
        self._loading = False

    def sync(self, view=None):
        """Show what applies and fill in the live values (2.x's syncOutputs)."""
        s = self.state.settings
        make = s.mode == "make"
        self.make_panel.setVisible(make)
        self.photo_panel.setVisible(not make)
        mix_book = s.booklet and s.mix
        self.words_opts.setVisible(s.gen == "words")
        self.ws_words_row.setVisible(s.ws_theme == "custom")
        self.maze_opts.setVisible(s.gen == "maze" or mix_book)
        self.maze_word_row.setVisible(s.maze_shape == "word")
        self.name_opts.setVisible(s.gen == "name")
        self.cbn_opts.setVisible(s.cbn)
        if s.gen == "name" and s.name_bg in ("none", "flow"):
            note = "Flow lines and plain pages enclose few spaces: choose Woven tiles or Contours around the letters for more to colour."
        elif s.gen in cbn.CBN_GENS or mix_book:
            note = CBN_PATTERN_NOTE
        else:
            note = "Works on mandalas, woven tiles, contours and name pages; choose one of those to see it."
        self.cbn_note.setText(note)
        self.seed.setText(f"seed {s.seed}")
        self.book_opts.setVisible(s.booklet)
        self.pbook_opts.setVisible(s.photobook)
        self.pcbn_opts.setVisible(s.style == "cbn")
        self.pnono_opts.setVisible(s.style == "nono")
        self.poster_opts.setVisible(s.poster)
        if s.poster:
            from inkengine.poster import size_note
            self.poster_size.setText(size_note(s))
        is_book = make and s.booklet and not s.poster
        is_pbook = not make and s.photobook and bool(self.state.photos) and not s.poster
        self.fold_check.setVisible(is_book or is_pbook)
        fold = s.fold and (is_book or is_pbook)
        self.fold_hint.setVisible(fold)
        if fold:
            pages = book.photo_book_pages(s, self.state.photos) if is_pbook else book.book_pages(s)
            n = len(pages)
            padded = -(-n // 4) * 4
            half = book.half_geometry(s)
            extra = f" ({padded - n} blank page{'s' if padded - n > 1 else ''} added at the end)" if padded > n else ""
            self.fold_hint.setText(f"{n} pages of {half.w:g} × {half.h:g} in → {padded // 4} sheet{'s' if padded > 4 else ''}{extra}. "
                                   "Print double-sided, flipping on the short edge. Stack the sheets in order, fold in half, "
                                   "staple along the fold.")
        self.testpage_hint.setVisible(s.testpage)
        if view is not None:
            self.pager.set_text(view.label)
            self.ppager.set_text(view.label)
            p = view.pages[view.index] if view.pages and view.kind == "booklet" else None
            key = p.idx if p is not None and p.kind == "design" else "cover" if p is not None and p.kind == "cover" else None
            self.page_new.setEnabled(key is not None and not s.fold)
            self.page_new.setToolTip("Turn off fold-and-staple to pick a single page" if s.fold else
                                     "Answer pages follow their puzzles" if key is None else "")
            self.page_new.setText("New cover art" if p is not None and p.kind == "cover" else "New design for this page")
            seeds = s.page_seeds or {}
            self.page_orig.setVisible(key is not None and (key in seeds or str(key) in seeds) and not s.fold)
            self.current_key = key
        # the footer's buttons: PNG isn't for posters; SVG suits designs and the vector photo styles
        poster = s.poster and not s.testpage
        self.png_btn.setEnabled(not poster)
        self.png_btn.setToolTip("Posters save as PDF (one page per sheet) or print directly" if poster else "Save PNG (Ctrl+Shift+S)")
        vector = not make and s.style in photo.VECTOR_STYLES
        self.svg_btn.setEnabled((make or vector) and not s.testpage and not fold)
        tips = {"engrave": "Engraving lines save as vector paths, for laser engravers and plotters",
                "stipple": "Stippling dots save as vector circles, for laser engravers and plotters",
                "nono": "Photo nonograms save as vector lines and text, for editing in Inkscape",
                "cbn": "Colour-by-number outlines save as vector lines, for editing in Inkscape"}
        self.svg_btn.setToolTip(tips[s.style] if vector else "Vector lines for Inkscape, Cricut, Silhouette or laser cutters"
                                if make else "Photos are made of pixels; choose Engraving, Stippling, Colour by number or Nonogram for SVG")
        self.ws_note.setVisible(bool(self.ws_note.text()) and s.gen == "words")
        self.synced.emit()

    def set_status(self, text):
        self.status.setText(text)


class _Elided(QLabel):
    """A one-line label that ends in … when it doesn't fit (2.x's text-overflow: ellipsis)."""

    def __init__(self, text):
        super().__init__()
        self.full = text
        self.setMinimumWidth(0)
        self.setToolTip(text)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.setText(self.fontMetrics().elidedText(self.full, Qt.TextElideMode.ElideRight, self.width()))

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())


def _row(first, second, stretch_first=False):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.PAIR_GAP)
    lay.addWidget(first, 1)
    lay.addWidget(second, 0)
    return w
