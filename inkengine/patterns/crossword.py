"""Crossword: words that cross in a grid, numbered as crosswords are, with Across and Down clues to solve.

Words and clues come from a theme (a seeded pick, with simple clues for children) or your own list, one
"word: clue" per line (a word without a clue gets "?"). Complexity sets how many words from a theme: 5 at 1,
14 at 10; your own list is used whole.

The longest word goes across the middle; each next word goes where it crosses the most letters already
placed, without touching another word side by side (so no stray words appear), ties broken by the seed. The
best of several tries (each with the words in another order) is kept: the most words, then the smallest grid.
A theme's words that find no place give way to others from the theme; your own words that can't cross
anything are left out and reported, as the word search does. The answer page shows the grid filled in.
"""

import re

from ..rng import pick
from .. import i18n
from ..i18n import tr

THEMES = {
    "animals": "cat: Says miaow; dog: Barks and wags its tail; cow: Gives us milk; horse: You can ride it; "
               "sheep: Its wool makes jumpers; duck: Says quack; frog: Green, and hops; owl: Hoots at night; "
               "lion: King of the jungle; tiger: A big cat with stripes; zebra: A horse with stripes; "
               "monkey: Swings from trees; rabbit: Has long ears and hops; mouse: Small, and likes cheese; "
               "elephant: Has a trunk; giraffe: Has a very long neck; snake: Long, with no legs; "
               "bear: Big, furry, and likes honey; fish: Swims and has fins; bee: Makes honey",
    "food": "apple: A red or green fruit; banana: A long yellow fruit; bread: Toast is made from it; "
            "cheese: Mice love it; egg: Hens lay it; milk: A white drink from cows; pizza: Round, with toppings; "
            "carrot: An orange vegetable; soup: Eaten hot from a bowl; cake: Has candles on a birthday; "
            "honey: Bees make it; rice: Small white grains; pear: A fruit shaped like a bell; "
            "lemon: A sour yellow fruit; grape: Small, and grows in bunches; peas: Small green balls; "
            "jam: Spread on toast; pasta: Spaghetti is one",
    "space": "sun: Our nearest star; moon: Shines at night; star: Twinkles in the sky; earth: The planet we live on; "
             "mars: The red planet; rocket: Flies into space; comet: Has a long tail; alien: A visitor from space; "
             "orbit: The path round a planet; saturn: The planet with rings; planet: Earth is one; "
             "astronaut: A space traveller; telescope: For looking at stars; galaxy: Billions of stars",
    "ocean": "wave: Rolls onto the beach; shell: You can find it on the beach; crab: Walks sideways and has claws; "
             "whale: The biggest animal in the sea; shark: A fish with sharp teeth; coral: Colourful reefs are "
             "made of it; octopus: Has eight arms; dolphin: A clever sea animal that jumps; seal: Claps its "
             "flippers; tide: The sea comes in and goes out with it; sand: You build castles with it; squid: "
             "Squirts ink; starfish: Shaped like a star; jellyfish: Wobbly, and can sting; lobster: Like a big "
             "crab with a long tail; anchor: Stops a boat drifting away; boat: Floats on water; pearl: A shiny "
             "ball inside an oyster; salt: Makes sea water taste funny",
    "weather": "rain: Water falling from clouds; snow: White and cold, good for snowmen; wind: Blows kites up high; "
               "cloud: White and fluffy in the sky; storm: Bad weather with thunder; sunny: When the sun is out; "
               "thunder: A loud bang in a storm; fog: Makes it hard to see far; hail: Little balls of ice falling "
               "down; frost: Makes the grass white on cold mornings; rainbow: Seven colours in the sky; breeze: A "
               "gentle wind; heat: You feel it on a hot summer day; tornado: A wind that spins very fast; drizzle: "
               "Very light rain; umbrella: Keeps you dry in the rain; puddle: Jump in it after rain; lightning: A "
               "bright flash in a storm",
    "sports": "soccer: Kick the ball into the goal; tennis: Hit a ball over a net with a racket; golf: Hit a small "
              "ball into a hole; hockey: Played with a stick; rugby: Played with an oval ball; skating: Gliding on "
              "ice; skiing: Sliding down snowy hills; rowing: Moving a boat with oars; boxing: Fighting with big "
              "gloves; surfing: Riding waves on a board; archery: Shooting arrows at a target; baseball: Hit the "
              "ball with a bat and run the bases; cricket: Played with a bat, a ball and wickets; diving: Jumping "
              "into a pool head first; running: Moving fast on your feet; swimming: Moving through water; goal: "
              "Score one to win; ball: Round, and you kick or throw it; team: Players who play together; medal: A "
              "prize for winning",
}
THEMES_ES = {
    "animals": "gato: Dice miau; perro: Ladra y mueve la cola; vaca: Nos da leche; caballo: Puedes montar en él; "
               "oveja: Su lana sirve para jerséis; pato: Dice cua cua; rana: Verde, y salta; buho: Ulula de noche; "
               "leon: El rey de la selva; tigre: Un gran felino con rayas; cebra: Un caballo con rayas; "
               "mono: Se columpia en los árboles; conejo: Tiene orejas largas y salta; raton: Pequeño, y le gusta el queso; "
               "elefante: Tiene trompa; jirafa: Tiene el cuello muy largo; serpiente: Larga y sin patas; "
               "oso: Grande, peludo y le gusta la miel; pez: Nada y tiene aletas; abeja: Hace miel",
    "food": "manzana: Una fruta roja o verde; platano: Una fruta larga y amarilla; pan: Con él se hacen tostadas; "
            "queso: A los ratones les encanta; huevo: Lo ponen las gallinas; leche: Una bebida blanca de la vaca; "
            "pizza: Redonda y con ingredientes encima; zanahoria: Una verdura naranja; sopa: Se toma caliente en un plato hondo; "
            "tarta: Lleva velas en un cumpleaños; miel: La hacen las abejas; arroz: Granos pequeños y blancos; "
            "pera: Una fruta con forma de campana; limon: Una fruta amarilla y ácida; uva: Pequeña, crece en racimos; "
            "guisantes: Bolitas verdes; mermelada: Se unta en las tostadas; pasta: Los espaguetis lo son",
    "space": "sol: Nuestra estrella más cercana; luna: Brilla de noche; estrella: Centellea en el cielo; "
             "tierra: El planeta donde vivimos; marte: El planeta rojo; cohete: Vuela al espacio; "
             "cometa: Tiene una larga cola; orbita: El camino alrededor de un planeta; saturno: El planeta con anillos; "
             "planeta: La Tierra es uno; astronauta: Viaja al espacio; telescopio: Para mirar las estrellas; "
             "galaxia: Miles de millones de estrellas; nave: Lleva astronautas",
    "ocean": "ola: Llega a la playa una y otra vez; concha: La encuentras en la playa; cangrejo: Camina de lado y "
             "tiene pinzas; ballena: El animal más grande del mar; tiburon: Un pez con dientes afilados; coral: "
             "Los arrecifes están hechos de él; pulpo: Tiene ocho brazos; delfin: Un animal del mar muy listo que "
             "salta; foca: Aplaude con sus aletas; marea: El mar sube y baja con ella; arena: Con ella haces "
             "castillos; calamar: Echa tinta; estrella: La de mar tiene cinco brazos; medusa: Es blanda y puede "
             "picar; langosta: Tiene pinzas y una cola larga; ancla: Sujeta el barco para que no se vaya; barco: "
             "Flota en el agua; perla: Una bolita brillante dentro de una ostra; sal: Hace que el agua del mar "
             "sepa salada",
    "weather": "lluvia: Agua que cae de las nubes; nieve: Blanca y fría, sirve para hacer muñecos; viento: Hace "
               "volar las cometas; nube: Blanca y esponjosa en el cielo; tormenta: Tiene truenos y rayos; sol: "
               "Brilla y nos da calor; trueno: Un ruido fuerte en una tormenta; niebla: No te deja ver lejos; "
               "granizo: Bolitas de hielo que caen del cielo; escarcha: Hielo blanco sobre la hierba por la mañana; "
               "arcoiris: Siete colores en el cielo; brisa: Un viento suave; rocio: Gotitas en la hierba al "
               "amanecer; calor: Lo sientes en verano; frio: Lo sientes en invierno; llovizna: Lluvia muy fina; "
               "tornado: Un viento que gira muy rápido; paraguas: Te protege de la lluvia; charco: Saltas en él "
               "después de llover; rayo: Una luz fuerte en una tormenta",
    "sports": "futbol: Metes el balón en la portería con el pie; tenis: Se juega con raqueta y red; golf: Metes una "
              "pelotita en un hoyo; hockey: Se juega con un palo; rugby: Se juega con un balón ovalado; ciclismo: "
              "Carreras en bici; patinaje: Deslizarse sobre el hielo; esqui: Bajar por la nieve; remo: Con él "
              "mueves una barca; boxeo: Pelear con guantes grandes; karate: Un arte marcial de Japón; surf: Montar "
              "las olas en una tabla; beisbol: Bateas la pelota y corres las bases; buceo: Nadar bajo el agua; "
              "judo: Un arte marcial con cinturones de colores; carrera: Gana quien llega primero; natacion: Nadar "
              "en la piscina; gol: Lo celebras en el fútbol; balon: Lo pateas o lo lanzas; equipo: Jugadores que "
              "juegan juntos",
}
THEMES_FR = {
    "animals": "chat: Il fait miaou; chien: Il aboie et remue la queue; vache: Elle nous donne du lait; cheval: On "
               "peut monter dessus; mouton: Sa laine sert à faire des pulls; canard: Il fait coin-coin; grenouille: "
               "Elle est verte et elle saute; hibou: Il hulule la nuit; lion: Le roi de la savane; tigre: Un grand "
               "félin avec des rayures; zèbre: Un cheval avec des rayures; singe: Il se balance dans les arbres; "
               "lapin: Il a de longues oreilles et il saute; souris: Petite, elle aime le fromage; éléphant: Il a "
               "une trompe; girafe: Elle a un très long cou; serpent: Long et sans pattes; ours: Gros, poilu et il "
               "aime le miel; poisson: Il nage et a des nageoires; abeille: Elle fait du miel",
    "food": "pomme: Un fruit rouge ou vert; banane: Un fruit long et jaune; pain: On en fait des tartines; "
            "fromage: Les souris l'adorent; oeuf: Les poules le pondent; lait: Une boisson blanche de la vache; "
            "pizza: Ronde avec des garnitures dessus; carotte: Un légume orange; soupe: On la mange chaude dans "
            "une assiette creuse; gâteau: Il a des bougies pour un anniversaire; miel: Les abeilles le "
            "fabriquent; riz: De petits grains blancs; poire: Un fruit en forme de cloche; citron: Un fruit jaune "
            "et acide; raisin: Petits fruits en grappes; haricot: Un légume vert, long et fin; confiture: On "
            "l'étale sur les tartines; pâtes: Les spaghettis en sont",
    "space": "soleil: Notre étoile la plus proche; lune: Elle brille la nuit; étoile: Elle scintille dans le ciel; "
             "terre: La planète où nous vivons; mars: La planète rouge; fusée: Elle vole dans l'espace; comète: "
             "Elle a une longue queue; orbite: Le chemin autour d'une planète; saturne: La planète avec des "
             "anneaux; planète: La Terre en est une; astronaute: Il voyage dans l'espace; télescope: Pour regarder "
             "les étoiles; galaxie: Des milliards d'étoiles; navette: Elle transporte les astronautes; ciel: Il "
             "est bleu le jour",
    "ocean": "vague: Elle roule jusqu'à la plage; coquillage: On le ramasse sur la plage; crabe: Il marche de côté "
             "avec ses pinces; baleine: Le plus gros animal de la mer; requin: Un poisson aux dents pointues; "
             "corail: Les récifs en sont faits; pieuvre: Elle a huit bras; dauphin: Il saute et il est très malin; "
             "phoque: Il applaudit avec ses nageoires; marée: La mer monte et descend avec elle; sable: On en fait "
             "des châteaux; calmar: Il crache de l'encre; étoile: Celle de mer a cinq bras; méduse: Elle est molle "
             "et elle peut piquer; homard: Il a de grosses pinces et une longue queue; ancre: Elle retient le "
             "bateau; bateau: Il flotte sur l'eau; perle: Une petite boule brillante dans une huître; sel: Il rend "
             "l'eau de mer salée",
    "weather": "pluie: L'eau qui tombe des nuages; neige: Blanche et froide, pour faire un bonhomme; vent: Il fait "
               "voler les cerfs-volants; nuage: Blanc et doux dans le ciel; orage: Il y a du tonnerre et des "
               "éclairs; soleil: Il brille et nous réchauffe; tonnerre: Un grand bruit pendant l'orage; brouillard: "
               "Avec lui, on ne voit pas loin; grêle: De petites boules de glace qui tombent; givre: Il rend l'herbe "
               "blanche les matins froids; flocon: Un petit morceau de neige; brise: Un vent doux; rosée: Des "
               "gouttes sur l'herbe le matin; chaleur: On la sent en été; froid: On le sent en hiver; bruine: Une "
               "pluie très fine; tornade: Un vent qui tourne très vite; éclair: Une lumière vive pendant l'orage; "
               "parapluie: Il te protège de la pluie; flaque: On saute dedans après la pluie",
    "sports": "football: On tape dans le ballon avec le pied; tennis: Avec une raquette et un filet; golf: On met "
              "une petite balle dans un trou; hockey: On y joue avec une crosse; rugby: On y joue avec un ballon "
              "ovale; vélo: Il a deux roues et des pédales; patinage: Glisser sur la glace; ski: Pour glisser sur "
              "la neige; aviron: Ramer dans un bateau; boxe: On se bat avec de gros gants; karaté: Un art martial "
              "du Japon; surf: Glisser sur les vagues avec une planche; judo: Un art martial avec des ceintures de "
              "couleur; natation: Nager dans la piscine; course: Le plus rapide gagne; basket: On lance le ballon "
              "dans un panier; escrime: On se bat avec une épée; voile: Le vent pousse le bateau grâce à elle; "
              "plongée: Nager sous l'eau; but: On en marque au football",
}
THEMES_BY_LANGUAGE = {"es": THEMES_ES, "fr": THEMES_FR}
THEME_NAMES = {"animals": "Animals", "food": "Food", "space": "Space", "ocean": "Ocean", "weather": "Weather",
               "sports": "Sports", "custom": "Your own words and clues"}
