"""Cryptogram: a saying written in code, each letter swapped for a number (or a symbol), to crack with a few letters
given in the key.

The saying is an old proverb or one of Inkline's own, in the current language (picked by the seed: short ones at
complexity 1-3, longer ones at 4-7, the longest at 8-10), or your own text. The seed gives every letter of the
alphabet its own code, 1-26 (27 with Spanish Ñ) or one of 27 shapes. Complexity sets how many letters the key
gives away: seven at 1, down to one at 10, the saying's commonest letters first for the youngest.

Letters lose their accents, as in the word puzzles (É is written E, Ä is A, ß is SS); Spanish keeps Ñ as a letter of
its own. Anything else (spaces, commas, apostrophes, numbers) is printed as it is.

Each letter of the saying is a box with its code under it. The key lists every code in the saying with a box for
its letter; the letters given are filled in there and in the saying. The answer page fills in every box.
"""

import math
import re
import unicodedata

from .. import i18n
from ..i18n import tr
from ..rng import pick

KINDS = {"numbers": "Numbers", "symbols": "Symbols"}
SOURCES = {"sayings": "Sayings", "custom": "Your own text"}
INSTRUCTIONS = {"numbers": "Each number stands for a letter. Use the key to crack the code.",
                "symbols": "Each symbol stands for a letter. Use the key to crack the code."}
MAX_TEXT = 120

SAYINGS = {
    "en": ["Be kind.", "Dream big.", "Never give up.", "Practice makes perfect.", "Slow and steady wins the race.",
           "Every day is a fresh start.", "A smile is a gift you can give every day.", "Books are doors to new worlds.",
           "Many hands make light work.", "Look before you leap.", "Where there is a will, there is a way.",
           "Great oaks from little acorns grow.", "The early bird catches the worm.",
           "Do not count your chickens before they hatch.", "You never know what you can do until you try.",
           "A friend in need is a friend indeed.", "Kindness is a language everyone understands."],
    "es": ["Sé amable.", "Sueña en grande.", "Nunca te rindas.", "Querer es poder.", "Poco a poco se va lejos.",
           "Cada día es un nuevo comienzo.", "Más vale tarde que nunca.", "Una sonrisa es un regalo para todos.",
           "Los libros son puertas a otros mundos.", "En la unión está la fuerza.", "No hay mal que por bien no venga.",
           "Quien busca encuentra.", "A quien madruga, Dios le ayuda.", "El que la sigue la consigue.",
           "Dime con quién andas y te diré quién eres.", "La amabilidad es un idioma que todos entienden."],
    "fr": ["Sois gentil.", "Rêve en grand.", "N'abandonne jamais.", "Vouloir, c'est pouvoir.",
           "Petit à petit, l'oiseau fait son nid.", "Chaque jour est un nouveau départ.", "Mieux vaut tard que jamais.",
           "Un sourire est un cadeau pour tout le monde.", "Les livres ouvrent des portes sur le monde.",
           "L'union fait la force.", "Rien ne sert de courir, il faut partir à point.", "Qui cherche trouve.",
           "Après la pluie, le beau temps.", "C'est en forgeant qu'on devient forgeron.",
           "La gentillesse est une langue que tout le monde comprend."],
    "pt": ["Seja gentil.", "Sonhe alto.", "Nunca desista.", "Querer é poder.", "Devagar se vai ao longe.",
           "Cada dia é um novo começo.", "Antes tarde do que nunca.", "Um sorriso é um presente para todos.",
           "Os livros são portas para outros mundos.", "A união faz a força.", "Quem procura acha.",
           "Água mole em pedra dura tanto bate até que fura.", "De grão em grão a galinha enche o papo.",
           "Depois da tempestade vem a bonança.", "A gentileza é uma língua que todos entendem."],
    "de": ["Sei freundlich.", "Träume groß.", "Gib niemals auf.", "Übung macht den Meister.",
           "Langsam kommt man auch ans Ziel.", "Jeder Tag ist ein neuer Anfang.", "Besser spät als nie.",
           "Ein Lächeln ist ein Geschenk für alle.", "Bücher sind Türen zu neuen Welten.",
           "Gemeinsam sind wir stark.", "Wer suchet, der findet.", "Morgenstund hat Gold im Mund.",
           "Auf Regen folgt Sonnenschein.", "Aller Anfang ist schwer.", "Wo ein Wille ist, ist auch ein Weg.",
           "Freundlichkeit ist eine Sprache, die jeder versteht."],
    "it": ["Sii gentile.", "Sogna in grande.", "Non arrenderti mai.", "Volere è potere.", "Chi va piano va sano e va lontano.",
           "Ogni giorno è un nuovo inizio.", "Meglio tardi che mai.", "Un sorriso è un regalo per tutti.",
           "I libri sono porte su nuovi mondi.", "L'unione fa la forza.", "Chi cerca trova.",
           "Dopo la pioggia viene il sereno.", "Il mattino ha l'oro in bocca.", "Sbagliando si impara.",
           "La gentilezza è una lingua che tutti capiscono."],
    "nl": ["Wees aardig.", "Droom groot.", "Geef nooit op.", "Oefening baart kunst.", "Al doende leert men.",
           "Elke dag is een nieuw begin.", "Beter laat dan nooit.", "Een glimlach is een cadeau voor iedereen.",
           "Boeken zijn deuren naar nieuwe werelden.", "Eendracht maakt macht.", "Wie zoekt, die vindt.",
           "Na regen komt zonneschijn.", "De aanhouder wint.", "Oost west, thuis best.",
           "Vriendelijkheid is een taal die iedereen begrijpt."],
}


