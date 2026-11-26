"""Word ladders: get from the top word to the bottom one changing one letter at a time, every step a real word
(CAT, COT, DOT, DOG).

Each language has its own list of three-, four- and five-letter words below (written in the language rather than
translated, as the word search's themes are). A ladder is found by a breadth-first search from a start word picked
by the seed: the bottom word is one whose shortest way there takes exactly the number of steps wanted, so the
ladder can't be done in fewer. The answer page writes in one shortest way (any other way of real words is right too).

Complexity sets the words and the steps: three letters and 2-3 steps at 1-3 (four ladders), four letters and 3-4
steps at 4-7, five letters and 5 steps at 8-10 (three ladders). Where a language's list has no ladder that long, a
shorter word length is tried, then English words (note() says so). "Mark the letter that changes" shades the box of
each rung that differs from the rung above, as a clue.

Letters lose their accents, as in the word puzzles (Spanish keeps Ñ).
"""

from collections import deque

from .. import i18n
from ..i18n import tr
from ..rng import pick
from .cryptogram import letters_of

KINDS = {"plain": "Just the words", "marked": "Mark the letter that changes"}
INSTRUCTIONS = "Change one letter at a time to get from the top word to the bottom one. Every step must be a real word."

WORDS = {
    "en": """
ace act add age ago aid aim air all and ant any ape arm art ash ask ate bad bag ban bar bat bay bed bee beg bet bib
bid big bin bit bob bog boo bow box boy bud bug bun bus but buy cab can cap car cat cod cog cop cot cow cry cub cup
cut dad dam day den dew did dig dim dip dog dot dry dug ear eat egg elf end eye fan far fat fed fee few fig fin fir
fit fix fly fog for fox fry fun fur gap gas gem get got gum guy ham has hat hay hen her hid him hip his hit hog hop
hot how hub hug hum hut ice ill ink inn jab jam jar jaw jet jig job jog jot joy jug kid kit lab lad lap law lay led
leg let lid lie lip lit log lot low mad man map mat may men met mix mob mom mop mud mug mum nag nap net new nod not
now nut oak oar odd off oil old one our out owl own pad pal pan pat paw pay pea peg pen pet pie pig pin pit pod pop
pot pug pun pup put rag ram ran rap rat raw ray red rib rid rim rip rob rod rot row rub rug run sad sag sat saw say
sea see set sew she shy sip sit six ski sky sly sob son sow soy spy sub sun tab tag tan tap tar tea ten the tie tin
tip toe ton top tot tow toy try tub tug two urn use van vet wag was wax way web wed wet who why wig win wit wok won
yes yet you zip zoo
able ache acid also arch area army away baby back bake bald ball band bang bank bare bark barn base bath bead beak
beam bean bear beat beef been bell belt bend best bike bill bind bird bite blow blue boat body boil bold bolt bone
book boot bore born boss both bowl bulb bull bump burn bush busy cage cake call calm came camp cane cape card care
cart case cash cast cave cell chin chip chop city clap claw clay clip club coal coat code coin cold come cone cook
cool copy cord core corn cost cosy crab crib crop crow cube curl cute damp dare dark dart dash date dawn dead deal
dear deck deep deer desk dial dice dime dine dirt dish dive dock does doll dome done door dose dove down drag draw
drip drop drum duck dull dust duty each earn ease east easy edge even ever face fact fade fail fair fall fame fang
farm fast fate fear feed feel feet fell felt file fill film find fine fire firm fish fist five flag flap flat flew
flip flow foal foam fold folk fond food fool foot fork form fort four free frog from fuel full fuse gain game gate
gave gaze gear gift girl give glad glow glue goal goat gold golf gone good gown grab gram grew grey grid grin grip
grow gull hail hair half hall halt hand hang hard hare harm harp have hawk head heal heap hear heat heel held help
herb herd here hero hide high hike hill hint hire hold hole home hood hook hoop hope horn hose host hour huge hump
hunt hurt idea inch iron item jazz join joke jump just keen keep kept kick kind king kiss kite knee knew knit knob
knot know lace lady laid lake lamb lamp land lane last late lawn lazy lead leaf leak lean leap left lend lens less
lick life lift like lily lime line link lion list live load loaf loan lock loft long look loop lose loss lost loud
love luck lump lung made mail main make male mane many mare mark mash mask mast mate maze meal mean meat meet melt
menu mice mild milk mill mind mine mint miss mist moan moat mole mood moon more moss most moth move much mule must
name navy near neat neck need nest news next nice nine none noon nose note oats once only open oven over pace pack
page paid pail pain pair pale palm pane park part pass past path peak pear peas peel pest pick pier pile pill pine
pink pipe plan play plot plug plum poem pole pond pony pool poor pork port pose post pour pram pull pump pure push
race rack raft rail rain rake ramp rang rank rare rash rate read real rear rest rice rich ride ring ripe rise risk
road roam roar robe rock rode role roll roof room root rope rose rosy rude rule rung rush rust safe sage said sail
sale salt same sand sang sank save seal seam seat seed seek seem seen self sell send sent shed ship shoe shop shot
show shut sick side sigh sign silk sing sink site size skin skip slab sled slid slim slip slot slow snap snow soak
soap sock soda sofa soft soil sold sole some song soon sore sort soup sour spin spot star stay stem step stew stir
stop such suit sung sunk sure swan swim tail take tale talk tall tame tank tape task team tear tell tend tent term
test than that them then they thin this tick tide tidy tile till time tiny tire toad toes told tone took tool tops
torn toss town toys tram trap tray tree trim trip true tube tuck tune turn twin type unit upon used vase vast very
vest view vine vote wade wage wait wake walk wall wand want ward warm wash wasp wave wavy weak wear week well went
were west what when whip wide wild will wind wing wink wipe wire wise wish with woke wolf wood wool word wore work
worm worn wrap yard yarn year yell your zero zone zoom
about above actor adult after again agree alarm album alert alike alive allow alone along angel anger angle angry
apple apron arena arrow aside award aware badge baker basin batch beach beard beast begin being bench berry bikes
birds black blade blame blank blast blaze blend bless blind blink block blond blood bloom blown blues board boast
boats bones bonus boots bored bound boxer brain brake brand brass brave bread break brick bride brief bring brisk
broad broke brook broom brown brush build built bunch bunny burst cabin cable camel candy canoe cards cargo carry
carve catch cause chain chair chalk charm chart chase cheap check cheek cheer chess chest chick chief child chill
chips choir chore clamp clang clank clash clasp class clean clear click cliff climb cling cloak clock close cloth
cloud clown coach coast coats cocoa coins comet coral couch cough count court cover crane crank crash crate crawl
crazy cream creek crest crisp crops cross crowd crown crumb crust cubes curls curve cycle daily dairy daisy dance
dates diary diner dives dizzy dodge doing dolls dough draft drain drake drama drank drawn dream dress dried drift
drill drink drive drops drove drums ducks dunes eager eagle early earth easel eight elbow empty enjoy enter equal
event every exact extra fable faces facts faint fairy faith false fancy farms feast fence ferry fever field fifth
fifty final first flake flame flash flask fleet float flock flood floor flour flute foggy force forge forms forty
found frame fresh fried frost froze fruit fudge funny games gates giant gifts given glass globe glove goals goats
going grace grade grain grand grant grape grasp grass grate grave gravy great green greet grill grind groan group
grown guard guess guest guide habit handy happy hatch heads heard heart heavy hedge hello herbs hills hinge hobby
holes honey hoped horse hotel hound house hover human hurry ideal igloo image inner items jelly jewel joint jokes
judge juice kayak kites knife knock known label lakes lamps large later laugh layer leaps learn least leave ledge
lemon level light limit lined lines lions liver loads loose lorry lucky lunch magic major maker mango maple march
match mates maybe meals medal melon merry metal might mines minor minus mixed model money month moose motor mount
mouse mouth moved movie muddy music nerve never night noble noise north notes novel nurse ocean offer often olive
onion orbit order other otter outer owner paint pairs panda panel paper parks party paste patch pause peace peach
pearl pedal penny perch phone photo piano piece pilot pinch pines pitch pizza place plain plane plank plant plate
plays plump point polar porch pound power press price pride print prize proud prove prune punch puppy purse queen
quest quick quiet quilt quite radio rails raise ranch range rapid raven reach ready reply ridge rider right rings
rinse river roads roast robin robot rocks rocky rough round route royal rugby ruler salad sandy sauce scale scarf
scene scent score scout seven shade shake shall shape share shark sharp sheep sheet shelf shell shine shiny shirt
shock shoes shore short shout shown sight silly since skate skill skirt slate sleep slept slice slide slope small
smart smell smile smoke snack snail snake sneak sniff snore sound south space spade spare spark speak spear speed
spell spend spent spice spike spill spine spoon sport spray stack staff stage stair stake stamp stand stare start
state steak steam steel steep steer stick still sting stock stone stood stool store storm story stove straw strip
stuck study stuff sugar suits sunny super swamp swans sweep sweet swept swift swing table tales taste teach teeth
thank there thick thing think third thorn those three threw throw thumb tiger tight timer tired title toast today
tooth torch total touch tough tower towns trace track trade trail train tramp tread treat trees trick tried trout
truck truly trunk trust truth tulip tunes twice twins under until upper usual value video visit vivid voice wagon
waist watch water waves weave wheat wheel where which while white whole wider winds windy woman women woods words
world worry worth would woven wrist write wrong wrote yacht yards young yours youth zebra
""",
    "es": """
ajo ala ama ave bar bus col con dar das dos eco era fin gas gol hay hoy ida las les los luz mal mar mes mil mis
nos oca ojo ola oro oso pan par paz pez pie red rey rio sal sed ser sol son sur tal tan ten tia tio uno uva van ven
ver vez vid zoo
bala baja bajo bata boca boda bola bota cada caja cama capa cara caro casa caso cera cola copa cosa cuna dama dado
dato dedo dona fama faro fila fino foca foco foto gana gano gata gato gota hada higo hija hijo hilo hola kilo lado
lago lana lata lija lima lino lobo loca loco loma lona loro luna malo mala mano masa mata mayo mesa mina mira misa
moda modo mona mono moto nada nado nata nota pala palo pana para paro pasa paso pata pato pavo pelo pera pesa peso
piña pino pisa piso poco polo rama ramo rana raro rata rato rayo remo risa rima roca ropa rosa rota sala sano sapo
saco sola solo sopa suma tapa taza tela tiza toca todo topo toro vaca vale vaso vela velo vino beso cena pena sana
tono tipo dama boca coco coro duro muro puro mudo nube nudo pila pico rico lote bote mote
balas bajos batas bocas bolas botas cajas camas capas caras casas casos colas copas cosas cunas dados dedos focas
fotos gatas gatos gotas hadas higos hijos hilos lagos latas limas lobos lunas manos masas matas mesas monos motos
notas palos patas patos pavos pelos peras pesas pesos pinos pisos ramas ramos ranas ratas ratos rayos remos rocas
ropas rosas salas sapos sopas tapas tazas telas toros vacas vasos velas velos vinos besos cenas penas tonos tipos
nubes muros plato plata playa pluma llama llave carta tarta parte pasta pista costa cesta monte mente menta venta
punta junta junto juego fuego luego lento lente gente verde perla perro burro barro barra cerdo dulce noche leche
""",
    "fr": """
air ami art bac bal bar bas bec bol bon bus cas col cou don dos dur fer feu fil fin fou ile jeu jus lac lin lit
loi mal mer moi mon mot mur nez nid nom non nul oie par pas peu pin pot pou pur rat roi rue sac sec sel sol son
sur tas toi ton tri vol vue
bain bord bout boue cave chat char chou clou coup cour dame dent dose dune fait fort four gain gare joue jour lame
lait lave loup lune main mare mere mont mort mots mule nain nous page pain pare pere pont port pose poux rame rare
robe roue rose rive sain sort sous tard tour tout vain vent vous vrai pore pois mois noix voix bois rois loin soin
foin coin lion pion fil mine fine pile file ride rire dire lire cire pire bise mise rose
arbre balle belle bulle cable carte carpe corde corne fable ferme forme fleur livre libre linge lourd porte poire
pomme rouge sable singe songe table terre verre verte salle selle ville mille fille bille quille cache vache tache
poche roche biche niche mouche bouche douche louche
""",
    "pt": """
ave boi cor dor dez giz lei lua mal mar mel noz par paz por rei rua sal sol voz luz ovo uva asa
bala bola bota cama cano capa cara caro casa caso cola copo dado dama fada fama faro foca foto gado gata gato gola
gota jato lado lama lata lobo lodo logo mala mapa mata mato mesa moda modo mola moto nado nota pano pato pena pesa
peso pote rama rato roda rota sala sapo saco sete soda sola sopa tapa todo vaso vela fala vala cena lima rima mina
fina pino bico rico pico fogo jogo logo lago mago galo gelo pelo selo bolo rolo solo polo
balas bolas botas camas capas caras casas casos colas copos dados damas fadas focas fotos gatos gotas lados latas
lobos malas mapas mesas motos notas panos patos penas pesos ratos rodas salas sapos sacos sopas vasos velas carro
barro burro festa testa pasta posta porta porto corpo torta torre terra carta corta curta curto certo perto porco
peixe leite noite norte forte sorte corte conta ponta ponte monte fonte gente dente mente lente vento lento tanto
canto campo tempo
""",
    "de": """
alt arm ast bad bau bus eis gut hai hut mut not ohr rad rat rot see tag tal tee tor uhr weg zoo zug kuh reh
bach bahn bald ball band baum bein bett bild buch dach damm dann dein ding dose ente fach fall feld fest fein gold
geld hahn hals hand hase haus held hemd hose hund igel kahn kalt kamm kann kind kinn koch kopf lamm land laus loch
lohn mann maus mein mild mohn most mund nase nest nett noch post raum rand rest rind ring rose rost rund saum sand
sein sinn sohn tier test topf tuch vase vier wald wand wann welt wild wind zahn zelt zopf hier mehl fell hell
wolle rolle
blatt blume hasen hosen kanne katze knopf nasen panne rosen stein stuhl tanne tatze tisch fisch wanne vasen dosen
klein kranz kreis glanz pferd sonne tonne nonne wolke welle kelle zelle hasel nadel nagel vogel kegel segel regel
regen wagen magen lagen tagen
""",
    "it": """
ala ape bar blu due gas oca ora oro sei tre uno uva via zia zio
alto ago cane pane rana lana luna tana mano nano cara caro casa cosa rosa rose pera cera sera vera vero nero zero
mare male sale sole mole sola gola cola palo pala sala mela tela vela velo pelo dito dado lago mago lato cena pena
vena gatto riso viso vaso naso caso peso pesce dove nove mese rete sete tetto letto detto petto
gatta matto fatto patto latte notte botte rotta porta porto posta pasta pista costa testa festa resta torta torre
terra serra carta corta corto forte monte ponte fonte conte dente mente gente lente vento cento lento tanto canto
conto santo salto sasso rosso rossa pozzo pezzo mezzo nonno nonna donna gonna penna panna canna palla pelle bella
bello cella colla colle mille villa valle fiore
""",
    "nl": """
bal bed bel bos dak dal dam dag das dik dun gat hok hol hut kat kop kus lam lap mat mes mol mos nat net nek oog
oom pad pan pak pen pet pit pop pot rat rok rug sap sok tak tas tol ton top vak vat vis vos wal was wat weg wit
zak zat zes zon zoo
baan band beer berg boek boom boot deur doek geur glas goed gras haan haar hand hoed hoek hond hoop jaar kaal keer
kerk koek koop land loop maal maan mand meer melk mond naam paal paar peer poot raam rand roet rond room soep taal
veer voet waar wand weer werk zaal zand zoek zoon kind wind lint vlag vlam klok blok slak slim
bloem broek brood groot grond groen kaars paard steen stoel stoep fiets appel tafel vogel kogel zegel regel regen
wegen tegen deken teken leven zeven beker peper water later kater vader
""",
}

