<!-- translated from b1dfa1159ff4 -->
# Pakketten

Een pakket is een spelsysteem, orakel, setting, avontuur of supplement, geschreven als YAML-bestanden plus een optionele Python-plugin. Deze gids laat zien hoe je er een schrijft: een regelboek omzetten in een pakket, of eigen huisinhoud toevoegen.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Een pakket kun je ook maken uit wat er in je bibliotheek staat. `didact pack new my-brew --from-overlay my-system` maakt van je homebrew voor een systeem (`compendium add`, items bewaard met `--scope system`, lore) een supplement, en `didact world export --as setting` maakt van een wereld een settingpakket: haar personen, plaatsen en lore als compendium-items en pakketlore, die je met `compendium import` naar een andere wereld haalt. Beide laten geheimen en de SL-notities weg, tenzij `--secrets`, en geen van beide is als deelbaar gemarkeerd tot je de licentie instelt.

## Opbouw

```
my-hack/
  pack.yaml        id, name, kind, version, requires, extends, license, plugins, settings
  GUIDE.md         how to run it: an LLM reads this first
  dice.yaml        named dice, macros, dice chains
  schemas/         record types and their fields (sheets)
  tables/          random and lookup tables, decks, bags
  rules/           checks, actions, procedures, triggers
  compendium/      monsters, items, spells, backgrounds…
  reference/       the rules text, one short section per file (Markdown)
  glossary.yaml    terms and definitions
  tests/           examples `pack test` runs
  plugins/         Python, for what YAML can't express (off until trusted)
```

Een bestand bevat één element, een lijst van elementen, of meerdere elementen gescheiden door `---`. Elk element noemt zijn id met de sleutel van zijn soort: `table: weather`, `check: save`, `type: pc`, of `id: troll` voor compendiumitems. Verwijs naar elementen als `pack.id` (`my-system.save`), of met alleen de id als maar één ingeschakeld pakket die heeft.

```yaml
# pack.yaml
id: my-hack
name: My Hack
kind: system                 # system | oracle | supplement | setting | adventure
version: 0.1.0
alias: hack                  # the name in expressions: hack.attack(d8, d8)
requires: {didact: ">=0.1", packs: [core]}
extends: []                  # for a hack: [my-system]; same-id items replace the base's
license: {spdx: CC-BY-SA-4.0, redistributable: true, attribution: "…"}
settings: {torch_uses: 3}    # rules read these as @settings.torch_uses
```

Een hack noemt zijn basis in `extends` en bevat alleen wat afwijkt:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Zijn element met hetzelfde id vervangt dat van de basis, van welke soort ook (een tabel, een regel, een compendiumitem, een naslagsectie, een woordenlijstterm). Zijn `settings` komen sleutel voor sleutel bovenop die van de basis: een sleutel die hij instelt, vervangt de waarde van de basis volledig (zijn `names`-tabellen komen in de plaats van die van de basis), en de regels van de basis lezen ook de waarden van de hack. `hides` laat weg wat overblijft en wat de hack niet nodig heeft: `*` komt overeen met elke reeks tekens, het laatste patroon dat met een id overeenkomt beslist, en een patroon dat met `!` begint behoudt het element. Wat de hack vervangt, wordt nooit verborgen. De soorten zijn `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` en `term`. `didact pack validate` waarschuwt voor een patroon dat met niets overeenkomt.

## Expressies

Elke voorwaarde en formule gebruikt de dobbelsteentaal (`didact guide dice`), plus:
- **Waarden:** `@name` leest een waarde: `@roll`, `@who.STR`, `@settings.x`. `$name` plakt eerst de tekst van een parameter in, dus `@who.$attr` wordt `@who.STR`. Lees een parameter met vrije tekst als `@name`, niet tussen aanhalingstekens (`'$name'`): een apostrof in de tekst zou ze afsluiten (`pack validate` waarschuwt).
- **Logica:** `and`, `or`, `not`, en `in` (`'deprived' in @who.conditions`).
- **Letterlijke waarden:** tekst (`'travel'`) en `true`/`false`.
- **Functies:** `if(cond, a, b)` gooit alleen de tak die het kiest. `default(@thread.flashpoint, 0)` is de waarde, of de terugvalwaarde als die niet is ingesteld. `sum`, `count` (`count(@roll.dice, 6)` telt de zessen), `min`, `max`, `any` en `all` nemen lijsten.

## Bladen: `schemas/`

```yaml
type: character
fields:
  STR: {kind: stat, range: [0, 18], roll: 3d6, on_zero: {trigger: death}}
  hp: {kind: resource, min: 0, roll: d6}
  armor: {kind: derived, expr: "min(3, sum(@inventory.armor))"}
  inventory: {kind: slots, capacity: 10, sizes: {petty: 0, normal: 1, bulky: 2},
              when_full: {set: {hp: 0}}}
  fatigue: {kind: counter, min: 0, occupies: inventory}
guidance: "3 HP is an average monster, 6 a hardy one, 10+ a serious threat."
---
type: pc
extends: character
```