MAX_WORD = 15
MAX_OWN = 30    # your own words used, at most


def letters(word):
    """A word as crossword letters: capitals A-Z, accents taken off (café → CAFE), anything else left out. In
    Spanish, Ñ stays (NIÑO)."""
    return i18n.grid_letters(word)


def count_for(c):
    return 4 + c


def parse_entries(text):
    """[(WORD, clue)] from "word: clue" lines (or ";"-separated), words in capitals, letters only, 2-15 long."""
    out, seen = [], set()
    for part in re.split(r"[;\n]+", text or ""):
        if not part.strip():
            continue
        word, _, clue = part.partition(":")
        word = letters(word)
        if 2 <= len(word) <= MAX_WORD and word not in seen:
            seen.add(word)
            out.append((word, clue.strip() or "?"))
    return out


def entries_for(rnd, settings):
    """(the words to choose from, whether they're your own): your own list (every word is wanted), else the
    theme's words in a seeded order."""
    theme = getattr(settings, "cross_theme", "animals")
    if theme == "custom":
        mine = parse_entries(getattr(settings, "cross_words", ""))
        if mine:
            return mine[:MAX_OWN], True
        theme = "animals"   # none of them usable: the note says so
    themes = THEMES_BY_LANGUAGE.get(i18n.LANG, THEMES)
    pool = parse_entries(themes.get(theme, themes["animals"]))
    for i in range(len(pool) - 1, 0, -1):
        j = pick(rnd, i + 1)
        pool[i], pool[j] = pool[j], pool[i]
    return pool, False


