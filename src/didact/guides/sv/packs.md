<!-- translated from b1dfa1159ff4 -->
# Paket

Ett paket är ett spelsystem, ett orakel, en spelvärld, ett äventyr eller ett supplement, skrivet som YAML-filer plus ett valfritt Python-plugin. Den här guiden visar hur du skriver ett: gör om en regelbok till ett paket, eller lägg till eget material.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Ett paket kan också göras av det som finns i ditt bibliotek. `didact pack new my-brew --from-overlay my-system` gör ditt eget material för ett system (`compendium add`, uppslag som sparats med `--scope system`, lore) till ett supplement, och `didact world export --as setting` gör en värld till ett spelvärldspaket: dess personer, platser och lore som kompendieposter och paketlore, som hämtas in i en annan värld med `compendium import`. Båda lämnar hemligheter och SL-anteckningarna utanför om inte `--secrets` anges, och inget av dem är markerat som delbart förrän du anger dess licens.

## Struktur

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

En fil innehåller ett objekt, en lista av objekt eller flera objekt åtskilda av `---`. Varje objekt anger sitt id med nyckeln för sin sort: `table: weather`, `check: save`, `type: pc`, eller `id: troll` för kompendieposter. Hänvisa till objekt som `pack.id` (`my-system.save`), eller med bara id:t när bara ett aktiverat paket har det.

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

Ett hack anger sin bas i `extends` och innehåller bara det som skiljer sig:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Dess objekt med samma id ersätter basens, oavsett sort (en tabell, en regel, en kompendiepost, ett referensavsnitt, ett ordlistebegrepp). Dess `settings` läggs ovanpå basens, nyckel för nyckel: en nyckel som hacket sätter ersätter basens värde i sin helhet (dess `names`-tabeller träder i stället för basens), och basens regler läser också hackets värden. `hides` utelämnar resten, som hacket inte har användning för: `*` matchar vilken teckenföljd som helst, det sista mönstret som matchar ett id avgör, och ett mönster som börjar med `!` behåller objektet. Det som hacket ersätter döljs aldrig. Sorterna är `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` och `term`. `didact pack validate` varnar för ett mönster som inte matchar något.

## Uttryck

Varje villkor och formel använder tärningsspråket (`didact guide dice`), plus:
- **Värden:** `@name` läser ett värde: `@roll`, `@who.STR`, `@settings.x`. `$name` klistrar först in en parameters text, så `@who.$attr` blir `@who.STR`. Läs en parameter med fri text som `@name`, inte inom citattecken (`'$name'`): en apostrof i dess text skulle avsluta dem (`pack validate` varnar).
- **Logik:** `and`, `or`, `not` och `in` (`'deprived' in @who.conditions`).
- **Literaler:** text (`'travel'`) och `true`/`false`.
- **Funktioner:** `if(cond, a, b)` slår bara den gren det väljer. `default(@thread.flashpoint, 0)` är värdet, eller reservvärdet när det inte är satt. `sum`, `count` (`count(@roll.dice, 6)` räknar sexorna), `min`, `max`, `any` och `all` tar listor.

## Formulär: `schemas/`

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

| Sort | Innehåller | Alternativ |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | ett enkelt värde | min, max; `values` för enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` är värdet, `@hp.max` taket | range; min; max eller max_field; die |
| `counter` | ett tal | min, max, thresholds, occupies (ett slots-fält) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | föremål (`Rope` eller `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | som namnet säger | `to` (för refs), `allowed` |
| `derived` | beräknat, sparas aldrig | expr |

Varje fält tar också `label`, `help`, `default`, `required` och `roll`: `new pc Hero --fill`, eller värdet `"roll"`, slår fram det genom loggen. Typer från paketet `core` håller systemoberoende prosa i `fields`. Ett systems typer håller dess siffror i `mechanics.<system>`. `set hero hp-=2` hittar fältet, begränsar värdet och rapporterar eventuellt överskott. `+=` lägger till i en lista: en `list` (som `slots`) behåller ett värde som läggs till igen, `tags`, `conditions` och `refs` innehåller det bara en gång, och `-=` tar bort alla kopior.

