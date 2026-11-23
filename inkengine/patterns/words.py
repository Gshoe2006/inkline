"""Word search: words hidden in a grid of letters, each exactly once, with a list to tick off.

Ported line for line from index.html (wordPool, makeWordSearch, genWords), so a seed gives the same
puzzle as Inkline 2.x. tests/test_words.py checks this against recordings of the JavaScript.

Words come from a theme (a seeded pick) or your own list (all of it). They are hidden longest first,
across and down at low complexity and up to all eight directions at the highest, crossing where
their letters agree. The gaps get random letters; a fill that accidentally spells a listed word a
second time is redone, so every word appears exactly once. Words too long for the grid, or hidden
inside another listed word (RAIN in RAINBOW, SUN backwards in VENUS), are left out and reported.
"""

import math
import re

from ..rng import pick
from .. import i18n
from ..i18n import tr

THEMES = {
    "animals": "cat dog horse tiger zebra rabbit monkey giraffe lion bear mouse sheep goat duck frog owl eagle panda koala otter camel hippo snake turtle wolf fox",
    "ocean": "wave shell crab whale shark coral octopus dolphin seal tide sand reef squid kelp starfish jellyfish lobster anchor boat pearl salt clam",
    "space": "star moon planet comet rocket orbit galaxy saturn mars venus earth jupiter asteroid nebula alien sun meteor crater astronaut telescope",
    "food": "apple bread cheese pizza pasta soup salad banana grape mango carrot rice honey cookie muffin peach lemon toast butter pear plum",
    "weather": "rain snow wind cloud storm sunny thunder fog hail frost rainbow breeze mist sleet heat chilly drizzle tornado",
    "sports": "soccer tennis golf hockey rugby cycling skating skiing rowing boxing karate surfing archery baseball cricket diving judo running",
}
# The same themes in Spanish, used when Inkline is in Spanish (words keep Ñ; other accents come off, as Spanish
# word searches print them)
THEMES_ES = {
    "animals": "gato perro caballo tigre cebra conejo mono jirafa leon oso raton oveja cabra pato rana buho aguila "
               "panda koala nutria camello hipopotamo serpiente tortuga lobo zorro pingüino ardilla",
    "ocean": "ola concha cangrejo ballena tiburon coral pulpo delfin foca marea arena arrecife calamar alga estrella "
             "medusa langosta ancla barco perla sal almeja",
    "space": "estrella luna planeta cometa cohete orbita galaxia saturno marte venus tierra jupiter asteroide "
             "nebulosa extraterrestre sol meteorito crater astronauta telescopio",
    "food": "manzana pan queso pizza pasta sopa ensalada platano uva mango zanahoria arroz miel galleta magdalena "
            "melocoton limon tostada mantequilla pera ciruela piña",
    "weather": "lluvia nieve viento nube tormenta sol trueno niebla granizo escarcha arcoiris brisa rocio calor frio "
               "llovizna tornado",
    "sports": "futbol tenis golf hockey rugby ciclismo patinaje esqui remo boxeo karate surf tiro beisbol criquet "
              "buceo judo carrera",
}
THEMES_FR = {
    "animals": "chat chien cheval tigre zèbre lapin singe girafe lion ours souris mouton chèvre canard grenouille "
               "hibou aigle panda koala loutre chameau serpent tortue loup renard pingouin écureuil",
    "ocean": "vague coquillage crabe baleine requin corail pieuvre dauphin phoque marée sable récif calmar algue "
             "étoile méduse homard ancre bateau perle sel moule",
    "space": "étoile lune planète comète fusée orbite galaxie saturne mars vénus terre jupiter astéroïde nébuleuse "
             "soleil météorite cratère astronaute télescope satellite",
    "food": "pomme pain fromage pizza pâtes soupe salade banane raisin mangue carotte riz miel biscuit gâteau "
            "pêche citron tartine beurre poire prune ananas",
    "weather": "pluie neige vent nuage orage soleil tonnerre brouillard grêle givre flocon brise rosée chaleur froid "
               "bruine tornade éclair tempête",
    "sports": "football tennis golf hockey rugby vélo patinage ski aviron boxe karaté surf judo natation course "
              "basket danse escrime voile plongée",
}
THEMES_BY_LANGUAGE = {"es": THEMES_ES, "fr": THEMES_FR}
THEME_NAMES = {"animals": "Animals", "ocean": "Ocean", "space": "Space", "food": "Food", "weather": "Weather",
               "sports": "Sports", "custom": "Your own list"}
