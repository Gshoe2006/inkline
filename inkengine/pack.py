"""Worksheet packs: a week of classroom worksheets on one theme, for one age, as a booklet built page by page.

A pack is five pages, one for each school day, each set for the age as Age sets it (the sums, what's traced,
how hard the puzzles are):

- on a theme (animals, food, space, ocean, weather, sports): a maths drill, a handwriting sheet, a crossword, a
  word search and a maze, the crossword and word search on the theme, and an older child's handwriting sheet
  tracing the theme's words;
- on this week's spelling words: the words four ways (traced, in a crossword whose clues are the words'
  letters mixed up, in a word search, and to unscramble), then Friday's spelling test.

It's an ordinary booklet afterwards: a cover with a name line, page numbers and answer pages at the end, and
any page can be changed, swapped or removed in the page list. With Paper → Copies and Names it makes a pack
for every child, and the answers can go in one teacher's book.
"""

import re

from . import ages, i18n
from .patterns import crossword, scramble, words
from .rng import mulberry32

DAYS = ("maths", "trace", "crossword", "words", "maze")
SPELLING_DAYS = ("trace", "crossword", "words", "scramble", "spelltest")
THEMES = tuple(t for t in crossword.THEME_NAMES if t != "custom")   # themes the crossword and word search share
THEME_NAMES = {**{t: crossword.THEME_NAMES[t] for t in THEMES}, "spelling": "Spelling words (your own list)"}
DEFAULT_AGE = "7-9"                # "Any age" makes the middle one
MAX_WORDS = 20


def theme_words(theme, n=6):
    """The first few words of a theme's crossword, in the current language, to trace."""
    themes = crossword.THEMES_BY_LANGUAGE.get(i18n.LANG, crossword.THEMES)
    text = themes.get(theme, themes["animals"])
    return [e.partition(":")[0].strip() for e in text.split(";") if e.strip()][:n]


def spelling_list(text):
    """The words of a spelling list, as typed (separated by commas, spaces or new lines), without repeats; words
    with no letters are left out."""
    out = []
    for w in re.split(r"[\s,;]+", text or ""):
        w = w.strip()
        if w and words.clean_word(w) and w.lower() not in (x.lower() for x in out):
            out.append(w)
    return out[:MAX_WORDS]


def week(s, seeds, theme=None, age=None, spelling=None):
    """The settings for a pack: {setting: value}, with page_list holding the five pages. s: the settings now
    (whose page options the pages start from); seeds: five seeds, one per page. The theme and spelling words
    are s.pack_theme and s.pack_words unless given; a spelling pack with no words is an animals pack."""
    age = age or (s.age if s.age in ages.EXTRAS else DEFAULT_AGE)
    theme = theme or getattr(s, "pack_theme", "animals")
    spelling = spelling_list(getattr(s, "pack_words", "") if spelling is None else spelling)
    if theme == "spelling" and not spelling:
        theme = "animals"
    if theme not in THEME_NAMES:
        theme = "animals"
    extras = ages.EXTRAS[age]
    base = {k: getattr(s, k) for k in ("cbn", "cbn_colours", "cbn_maths", "maze_shape", "maze_word", "ws_words",
                                       "name_text", "name_bg", "spot_base", "trace_text", "cross_words", "clock_task")}
    base.update(cbn=False, maze_shape="rect", maths_kind=extras["maths_kind"], trace_source=extras["trace_source"])
    if theme == "spelling":
        days = SPELLING_DAYS
        listed = ", ".join(spelling)
        clues = scramble.crossword_clues(mulberry32(seeds[1] ^ 0x5EED), [words.clean_word(w) for w in spelling])
        base.update(ws_theme="custom", ws_words=listed, cross_theme="custom", cross_words=clues,
                    trace_source="words", trace_text=listed)
    else:
        days = DAYS
        base.update(ws_theme=theme, cross_theme=theme)
        if extras["trace_source"] == "words":
            base["trace_text"] = ", ".join(theme_words(theme))
    pages = [{**base, "gen": gen, "seed": seed, "complexity": ages.COMPLEXITY[gen][age]}
             for gen, seed in zip(days, seeds)]
    return {"mode": "make", "age": age, "weight": extras["weight"], "booklet": True, "poster": False,
            "testpage": False, "fold": False, "cover": True, "name_line": True, "page_nums": True, "key": True,
            "ramp": False, "mix": False, "sheet": "one", "pages": len(pages), "page_list": pages,
            "pack_theme": theme, **{k: v for k, v in pages[0].items() if k != "seed"}}