**Hooks** säger vad som händer när ett värde passerar en gräns. De utlöses vid varje ändring (`set`, `inv`, en regels `set`-steg), men bara när gränsen passeras: 3 → 0 utlöser, 0 → 0 gör det inte. Ändringar med `--force` hoppar över dem.

| Hook | Utlöses när |
|---|---|
| `on_zero` | ett tal eller `{value}` når 0 |
| `on_full` (`when_full` på slots) | det når sitt max, sin storlek eller sin kapacitet |
| `thresholds: {10: …, 20: …}` (räknare) | det klättrar förbi varje markering |

En åtgärd är text (en anteckning för LLM:en), `{set: {hp: 0}}` eller `{condition: paralyzed}` på samma uppslag, `{trigger: death}` (kör den regeln med `who` = uppslaget), eller en lista av dessa.

**Inventarier** (`didact inv …`) arbetar med arkets `slots`-fält:
- **Utrymme:** föremål tar upp sin `size` × `count`, och räknare som har `occupies` på fältet tar upp sitt värde. Över `capacity` nekas om inte `--force` anges.
- **Grupper:** `groups: {backpack: 6, body: 4}` ger varje grupp eget utrymme, och egna kolumner och summor: `@inventory.body.armor` är bara det som bärs på kroppen eller hålls i handen, `@inventory.body.free` gruppens återstående utrymme.
- **Användningar:** `uses: 3` räknas ner med `inv use`. `uses: d8` är en förbrukningstärning: 1–2 stegar ner den. Ett förbrukat föremål är borta om det inte har `recharge` eller `keep: true`. Av flera föremål med samma namn avser namnet det första; för att spendera en användning (`inv use`, en regels `use:`, `set …uses-=1`) det första som har någon kvar.
- **Ett föremåls egna nycklar:** `didact set freya inventory.sword.damage=d10` (liksom en regels `set: who.inventory.$item.damage`) ändrar en av dem, med föremålet angivet som `inv` anger det, med en del av namnet eller hela namnet, mellanslag och punkter också (`'inventory.12.7mm pistol.damage=d10'`, inom citattecken för skalet); `uses` och `charges` räknas som ett `uses`-fält (`charges+=2` stannar vid max), och utrymmet kontrolleras som vid `inv add`. En regel läser en som `@{who.inventory.$item.damage}` (en förbrukningstärning som sin tärning, användningar som sitt antal); ett föremål eller en nyckel som inte finns läses som frånvarande, så att `default(…)` ger sitt reservvärde.
- **Kompendium:** poster av typen `item` (eller weapon, armor, relic, …, eller en egen typ i paketet som utökar någon av dem med `extends`) lånar ut sina detaljer till `inv add`, hittade via id, namn eller ett alias (delar två på ett: ange den avsedda som `pack.id`); alla andra namn, `:` och allt, är föremålets eget namn.

## Tabeller: `tables/`

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

Andra former:
- **Viktade listor:** `entries` som en lista, med `weight:` per post.
- **Kolumner:** `columns: [a, b]` slår separat för varje kolumn i en rad. En enkel post (inte en lista) fyller varje kolumn, så `columns: [first, second]` över en ordlista betyder ”slå två gånger på den här listan”. `labels: false` utelämnar kolumnnamnen ur resultatet (”Abandon · Advantage”). `read: "It's a {first} {second} with {third} {fourth} inside."` läser kolumnerna som en mening.
- **Lookup-tabeller:** `lookup: hp_lost`, eller `[odds, chaos]` för ett 2D-diagram.
- **Dubbletter:** `duplicates: reroll | keep | make_it_worse` för ”slå två gånger”.
- **Två steg:** en post som slår på en annan tabell (`{table: lightning}` i stället för text, eller `then:` efter texten) tar med sig data från det slaget: en regel eller ett utkast som slår fram posten läser båda, först postens egna nycklar och sedan nycklarna från den första tabell som slås därefter. En `--prefill` kan ange en post längre ner, på valfritt djup (`Ring of the Hunt`), med data från varje post på vägen: av två med samma namn gäller den närmare (sedan den första), en som går vidare slår vidare därifrån, och en som liknar någon av dem utan att vara den avvisas, och den närmaste nämns. Ett guidat utkast erbjuder första steget när dess poster säger vad de är (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): att välja en slår på nästa tabell, som när ett slag hamnar på den.
- **Läs åt båda hållen:** `both_ways: true` på en d66-tabell lägger till den andra läsningen: 31 ger också 13, och läsaren väljer.
- **Vad en post betyder:** `about: "Knows: {skills}. Also known as: {aka}."` fyller i varje posts data (en lista läses `a, b`; `{text}` är själva posten) för att säga vad den ger när ett val erbjuder den; en posts egen `note:` säger det i stället. Utan något av dem beskrivs en post vars data har ett `id` som anger en kompendiepost av den kompendieposten.
- **Kortlekar och påsar:** `deck: tarot` med `cards` (eller `standard: true`); `bag: initiative` med `tokens`.

