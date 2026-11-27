"""What's being made: the settings, the photos, which page is shown, and the built-in presets."""

import random
from dataclasses import dataclass, field, replace

from inkengine.page import PAGE_KEYS, Settings

# 2.x's built-in presets, in its order and words (its keys; Settings.from_dict reads them).
BUILTIN_PRESETS = {
    "Colouring page, bold lines": {"mode": "make", "gen": "mandala", "complexity": 5, "weight": 7, "frame": False, "cbn": False, "booklet": False, "poster": False},
    "Classroom maze worksheet": {"mode": "make", "gen": "maze", "mazeShape": "rect", "complexity": 4, "weight": 4, "title": "Maze time", "nameLine": True, "booklet": False, "poster": False},
    "Maze booklet with answers": {"mode": "make", "gen": "maze", "mazeShape": "rect", "booklet": True, "pages": 10, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False},
    "Name colouring page": {"mode": "make", "gen": "name", "nameBg": "flow", "complexity": 3, "weight": 5, "frame": False, "cbn": False, "booklet": False, "poster": False},
    "Word search booklet with answers": {"mode": "make", "gen": "words", "wsTheme": "animals", "booklet": True, "pages": 8, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False, "weight": 3},
    "Sudoku booklet with answers": {"mode": "make", "gen": "sudoku", "booklet": True, "pages": 10, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False},
    "Name maze": {"mode": "make", "gen": "maze", "mazeShape": "word", "mazeWord": "Maya", "complexity": 4, "weight": 4, "booklet": False, "poster": False},
    "Nonogram booklet with answers": {"mode": "make", "gen": "nonogram", "booklet": True, "pages": 8, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False},
    "Dot-to-dot booklet with answers": {"mode": "make", "gen": "dots", "booklet": True, "pages": 8, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False, "weight": 4},
    "Spot the difference booklet with answers": {"mode": "make", "gen": "spot", "spotBase": "mandala", "booklet": True, "pages": 8, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False},
    "Logic puzzle booklet with answers": {"mode": "make", "gen": "logic", "booklet": True, "pages": 8, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False},
    "Kakuro booklet with answers": {"mode": "make", "gen": "kakuro", "booklet": True, "pages": 8, "ramp": True, "mix": False, "cover": True, "pageNums": True, "key": True, "poster": False},
    # a week of worksheets for the age chosen (pack.week builds its pages when it's applied)
    "Worksheet pack: a week, with answers": {"pack": True},
    "Newspaper halftone photo": {"mode": "convert", "style": "halftone", "dot": 3, "contrast": 120, "brightness": 0, "invert": False},
    "Engraved photo": {"mode": "convert", "style": "engrave", "dot": 2, "contrast": 110, "brightness": 0, "invert": False},
    "Colour-by-number mandala": {"mode": "make", "gen": "mandala", "cbn": True, "cbnColours": 6, "complexity": 3, "weight": 5, "frame": False, "booklet": False, "poster": False},
    "Colour-by-number photo": {"mode": "convert", "style": "cbn", "pcbnColours": 8, "threshold": 128, "contrast": 110, "brightness": 0},
    "Calendar for next month": {"mode": "make", "gen": "calendar", "calKind": "month", "calMonth": 0, "calArt": "mandala", "complexity": 4, "weight": 4, "booklet": False, "poster": False, "sheet": "one"},
    "Photo dot-to-dot": {"mode": "convert", "style": "dots", "pdotsN": 60, "pdotsAnswer": False, "threshold": 128, "contrast": 110, "brightness": 0, "invert": False},
    "Photo nonogram": {"mode": "convert", "style": "nono", "pnonoSize": 15, "pnonoAnswer": False, "threshold": 128, "contrast": 110, "brightness": 0, "invert": False},
    "Stippled photo": {"mode": "convert", "style": "stipple", "dot": 2, "contrast": 110, "brightness": 0, "invert": False},
    "Photo colouring page": {"mode": "convert", "style": "line", "threshold": 128, "dot": 2, "invert": False},
    "Wall poster 3 × 3": {"poster": True, "booklet": False, "grid": "3x3", "overlap": "0.25"},
    "Start fresh (defaults)": {},   # every setting back to its default (filled in below)
}
FIRST_PATTERN = "mandala"   # 2.x opened on the first pattern in its list (the engine's own default is maze)

# Settings that belong to the photo being cropped or the page being viewed, not to a preset.
NOT_IN_PRESETS = {"seed", "page_seeds", "testpage"}
BUILTIN_PRESETS["Start fresh (defaults)"] = {k: v for k, v in Settings(gen=FIRST_PATTERN).to_dict().items()
                                            if k not in NOT_IN_PRESETS}


def new_seed():
    return random.randrange(10 ** 9)


@dataclass
class State:
    settings: Settings = field(default_factory=lambda: Settings(seed=new_seed(), gen=FIRST_PATTERN))
    photos: list = field(default_factory=list)   # photo.Photo, each with its own crop
    sel: int = 0                                  # the photo being cropped
    page: int = 0                                 # the booklet / photo book page (or folded side) shown
    book_sel: int = 0                             # the booklet page being edited, when it's built page by page
    copy: int = 0                                 # a class set: the copy the preview shows
    class_set: object = None                      # the Paper section's class set (classset.ClassSet), for the preview

    @property
    def photo(self):
        return self.photos[self.sel] if 0 <= self.sel < len(self.photos) else None

    def apply_preset(self, preset):
        """The settings with a preset's values on top (2.x's keys or 3.0's)."""
        merged = {**self.settings.to_dict(), **{k: v for k, v in Settings.from_dict(preset).to_dict().items()
                                                 if _named(preset, k)}}
        if not _named(preset, "page_list"):   # a preset starts a quick booklet: pages, ramp and mix apply again
            merged["page_list"] = []
        self.settings = Settings.from_dict(merged)
        self.page = 0
        self.book_sel = 0

    def preset_values(self):
        return {k: v for k, v in self.settings.to_dict().items() if k not in NOT_IN_PRESETS}

    def update(self, **changes):
        self.settings = replace(self.settings, **changes)

    # --- a booklet built page by page --------------------------------------------------------------------
    # The Design section edits the selected page: its settings are copied into the top-level ones (the
    # controls show those), and a change to one is written back into that page. The list itself is never
    # changed in place, so an undo step's settings keep the list as it was.
    @property
    def listing(self):
        """Whether the booklet built page by page is what's being made (it's kept, unused, while it isn't)."""
        s = self.settings
        return bool(s.page_list) and s.booklet and s.mode == "make" and not s.poster

    def mirror(self):
        """Show the selected page's settings in the top-level ones (its seed stays its own: the cover art uses
        the booklet's)."""
        pl = self.settings.page_list
        if not self.listing:
            return
        self.book_sel = max(0, min(self.book_sel, len(pl) - 1))
        p = pl[self.book_sel]
        self.update(**{k: p[k] for k in PAGE_KEYS if k in p and k != "seed"})

    def write_page(self, **changes):
        """Change the selected page (a new list with a new copy of that page)."""
        pl = list(self.settings.page_list)
        pl[self.book_sel] = {**pl[self.book_sel], **changes}
        self.update(page_list=pl)

    @property
    def book_page(self):
        pl = self.settings.page_list
        return pl[self.book_sel] if self.listing and 0 <= self.book_sel < len(pl) else None


def _named(preset, key):
    """Whether a preset (2.x's camelCase or 3.0's snake_case keys) sets this setting."""
    import re
    return any(re.sub(r"(?<!^)([A-Z])", r"_\1", k).lower() == key for k in preset)