def _fits(grid, word, r, c, dr, dc):
    """How many letters word shares with the grid if placed at (r, c) going (dr, dc); None if it can't go there."""
    if grid.get((r - dr, c - dc)) or grid.get((r + dr * len(word), c + dc * len(word))):
        return None   # it would run on into another word
    crossings = 0
    for k, ch in enumerate(word):
        y, x = r + dr * k, c + dc * k
        here = grid.get((y, x))
        if here:
            if here[0] != ch or here[1] & (1 if dr == 0 else 2):
                return None   # a different letter, or a word going the same way
            crossings += 1
        elif grid.get((y + dc, x + dr)) or grid.get((y - dc, x - dr)):
            return None       # it would touch a word side by side
    return crossings


def layout(rnd, entries, want):
    """Place up to want words, in the order given (the first across the middle): {(row, col): (letter, dirs)}
    (dirs: 1 across, 2 down), [(word, clue, row, col, across)], and the words that found no place."""
    grid, placed, left = {}, [], []

    def put(word, clue, r, c, across):
        for k, ch in enumerate(word):
            key = (r, c + k) if across else (r + k, c)
            grid[key] = (ch, grid.get(key, ("", 0))[1] | (1 if across else 2))
        placed.append((word, clue, r, c, across))
    for word, clue in entries:
        if len(placed) >= want:
            break
        if not placed:
            put(word, clue, 0, 0, True)
            continue
        best, choices = 0, []
        for (y, x), (ch, _d) in list(grid.items()):
            for k, wc in enumerate(word):
                if wc != ch:
                    continue
                for across in (True, False):
                    r, c = (y, x - k) if across else (y - k, x)
                    n = _fits(grid, word, r, c, 0 if across else 1, 1 if across else 0)
                    if n and n >= best:
                        if n > best:
                            best, choices = n, []
                        choices.append((r, c, across))
        if choices:
            choices = sorted(set(choices))
            r, c, across = choices[pick(rnd, len(choices))]
            put(word, clue, r, c, across)
        else:
            left.append((word, clue))
    # a word that found no place may cross one placed after it: try those again until nothing more fits
    while left and len(placed) < want:
        before = len(placed)
        retry, left = left, []
        grid, placed, still = _place_more(rnd, grid, placed, retry, want, put)
        left = still
        if len(placed) == before:
            break
    return grid, placed, [w for w, _c in left]


