<!-- translated from bef7b2c650cb -->
# Een sessie spelen

Hoe een spel via Didact verloopt: het LLM vertelt, en Didact bewaart elk feit, elke worp en elke wijziging.

## Voor de eerste sessie

```
didact world new vale --system my-system       # the system it plays, for good
didact campaign new withering                  # then: didact session zero
didact campaign profile role=gm tone=grim 'lines+=spiders' dice=didact
didact new pc Freya --fill                     # rolls what the system rolls, through the log
didact party add old-gannet --as hireling
```

Een wereld houdt het systeem waarmee ze gemaakt is, en haar campagnes worden ermee gespeeld: een ander systeem wordt in een eigen wereld gespeeld. `didact campaign close` legt een campagne weg (haar wereld blijft geopend) en `didact campaign open <id>` pakt haar weer op waar ze gebleven was, met sessie en al.

`didact world delete <id>` en `didact campaign delete <id>` verwijderen er een, eerst met een voorbeeld; `--yes` verwijdert, en `didact undo` haalt alles terug.

`session zero` toont de vragen die je met de speler afspreekt. Die van het pakket komen eerst. Daaronder vallen de opties van het systeem (zijn varianten en optionele regels): zijn regels volgen de antwoorden, en de briefing zegt wat elke gewijzigde optie betekent. Elke briefing bevat de antwoorden.

## Een sessie

```
didact session start                           # shows the brief: time, place, party, what's due
didact scene new 'Amber Grave' --expected 'a quiet pool of sap'
didact do save who=freya attr=DEX              # a rule: rolled, logged, consequences applied
didact set freya hp-=2                         # sheet changes are checked, clamped, hooked
didact log result 'The sap holds her fast'     # one beat per thing that happened
didact scene end --summary 'Freya reached the crystal.'
didact session end --summary '…'               # or later: didact summary due
```

- **Beurten:** elk bericht van de speler opent een beurt (de Claude Code-hook roept `didact capture` aan, andere clients gebruiken `turn begin`). `didact undo --turn` draait alles terug wat voor dat bericht gedaan is: wijzigingen, gebeurtenissen en worpen. Het transcript bewaart het.
- **Terugspringen:** `didact undo --to e40` draait alles na #e40 terug, nieuwste eerst (`--dry-run` toont het): elke wijziging wordt ongedaan gemaakt en elke worp als ongedaan gemarkeerd. Er wordt niets verwijderd: `redo`, of terugspringen naar een latere wijziging, haalt het terug.
- **Tijd:** `didact time advance 1 watch` laat timers aflopen, haalt herinneringen naar boven en voert tijdtriggers uit. `didact remind --list` toont de komende herinneringen, en `didact remind --cancel 2` schrapt er een. Een campagne begint op het begin van de kalender, of op de datum die `campaign new --date '4 July 1902'` geeft, en `didact time set '<date>'` verandert hem tot de eerste sessie.
- **Plaatsen:** `didact visit <place>` verplaatst de groep en markeert de plaats als bezocht. `didact map` toont wat de groep kent, en een onverkende uitgang is `?`.
- **Gevechten:** `didact combat start --party troll`, dan `combat next`, `combat hit freya troll weapon=d8` en `combat end`. Vechters komen en gaan midden in een gevecht: `didact combat join wolf-2` (in de individuele modus gooien ze initiatief) en `didact combat leave troll --why fled`. Niemands beurt wordt overgeslagen.
- **Dingen:** `didact inv add freya Rope Longsword`, `inv use freya torch`, `inv move freya rope ansel` (of in een kist, of op een plaats); `didact where rope` vindt het. `inv add` vindt een compendiumvoorwerp via zijn id, zijn naam of een alias.
- **Je notities:** `didact about sweeney plan='…' doing='…' where='…'` bewaart wat je over iemand of iets hebt besloten. Spelers zien alleen `looks`. `didact log … --about sweeney` zet een gebeurtenis op diens item (`--secret` als de spelers het niet zien). `didact guide details` vertelt meer.
- **De wereld gaat door:** `didact faction turn`, plus klokken: `didact track new 'The flood' --size 6`. Een opdracht die maar één soort item aanneemt, neemt een naam die andere delen als die soort: `didact track roll draugr` gooit de pool die naar een vijand heet (net zo `track tick` een teller, `quest done` een quest en `visit` een plaats).

## Orakels, generatoren en personages

```
didact ask 'Is the ferryman home?' --odds likely        # #o3 ? … → Yes, but…
didact interpret o3 'Home, but drunk and grieving.'     # what it meant, kept with it
didact meaning                                          # two words to interpret: betray · oath
didact gen run pointcrawl --prefill '{"terrain": "Swamp"}' --auto   # a draft: #g4
didact gen edit g4 poi-1.name='Amber Grave'
didact gen commit g4
didact char new                                         # guided: answer with `char choose c5 …`
didact char back c5                                     # take the last answer back: ask it again
didact char new --mode random --prefill '{"name": "Wren", "background": "Cutpurse"}'
didact char advance wren                                # the system's level-up, step by step (#c6)
didact world new fenmoor --system my-system --gen <generator> --prefill '{…}'
```

Niets wat een generator of het maken van een personage oplevert, wordt weggeschreven vóór `commit`. Beschrijf in `--prefill` wat de speler wil, en de procedure vult de gaten. Een vraag toont wat elke optie betekent als het pakket dat zegt (`- Cutpurse: …`): vertel het de speler, zodat die bij het kiezen weet wat hij krijgt.

## Geheimen

Weergaven zijn standaard veilig voor spelers: `show`, `find`, `sheet`, `map`, `brief`. Ze laten weg:
- geheime items (`knowledge: secret`);
- de secties `## Secrets` en `## GM notes`;
- velden met `secret: true`.

