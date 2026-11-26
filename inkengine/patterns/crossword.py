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
    "autumn": "leaf: Falls from trees in autumn; acorn: An oak tree grows from it; conker: A shiny brown nut on a "
              "string; pumpkin: A big orange vegetable; harvest: When farmers gather their crops; apple: You can "
              "pick it from a tree; squirrel: Hides nuts for winter; hedgehog: Prickly, and sleeps all winter; "
              "mushroom: Grows in the woods after rain; rake: Sweeps up fallen leaves; wind: Blows the leaves "
              "around; scarf: Keeps your neck warm; boots: Wear them to splash in puddles; school: Where you go to "
              "learn; pencil: You write and draw with it; satchel: A bag for school books",
    "halloween": "pumpkin: Carve a face in it; ghost: Says boo and is all white; bat: Flies at night and hangs upside "
                 "down; witch: Rides a broom; broom: A witch flies on it; costume: You dress up in it; mask: Covers "
                 "your face; sweets: You get them when you trick or treat; spider: Has eight legs; web: A spider spins "
                 "it; moon: Shines big and round at night; owl: Hoots in the dark; lantern: A light you carry; "
                 "cauldron: A big pot for a witch's potion; wizard: Waves a magic wand; skeleton: All the bones in "
                 "your body; party: Fun with friends and games",
    "winter": "snow: White and falls from the sky; ice: Frozen water; cold: How you feel without a coat; scarf: "
              "Wrap it round your neck; mitten: Keeps your hand warm; coat: Put it on before going out; sledge: "
              "Slide down a snowy hill on it; snowman: Has a carrot for a nose; snowflake: No two are the same; "
              "frost: Makes windows sparkle; cocoa: A hot chocolate drink; igloo: A house made of snow; skate: "
              "Glide on the ice; penguin: A bird that cannot fly; icicle: Hangs from the roof like a pointy spike; "
              "present: A gift wrapped in paper; star: Shines on the top of a tree; candle: Its little flame gives "
              "light; blanket: Snuggle under it to keep warm",
    "spring": "flower: Grows from a seed and smells nice; tulip: A cup-shaped flower; daffodil: A yellow spring "
              "flower; lamb: A baby sheep; chick: A baby hen; nest: Birds lay eggs in it; egg: Hunt for chocolate "
              "ones at Easter; bunny: A rabbit with long ears; rain: Helps the plants grow; puddle: Splash in it "
              "with your boots; blossom: Pink flowers on trees; bee: Buzzes from flower to flower; butterfly: Has "
              "bright colourful wings; seed: Plant it to grow a flower; garden: Where flowers and vegetables grow; "
              "rainbow: Colours in the sky after rain; duckling: A baby duck",
    "summer": "sun: Shines hot in the sky; beach: Sand by the sea; sand: Build castles with it; bucket: Fill it "
              "with sand or water; spade: Dig in the sand with it; shell: Find it on the seashore; wave: The sea "
              "rolls in with it; swim: Move through water; picnic: A meal outside on a blanket; holiday: Time off "
              "from school; sunglasses: Protect your eyes from the sun; kite: Flies high on a string; tent: Sleep "
              "in it when camping; island: Land with water all around; lemonade: A cold lemon drink; watermelon: A "
              "big green fruit, red inside; shorts: Short trousers for hot days; sunhat: Keeps the sun off your "
              "head",
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
    "autumn": "hoja: Cae de los árboles en otoño; bellota: De ella crece un roble; castaña: Se come asada en otoño; "
              "calabaza: Una verdura grande y naranja; cosecha: Cuando se recoge lo sembrado; manzana: Se coge de "
              "un árbol; ardilla: Guarda nueces para el invierno; erizo: Tiene púas y duerme en invierno; seta: "
              "Sale en el bosque después de llover; rastrillo: Sirve para juntar las hojas; viento: Hace volar las "
              "hojas; bufanda: Te abriga el cuello; botas: Para saltar en los charcos; colegio: Donde vas a "
              "aprender; lapiz: Con él escribes y dibujas; mochila: Llevas los libros en ella",
    "halloween": "calabaza: Le haces una cara y una vela dentro; fantasma: Es blanco y dice bu; murcielago: Vuela de "
                 "noche y duerme boca abajo; bruja: Vuela en una escoba; escoba: Una bruja vuela en ella; disfraz: Te "
                 "lo pones para parecer otro; mascara: Te tapa la cara; caramelo: Un dulce que te dan; araña: Tiene "
                 "ocho patas; telaraña: La teje una araña; luna: Brilla redonda de noche; buho: Ulula en la oscuridad; "
                 "caldero: Una olla grande de bruja; mago: Tiene una varita mágica; esqueleto: Todos los huesos del "
                 "cuerpo; fiesta: Juegos y diversión con amigos",
    "winter": "nieve: Blanca, cae del cielo; hielo: Agua congelada; frio: Lo sientes sin abrigo; bufanda: Te la "
              "enrollas al cuello; guantes: Te abrigan las manos; abrigo: Te lo pones para salir; trineo: Con él "
              "bajas por la nieve; muñeco: El de nieve tiene nariz de zanahoria; copo: Uno pequeño de nieve; "
              "escarcha: Hace brillar la hierba en invierno; chocolate: Se bebe caliente en taza; iglu: Una casa de "
              "nieve; patines: Con ellos te deslizas por el hielo; pingüino: Un pájaro que no vuela; regalo: Viene "
              "envuelto en papel; estrella: Brilla en lo alto del árbol; vela: Su llamita da luz; manta: Te tapas "
              "con ella para no tener frío",
    "spring": "flor: Crece de una semilla y huele bien; tulipan: Una flor con forma de copa; margarita: Una flor "
              "blanca con el centro amarillo; cordero: El hijo de la oveja; pollito: El hijo de la gallina; nido: "
              "Los pájaros ponen huevos en él; huevo: En Pascua los buscas de chocolate; conejo: Tiene orejas "
              "largas y salta; lluvia: Ayuda a crecer a las plantas; charco: Saltas en él con botas; abeja: Zumba "
              "de flor en flor; mariposa: Tiene alas de colores; semilla: La plantas para que crezca una flor; "
              "jardin: Allí crecen las flores; arcoiris: Colores en el cielo después de llover; patito: El hijo de "
              "la pata; nube: Trae la lluvia",
    "summer": "sol: Calienta mucho en el cielo; playa: Arena junto al mar; arena: Con ella haces castillos; cubo: "
              "Lo llenas de arena o de agua; pala: Con ella cavas en la arena; concha: La encuentras en la orilla; "
              "ola: El mar la trae a la playa; nadar: Moverse en el agua; helado: Frío y dulce, en cucurucho; "
              "vacaciones: Días sin colegio; gafas: Las de sol protegen tus ojos; cometa: Vuela alto con una "
              "cuerda; tienda: Duermes en ella de acampada; isla: Tierra con agua alrededor; limonada: Una bebida "
              "fría de limón; sandia: Fruta grande, verde por fuera y roja por dentro; piscina: Te bañas en ella; "
              "toalla: Te secas con ella",
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
    "autumn": "feuille: Elle tombe des arbres en automne; gland: Un chêne pousse à partir de lui; marron: Il est "
              "brillant et tombe du marronnier; citrouille: Un gros légume orange; récolte: Quand on ramasse ce qui "
              "a poussé; pomme: On la cueille dans un arbre; écureuil: Il cache des noisettes pour l'hiver; "
              "hérisson: Il a des piquants et dort tout l'hiver; champignon: Il pousse dans les bois après la "
              "pluie; râteau: Il ramasse les feuilles mortes; vent: Il fait voler les feuilles; écharpe: Elle te "
              "tient le cou au chaud; bottes: Pour sauter dans les flaques; école: On y va pour apprendre; crayon: "
              "On écrit et on dessine avec; cartable: Le sac pour l'école",
    "halloween": "citrouille: On y creuse un visage; fantôme: Il est tout blanc et fait bouh; sorcière: Elle vole sur "
                 "un balai; balai: Une sorcière vole dessus; costume: On le met pour se déguiser; masque: Il cache ton "
                 "visage; bonbon: On en reçoit en frappant aux portes; araignée: Elle a huit pattes; toile: L'araignée "
                 "la tisse; lune: Elle brille ronde la nuit; hibou: Il hulule dans le noir; lanterne: Une lumière "
                 "qu'on porte; chaudron: La grosse marmite de la sorcière; sorcier: Il a une baguette magique; "
                 "squelette: Tous les os du corps; fête: Des jeux et des amis; chat: Le noir est l'ami de la sorcière",
    "winter": "neige: Elle tombe blanche du ciel; glace: De l'eau gelée; froid: On le sent sans manteau; écharpe: "
              "On l'enroule autour du cou; moufle: Elle garde ta main au chaud; bonnet: Il te couvre la tête; "
              "manteau: On le met avant de sortir; luge: On glisse dessus dans la neige; bonhomme: Celui de neige a "
              "une carotte pour nez; flocon: Un petit morceau de neige; givre: Il fait briller les vitres; "
              "chocolat: On le boit chaud; igloo: Une maison de neige; pingouin: Un oiseau noir et blanc; glaçon: "
              "Il pend du toit, tout pointu; cadeau: Il est emballé dans du papier; étoile: Elle brille en haut du "
              "sapin; bougie: Sa petite flamme éclaire; couverture: On se blottit dessous",
    "spring": "fleur: Elle pousse d'une graine et sent bon; tulipe: Une fleur en forme de coupe; jonquille: Une "
              "fleur jaune du printemps; agneau: Le bébé du mouton; poussin: Le bébé de la poule; nid: Les oiseaux "
              "y pondent leurs oeufs; oeuf: On le cherche en chocolat à Pâques; lapin: Il a de longues oreilles; "
              "pluie: Elle aide les plantes à pousser; flaque: On saute dedans avec ses bottes; abeille: Elle "
              "butine les fleurs; papillon: Il a de jolies ailes colorées; graine: On la plante pour avoir une "
              "fleur; bourgeon: Il deviendra une feuille ou une fleur; jardin: Les fleurs y poussent; oiseau: Il "
              "chante dans les arbres; caneton: Le bébé du canard",
    "summer": "soleil: Il brille fort dans le ciel; plage: Du sable au bord de la mer; sable: On en fait des "
              "châteaux; seau: On le remplit de sable ou d'eau; pelle: On creuse le sable avec; coquillage: On le "
              "ramasse au bord de l'eau; vague: La mer la pousse sur la plage; nager: Avancer dans l'eau; glace: "
              "Froide et sucrée, dans un cornet; vacances: Pas d'école pendant ces jours; lunettes: Celles de "
              "soleil protègent tes yeux; tente: On dort dedans en camping; île: De la terre entourée d'eau; "
              "limonade: Une boisson fraîche qui pétille; pastèque: Un gros fruit vert, rouge dedans; piscine: On "
              "s'y baigne; serviette: On s'essuie avec; chapeau: Il protège ta tête du soleil",
}
THEMES_PT = {
    "animals": "gato: Faz miau; cachorro: Late e abana o rabo; vaca: Dá leite para nós; cavalo: Dá para andar "
               "montado nele; ovelha: Sua lã vira blusa; pato: Faz quá-quá; sapo: Verde e pula; coruja: Pia à noite; "
               "leão: O rei da selva; tigre: Um gatão com listras; zebra: Um cavalo com listras; macaco: Pula de "
               "galho em galho; coelho: Tem orelhas compridas e pula; rato: Pequeno e gosta de queijo; elefante: Tem "
               "uma tromba; girafa: Tem o pescoço muito comprido; cobra: Comprida e sem pernas; urso: Grande, peludo "
               "e gosta de mel; peixe: Nada e tem nadadeiras; abelha: Faz mel",
    "food": "maçã: Uma fruta vermelha ou verde; banana: Uma fruta comprida e amarela; pão: Com ele se faz "
            "torrada; queijo: Os ratos adoram; ovo: A galinha bota; leite: Uma bebida branca da vaca; pizza: "
            "Redonda e com cobertura; cenoura: Um legume laranja; sopa: Tomada quente no prato fundo; bolo: Tem "
            "velas no aniversário; mel: As abelhas fazem; arroz: Grãozinhos brancos do almoço; feijão: Vai junto "
            "com o arroz no prato; pera: Uma fruta com formato de sino; limão: Uma fruta azeda; uva: Pequena e "
            "cresce em cachos; ervilha: Uma bolinha verde; geleia: Passa no pão; macarrão: O espaguete é um tipo; "
            "milho: Vira pipoca",
    "space": "sol: A estrela mais perto de nós; lua: Brilha à noite; estrela: Pisca no céu; terra: O planeta onde "
             "vivemos; marte: O planeta vermelho; foguete: Voa para o espaço; cometa: Tem uma cauda comprida; "
             "órbita: O caminho em volta de um planeta; saturno: O planeta com anéis; planeta: A Terra é um; "
             "astronauta: Viaja para o espaço; telescópio: Serve para olhar as estrelas; galáxia: Bilhões de "
             "estrelas juntas; nave: Leva os astronautas; satélite: Gira em volta de um planeta; cratera: Um "
             "buraco redondo na Lua",
    "ocean": "onda: Quebra na praia; concha: Dá para achar na praia; caranguejo: Anda de lado e tem garras; "
             "baleia: O maior animal do mar; tubarão: Um peixe de dentes afiados; coral: Forma recifes coloridos; "
             "polvo: Tem oito braços; golfinho: Um animal do mar esperto que pula; foca: Bate as nadadeiras; maré: "
             "O mar sobe e desce com ela; areia: Dá para fazer castelos com ela; lula: Solta tinta; lagosta: "
             "Parece um caranguejo grande de rabo comprido; âncora: Segura o barco no lugar; barco: Flutua na "
             "água; pérola: Uma bolinha brilhante dentro da ostra; sal: Deixa a água do mar com gosto estranho; "
             "praia: Lugar com areia perto do mar",
    "weather": "chuva: Água que cai das nuvens; neve: Branca e gelada, boa para fazer bonecos; vento: Leva a pipa lá "
               "para cima; nuvem: Branca e fofinha no céu; tempestade: Tempo ruim com trovões; trovão: Um barulhão "
               "na tempestade; neblina: Não deixa ver longe; granizo: Bolinhas de gelo caindo do céu; geada: Deixa a "
               "grama branca nas manhãs frias; brisa: Um vento fraquinho; calor: Você sente num dia quente de verão; "
               "tornado: Um vento que gira muito rápido; garoa: Chuva bem fininha; poça: Pule nela depois da chuva; "
               "relâmpago: Um clarão na tempestade; frio: Pede casaco e cobertor; sol: Brilha num dia bonito",
    "sports": "futebol: Chute a bola no gol; tênis: Bata na bola por cima da rede com uma raquete; golfe: Coloque "
              "uma bolinha num buraco; hóquei: Jogado com um taco; rúgbi: Jogado com uma bola oval; patinação: "
              "Deslizar no gelo; esqui: Descer montanhas de neve deslizando; remo: Mover o barco com a força dos "
              "braços; boxe: Luta com luvas grandes; surfe: Andar nas ondas em uma prancha; beisebol: Bata na bola "
              "com um taco e corra pelas bases; natação: Mover-se dentro da água; corrida: Ir bem rápido com os "
              "pés; vôlei: Passe a bola por cima da rede com as mãos; basquete: Jogue a bola na cesta; gol: Faça um "
              "para ganhar; bola: Redonda, você chuta ou joga; time: Jogadores que jogam juntos; medalha: Prêmio "
              "para quem vence; judô: Luta com faixa e quimono",
    "autumn": "folha: Cai da árvore no outono; abóbora: Grande e laranja; colheita: Quando se recolhe o que "
              "plantou; maçã: Fruta colhida no outono; esquilo: Guarda nozes para o inverno; noz: O esquilo adora; "
              "vento: Faz as folhas voarem; galho: Parte da árvore que segura as folhas; árvore: Tem tronco e "
              "galhos; cogumelo: Nasce no chão úmido da floresta; espantalho: Assusta os passarinhos na plantação; "
              "casaco: Vestimos quando esfria; chuva: Água que cai das nuvens; marrom: A cor das folhas secas; "
              "vassoura: Varre as folhas do quintal; milho: Tem espiga e grãos amarelos; outono: Estação em que as "
              "folhas caem; bota: Calçado para pisar na lama; cachecol: Esquenta o pescoço",
    "halloween": "bruxa: Voa numa vassoura; fantasma: Lençol branco que diz buu; abóbora: Vira lanterna com cara "
                 "assustadora; morcego: Voa à noite e dorme de cabeça para baixo; vassoura: A bruxa voa nela; "
                 "caldeirão: Panela grande da bruxa; aranha: Tem oito patas e faz teia; teia: A aranha fica nela; "
                 "doce: As crianças pedem de porta em porta; fantasia: Roupa para se disfarçar; máscara: Cobre o "
                 "rosto; esqueleto: Feito só de ossos; múmia: Toda enrolada em faixas; vampiro: Tem dentes pontudos e "
                 "capa preta; lua: Brilha na noite escura; coruja: Pia à noite; poção: Bebida mágica da bruxa; chapéu: "
                 "O da bruxa é pontudo; gato: O da bruxa é preto",
    "winter": "neve: Branca e gelada; gelo: Água bem congelada; frio: Pede casaco e cobertor; floco: Cada pedacinho "
              "de neve; trenó: Desliza na neve; cachecol: Esquenta o pescoço; luva: Esquenta as mãos; gorro: "
              "Esquenta a cabeça; casaco: Roupa grossa para o frio; lareira: Fogo que esquenta a casa; chocolate: "
              "Quente, é bom no frio; pinguim: Ave que não voa e vive no gelo; esqui: Para deslizar na neve; "
              "patins: Para deslizar no gelo; iglu: Casa feita de gelo; inverno: A estação mais fria; cobertor: "
              "Esquenta a gente na cama; sopa: Tomada quente no prato fundo; pijama: Roupa de dormir",
    "spring": "flor: Cresce no jardim e cheira bem; borboleta: Inseto de asas coloridas; abelha: Visita as flores e "
              "faz mel; jardim: Lugar com plantas e flores; semente: Plantada, vira uma planta; broto: Planta bem "
              "novinha; ninho: Casa do passarinho; pássaro: Tem penas e canta; grama: Verde e cobre o chão; pétala: "
              "Parte colorida da flor; joaninha: Vermelha com bolinhas pretas; minhoca: Mora debaixo da terra; "
              "girassol: Flor amarela que segue o sol; tulipa: Flor em forma de copo; lagarta: Vira borboleta; "
              "primavera: A estação das flores; coelho: Tem orelhas compridas e pula; chuva: Ajuda as plantas a "
              "crescer; regador: Usado para molhar as plantas",
    "summer": "praia: Lugar com areia e mar; sol: Brilha forte no verão; mar: Água salgada com ondas; areia: Dá "
              "para fazer castelos com ela; sorvete: Gelado e doce; piscina: Lugar para nadar; férias: Dias sem "
              "aula; chapéu: Protege a cabeça do sol; óculos: Protegem os olhos do sol; calor: Faz a gente suar; "
              "toalha: Seca o corpo depois do banho; balde: Para carregar água e areia; onda: Quebra na praia; "
              "chinelo: Calçado de praia; picolé: Sorvete no palito; melancia: Verde por fora e vermelha por "
              "dentro; coco: Tem água dentro; pipa: Voa alto com o vento; verão: A estação mais quente",
}
THEMES_DE = {
    "animals": "Katze: Sagt miau; Hund: Bellt und wedelt mit dem Schwanz; Kuh: Gibt uns Milch; Pferd: Darauf kann "
               "man reiten; Schaf: Aus seiner Wolle macht man Pullis; Ente: Sagt quak; Frosch: Grün und hüpft; Eule: "
               "Ruft nachts uhu; Löwe: König der Tiere; Tiger: Große Katze mit Streifen; Zebra: Ein Pferd mit "
               "Streifen; Affe: Schwingt durch die Bäume; Hase: Hat lange Ohren und hoppelt; Maus: Klein und mag "
               "Käse; Elefant: Hat einen Rüssel; Giraffe: Hat einen sehr langen Hals; Schlange: Lang und ohne Beine; "
               "Bär: Groß, pelzig und mag Honig; Fisch: Schwimmt und hat Flossen; Biene: Macht Honig",
    "food": "Apfel: Eine rote oder grüne Frucht; Banane: Eine lange gelbe Frucht; Brot: Daraus macht man Toast; "
            "Käse: Mäuse lieben ihn; Butter: Kommt aufs Brot; Milch: Ein weißes Getränk von der Kuh; Pizza: Rund "
            "und mit Belag; Karotte: Ein oranges Gemüse; Suppe: Isst man heiß aus dem Teller; Kuchen: Hat Kerzen "
            "am Geburtstag; Honig: Bienen machen ihn; Reis: Kleine weiße Körner; Birne: Eine Frucht wie eine "
            "Glühbirne; Zitrone: Eine saure gelbe Frucht; Traube: Klein und wächst in Büscheln; Erbsen: Kleine "
            "grüne Kugeln; Marmelade: Kommt aufs Brötchen; Nudeln: Spaghetti sind welche",
    "space": "Sonne: Unser nächster Stern; Mond: Leuchtet in der Nacht; Stern: Funkelt am Himmel; Erde: Der "
             "Planet, auf dem wir leben; Mars: Der rote Planet; Rakete: Fliegt ins Weltall; Komet: Hat einen "
             "langen Schweif; Alien: Ein Besucher aus dem All; Saturn: Der Planet mit Ringen; Planet: Die Erde ist "
             "einer; Astronaut: Reist ins Weltall; Teleskop: Damit schaut man zu den Sternen; Galaxie: Milliarden "
             "von Sternen; Krater: Ein Loch auf dem Mond; Satellit: Kreist um die Erde",
    "ocean": "Welle: Rollt an den Strand; Muschel: Findest du am Strand; Krebs: Läuft seitwärts und hat Scheren; "
             "Wal: Das größte Tier im Meer; Hai: Ein Fisch mit scharfen Zähnen; Koralle: Daraus sind bunte Riffe; "
             "Krake: Hat acht Arme; Delfin: Ein kluges Meerestier, das springt; Robbe: Klatscht mit den Flossen; "
             "Sand: Daraus baust du Burgen; Seestern: Sieht aus wie ein Stern; Qualle: Wabbelig und kann brennen; "
             "Hummer: Wie ein großer Krebs mit langem Schwanz; Anker: Hält das Schiff fest; Boot: Schwimmt auf dem "
             "Wasser; Perle: Glänzt in einer Muschel; Salz: Macht Meerwasser komisch im Geschmack; Ebbe: Dann ist "
             "das Meer weit weg",
    "weather": "Regen: Wasser, das aus Wolken fällt; Schnee: Weiß und kalt, gut für Schneemänner; Wind: Lässt "
               "Drachen steigen; Wolke: Weiß und flauschig am Himmel; Sturm: Sehr starker Wind; Sonnig: Wenn die "
               "Sonne scheint; Donner: Ein lauter Knall beim Gewitter; Nebel: Dann sieht man nicht weit; Hagel: "
               "Kleine Eiskugeln fallen herab; Frost: Macht das Gras an kalten Morgen weiß; Regenbogen: Sieben "
               "Farben am Himmel; Brise: Ein sanfter Wind; Hitze: Spürst du an heißen Sommertagen; Tornado: Ein "
               "Wind, der sich schnell dreht; Schirm: Hält dich im Regen trocken; Pfütze: Da springst du nach dem "
               "Regen hinein; Blitz: Ein heller Strahl beim Gewitter",
    "sports": "Fußball: Schieß den Ball ins Tor; Tennis: Schlag den Ball mit dem Schläger übers Netz; Golf: Schlag "
              "einen kleinen Ball ins Loch; Hockey: Man spielt mit einem Schläger; Rugby: Man spielt mit einem "
              "eiförmigen Ball; Eislauf: Gleiten auf dem Eis; Ski: Damit fährst du den Berg hinab; Rudern: Ein Boot "
              "mit Rudern bewegen; Boxen: Kämpfen mit dicken Handschuhen; Surfen: Auf Wellen reiten; Turnen: Rolle "
              "und Handstand; Reiten: Sport auf dem Pferd; Tauchen: Unter Wasser schwimmen; Laufen: Schnell auf den "
              "Füßen sein; Schwimmen: Sich im Wasser bewegen; Tor: Triff es, um zu gewinnen; Ball: Rund, du kickst "
              "oder wirfst ihn; Team: Spieler, die zusammen spielen; Medaille: Ein Preis für den Sieg",
    "autumn": "Blatt: Wird im Herbst bunt und fällt; Kastanie: Braun und glänzend in einer stacheligen Schale; "
              "Eichel: Die Frucht der Eiche; Pilz: Wächst im Wald und hat einen Hut; Drachen: Lässt du im Wind "
              "steigen; Kürbis: Groß, rund und orange; Igel: Hat Stacheln und sucht ein Laubnest; Nebel: Morgens "
              "grau und dicht; Ernte: Dann holt man das Obst vom Feld; Nuss: Hat eine harte Schale; Apfel: Hängt "
              "reif am Baum; Wind: Weht die Blätter weg; Regen: Macht Pfützen; Laterne: Leuchtet beim Martinsumzug; "
              "Stiefel: Damit springst du in Pfützen; Schal: Wärmt deinen Hals",
    "halloween": "Kürbis: Wird ausgehöhlt und leuchtet; Hexe: Fliegt auf einem Besen; Geist: Weiß und sagt huh; Besen: "
                 "Damit fegt man oder fliegt; Kessel: Darin braut die Hexe; Spinne: Hat acht Beine; Fledermaus: Fliegt "
                 "nachts und hängt kopfüber; Kerze: Gibt Licht mit einer Flamme; Maske: Versteckt dein Gesicht; Mond: "
                 "Leuchtet hell in der Nacht; Eule: Ruft nachts uhu; Katze: Oft schwarz bei Hexen; Vampir: Hat spitze "
                 "Zähne; Monster: Ein Ungeheuer; Kostüm: Verkleidung für das Fest; Skelett: Nur Knochen; Nacht: Dann "
                 "ist es dunkel; Zauber: Hexen sprechen ihn",
    "winter": "Schnee: Weiße Flocken fallen vom Himmel; Eis: Gefrorenes Wasser; Schlitten: Damit fährst du den Hang "
              "hinab; Schal: Wärmt deinen Hals; Mütze: Wärmt deinen Kopf; Flocke: Ein Stück Schnee; Kamin: Darin "
              "brennt ein Feuer; Tee: Ein heißes Getränk; Pinguin: Ein Vogel, der nicht fliegt; Eisbär: Ein weißer "
              "Bär am Nordpol; Iglu: Ein Haus aus Schnee; Eiszapfen: Hängt spitz vom Dach; Ski: Damit gleitest du "
              "über Schnee; Kakao: Heiße Schokolade zum Trinken; Decke: Hält dich warm im Bett; Frost: Macht die "
              "Fenster weiß; Stiefel: Warme Schuhe für den Schnee",
    "spring": "Blume: Blüht bunt im Garten; Tulpe: Eine Blume mit Kelch; Knospe: Daraus wird eine Blüte; Vogel: "
              "Singt und baut ein Nest; Nest: Darin liegen Vogeleier; Küken: Ein kleines gelbes Huhn; Lamm: Ein "
              "junges Schaf; Hase: Bringt die Ostereier; Biene: Summt von Blüte zu Blüte; Regen: Lässt die Pflanzen "
              "wachsen; Sonne: Wärmt die Erde; Garten: Dort wachsen Blumen; Gras: Grün auf der Wiese; Wiese: Eine "
              "Fläche voller Gras; Ostern: Fest mit bunten Eiern; Samen: Daraus wächst eine Pflanze",
    "summer": "Sonne: Scheint heiß am Himmel; Strand: Dort liegt Sand am Meer; Meer: Viel salziges Wasser; Sand: "
              "Daraus baust du Burgen; Eis: Kalt und süß in der Waffel; Urlaub: Freie Zeit zum Reisen; Hitze: Dann "
              "schwitzt du; Welle: Rollt an den Strand; Muschel: Findest du am Strand; Zelt: Darin schläft man beim "
              "Camping; Picknick: Essen auf einer Decke im Freien; Ferien: Keine Schule; Melone: Grün außen und rot "
              "innen; Erdbeere: Eine rote Beere; Grillen: Würstchen über Glut braten; Boot: Schwimmt auf dem "
              "Wasser; Badehose: Ziehst du zum Schwimmen an",
}
THEMES_IT = {
    "animals": "gatto: Fa miao; cane: Abbaia e scodinzola; mucca: Ci dà il latte; cavallo: Ci si può andare in "
               "groppa; pecora: Con la sua lana si fanno i maglioni; anatra: Fa qua qua; rana: Verde e salta; gufo: "
               "Di notte fa uh uh; leone: Il re degli animali; tigre: Un grande gatto a strisce; zebra: Un cavallo "
               "a strisce; scimmia: Si dondola sugli alberi; coniglio: Ha le orecchie lunghe e saltella; topo: "
               "Piccolo e ama il formaggio; elefante: Ha la proboscide; giraffa: Ha il collo lunghissimo; serpente: "
               "Lungo e senza zampe; orso: Grande, peloso e ama il miele; pesce: Nuota e ha le pinne; ape: Fa il miele",
    "food": "mela: Un frutto rosso o verde; banana: Un frutto lungo e giallo; pane: Si compra dal fornaio; "
            "formaggio: I topi lo adorano; burro: Si spalma sul pane; latte: Una bevanda bianca della mucca; pizza: "
            "Rotonda, con pomodoro e mozzarella; carota: Un ortaggio arancione; minestra: Si mangia calda nel "
            "piatto fondo; torta: Ha le candeline al compleanno; miele: Lo fanno le api; riso: Piccoli chicchi "
            "bianchi; pera: Un frutto a forma di lampadina; limone: Un frutto giallo e aspro; uva: Cresce a "
            "grappoli; piselli: Palline verdi; marmellata: Si spalma sulle fette biscottate; pasta: Gli spaghetti "
            "lo sono; gelato: Freddo e dolce, in coppetta o cono",
    "space": "sole: La stella più vicina a noi; luna: Brilla di notte; stella: Luccica nel cielo; terra: Il pianeta "
             "dove viviamo; marte: Il pianeta rosso; razzo: Vola nello spazio; cometa: Ha una lunga coda; alieno: Un "
             "visitatore dallo spazio; saturno: Il pianeta con gli anelli; pianeta: La Terra è uno di loro; "
             "astronauta: Viaggia nello spazio; telescopio: Serve a guardare le stelle; galassia: Miliardi di "
             "stelle insieme; cratere: Un buco sulla Luna; satellite: Gira intorno alla Terra; orbita: Il giro "
             "intorno a un pianeta",
    "ocean": "onda: Arriva sulla spiaggia; conchiglia: La trovi sulla spiaggia; granchio: Cammina di lato e ha le "
             "chele; balena: L'animale più grande del mare; squalo: Un pesce con denti aguzzi; corallo: Forma le "
             "barriere colorate; polpo: Ha otto tentacoli; delfino: Un animale marino intelligente che salta; foca: "
             "Batte le pinne; sabbia: Ci costruisci i castelli; stella: Quella marina ha cinque punte; medusa: "
             "Molle e può pungere; aragosta: Ha le chele e una lunga coda; ancora: Tiene ferma la nave; barca: "
             "Galleggia sull'acqua; perla: Brilla dentro un'ostrica; sale: Rende salata l'acqua del mare; marea: "
             "Fa salire e scendere il mare",
    "weather": "pioggia: Acqua che cade dalle nuvole; neve: Bianca e fredda, ottima per i pupazzi; vento: Fa volare "
               "gli aquiloni; nuvola: Bianca e soffice nel cielo; tempesta: Vento fortissimo e pioggia; sole: "
               "Splende quando è bel tempo; tuono: Il botto del temporale; nebbia: Non si vede lontano; grandine: "
               "Palline di ghiaccio che cadono; brina: Rende bianca l'erba nelle mattine fredde; arcobaleno: Sette "
               "colori nel cielo; brezza: Un vento leggero; caldo: Lo senti nei giorni d'estate; tornado: Un vento "
               "che gira velocissimo; ombrello: Ti tiene asciutto quando piove; pozzanghera: Ci salti dentro dopo "
               "la pioggia; fulmine: Una luce forte nel temporale",
    "sports": "calcio: Tira la palla in porta; tennis: Colpisci la palla con la racchetta sopra la rete; golf: "
              "Manda una pallina in una buca; hockey: Si gioca con una mazza; rugby: Si gioca con una palla ovale; "
              "pattinaggio: Scivolare sul ghiaccio; sci: Per scendere dalla montagna sulla neve; canottaggio: "
              "Muovere una barca con i remi; pugilato: Si combatte con guantoni imbottiti; surf: Cavalcare le onde; "
              "ginnastica: Capriole e salti sul tappeto; nuoto: Muoversi nell'acqua; corsa: Andare più veloce che "
              "puoi; vela: Il vento spinge la barca; pallavolo: Si passa la palla sopra la rete con le mani; "
              "ciclismo: Si fa in bicicletta; karate: Un'arte marziale giapponese; danza: Muoversi a ritmo di musica",
    "autumn": "autunno: La stagione dopo l'estate; foglia: Cade dagli alberi; castagna: Si mangia arrostita; "
              "ghianda: Il frutto della quercia; fungo: Cresce nel bosco dopo la pioggia; zucca: Grande e "
              "arancione; riccio: Animale con gli aculei; bosco: Tanti alberi insieme; nebbia: Nuvola bassa che "
              "copre tutto; pioggia: Cade dalle nuvole; vento: Fa volare le foglie; raccolto: Si fa nei campi a "
              "fine estate; noce: Ha il guscio duro; albero: Ha il tronco e i rami; stivali: Per saltare nelle "
              "pozzanghere; sciarpa: Tiene caldo il collo; vendemmia: Si raccoglie l'uva; ottobre: Il decimo mese",
    "halloween": "zucca: Ci si intaglia una faccia; strega: Vola su una scopa; fantasma: Un lenzuolo che fa buu; "
                 "scopa: La strega ci vola sopra; calderone: Grande pentola della strega; ragno: Ha otto zampe; "
                 "pipistrello: Vola di notte e dorme a testa in giù; candela: Fa luce dentro la zucca; maschera: "
                 "Copre il viso; luna: Splende di notte; gufo: Uccello notturno; gatto: Quello della strega è nero; "
                 "vampiro: Ha i canini lunghi; mostro: Una creatura spaventosa; costume: Lo indossi per "
                 "travestirti; caramelle: Dolcetti per chi bussa; castello: Ci abitano i fantasmi; notte: È buio; "
                 "scheletro: Tutte ossa; mummia: Avvolta nelle bende",
    "winter": "neve: Fiocchi bianchi che cadono; ghiaccio: Acqua diventata dura; slittino: Per scivolare giù dalla "
              "collina; sciarpa: Si avvolge intorno al collo; berretto: Tiene calda la testa; guanti: Tengono "
              "calde le mani; fiocco: Un pezzetto di neve; camino: Ci brucia il fuoco; pinguino: Un uccello che "
              "non vola; pupazzo: Quello di neve ha il naso di carota; igloo: Una casa di ghiaccio; ghiacciolo: "
              "Pende dal tetto; sci: Per scendere sulla neve; inverno: La stagione più fredda; coperta: Ti tiene "
              "caldo a letto; cioccolata: Bevanda calda e dolce; dicembre: Il mese di Natale; freddo: Ti fa "
              "tremare",
    "spring": "primavera: La stagione dei fiori; fiore: Sboccia in giardino; tulipano: Un fiore a forma di coppa; "
              "nido: La casa degli uccellini; uovo: Da qui nasce il pulcino; pulcino: Piccolo e giallo; agnello: "
              "Il cucciolo della pecora; coniglio: Ha le orecchie lunghe; ape: Ronza di fiore in fiore; pioggia: "
              "Aiuta le piante a crescere; giardino: Ci crescono i fiori; erba: Verde e copre il prato; "
              "coccinella: Rossa con i puntini neri; bruco: Diventerà farfalla; seme: Da qui nasce una pianta; "
              "farfalla: Ha ali colorate; arcobaleno: Esce dopo la pioggia; margherita: Fiore bianco con il "
              "centro giallo",
    "summer": "estate: La stagione più calda; sole: Splende in cielo; spiaggia: Ci si va al mare; mare: Acqua "
              "salata e onde; sabbia: Ci costruisci i castelli; gelato: Freddo e dolce; vacanze: Niente scuola; "
              "costume: Lo metti per fare il bagno; onda: Arriva sulla riva; conchiglia: La raccogli sulla "
              "spiaggia; tenda: Per dormire in campeggio; picnic: Si mangia sul prato; nuoto: Muoversi "
              "nell'acqua; cappello: Ripara la testa dal sole; occhiali: Quelli da sole proteggono gli occhi; "
              "anguria: Frutto verde fuori e rosso dentro; secchiello: Si riempie di sabbia; ombrellone: Fa ombra "
              "in spiaggia",
}
THEMES_NL = {
    "animals": "kat: Zegt miauw; hond: Blaft en kwispelt; koe: Geeft ons melk; paard: Daar kun je op rijden; "
               "schaap: Van zijn wol maak je truien; eend: Zegt kwak; kikker: Groen en springt; uil: Roept 's nachts "
               "oehoe; leeuw: Koning van de dieren; tijger: Grote kat met strepen; zebra: Een paard met strepen; "
               "aap: Slingert door de bomen; konijn: Heeft lange oren en huppelt; muis: Klein en houdt van kaas; "
               "olifant: Heeft een slurf; giraf: Heeft een heel lange nek; slang: Lang en zonder poten; beer: Groot, "
               "harig en dol op honing; vis: Zwemt en heeft vinnen; bij: Maakt honing",
    "food": "appel: Rood of groen en groeit aan een boom; banaan: Geel en krom; brood: Daar maak je boterhammen "
            "van; kaas: Geel, en Nederland is er beroemd om; melk: Wit drinken van de koe; ei: Komt van de kip; "
            "soep: Eet je warm uit een kom; pizza: Rond, met tomaat en kaas; taart: Eet je op je verjaardag; "
            "wortel: Oranje groente die konijnen lusten; peer: Fruit dat onderaan dik is; druif: Klein, rond fruit "
            "aan een tros; citroen: Geel en heel zuur; honing: Zoet en gemaakt door bijen; rijst: Kleine witte "
            "korrels; tomaat: Rood en rond, voor in de salade; aardbei: Rood fruit met pitjes aan de buitenkant; "
            "pannenkoek: Plat en rond, uit de koekenpan",
    "space": "zon: Onze dichtstbijzijnde ster; maan: Schijnt 's nachts aan de hemel; ster: Twinkelt in de nacht; "
             "aarde: De planeet waar wij wonen; mars: De rode planeet; raket: Vliegt de ruimte in; astronaut: "
             "Reist naar de ruimte; komeet: Heeft een lange staart van ijs en stof; planeet: Draait om de zon; "
             "saturnus: Planeet met mooie ringen; jupiter: De grootste planeet; krater: Een gat in de maan; "
             "telescoop: Daarmee kijk je naar de sterren; satelliet: Draait om de aarde; melkweg: Ons sterrenstelsel; "
             "meteoor: Een vallende ster",
    "ocean": "golf: Rolt naar het strand; schelp: Vind je op het strand; krab: Loopt zijwaarts en heeft scharen; "
             "walvis: Het grootste dier in de zee; haai: Een vis met scherpe tanden; koraal: Daar zijn kleurige "
             "riffen van; octopus: Heeft acht armen; dolfijn: Een slim zeedier dat springt; zeehond: Ligt graag op "
             "een zandbank; zand: Daar bouw je kastelen van; zeester: Lijkt op een ster; kwal: Doorzichtig en kan "
             "prikken; kreeft: Rood als hij gekookt is; anker: Houdt het schip op zijn plek; boot: Drijft op het "
             "water; parel: Glanst in een oester; zout: Daarom smaakt zeewater vies; eb: Dan staat het water laag",
    "weather": "regen: Water dat uit de wolken valt; sneeuw: Witte vlokken in de winter; wind: Laat de vlieger "
               "vliegen; wolk: Wit of grijs, hoog in de lucht; zon: Maakt het warm en licht; storm: Heel harde wind; "
               "donder: Het gerommel na de bliksem; bliksem: Een felle flits tijdens onweer; mist: Dan kun je niet "
               "ver kijken; hagel: Kleine ijsballetjes uit de lucht; vorst: Dan bevriest het water; regenboog: "
               "Kleurige boog in de lucht; paraplu: Houdt je droog als het regent; ijzel: Maakt de weg spiegelglad; "
               "dauw: Druppeltjes op het gras in de ochtend; thermometer: Meet hoe warm het is; orkaan: Een enorme "
               "storm",
    "sports": "voetbal: Je schopt de bal in het doel; tennis: Sla de bal met een racket over het net; zwemmen: Dat "
              "doe je in het water; schaatsen: Glijden over het ijs; fietsen: Trappen op twee wielen; hockey: Met "
              "een stick en een kleine bal; judo: Een vechtsport in een wit pak; turnen: Salto's en de evenwichtsbalk; "
              "dansen: Bewegen op muziek; roeien: Met riemen door het water; zeilen: De wind duwt je boot vooruit; "
              "basketbal: Gooi de bal door de ring; golf: Sla een balletje in een holletje; skiën: Van een besneeuwde "
              "berg glijden; surfen: Op een plank over de golven; korfbal: Gooi de bal in de korf; hardlopen: Zo "
              "snel mogelijk rennen; scheidsrechter: Fluit bij een overtreding; medaille: Krijg je als je wint",
    "autumn": "herfst: Het seizoen van vallende bladeren; blad: Valt in de herfst van de boom; kastanje: Bruin en "
              "glanzend, uit een stekelig bolster; eikel: Groeit aan een eik; paddenstoel: Groeit in het bos, "
              "soms met stippen; pompoen: Grote oranje vrucht; egel: Heeft stekels en zoekt een plek om te slapen; "
              "eekhoorn: Verzamelt nootjes voor de winter; regen: Valt in de herfst heel vaak; wind: Blaast de "
              "bladeren weg; laarzen: Trek je aan om in plassen te stampen; sjaal: Houdt je nek warm; vlieger: Gaat "
              "omhoog als het waait; noot: Heeft een harde dop; oogst: Dan worden appels en graan geplukt; mist: "
              "Grijze wolk dicht bij de grond; lantaarn: Daarmee loop je met Sint-Maarten",
    "halloween": "pompoen: Daar snijd je een gezicht in; heks: Vliegt op een bezem; spook: Een wit laken met gaten; "
                 "bezem: Daar vliegt de heks op; ketel: Daar roert de heks haar soep in; spin: Heeft acht poten en "
                 "maakt een web; vleermuis: Hangt ondersteboven en vliegt 's nachts; kaars: Geeft licht in de "
                 "pompoen; masker: Verbergt je gezicht; maan: Schijnt in de donkere nacht; uil: Roept oehoe in de "
                 "nacht; kat: Een zwarte hoort bij een heks; vampier: Heeft lange hoektanden; monster: Eng wezen uit "
                 "een verhaal; kostuum: Trek je aan om je te verkleden; snoep: Krijg je aan de deur; skelet: Al je "
                 "botten bij elkaar; kasteel: Een oud gebouw met torens",
    "winter": "sneeuw: Witte vlokken uit de lucht; ijs: Bevroren water; slee: Daarmee glij je van een heuvel; sjaal: "
              "Houdt je nek warm; muts: Zet je op tegen de kou; want: Een handschoen zonder vingers; sneeuwpop: Heeft "
              "een wortel als neus; schaatsen: Daarmee rijd je op het ijs; ijsbeer: Wit dier op de Noordpool; "
              "pinguïn: Vogel die niet vliegt maar wel zwemt; iglo: Een huis van sneeuw; ijspegel: Hangt aan het "
              "dak en druppelt; haard: Daar brandt het vuur; deken: Daar kruip je onder; kerst: Feest met een "
              "versierde boom; vorst: Dan bevriest alles; chocolademelk: Warm, bruin en zoet drinken",
    "spring": "lente: Het seizoen na de winter; bloem: Groeit en ruikt lekker; tulp: Bekende bloem uit Nederland; "
              "knop: Daar komt een blad of bloem uit; vogel: Bouwt een nest en zingt; nest: Daar legt een vogel haar "
              "eieren in; ei: Daar komt een kuiken uit; kuiken: Klein geel pluisje; lam: Jong schaap; bij: Vliegt "
              "van bloem naar bloem; rups: Wordt later een vlinder; vlinder: Heeft kleurige vleugels; regen: Laat "
              "de planten groeien; tuin: Daar plant je bloemen; gras: Groen en moet gemaaid worden; pasen: Feest met "
              "gekleurde eieren; zaadje: Daar groeit een plant uit; narcis: Gele voorjaarsbloem",
    "summer": "zomer: Het warmste seizoen; zon: Schijnt fel aan de hemel; strand: Zand bij de zee; zee: Groot zout "
              "water; zand: Daar bouw je een kasteel van; ijsje: Koud en lekker op een hoorntje; vakantie: Geen "
              "school, op reis!; zwembad: Daar kun je zwemmen en duiken; schelp: Vind je op het strand; tent: Daar "
              "slaap je in op de camping; picknick: Eten op een kleed in het gras; zonnebril: Beschermt je ogen; "
              "meloen: Groot sappig fruit; aardbei: Rood zomerfruit; barbecue: Daarop grill je worstjes; boot: "
              "Vaart over het water; zonnebrand: Smeer je op tegen verbranden",
}
THEMES_BY_LANGUAGE = {"es": THEMES_ES, "fr": THEMES_FR, "pt": THEMES_PT, "de": THEMES_DE, "it": THEMES_IT, "nl": THEMES_NL}
THEME_NAMES = {"animals": "Animals", "food": "Food", "space": "Space", "ocean": "Ocean", "weather": "Weather",
               "sports": "Sports", "autumn": "Autumn", "halloween": "Halloween", "winter": "Winter", "spring": "Spring",
               "summer": "Summer", "custom": "Your own words and clues"}
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
