"""Simple pictures drawn from straight lines between whole-number points, shared by the coordinate grid's "plot the
points" pictures and the memory cards.

Each picture lives on a 0-10 grid, y up (as on a coordinate grid): strokes are lists of (x, y) points joined in order
(a closed shape repeats its first point), and extras are circles (x, y, r) that make a picture easier to recognise
on a card (an eye, wheels) but aren't plotted. Every picture reads clearly from its strokes alone.

SIMPLE pictures have few points, for the youngest plotting; the others have more. WORDS names each picture in each
language, for the memory cards' word and picture pairs.
"""

PICTURES = {
    "house": {"strokes": [[(2, 1), (2, 6), (5, 9), (8, 6), (8, 1), (2, 1)], [(2, 6), (8, 6)],
                          [(4, 1), (4, 4), (6, 4), (6, 1)]]},
    "star": {"strokes": [[(5, 10), (6, 7), (9, 7), (7, 5), (8, 1), (5, 3), (2, 1), (3, 5), (1, 7), (4, 7), (5, 10)]]},
    "heart": {"strokes": [[(5, 2), (1, 6), (1, 8), (2, 9), (4, 9), (5, 8), (6, 9), (8, 9), (9, 8), (9, 6), (5, 2)]]},
    "fish": {"strokes": [[(1, 5), (3, 7), (6, 7), (8, 5), (10, 7), (10, 3), (8, 5), (6, 3), (3, 3), (1, 5)],
                         [(5, 7), (5, 3)]],
             "extras": [(3, 5.4, 0.45)]},
    "boat": {"strokes": [[(1, 4), (9, 4), (7, 2), (3, 2), (1, 4)], [(5, 4), (5, 10)], [(5, 10), (8, 5), (5, 5)]]},
    "rocket": {"strokes": [[(5, 10), (7, 8), (7, 3), (3, 3), (3, 8), (5, 10)], [(3, 5), (1, 2), (3, 3)],
                           [(7, 5), (9, 2), (7, 3)], [(4, 3), (5, 1), (6, 3)]],
               "extras": [(5, 6.5, 0.8)]},
    "tree": {"strokes": [[(5, 10), (8, 6), (6, 6), (9, 3), (6, 3), (6, 1), (4, 1), (4, 3), (1, 3), (4, 6), (2, 6),
                          (5, 10)]]},
    "cat": {"strokes": [[(2, 2), (2, 7), (1, 10), (4, 8), (6, 8), (9, 10), (8, 7), (8, 2), (2, 2)],
                        [(4, 4), (5, 3), (6, 4), (4, 4)]],
            "extras": [(3.7, 5.7, 0.45), (6.3, 5.7, 0.45)]},
    "crown": {"strokes": [[(1, 2), (1, 8), (3, 5), (5, 9), (7, 5), (9, 8), (9, 2), (1, 2)]]},
    "kite": {"strokes": [[(5, 10), (8, 6), (5, 2), (2, 6), (5, 10)], [(5, 10), (5, 2)], [(2, 6), (8, 6)],
                         [(5, 2), (4, 1), (6, 0)]]},
    "cup": {"strokes": [[(2, 8), (3, 1), (7, 1), (8, 8), (2, 8)], [(8, 7), (10, 7), (10, 4), (7, 3)]]},
    "car": {"strokes": [[(1, 2), (1, 5), (3, 5), (4, 7), (7, 7), (8, 5), (10, 5), (10, 2), (1, 2)], [(5, 5), (5, 7)]],
            "extras": [(3, 2, 1), (8, 2, 1)]},
    "umbrella": {"strokes": [[(1, 6), (2, 8), (5, 9), (8, 8), (9, 6), (7, 7), (5, 6), (3, 7), (1, 6)],
                             [(5, 6), (5, 2), (4, 1), (3, 2)]]},
    "apple": {"strokes": [[(5, 8), (3, 9), (1, 7), (1, 4), (3, 1), (5, 2), (7, 1), (9, 4), (9, 7), (7, 9), (5, 8)],
                          [(5, 8), (6, 10)]]},
    "gem": {"strokes": [[(3, 9), (7, 9), (9, 7), (5, 1), (1, 7), (3, 9)], [(1, 7), (9, 7)]]},
    "butterfly": {"strokes": [[(5, 7), (2, 10), (1, 8), (2, 5), (1, 2), (3, 1), (5, 4), (7, 1), (9, 2), (8, 5), (9, 8),
                               (8, 10), (5, 7)], [(5, 8), (5, 3)]]},
}
SIMPLE = ("house", "star", "heart", "crown", "kite", "cup", "gem")