`--gm` toont alles. Als de spelers iets te weten komen:

```
didact reveal loc:hidden-vault                 # the record becomes known
didact reveal sweeney 'Anglwyst'               # that secret line moves to ## Revealed
didact reveal loc:drowned-tower --rumor        # heard of, not confirmed
```

`didact export --as site --to ~/Desktop/withering-site` schrijft wat de spelers weten weg als een kleine website om te delen of op een telefoon te lezen: de groep, een pagina per item, het logboek en de kaart. Die is altijd veilig voor spelers, en opnieuw exporteren naar die map werkt hem bij. `didact export --as lonelog` schrijft het logboek in Lonelog-notatie (`@ ? d: -> =>`, scènes als `S1`, tags zoals `[N:Sweeney]`), ook veilig voor spelers.

## Lore: wat terugkomt als iets genoemd wordt

```
didact lore add 'Sweeney owes the river witch a debt.' --keys 'sweeney, river witch'
didact lore add 'Torches burn 3 uses.' --keys torch --kind rule-reminder --scope system
didact lore scan 'Freya asks Sweeney about the wolves'     # cards, lore and rulings, best first
didact lore explain lore:sweeney-owes-the-river 'we meet Sweeney'
```

- **Wat telt:** elke NPC, plaats, elk voorwerp en elke factie is een kaart met de naam en aliassen als sleutels. Lore-items hebben `keys`, en uitspraken komen naar boven via hun regel. Er wordt op hele woorden gezocht, en meervouden tellen mee (“wolves” past bij `wolf`).
- **Wanneer lore naar boven komt:** de Claude Code-hook doorzoekt elk bericht van de speler. Ook `log`, `scene new` en `show` brengen nieuw getriggerde lore mee, en een item wordt een paar beurten niet herhaald.
- **Een item afstellen:** `--secondary` met `--logic`, `--priority`, `--group`, `--probability`, `--sticky`/`--cooldown`/`--delay` (in beurten of scènes), `--constant` (altijd in de briefing) en `--no-recurse`.
- **Bereiken:** items horen bij de campagne, tenzij `--scope` world, system of global zegt. Een scan ziet alleen deze campagne, haar wereld, haar systeem en global, nooit een andere wereld. Een smaller item met dezelfde id overschaduwt een breder item.
- **Lorebooks van andere tools:** `didact lore import <file>` leest SillyTavern World Info (ook die van KoboldAI), het lorebook van een personagekaart en het `.lorebook` van NovelAI; `didact lore export --to <file>` schrijft World Info. Trefwoorden, logica, prioriteit, kans, groepen en timing gaan mee.

## Het verhaal veranderen

- `didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret` verandert het feit maar bewaart de oude waarde. Het markeert ook samenvattingen die Sweeney noemen als verouderd, en `audit` toont het.
- `didact ruling add '<question>' '<ruling>' --rule <rule>` legt een uitspraak vast. Die verschijnt dan in `rules lookup` en wanneer die regel wordt uitgevoerd.
- `didact name npc` gooit een nieuwe naam, nooit een die de wereld al gebruikt. Controleer een naam met `didact names check <name>` voordat je er een verzint. `didact names forget <name>` geeft er weer een vrij.

## Opruimen

- `didact history --clear` toont wat het wissen van oude geschiedenis zou weggooien; `--yes` gooit het voorgoed weg, verwijderde items inbegrepen, en ongedaan maken, `diff`, `rewind` en oudere herstelpunten kunnen er niet meer bij (`--before e120` bewaart die gebeurtenis en latere, `--rolls` gooit ook de dobbelsteenlog weg). Voer eerst `didact snapshot` uit.
- `didact save --remove 'before the dragon'` verwijdert een herstelpunt; `didact undo` haalt het terug.
- `didact transcript 3 --clear` verwijdert het transcript van sessie 3 (`--clear --all`: dat van elke sessie). `didact undo` haalt het terug, en de tekst blijft in de geschiedenis tot `history --clear`.
- `didact compendium remove <entry>` verwijdert een item dat jij hebt toegevoegd; items die ermee zijn gemaakt blijven.
- `didact snapshot --keep 3` verwijdert alle back-ups behalve de nieuwste drie, en `didact snapshot --remove <name>` verwijdert er een. Geen van beide kan ongedaan worden gemaakt.
- `didact session end` maakt vanzelf een back-up van de bibliotheek (`snapshot-<time>-auto.zip`) en bewaart daarvan de nieuwste vijf; `didact snapshot --list` markeert ze.
- `didact reset` toont wat het leegmaken van de bibliotheek zou meenemen; `--yes` maakt haar als nieuw geïnstalleerd: elke wereld, campagne en elk item, de geschiedenis en de zoekindex verdwijnen, en de volgende wijziging is weer #e1. Eerst wordt er een back-up van de bibliotheek gemaakt (`…-before-reset.zip`), en de back-ups blijven, net als geïnstalleerde pakketten, tenzij `--packs`. Om Didact in plaats daarvan op een kant-en-klare campagne uit te proberen, bouwt `didact sample` de voorbeeldcampagne in een lege bibliotheek (`--home` geeft haar een eigen map), en `didact serve --demo` serveert haar telkens vers.
- `didact snapshot --restore <name>` toont wat een back-up bevat naast de huidige bibliotheek; `--yes` maakt een back-up van de bibliotheek zoals ze is (`…-before-restore.zip`) en zet daarna de back-up op haar plaats. Gebeurtenis- en worpnummers lopen door. Ongedaan maken kan een herstel niet terugdraaien: die veiligheidsback-up herstellen wel.
