"""The left rail (2.x's aside): brand row, a scrolling column of sections, and the footer.

Every control writes straight into the window's State and says so through changed(); sync() shows
and hides the sub-options and fills in the live values, as 2.x's syncOutputs did. Labels, ranges and
defaults are 2.x's. The sections, in 2.x's order: Presets, then Design and Booklet ("Make one up") or
Photo ("Convert a photo"), then Page text, Poster and Paper.
"""

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIntValidator, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QProgressBar, QScrollArea, QTabBar, QVBoxLayout, QWidget)

from inkengine import ages, book, cbn, pack, photo
from inkengine.i18n import tr
from inkengine.page import PAGE_KEYS, PANELS, SHEETS, has_answer, sheet_gens
from inkengine.patterns import NAMES, bingo, clock, crossword, fractions, reward, ruled, maths, maze, money, name, spot, trace, words

from . import jobs, theme, thumbs
from .jobs import MAX_COPIES
from .state import BUILTIN_PRESETS
from .widgets import (Hint, OptionRow, Pager, Pair, Section, SubOptions, button, check, combo, label, line_edit,
                      slider_row)

GEN_OPTIONS = [("mandala", "Mandala (colouring page)"), ("maze", "Maze"), ("truchet", "Woven tiles"),
               ("contour", "Topographic contours"), ("flow", "Flow lines"), ("dots", "Dot-to-dot"), ("sudoku", "Sudoku"),
               ("name", "Name or word (bubble letters)"), ("words", "Word search"), ("nonogram", "Nonogram (picture logic)"),
               ("spot", "Spot the difference"), ("kakuro", "Kakuro (cross sums)"), ("maths", "Maths drill"),
               ("trace", "Handwriting (letters and words to trace)"), ("crossword", "Crossword"),
               ("clock", "Telling the time (clock faces)"),
               ("scramble", "Unscramble (mixed-up words)"),
               ("spelltest", "Spelling test (lines to write words read aloud)"),
               ("fractions", "Fractions, number lines and times grids"),
               ("symmetry", "Symmetry (shade the mirror half)"),
               ("ruled", "Graph and lined paper"), ("reward", "Reward charts and certificates"),
               ("reading", "Reading comprehension (a passage and questions)"),
               ("bingo", "Bingo cards (a different card for each child)")]
GRID_OPTIONS = [("2x2", "2 × 2"), ("3x3", "3 × 3"), ("4x4", "4 × 4"), ("2x1", "2 across × 1"), ("3x2", "3 across × 2"),
                ("1x2", "1 across × 2"), ("2x3", "2 across × 3")]
CBN_PATTERN_NOTE = "Repeated spaces share a number, and spaces side by side get different colours."
MAX_PHOTOS = 60
THUMB_MARGIN = 3      # page pictures drawn beyond the rows that can be seen, so a short scroll finds them ready
MAX_BOOK_PAGES = 40   # design pages in a booklet built page by page, as the quick booklet's slider
MARGINS = [(0.25, "¼ in"), (0.5, "½ in"), (0.75, "¾ in"), (1.0, "1 in")]   # Paper → Margin