def _place_more(rnd, grid, placed, entries, want, put):
    still = []
    for word, clue in entries:
        if len(placed) >= want:
            still.append((word, clue))
            continue
        best, choices = 0, []
        for (y, x), (ch, _d) in list(grid.items()):
            for k, wc in enumerate(word):
                if wc != ch:
                    continue
                for across in (True, False):
                    r, c = (y, x - k) if across else (y - k, x)
                    n = _fits(grid, word, r, c, 0 if across else 1, 1 if across else 0)
                    if n and n >= best:
                        if n > best:
                            best, choices = n, []
                        choices.append((r, c, across))
        if choices:
            choices = sorted(set(choices))
            r, c, across = choices[pick(rnd, len(choices))]
            put(word, clue, r, c, across)
        else:
            still.append((word, clue))
    return grid, placed, still


def _area(grid):
    rows = [r for r, _c in grid]
    cols = [c for _r, c in grid]
    return (max(rows) - min(rows) + 1) * (max(cols) - min(cols) + 1) if grid else 0


TRIES = 12


def best_layout(rnd, entries, want, own):
    """The best of several tries (each with the words in another order, longest first): the most words placed,
    then the smallest grid. With a theme, words that find no place give way to others from the theme."""
    best = None
    for t in range(TRIES):
        order = list(entries)
        for i in range(len(order) - 1, 0, -1):
            j = pick(rnd, i + 1)
            order[i], order[j] = order[j], order[i]
        if own and t == 0:   # all of your words: longest first, then other orders
            order.sort(key=lambda e: -len(e[0]))
        else:     # the theme's words: the first ones wanted, longest first, the rest standing by
            order = sorted(order[:want], key=lambda e: -len(e[0])) + order[want:]
        grid, placed, left = layout(rnd, order, want)
        score = (len(placed), -_area(grid))
        if best is None or score > best[0]:
            best = (score, grid, placed, left if own else [])
    return best[1], best[2], best[3]