Valideringen kontrollerar att varje resultat tärningarna kan ge landar på en post.

## Regler: `rules/`

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

Handlingar och procedurer är steglistor, och utlösare är steg med ett `when:`-villkor. Stegen är:

| Steg | Gör |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | ett loggat slag; binder `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; en `{…}` fylls i först, som i all text, så tärningar som ett värde håller som text slås (`{@{who.inventory.$item.damage}}`), och loggen visar dem: ett värde som inte är tärningar avvisas, liksom `roll: "@die"` med sådan text, som inte slår något; en mängd slag (`{d8, d6}kh1`) förblir en |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | beräknar värden; som i `set`s `value` är `{…}`-text en mall och ett ensamt ord är text; i all text som fylls i skriver `{{` och `}}` själva klammern |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (eller `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | ändrar ett uppslag: validerat, begränsat, går att ångra; `set: who.$attr` sätter fältet som en parameter anger, och `set: who.inventory.$item.damage` en nyckel hos ett föremål som uppslaget bär på (se Inventarier); `-=` tar bort ett värde ur en lista, och ett som den inte innehåller ändrar ingenting (en anteckning säger det; ett som den aldrig skulle kunna innehålla avvisas); `unset:` tar bort ett fält, som `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | ger ett uppslag ett föremål eller tar ett från det, som `inv add` och `inv drop` gör: detaljerna hämtas från kompendiet, en unik del av namnet räcker, och utrymmet och fältets hooks kontrolleras |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | använder ett buret föremål som `inv use` gör: användningar eller laddningar räknas ner, en förbrukningstärning slås och stegas ner på 1–2, och ett som tar slut är borta om det inte laddas om eller behålls; av flera med det namnet det första som har en användning kvar; binder `@torch.out` (dess sista användning är borta), `@torch.gone` (inget av det finns kvar), `@torch.left`, `@torch.die` och `@torch.rolled` (`as:` är `use` som standard) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | skapar ett uppslag direkt, beskrivet som i ett utkasts `entity`-steg (nedan) och kontrollerat mot sitt ark; `as:` (annars dess `key`, annars dess typ) binder det som ett uppslag, som läses och sätts som en `ref`-parameter (`pool: "@bleeding"`, `@bleeding.name`), och är aldrig en parameters namn; utan `key:` tas inget fält för en nyckel (`kind: track` står kvar som det är skrivet); finns det redan ett av den typen och med det namnet här tas det som det är, så en regel som körs igen skapar inget nytt |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | kör en kontroll och binder dess utfall |
| `do: other-action`, `with: {…}`, `as: trip` | kör en annan regel; `@trip` är dess utfall och `@trip.<name>` det den band (`@trip.found` för dess `let: {found: 2}`, `@trip.luck` för dess `roll: d6`, `as: luck`); `as:` är dess id som standard |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | ett loggat tabellslag; binder texten och postens `data` (`@scar.<key>`, och nycklarna i en mappning via sökvägen: `@scar.cost.hp`), samt data från en eventuell tabell som slås därefter; en lista med föremål (`[Rope, {name: Laser, damage: d8}]`) läses som deras namn (`count(@scar.gear)`, `'Laser' in @scar.gear`), och given som den är till ett steg (`apply: "@scar.gear"`) är den föremålen själva; en lista med andra mappningar läses bara av ett steg |
| `table: "setting-{@drop.difficulty}-terrain"` | en beräknad tabell: `{…}` och `$param` fylls i |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | flera resultat som en lista (`distinct` slår om upprepningar) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | förgreningar |
| `repeat: "@count"`, `as: i`, `steps: […]` | en loop: kör stegen så många gånger, där `@i` räknar från 1 |
| `for: pcs` (eller `party`), `as: member`, `steps: […]` | kör stegen en gång för varje rollperson (eller gruppmedlem), som `@member`: ett uppslag, likt det som `entity:` binder (`@member.name`, `set: member.fatigue`); `as:` tar aldrig en parameters namn, så regelns egen `who` förblir orörd |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | utdata för LLM:en |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (eller `every: 1 day`) | en påminnelse som förfaller allteftersom speltiden går, som de `didact remind` sätter |
| `reroll: roll`, `keep_if: "@face == 6"` | slår om några av ett slags tärningar (push-mekanik) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | slår på ett listvärde (ett orakels listor): binder posten, `@who.choose` (en tom rad) och `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | slår en räknares krympande pöl som `track roll` gör (tärningar som visar 1-3 försvinner; `drop`-tärningar tas bort först, `extra`-tärningar slås med) eller tar bara bort tärningar (`mode: drop`: en push, en bock); kopplade faser och pölens händelse följer; binder `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

En kontrolls utfall kan läsas av regeln som körde den (`check: … as: answer` ger `@answer`), och likaså dess flaggor: `'random-event' in @answer.flags`. `with:`-värden beräknas när de innehåller `@`, fylls i när de innehåller `$param` eller `{…}` (”Does $npc flee?”), och skickas annars vidare som de är skrivna. En regel med en `oracle`-parameter får kampanjorakelets tillståndsuppslag utan att behöva be om det. En `ref`-parameter med `to: monster` tar ett uppslag av den typen: ett namn som ett annat uppslag delar (en fiendes pool, namngiven som dess kort) är det av den typen.

Utlösare körs av sig själva när det de väntar på inträffar, och bara om deras `when:` gäller:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Varje regel (även generatorer och rollpersonsskapande) kan läsa `@system` (id:t för systemet som världen spelas med, så att en spelvärld skriven för två system kan skilja dem åt), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` och `@time.is_night`, och med en kalender med månader även `@time.month`, `@time.month_name`, `@time.day_of_month` och `@time.year`; medan en strid pågår också `@combat.round` och `@combat.fighters` (id:n för dem som är med i den). En tidsutlösare kan också läsa `@time.passed`, sekunderna som just gick, en `combat_start`- eller `combat_end`-utlösare läser striden som börjar eller slutar (`combat start` och `combat end` kör dem; att en kombattant lämnar striden avslutar den inte), och en regel som en utlösare kör läser det som utlösaren läser. En utlösare med obligatoriska parametrar körs bara av `didact do` eller en fälthook (`who` = uppslaget). `on: manual`-utlösare körs bara när de anropas. `for: pcs` (eller `party`) kör en utlösare en gång för varje rollperson (eller gruppmedlem), som `who`: erfarenhet efter varje spelmöte, till exempel. En utlösare som misslyckas stoppar kommandot som avfyrade den, och säger vilken utlösare det var och hur man fortsätter utan den (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalendern ligger i ett pakets `settings`: ett spelvärldspakets kalender går före systemets, och en världs egen (`calendar:` i dess `world.yaml`) före båda:

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

`leap: 4` gör en månad en dag längre vart 4:e år, och `leap: [4, 100, 400]` vart 4:e, men inte vart 100:e, men ändå vart 400:e: varje tal åsidosätter det föregående. `weekday` anger vilken veckodag starten är (annars veckans första), och `year` är hur ett datum skriver sitt år, både i de datum Didact visar och i dem det läser (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` kontrollerar alla tre. En kampanj kan börja på ett annat datum i kalendern, före dess start eller efter: `didact campaign new <id> --date '4 July 1902'`, eller `didact time set '<date>'` fram till kampanjens första spelmöte. En veckodag skriven före datumet kontrolleras: datumet avgör, och en anteckning säger till när det infaller på en annan dag.

Alternativ är systemets varianter och valfria regler, som varje kampanj väljer vid session noll:

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

`didact campaign profile lethality=deadly supplies=on` sparar dem (eller webbappens sida Inställningar). Regler, rollpersonsskapande och generatorer läser dem (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): ett svar går före det ett annat alternativ medför, som i sin tur går före standardvärdet. Det som ett alternativ medför följs hela vägen (en stil som sätter dödligheten sätter också det som den dödligheten medför), och av två följder vinner den som ligger närmast. Sammanfattningen visar dem som skiljer sig från sitt standardvärde, med vad de betyder, så att spelledaren tillämpar det reglerna inte kan. En generator som inte kan köras med dem stoppar med `stop:` och skälet, och inget utkast skapas.

## Orakel: `oracles/`

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

- **Fråga:** `didact ask '…' --odds likely` kör `ask`-kontrollen. Svaret är dess utfall (ett band), och dess flaggor följer med.
- **Tillstånd:** det ligger i ett uppslag som kontrollen får som `oracle`. En kontroll ändrar det med `set: oracle.chaos += 1`.
- **Listor:** `lists: {names: […], method: sections, most: 3}` håller viktade listor på det uppslaget. `didact lists add|drop|roll|show` hanterar dem, och regler slår på dem med `pick`. `sections` slår fram ett avsnitt om fem rader, sedan en rad i det (en tom rad betyder välj själv); `uniform` ger varje rad samma chans.
- **Mer till kontrollen:** `didact ask '…' --with as_rule=true` skickar extra parametrar till oraklets kontroll.
- **Loggen:** varje svar numreras (`#o12`) och loggas, och `didact interpret o12 '…'` sparar vad det betydde. Kärnpaketets orakel `yes-no` är reservvalet.

## Generatorer och rollpersonsskapande: `generators/`, `chargen/`

Båda är procedurer som bygger ett **utkast**. De använder alla regelsteg (`roll`, `table`, `if`, `let`, `prompt`, …) plus dessa:

| Steg | Gör |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | lägger till ett uppslag i utkastet (nycklar `poi-1`, `poi-2`, …); ett fält eller en länk som anger en nyckel som paketet skrev (`key:`, eller ett `as:`-namn) blir det uppslagets id vid commit, så välj nycklar som inget fält har som text (en entitet utan någotdera har ingen att byta ut); `from: "@relic.id"` gör att det utgår från en post i kompendiet (dess typ, namn och fält) |
| `choose: {from: [a, b], as: x}` (eller `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | ett val; i guidat läge väntar utkastet på `choose`; `exclude` utesluter tidigare val (ett slaget slås om); `records:` lägger till uppslagen av den typen här, efter id (skapade under spelet); `answer:` gör valet utan att fråga när dess värde är ett av alternativen (en rollpersons egen väg) |
| `choose_or_roll: {table: backgrounds, as: background}` | ett val som tärningarna kan göra; en vald posts data är `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | slår värden till rollpersonen |
| `swap: {among: [STR, DEX, WIL], optional: true}` | byt plats på två värden, eller behåll |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | fördela en fast uppsättning |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | köp värden inom en budget (`default: random` spenderar den slumpvis i slumpläge) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | en lista hamnar i inventariet; en mappning sätter fält (listor läggs ihop) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | lägger till i ett fält på rollpersonen (eller på en entitet i utkastet): tal adderas, allt annat läggs till i en lista; att inget finns att lägga till går bra |
| `remove: {field: talents, value: "@old"}` | tar bort något från ett listfält (en utbytt talang, ett avslutat band); att inget finns att ta bort går bra |
| `roll_tables: [physique, vice]` | slår på tabeller till `traits`; en posts `data.gear` hamnar i inventariet och `data.add: {gold: 20}` lägger till i fält |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | namnet; `name: {prompt: …}` utan något att slå fram från väntar på ett, även i slumpläge |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | en fråga där vilket svar som helst duger (ett mål, namnet på ett annat uppslag): utkastet väntar på den, även i slumpläge, om den inte är ifylld i förväg; `field:` sparar svaret |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | en pointcrawl: ett loggat tärningsdropp, vägar (alltid sammanhängande), avstånd, dolda vägar (se nedan) |

Kartsteget tar fler nycklar, för bokens tärningsdroppsprocedurer:

| Nyckel | Gör |
|---|---|
| `regions: terrain` | de här entiteterna droppas också; varje plats hamnar i den närmaste (dess `region`) |
| `hidden: 6`, `conditional: 5` | en d6 per väg: på eller över talet blir det en dold eller villkorad väg (dolda vägar hålls borta från spelarnas karta) |
| `describe: [path-feature, path-condition]` | tabeller som slås för varje väg, sparade som dess `details` |
| `entrance: true`, `exit: true` | platsen närmast kanten är ingången; resten numreras från den längs vägarna (`map.n`), vägarna leder bort från den, och utgången är en avlägsen plats nära en kant, numrerad sist |
| `number: "{@dungeon_name}, room {@n}"` | döper om de numrerade platserna (deras utkastnycklar följer med: `room-1` är rum 1) |

En tärningsdroppstabell kan ange nästa tabeller i sina posters data, så att proceduren läses som boken: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, sedan `table: "{@drop.what}"`. Listfält som inte är satta (conditions, lists, tags) läses som tomma listor, så `'deprived' in @who.conditions` fungerar från början.

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

Ett rollpersonsskapande med `advances:` ändrar ett uppslag i stället för att skapa ett: systemets procedur för ny nivå.

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

- **Ett uppslag:** en generator med `creates: npc` bygger det uppslaget så som rollpersonsskapande bygger en rollperson (`apply`, `add`, `name`, `field:`); dess `entity`-steg lägger till uppslag bredvid, och en länk `to: character` pekar på det.
- **Köra:** `gen run` och `char new` skapar ett utkast (`#g7`, `#c3`) och skriver ingenting. Ett `stop:` avslutar det utan att något utkast skapas: under ett `if:` som läser en kampanjoption pekar dess tips på optionerna (`didact session zero`); annars säger dess egna ord vad man gör i stället.
- **Bestämma:** `--prefill '{…}'` bestämmer saker i förväg, via namnet ett steg binder (`as:`): ett enskilt värde besvarar varje förekomst, en lista en förekomst per element (en lista för `choose` med `count` är hela valet). `let`-värden kan också förifyllas (`{"hp": 6}`), och för ett namn, ett `ask`-steg eller ett `let`-steg behålls vilken text som helst precis som den angavs. Ett värde för ett val bland kända alternativ (ett `choose`-steg, en tabells post) blir det alternativ som det anger, ordagrant eller med annat skiftläge, via postens `id` eller via ett slag som landar på posten (`{"group": 3}`), och tar med sig postens data; ett värde som ligger nära ett alternativ men inte är något av dem nekas med det närmaste som förslag, och vilket annat värde som helst är ett eget svar, utan data. `--auto` (eller `char new --mode random`) låter tärningarna avgöra resten. Annars väntar utkastet vid varje val.
- **Beskriva:** ett val säger vad varje alternativ betyder, för spelaren som väljer: en tabellposts `note:` eller dess tabells `about:`, annars kompendieposten den anger (`id` i dess data), eller den som alternativet självt är (ett val bland kompendie-id:n visar vars och ens namn): dess fält `tagline` och `summary`, `description` eller `effect`, annars dess texts första stycke.
- **Gå tillbaka:** `char back` (eller `gen back`) tar tillbaka det senaste svaret, slaget eller den senaste redigeringen, så att utkastet ställer den frågan igen; slagen som steget gjorde markeras som ångrade.
- **Återuppta:** ett återupptaget utkast spelar upp sitt spår igen: varje värde som slagits eller valts, vart och ett använt en gång och i ordning (kartans tärningsdropp också), så inget slås två gånger och inget som redan bestämts ändras.
- **Skriva:** `commit` skriver uppslagen, kontrollerade mot sina ark.
- **Utveckla:** ett `advances:`-utkast börjar från en kopia av uppslaget (med standardvärdena från dess ark), dess steg läser uppslaget som `@who` och utkastets värden som `@character.*`, och `commit` skriver bara det som ändrades, kontrollerat som vid `set`; uppslag från dess `entity`-steg (tråden för ett nytt band) skapas bredvid: en länk `to: character` pekar på uppslaget, och ett fält som anger en nyckel innehåller det uppslagets id, som när en rollperson skapas (`apply: {blood: "@pool"}`). Ett `stop:` säger varför inte än (inte tillräckligt med XP), och inget utkast skapas. Ett system vars utveckling är en enda regel anger den i stället i sitt rollpersonsskapande: `advance: {rule: grow}`.
- **Lägen:** `modes: [guided]` gör att en procedur bara går steg för steg: `--mode random` nekas.

## Kompendium, referens och ordlista

- **Kompendieposter** skrivs som `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Ett värde som `"roll 2d8"` slås när posten skapas. Kör `didact spawn troll`, eller hämta in ett pakets poster i världen med `didact compendium import <pack>` (`--type loc`, och `--tag coast` för dem som har varje angiven tagg).
- **För flera system:** en nyckel på översta nivån hamnar där `set` lägger den: i systemets block när dess ark har det fältet, annars i `fields`. En post som en spelvärld skriver för mer än ett system ger varje systems siffror i ett eget block (`mechanics: {my-system: {hp: 12}}`): `pack validate` kontrollerar varje block mot det systemets ark när det är installerat, och noterar en nyckel på översta nivån som både det arket och cores ark har. Det ett block säger gäller: bredvid `mechanics: {my-system: {role: tactician}}` är en `role: innkeeper` på översta nivån cores fält, liksom allt under `fields:`. Ett block som anger paketet som valideras kontrolleras mot det paketet som det ligger i sin mapp.
- **Referensavsnitt** läggs i `reference/*.md`, med front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` hittar dem; en fras inom citattecken som inte finns där provas ord för ord.
- **Ordlistan** är `glossary.yaml`: `term: definition`, eller en lista av `{term, definition, aliases, see}`. `didact define <term>` läser den.

## Tester: `tests/`

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

## Dela och ta bort paket

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Ett paket som anger `redistributable: false` kan inte exporteras.
- **core** är en del av Didact och alltid på: varje system bygger på det, så det kan inte inaktiveras eller avinstalleras.
- De andra paketen som följer med Didact är `.didactpack`-filer i dess mapp `packs/`. `pack list` visar dem tills de är installerade, och när du installerar ett följer de medföljande paket det behöver med.
- `pack update` letar efter nyare versioner i Didacts mapp `packs/` och på GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` anger ett annat ställe, eller inget för att inte leta alls). En ny version installeras bredvid den gamla: kampanjer behåller sin tills `didact campaign upgrade`.
- Bara ett spelsystem används i taget: den öppna världens. En värld behåller systemet den skapades med (`didact world new <id> --system <pack>`; en värld som skapats utan system tar det första den får, med `pack enable` eller `world set system=`), dess kampanjer spelas med det, och ett paket som behöver ett annat system (en spelvärld skriven för det) kan inte läggas till: ett annat system spelas i en egen värld.
- `uninstall` vägrar så länge en värld eller kampanj använder paketets enda kopia (`--force` tar bort det ändå). Det kan inte ångras: installera .didactpack-filen igen.

## Från regelbok till paket: checklistan

Gå igenom bokens mekanik i den här ordningen. Varje del motsvarar något ovan:

1. **Utfall:** hur ett slag lyckas (en kontroll: `success`, `bands`, `auto`).
2. **Tärningar:** ovanliga tärningar, symboler, steg (`dice.yaml`, namngivna tärningar, kedjor).
3. **Formuläret:** grundegenskaper, härledda värden (`schemas/`, härledda fält).
4. **Resurser:** KP, tur, momentum (resurs- och räknarfält; `set`-steg).
5. **Tillstånd:** lägen och vad de gör (`conditions`-fält; `if`-steg).
6. **Strid:** attacker, skada, initiativ (handlingar; `bag`/`deck` för turordning).
7. **Procedurer:** utforskning, resor, tid mellan äventyr (procedurer med uppmaningar).
8. **Tabeller:** varje slumptabell (`tables/`; `pack import` för Markdown-tabeller).
9. **Bestiariet:** monster och SLP (`compendium/`).
10. **Föremål:** utrustning, besvärjelser, reliker (`compendium/`, slots-fält).
11. **Råd till SL:** principer och råd (`GUIDE.md`, `reference/`, `guidance:` på typer).
12. **Rollpersonsskapande:** hur man skapar en rollperson (en `chargen/`-procedur, eller `roll:` på varje fält).

Ange sidor med `source:` överallt, så att luckor syns. Lägg till ett smoke-play-test som skapar en rollperson, slår en kontroll, strider och kör en procedur.
