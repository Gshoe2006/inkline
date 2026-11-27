"""Draw what you read: short sentences, each over a framed box to draw what it describes ("A red ball under a big
tree"), to show a sentence has been read and understood.

The sentences are Inkline's own, written in each language at three levels: a few words for ages 4-6 (complexity
1-3), a sentence with where things are for 7-9 (4-7), two sentences with more to put in the picture for 10 and up
(8-10). The seed picks them, none twice on a page. Or type your own, separated by ; (up to six).

Six boxes (two across, three down; three across on a sideways page) at complexity 3-7, four bigger ones for the
youngest and for the longest sentences. Every box has a frame to draw in. There's nothing to solve, so no answer page.
"""

import re

from .. import i18n
from ..i18n import tr
from ..rng import pick

SOURCES = {"sentences": "Inkline's sentences", "custom": "Your own sentences"}
MAX_TEXT = 600
MAX_OWN = 6

READ_SENTENCES = {
    "en": [
        ["A big red ball.", "A cat on a mat.", "The sun is hot.", "A fish in a bowl.", "Two green apples.",
         "A dog with a hat.", "A boat on the sea.", "Three yellow stars.", "A bird in a tree.", "A small blue car.",
         "A duck in a pond.", "A cake with candles."],
        ["A red ball is under a big tree.", "A girl flies a kite on a windy hill.",
         "Two cats are sleeping on a soft blue sofa.", "A snowman wears a hat and a long scarf.",
         "A rocket is flying past the moon and the stars.", "A frog sits on a leaf in the middle of a pond.",
         "There are four flowers in a pot by the window.", "A boy is eating an ice cream on the beach.",
         "A spider has made a web between two branches.", "A tall giraffe is eating leaves from a tree.",
         "A little mouse is hiding behind a big piece of cheese.", "A train goes over a bridge above a river."],
        ["A lighthouse stands on a rock in a stormy sea. A small boat with one sail is sailing towards it.",
         "A castle has two towers with flags on top. A dragon is sleeping in front of the gate.",
         "A bus is waiting at a stop on a rainy day. Three people with umbrellas are standing in a queue.",
         "A treehouse is built in an old oak tree. A rope ladder hangs down, and a cat is climbing it.",
         "An astronaut is floating outside a space station. The Earth is behind her.",
         "A market stall sells fruit in baskets. There are bananas on the left and grapes on the right.",
         "A hot-air balloon with stripes floats over a farm. Below it, cows stand next to a red barn.",
         "A pirate ship has three masts and a flag. A parrot is sitting on the captain's shoulder.",
         "A snail and a ladybird are racing along a garden wall. The snail is winning.",
         "A robot is watering plants in a greenhouse. One of the plants is taller than the robot.",
         "Two children are building a sandcastle with a moat. A big wave is about to reach it.",
         "A bakery window shows three cakes. The biggest cake has a cherry on top."],
    ],
    "es": [
        ["Una pelota roja grande.", "Un gato en una alfombra.", "El sol calienta.", "Un pez en una pecera.",
         "Dos manzanas verdes.", "Un perro con sombrero.", "Un barco en el mar.", "Tres estrellas amarillas.",
         "Un pájaro en un árbol.", "Un coche azul pequeño.", "Un pato en un estanque.", "Una tarta con velas."],
        ["Una pelota roja está debajo de un árbol grande.", "Una niña vuela una cometa en una colina con viento.",
         "Dos gatos duermen en un sofá azul.", "Un muñeco de nieve lleva sombrero y una bufanda larga.",
         "Un cohete pasa volando junto a la luna y las estrellas.", "Una rana está sentada en una hoja en medio de un estanque.",
         "Hay cuatro flores en una maceta junto a la ventana.", "Un niño come un helado en la playa.",
         "Una araña ha hecho una telaraña entre dos ramas.", "Una jirafa alta come hojas de un árbol.",
         "Un ratoncito se esconde detrás de un trozo grande de queso.", "Un tren pasa por un puente sobre un río."],
        ["Un faro está sobre una roca en un mar con tormenta. Un barquito de vela navega hacia él.",
         "Un castillo tiene dos torres con banderas arriba. Un dragón duerme delante de la puerta.",
         "Un autobús espera en una parada un día de lluvia. Tres personas con paraguas hacen cola.",
         "Hay una casa en un roble viejo. Cuelga una escalera de cuerda y un gato está subiendo.",
         "Una astronauta flota fuera de una estación espacial. La Tierra está detrás de ella.",
         "Un puesto del mercado vende fruta en cestas. Hay plátanos a la izquierda y uvas a la derecha.",
         "Un globo aerostático de rayas vuela sobre una granja. Debajo, unas vacas están junto a un granero rojo.",
         "Un barco pirata tiene tres mástiles y una bandera. Un loro está en el hombro del capitán.",
         "Un caracol y una mariquita hacen una carrera por un muro del jardín. Va ganando el caracol.",
         "Un robot riega plantas en un invernadero. Una de las plantas es más alta que el robot.",
         "Dos niños hacen un castillo de arena con un foso. Una ola grande está a punto de llegar.",
         "En el escaparate de una pastelería hay tres tartas. La más grande tiene una cereza encima."],
    ],
    "fr": [
        ["Un gros ballon rouge.", "Un chat sur un tapis.", "Le soleil est chaud.", "Un poisson dans un bocal.",
         "Deux pommes vertes.", "Un chien avec un chapeau.", "Un bateau sur la mer.", "Trois étoiles jaunes.",
         "Un oiseau dans un arbre.", "Une petite voiture bleue.", "Un canard dans une mare.", "Un gâteau avec des bougies."],
        ["Un ballon rouge est sous un grand arbre.", "Une fille fait voler un cerf-volant sur une colline.",
         "Deux chats dorment sur un canapé bleu.", "Un bonhomme de neige porte un chapeau et une longue écharpe.",
         "Une fusée vole près de la lune et des étoiles.", "Une grenouille est assise sur une feuille au milieu d'une mare.",
         "Il y a quatre fleurs dans un pot près de la fenêtre.", "Un garçon mange une glace sur la plage.",
         "Une araignée a tissé une toile entre deux branches.", "Une grande girafe mange les feuilles d'un arbre.",
         "Une petite souris se cache derrière un gros morceau de fromage.", "Un train passe sur un pont au-dessus d'une rivière."],
        ["Un phare se dresse sur un rocher dans une mer agitée. Un petit voilier navigue vers lui.",
         "Un château a deux tours avec des drapeaux. Un dragon dort devant la porte.",
         "Un bus attend à l'arrêt un jour de pluie. Trois personnes avec des parapluies font la queue.",
         "Une cabane est construite dans un vieux chêne. Une échelle de corde pend et un chat y grimpe.",
         "Une astronaute flotte à l'extérieur d'une station spatiale. La Terre est derrière elle.",
         "Un étal du marché vend des fruits dans des paniers. Il y a des bananes à gauche et du raisin à droite.",
         "Une montgolfière à rayures flotte au-dessus d'une ferme. En dessous, des vaches sont près d'une grange rouge.",
         "Un bateau pirate a trois mâts et un drapeau. Un perroquet est perché sur l'épaule du capitaine.",
         "Un escargot et une coccinelle font la course sur un mur du jardin. L'escargot est en tête.",
         "Un robot arrose des plantes dans une serre. Une des plantes est plus grande que le robot.",
         "Deux enfants construisent un château de sable avec des douves. Une grosse vague va l'atteindre.",
         "La vitrine d'une pâtisserie montre trois gâteaux. Le plus gros a une cerise dessus."],
    ],
    "pt": [
        ["Uma bola vermelha grande.", "Um gato num tapete.", "O sol está quente.", "Um peixe num aquário.",
         "Duas maçãs verdes.", "Um cachorro de chapéu.", "Um barco no mar.", "Três estrelas amarelas.",
         "Um pássaro numa árvore.", "Um carrinho azul.", "Um pato num lago.", "Um bolo com velas."],
        ["Uma bola vermelha está debaixo de uma árvore grande.", "Uma menina solta pipa num morro com vento.",
         "Dois gatos dormem num sofá azul.", "Um boneco de neve usa chapéu e um cachecol comprido.",
         "Um foguete passa voando perto da lua e das estrelas.", "Um sapo está sentado numa folha no meio do lago.",
         "Há quatro flores num vaso perto da janela.", "Um menino toma sorvete na praia.",
         "Uma aranha fez uma teia entre dois galhos.", "Uma girafa alta come folhas de uma árvore.",
         "Um ratinho se esconde atrás de um pedaço grande de queijo.", "Um trem passa numa ponte sobre um rio."],
        ["Um farol fica numa rocha no meio de um mar agitado. Um barquinho a vela navega até ele.",
         "Um castelo tem duas torres com bandeiras no alto. Um dragão dorme na frente do portão.",
         "Um ônibus espera no ponto num dia de chuva. Três pessoas de guarda-chuva estão na fila.",
         "Há uma casa na árvore num carvalho velho. Uma escada de corda está pendurada e um gato sobe por ela.",
         "Uma astronauta flutua fora de uma estação espacial. A Terra está atrás dela.",
         "Uma banca da feira vende frutas em cestos. Há bananas à esquerda e uvas à direita.",
         "Um balão listrado voa sobre uma fazenda. Embaixo, vacas estão ao lado de um celeiro vermelho.",
         "Um navio pirata tem três mastros e uma bandeira. Um papagaio está no ombro do capitão.",
         "Um caracol e uma joaninha apostam corrida num muro do jardim. O caracol está ganhando.",
         "Um robô rega plantas numa estufa. Uma das plantas é mais alta que o robô.",
         "Duas crianças fazem um castelo de areia com um fosso. Uma onda grande está quase chegando.",
         "A vitrine de uma confeitaria mostra três bolos. O bolo maior tem uma cereja em cima."],
    ],
    "de": [
        ["Ein großer roter Ball.", "Eine Katze auf einer Matte.", "Die Sonne ist heiß.", "Ein Fisch im Glas.",
         "Zwei grüne Äpfel.", "Ein Hund mit Hut.", "Ein Boot auf dem Meer.", "Drei gelbe Sterne.",
         "Ein Vogel im Baum.", "Ein kleines blaues Auto.", "Eine Ente im Teich.", "Ein Kuchen mit Kerzen."],
        ["Ein roter Ball liegt unter einem großen Baum.", "Ein Mädchen lässt auf einem Hügel einen Drachen steigen.",
         "Zwei Katzen schlafen auf einem blauen Sofa.", "Ein Schneemann trägt einen Hut und einen langen Schal.",
         "Eine Rakete fliegt am Mond und an den Sternen vorbei.", "Ein Frosch sitzt auf einem Blatt mitten im Teich.",
         "Am Fenster stehen vier Blumen in einem Topf.", "Ein Junge isst am Strand ein Eis.",
         "Eine Spinne hat ein Netz zwischen zwei Ästen gebaut.", "Eine große Giraffe frisst Blätter von einem Baum.",
         "Eine kleine Maus versteckt sich hinter einem großen Stück Käse.", "Ein Zug fährt über eine Brücke über einem Fluss."],
        ["Ein Leuchtturm steht auf einem Felsen im stürmischen Meer. Ein kleines Segelboot fährt auf ihn zu.",
         "Eine Burg hat zwei Türme mit Fahnen. Vor dem Tor schläft ein Drache.",
         "Ein Bus wartet an einem Regentag an der Haltestelle. Drei Leute mit Schirmen stehen in einer Reihe.",
         "In einer alten Eiche ist ein Baumhaus. Eine Strickleiter hängt herunter, und eine Katze klettert hinauf.",
         "Eine Astronautin schwebt draußen vor einer Raumstation. Hinter ihr ist die Erde.",
         "Ein Marktstand verkauft Obst in Körben. Links liegen Bananen und rechts Trauben.",
         "Ein gestreifter Heißluftballon schwebt über einem Bauernhof. Darunter stehen Kühe neben einer roten Scheune.",
         "Ein Piratenschiff hat drei Masten und eine Flagge. Ein Papagei sitzt auf der Schulter des Kapitäns.",
         "Eine Schnecke und ein Marienkäfer machen ein Wettrennen auf einer Gartenmauer. Die Schnecke liegt vorn.",
         "Ein Roboter gießt Pflanzen in einem Gewächshaus. Eine Pflanze ist größer als der Roboter.",
         "Zwei Kinder bauen eine Sandburg mit einem Graben. Gleich kommt eine große Welle.",
         "Im Schaufenster einer Bäckerei stehen drei Torten. Die größte hat eine Kirsche obendrauf."],
    ],
    "it": [
        ["Una grande palla rossa.", "Un gatto su un tappeto.", "Il sole è caldo.", "Un pesce nella boccia.",
         "Due mele verdi.", "Un cane con il cappello.", "Una barca sul mare.", "Tre stelle gialle.",
         "Un uccello su un albero.", "Una piccola auto blu.", "Un'anatra nello stagno.", "Una torta con le candeline."],
        ["Una palla rossa è sotto un grande albero.", "Una bambina fa volare un aquilone su una collina.",
         "Due gatti dormono su un divano blu.", "Un pupazzo di neve ha un cappello e una lunga sciarpa.",
         "Un razzo vola vicino alla luna e alle stelle.", "Una rana è seduta su una foglia in mezzo allo stagno.",
         "Ci sono quattro fiori in un vaso vicino alla finestra.", "Un bambino mangia un gelato in spiaggia.",
         "Un ragno ha fatto una ragnatela tra due rami.", "Una giraffa alta mangia le foglie di un albero.",
         "Un topolino si nasconde dietro un grosso pezzo di formaggio.", "Un treno passa su un ponte sopra un fiume."],
        ["Un faro si trova su uno scoglio in un mare in tempesta. Una piccola barca a vela naviga verso di lui.",
         "Un castello ha due torri con le bandiere in cima. Un drago dorme davanti al portone.",
         "Un autobus aspetta alla fermata in un giorno di pioggia. Tre persone con l'ombrello sono in fila.",
         "C'è una casetta su una vecchia quercia. Pende una scala di corda e un gatto ci sta salendo.",
         "Un'astronauta galleggia fuori da una stazione spaziale. Dietro di lei c'è la Terra.",
         "Una bancarella del mercato vende frutta nei cesti. Ci sono banane a sinistra e uva a destra.",
         "Una mongolfiera a righe vola sopra una fattoria. Sotto, delle mucche sono vicino a un fienile rosso.",
         "Una nave pirata ha tre alberi e una bandiera. Un pappagallo è sulla spalla del capitano.",
         "Una lumaca e una coccinella fanno una gara lungo un muretto del giardino. La lumaca è in testa.",
         "Un robot annaffia le piante in una serra. Una delle piante è più alta del robot.",
         "Due bambini costruiscono un castello di sabbia con un fossato. Sta per arrivare una grande onda.",
         "La vetrina di una pasticceria mostra tre torte. La più grande ha una ciliegia sopra."],
    ],
    "nl": [
        ["Een grote rode bal.", "Een kat op een mat.", "De zon is heet.", "Een vis in een kom.", "Twee groene appels.",
         "Een hond met een hoed.", "Een boot op zee.", "Drie gele sterren.", "Een vogel in een boom.",
         "Een kleine blauwe auto.", "Een eend in een vijver.", "Een taart met kaarsjes."],
        ["Een rode bal ligt onder een grote boom.", "Een meisje laat een vlieger op op een winderige heuvel.",
         "Twee katten slapen op een blauwe bank.", "Een sneeuwpop draagt een hoed en een lange sjaal.",
         "Een raket vliegt langs de maan en de sterren.", "Een kikker zit op een blad midden in een vijver.",
         "Er staan vier bloemen in een pot bij het raam.", "Een jongen eet een ijsje op het strand.",
         "Een spin heeft een web gemaakt tussen twee takken.", "Een lange giraf eet blaadjes van een boom.",
         "Een muisje verstopt zich achter een groot stuk kaas.", "Een trein rijdt over een brug boven een rivier."],
        ["Een vuurtoren staat op een rots in een stormachtige zee. Een klein zeilbootje vaart ernaartoe.",
         "Een kasteel heeft twee torens met vlaggen. Voor de poort slaapt een draak.",
         "Een bus wacht bij de halte op een regenachtige dag. Drie mensen met paraplu's staan in de rij.",
         "In een oude eik is een boomhut gebouwd. Er hangt een touwladder en een kat klimt erin.",
         "Een astronaut zweeft buiten een ruimtestation. Achter haar is de aarde.",
         "Een marktkraam verkoopt fruit in manden. Links liggen bananen en rechts druiven.",
         "Een gestreepte luchtballon zweeft boven een boerderij. Daaronder staan koeien naast een rode schuur.",
         "Een piratenschip heeft drie masten en een vlag. Een papegaai zit op de schouder van de kapitein.",
         "Een slak en een lieveheersbeestje houden een wedstrijd op een tuinmuur. De slak ligt voor.",
         "Een robot geeft planten water in een kas. Een van de planten is groter dan de robot.",
         "Twee kinderen bouwen een zandkasteel met een gracht. Er komt zo een grote golf aan.",
         "In de etalage van een bakker staan drie taarten. De grootste heeft een kers erop."],
    ],
}