class Sidebar(QFrame):
    changed = Signal(str)         # a setting changed (its name): draw again and remember
    reroll = Signal()             # New design
    more_designs = Signal()       # More designs…: several to choose from
    page_step = Signal(int)       # the pager: -1 or +1
    swap_page = Signal(bool)      # New design for this page (True) / Back to original (False)
    open_images = Signal(bool)    # Open image… (False) / Add photos… (True)
    sample = Signal()
    preset_chosen = Signal(str, str)   # ("b" built-in or "s" saved, name)
    preset_save = Signal(str)
    preset_delete = Signal(str)
    class_list_save = Signal(str)     # Paper → Names: save the names as a list (the one chosen, to update it)
    class_list_delete = Signal(str)
    class_set_changed = Signal()      # Copies, Names or their switches changed (a project keeps them)
    copy_step = Signal(int)           # the class set's copy pager: -1 / +1
    photo_selected = Signal(int)
    photo_moved = Signal(int, int)
    photo_removed = Signal(int)
    pack_make = Signal()          # Booklet → Make a week of worksheets
    pages_edit = Signal(bool)     # Edit pages one by one (True) / Back to quick booklet (False)
    book_page_selected = Signal(int)
    book_page_added = Signal()
    book_page_moved = Signal(int, int)
    book_page_copied = Signal(int)
    book_page_removed = Signal(int)
    page_answer = Signal(bool)    # the page being edited: its answer on the answer pages, or not
    pages_copy = Signal()         # Ctrl+C in the page list: the selected page onto the clipboard
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
        self.thumbs = thumbs.Thumbnails()   # the booklet page list's pictures
        self.thumbs.ready.connect(self._thumb_ready)
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
        self._scroll, self._column = scroll, column
        self._build()
        self.col.addStretch(1)
        self._foot = self._footer()
        outer.addWidget(self._foot)
        # the desktop's style (Breeze...) can make the controls wider than Inkline's own: the sidebar widens to fit
        # them rather than cut them off on the right (fit_width)
        self._fit_pending = False
        column.installEventFilter(self)
        self.load()
        self._fit_later()   # once shown: the widgets' sizes are only right after the stylesheet has polished them

    def fit_width(self):
        """As wide as Inkline's sidebar, or wider when the controls shown need more (up to MAX_SIDEBAR_WIDTH)."""
        self._fit_pending = False
        sc = self._scroll
        bar = sc.verticalScrollBar().sizeHint().width()
        need = max(self._column.minimumSizeHint().width() + bar + 2 * sc.frameWidth(),
                   self._foot.minimumSizeHint().width())
        w = max(theme.SIDEBAR_WIDTH, min(theme.MAX_SIDEBAR_WIDTH, need))
        if w != self.width() or self.minimumWidth() != w:
            self.setFixedWidth(w)

    def _fit_later(self):
        if not self._fit_pending:
            self._fit_pending = True
            QTimer.singleShot(0, self.fit_width)

    def eventFilter(self, obj, ev):
        if obj is self._column and ev.type() == QEvent.Type.LayoutRequest:   # a part shown or hidden, a restyle
            self._fit_later()
        return super().eventFilter(obj, ev)

    def changeEvent(self, ev):
        if ev.type() in (QEvent.Type.StyleChange, QEvent.Type.FontChange):
            self._fit_later()
        super().changeEvent(ev)

    # --- holders ------------------------------------------------------------------------------------
    def _brand(self, version):
        f = QFrame()
        f.setObjectName("brand")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(theme.PAD_X, 18, theme.PAD_X, 14)
        lay.setSpacing(10)
        n = QLabel("Inkline")
        n.setObjectName("brandName")
        t = QLabel(tr("black & white for print"))
        t.setObjectName("brandTag")
        v = QLabel(tr("dev build") if version == "dev" else f"v{version}")
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
        self.png_btn = button("PNG", tip="Save PNG (Ctrl+Shift+E)")
        self.pdf_btn = button("PDF", tip="Save PDF (Ctrl+E)")
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
        self.progress.setAccessibleName(tr("Saving progress"))
        # stops a long print or save after the page being drawn (the window wires it up: cancel_job)
        self.cancel_btn = button("Cancel", "mini", "Stop printing or saving (Esc)")
        self.progress_row = QWidget()
        prow = QHBoxLayout(self.progress_row)
        prow.setContentsMargins(0, 0, 0, 0)
        prow.setSpacing(theme.PAIR_GAP)
        prow.addWidget(self.progress, 1)
        prow.addWidget(self.cancel_btn)
        self.progress_row.hide()
        lay.addWidget(self.progress_row)
        keys = label("Ctrl+P print · Ctrl+E PDF · Ctrl+S save project · Ctrl+N new design · ← → pages", "keys")
        keys.setWordWrap(True)
        lay.addWidget(keys)
        return f

    # --- sections -----------------------------------------------------------------------------------
    def _build(self):
        s = self.state.settings
        self.tabs = QTabBar()
        self.tabs.setObjectName("modeTabs")
        self.tabs.addTab(tr("Make one up"))
        self.tabs.addTab(tr("Convert a photo"))
        self.tabs.setExpanding(True)
        self.tabs.setDrawBase(False)
        self.tabs.currentChanged.connect(lambda i: None if self._loading else self.mode_changed.emit("make" if i == 0 else "convert"))
        self.col.addWidget(self.tabs)

        # Presets
        sec = Section("Presets")
        self.preset = combo([("", "Choose a preset…")])
        self.preset.setAccessibleName(tr("Apply a preset"))
        self.preset_del = button("Delete")
        self.preset_del.setEnabled(False)
        sec.add(_row(self.preset, self.preset_del))
        self.preset_name = line_edit(placeholder="Name for current settings", max_length=40)
        self.preset_name.setAccessibleName(tr("Preset name"))
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
        self.design_note = sec.add(Hint())   # which booklet page the section edits, when it's built page by page
        self.gen = self._combo("gen", GEN_OPTIONS)
        sec.add(OptionRow("Pattern", self.gen))
        # several designs on one sheet (single pages): the layout, then the patterns after this one
        self.sheet = self._combo("sheet", list(SHEETS.items()))
        self.sheet_row = sec.add(OptionRow("On the sheet", self.sheet))
        self.sheet_opts = SubOptions()
        self.panel_combos = []
        for which in ("2nd design", "3rd design", "4th design"):
            c = combo(list(GEN_OPTIONS))
            c.setAccessibleName(tr("{which} on the sheet").format(which=tr(which)))
            c.currentIndexChanged.connect(self._panels_picked)
            self.panel_combos.append((self.sheet_opts.add(OptionRow(which, c)), c))
        self.sheet_hint = self.sheet_opts.add(Hint("They share Complexity and the options above. Answer pages "
                                                   "(with copies) show each puzzle's answer."))
        sec.add(self.sheet_opts)
        self.age = self._combo("age", list(ages.AGES.items()))
        sec.add(OptionRow("Age", self.age))
        self.age_hint = sec.add(Hint("Sets complexity, line weight and options to suit. Change any of them after."))
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
        self.spot_opts = SubOptions()
        self.spot_base = self._combo("spot_base", list(spot.BASES.items()))
        self.spot_opts.add(OptionRow("Picture", self.spot_base))
        self.maths_opts = SubOptions()
        self.maths_kind = self._combo("maths_kind", list(maths.KINDS.items()))
        self.maths_opts.add(OptionRow("Sums", self.maths_kind))
        self.money = self._combo("money", list(money.CURRENCIES.items()))
        self.money_row = self.maths_opts.add(OptionRow("Money", self.money))
        self.maths_opts.add(Hint("Complexity sets how big the numbers get and how many sums there are."))
        self.frac_opts = SubOptions()
        self.frac_kind = self._combo("frac_kind", list(fractions.KINDS.items()))
        self.frac_opts.add(OptionRow("Worksheet", self.frac_kind))
        self.ruled_opts = SubOptions()
        self.ruled_kind = self._combo("ruled_kind", list(ruled.KINDS.items()))
        self.ruled_opts.add(OptionRow("Paper", self.ruled_kind))
        self.ruled_opts.add(Hint("Complexity sets the spacing: an inch apart at 1, down to 5 mm at 10."))
        self.reward_opts = SubOptions()
        self.reward_kind = self._combo("reward_kind", list(reward.KINDS.items()))
        self.reward_opts.add(OptionRow("Make", self.reward_kind))
        self.reward_text = self._text("reward_text", "e.g. reading every day", 60)
        self.reward_opts.add(OptionRow("For", self.reward_text))
        self.reward_opts.add(Hint("With Paper → Names, each child gets one with their name on it."))
        self.bingo_opts = SubOptions()
        self.bingo_kind = self._combo("bingo_kind", list(bingo.KINDS.items()))
        self.bingo_opts.add(OptionRow("Call out", self.bingo_kind))
        self.bingo_theme = self._combo("bingo_theme", list(words.THEME_NAMES.items()))
        self.bingo_theme_row = self.bingo_opts.add(OptionRow("Words from", self.bingo_theme))
        self.bingo_words = self._text("bingo_words", "e.g. cat, dog, sun, hat, pen", 600)
        self.bingo_words_row = self.bingo_opts.add(OptionRow("Your words", self.bingo_words))
        self.bingo_note = self.bingo_opts.add(Hint())
        self.bingo_opts.add(Hint("Complexity sets the card: 3 × 3, 4 × 4 or 5 × 5. With Paper → Copies or Names, every "
                                 "card is different; Answer pages adds the caller's sheet."))
        self.clock_opts = SubOptions()
        self.clock_task = self._combo("clock_task", list(clock.TASKS.items()))
        self.clock_opts.add(OptionRow("Clocks", self.clock_task))
        self.clock_opts.add(Hint("Complexity goes from o'clock and half past to quarters, five minutes and any minute."))
        self.trace_opts = SubOptions()
        self.trace_source = self._combo("trace_source", list(trace.SOURCES.items()))
        self.trace_opts.add(OptionRow("Trace", self.trace_source))
        self.trace_style = self._combo("trace_style", list(trace.LETTERS.items()))
        self.trace_opts.add(OptionRow("Letters", self.trace_style))
        self.trace_hand = self._combo("trace_hand", list(trace.HANDS.items()))
        self.trace_hand_row = self.trace_opts.add(OptionRow("Style", self.trace_hand))
        self.trace_text = self._text("trace_text", "e.g. cat, dog, sun, my name", 300)
        self.trace_text_row = self.trace_opts.add(OptionRow("Your words", self.trace_text))
        self.trace_hint = self.trace_opts.add(Hint())
        self.cross_opts = SubOptions()
        self.cross_theme = self._combo("cross_theme", list(crossword.THEME_NAMES.items()))
        self.cross_opts.add(OptionRow("Words from", self.cross_theme))
        self.cross_words = self._text("cross_words", "e.g. cat: Says miaow; sun: Our nearest star", 2000)
        self.cross_words_row = self.cross_opts.add(OptionRow("Your words and clues", self.cross_words))
        self.cross_words_hint = self.cross_opts.add(Hint("Each as word: clue, separated by ; (a word without a clue gets ?)."))
        self.cross_note = self.cross_opts.add(Hint())
        sec.add(self.words_opts, self.maze_opts, self.name_opts, self.spot_opts, self.maths_opts, self.frac_opts, self.ruled_opts,
                self.reward_opts, self.bingo_opts, self.clock_opts,
                self.trace_opts, self.cross_opts)
        sec.add(self._slider("complexity", "Complexity", 1, 10, lambda v: f"{v} / 10"))
        sec.add(self._slider("weight", "Line weight", 1, 10, lambda v: f"{v / 150 * 25.4:.2f} mm"))
        sec.add(self._check("frame", "Draw a border around the design"))
        sec.add(self._check("cbn", "Colour by number (a number in each space, with a crayon key)"))
        self.cbn_opts = SubOptions()
        self.cbn_opts.add(self._slider("cbn_colours", "Colours", 3, 12))
        self.cbn_opts.add(self._check("cbn_maths", "Colour by maths (a sum in each space: its answer is the colour)"))
        self.cbn_note = self.cbn_opts.add(Hint(CBN_PATTERN_NOTE))
        sec.add(self.cbn_opts)
        # a booklet built page by page: this page's solution on the answer pages (shown for puzzles and colour by number)
        self.page_answer_check = check("Include its answer in the answer pages")
        self.page_answer_check.toggled.connect(lambda on: None if self._loading else self.page_answer.emit(on))
        sec.add(self.page_answer_check)
        self.seed = label("", "seed")
        new = button("New design", "primary", "New design (Ctrl+N)")
        new.setObjectName("newDesign")
        new.clicked.connect(self.reroll)
        self.new_design = new
        sec.add(_row(self.seed, new, stretch_first=True))
        more = button("More designs…", "mini", "Choose from six designs (Ctrl+Shift+N)")
        more.clicked.connect(self.more_designs)
        self.more_btn = more
        sec.add(_tools(more))
        mk.addWidget(sec)

        # Make one up: Booklet
        sec = Section("Booklet")
        # a week of worksheets in one go: the theme (or this week's spelling words), then Make
        self.pack_theme = self._combo("pack_theme", list(pack.THEME_NAMES.items()))
        sec.add(OptionRow("Worksheet pack", self.pack_theme))
        self.pack_words = self._text("pack_words", "e.g. because, friend, said, which", 600)
        self.pack_words_row = sec.add(OptionRow("Spelling words", self.pack_words))
        self.pack_btn = button("Make a week of worksheets", "mini",
                               "Five worksheets with answers, set for the age under Age (Undo brings back what you had)")
        self.pack_btn.clicked.connect(self.pack_make)
        sec.add(_tools(self.pack_btn))
        self.pack_hint = sec.add(Hint())
        sec.add(self._check("booklet", "Make a multi-page booklet"))
        self.book_opts = SubOptions()
        self.pages_row = self.book_opts.add(self._slider("pages", "Design pages", 2, 40))
        self.ramp_check = self.book_opts.add(self._check("ramp", "Get harder page by page"))
        self.mix_check = self.book_opts.add(self._check("mix", "Mix every pattern (except name pages)"))
        self.pages_edit_btn = button("Edit pages one by one", "mini",
                                     "Choose each page's pattern and complexity, and reorder, copy or remove pages")
        self.pages_edit_btn.clicked.connect(lambda: self.pages_edit.emit(True))
        self.pages_quick_btn = button("Back to quick booklet", "mini", "Make the pages from Design pages, "
                                      "Get harder and Mix again (Undo brings your pages back)")
        self.pages_quick_btn.clicked.connect(lambda: self.pages_edit.emit(False))
        self.book_opts.add(_tools(self.pages_edit_btn, self.pages_quick_btn))
        self.page_count = label("")
        self.page_add = button("Add page", "mini", "Add a page like the last one, with a new design")
        self.page_add.clicked.connect(self.book_page_added)
        self.page_count_row = self.book_opts.add(_row(self.page_count, self.page_add, stretch_first=True))
        self.page_list = _PageList()
        self.page_list.moved.connect(lambda i, j: self.book_page_moved.emit(i, j - i))
        self.page_list.verticalScrollBar().valueChanged.connect(self._request_visible_thumbs)
        # with the page list focused, the selected page: copy, remove, duplicate, move (as its row's buttons do)
        keys = ((QKeySequence.StandardKey.Copy, self.pages_copy),
                (QKeySequence(Qt.Key.Key_Delete), lambda: self._page_key("remove")),
                (QKeySequence("Ctrl+D"), lambda: self._page_key("copy")),
                (QKeySequence("Alt+Up"), lambda: self._page_key("up")),
                (QKeySequence("Alt+Down"), lambda: self._page_key("down")))
        for key, fn in keys:
            QShortcut(key, self.page_list, context=Qt.ShortcutContext.WidgetShortcut).activated.connect(fn)
        self.page_list.setObjectName("pageList")
        self.page_list.setAccessibleName(tr("Booklet pages"))
        self.page_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.page_list.currentRowChanged.connect(lambda i: None if self._loading or i < 0 else self.book_page_selected.emit(i))
        self.book_opts.add(self.page_list)
        self.page_list_hint = self.book_opts.add(Hint("Click a page to change it in Design above, or drag it to move it. "
                                                      "Line weight, border, title and paper apply to every page."))
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
        self.book_opts.add(_tools(self.page_new, self.page_orig))
        self.book_opts.add(Hint("PDF and Print use every page, or only those chosen under Paper. PNG and SVG save the page shown."))
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
        self.src = QLabel(tr("Drop an image anywhere, paste one, or"))
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
        self.pbook_opts.add(Hint("Click a photo to crop it; each photo keeps its own crop. PDF and Print use every page, or only those chosen under Paper."))
        self.photo_panel.add(self.pbook_opts)
        rotl, rotr, reset = button("↺", tip="Rotate left 90°"), button("↻", tip="Rotate right 90°"), button("Reset")
        rotl.setAccessibleName(tr("Rotate left"))
        rotr.setAccessibleName(tr("Rotate right"))
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
        # Print and Save PDF of a booklet or photo book: every page, or only some (not a setting: never remembered,
        # so a range typed for one reprint can't shorten a later print unnoticed)
        self.only_pages = line_edit(placeholder="All pages, or e.g. 3-5, 8, cover", max_length=80)
        self.only_pages.setAccessibleName(tr("Print or save only these pages"))
        self.only_pages.textChanged.connect(lambda _t: self.sync())
        self.only_row = sec.add(OptionRow("Print or save only", self.only_pages))
        self.only_hint = sec.add(Hint())
        # Print and Save PDF of a single page: how many (a class set), each with a new design or alike; not a
        # setting either, so it's never remembered
        self.copies = line_edit(placeholder="1", max_length=3)
        self.copies.setValidator(_CopiesValidator(self.copies))
        self.copies.setAccessibleName(tr("Copies to print or save"))
        self.copies.textChanged.connect(lambda _t: (self.sync(), self.class_set_changed.emit()))
        self.copies_row = sec.add(OptionRow("Copies", self.copies))
        # a class set: one copy per name, each name written on its copy's "Name" line (never remembered either)
        self.copies_names = line_edit(placeholder="Optional: Ana, Ben, Cara…", max_length=4000)
        self.copies_names.setAccessibleName(tr("Names: one copy for each, written on its Name line"))
        self.copies_names.textChanged.connect(lambda _t: (self.sync(), self.class_set_changed.emit()))
        self.copies_names_row = sec.add(OptionRow("Names", self.copies_names))
        # class lists kept in the settings folder (class-lists.json), to use again
        self.class_lists = {}
        self.class_list = combo([("", "Saved lists…")])
        self.class_list.setAccessibleName(tr("Use a saved class list"))
        self.class_list.activated.connect(self._class_list_picked)
        self.class_list_del = button("Delete", tip="Delete the chosen list")
        self.class_list_del.setEnabled(False)
        self.class_list_del.clicked.connect(lambda: self.class_list_delete.emit(self.class_list.value() or ""))
        # as Presets pairs its drop-down with Delete; Save… on its own line, so no row is wider than Presets'
        self.class_list_row = sec.add(_row(self.class_list, self.class_list_del))
        self.class_list_save_btn = button("Save names as a list…", tip="Save these names as a list, to use again")
        self.class_list_save_btn.clicked.connect(lambda: self.class_list_save.emit(self.class_list.value() or ""))
        self.class_list_save_row = QWidget()
        srow = QHBoxLayout(self.class_list_save_row)
        srow.setContentsMargins(0, 0, 0, 0)
        srow.addStretch(1)
        srow.addWidget(self.class_list_save_btn)
        sec.add(self.class_list_save_row)
        self.copies_vary = check("A new design on each copy")
        self.copies_vary.setChecked(True)
        self.copies_vary.toggled.connect(lambda _on: (self.sync(), self.class_set_changed.emit()))
        sec.add(self.copies_vary)
        self.copies_answers = check("Answer pages at the end")
        self.copies_answers.setChecked(True)
        self.copies_answers.toggled.connect(lambda _on: (self.sync(), self.class_set_changed.emit()))
        sec.add(self.copies_answers)
        # a class set of booklets: their answers in one book for the teacher, not in each child's booklet
        self.copies_answer_book = check("Answers in a separate teacher's book")
        self.copies_answer_book.toggled.connect(lambda _on: (self.sync(), self.class_set_changed.emit()))
        sec.add(self.copies_answer_book)
        self.copies_hint = sec.add(Hint())
        # look through the class set's copies in the preview: each one's designs, and its name
        self.copy_pager = Pager()
        self.copy_pager.back.setAccessibleName(tr("Previous copy"))
        self.copy_pager.forward.setAccessibleName(tr("Next copy"))
        self.copy_pager.back.setToolTip(tr("Previous copy"))
        self.copy_pager.forward.setToolTip(tr("Next copy"))
        self.copy_pager.prev.connect(lambda: self.copy_step.emit(-1))
        self.copy_pager.next.connect(lambda: self.copy_step.emit(1))
        sec.add(self.copy_pager)
        self.testpage_hint = sec.add(Hint("Print it at 100% (“Actual size”), then check the squares with a ruler. Always portrait."))
        sec.add(Pair(OptionRow("Size", self._combo("paper", [("letter", "Letter"), ("a4", "A4")])),
                     OptionRow("Orientation", self._combo("orient", [("portrait", "Portrait"), ("landscape", "Landscape")]))))
        sec.add(Pair(OptionRow("Margin", self._combo("margin", MARGINS)),
                     OptionRow("Resolution", self._combo("dpi", [(150, "150 dpi (draft)"), (300, "300 dpi")]))))
        self.margin_hint = sec.add(Hint())   # the printer can't reach that far in: set_margin_warning()
        self.margin_hint.setVisible(False)
        self.col.addWidget(sec)

    def copies_typed(self):
        """The number in the Copies field, or None when it's empty."""
        try:
            return int(self.copies.text())
        except ValueError:
            return None

    def fill_class_lists(self, lists, selected=""):
        """The saved class lists in the drop-down, by name; selected: the one to show chosen."""
        self.class_lists = dict(lists)
        c = self.class_list
        c.blockSignals(True)
        c.clear()
        c.addItem(tr("Saved lists…") if lists else tr("No saved lists yet"), "")
        for n in sorted(lists, key=str.lower):
            c.addItem(n, n)
        c.setCurrentIndex(max(0, c.findData(selected)))
        c.setEnabled(bool(lists))
        c.blockSignals(False)
        self.class_list_del.setEnabled(bool(selected) and selected in lists)

    def _class_list_picked(self, _i):
        name = self.class_list.value() or ""
        self.class_list_del.setEnabled(bool(name))
        if name in self.class_lists:
            self.copies_names.setText(self.class_lists[name])

    def class_set(self):
        """Copies, Names and their switches, as a project keeps them."""
        text = self.copies_names.text().strip()   # spaces round the names, or only separators, don't count
        return {"copies": self.copies_count(), "names": text if jobs.parse_names(text, None) else "",
                "vary": self.copies_vary.isChecked(), "answers": self.copies_answers.isChecked(),
                "answer_book": self.copies_answer_book.isChecked()}

    def set_class_set(self, cs=None):
        """Put Copies, Names and their switches back (None: as on a fresh start)."""
        cs = cs or {}
        n = cs.get("copies", 1)
        self.copies.setText(str(n) if n > 1 else "")
        self.copies_names.setText(cs.get("names", ""))
        self.copies_vary.setChecked(cs.get("vary", True))
        self.copies_answers.setChecked(cs.get("answers", True))
        self.copies_answer_book.setChecked(cs.get("answer_book", False))
        self.class_list.setCurrentIndex(0)
        self.class_list_del.setEnabled(False)
        self.sync()

    def class_set_view(self):
        """The class set Print and Save PDF would make (for the preview's copy pager), or None without one."""
        from .classset import ClassSet
        if not self.copies_row.isVisibleTo(self):
            return None
        names = self.copies_names_list()
        cs = ClassSet(count=len(names) if names else self.copies_count(), vary=self.copies_vary.isChecked(),
                      answers=self.copies_answers.isChecked(), names=names,
                      answer_book=self.copies_answer_book.isChecked())
        return cs if cs.active else None   # one name is a class set too: it goes on the page

    def copies_names_list(self):
        """The names typed for a class set: they replace Copies, but only with the Name line on."""
        return jobs.parse_names(self.copies_names.text()) if self.state.settings.name_line else []

    def copies_count(self):
        """The copies asked for: 1 when the field is empty or not a number, at most MAX_COPIES."""
        try:
            return max(1, min(MAX_COPIES, int(self.copies.text())))
        except ValueError:
            return 1

    def _only_note(self, s, photo_book):
        """What Print and Save PDF will do with the pages typed, or what's wrong with them."""
        from . import jobs
        pages = book.photo_book_pages(s, self.state.photos) if photo_book else book.book_pages(s)
        try:
            picked = jobs.parse_pages(self.only_pages.text(), pages)
        except ValueError as why:
            return str(why)
        what = jobs.describe_pages(picked, len(pages))
        if s.fold:
            sheets = jobs.fold_sheets(picked, len(book.fold_pages(pages)))
            names = jobs.describe_pages(sheets, 0, sheets=True)
            return (tr("Prints {sheets}, both sides: they hold {what}.") if len(sheets) > 1 else
                    tr("Prints {sheets}, both sides: it holds {what}.")).format(sheets=names, what=what)
        return tr("Prints and saves {what} of {n}.").format(what=what, n=len(pages))

    def set_margin_warning(self, text):
        self.margin_hint.setText(text)
        self.margin_hint.setVisible(bool(text))

    # --- controls bound to a setting ----------------------------------------------------------------
    def _panels_picked(self, _i=None):
        if self._loading:
            return
        self.state.update(panel_gens=",".join(c.value() for _row, c in self.panel_combos))
        self.changed.emit("panel_gens")

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
        c.addItem(tr("Choose a preset…"), "")
        c.addItem(tr("— Built-in —"), None)
        c.model().item(c.count() - 1).setEnabled(False)
        for n in BUILTIN_PRESETS:
            c.addItem(tr(n), f"b:{n}")
        if saved:
            c.addItem(tr("— Saved —"), None)
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
            item.setData(Qt.ItemDataRole.AccessibleTextRole, tr("Photo {n}: {name}").format(n=i + 1, name=ph.name))
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
                b.setAccessibleName(tr(tip))
                b.setEnabled(not off)
                b.clicked.connect(fn)
                rl.addWidget(b)
            lst.setItemWidget(item, row)
        # as tall as its photos, up to 260 px (2.x's list), then it scrolls
        lst.setFixedHeight(min(260, max(1, len(st.photos)) * (row_h + 4) + 4))
        lst.setCurrentRow(st.sel)
        n = len(st.photos)
        self.photo_count.setText(tr("1 photo") if n == 1 else tr("{n} photos").format(n=n))
        if n:
            nm = st.photo.name if st.photo else ""
            self.src.setText(tr("{n} photos · editing {name}").format(n=n, name=nm) if n > 1 else nm)
        else:
            self.src.setText(tr("Drop images anywhere, paste one, or"))
        self.src.setProperty("named", "true" if n else "false")   # the name in bold ink, as 2.x's <strong>
        self.src.style().unpolish(self.src)
        self.src.style().polish(self.src)
        self._loading = False

    def fill_pages(self):
        """The booklet's pages, when it's built page by page: a row each, as the photo book's photo list."""
        self._loading = True
        lst, st = self.page_list, self.state
        pl = st.settings.page_list or []
        cx = st.settings.complexity
        lst.clear()
        self._thumb_rows = []
        row_h = 60   # two lines: the name doesn't fit beside four buttons in the sidebar's width
        for i, p in enumerate(pl):
            gen = p.get("gen") if p.get("gen") in NAMES else st.settings.gen
            detail = _page_detail(gen, p)
            text = f"{i + 1}. {tr(NAMES[gen])}{f' · {detail}' if detail else ''} · {p.get('complexity', cx)}/10"
            if p.get("answer", True) is False and st.settings.key and has_answer(gen, _own_settings(st.settings, p)):
                text += " · " + tr("no answer")
            item = QListWidgetItem()
            item.setToolTip(text + ("\n" + tr("Words: {words}").format(words=p["ws_words"])
                                    if gen in ("words", "scramble", "spelltest") and p.get("ws_theme") == "custom" and p.get("ws_words") else ""))
            item.setData(Qt.ItemDataRole.AccessibleTextRole, tr("Page {text}").format(text=text))
            item.setSizeHint(QSize(0, row_h))
            lst.addItem(item)
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(4, 4, 4, 4)
            rl.setSpacing(6)
            slot = QWidget()   # a 36 px slot, as the photo list's, with the page centred in it
            slot.setFixedSize(36, 36)
            sl = QHBoxLayout(slot)
            sl.setContentsMargins(0, 0, 0, 0)
            thumb = QLabel()
            thumb.setObjectName("pageThumb")
            sl.addWidget(thumb, 0, Qt.AlignmentFlag.AlignCenter)
            self._thumb_rows.append(thumb)
            rl.addWidget(slot)
            right = QVBoxLayout()
            right.setContentsMargins(0, 0, 0, 0)
            right.setSpacing(theme.LABEL_GAP)
            nm = _Elided(text)
            nm.setObjectName("pageName")
            right.addWidget(nm)
            btns = QHBoxLayout()
            btns.setContentsMargins(0, 0, 0, 0)
            btns.setSpacing(6)
            right.addLayout(btns)
            rl.addLayout(right, 1)
            full = len(pl) >= MAX_BOOK_PAGES
            for txt, tip, key, fn, off in (
                    ("↑", "Move up", "Alt+↑", lambda _c=False, i=i: self.book_page_moved.emit(i, -1), i == 0),
                    ("↓", "Move down", "Alt+↓", lambda _c=False, i=i: self.book_page_moved.emit(i, 1), i == len(pl) - 1),
                    ("⧉", "Duplicate with a new design", "Ctrl+D", lambda _c=False, i=i: self.book_page_copied.emit(i), full),
                    ("✕", "Remove", "Delete", lambda _c=False, i=i: self.book_page_removed.emit(i), len(pl) < 2)):
                b = button(txt, "mini")
                b.setToolTip(f"{tr(tip)} ({key})")
                b.setAccessibleName(tr(tip))
                b.setEnabled(not off)
                b.clicked.connect(fn)
                # the list is filled again (this button goes): the focus goes back to the list, so the keys named
                # in the tooltip work straight after a click
                b.clicked.connect(lambda _c=False: self.page_list.setFocus())
                btns.addWidget(b)
            btns.addStretch(1)
            lst.setItemWidget(item, row)
        lst.setFixedHeight(min(260, max(1, len(pl)) * (row_h + 4) + 4))
        lst.setCurrentRow(st.book_sel if pl else -1)
        self.refresh_thumbs()
        n = len(pl)
        self.page_count.setText(tr("1 design page") if n == 1 else tr("{n} design pages").format(n=n))
        self.page_add.setEnabled(0 < n < MAX_BOOK_PAGES)
        self.page_add.setToolTip(tr("A booklet has at most {n} design pages").format(n=MAX_BOOK_PAGES) if n >= MAX_BOOK_PAGES
                                 else tr("Add a page like the last one, with a new design"))
        self._loading = False

    def _page_key(self, what):
        """A page-list shortcut on the selected page: whatever its row's button would do (and nothing where that
        button is off: the first page can't move up, the last page can't be removed)."""
        pl, i = self.state.settings.page_list or [], self.page_list.currentRow()
        if not self.state.listing or not 0 <= i < len(pl):
            return
        if what == "up" and i > 0:
            self.book_page_moved.emit(i, -1)
        elif what == "down" and i < len(pl) - 1:
            self.book_page_moved.emit(i, 1)
        elif what == "copy" and len(pl) < MAX_BOOK_PAGES:
            self.book_page_copied.emit(i)
        elif what == "remove" and len(pl) > 1:
            self.book_page_removed.emit(i)
        self.page_list.setFocus()   # the list is filled again: keep the keys working on the page that moved

    def show_selected_page(self):
        """Highlight the page being edited, without filling the list again (a drag may be starting on it)."""
        if self.page_list.currentRow() != self.state.book_sel:
            was, self._loading = self._loading, True
            self.page_list.setCurrentRow(self.state.book_sel)
            self._loading = was

    def refresh_thumbs(self):
        """Each row's picture of its page: from the cache, or a blank page until it's drawn in the background."""
        st = self.state
        rows = getattr(self, "_thumb_rows", [])
        self._thumb_keys = {}
        if not st.listing or not rows:
            return
        s = st.settings
        designs = [p for p in book.book_pages(s) if p.kind == "design"]
        w, h = thumbs.thumb_size(s)
        for i, (label, spec) in enumerate(zip(rows, designs)):
            k = thumbs.key(s, spec)
            self._thumb_keys.setdefault(k, []).append(i)
            label.setFixedSize(w + 2, h + 2)   # the page and its 1 px edge: at most the 36 px slot
            img = self.thumbs.get(k)
            label.setPixmap(QPixmap.fromImage(img) if img is not None else QPixmap())
        self._designs = designs[:len(rows)]
        self._request_visible_thumbs()

    def _request_visible_thumbs(self, *_args):
        """Draw the pictures of the rows that can be seen (and a few either side), nearest the selected page first:
        a long booklet doesn't draw forty pictures at once when it opens; scrolling draws the rest."""
        designs = getattr(self, "_designs", [])
        if not designs or not self.state.listing:
            return
        lst, n = self.page_list, len(designs)
        top = lst.indexAt(QPoint(4, 2)).row()
        bottom = lst.indexAt(QPoint(4, lst.viewport().height() - 2)).row()
        sel = max(0, min(n - 1, self.state.book_sel))
        if top < 0:   # not laid out yet: around the selected page
            top, bottom = sel - 3, sel + 3
        elif bottom < 0:
            bottom = n - 1
        lo, hi = max(0, top - THUMB_MARGIN), min(n - 1, bottom + THUMB_MARGIN)
        order = sorted(range(lo, hi + 1), key=lambda i: (not top <= i <= bottom, abs(i - sel)))
        self.thumbs.request(self.state.settings, [designs[i] for i in order])

    def _thumb_ready(self, k):
        rows = getattr(self, "_thumb_rows", [])
        img = self.thumbs.get(k)
        for i in getattr(self, "_thumb_keys", {}).get(k, []):
            if img is not None and i < len(rows):
                rows[i].setPixmap(QPixmap.fromImage(img))

    def sync(self, view=None):
        """Show what applies and fill in the live values (2.x's syncOutputs)."""
        s = self.state.settings
        make = s.mode == "make"
        self.make_panel.setVisible(make)
        self.photo_panel.setVisible(not make)
        listing = s.booklet and bool(s.page_list)   # built page by page: Design edits the selected page
        mix_book = s.booklet and s.mix and not listing
        self.words_opts.setVisible(s.gen in ("words", "scramble", "spelltest"))   # unscramble takes its words from the same place
        self.age_hint.setVisible(s.age != "any")
        sheet_ok = make and not s.booklet and not s.poster and not s.testpage   # single designs only
        self.sheet_row.setVisible(sheet_ok)
        n_panels = PANELS.get(s.sheet, 1) if sheet_ok else 1
        self.sheet_opts.setVisible(n_panels > 1)
        gens = sheet_gens(s) + ["words", "maze", "dots"]
        was, self._loading = self._loading, True
        for k, (row, c) in enumerate(self.panel_combos):
            row.setVisible(k + 1 < n_panels)
            c.set_value(gens[k + 1])
        self._loading = was
        self.maths_opts.setVisible(s.gen == "maths")
        self.clock_opts.setVisible(s.gen == "clock")
        self.frac_opts.setVisible(s.gen == "fractions")
        self.ruled_opts.setVisible(s.gen == "ruled")
        self.reward_opts.setVisible(s.gen == "reward")
        self.bingo_opts.setVisible(s.gen == "bingo")
        self.bingo_theme_row.setVisible(s.bingo_kind == "words")
        self.bingo_words_row.setVisible(s.bingo_kind == "words" and s.bingo_theme == "custom")
        self.bingo_note.setText(bingo.note(s))
        self.bingo_note.setVisible(bool(self.bingo_note.text()))
        self.money_row.setVisible(s.maths_kind == "money")
        self.pack_words_row.setVisible(s.pack_theme == "spelling")
        spelling = s.pack_theme == "spelling"
        what = (tr("Handwriting, a crossword, a word search and an unscramble sheet of your words, then a spelling test, for {age}.")
                if spelling else
                tr("Twelve of these sight words traced, in a crossword, a word search and an unscramble sheet, then a "
                   "spelling test, for {age}.") if s.pack_theme in pack.SIGHT else
                tr("Maths, handwriting, a crossword, a word search and a maze, for {age}."))
        ready = not spelling or bool(pack.spelling_list(s.pack_words))
        self.pack_hint.setText(what.format(age=tr(ages.AGES[s.age if s.age in ages.EXTRAS else pack.DEFAULT_AGE]).lower())
                               if ready else tr("Type this week's spelling words to make the pack."))
        self.pack_btn.setEnabled(ready)
        self.cross_opts.setVisible(s.gen == "crossword")
        self.cross_words_row.setVisible(s.cross_theme == "custom")
        self.cross_words_hint.setVisible(s.cross_theme == "custom")
        self.trace_opts.setVisible(s.gen == "trace")
        self.trace_text_row.setVisible(s.trace_source == "words")
        self.trace_hand_row.setVisible(s.trace_style == "joined")
        self.trace_hint.setVisible(s.trace_source == "name")
        self.trace_hint.setText(tr("Traces each child's name from Paper → Names, or else the name page's text.")
                                if s.trace_source == "name" else "")
        self.ws_words_row.setVisible(s.ws_theme == "custom")
        self.maze_opts.setVisible(s.gen == "maze" or mix_book)
        self.maze_word_row.setVisible(s.maze_shape == "word")
        self.name_opts.setVisible(s.gen == "name")
        self.spot_opts.setVisible(s.gen == "spot")
        self.cbn_opts.setVisible(s.cbn)
        if s.gen == "name" and s.name_bg in ("none", "flow"):
            note = "Flow lines and plain pages enclose few spaces: choose Woven tiles or Contours around the letters for more to colour."
        elif s.gen in cbn.CBN_GENS or mix_book:
            note = CBN_PATTERN_NOTE
        else:
            note = "Works on mandalas, woven tiles, contours and name pages; choose one of those to see it."
        self.cbn_note.setText(tr(note))
        page = self.state.book_page if listing else None
        self.seed.setText(tr("seed {n}").format(n=page.get('seed', s.seed) if page else s.seed))
        self.design_note.setVisible(page is not None)
        answers = page is not None and s.key and has_answer(s.gen, s)
        self.page_answer_check.setVisible(answers)
        if answers:
            was, self._loading = self._loading, True
            self.page_answer_check.setChecked(page.get("answer", True) is not False)
            self._loading = was
        if page is not None:
            self.design_note.setText(tr("Editing page {i} of {n} of the booklet. Line weight and border apply to every "
                                        "page.").format(i=self.state.book_sel + 1, n=len(s.page_list)))
        self.book_opts.setVisible(s.booklet)
        for w in (self.pages_row, self.ramp_check, self.mix_check, self.pages_edit_btn):
            w.setVisible(not listing)
        for w in (self.pages_quick_btn, self.page_count_row, self.page_list, self.page_list_hint):
            w.setVisible(listing)
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
            blanks = padded - n
            extra = (" " + (tr("({n} blank pages added at the end)") if blanks > 1 else
                            tr("(1 blank page added at the end)")).format(n=blanks)) if blanks else ""
            sheets = (tr("{n} sheets") if padded > 4 else tr("1 sheet")).format(n=padded // 4)
            self.fold_hint.setText(tr("{n} pages of {w} × {h} in → {sheets}").format(n=n, w=f"{half.w:g}", h=f"{half.h:g}",
                                                                                   sheets=sheets) + extra + ". " +
                                   tr("Print double-sided, flipping on the short edge. Stack the sheets in order, fold "
                                      "in half, staple along the fold."))
        self.testpage_hint.setVisible(s.testpage)
        multi = (is_book or is_pbook) and not s.testpage
        single = not multi and not s.poster and not s.testpage and (make or bool(self.state.photos))
        books = is_book and not s.testpage   # a class set of booklets: each child their own
        shown = single or books
        names = self.copies_names_list() if shown else []
        typed_names = jobs.parse_names(self.copies_names.text()) if shown else []
        n = len(names) if names else self.copies_count() if shown else 1
        for row in (self.copies_row, self.copies_names_row, self.class_list_row, self.class_list_save_row):
            row.setVisible(shown)
        self.copies.setEnabled(not names)   # the names say how many
        # a booklet's pages each vary in their own way (and it has its own answer pages)
        can_vary, vary_note = (True, "") if books else jobs.copies_vary(s)
        typed = self.copies_typed()
        off = not names and typed is not None and typed != n   # 0 or over the most: say what will print instead
        unnamed = bool(typed_names) and not names   # names typed, but no Name line to write them on
        always = jobs.always_vary(s)   # bingo: alike cards would all win at once, so there's nothing to choose
        self.copies_vary.setVisible(shown and can_vary and n > 1 and not always)
        keyed = single and n > 1 and jobs.copies_have_answers(s)
        self.copies_answers.setVisible(keyed)
        book_keys = books and n > 1 and s.key
        self.copies_answer_book.setVisible(book_keys)
        self.copies_hint.setVisible(shown and (n > 1 or off or unnamed or bool(names)))
        if shown and (n > 1 or off or unnamed or names):
            vary = can_vary and (self.copies_vary.isChecked() or always)
            parts = [tr("Copies go from 1 to {top}.").format(top=MAX_COPIES)] if off else []
            if unnamed:
                parts.append(tr('To write the names on the booklets, turn on Page text → Add a "Name ______" line.')
                             if books else
                             tr('To write the names on the copies, turn on Page text → Add a "Name ______" line.'))
            # whole sentences, so each language can phrase them (and agree them with booklet or copy) its own way
            if names:
                many = len(jobs.parse_names(self.copies_names.text(), None)) > MAX_COPIES
                if n == 1:
                    sentence = tr("Print and Save PDF make 1 booklet, for the name.") if books else \
                        tr("Print and Save PDF make 1 copy, for the name.")
                elif books:
                    sentence = (tr("Print and Save PDF make {n} booklets, one for each name (the first {top}), each with "
                                   "its own designs (the first is the one shown).") if vary and many else
                                tr("Print and Save PDF make {n} booklets, one for each name, each with its own designs "
                                   "(the first is the one shown).") if vary else
                                tr("Print and Save PDF make {n} booklets, one for each name (the first {top}).") if many
                                else tr("Print and Save PDF make {n} booklets, one for each name."))
                else:
                    sentence = (tr("Print and Save PDF make {n} copies, one for each name (the first {top}), each with "
                                   "its own design (the first is the one shown).") if vary and many else
                                tr("Print and Save PDF make {n} copies, one for each name, each with its own design "
                                   "(the first is the one shown).") if vary else
                                tr("Print and Save PDF make {n} copies, one for each name (the first {top}).") if many
                                else tr("Print and Save PDF make {n} copies, one for each name."))
                parts.append(sentence.format(n=n, top=MAX_COPIES))
                if books:
                    parts.append(tr("Each name goes on its booklet's cover and Name lines, and heads its answers in "
                                    "the teacher's book.") if book_keys and self.copies_answer_book.isChecked() else
                                 tr("Each name goes on its booklet's cover, Name lines and answer pages."))
            elif n == 1:
                parts.append(tr("Print and Save PDF make 1 booklet.") if books else tr("Print and Save PDF make 1 copy."))
            elif books:
                parts.append((tr("Print and Save PDF make {n} booklets, each with its own designs (the first is the one "
                                 "shown).") if vary else tr("Print and Save PDF make {n} booklets, all alike.")).format(n=n))
            else:
                parts.append((tr("Print and Save PDF make {n} copies, each with its own design (the first is the one "
                                 "shown).") if vary else tr("Print and Save PDF make {n} copies, all alike.")).format(n=n))
            if vary_note and (vary or not can_vary):
                parts.append(tr(vary_note))
            if book_keys and self.copies_answer_book.isChecked() and not names:
                parts.append(tr("The answers follow them all, in a teacher's book: each booklet is numbered to match."))
            if keyed and self.copies_answers.isChecked():
                parts.append(tr("One answer page follows.") if not vary else
                             tr("Answer pages follow, each labelled with its copy's name.") if names else
                             tr("Answer pages follow, and each copy is numbered to match them."))
            text = " ".join(parts)
            self.copies_hint.setText(text)
        self.copy_pager.setVisible(shown and n > 1)
        self.only_row.setVisible(multi)
        self.only_hint.setVisible(multi and bool(self.only_pages.text().strip()))
        if multi and self.only_pages.text().strip():
            self.only_hint.setText(self._only_note(s, is_pbook))
        if view is not None:
            self.pager.set_text(view.label)
            self.ppager.set_text(view.label)
            self.copy_pager.set_text(view.copy_label)
            p = view.pages[view.index] if view.pages and view.kind == "booklet" else None
            key = p.idx if p is not None and p.kind == "design" else "cover" if p is not None and p.kind == "cover" else None
            self.page_new.setEnabled(key is not None and not s.fold)
            # built page by page, a page's New design is Design's own button; the cover keeps its New cover art
            self.page_new.setVisible(not listing or key == "cover")
            self.page_new.setToolTip(tr("Turn off fold-and-staple to pick a single page") if s.fold else
                                     tr("Answer pages follow their puzzles") if key is None else "")
            self.page_new.setText(tr("New cover art") if p is not None and p.kind == "cover" else tr("New design for this page"))
            seeds = s.page_seeds or {}
            self.page_orig.setVisible(key is not None and (key in seeds or str(key) in seeds) and not s.fold
                                      and (not listing or key == "cover"))
            self.current_key = key
        # the footer's buttons: PNG isn't for posters; SVG suits designs and the vector photo styles
        poster = s.poster and not s.testpage
        self.png_btn.setEnabled(not poster)
        vector = not make and s.style in photo.VECTOR_STYLES
        self.svg_btn.setEnabled((make or vector) and not s.testpage and not fold)
        self.save_tips(s)
        self.ws_note.setVisible(bool(self.ws_note.text()) and s.gen == "words")
        self.cross_note.setVisible(bool(self.cross_note.text()) and s.gen == "crossword")
        self.synced.emit()

    def save_tips(self, s):
        """The footer's save buttons' tooltips, with the shortcut each has (Ctrl+E saves Edit → Settings' format)."""
        fmt = getattr(self, "save_format", "pdf")
        make = s.mode == "make"
        self.pdf_btn.setToolTip(tr("Save PDF (Ctrl+E)") if fmt == "pdf" else
                                tr("Save PDF (Ctrl+Shift+E)") if fmt == "png" else tr("Save PDF"))
        self.png_btn.setToolTip(tr("Posters save as PDF (one page per sheet) or print directly")
                                if s.poster and not s.testpage else
                                tr("Save PNG (Ctrl+E)") if fmt == "png" else tr("Save PNG (Ctrl+Shift+E)"))
        vector = not make and s.style in photo.VECTOR_STYLES
        tips = {"engrave": tr("Engraving lines save as vector paths, for laser engravers and plotters"),
                "stipple": tr("Stippling dots save as vector circles, for laser engravers and plotters"),
                "nono": tr("Photo nonograms save as vector lines and text, for editing in Inkscape"),
                "cbn": tr("Colour-by-number outlines save as vector lines, for editing in Inkscape")}
        tip = tips[s.style] if vector else tr("Vector lines for Inkscape, Cricut, Silhouette or laser cutters"
                                              if make else "Photos are made of pixels; choose Engraving, Stippling, "
                                                           "Colour by number or Nonogram for SVG")
        self.svg_btn.setToolTip(tr("{tip} (Ctrl+E)").format(tip=tip) if fmt == "svg" and (make or vector) else tip)

    def set_status(self, text):
        self.status.setText(text)


class _CopiesValidator(QIntValidator):
    """1 to MAX_COPIES; leaving the field with 0 or more than the most puts in the nearest that prints."""

    def __init__(self, parent):
        super().__init__(1, MAX_COPIES, parent)

    def fixup(self, text):
        try:
            return str(max(1, min(MAX_COPIES, int(text))))
        except ValueError:
            return text


def _own_settings(s, p):
    """The settings a page of page_list is drawn with (its own on top of the booklet's)."""
    from dataclasses import replace
    return replace(s, **{k: p[k] for k in PAGE_KEYS if k in p})


def _page_detail(gen, p):
    """What tells a page apart from others of its pattern, for its row, in the person's language: a word search's
    theme, a word maze's word or a name page's name (those as typed, never translated)."""
    if gen in ("words", "scramble", "spelltest"):
        return tr("Your words") if p.get("ws_theme") == "custom" else tr(words.THEME_NAMES.get(p.get("ws_theme"), ""))
    if gen == "maze" and p.get("maze_shape") == "word":
        return p.get("maze_word", "").strip()
    if gen == "name":
        return p.get("name_text", "").strip()
    if gen == "maths":
        return tr(maths.KINDS.get(p.get("maths_kind", "add"), ""))
    if gen == "ruled":
        return tr(ruled.KINDS.get(p.get("ruled_kind", "squared"), ""))
    if gen == "reward":
        return tr(reward.KINDS.get(p.get("reward_kind", "chart"), ""))
    if gen == "bingo":
        kind = p.get("bingo_kind", "numbers")
        if kind == "words":
            return tr("Your words") if p.get("bingo_theme") == "custom" else tr(words.THEME_NAMES.get(p.get("bingo_theme"), ""))
        return tr(bingo.KINDS.get(kind, ""))
    if gen == "fractions":
        return tr(fractions.KINDS.get(p.get("frac_kind", "fractions"), ""))
    if gen == "clock":
        return tr(clock.TASKS.get(p.get("clock_task", "read"), ""))
    if gen == "trace":
        return tr(trace.SOURCES.get(p.get("trace_source", "upper"), ""))
    if gen == "crossword":
        return tr("Your words") if p.get("cross_theme") == "custom" else tr(crossword.THEME_NAMES.get(p.get("cross_theme"), ""))
    return ""


class _PageList(QListWidget):
    """The booklet's page list: drag a page to move it. The drop only says where it went (moved); the window
    makes the change, as an undo step, and the list is filled again from the settings."""

    moved = Signal(int, int)   # (from, to): the page's row before, and after

    def __init__(self):
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)

    def drop_row(self, y):
        """Where a page dropped at y (viewport pixels) lands, as a row in the list before the move."""
        idx = self.indexAt(QPoint(10, int(y)))
        if not idx.isValid():
            return self.count() if y > 0 else 0
        r = self.visualRect(idx)
        return idx.row() + (1 if y > r.center().y() else 0)

    def dropEvent(self, e):
        src, dst = self.currentRow(), self.drop_row(e.position().y())
        e.setDropAction(Qt.DropAction.IgnoreAction)   # the list isn't changed here: it's filled again
        e.accept()
        to = dst - 1 if dst > src else dst
        if src >= 0 and to != src:
            self.moved.emit(src, to)


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


def _tools(*buttons):
    """Mini buttons side by side, from the left."""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.PAIR_GAP)
    for b in buttons:
        lay.addWidget(b)
    lay.addStretch(1)
    return w


def _row(first, second, stretch_first=False):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(theme.PAIR_GAP)
    if isinstance(first, QLabel):   # a label beside a button wraps rather than widening the sidebar (a longer
        first.setWordWrap(True)     # language, or a desktop font wider than Inkline's)
    lay.addWidget(first, 1)
    lay.addWidget(second, 0)
    return w