| Soort | Bevat | Opties |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | een gewone waarde | min, max; `values` voor enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` is de waarde, `@hp.max` het maximum | range; min; max of max_field; die |
| `counter` | een getal | min, max, thresholds, occupies (een slots-veld) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | voorwerpen (`Rope` of `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | zoals de naam zegt | `to` (voor refs), `allowed` |
| `derived` | berekend, nooit opgeslagen | expr |

Elk veld neemt ook `label`, `help`, `default`, `required` en `roll`: `new pc Hero --fill`, of een waarde `"roll"`, gooit het via het log. Types uit het pakket `core` bevatten systeemonafhankelijk proza in `fields`. De types van een systeem bevatten de getallen in `mechanics.<system>`. `set hero hp-=2` vindt het veld, begrenst het en meldt elke overloop. `+=` voegt toe aan een lijst: een `list` (zoals `slots`) neemt een waarde die opnieuw wordt toegevoegd nog een keer op, `tags`, `conditions` en `refs` bevatten die maar één keer, en `-=` haalt elke kopie weg.

**Hooks** bepalen wat er gebeurt als een waarde een grens passeert. Ze gaan af bij elke wijziging (`set`, `inv`, een `set`-stap van een regel), maar alleen als de grens gepasseerd wordt: 3 → 0 gaat af, 0 → 0 niet. Wijzigingen met `--force` slaan ze over.

| Hook | Gaat af als |
|---|---|
| `on_zero` | een getal of `{value}` 0 bereikt |
| `on_full` (`when_full` bij slots) | het zijn max, grootte of capaciteit bereikt |
| `thresholds: {10: …, 20: …}` (counters) | het elke drempel voorbijgaat |

Een actie is tekst (een notitie voor het LLM), `{set: {hp: 0}}` of `{condition: paralyzed}` op hetzelfde item, `{trigger: death}` (voert die regel uit met `who` = het item), of een lijst hiervan.

**Inventaris** (`didact inv …`) werkt op het `slots`-veld van het blad:
- **Ruimte:** voorwerpen nemen hun `size` × `count` in, en tellers die het veld met `occupies` bezetten hun waarde. Boven `capacity` wordt geweigerd, tenzij met `--force`.
- **Groepen:** `groups: {backpack: 6, body: 4}` geeft elke groep eigen ruimte, en eigen kolommen en totalen: `@inventory.body.armor` is alleen wat gedragen of vastgehouden wordt, `@inventory.body.free` de ruimte die de groep nog over heeft.
- **Gebruik:** `uses: 3` telt af met `inv use`. `uses: d8` is een gebruiksdobbelsteen: bij 1–2 gaat hij een stap omlaag. Een opgebruikt voorwerp is weg, tenzij het `recharge` of `keep: true` heeft. Van meerdere voorwerpen met dezelfde naam bedoelt de naam het eerste; om een gebruik te besteden (`inv use`, de `use:` van een regel, `set …uses-=1`), het eerste dat er nog een over heeft.
- **Eigen sleutels van een voorwerp:** `didact set freya inventory.sword.damage=d10` (ook `set: who.inventory.$item.damage` in een regel) wijzigt er een, waarbij je het voorwerp noemt zoals bij `inv`, met een deel van de naam of de hele naam, spaties en punten inbegrepen (`'inventory.12.7mm pistol.damage=d10'`, tussen aanhalingstekens voor de shell); `uses` en `charges` tellen zoals een `uses`-veld (`charges+=2` stopt bij het maximum), en de ruimte wordt gecontroleerd zoals `inv add` dat doet. Een regel leest er een als `@{who.inventory.$item.damage}` (een gebruiksdobbelsteen als zijn dobbelsteen, gebruik als het aantal); een voorwerp of sleutel die er niet is, leest als afwezig, zodat `default(…)` zijn terugvalwaarde geeft.
- **Compendium:** items van type `item` (of weapon, armor, relic, …, of een eigen type van het pakket dat er een uitbreidt met `extends`) lenen `inv add` hun details, gevonden via id, naam of een alias (delen twee er een, noem het bedoelde dan als `pack.id`); elke andere naam, `:` en al, is de eigen naam van het voorwerp.

## Tabellen: `tables/`

```yaml
table: weather
dice: d6                     # any expression: 2d6, d66, d100, d20 + @corruption
clamp: true                  # a total past the ends uses the first or last entry
entries:
  1-2: Clear
  3-4: {text: Rain, data: {travel: slow}}
  5: {text: Storm, then: [{table: lightning}]}
  6: {text: Two fronts, roll: 2}
refs: {noun: nouns}          # "{noun}" in a text rolls on table nouns; "{1d4}" rolls dice
source: "Core Rules p. 12"
```