def level_for(c):
    return 0 if c <= 3 else 1 if c <= 7 else 2


def count_for(c):
    """How many boxes at complexity c: four big ones for the youngest and the longest sentences, else six."""
    return 4 if c <= 2 or c >= 8 else 6


def own_sentences(settings):
    """Your own sentences, as typed (separated by ; or new lines), up to six."""
    text = getattr(settings, "draw_text", "") or ""
    return [t.strip() for t in re.split(r"[;\n]+", text) if t.strip()][:MAX_OWN]


def note(settings):
    """What the sidebar says when your own sentences are chosen and none are typed, or ""."""
    if getattr(settings, "draw_source", "sentences") == "custom" and not own_sentences(settings):
        return tr("Type sentences to draw, separated by ;")
    return ""


def choose(rnd, c, settings=None):
    """The page's sentences: your own, or a seeded pick for the level, none twice."""
    if getattr(settings, "draw_source", "sentences") == "custom":
        own = own_sentences(settings)
        if own:
            return own
    pool = list(READ_SENTENCES.get(i18n.LANG, READ_SENTENCES["en"])[level_for(c)])
    for i in range(len(pool) - 1, 0, -1):
        j = pick(rnd, i + 1)
        pool[i], pool[j] = pool[j], pool[i]
    return pool[:count_for(c)]


