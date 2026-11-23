"""Worksheet packs: a week of classroom worksheets on one theme, for one age, as a booklet built page by page.

A pack is five pages, one for each school day: a maths drill, a handwriting sheet, a crossword, a word search
and a maze, each set for the age as Age sets it (the sums, what's traced, how hard the puzzles are). The
crossword and word search share the theme, and an older child's handwriting sheet traces the theme's words.
It's an ordinary booklet afterwards: a cover with a name line, page numbers and answer pages at the end, and
any page can be changed, swapped or removed in the page list. With Paper → Copies and Names it makes a pack
for every child, and the answers can go in one teacher's book.
"""

from . import ages, i18n
from .patterns import crossword

DAYS = ("maths", "trace", "crossword", "words", "maze")
THEMES = tuple(crossword.THEMES)   # the themes both the crossword and the word search have: animals, food, space
DEFAULT_AGE = "7-9"                # "Any age" makes the middle one


def theme_words(theme, n=6):
    """The first few words of a theme's crossword, in the current language, to trace."""
    themes = crossword.THEMES_BY_LANGUAGE.get(i18n.LANG, crossword.THEMES)
    text = themes.get(theme, themes["animals"])
    return [e.partition(":")[0].strip() for e in text.split(";") if e.strip()][:n]


def week(s, seeds, theme=None, age=None):
    """The settings for a pack: {setting: value}, with page_list holding the five pages. s: the settings now
    (whose page options the pages start from); seeds: five seeds, one per page."""
    age = age or (s.age if s.age in ages.EXTRAS else DEFAULT_AGE)
    if theme is None:   # the theme of the crossword or word search being looked at, else the word search's
        mine = s.cross_theme if s.gen == "crossword" else s.ws_theme
        theme = next((t for t in (mine, s.ws_theme, s.cross_theme) if t in THEMES), "animals")
    extras = ages.EXTRAS[age]
    base = {k: getattr(s, k) for k in ("cbn", "cbn_colours", "cbn_maths", "maze_shape", "maze_word", "ws_words",
                                       "name_text", "name_bg", "spot_base", "trace_text", "cross_words")}
    base.update(cbn=False, maze_shape="rect", maths_kind=extras["maths_kind"], trace_source=extras["trace_source"],
                ws_theme=theme, cross_theme=theme)
    if extras["trace_source"] == "words":
        base["trace_text"] = ", ".join(theme_words(theme))
    pages = [{**base, "gen": gen, "seed": seed, "complexity": ages.COMPLEXITY[gen][age]}
             for gen, seed in zip(DAYS, seeds)]
    return {"mode": "make", "age": age, "weight": extras["weight"], "booklet": True, "poster": False,
            "testpage": False, "fold": False, "cover": True, "name_line": True, "page_nums": True, "key": True,
            "ramp": False, "mix": False, "sheet": "one", "pages": len(pages), "page_list": pages,
            **{k: v for k, v in pages[0].items() if k != "seed"}}