DIRS = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]   # E, S, SE, NE, then the backwards ones


def level(c):
    """Grid 8..16, 6..15 words, directions from across/down up to all eight."""
    n = 2 if c <= 3 else 4 if c <= 6 else 6 if c <= 8 else 8
    return {"size": 8 + int(math.floor((c - 1) * 8 / 9 + 0.5)), "count": 5 + c, "dirs": DIRS[:n]}


def clean_word(w):
    if i18n.LANG != "en":   # accents off, the language's own letters kept (Spanish NIÑO, not NINO)
        return i18n.grid_letters(w)
    return re.sub(r"[^A-Z]", "", w.upper())   # as 2.x did (its recordings are checked)


def _alphabet():
    """The letters that fill a grid's gaps: A-Z, and Ñ in Spanish (so a word's Ñ doesn't stand out)."""
    return i18n.alphabet() if i18n.LANG in i18n.ALPHABETS else None


def hidden_in(w, o):
    """A word hidden inside another (forwards or backwards) can never appear exactly once."""
    return o != w and (w in o or w[::-1] in o)


def _shuffle(items, rnd):
    for i in range(len(items) - 1, 0, -1):
        j = pick(rnd, i + 1)
        items[i], items[j] = items[j], items[i]


def word_pool(rnd, c, theme="animals", own_words=""):
    """The words for one puzzle: your own list if chosen (all of it), else a seeded pick from the theme."""
    lv = level(c)
    if theme == "custom":
        mine = list(dict.fromkeys(w for w in (clean_word(x) for x in re.split(r"[\s,;]+", own_words)) if len(w) >= 2))
        if mine:
            return mine
    themes = THEMES_BY_LANGUAGE.get(i18n.LANG, THEMES)
    pool = [w for w in (clean_word(x) for x in themes.get(theme, themes["animals"]).split(" ")) if len(w) <= lv["size"]]
    _shuffle(pool, rnd)
    chosen = []   # skip any word that hides inside (or contains) one already chosen
    for w in pool:
        if len(chosen) < lv["count"] and not any(hidden_in(w, o) or hidden_in(o, w) for o in chosen):
            chosen.append(w)
    return chosen


def find_word(grid, size, word):
    """How many places the word can be read, in any of the 8 directions (a palindrome counts once)."""
    hits, n, first = set(), len(word), word[0]
    for r in range(size):
        for c in range(size):
            if grid[r * size + c] != first:
                continue
            for dr, dc in DIRS:
                er, ec = r + dr * (n - 1), c + dc * (n - 1)
                if not (0 <= er < size and 0 <= ec < size):
                    continue
                if all(grid[(r + dr * k) * size + c + dc * k] == word[k] for k in range(1, n)):
                    a, b = r * size + c, er * size + ec
                    hits.add((min(a, b), max(a, b)))
    return len(hits)


def make_word_search(rnd, c, words):
    """{size, grid, placed, skipped}, or None if no fair fill was found (practically never)."""
    lv = level(c)
    size, dirs = lv["size"], lv["dirs"]
    left = [f"{w} (too long for {size} × {size})" for w in words if len(w) > size]
    fit = [w for w in words if len(w) <= size]
    inside = [w for w in fit if any(hidden_in(w, o) for o in fit)]
    for w in inside:
        left.append(f"{w} (it's inside {next(o for o in fit if hidden_in(w, o))})")
    # longest first; equal lengths keep their order, as JavaScript's stable sort does
    order = sorted((w for w in fit if w not in inside), key=lambda w: -len(w))
    for _attempt in range(40):
        grid, placed, skipped = [""] * (size * size), [], []
        for w in order:   # longest first; words may cross where their letters agree
            done = False
            for _t in range(300):
                dr, dc = dirs[pick(rnd, len(dirs))]
                r, col = pick(rnd, size), pick(rnd, size)
                er, ec = r + dr * (len(w) - 1), col + dc * (len(w) - 1)
                if er < 0 or ec < 0 or er >= size or ec >= size:
                    continue
                if not all(grid[(r + dr * k) * size + col + dc * k] in ("", w[k]) for k in range(len(w))):
                    continue
                for k in range(len(w)):
                    grid[(r + dr * k) * size + col + dc * k] = w[k]
                placed.append({"word": w, "r": r, "c": col, "dr": dr, "dc": dc})
                done = True
                break
            if not done:
                skipped.append(f"{w} (no room left)")
        blanks = [i for i, ch in enumerate(grid) if not ch]
        letters = _alphabet()
        for _fill in range(30):   # fill the gaps; redo the fill if it spells a listed word a second time
            for i in blanks:
                grid[i] = letters[pick(rnd, len(letters))] if letters else chr(65 + pick(rnd, 26))
            if all(find_word(grid, size, p["word"]) == 1 for p in placed):
                return {"size": size, "grid": grid, "placed": placed, "skipped": left + skipped}
    return None