def number(placed):
    """Crossword numbers: each square where a word starts, numbered in reading order. [(number, word, clue,
    row, col, across)] sorted by number."""
    starts = sorted({(r, c) for _w, _cl, r, c, _a in placed})
    nums = {rc: i + 1 for i, rc in enumerate(starts)}
    return sorted(((nums[(r, c)], w, cl, r, c, a) for w, cl, r, c, a in placed), key=lambda e: (not e[5], e[0]))


def make_crossword(rnd, c, settings):
    entries, own = entries_for(rnd, settings)
    grid, placed, left = best_layout(rnd, entries, len(entries) if own else count_for(c), own)
    return grid, number(placed), left


def own_note(settings):
    """What the sidebar says about your own list itself: too many words, or none usable."""
    if getattr(settings, "cross_theme", "") != "custom":
        return ""
    mine = parse_entries(getattr(settings, "cross_words", ""))
    if not mine:
        return tr("None of your words can be used (they need letters A-Z), so animal words are shown.")
    if len(mine) > MAX_OWN:
        return tr("Only the first {n} of your words are used.").format(n=MAX_OWN)
    return ""


def note(cw):
    """What the sidebar says about words left out, and about your own list."""
    if not isinstance(cw, dict):
        return ""
    left = cw.get("left")
    parts = [cw.get("own", "")] + ([tr("Left out (no place to cross): {words}.").format(
        words=", ".join(w.lower() for w in left))] if left else [])
    return " ".join(p for p in parts if p)