Andere vormen:
- **Gewogen lijsten:** `entries` als lijst, met `weight:` per regel.
- **Kolommen:** `columns: [a, b]` gooit voor elke kolom van een rij apart. Een gewone regel (geen lijst) vult elke kolom, dus `columns: [first, second]` over een woordenlijst betekent “gooi twee keer op deze lijst”. `labels: false` laat de kolomnamen weg uit het resultaat (“Abandon · Advantage”). `read: "It's a {first} {second} with {third} {fourth} inside."` leest de kolommen als een zin.
- **Opzoektabellen:** `lookup: hp_lost`, of `[odds, chaos]` voor een 2D-tabel.
- **Dubbele:** `duplicates: reroll | keep | make_it_worse` voor “gooi twee keer”.
- **In twee stappen:** een tabelregel die op een andere tabel gooit (`{table: lightning}` in plaats van een tekst, of `then:` erna), neemt de data van die worp mee: een regel of concept dat op die tabelregel uitkomt, leest beide, eerst de eigen sleutels van de tabelregel, dan die van de eerste tabel waarop daarna gegooid wordt. Een `--prefill` kan een regel verderop noemen, op elke diepte (`Ring of the Hunt`), met de data van elke regel onderweg: van twee met dezelfde naam telt de dichtstbijzijnde (dan de eerste), een die doorgaat gooit vanaf daar verder, en een die op een ervan lijkt maar er geen is, wordt geweigerd, met de dichtstbijzijnde genoemd. Een begeleid concept biedt de eerste stap aan als de regels ervan zeggen wat ze zijn (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): er een kiezen gooit op de volgende tabel, zoals een worp die erop landt.
- **In beide richtingen lezen:** `both_ways: true` op een d66-tabel voegt de andere lezing toe: 31 geeft ook 13, en wie leest kiest.
- **Wat een regel betekent:** `about: "Knows: {skills}. Also known as: {aka}."` vult de data van elke regel in (een lijst leest als `a, b`; `{text}` is de regel zelf) om te zeggen wat die geeft als een keuze hem aanbiedt; de eigen `note:` van een regel zegt het in plaats daarvan. Zonder een van beide wordt een regel waarvan de data een `id` heeft die een compendiumitem noemt, door dat item beschreven.
- **Stapels en zakken:** `deck: tarot` met `cards` (of `standard: true`); `bag: initiative` met `tokens`.

De validatie controleert dat elke uitkomst die de dobbelstenen kunnen gooien op een regel uitkomt.

## Regels: `rules/`

```yaml
check: save
params: {who: ref, attr: {enum: [STR, DEX, WIL]}}
prompt: State the risk before rolling.
before: [{table: chart, with: {odds: $odds}, as: cell}]   # optional: steps first (a `roll` step can replace `roll:`)
roll: d20                              # or several: {action: "d6 + @stat", challenge: 2d10}
success: "@roll <= @who.$attr"         # or bands: {strong: "@roll >= 10", weak: "@roll >= 7", miss: else}
auto: {1: success, 20: failure}        # natural rolls
flags: {crit: "count(@roll.dice, 6) >= 2"}
on: {failure: ["The risk comes true."]}
options:                               # the roll comes back pending: `didact resolve r12 push`
  push: {label: "Push", steps: [{reroll: roll, keep_if: "@face == 6"}]}
```

Acties en procedures zijn lijsten van stappen, en triggers zijn stappen met een `when:`-voorwaarde. De stappen zijn:

