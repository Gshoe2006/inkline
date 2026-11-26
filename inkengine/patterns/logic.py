"""Logic puzzle: who has which pet, wears which colour, eats which fruit or plays which sport, worked out from clues.

Three things to match up (the children, then two of pets, colours, fruit and sports, picked by the seed), with 3
items each at complexity 1-3, 4 at 4-7 and 5 at 8-10. The seed makes up the answer, then the clues: every true
"has" and "does not have" sentence is a candidate, taken in a seeded order (at higher complexity the "does not"
clues come first, so fewer give an answer away) until the solver below can finish the grid, and then each clue
it can do without is dropped again. So the clues left are just enough.

The solver only uses the rules a child uses with the grid: a tick rules out the rest of its row and column, a
row or column with one box left gets a tick, and two ticks (or a tick and a cross) in the other parts of the
grid say what goes in a third box. Every step is certain, so a grid the solver fills has one answer only.

The page has the grid (the children down the side, then the third thing under the second's columns, as printed
logic puzzles have it) and the numbered clues. The answer page ticks the grid and lists who has what.

Words are written in each language, as the word search's themes are: each item has the short word for the grid
and the words a clue uses (with "the" or "den" or "au" as that language needs); the sentences are translated.
"""

from .. import i18n
from ..i18n import tr
from ..rng import pick

# the sentences for each kind of thing: saying it, saying not, and "the child who ..." to start a sentence
SENTENCES = {"pet": "{who} has {x}.", "colour": "{who} wears {x}.", "fruit": "{who} eats {x}.", "sport": "{who} plays {x}.",
             "child": "{who} is {x}."}
NOT_SENTENCES = {"pet": "{who} does not have {x}.", "colour": "{who} does not wear {x}.", "fruit": "{who} does not eat {x}.",
                 "sport": "{who} does not play {x}.", "child": "{who} is not {x}."}
WHO_PHRASES = {"pet": "the child who has {x}", "colour": "the child who wears {x}", "fruit": "the child who eats {x}",
               "sport": "the child who plays {x}"}
HEADINGS = {"child": "Child", "pet": "Pet", "colour": "Colour", "fruit": "Fruit", "sport": "Sport"}