_graphs = {}


def _norm(word):
    return "".join(letters_of(ch) for ch in word)


def word_list(lang, length):
    """A language's words of this length, as capitals without accents."""
    seen, out = set(), []
    for w in WORDS.get(lang, "").split():
        n = _norm(w)
        if len(n) == length and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def neighbours(lang, length):
    """{word: [words one letter away]} for a language's words of this length."""
    key = (lang, length)
    if key not in _graphs:
        words = word_list(lang, length)
        buckets = {}
        for w in words:
            for i in range(length):
                buckets.setdefault(w[:i] + "_" + w[i + 1:], []).append(w)
        _graphs[key] = {w: sorted({v for i in range(length) for v in buckets[w[:i] + "_" + w[i + 1:]] if v != w})
                        for w in words}
    return _graphs[key]


def shortest(graph, start):
    """{word: (steps from start, the word before it)} by a breadth-first search."""
    seen = {start: (0, None)}
    todo = deque([start])
    while todo:
        w = todo.popleft()
        for v in graph[w]:
            if v not in seen:
                seen[v] = (seen[w][0] + 1, w)
                todo.append(v)
    return seen


def plan(c):
    """(letters, steps, ladders) for complexity c."""
    if c <= 3:
        return 3, (2, 3, 3)[c - 1], 4
    if c <= 7:
        return 4, (3, 4, 4, 4)[c - 4], 3
    return 5, 5, 3