| Stap | Doet |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | een gelogde worp; bindt `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; een `{…}` wordt eerst ingevuld, zoals in elke tekst, zodat dobbelstenen die een waarde als tekst bevat worden gegooid (`{@{who.inventory.$item.damage}}`), en het log toont ze: een waarde die geen dobbelstenen is, wordt geweigerd, net als `roll: "@die"` met zulke tekst, dat niets gooit; een set worpen (`{d8, d6}kh1`) blijft er een |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | berekent waarden; net als bij `value` van `set` is `{…}`-tekst een sjabloon en een los woord tekst; in alle tekst die wordt ingevuld, schrijven `{{` en `}}` de accolade zelf |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (of `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | wijzigt een item: gevalideerd, begrensd, ongedaan te maken; `set: who.$attr` zet het veld dat een parameter noemt, en `set: who.inventory.$item.damage` een sleutel van een voorwerp dat het item bij zich heeft (zie Inventaris); `-=` haalt een waarde uit een lijst, en een die er niet in staat verandert niets (een notitie zegt het; een die er nooit in zou kunnen staan wordt geweigerd); `unset:` haalt een veld weg, zoals `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | geeft een item een voorwerp of neemt het er een af, zoals `inv add` en `inv drop` doen: de details komen uit het compendium, een uniek deel van de naam volstaat, en de ruimte en de hooks van het veld worden gecontroleerd |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | gebruikt een meegedragen voorwerp zoals `inv use` dat doet: gebruik of ladingen tellen af, een gebruiksdobbelsteen wordt gegooid en gaat bij 1–2 een stap omlaag, en een opgebruikt voorwerp is weg, tenzij het opnieuw oplaadt of bewaard wordt; van meerdere met die naam het eerste dat nog een gebruik over heeft; bindt `@torch.out` (zijn laatste gebruik is op), `@torch.gone` (er is niets meer van over), `@torch.left`, `@torch.die` en `@torch.rolled` (`as:` is standaard `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | maakt meteen een item, beschreven zoals bij de stap `entity` van een concept (hieronder) en gecontroleerd tegen zijn blad; `as:` (anders zijn `key`, anders zijn type) bindt het als een item, dat je leest en zet zoals een parameter `ref` (`pool: "@bleeding"`, `@bleeding.name`), en is nooit de naam van een parameter; zonder `key:` wordt geen veld voor een sleutel gehouden (`kind: track` blijft zoals het er staat); is er hier al een item van dat type met die naam, dan wordt dat genomen zoals het is, zodat een regel die nog eens draait niets nieuws maakt |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | voert een check uit en bindt de uitkomst |
| `do: other-action`, `with: {…}`, `as: trip` | voert een andere regel uit; `@trip` is de uitkomst ervan en `@trip.<name>` wat die gebonden heeft (`@trip.found` voor de `let: {found: 2}` ervan, `@trip.luck` voor de `roll: d6`, `as: luck` ervan); `as:` is standaard de id ervan |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | een gelogde tabelworp; bindt de tekst en de `data` van de regel (`@scar.<key>`, en de sleutels van een mapping via hun pad: `@scar.cost.hp`), samen met die van elke tabel waarop daarna gegooid wordt; een lijst van voorwerpen (`[Rope, {name: Laser, damage: d8}]`) leest als hun namen (`count(@scar.gear)`, `'Laser' in @scar.gear`), en zoals ze is aan een stap gegeven (`apply: "@scar.gear"`) is ze de voorwerpen zelf; een lijst van andere mappings kan alleen een stap lezen |
| `table: "setting-{@drop.difficulty}-terrain"` | een berekende tabel: `{…}` en `$param` worden ingevuld |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | meerdere uitkomsten als lijst (`distinct` gooit herhalingen opnieuw) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | vertakkingen |
| `repeat: "@count"`, `as: i`, `steps: […]` | een lus: de stappen dat aantal keer, waarbij `@i` telt vanaf 1 |
| `for: pcs` (of `party`), `as: member`, `steps: […]` | de stappen één keer voor elk spelerspersonage (of groepslid), als `@member`: een item, zoals het item dat `entity:` bindt (`@member.name`, `set: member.fatigue`); `as:` neemt nooit de naam van een parameter aan, zodat de eigen `who` van de regel ongemoeid blijft |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | uitvoer voor het LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (of `every: 1 day`) | een herinnering die actueel wordt naarmate de speltijd verstrijkt, zoals `didact remind` die instelt |
| `reroll: roll`, `keep_if: "@face == 6"` | gooit een deel van de dobbelstenen van een worp opnieuw (push-mechanieken) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | gooit op een lijstwaarde (de lijsten van een orakel): bindt de regel, `@who.choose` (een lege regel) en `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | gooit de slinkende pool van een teller zoals `track roll` (dobbelstenen met 1-3 vallen af; `drop`-dobbelstenen vallen eerst weg, `extra`-dobbelstenen rollen mee) of laat alleen dobbelstenen wegvallen (`mode: drop`: een push, een vinkje); gekoppelde fasen en het event van de pool volgen; bindt `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

De uitkomst van een check is leesbaar voor de regel die hem uitvoerde (`check: … as: answer` geeft `@answer`), en zijn vlaggen ook: `'random-event' in @answer.flags`. Waarden in `with:` worden geëvalueerd als ze `@` bevatten, ingevuld als ze `$param` of `{…}` bevatten (“Does $npc flee?”), en anders doorgegeven zoals ze geschreven zijn. Een regel met een parameter `oracle` krijgt het statusitem van het campagne-orakel zonder dat je het hoeft te zeggen. Een parameter `ref` met `to: monster` neemt een item van dat type: een naam die een ander item deelt (de pool van een vijand, genoemd naar zijn kaart) is die van dat type.