def _alphabet():
    return i18n.alphabet()


def letters_of(ch):
    """A character as code letters in the current language ("É" -> "E", "ß" -> "SS", Spanish "ñ" -> "Ñ"), or "" for
    anything that isn't a letter."""
    keep = i18n.KEEP_LETTERS.get(i18n.LANG, "")
    up = unicodedata.normalize("NFC", ch.upper()).replace("Œ", "OE").replace("Æ", "AE").replace("ß", "SS").replace("ẞ", "SS")
    out = "".join(c if c in keep else unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode("ascii") for c in up)
    return re.sub(f"[^A-Z{keep}]", "", out) if ch.isalpha() else ""


def _shuffle(items, rnd):
    for i in range(len(items) - 1, 0, -1):
        j = pick(rnd, i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def own_text(settings):
    text = " ".join((getattr(settings, "crypto_text", "") or "").split())[:MAX_TEXT]
    return text if any(letters_of(ch) for ch in text) else ""


def note(settings):
    """What the sidebar says when your own text has no letters to put in code, or ""."""
    if getattr(settings, "crypto_source", "") == "custom" and not own_text(settings):
        return tr("Type a sentence to put in code.")
    return ""


def choose(rnd, c, settings=None):
    """The text to put in code: your own, or a saying for the complexity."""
    if getattr(settings, "crypto_source", "sayings") == "custom":
        return own_text(settings)
    pool = sorted(SAYINGS.get(i18n.LANG, SAYINGS["en"]), key=lambda t: sum(1 for ch in t if ch.isalpha()))
    third = len(pool) / 3
    lo, hi = (0, third) if c <= 3 else (third, 2 * third) if c <= 7 else (2 * third, len(pool))
    band = pool[int(lo):max(int(lo) + 1, int(math.ceil(hi)))]
    return band[pick(rnd, len(band))]


def tokens(text):
    """The text as [(letter, shown)]: a letter to code (shown is ""), or something printed as it is (letter "")."""
    out = []
    for ch in text:
        ls = letters_of(ch)
        if ls:
            out.extend((x, "") for x in ls)
        else:
            out.append(("", ch))
    return out


def make(rnd, c, settings=None):
    """{"text", "tokens", "code": {letter: code}, "given": set of letters} or None (no text)."""
    text = choose(rnd, c, settings)
    if not text:
        return None
    alpha = _alphabet()
    codes = _shuffle(list(range(len(alpha))), rnd)
    code = {a: codes[i] for i, a in enumerate(alpha)}   # numbers print code + 1; symbols draw shape code
    toks = tokens(text)
    used = [t for t, _s in toks if t]
    counts = {t: used.count(t) for t in set(used)}
    distinct = sorted(counts, key=lambda t: (-counts[t], alpha.index(t)))
    n = max(1, min(len(distinct) // 2, round(8 - 0.75 * c))) if len(distinct) > 1 else 0
    if c <= 3:   # the commonest letters, so the youngest get the most help
        given = set(distinct[:n])
    else:
        given = set(_shuffle(distinct[:], rnd)[:n])
    return {"text": text, "tokens": toks, "code": code, "given": given}


# --- drawing ------------------------------------------------------------------------------------------------------

def symbol(ctx, k, cx, cy, r, lw):
    """Shape k (0-26) centred at (cx, cy), about r across from the middle: nine outlines, each plain, filled or with
    a dot in the middle."""
    shape, style = k % 9, k // 9
    pts = None
    if shape == 0:
        ctx.begin_path()
        ctx.arc(cx, cy, r, 0, math.pi * 2)
    elif shape == 1:
        pts = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        pts = [(x * 0.85, y * 0.85) for x, y in pts]
    elif shape == 2:
        pts = [(0, -1), (1, 0.8), (-1, 0.8)]
    elif shape == 3:
        pts = [(-1, -0.8), (1, -0.8), (0, 1)]
    elif shape == 4:
        pts = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    elif shape == 5:
        pts = [(math.cos(a), math.sin(a)) for a in (math.pi / 3 * i for i in range(6))]
    elif shape == 6:
        pts = [(math.cos(a), math.sin(a)) for a in (-math.pi / 2 + 2 * math.pi / 5 * i for i in range(5))]
    elif shape == 7:   # a star
        pts = [((1 if i % 2 == 0 else 0.45) * math.cos(a), (1 if i % 2 == 0 else 0.45) * math.sin(a))
               for i, a in enumerate(-math.pi / 2 + math.pi / 5 * i for i in range(10))]
    else:              # half a circle, flat side down
        ctx.begin_path()
        ctx.arc(cx, cy + r * 0.4, r, math.pi, math.pi * 2)
        ctx.close_path()
    if pts is not None:
        ctx.begin_path()
        for i, (x, y) in enumerate(pts):
            (ctx.line_to if i else ctx.move_to)(cx + x * r, cy + y * r)
        ctx.close_path()
    if style == 1:
        ctx.fill()
    ctx.stroke()
    if style == 2:
        ctx.begin_path()
        ctx.arc(cx, cy + (r * 0.3 if shape == 2 else -r * 0.2 if shape == 3 else r * 0.1 if shape == 8 else 0),
                r * 0.22, 0, math.pi * 2)
        ctx.fill()


def _words(toks):
    """The tokens split into words at spaces (each word kept whole on a line)."""
    words, cur = [], []
    for t in toks:
        if t == ("", " "):
            if cur:
                words.append(cur)
            cur = []
        else:
            cur.append(t)
    return words + ([cur] if cur else [])


def _lines(words, cell, width):
    lines, line, used = [], [], 0.0
    for w in words:
        need = len(w) * cell + (cell * 0.8 if line else 0)
        if line and used + need > width:
            lines.append(line)
            line, used = [w], len(w) * cell
        else:
            line.append(w)
            used += need
    return lines + ([line] if line else [])


def _draw_code(ctx, kind, code, cx, cy, cell, lw):
    if kind == "symbols":
        ctx.line_width = max(1.0, lw * 0.7)
        symbol(ctx, code, cx, cy, cell * 0.2, lw)
    else:
        ctx.set_font(cell * 0.36, 500)
        ctx.fill_text(str(code + 1), cx, cy)


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    p = make(rnd, c, settings)
    if p is None:   # your own text, with no letters: the sidebar says so
        return None
    kind = getattr(settings, "crypto_code", "numbers")
    if kind not in KINDS:
        kind = "numbers"
    code, given = p["code"], p["given"]
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    fs = min(dpi * 0.2, box.h / 22)
    ctx.set_font(fs * 0.9, 400)
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    ctx.fill_text(tr(INSTRUCTIONS[kind]), box.x, box.y + fs, box.w)
    top = box.y + fs * 2
    # the key: every code in the text, in order, each with a box for its letter (two rows if it's long)
    keys = sorted({code[t] for t, _s in p["tokens"] if t})
    per_row = len(keys) if len(keys) <= 14 else math.ceil(len(keys) / 2)
    kcell = min(box.w / (per_row + 0.5), dpi * 0.45, box.h / 9)
    key_rows = math.ceil(len(keys) / per_row)
    key_h = fs * 1.4 + key_rows * kcell * 1.9
    # the text: the biggest boxes that fit above the key
    words = _words(p["tokens"])
    room = box.y + box.h - top - key_h - fs
    cell = min(dpi * 0.5, box.w / 6, box.w / max(len(w) for w in words))   # the longest word fits on a line
    lines = _lines(words, cell, box.w)
    while len(lines) * cell * 2.1 > room and cell > dpi * 0.12:
        cell *= 0.94
        lines = _lines(words, cell, box.w)
    ctx.text_align, ctx.text_baseline = "center", "middle"
    y = top + (room - len(lines) * cell * 2.1) / 2 if room > len(lines) * cell * 2.1 else top
    for line in lines:
        widths = sum(len(w) for w in line) * cell + cell * 0.8 * (len(line) - 1)
        x = box.x + (box.w - widths) / 2
        for w in line:
            for letter, shown in w:
                bx = x + cell * 0.08
                if letter:
                    ctx.line_width = max(1.0, lw * 0.6)
                    ctx.stroke_style = "#000"
                    ctx.stroke_rect(bx, y, cell * 0.84, cell * 0.84)
                    if solve or letter in given:
                        ctx.set_font(cell * 0.55, 600)
                        ctx.fill_style = "#666" if solve and letter not in given else "#000"
                        ctx.fill_text(letter, x + cell / 2, y + cell * 0.44)
                        ctx.fill_style = "#000"
                    _draw_code(ctx, kind, code[letter], x + cell / 2, y + cell * 1.3, cell, lw)
                else:
                    ctx.set_font(cell * 0.6, 600)
                    ctx.fill_text(shown, x + cell / 2, y + cell * 0.44)
                x += cell
            x += cell * 0.8
        y += cell * 2.1
    # the key
    letter_of = {v: k for k, v in code.items()}
    ky = box.y + box.h - key_h
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    ctx.set_font(fs * 0.85, 700)
    ctx.fill_text(tr("Key"), box.x, ky + fs)
    ctx.text_align, ctx.text_baseline = "center", "middle"
    for k, v in enumerate(keys):
        row, col = divmod(k, per_row)
        x = box.x + (box.w - per_row * kcell) / 2 + col * kcell
        y = ky + fs * 1.4 + row * kcell * 1.9
        ctx.line_width = max(1.0, lw * 0.6)
        ctx.stroke_rect(x + kcell * 0.08, y, kcell * 0.84, kcell * 0.84)
        letter = letter_of[v]
        if solve or letter in given:
            ctx.set_font(kcell * 0.55, 600)
            ctx.fill_style = "#666" if solve and letter not in given else "#000"
            ctx.fill_text(letter, x + kcell / 2, y + kcell * 0.44)
            ctx.fill_style = "#000"
        _draw_code(ctx, kind, v, x + kcell / 2, y + kcell * 1.3, kcell, lw)
    ctx.restore()
    return {"text": p["text"], "given": sorted(given), "cell": cell / dpi, "lines": len(lines)}