# each item: (the word in the grid, the words in a clue)
WORDS = {
    "en": {
        "child": "Mia Sam Leo Ava Ben Zoe Max Lily Noah Ella",
        "pet": [("dog", "the dog"), ("cat", "the cat"), ("rabbit", "the rabbit"), ("fish", "the fish"),
                ("parrot", "the parrot"), ("hamster", "the hamster"), ("tortoise", "the tortoise")],
        "colour": [("red", "red"), ("blue", "blue"), ("green", "green"), ("yellow", "yellow"), ("purple", "purple"),
                   ("orange", "orange")],
        "fruit": [("apple", "the apple"), ("banana", "the banana"), ("pear", "the pear"), ("orange", "the orange"),
                  ("grapes", "the grapes"), ("cherries", "the cherries"), ("plum", "the plum")],
        "sport": [("tennis", "tennis"), ("hockey", "hockey"), ("golf", "golf"), ("basketball", "basketball"),
                  ("volleyball", "volleyball"), ("badminton", "badminton")],
    },
    "es": {
        "child": "Lucía Pablo Sofía Hugo Martina Leo Daniela Mateo Carla Álex",
        "pet": [("perro", "el perro"), ("gato", "el gato"), ("conejo", "el conejo"), ("pez", "el pez"),
                ("loro", "el loro"), ("hámster", "el hámster"), ("tortuga", "la tortuga")],
        "colour": [("rojo", "rojo"), ("azul", "azul"), ("verde", "verde"), ("amarillo", "amarillo"),
                   ("morado", "morado"), ("naranja", "naranja")],
        "fruit": [("manzana", "la manzana"), ("plátano", "el plátano"), ("pera", "la pera"), ("naranja", "la naranja"),
                  ("uvas", "las uvas"), ("cerezas", "las cerezas"), ("ciruela", "la ciruela")],
        "sport": [("fútbol", "al fútbol"), ("tenis", "al tenis"), ("baloncesto", "al baloncesto"), ("golf", "al golf"),
                  ("hockey", "al hockey"), ("voleibol", "al voleibol")],
    },
    "fr": {
        "child": "Léa Hugo Emma Louis Chloé Jules Inès Noé Zoé Tom",
        "pet": [("chien", "le chien"), ("chat", "le chat"), ("lapin", "le lapin"), ("poisson", "le poisson"),
                ("perroquet", "le perroquet"), ("hamster", "le hamster"), ("tortue", "la tortue")],
        "colour": [("rouge", "rouge"), ("bleu", "bleu"), ("vert", "vert"), ("jaune", "jaune"), ("violet", "violet"),
                   ("orange", "orange")],
        "fruit": [("pomme", "la pomme"), ("banane", "la banane"), ("poire", "la poire"), ("orange", "l'orange"),
                  ("raisin", "le raisin"), ("cerises", "les cerises"), ("prune", "la prune")],
        "sport": [("football", "au football"), ("tennis", "au tennis"), ("basket", "au basket"), ("golf", "au golf"),
                  ("hockey", "au hockey"), ("rugby", "au rugby")],
    },
    "pt": {
        "child": "Ana Pedro Sofia Lucas Laura Davi Júlia Miguel Alice Rafael",
        "pet": [("cachorro", "o cachorro"), ("gato", "o gato"), ("coelho", "o coelho"), ("peixe", "o peixe"),
                ("papagaio", "o papagaio"), ("hamster", "o hamster"), ("tartaruga", "a tartaruga")],
        "colour": [("vermelho", "vermelho"), ("azul", "azul"), ("verde", "verde"), ("amarelo", "amarelo"),
                   ("roxo", "roxo"), ("laranja", "laranja")],
        "fruit": [("maçã", "a maçã"), ("banana", "a banana"), ("pera", "a pera"), ("laranja", "a laranja"),
                  ("uvas", "as uvas"), ("cerejas", "as cerejas"), ("manga", "a manga")],
        "sport": [("futebol", "futebol"), ("tênis", "tênis"), ("basquete", "basquete"), ("vôlei", "vôlei"),
                  ("golfe", "golfe"), ("handebol", "handebol")],
    },
    "de": {
        "child": "Mia Paul Emma Ben Lina Finn Lea Noah Hanna Tim",
        "pet": [("Hund", "den Hund"), ("Katze", "die Katze"), ("Hase", "den Hasen"), ("Fisch", "den Fisch"),
                ("Papagei", "den Papagei"), ("Hamster", "den Hamster"), ("Schildkröte", "die Schildkröte")],
        "colour": [("Rot", "Rot"), ("Blau", "Blau"), ("Grün", "Grün"), ("Gelb", "Gelb"), ("Lila", "Lila"),
                   ("Orange", "Orange")],
        "fruit": [("Apfel", "den Apfel"), ("Banane", "die Banane"), ("Birne", "die Birne"), ("Orange", "die Orange"),
                  ("Trauben", "die Trauben"), ("Kirschen", "die Kirschen"), ("Pflaume", "die Pflaume")],
        "sport": [("Fußball", "Fußball"), ("Tennis", "Tennis"), ("Basketball", "Basketball"), ("Golf", "Golf"),
                  ("Hockey", "Hockey"), ("Volleyball", "Volleyball")],
    },
    "it": {
        "child": "Giulia Luca Sofia Marco Anna Leo Sara Matteo Alice Pietro",
        "pet": [("cane", "il cane"), ("gatto", "il gatto"), ("coniglio", "il coniglio"), ("pesce", "il pesce"),
                ("pappagallo", "il pappagallo"), ("criceto", "il criceto"), ("tartaruga", "la tartaruga")],
        "colour": [("rosso", "rosso"), ("blu", "blu"), ("verde", "verde"), ("giallo", "giallo"), ("viola", "viola"),
                   ("arancione", "arancione")],
        "fruit": [("mela", "la mela"), ("banana", "la banana"), ("pera", "la pera"), ("arancia", "l'arancia"),
                  ("uva", "l'uva"), ("ciliegie", "le ciliegie"), ("prugna", "la prugna")],
        "sport": [("calcio", "calcio"), ("tennis", "tennis"), ("basket", "basket"), ("golf", "golf"),
                  ("pallavolo", "pallavolo"), ("rugby", "rugby")],
    },
    "nl": {
        "child": "Emma Daan Sophie Sem Julia Lucas Tess Finn Noor Bram",
        "pet": [("hond", "de hond"), ("kat", "de kat"), ("konijn", "het konijn"), ("vis", "de vis"),
                ("papegaai", "de papegaai"), ("hamster", "de hamster"), ("schildpad", "de schildpad")],
        "colour": [("rood", "rood"), ("blauw", "blauw"), ("groen", "groen"), ("geel", "geel"), ("paars", "paars"),
                   ("oranje", "oranje")],
        "fruit": [("appel", "de appel"), ("banaan", "de banaan"), ("peer", "de peer"), ("sinaasappel", "de sinaasappel"),
                  ("druiven", "de druiven"), ("kersen", "de kersen"), ("pruim", "de pruim")],
        "sport": [("voetbal", "voetbal"), ("tennis", "tennis"), ("hockey", "hockey"), ("golf", "golf"),
                  ("basketbal", "basketbal"), ("volleybal", "volleybal")],
    },
}
THINGS = ("pet", "colour", "fruit", "sport")
INSTRUCTIONS = "Use the clues to work out who has what. Put a tick in a box for yes and a cross for no."