def _wrap(ctx, text, width):
    """text broken into lines no wider than width (a word longer than that keeps a line to itself)."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and ctx.measure_text(trial) > width:
            lines.append(line)
            line = "  " + word   # continued lines indented a little
        else:
            line = trial if not line.startswith("  ") else f"{line} {word}"
    return lines + ([line] if line else [])


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    """The numbered grid with its clues (or, with solve=True, the grid filled in)."""
    grid, clues, left = make_crossword(rnd, c, settings)
    if not grid:
        return {"left": left, "clues": [], "own": own_note(settings)}
    rows = [r for r, _c in grid]
    cols = [c for _r, c in grid]
    r0, c0 = min(rows), min(cols)
    nr, nc = max(rows) - r0 + 1, max(cols) - c0 + 1
    area_h = box.h if solve else box.h * 0.6
    cs = min(box.w / nc, area_h / nr, dpi * 0.5)
    x0, y0 = box.x + (box.w - cs * nc) / 2, box.y + (area_h - cs * nr) / 2
    ctx.save()
    ctx.line_width, ctx.stroke_style = max(1.0, lw * 0.6), "#000"
    for (r, c), (ch, _d) in grid.items():
        x, y = x0 + (c - c0) * cs, y0 + (r - r0) * cs
        ctx.stroke_rect(x, y, cs, cs)
        if solve:   # the letter low and to the right, clear of the square's number
            ctx.set_font(cs * 0.55, 600)
            ctx.fill_style, ctx.text_align = "#000", "center"
            ctx.fill_text(ch, x + cs * 0.56, y + cs * 0.82)
    ctx.set_font(cs * 0.28, 400)
    ctx.fill_style, ctx.text_align = "#000", "left"
    done = set()
    for n, _w, _cl, r, c, _a in clues:
        if (r, c) not in done:
            done.add((r, c))
            ctx.fill_text(str(n), x0 + (c - c0) * cs + cs * 0.08, y0 + (r - r0) * cs + cs * 0.3)
    if not solve:   # the clues, Across then Down, in two columns under the grid, wrapped to fit
        top = box.y + area_h + dpi * 0.15
        col_w = box.w / 2 - dpi * 0.15
        room = box.y + box.h - top
        fs = dpi * 0.15
        while True:   # the largest size (down to a floor) at which both columns fit
            ctx.set_font(fs, 400)
            lines = {a: [ln for e in clues if e[5] == a for ln in _wrap(ctx, f"{e[0]}. {e[2]} ({len(e[1])})", col_w)]
                     for a in (True, False)}
            need = (max(len(lines[True]), len(lines[False])) + 1.5) * fs * 1.35
            if need <= room or fs <= dpi * 0.09:
                break
            fs *= 0.92
        for k, (title, across) in enumerate(((tr("Across"), True), (tr("Down"), False))):
            x, y = box.x + k * box.w / 2, top + fs
            ctx.set_font(fs * 1.1, 700)
            ctx.fill_text(title, x, y)
            ctx.set_font(fs, 400)
            for line in lines[across]:
                y += fs * 1.35
                ctx.fill_text(line, x, y)
    ctx.restore()
    return {"left": left, "clues": clues, "own": own_note(settings)}
