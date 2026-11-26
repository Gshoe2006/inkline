"""Worksheet packs: a week of classroom worksheets on one theme, for one age, as a booklet built page by page.

A pack is five pages, one for each school day, each set for the age as Age sets it (the sums, what's traced,
how hard the puzzles are):

- on a theme (animals, food, space, ocean, weather, sports): a maths drill, a handwriting sheet, a crossword, a
  word search and a maze, the crossword and word search on the theme, and an older child's handwriting sheet
  tracing the theme's words;
- on this week's spelling words, or a week of sight words (a pick from the list for the stage): the words four ways (traced, in a crossword whose clues are the words'
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
# what a day can be, when the teacher chooses the week's sheets (Booklet → Worksheet pack → the days)
DAY_CHOICES = ("maths", "early", "trace", "crossword", "words", "maze", "clock", "scramble", "spelltest", "fractions",
               "symmetry", "reading", "bingo", "dots", "sudoku", "kakuro")
THEMES = tuple(t for t in crossword.THEME_NAMES if t != "custom")   # themes the crossword and word search share
SIGHT = ("sight1", "sight2", "sight3")   # sight words: a week of them, picked from the word search's lists
THEME_NAMES = {**{t: crossword.THEME_NAMES[t] for t in THEMES}, **{t: words.THEME_NAMES[t] for t in SIGHT},
               "spelling": "Spelling words (your own list)"}
SIGHT_WEEK = 12   # sight words in a week's pack
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


def chosen_days(text):
    """The five days typed into pack_days ("maths,trace,..."), or None if they aren't five known sheets."""
    days = [d.strip() for d in (text or "").split(",") if d.strip()]
    return tuple(days) if len(days) == 5 and all(d in DAY_CHOICES for d in days) else None


def days_for(s, spelling):
    """The week's five sheets: the teacher's choice, else the usual ones for a theme or a spelling list."""
    return chosen_days(getattr(s, "pack_days", "")) or (SPELLING_DAYS if spelling else DAYS)


def week(s, seeds, theme=None, age=None, spelling=None):
    """The settings for a pack: {setting: value}, with page_list holding the five pages. s: the settings now
    (whose page options the pages start from); seeds: five seeds, one per page. The theme and spelling words
    are s.pack_theme and s.pack_words unless given; a spelling pack with no words is an animals pack."""
    age = age or (s.age if s.age in ages.EXTRAS else DEFAULT_AGE)
    theme = theme or getattr(s, "pack_theme", "animals")
    spelling = spelling_list(getattr(s, "pack_words", "") if spelling is None else spelling)
    chosen = theme       # what the controls keep showing (a sight-word pack is made as a spelling pack)
    if theme in SIGHT:   # this week's sight words: a seeded pick from the stage's list, then as spelling words
        pool = words.THEMES_BY_LANGUAGE.get(i18n.LANG, words.THEMES)[theme].split()
        rnd = mulberry32(seeds[0] ^ 0x51647)
        for i in range(len(pool) - 1, 0, -1):
            j = rnd() * (i + 1)
            pool[i], pool[int(j)] = pool[int(j)], pool[i]
        spelling, theme = pool[:SIGHT_WEEK], "spelling"
    if theme == "spelling" and not spelling:
        theme = "animals"
    if theme not in THEME_NAMES:
        theme = "animals"
    extras = ages.EXTRAS[age]
    base = {k: getattr(s, k) for k in ("cbn", "cbn_colours", "cbn_maths", "maze_shape", "maze_word", "ws_words",
                                       "name_text", "name_bg", "spot_base", "trace_text", "cross_words", "clock_task")}
    base.update(cbn=False, maze_shape="rect", maths_kind=extras["maths_kind"], trace_source=extras["trace_source"])
    if theme == "spelling":
        days = days_for(s, True)
        listed = ", ".join(spelling)
        clues = scramble.crossword_clues(mulberry32(seeds[1] ^ 0x5EED), [words.clean_word(w) for w in spelling])
        base.update(ws_theme="custom", ws_words=listed, cross_theme="custom", cross_words=clues,
                    trace_source="words", trace_text=listed)
    else:
        days = days_for(s, False)
        base.update(ws_theme=theme, cross_theme=theme)
        if extras["trace_source"] == "words":
            base["trace_text"] = ", ".join(theme_words(theme))
    pages = [{**base, "gen": gen, "seed": seed, "complexity": ages.COMPLEXITY[gen][age]}
             for gen, seed in zip(days, seeds)]
    return {"mode": "make", "age": age, "weight": extras["weight"], "booklet": True, "poster": False,
            "testpage": False, "fold": False, "cover": True, "name_line": True, "page_nums": True, "key": True,
            "ramp": False, "mix": False, "sheet": "one", "pages": len(pages), "page_list": pages,
            "pack_theme": chosen if chosen in SIGHT else theme, **{k: v for k, v in pages[0].items() if k != "seed"}}