def size_for(c):
    return 3 if c <= 3 else 4 if c <= 7 else 5


def _shuffle(items, rnd):
    for i in range(len(items) - 1, 0, -1):
        j = pick(rnd, i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def _words():
    return WORDS.get(i18n.LANG, WORDS["en"])


# --- the solver ----------------------------------------------------------------------------------------------------

class Grid:
    """What's known about each pair of items: True (a tick), False (a cross) or None (empty), for the three parts of
    the grid: (0, 1), (0, 2) and (1, 2), where 0 is the children."""

    def __init__(self, n):
        self.n = n
        self.cells = {pair: [[None] * n for _ in range(n)] for pair in ((0, 1), (0, 2), (1, 2))}

    def get(self, x, i, y, j):
        return self.cells[(x, y)][i][j] if x < y else self.cells[(y, x)][j][i]

    def set(self, x, i, y, j, v):
        """Write a tick or cross: True if it's new, False if it was there already. ValueError if it disagrees."""
        old = self.get(x, i, y, j)
        if old is not None:
            if old != v:
                raise ValueError("the clues disagree")
            return False
        if x < y:
            self.cells[(x, y)][i][j] = v
        else:
            self.cells[(y, x)][j][i] = v
        return True

    def solved(self):
        return all(v is not None for m in self.cells.values() for row in m for v in row)

    def answer(self):
        """[(child, item of 1, item of 2)] for each child, from the ticks."""
        out = []
        for i in range(self.n):
            a = next(j for j in range(self.n) if self.get(0, i, 1, j))
            b = next(j for j in range(self.n) if self.get(0, i, 2, j))
            out.append((i, a, b))
        return out


def deduce(n, clues):
    """Fill a grid from clues [(yes, x, i, y, j)] with the simple rules: the Grid, or None if the clues disagree.
    grid.solved() says whether the rules finished it."""
    g = Grid(n)
    try:
        for yes, x, i, y, j in clues:
            g.set(x, i, y, j, yes)
        changed = True
        while changed:
            changed = False
            for (x, y), m in g.cells.items():
                for i in range(n):   # a tick rules out its row and column; one box left in a row or column is a tick
                    for line in ([(i, j) for j in range(n)], [(j, i) for j in range(n)]):
                        vals = [m[a][b] for a, b in line]
                        if True in vals:
                            for a, b in line:
                                if m[a][b] is None:
                                    changed |= g.set(x, a, y, b, False)
                        elif vals.count(False) == n - 1 and None in vals:
                            a, b = line[vals.index(None)]
                            changed |= g.set(x, a, y, b, True)
                        elif vals.count(False) == n:
                            raise ValueError("nothing left")
            for x, y, z in ((0, 1, 2), (0, 2, 1), (1, 2, 0)):   # what a third part of the grid says
                for i in range(n):
                    for j in range(n):
                        if g.get(x, i, y, j) is not None:
                            continue
                        for k in range(n):
                            xz, yz = g.get(x, i, z, k), g.get(y, j, z, k)
                            if xz and yz:
                                changed |= g.set(x, i, y, j, True)
                                break
                            if (xz and yz is False) or (yz and xz is False):
                                changed |= g.set(x, i, y, j, False)
                                break
    except ValueError:
        return None
    return g


def count_answers(n, clues):
    """How many answers the clues allow, trying every one (for checking: at most 5! x 5! = 14400)."""
    from itertools import permutations
    found = 0
    for a in permutations(range(n)):
        for b in permutations(range(n)):
            items = {0: list(range(n)), 1: list(a), 2: list(b)}
            ok = True
            for yes, x, i, y, j in clues:
                child = items[x].index(i)
                if (items[y][child] == j) != yes:
                    ok = False
                    break
            found += ok
    return found


# --- making a puzzle -----------------------------------------------------------------------------------------------

def make_puzzle(rnd, c):
    """{"kinds": (child, thing, thing), "items": [[(grid word, clue words)] x3], "answer": [(child, a, b)],
    "clues": [(yes, x, i, y, j)]}: item i of kind x goes (yes) or doesn't go (not yes) with item j of kind y."""
    n = size_for(c)
    words = _words()
    things = _shuffle(list(THINGS), rnd)[:2]
    things.sort(key=THINGS.index)
    kinds = ("child",) + tuple(things)
    names = _shuffle(words["child"].split(), rnd)[:n]
    items = [[(nm, nm) for nm in names]] + [_shuffle(list(words[k]), rnd)[:n] for k in things]
    a, b = _shuffle(list(range(n)), rnd), _shuffle(list(range(n)), rnd)
    answer = [(i, a[i], b[i]) for i in range(n)]
    owner = {0: list(range(n)), 1: [a.index(j) for j in range(n)], 2: [b.index(j) for j in range(n)]}   # whose item j is
    candidates = []
    for x, y in ((0, 1), (0, 2), (1, 2), (2, 1), (1, 0), (2, 0)):   # (who the sentence is about, what it says)
        for i in range(n):
            for j in range(n):
                yes = owner[x][i] == owner[y][j]
                late = 0.3 if yes and c >= 4 else 0.0   # harder puzzles say "not" more and give fewer away
                candidates.append((rnd() + late, (yes, x, i, y, j)))
    candidates.sort(key=lambda t: t[0])
    clues = []
    for _k, clue in candidates:
        x, i, y, j = clue[1:]
        if any((x, i, y, j) == (q[3], q[4], q[1], q[2]) or (x, i, y, j) == q[1:] for q in clues):
            continue   # the same pair said the other way round
        clues.append(clue)
        g = deduce(n, clues)
        if g is not None and g.solved():
            break
    for clue in _shuffle(clues[:], rnd):   # then each clue the rest can do without goes
        rest = [q for q in clues if q is not clue]
        g = deduce(n, rest)
        if g is not None and g.solved():
            clues = rest
    return {"kinds": kinds, "items": items, "answer": answer, "clues": _shuffle(clues, rnd)}


def sentence(p, clue):
    """A clue as a sentence in the current language."""
    yes, x, i, y, j = clue
    kinds, items = p["kinds"], p["items"]
    said = tr((SENTENCES if yes else NOT_SENTENCES)[kinds[y]])
    who = items[x][i][1] if x == 0 else tr(WHO_PHRASES[kinds[x]]).format(x=items[x][i][1])
    text = said.format(who=who, x=items[y][j][1])
    return text[:1].upper() + text[1:]


# --- drawing -------------------------------------------------------------------------------------------------------

def _wrap(ctx, text, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and ctx.measure_text(trial) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def _grid_size(ctx, p, w, h):
    """The square size, the row labels' width and the column labels' height for the grid to fit in w x h."""
    n = len(p["items"][0])
    rows = [t for t, _ in p["items"][0]] + [t for t, _ in p["items"][2]]
    cols = [t for t, _ in p["items"][1]] + [t for t, _ in p["items"][2]]
    cell = min(w / (2 * n + 2.5), h / (2 * n + 3))
    for _ in range(30):
        fs = cell * 0.42
        ctx.set_font(fs, 500)
        lab_w = max(ctx.measure_text(t) for t in rows) + fs * 2.2   # the heading of each part goes beside its labels
        lab_h = max(ctx.measure_text(t) for t in cols) + fs * 2.2
        if lab_w + 2 * n * cell <= w and lab_h + 2 * n * cell <= h:
            break
        cell *= 0.93
    return cell, lab_w, lab_h


def _tick(ctx, x, y, s):
    ctx.begin_path()
    ctx.move_to(x + s * 0.2, y + s * 0.55)
    ctx.line_to(x + s * 0.42, y + s * 0.76)
    ctx.line_to(x + s * 0.8, y + s * 0.26)
    ctx.stroke()


def _cross(ctx, x, y, s):
    ctx.begin_path()
    ctx.move_to(x + s * 0.3, y + s * 0.3)
    ctx.line_to(x + s * 0.7, y + s * 0.7)
    ctx.move_to(x + s * 0.7, y + s * 0.3)
    ctx.line_to(x + s * 0.3, y + s * 0.7)
    ctx.stroke()


def draw_grid(ctx, p, x0, y0, w, h, lw, grid=None, size=None):
    """The grid in w x h at (x0, y0): children down the side then the third kind; the second kind across, then the
    third. grid (a solved Grid) ticks it. Returns its (width, height)."""
    n = len(p["items"][0])
    cell, lab_w, lab_h = size or _grid_size(ctx, p, w, h)
    gx, gy = x0 + lab_w, y0 + lab_h
    fs = cell * 0.42
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.set_font(fs, 500)
    # the labels: rows to the left, columns turned to read upwards
    ctx.text_align, ctx.text_baseline = "right", "middle"
    for r, (part, k) in enumerate([(0, i) for i in range(n)] + [(2, i) for i in range(n)]):
        ctx.fill_text(p["items"][part][k][0], gx - fs * 0.4, gy + (r + 0.5) * cell)
    for col, (part, k) in enumerate([(1, i) for i in range(n)] + [(2, i) for i in range(n)]):
        ctx.save()
        ctx.translate(gx + (col + 0.5) * cell, gy - fs * 0.4)
        ctx.transform(0, -1, 1, 0, 0, 0)
        ctx.text_align = "left"
        ctx.fill_text(p["items"][part][k][0], 0, 0)
        ctx.restore()
    # each part's heading, in bold beside its labels
    ctx.set_font(fs * 0.95, 700)
    ctx.text_align, ctx.text_baseline = "center", "top"
    for part, (cx, offset) in ((1, (gx + n * cell / 2, 0)), (2, (gx + n * cell * 1.5, 0))):
        ctx.fill_text(tr(HEADINGS[p["kinds"][part]]), cx, y0 + offset)
    for part, cy in ((0, gy + n * cell / 2), (2, gy + n * cell * 1.5)):
        ctx.save()
        ctx.translate(x0 + fs * 0.1, cy)
        ctx.transform(0, -1, 1, 0, 0, 0)
        ctx.text_align, ctx.text_baseline = "center", "top"
        ctx.fill_text(tr(HEADINGS[p["kinds"][part]]), 0, 0)
        ctx.restore()
    # the squares: three parts, thick lines round each and between them
    blocks = ((0, 0, 0, 1), (n, 0, 0, 2), (0, n, 2, 1))   # (column, row, kind down, kind across)
    for bc, br, down, across in blocks:
        bx, by = gx + bc * cell, gy + br * cell
        ctx.line_width = max(1.0, lw * 0.5)
        ctx.begin_path()
        for k in range(1, n):
            ctx.move_to(bx + k * cell, by)
            ctx.line_to(bx + k * cell, by + n * cell)
            ctx.move_to(bx, by + k * cell)
            ctx.line_to(bx + n * cell, by + k * cell)
        ctx.stroke()
        ctx.line_width = max(1.5, lw * 1.2)
        ctx.stroke_rect(bx, by, n * cell, n * cell)
        if grid is None:
            continue
        for i in range(n):
            for j in range(n):
                v = grid.get(down, i, across, j)
                x, y = bx + j * cell, by + i * cell
                if v:
                    ctx.stroke_style, ctx.line_width = "#000", max(1.5, lw * 1.1)
                    _tick(ctx, x, y, cell)
                elif v is False:
                    ctx.stroke_style, ctx.line_width = "#999", max(1.0, lw * 0.5)
                    _cross(ctx, x, y, cell)
        ctx.stroke_style = "#000"
    return lab_w + 2 * n * cell, lab_h + 2 * n * cell


def _clue_lines(ctx, p, w, fs):
    ctx.set_font(fs, 400)
    out = []
    for k, clue in enumerate(p["clues"]):
        for m, line in enumerate(_wrap(ctx, f"{k + 1}. {sentence(p, clue)}", w)):
            out.append((m == 0, line))
    return out


def _clue_rest(lines, k):
    """The lines of the clue that starts at line k."""
    yield lines[k]
    for first, line in lines[k + 1:]:
        if first:
            return
        yield first, line


def _clue_columns(ctx, p, w, h, fs, dpi):
    """The clues as columns of lines that fit in w x h: (size, columns, column width), as big as they'll go, in two
    columns rather than smaller when there's room across."""
    size = fs
    while True:
        for cols in (1, 2):
            cw = (w - fs * (cols - 1)) / cols
            if cols > 1 and cw < dpi * 2.4:
                continue
            lines = _clue_lines(ctx, p, cw, size)
            per = -(-len(lines) // cols)
            columns = [[]]
            for k, (first, line) in enumerate(lines):   # a clue stays in one column
                if first and len(columns) < cols and len(columns[-1]) + sum(1 for _ in _clue_rest(lines, k)) > per:
                    columns.append([])
                columns[-1].append((first, line))
            if max(len(col) for col in columns) * size * 1.4 <= h or size <= dpi * 0.07:
                return size, columns, cw
        size *= 0.93


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    p = make_puzzle(rnd, c)
    n = len(p["items"][0])
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    side = box.w > box.h * 1.15   # landscape: the grid on the left, the clues on the right
    fs = min(dpi * 0.2, box.h / 22)
    top = box.y
    if not solve:
        ctx.set_font(fs * 0.9, 400)
        ctx.text_align, ctx.text_baseline = "left", "alphabetic"
        for line in _wrap(ctx, tr(INSTRUCTIONS), box.w):
            top += fs * 1.25
            ctx.fill_text(line, box.x, top)
        top += fs * 0.8
    h = box.y + box.h - top
    gw, gh = (box.w * 0.5, h) if side else (box.w, h * (0.5 if not solve else 0.7))
    size = _grid_size(ctx, p, gw, gh)
    used_w, used_h = size[1] + 2 * n * size[0], size[2] + 2 * n * size[0]
    gx = box.x if side else box.x + (box.w - used_w) / 2
    grid = deduce(n, p["clues"]) if solve else None
    draw_grid(ctx, p, gx, top, gw, gh, lw, grid, size)
    if side:
        tx, ty = box.x + used_w + box.w * 0.04, top
        tw, th = box.x + box.w - tx, h
    else:
        tx, ty, tw, th = box.x, top + used_h + fs, box.w, h - used_h - fs
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    if solve:   # who has what, a line each
        rows = [", ".join([p["items"][0][i][0], p["items"][1][a][0], p["items"][2][b][0]]) for i, a, b in p["answer"]]
        size = min(fs, th / (len(rows) * 1.5 + 0.5))
        ctx.set_font(size, 500)
        for k, row in enumerate(rows):
            ctx.fill_text(row, tx, ty + (k + 1) * size * 1.5, tw)
        ctx.restore()
        return {"kinds": p["kinds"], "size": n, "clues": len(p["clues"])}
    size, columns, cw = _clue_columns(ctx, p, tw, th, fs, dpi)
    ctx.set_font(size, 400)
    for k, lines in enumerate(columns):
        x, y = tx + k * (cw + fs), ty
        for first, line in lines:
            y += size * (1.4 if first else 1.25)
            ctx.fill_text(line, x if first else x + size * 1.2, y)
    ctx.restore()
    return {"kinds": p["kinds"], "size": n, "clues": len(p["clues"]), "sentences": [sentence(p, q) for q in p["clues"]],
            "clue_size": size / dpi}

