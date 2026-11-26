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
    "autumn": "leaf acorn conker pumpkin harvest apple squirrel hedgehog mushroom rake wind orange brown scarf "
              "boots school pencil satchel berry chestnut hay owl misty puddle",
    "halloween": "pumpkin ghost bat witch broom cat costume mask candy sweets spider web moon owl lantern cauldron "
                 "potion wizard skeleton monster spooky party treat night hat",
    "winter": "snow ice cold scarf mitten hat coat sledge jumper glove frost fire cocoa boots igloo skate penguin "
              "icicle present star candle blanket holly robin december",
    "spring": "flower tulip daffodil lamb chick nest egg bunny rain puddle blossom bee butterfly seed bud garden "
              "grass lily bird duckling umbrella frog sprout april",
    "summer": "sun beach sand bucket spade shell wave swim cone lolly picnic holiday hat goggles kite camping tent "
              "boat island seaside lemonade watermelon flipflops shorts july",
    "sight1": "and big blue can come down find for funny help jump little look make not one play run said see the "
              "two where yellow you all are black brown but did eat four good have like must now out please",
    "sight2": "after again could every fly from give going had has her him how just know live may once open over "
              "put some stop take thank walk always around because been before best both buy call does fast first "
              "found sleep",
    "sight3": "about better bring carry clean cut done draw drink eight fall far full grow hold hot hurt keep kind "
              "laugh light long much myself never only own pick seven shall show six small start ten today together "
              "try warm",
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
    "autumn": "hoja bellota castaña calabaza cosecha manzana ardilla erizo seta rastrillo viento naranja marron "
              "bufanda botas colegio lapiz mochila uva nuez paja buho niebla charco",
    "halloween": "calabaza fantasma murcielago bruja escoba gato disfraz mascara caramelo araña linterna luna buho "
                 "farol caldero pocion mago esqueleto monstruo fiesta noche sombrero vela dulce",
    "winter": "nieve hielo frio bufanda guantes gorro abrigo trineo muñeco copo escarcha fuego chocolate botas iglu "
              "patines pingüino carambano regalo estrella vela manta chimenea diciembre",
    "spring": "flor tulipan margarita cordero pollito nido huevo conejo lluvia charco abeja mariposa semilla jardin "
              "hierba arcoiris pajaro patito paraguas rana brote abril primavera",
    "summer": "sol playa arena cubo pala concha ola nadar helado picnic vacaciones gorra gafas cometa tienda barco "
              "isla castillo limonada sandia chanclas piscina julio toalla",
    "sight1": "las casa mamá papá sol mesa pato oso ama mira come dame sube baja amigo niño niña gato perro agua "
              "luna leche pelota rojo azul hola mano dedo pie",
    "sight2": "que con por para pero más muy está son tiene hay como cuando donde aquí allí hoy ayer bien mal "
              "grande chico bonito nuevo todo mucho poco otro hacer decir ver dar",
    "sight3": "también siempre nunca después antes entonces porque mientras durante contra sobre entre hacia desde "
              "hasta mismo cada cosa tiempo mundo vida año día parte persona lugar momento trabajo escuela juntos",
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
    "autumn": "feuille gland marron citrouille récolte pomme écureuil hérisson champignon râteau vent orange "
              "écharpe bottes école crayon cartable mûre noisette châtaigne hibou brouillard flaque raisin",
    "halloween": "citrouille fantôme chouette sorcière balai chat déguisement masque bonbon araignée toile lune hibou "
                 "lanterne chaudron potion sorcier squelette monstre fête nuit chapeau bougie",
    "winter": "neige glace froid écharpe moufle bonnet manteau luge bonhomme flocon givre feu chocolat bottes igloo "
              "patins pingouin glaçon cadeau étoile bougie couverture sapin décembre",
    "spring": "fleur tulipe jonquille agneau poussin nid oeuf lapin pluie flaque abeille papillon graine bourgeon "
              "potager herbe pâquerette oiseau caneton averse grenouille avril cerisier",
    "summer": "soleil plage sable seau pelle coquillage vague nager glace maillot vacances chapeau lunettes parasol "
              "camping tente bateau île château limonade pastèque tongs piscine juillet serviette",
    "sight1": "les des moi toi lui elle papa maman chat chien maison école ami jouer voir dans sur avec pour qui "
              "non oui petit grand rouge bleu jaune vert bébé lit",
    "sight2": "que pas mais plus très tout bien aussi alors comme être avoir faire dire aller venir prendre donner "
              "veut peut fait sont avait était nous vous ils elles leur cette",
    "sight3": "toujours jamais souvent encore déjà depuis pendant parce quand pourquoi beaucoup peu chaque autre "
              "même quelque chose temps monde matin année enfant famille travail ensemble devant derrière",
}
THEMES_PT = {
    "animals": "gato cachorro cavalo tigre zebra coelho macaco girafa leão urso rato ovelha cabra pato sapo coruja "
               "águia panda coala lontra camelo tartaruga cobra lobo raposa onça jacaré",
    "ocean": "onda concha caranguejo baleia tubarão coral polvo golfinho foca maré areia recife lula alga lagosta "
             "âncora barco pérola sal marisco peixe praia navio ilha",
    "space": "estrela lua planeta cometa foguete órbita galáxia saturno marte vênus terra júpiter asteroide "
             "nebulosa sol meteoro cratera astronauta telescópio satélite céu universo",
    "food": "maçã pão queijo pizza macarrão sopa salada banana uva manga cenoura arroz feijão mel biscoito bolo "
            "pêssego limão torrada manteiga pera ameixa abacaxi milho ovo leite",
    "weather": "chuva neve vento nuvem tempestade sol trovão neblina granizo geada brisa garoa calor frio tornado "
               "relâmpago raio orvalho nublado poça furacão",
    "sports": "futebol tênis golfe hóquei rúgbi ciclismo patinação esqui remo boxe caratê surfe beisebol natação "
              "judô corrida vôlei basquete handebol skate ginástica",
    "autumn": "outono folha vento abóbora maçã colheita galho árvore castanha cogumelo amarelo laranja marrom "
              "rastelo esquilo noz milho espantalho cachecol casaco chuva bota uva pinha",
    "halloween": "bruxa fantasma abóbora morcego vassoura caldeirão aranha teia gato máscara fantasia doce bala "
                 "travessura caveira esqueleto múmia vampiro lua coruja castelo vela poção chapéu lanterna noite",
    "winter": "inverno neve frio gelo floco trenó cachecol luva gorro casaco lareira chocolate sopa pinguim urso "
              "esqui patins geada nevasca bota cobertor iglu pijama",
    "spring": "primavera flor borboleta abelha jardim semente broto ninho passarinho chuva grama folha sol pétala "
              "rosa margarida joaninha minhoca coelho girassol tulipa piquenique lagarta verde",
    "summer": "verão praia sol mar areia sorvete piscina férias chapéu óculos calor toalha balde concha onda "
              "castelo bermuda chinelo picolé melancia coco pipa barco suco",
    "sight1": "uma casa mamãe papai sol bola pato gato cão vovó vovô dedo mão água leite azul vermelho amarelo "
              "menino menina amigo olha come dia lua rua sim não",
    "sight2": "que com por para mas mais muito está são tem logo quando onde aqui ali hoje bem grande feliz bonito "
              "novo todo pouco outro fazer dizer ver dar",
    "sight3": "também sempre nunca depois antes então porque enquanto durante contra sobre entre desde até mesmo "
              "cada coisa tempo mundo vida ano parte pessoa lugar momento trabalho escola juntos",
}
THEMES_DE = {
    "animals": "katze hund pferd tiger zebra hase affe giraffe löwe bär maus schaf ziege ente frosch eule adler "
               "panda koala otter kamel nilpferd schlange igel wolf fuchs pinguin",
    "ocean": "welle muschel krebs wal hai koralle krake delfin robbe ebbe flut sand riff tintenfisch alge seestern "
             "qualle hummer anker boot perle salz insel strand",
    "space": "stern mond planet komet rakete galaxie saturn mars venus erde jupiter asteroid nebel sonne meteor "
             "krater astronaut teleskop weltall raumschiff satellit",
    "food": "apfel brot käse pizza nudeln suppe salat banane traube mango karotte reis honig keks kuchen pfirsich "
            "zitrone butter birne pflaume ananas milch",
    "weather": "regen schnee wind wolke sturm sonnig donner nebel hagel frost regenbogen brise tau hitze kälte "
               "nieselregen tornado blitz gewitter",
    "sports": "fußball tennis golf hockey rugby radfahren eislauf ski rudern boxen karate surfen judo schwimmen "
              "laufen basketball tanzen turnen segeln reiten",
    "autumn": "herbst blatt laub kastanie eichel pilz drachen apfel kürbis igel wald nebel regen wind ernte nuss "
              "baum stiefel schal laterne",
    "halloween": "kürbis hexe geist gespenst besen kessel spinne fledermaus kerze maske mond eule katze vampir monster "
                 "grusel kostüm süßes schloss zauber nacht skelett",
    "winter": "schnee eis frost schlitten schal mütze handschuh flocke kälte kamin ofen tee pinguin eisbär "
              "schneemann iglu eiszapfen ski stern winter decke kakao",
    "spring": "frühling blume tulpe knospe blüte vogel nest ei küken lamm hase biene regen sonne garten gras wiese "
              "marienkäfer raupe ostern samen",
    "summer": "sommer sonne strand meer sand eis urlaub hitze badehose welle muschel zelt picknick schwimmen "
              "sonnenhut ferien melone erdbeere grillen boot",
    "sight1": "und ich bin ist eine die der das mit auf wir ihr sie Mama Papa Oma Opa Ball Katze Haus rot blau gelb "
              "grün nein",
    "sight2": "nicht auch noch nur sehr gut hat haben sein kann will muss geht kommt macht sagt sieht spielt heute "
              "dann wenn weil aber oder alle viel klein groß neu",
    "sight3": "immer wieder schon vielleicht zusammen manchmal zuerst später gestern morgen danach weiter bitte "
              "danke wirklich natürlich jeder etwas nichts warum welche Schule Freund Kinder Mutter Vater Wasser "
              "Stadt",
}
THEMES_IT = {
    "animals": "gatto cane cavallo tigre zebra coniglio scimmia giraffa leone orso topo pecora capra anatra rana gufo "
               "aquila panda koala lontra cammello ippopotamo serpente riccio lupo volpe pinguino elefante",
    "ocean": "onda conchiglia granchio balena squalo corallo polpo delfino foca marea sabbia scoglio calamaro alga "
             "stella medusa aragosta ancora barca perla sale isola spiaggia pesce",
    "space": "stella luna pianeta cometa razzo galassia saturno marte venere terra giove asteroide nebulosa sole "
             "meteora cratere astronauta telescopio spazio astronave satellite orbita",
    "food": "mela pane formaggio pizza pasta minestra insalata banana uva mango carota riso miele biscotto torta "
            "pesca limone burro pera prugna ananas latte gelato fragola",
    "weather": "pioggia neve vento nuvola tempesta sole tuono nebbia grandine brina arcobaleno brezza rugiada caldo "
               "freddo pioviggine tornado fulmine temporale ombrello",
    "sports": "calcio tennis golf hockey rugby ciclismo pattinaggio sci canottaggio pugilato karate surf judo nuoto "
              "corsa pallacanestro danza ginnastica vela equitazione pallavolo",
    "autumn": "autunno foglia castagna ghianda fungo aquilone mela zucca riccio bosco nebbia pioggia vento raccolto "
              "noce albero stivali sciarpa vendemmia uva ottobre",
    "halloween": "zucca strega fantasma scopa calderone ragno pipistrello candela maschera luna gufo gatto vampiro "
                 "mostro paura costume caramelle castello magia notte scheletro mummia",
    "winter": "neve ghiaccio gelo slittino sciarpa berretto guanti fiocco freddo camino stufa pinguino orso "
              "pupazzo igloo ghiacciolo sci stella inverno coperta cioccolata dicembre",
    "spring": "primavera fiore tulipano gemma bocciolo uccello nido uovo pulcino agnello coniglio ape pioggia sole "
              "giardino erba prato coccinella bruco seme farfalla margherita",
    "summer": "estate sole spiaggia mare sabbia gelato vacanze caldo costume onda conchiglia tenda picnic nuoto "
              "cappello occhiali anguria fragola secchiello barca ombrellone",
    "sight1": "una lui lei noi voi loro mamma papà nonno nonna casa sole mare cane gatto palla mano rosso blu "
              "ciao bimbo pane latte gioco luna",
    "sight2": "che non con per più molto anche come quando dove oggi ieri bene male grande piccolo bello nuovo "
              "tutto poco altro fare dire vedere andare",
    "sight3": "sempre mai dopo prima allora perché mentre insieme ancora qualche ogni niente domani adesso spesso "
              "forse davvero grazie scuola amico bambini acqua città famiglia mattina",
}
THEMES_NL = {
    "animals": "kat hond paard tijger zebra konijn aap giraf leeuw beer muis schaap geit eend kikker uil adelaar "
               "panda koala otter kameel nijlpaard slang egel wolf vos pinguïn koe varken haas",
    "ocean": "golf schelp krab walvis haai koraal octopus dolfijn zeehond eb vloed zand rif inktvis zeewier zeester "
             "kwal kreeft anker boot parel zout eiland strand duin meeuw",
    "space": "ster maan planeet komeet raket melkweg saturnus mars venus aarde jupiter zon meteoor krater astronaut "
             "telescoop heelal satelliet baan neptunus uranus ruimte",
    "food": "appel brood kaas pizza pasta soep salade banaan druif mango wortel rijst honing koekje taart perzik "
            "citroen boter peer pruim ananas melk ei tomaat",
    "weather": "regen sneeuw wind wolk storm zonnig donder mist hagel vorst regenboog bries dauw hitte kou motregen "
               "tornado bliksem onweer ijzel",
    "sports": "voetbal tennis golf hockey rugby fietsen schaatsen skiën roeien boksen karate surfen judo zwemmen "
              "hardlopen basketbal dansen turnen zeilen paardrijden korfbal",
    "autumn": "herfst blad bladeren kastanje eikel paddenstoel vlieger appel pompoen egel bos mist regen wind oogst "
              "noot boom laarzen sjaal lantaarn eekhoorn",
    "halloween": "pompoen heks geest spook bezem ketel spin vleermuis kaars masker maan uil kat vampier monster "
                 "griezel kostuum snoep kasteel toverstaf nacht skelet",
    "winter": "sneeuw ijs vorst slee sjaal muts handschoen vlok kou haard kachel thee ijsbeer sneeuwpop iglo "
              "ijspegel ski ster winter deken schaatsen kerst",
    "spring": "lente bloem tulp knop bloesem vogel nest ei kuiken lam haas bij regen zon tuin gras wei vlinder rups "
              "pasen zaadje narcis",
    "summer": "zomer zon strand zee zand ijsje vakantie hitte zwembad golf schelp tent picknick zwemmen zonnehoed "
              "meloen aardbei barbecue boot zonnebril",
    "sight1": "ben het een nee mama papa oma opa bal kat vis huis rood blauw geel wij jij zij maan hond boom "
              "auto zon bed deur pop",
    "sight2": "niet ook nog maar heel goed heeft hebben zijn kan wil moet gaat komt maakt zegt ziet speelt vandaag "
              "dan als want alle veel klein groot nieuw",
    "sight3": "altijd weer misschien samen soms eerst later gisteren morgen daarna verder alsjeblieft bedankt echt "
              "natuurlijk iedereen iets niets waarom welke school vriend kinderen moeder vader water stad",
}
THEMES_BY_LANGUAGE = {"es": THEMES_ES, "fr": THEMES_FR, "pt": THEMES_PT, "de": THEMES_DE, "it": THEMES_IT, "nl": THEMES_NL}
THEME_NAMES = {"animals": "Animals", "ocean": "Ocean", "space": "Space", "food": "Food", "weather": "Weather",
               "sports": "Sports", "autumn": "Autumn", "halloween": "Halloween", "winter": "Winter", "spring": "Spring",
               "summer": "Summer", "sight1": "Sight words: first", "sight2": "Sight words: next",
               "sight3": "Sight words: harder", "custom": "Your own list"}
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