def _find(rnd, graph, steps, count):
    """count ladders of exactly steps steps (each a list of words), different start and end words; fewer if the
    words don't allow it."""
    words = sorted(w for w, near in graph.items() if near)
    out, used = [], set()
    for _ in range(80):
        if len(out) >= count or not words:
            break
        start = words[pick(rnd, len(words))]
        if start in used:
            continue
        reach = shortest(graph, start)
        ends = sorted(w for w, (d, _p) in reach.items() if d == steps and w not in used)
        if not ends:
            continue
        end = ends[pick(rnd, len(ends))]
        path = [end]
        while reach[path[-1]][1] is not None:
            path.append(reach[path[-1]][1])
        path.reverse()
        out.append(path)
        used.update((start, end))
    return out


def make_ladders(rnd, c):
    """(ladders, language whose words they use): the language's own if it has ladders this long, trying shorter
    words, then English's."""
    length, steps, count = plan(c)
    for lang in dict.fromkeys((i18n.LANG, "en")):
        for n in sorted({length, 4, 3, 5}, key=lambda k: (abs(k - length), k)):
            graph = neighbours(lang, n)
            found = _find(rnd, graph, steps, count)
            if len(found) == count:
                return found, lang
    return found, "en"


def note(settings=None, c=5):
    """What the sidebar says when this language's words can't make the ladders, or ""."""
    if i18n.LANG == "en":
        return ""
    from ..rng import mulberry32
    _ladders, lang = make_ladders(mulberry32(getattr(settings, "seed", 1)), getattr(settings, "complexity", c))
    return tr("Not enough words in this language for ladders this long: these use English words.") if lang != i18n.LANG else ""


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    ladders, _lang = make_ladders(rnd, c)
    if not ladders:
        return None
    marked = getattr(settings, "ladder_kind", "plain") == "marked"
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    fs = min(dpi * 0.2, box.h / 22)
    top = box.y
    if not solve:
        ctx.set_font(fs * 0.9, 400)
        ctx.text_align, ctx.text_baseline = "left", "alphabetic"
        from .logic import _wrap
        for line in _wrap(ctx, tr(INSTRUCTIONS), box.w):
            top += fs * 1.25
            ctx.fill_text(line, box.x, top)
        top += fs * 0.6
    count = len(ladders)
    letters = len(ladders[0][0])
    rungs = len(ladders[0])
    def layout(rows):   # (squares' size, ladders across, column width, row height) with the ladders in rows
        per_row = -(-count // rows)
        cw, ch = box.w / per_row, (box.y + box.h - top) / rows
        return min(cw * 0.8 / (letters + 1.2), ch / (rungs * 1.25 + 1.2), dpi * 0.55), per_row, cw, ch

    # side by side, or in two rows: whichever gives bigger squares
    cell, per_row, cw, ch = max(layout(1), layout(2), key=lambda t: t[0])
    ctx.text_align, ctx.text_baseline = "center", "middle"
    for k, path in enumerate(ladders):
        r, col = divmod(k, per_row)
        lx = box.x + col * cw + (cw - letters * cell) / 2
        ly = top + r * ch + (ch - rungs * cell * 1.25) / 2
        ctx.line_width = max(1.0, lw * 0.8)   # the rails
        ctx.begin_path()
        for x in (lx - cell * 0.35, lx + letters * cell + cell * 0.35):
            ctx.move_to(x, ly - cell * 0.3)
            ctx.line_to(x, ly + rungs * cell * 1.25 + cell * 0.05)
        ctx.stroke()
        for i, word in enumerate(path):
            y = ly + i * cell * 1.25
            end = i in (0, rungs - 1)
            for j, letter in enumerate(word):
                x = lx + j * cell
                changed = i > 0 and path[i - 1][j] != letter
                if marked and changed and not end:
                    ctx.fill_style = "#ddd"
                    ctx.fill_rect(x, y, cell, cell)
                    ctx.fill_style = "#000"
                ctx.line_width = max(1.0, lw * (0.9 if end else 0.6))
                ctx.stroke_rect(x, y, cell, cell)
                if end or solve:
                    ctx.set_font(cell * 0.6, 700 if end else 600)
                    ctx.fill_style = "#000" if end else "#666"
                    ctx.fill_text(letter, x + cell / 2, y + cell * 0.52)
                    ctx.fill_style = "#000"
    ctx.restore()
    return {"ladders": ladders, "lang": _lang}