def note(ws):
    """What to tell the person about words that were left out, or ""."""
    if not ws or not ws["skipped"]:
        return ""
    text = tr("Left out: {words}.").format(words=", ".join(ws["skipped"]))
    return text + (" Raise Complexity for a bigger grid." if any("too long" in t for t in ws["skipped"]) else "")


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The grid and the word list (or, with solve=True, the grid with each word ringed)."""
    theme = getattr(settings, "ws_theme", "animals")
    own = getattr(settings, "ws_words", "")
    ws = make_word_search(rnd, c, word_pool(rnd, c, theme, own))
    if not ws:
        return None
    size, grid, placed = ws["size"], ws["grid"], ws["placed"]
    words = sorted(p["word"] for p in placed)
    side = min(box.w, box.h) if solve else min(box.w, box.h * 0.66)
    cs = side / size
    x0 = box.x + (box.w - side) / 2
    y0 = box.y + ((box.h - side) / 2 if solve else 0)

    def centre(r, col):
        return x0 + (col + 0.5) * cs, y0 + (r + 0.5) * cs

    ctx.save()
    ctx.line_cap = ctx.line_join = "round"
    if solve:   # answer page: a hollow capsule round each word (black, then a narrower white pass)
        wide, ring = cs * 0.8, max(1, lw * 0.6)
        for white in (False, True):
            for p in placed:
                ctx.stroke_style = "#fff" if white else "#000"
                ctx.line_width = wide - 2 * ring if white else wide
                ctx.begin_path()
                ctx.move_to(*centre(p["r"], p["c"]))
                n = len(p["word"]) - 1
                ctx.line_to(*centre(p["r"] + p["dr"] * n, p["c"] + p["dc"] * n))
                ctx.stroke()
    ctx.fill_style, ctx.text_align, ctx.text_baseline = "#000", "center", "alphabetic"
    ctx.set_font(cs * 0.58, 600)
    for i in range(size * size):
        x, y = centre(i // size, i % size)
        ctx.fill_text(grid[i], x, y + cs * 0.21)
    ctx.stroke_style, ctx.line_width = "#000", max(1, lw * 0.8)
    ctx.stroke_rect(x0 - cs * 0.15, y0 - cs * 0.15, side + cs * 0.3, side + cs * 0.3)
    if not solve:   # the word list to tick off, in columns under the grid
        top = y0 + side + cs * 0.6
        avail = box.y + box.h - top
        cols = 4 if len(words) > 12 else 3
        rows = math.ceil(len(words) / cols)
        fs = min(dpi * 0.16, cs * 0.5)
        if rows * fs * 1.6 + fs * 1.8 > avail:
            fs = avail / (rows * 1.6 + 1.8)
        ctx.text_align = "left"
        ctx.set_font(fs, 700)
        ctx.fill_text(tr("Find these words"), box.x, top + fs)
        ctx.set_font(fs, 500)
        ctx.line_width = max(1, lw * 0.4)
        col_w = box.w / cols
        for i, w in enumerate(words):
            x, y = box.x + (i % cols) * col_w, top + fs * 2.7 + (i // cols) * fs * 1.6
            ctx.stroke_rect(x, y - fs * 0.78, fs * 0.8, fs * 0.8)
            ctx.fill_text(w, x + fs * 1.2, y)
    ctx.restore()
    return ws