WORDS = {
    "en": {"house": "house", "star": "star", "heart": "heart", "fish": "fish", "boat": "boat", "rocket": "rocket",
           "tree": "tree", "cat": "cat", "crown": "crown", "kite": "kite", "cup": "cup", "car": "car",
           "umbrella": "umbrella", "apple": "apple", "gem": "jewel", "butterfly": "butterfly"},
    "es": {"house": "casa", "star": "estrella", "heart": "corazón", "fish": "pez", "boat": "barco", "rocket": "cohete",
           "tree": "árbol", "cat": "gato", "crown": "corona", "kite": "cometa", "cup": "taza", "car": "coche",
           "umbrella": "paraguas", "apple": "manzana", "gem": "joya", "butterfly": "mariposa"},
    "fr": {"house": "maison", "star": "étoile", "heart": "cœur", "fish": "poisson", "boat": "bateau", "rocket": "fusée",
           "tree": "sapin", "cat": "chat", "crown": "couronne", "kite": "cerf-volant", "cup": "tasse", "car": "voiture",
           "umbrella": "parapluie", "apple": "pomme", "gem": "bijou", "butterfly": "papillon"},
    "pt": {"house": "casa", "star": "estrela", "heart": "coração", "fish": "peixe", "boat": "barco", "rocket": "foguete",
           "tree": "árvore", "cat": "gato", "crown": "coroa", "kite": "pipa", "cup": "xícara", "car": "carro",
           "umbrella": "guarda-chuva", "apple": "maçã", "gem": "joia", "butterfly": "borboleta"},
    "de": {"house": "Haus", "star": "Stern", "heart": "Herz", "fish": "Fisch", "boat": "Boot", "rocket": "Rakete",
           "tree": "Baum", "cat": "Katze", "crown": "Krone", "kite": "Drachen", "cup": "Tasse", "car": "Auto",
           "umbrella": "Schirm", "apple": "Apfel", "gem": "Edelstein", "butterfly": "Schmetterling"},
    "it": {"house": "casa", "star": "stella", "heart": "cuore", "fish": "pesce", "boat": "barca", "rocket": "razzo",
           "tree": "albero", "cat": "gatto", "crown": "corona", "kite": "aquilone", "cup": "tazza", "car": "auto",
           "umbrella": "ombrello", "apple": "mela", "gem": "gioiello", "butterfly": "farfalla"},
    "nl": {"house": "huis", "star": "ster", "heart": "hart", "fish": "vis", "boat": "boot", "rocket": "raket",
           "tree": "boom", "cat": "kat", "crown": "kroon", "kite": "vlieger", "cup": "kopje", "car": "auto",
           "umbrella": "paraplu", "apple": "appel", "gem": "edelsteen", "butterfly": "vlinder"},
}


def word(name, lang="en"):
    """A picture's name in a language (English's when the language has none)."""
    return WORDS.get(lang, WORDS["en"]).get(name, WORDS["en"][name])


def draw(ctx, name, x, y, size, lw, extras=True):
    """Picture name drawn in the square (x, y, size): the 0-10 grid fills it, y up."""
    pic = PICTURES[name]
    k = size / 10

    def at(px, py):
        return x + px * k, y + (10 - py) * k
    ctx.save()
    ctx.line_width = lw
    ctx.line_join = ctx.line_cap = "round"
    for stroke in pic["strokes"]:
        ctx.begin_path()
        ctx.move_to(*at(*stroke[0]))
        for p in stroke[1:]:
            ctx.line_to(*at(*p))
        ctx.stroke()
    if extras:
        for cx, cy, r in pic.get("extras", ()):
            ctx.begin_path()
            ctx.arc(*at(cx, cy), r * k, 0, 6.283185307179586)
            ctx.stroke()
    ctx.restore()