Triggers lopen vanzelf als hun gebeurtenis plaatsvindt, en alleen als hun `when:` klopt:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Elke regel (ook een generator en een personagecreatie) kan `@system` (de id van het systeem waarmee de wereld gespeeld wordt, zodat een setting die voor twee systemen geschreven is ze uit elkaar kan houden), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` en `@time.is_night` lezen, en met een kalender met maanden ook `@time.month`, `@time.month_name`, `@time.day_of_month` en `@time.year`; zolang er een gevecht bezig is, ook `@combat.round` en `@combat.fighters` (de id's van wie erin zit). Een tijdtrigger kan ook `@time.passed` lezen, de seconden die net verstreken zijn, een `combat_start`- of `combat_end`-trigger leest het gevecht dat begint of eindigt (`combat start` en `combat end` voeren ze uit; een vechter die het gevecht verlaat, beëindigt het niet), en een regel die door een trigger wordt uitgevoerd, leest wat de trigger leest. Een trigger met verplichte parameters wordt alleen uitgevoerd door `didact do` of een veldhook (`who` = het item). Triggers met `on: manual` lopen alleen als ze aangeroepen worden. `for: pcs` (of `party`) voert een trigger één keer uit voor elk spelerspersonage (of groepslid), als `who`: ervaring na elke sessie, bijvoorbeeld. Een trigger die mislukt, stopt de opdracht die hem afvuurde, en zegt welke trigger het was en hoe je zonder hem verdergaat (`didact override add trigger <id> --data '{"on": "manual"}'`).

De kalender staat in de `settings` van een pakket: die van een settingpakket gaat voor die van het systeem, en de eigen kalender van een wereld (`calendar:` in haar `world.yaml`) gaat voor allebei:

```yaml
settings:
  watches: [morning, afternoon, night]   # the day's watches
  calendar:
    week: [Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday]
    months: [{name: January, days: 31}, {name: February, days: 28, leap: [4, 100, 400]}, …]
    start: {year: 1890, month: 3, day: 14, weekday: Friday}   # where a campaign opens
    year: "{year} AD"                     # how a date writes its year
    seasons: [{name: spring, month: 3, day: 20}, …]           # each from its first day
    holidays: [{name: Midsummer, month: 6, day: 24, text: "…"}]
```

`leap: 4` maakt een maand elk 4e jaar een dag langer, en `leap: [4, 100, 400]` elk 4e, maar niet elk 100e, maar wel weer elk 400e: elk getal gaat voor het vorige. `weekday` noemt de weekdag van het begin (anders is het de eerste van de week), en `year` is hoe een datum zijn jaar schrijft, zowel in de data die Didact toont als in die het leest (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` controleert alle drie. Een campagne kan op een andere datum van de kalender beginnen, vóór het begin of erna: `didact campaign new <id> --date '4 July 1902'`, of `didact time set '<date>'` tot haar eerste sessie. Een weekdag die vóór de datum staat, wordt gecontroleerd: de datum beslist, en een notitie zegt het als die op een andere dag valt.

Opties zijn de varianten en optionele regels van het systeem, die elke campagne in sessie nul kiest:

```yaml
option: lethality                       # rules read it as @option.lethality
ask: How deadly should it be?           # session zero asks it (in place of Didact's own of that key)
choices: {gentle: "…", standard: "As the book has it.", deadly: "…"}   # each with what it means
default: standard
---
option: supplies                        # a flag: on or off (@option.supplies is true or false)
kind: flag
ask: Can the PCs run out of supplies?
help: Each PC has a 4d Supplies pool.
---
option: flavor
choices: {heroic: "…", grimdark: "…"}
implies: {grimdark: {lethality: deadly, supplies: true}}   # a choice that sets others (a flag's: on)
```

`didact campaign profile lethality=deadly supplies=on` slaat ze op (of de pagina Instellingen van de webapp). Regels, personages maken en generatoren lezen ze (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): een antwoord gaat voor wat een andere optie meebrengt, en dat gaat voor de standaard. Wat een optie meebrengt, wordt tot het einde gevolgd (een sfeer die de dodelijkheid instelt, stelt ook in wat die dodelijkheid meebrengt), en van twee implicaties wint de dichtstbijzijnde. De briefing noemt de opties die van hun standaard afwijken, met wat ze betekenen, zodat de spelleider toepast wat de regels niet kunnen. Een generator die er niet mee kan draaien, stopt met `stop:` en de reden, en er ontstaat geen concept.

## Orakels: `oracles/`

```yaml
oracle: chart
title: Chart oracle
ask: chart-question          # the check that answers; it may take question, odds and oracle
odds: [unlikely, 50-50, likely]
meaning: [actions, descriptions]   # tables for `didact meaning` (a word from each)
state: {chaos: {start: 5, min: 1, max: 9}}  # kept per campaign; rules read @oracle.chaos
lists: {names: [threads, characters], method: sections}   # weighted lists (`didact lists`)
prompt: Interpret the answer in the fiction.
```

- **Vragen:** `didact ask '…' --odds likely` voert de check `ask` uit. Het antwoord is de uitkomst ervan (een band), en de vlaggen gaan mee.
- **Status:** die zit in een item dat de check als `oracle` ontvangt. Een check wijzigt hem met `set: oracle.chaos += 1`.
- **Lijsten:** `lists: {names: […], method: sections, most: 3}` houdt gewogen lijsten bij op dat item. `didact lists add|drop|roll|show` beheren ze, en regels gooien erop met `pick`. `sections` gooit voor een sectie van vijf regels, daarna voor een regel daarin (een lege regel betekent: kies); `uniform` geeft elke regel dezelfde kans.
- **Meer voor de check:** `didact ask '…' --with as_rule=true` geeft extra parameters door aan de check van het orakel.
- **Het log:** elk antwoord krijgt een nummer (`#o12`) en wordt gelogd, en `didact interpret o12 '…'` bewaart wat het betekende. Het orakel `yes-no` van het pakket core is de terugvaloptie.