def grid_for(n, landscape):
    """(columns, rows) for n boxes."""
    if n <= 3:
        return (n, 1) if landscape else (1, n)
    if n == 4:
        return 2, 2
    return (3, 2) if landscape else (2, 3)


def _wrap(ctx, text, width):
    lines, line = [], ""
    for w in text.split():
        trial = f"{line} {w}".strip()
        if line and ctx.measure_text(trial) > width:
            lines.append(line)
            line = w
        else:
            line = trial
    return lines + ([line] if line else [])


def draw(ctx, box, rnd, c, settings=None, lw=1.0, dpi=300, solve=False, **_opts):
    sentences = choose(rnd, c, settings)
    cols, rows = grid_for(len(sentences), box.w > box.h)
    gap = dpi * 0.22
    cw, ch = (box.w - gap * (cols - 1)) / cols, (box.h - gap * (rows - 1)) / rows
    # one text size for every box: as big as lets each sentence fit in a quarter of its box's height
    fs = min(dpi * (0.26 if level_for(c) == 0 else 0.2), ch * 0.12)
    while fs > dpi * 0.08:
        ctx.set_font(fs, 500)
        tallest = max(len(_wrap(ctx, f"{k + 1}. {t}", cw)) for k, t in enumerate(sentences))
        if tallest * fs * 1.3 <= ch * 0.26:
            break
        fs *= 0.93
    ctx.save()
    ctx.fill_style = ctx.stroke_style = "#000"
    ctx.text_align, ctx.text_baseline = "left", "alphabetic"
    frames = []
    ctx.set_font(fs, 500)
    wrapped = [_wrap(ctx, f"{k + 1}. {text}", cw) for k, text in enumerate(sentences)]
    for k, lines in enumerate(wrapped):
        col, row = k % cols, k // cols
        x, y = box.x + col * (cw + gap), box.y + row * (ch + gap)
        for i, line in enumerate(lines):
            ctx.fill_text(line, x, y + fs * (1.0 + 1.3 * i))
        most = max(len(w) for w in wrapped[row * cols:(row + 1) * cols])   # the frames in a row start level
        top = y + fs * (0.45 + 1.3 * max(most, 1))
        ctx.line_width = max(1.0, lw * 1.1)
        ctx.stroke_rect(x, top, cw, y + ch - top)
        frames.append((x, top, cw, y + ch - top))
    ctx.restore()
    return {"sentences": sentences, "frames": frames}