## Generatoren en personages maken: `generators/`, `chargen/`

Beide zijn procedures die een **concept** opbouwen. Ze gebruiken elke regelstap (`roll`, `table`, `if`, `let`, `prompt`, …) plus deze:

| Stap | Doet |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | voegt een item toe aan het concept (sleutels `poi-1`, `poi-2`, …); een veld of een koppeling die een sleutel noemt die het pakket schreef (`key:`, of een `as:`-naam), wordt bij het vastleggen de id van dat item, dus kies sleutels die geen veld als tekst bevat (een entiteit zonder beide heeft er geen die vervangen wordt); `from: "@relic.id"` laat het beginnen vanuit een compendiumitem (met het type, de naam en de velden daarvan) |
| `choose: {from: [a, b], as: x}` (of `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | een keuze; in de begeleide modus wacht het concept op `choose`; `exclude` sluit eerdere keuzes uit (een gegooide wordt opnieuw gegooid); `records:` voegt hier de items van dat type toe, op id (tijdens het spel gemaakt); `answer:` maakt de keuze zonder te vragen als de waarde ervan een van de opties is (het eigen pad van een personage) |
| `choose_or_roll: {table: backgrounds, as: background}` | een keuze die de dobbelstenen kunnen maken; de data van een gekozen regel is `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | gooit waarden voor het personage |
| `swap: {among: [STR, DEX, WIL], optional: true}` | twee scores omwisselen, of houden |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | een vaste reeks verdelen |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | scores kopen binnen een budget (`default: random` besteedt het willekeurig in de willekeurige modus) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | een lijst gaat naar de inventaris; een mapping zet velden (lijsten tellen op) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | voegt toe aan een veld van het personage (of van een entiteit in het concept): getallen tellen op, al het andere komt in een lijst; niets toe te voegen is prima |
| `remove: {field: talents, value: "@old"}` | haalt iets uit een lijstveld (een ingeruild talent, een afgesloten band); niets te verwijderen is prima |
| `roll_tables: [physique, vice]` | gooit tabellen in `traits`; `data.gear` van een regel gaat naar de inventaris en `data.add: {gold: 20}` telt op bij velden |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | de naam; `name: {prompt: …}` zonder iets om op te gooien wacht op een naam, zelfs in de willekeurige modus |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | een vraag waarop elk antwoord goed is (een doel, de naam van een ander item): het concept wacht erop, zelfs in de willekeurige modus, tenzij hij vooraf is ingevuld; `field:` bewaart het antwoord |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | een pointcrawl: een gelogde dobbelsteen-drop, paden (altijd verbonden), afstanden, verborgen paden (zie hieronder) |

De stap map kent meer, voor de dobbelsteen-drop-procedures uit het boek:

| Sleutel | Doet |
|---|---|
| `regions: terrain` | deze entiteiten worden ook geworpen; elke plaats hoort bij de dichtstbijzijnde (haar `region`) |
| `hidden: 6`, `conditional: 5` | een d6 per pad: op of boven het getal een verborgen of voorwaardelijk pad (verborgen paden blijven van de kaart van de spelers) |
| `describe: [path-feature, path-condition]` | tabellen die voor elk pad gegooid worden, bewaard als de `details` ervan |
| `entrance: true`, `exit: true` | de plaats het dichtst bij de rand is de ingang; de rest wordt vanaf daar langs de paden genummerd (`map.n`), paden leiden ervan weg, en de uitgang is een verre plaats bij een rand, als laatste genummerd |
| `number: "{@dungeon_name}, room {@n}"` | hernoemt de genummerde plaatsen (hun conceptsleutels volgen: `room-1` is kamer 1) |

Een dobbelsteen-drop-tabel kan in de data van haar regels de volgende tabellen noemen, zodat de procedure leest als het boek: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, dan `table: "{@drop.what}"`. Niet-ingestelde lijstvelden (conditions, lists, tags) gelden als lege lijsten, dus `'deprived' in @who.conditions` werkt vanaf het begin.

```yaml
chargen: pc
creates: pc
modes: [random, guided]
steps:
  - choose_or_roll: {table: backgrounds, as: background, field: background}
  - apply: "@background.gear"
  - roll: {each: [STR, DEX, WIL], dice: 3d6}
  - swap: {among: [STR, DEX, WIL], optional: true}
  - name: {from: "@background.names"}
```

Een personagecreatie met `advances:` verandert een item in plaats van er een te maken: de level-up van het systeem.

```yaml
chargen: level-up
advances: pc                   # `didact char advance <pc>`, or Level up on its page
params: {who: ref}
steps:
  - if: "@who.xp < @who.level + 1"
    then: [stop: "{@who.name} needs more XP"]
  - apply: {level: "{@who.level + 1}", xp: "{@who.xp - @who.level - 1}"}
  - choose: {table: paths, as: path, answer: "@who.path"}     # the character's own: not asked
  - choose: {from: "@path.talents", records: talent, as: talent, exclude: "@character.talents"}
  - add: {field: talents, value: "@talent"}
```

- **Eén item:** een generator met `creates: npc` bouwt dat item zoals personages maken een personage bouwt (`apply`, `add`, `name`, `field:`); zijn `entity`-stappen voegen items ernaast toe, en een koppeling `to: character` wijst ernaar.
- **Uitvoeren:** `gen run` en `char new` maken een concept (`#g7`, `#c3`) en schrijven niets weg. Een `stop:` beëindigt het zonder dat er een concept ontstaat: onder een `if:` die een campagneoptie leest, wijst de hint ervan naar de opties (`didact session zero`); anders zeggen de eigen woorden ervan wat je in plaats daarvan doet.
- **Beslissen:** `--prefill '{…}'` beslist dingen vooraf, via de naam die een stap bindt (`as:`): één waarde beantwoordt elk voorkomen, een lijst één voorkomen per element (een lijst voor `choose` met `count` is de hele keuze). Ook `let`-waarden kun je vooraf invullen (`{"hp": 6}`), en een naam, een `ask` of een `let` houdt elke tekst zoals opgegeven. Een waarde voor een keuze uit bekende opties (een `choose`, een tabelregel) is de optie die ze noemt, zoals geschreven of met ander hoofdlettergebruik, via de `id` van de bijbehorende tabelregel, of via een worp die erop uitkomt (`{"group": 3}`), en brengt de data van die tabelregel mee; een waarde die dicht bij een optie ligt maar er geen van is, wordt geweigerd met vermelding van de dichtstbijzijnde, en elke andere is een eigen antwoord, zonder data. `--auto` (of `char new --mode random`) laat de dobbelstenen de rest beslissen. Anders wacht het concept bij elke keuze.
- **Beschrijven:** een keuze zegt wat elke optie betekent, voor de speler die kiest: de `note:` van een tabelregel of de `about:` van zijn tabel, anders het compendiumitem dat hij noemt (de `id` in zijn data), of het item dat de optie zelf is (een keuze tussen compendium-id's toont de naam van elk): de velden `tagline` en `summary`, `description` of `effect`, anders de eerste alinea van de tekst.
- **Teruggaan:** `char back` (of `gen back`) draait het laatste antwoord, de laatste worp of de laatste bewerking terug, zodat het concept die vraag opnieuw stelt; de worpen die daarbij gedaan zijn, worden als ongedaan gemarkeerd.
- **Hervatten:** een hervat concept speelt zijn spoor opnieuw af: elke gegooide of gekozen waarde, elk één keer en op volgorde (ook de dobbelsteen-drop van de kaart), zodat niets twee keer gegooid wordt en niets wat al besloten is verandert.
- **Wegschrijven:** `commit` schrijft de items weg, gecontroleerd tegen hun bladen.
- **Groeien:** een concept met `advances:` begint met een kopie van het item (met de standaardwaarden van zijn blad), de stappen lezen het item als `@who` en de waarden van het concept als `@character.*`, en `commit` schrijft alleen weg wat er veranderd is, gecontroleerd zoals bij `set`; items uit zijn `entity`-stappen (de verhaallijn van een nieuwe band) worden ernaast aangemaakt: een koppeling `to: character` wijst naar het item, en een veld dat een sleutel noemt, bevat de id van het item met die sleutel, net als bij het maken van een personage (`apply: {blood: "@pool"}`). Een `stop:` zegt waarom nog niet (niet genoeg XP), en er wordt geen concept gemaakt. Een systeem waarvan de groei één enkele regel is, noemt die in plaats daarvan in zijn personagecreatie: `advance: {rule: grow}`.
- **Modi:** `modes: [guided]` laat een procedure alleen stap voor stap lopen: `--mode random` wordt geweigerd.

## Compendium, naslag en woordenlijst

- **Compendiumitems** schrijf je zoals `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Een waarde `"roll 2d8"` wordt gegooid als het item verschijnt. Voer `didact spawn troll` uit, of haal de items van een pakket naar de wereld met `didact compendium import <pack>` (`--type loc`, en `--tag coast` voor de items met elke opgegeven tag).
- **Voor meerdere systemen:** een sleutel op het hoogste niveau komt waar `set` hem zet: in het blok van het systeem als zijn blad dat veld heeft, anders in `fields`. Een item dat een setting voor meer dan één systeem schrijft, geeft de getallen van elk systeem in een eigen blok (`mechanics: {my-system: {hp: 12}}`): `pack validate` toetst elk blok aan het blad van dat systeem als het geïnstalleerd is, en vermeldt een sleutel op het hoogste niveau die dat blad en dat van core allebei hebben. Wat een blok zegt, geldt: naast `mechanics: {my-system: {role: tactician}}` is een `role: innkeeper` op het hoogste niveau het veld van core, net als alles onder `fields:`. Een blok dat het pakket noemt dat gevalideerd wordt, wordt gecontroleerd tegen dat pakket zoals het in zijn map staat.
- **Naslagsecties** gaan in `reference/*.md`, met front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` vindt ze; een zin tussen aanhalingstekens die er niet staat, wordt woord voor woord geprobeerd.
- **De woordenlijst** is `glossary.yaml`: `term: definition`, of een lijst van `{term, definition, aliases, see}`. `didact define <term>` leest haar.

## Tests: `tests/`

```yaml
test: weather-lands     # roll a table many times: every roll must land
table: weather
times: 50
---
test: fair-save         # exact odds
odds: "d20 <= 10"
chance: 0.5
---
test: every-table       # each of the pack's tables (a lookup table once per key)
table: all
---
test: play              # a smoke-play script: real commands in a scratch library
script:
  - world new t --system {pack} --seed smoke    # seeded: it plays the same every time
  - new pc Hero --fill
  - run: do save who=hero attr=STR
    expect: "→"                                  # text the step must print (or a list)
  - run: table list
    expect_not: my-system.spell-fire             # text it must not print (or a list)
  - run: table roll my-system.spell-fire
    fails: true                                  # it must fail (`expect` reads its error too)
```

## Pakketten delen en verwijderen

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Een pakket dat `redistributable: false` opgeeft, kan niet geëxporteerd worden.
- **core** hoort bij Didact en staat altijd aan: elk systeem bouwt erop voort, dus het kan niet uitgeschakeld of gedeïnstalleerd worden.
- De andere pakketten die met Didact meekomen, zijn `.didactpack`-bestanden in de map `packs/`. `pack list` toont ze tot ze geïnstalleerd zijn, en als je er een installeert, komen de meegeleverde pakketten die het nodig heeft mee.
- `pack update` zoekt naar nieuwere versies in de map `packs/` van Didact en op GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` noemt een andere plek, of niets om niet te zoeken). Een nieuwe versie wordt naast de oude geïnstalleerd: campagnes houden de hunne tot `didact campaign upgrade`.
- Er is maar één spelsysteem tegelijk in gebruik: dat van de geopende wereld. Een wereld houdt het systeem waarmee ze gemaakt is (`didact world new <id> --system <pack>`; een wereld die zonder systeem gemaakt is, neemt het eerste dat ze krijgt, met `pack enable` of `world set system=`), haar campagnes worden ermee gespeeld, en een pakket dat een ander systeem nodig heeft (een setting die ervoor geschreven is) kan niet worden toegevoegd: een ander systeem wordt in een eigen wereld gespeeld.
- `uninstall` weigert zolang een wereld of campagne de enige kopie van het pakket gebruikt (`--force` verwijdert het toch). Het kan niet ongedaan worden gemaakt: installeer de .didactpack opnieuw.

## Van regelboek naar pakket: de checklist

Loop de mechanieken van het boek in deze volgorde door. Elk ervan past op iets hierboven:

1. **Resolutie:** hoe een worp slaagt (een check: `success`, `bands`, `auto`).
2. **Dobbelstenen:** ongewone dobbelstenen, symbolen, stappen (`dice.yaml`, benoemde dobbelstenen, reeksen).
3. **Het blad:** attributen, afgeleide getallen (`schemas/`, afgeleide velden).
4. **Hulpbronnen:** HP, geluk, momentum (resource- en counter-velden; `set`-stappen).
5. **Toestanden:** toestanden en wat ze doen (`conditions`-velden; `if`-stappen).
6. **Gevechten:** aanvallen, schade, initiatief (acties; `bag`/`deck` voor de beurtvolgorde).
7. **Procedures:** verkenning, reizen, rustperiodes (procedures met prompts).
8. **Tabellen:** elke willekeurige tabel (`tables/`; `pack import` voor Markdown-tabellen).
9. **Het bestiarium:** monsters en NPC's (`compendium/`).
10. **Voorwerpen:** uitrusting, spreuken, relikwieën (`compendium/`, slots-velden).
11. **Advies voor de SL:** principes en tips (`GUIDE.md`, `reference/`, `guidance:` op types).
12. **Personages maken:** hoe je een personage maakt (een `chargen/`-procedure, of `roll:` op elk veld).

Vermeld overal pagina's met `source:`, zodat gaten opvallen. Voeg een proefspeltest toe die een personage maakt, een check gooit, vecht en een procedure uitvoert.
