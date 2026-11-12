<!-- translated from b1dfa1159ff4 -->
# Pakker

En pakke er et spillsystem, et orakel, en spillverden, et eventyr eller et tillegg, skrevet som YAML-filer pluss en valgfri Python-plugin. Denne veiledningen viser hvordan du skriver en: hvordan du gjør en regelbok om til en pakke, eller legger til ditt eget husinnhold.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

En pakke kan også lages av det som ligger i biblioteket ditt. `didact pack new my-brew --from-overlay my-system` gjør husinnholdet ditt for et system (`compendium add`, oppslag holdt med `--scope system`, lore) om til et tillegg, og `didact world export --as setting` gjør en verden om til en spillverdenspakke: personene, stedene og loren som kompendieoppføringer og pakkelore, hentet inn i en annen verden med `compendium import`. Begge utelater hemmeligheter og SL-notatene med mindre `--secrets`, og ingen av dem er merket som delbar før du setter lisensen.

## Oppbygning

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

En fil inneholder ett element, en liste med elementer eller flere elementer skilt med `---`. Hvert element oppgir ID-en sin med nøkkelen for sin sort: `table: weather`, `check: save`, `type: pc`, eller `id: troll` for oppføringer i kompendiet. Vis til elementer som `pack.id` (`my-system.save`), eller med bare ID-en når bare én aktivert pakke har den.

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

En hack oppgir basisen sin i `extends` og inneholder bare det som avviker:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Elementet dens med samme ID erstatter basisens, uansett sort (en tabell, en regel, en oppføring i kompendiet, en referanseseksjon, et ordlistebegrep). Hackens `settings` legges oppå basisens, nøkkel for nøkkel: en nøkkel den setter, erstatter basisens verdi i sin helhet (`names`-tabellene dens trer i stedet for basisens), og basisens regler leser også hackens verdier. `hides` utelater resten, som hacken ikke har bruk for: `*` treffer en hvilken som helst tegnfølge, det siste mønsteret som treffer en ID, avgjør, og et mønster som begynner med `!`, beholder elementet. Det hacken erstatter, blir aldri skjult. Sortene er `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` og `term`. `didact pack validate` advarer om et mønster som ikke treffer noe.

## Uttrykk

Alle betingelser og formler bruker terningspråket (`didact guide dice`), pluss:
- **Verdier:** `@name` leser en verdi: `@roll`, `@who.STR`, `@settings.x`. `$name` setter først inn teksten til en parameter, så `@who.$attr` blir `@who.STR`. Les en parameter med fri tekst som `@name`, ikke i anførselstegn (`'$name'`): en apostrof i teksten ville avslutte dem (`pack validate` advarer).
- **Logikk:** `and`, `or`, `not` og `in` (`'deprived' in @who.conditions`).
- **Konstanter:** tekst (`'travel'`) og `true`/`false`.
- **Funksjoner:** `if(cond, a, b)` kaster bare for grenen den velger. `default(@thread.flashpoint, 0)` er verdien, eller reserveverdien når den ikke er satt. `sum`, `count` (`count(@roll.dice, 6)` teller seksere), `min`, `max`, `any` og `all` tar lister.

## Ark: `schemas/`

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

| Sort | Inneholder | Valg |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | en enkel verdi | min, max; `values` for enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` er verdien, `@hp.max` taket | range; min; max eller max_field; die |
| `counter` | et tall | min, max, thresholds, occupies (et slots-felt) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | gjenstander (`Rope` eller `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | som navnet sier | `to` (for refs), `allowed` |
| `derived` | beregnet, lagres aldri | expr |

Alle felter tar også `label`, `help`, `default`, `required` og `roll`: `new pc Hero --fill`, eller verdien `"roll"`, kaster det gjennom loggen. Typer fra pakken `core` inneholder systemuavhengig prosa i `fields`. Et systems typer inneholder tallene sine i `mechanics.<system>`. `set hero hp-=2` finner feltet, begrenser verdien og melder fra om eventuelt overløp. `+=` legger til i en liste: en `list` (som `slots`) beholder også en verdi som legges til igjen, `tags`, `conditions` og `refs` har den bare én gang, og `-=` fjerner alle kopiene.

**Hooks** sier hva som skjer når en verdi krysser en grense. De utløses ved hver endring (`set`, `inv`, et `set`-steg i en regel), men bare når grensen krysses: 3 → 0 utløser, 0 → 0 gjør det ikke. Redigeringer med `--force` hopper over dem.

| Hook | Utløses når |
|---|---|
| `on_zero` | et tall eller `{value}` når 0 |
| `on_full` (`when_full` på slots) | det når max, size eller capacity |
| `thresholds: {10: …, 20: …}` (counters) | det stiger forbi hvert merke |

En handling er tekst (et notat for LLM-en), `{set: {hp: 0}}` eller `{condition: paralyzed}` på samme oppslag, `{trigger: death}` (kjører den regelen med `who` = oppslaget), eller en liste med disse.

**Inventar** (`didact inv …`) virker på arkets `slots`-felt:
- **Plass:** gjenstander tar `size` × `count`, og counters som `occupies` feltet, tar verdien sin. Over `capacity` avvises med mindre `--force`.
- **Grupper:** `groups: {backpack: 6, body: 4}` gir hver gruppe sin egen plass og sine egne kolonner og summer: `@inventory.body.armor` er bare det som bæres på kroppen eller holdes i hånden, `@inventory.body.free` plassen gruppen har igjen.
- **Bruk:** `uses: 3` teller ned med `inv use`. `uses: d8` er en forbruksterning: 1–2 setter den ett trinn ned. En oppbrukt gjenstand forsvinner, med mindre den har `recharge` eller `keep: true`. Av flere gjenstander med samme navn betyr navnet den første; for å bruke opp en bruk (`inv use`, en regels `use:`, `set …uses-=1`) den første som har en igjen.
- **En gjenstands egne nøkler:** `didact set freya inventory.sword.damage=d10` (også `set: who.inventory.$item.damage` i en regel) endrer én av dem, med gjenstanden angitt slik `inv` angir den, med en del av navnet eller hele navnet, mellomrom og punktum også (`'inventory.12.7mm pistol.damage=d10'`, i anførselstegn for skallet); `uses` og `charges` teller som et `uses`-felt (`charges+=2` stopper ved maks), og plassen sjekkes slik `inv add` sjekker den. En regel leser en som `@{who.inventory.$item.damage}` (en forbruksterning som terningen sin, bruk som antallet sitt); en gjenstand eller nøkkel som ikke finnes, leses som fraværende, så `default(…)` gir reserveverdien sin.
- **Kompendium:** oppføringer av typen `item` (eller weapon, armor, relic, …, eller en egen type i pakken som utvider en av dem med `extends`) låner `inv add` detaljene sine, funnet via ID, navn eller et alias (deler to ett: oppgi den du mener, som `pack.id`); alle andre navn, `:` og alt, er gjenstandens eget navn.

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

Andre former:
- **Vektede lister:** `entries` som en liste, med `weight:` på hver oppføring.
- **Kolonner:** `columns: [a, b]` kaster for hver kolonne i en rad for seg. En enkel oppføring (ikke en liste) fyller alle kolonnene, så `columns: [first, second]` over en ordliste betyr «kast to ganger på denne lista». `labels: false` utelater kolonnenavnene fra resultatet («Abandon · Advantage»). `read: "It's a {first} {second} with {third} {fourth} inside."` leser kolonnene som en setning.
- **Oppslagstabeller:** `lookup: hp_lost`, eller `[odds, chaos]` for et 2D-diagram.
- **Duplikater:** `duplicates: reroll | keep | make_it_worse` for «kast to ganger».
- **To trinn:** en oppføring som kaster på en annen tabell (`{table: lightning}` i stedet for tekst, eller `then:` etter den), tar med seg dataene fra det kastet: en regel eller et utkast som får den oppføringen, leser begge, først oppføringens egne nøkler, deretter nøklene til den første tabellen som kastes etterpå. En `--prefill` kan nevne en oppføring lenger ned, på hvilken som helst dybde (`Ring of the Hunt`), med dataene til hver oppføring på veien: av to med samme navn gjelder den nærmeste (så den første), en som går videre, slår videre derfra, og en som ligner en av dem uten å være det, avvises, og den nærmeste nevnes. Et veiledet utkast tilbyr første steg når oppføringene sier hva de er (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): å velge en slår på neste tabell, slik et kast som lander på den gjør.
- **Les begge veier:** `both_ways: true` på en d66-tabell legger til den andre lesningen: 31 gir også 13, og leseren velger.
- **Hva en oppføring betyr:** `about: "Knows: {skills}. Also known as: {aka}."` fyller inn dataene til hver oppføring (en liste leses `a, b`; `{text}` er selve oppføringen) for å si hva den gir når et valg tilbyr den; en oppførings egen `note:` sier det i stedet. Uten noen av dem beskrives en oppføring der dataene har en `id` som navngir en oppføring i kompendiet, av den oppføringen.
- **Kortstokker og poser:** `deck: tarot` med `cards` (eller `standard: true`); `bag: initiative` med `tokens`.

Valideringen sjekker at hvert resultat terningene kan gi, lander på en oppføring.

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

Handlinger og prosedyrer er lister med steg, og utløsere er steg med en `when:`-betingelse. Stegene er:

| Steg | Gjør |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | et logget kast; binder `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; en `{…}` fylles inn først, som i all tekst, så terninger en verdi holder som tekst, blir slått (`{@{who.inventory.$item.damage}}`), og loggen viser dem: en verdi som ikke er terninger, avvises, likeså `roll: "@die"` med slik tekst, som ikke slår noe; et sett kast (`{d8, d6}kh1`) forblir ett |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | beregner verdier; som med `value` i `set` er tekst med `{…}` en mal, og et enkelt ord er tekst; i all tekst som fylles ut, skriver `{{` og `}}` selve klammen |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (eller `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | endrer et oppslag: validert, begrenset, kan angres; `set: who.$attr` setter feltet som en parameter oppgir, og `set: who.inventory.$item.damage` en nøkkel på en gjenstand som oppslaget bærer (se Inventar); `-=` tar en verdi ut av en liste, og en den ikke inneholder, endrer ingenting (en merknad sier det; en den aldri kunne inneholdt, avvises); `unset:` fjerner et felt, slik `set --unset` gjør |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | gir et oppslag en gjenstand eller tar en fra det, slik `inv add` og `inv drop` gjør: detaljene kommer fra kompendiet, en entydig del av navnet holder, og plassen og feltets hooks sjekkes |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | bruker en båret gjenstand slik `inv use` gjør: bruk eller ladninger teller ned, en forbruksterning kastes og går ett trinn ned på 1–2, og en som går tom, forsvinner med mindre den lades opp igjen eller beholdes; av flere med det navnet den første som har en bruk igjen; binder `@torch.out` (siste bruk er brukt), `@torch.gone` (ingenting av den er igjen), `@torch.left`, `@torch.die` og `@torch.rolled` (`as:` er `use` som standard) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | lager et oppslag med en gang, beskrevet som i `entity`-steget i et utkast (nedenfor) og sjekket mot arket sitt; `as:` (ellers dens `key`, ellers dens type) binder det som et oppslag, lest og satt som en `ref`-parameter (`pool: "@bleeding"`, `@bleeding.name`), og er aldri navnet på en parameter; uten `key:` tas ikke noe felt for en nøkkel (`kind: track` blir stående slik det er skrevet); finnes det allerede et oppslag med den typen og det navnet her, tas det som det er, så en regel som kjøres igjen, lager ingenting nytt |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | kjører en prøve og binder utfallet |
| `do: other-action`, `with: {…}`, `as: trip` | kjører en annen regel; `@trip` er utfallet dens og `@trip.<name>` det den bandt (`@trip.found` for dens `let: {found: 2}`, `@trip.luck` for dens `roll: d6`, `as: luck`); `as:` er ID-en dens som standard |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | et logget tabellkast; binder teksten og oppføringens `data` (`@scar.<key>`, og nøklene i en mapping via stien: `@scar.cost.hp`), sammen med dataene til enhver tabell som kastes etterpå; en liste med gjenstander (`[Rope, {name: Laser, damage: d8}]`) leses som navnene deres (`count(@scar.gear)`, `'Laser' in @scar.gear`), og gitt slik den er til et steg (`apply: "@scar.gear"`) er den selve gjenstandene; en liste med andre mappinger kan bare et steg lese |
| `table: "setting-{@drop.difficulty}-terrain"` | en beregnet tabell: `{…}` og `$param` fylles inn |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | flere resultater som en liste (`distinct` kaster om gjentakelser) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | forgreninger |
| `repeat: "@count"`, `as: i`, `steps: […]` | en løkke: stegene så mange ganger, med `@i` som teller fra 1 |
| `for: pcs` (eller `party`), `as: member`, `steps: […]` | stegene én gang for hver spillerperson (eller hvert gruppemedlem), som `@member`: et oppslag, slik som det `entity:` binder (`@member.name`, `set: member.fatigue`); `as:` tar aldri navnet til en parameter, så regelens egen `who` forblir urørt |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | utdata for LLM-en |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (eller `every: 1 day`) | en påminnelse som forfaller etter hvert som spilltiden går, slik `didact remind` setter dem |
| `reroll: roll`, `keep_if: "@face == 6"` | kaster om noen av terningene i et kast (push-mekanikker) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | kaster på en listeverdi (et orakels lister): binder oppføringen, `@who.choose` (en tom linje) og `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | kaster en tellers minkende pulje slik `track roll` gjør (terninger som viser 1-3, faller bort; `drop`-terninger fjernes først, `extra`-terninger kastes med) eller fjerner bare terninger (`mode: drop`: et push, et kryss); koblede faser og puljens hendelse følger med; binder `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

En prøves utfall kan leses av regelen som kjørte den (`check: … as: answer` gir `@answer`), og det samme kan markeringene: `'random-event' in @answer.flags`. Verdier i `with:` evalueres når de inneholder `@`, fylles inn når de inneholder `$param` eller `{…}` («Does $npc flee?»), og sendes videre slik de er skrevet ellers. En regel med en `oracle`-parameter får kampanjeorakelets tilstandsoppslag uten å bli bedt om det. En `ref`-parameter med `to: monster` tar et oppslag av den typen: et navn som et annet oppslag deler (en fiendes pulje, navngitt etter kortet dens), er det av den typen.

Utløsere kjører av seg selv når hendelsen deres skjer, og bare hvis `when:` holder:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Enhver regel (også en generator og personskaping) kan lese `@system` (ID-en til systemet som spilles i verdenen, så en spillverden skrevet for to systemer kan skille mellom dem), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` og `@time.is_night`, og med en kalender med måneder også `@time.month`, `@time.month_name`, `@time.day_of_month` og `@time.year`; mens en kamp pågår, også `@combat.round` og `@combat.fighters` (ID-ene til dem som er med i den). En tidsutløser kan også lese `@time.passed`, sekundene som nettopp gikk, en `combat_start`- eller `combat_end`-utløser leser kampen som begynner eller slutter (`combat start` og `combat end` kjører dem; en kjemper som forlater kampen, avslutter den ikke), og en regel som kjøres av en utløser, leser det utløseren leser. En utløser med påkrevde parametere kjøres bare av `didact do` eller en felthook (`who` = oppslaget). Utløsere med `on: manual` kjører bare når de kalles. `for: pcs` (eller `party`) kjører en utløser én gang for hver spillerperson (eller hvert gruppemedlem), som `who`: erfaring etter hver økt, for eksempel. En utløser som mislykkes, stopper kommandoen som utløste den, og sier hvilken utløser det var og hvordan man fortsetter uten den (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalenderen ligger i en pakkes `settings`: en spillverdenspakkes kalender går foran systemets, og en verdens egen (`calendar:` i dens `world.yaml`) foran begge:

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

`leap: 4` gjør en måned én dag lengre hvert 4. år, og `leap: [4, 100, 400]` hvert 4., men ikke hvert 100., men likevel hvert 400.: hvert tall overstyrer det forrige. `weekday` angir hvilken ukedag starten er (ellers ukens første), og `year` er hvordan en dato skriver året sitt, både i datoene Didact viser og i dem den leser (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` sjekker alle tre. En kampanje kan begynne på en annen dato i kalenderen, før starten eller etter: `didact campaign new <id> --date '4 July 1902'`, eller `didact time set '<date>'` fram til kampanjens første økt. En ukedag skrevet foran datoen sjekkes: datoen avgjør, og en merknad sier fra når den faller på en annen.

Valg er systemets varianter og valgfrie regler, som hver kampanje velger i sesjon null:

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

`didact campaign profile lethality=deadly supplies=on` lagrer dem (eller webappens side Innstillinger). Regler, personskaping og generatorer leser dem (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): et svar går foran det et annet valg medfører, som igjen går foran standarden. Det et valg medfører, følges hele veien (en stemning som setter dødeligheten, setter også det den dødeligheten medfører), og av to slike følger vinner den nærmeste. Oppsummeringen viser dem som avviker fra standarden, med hva de betyr, så spillederen kan bruke det reglene ikke kan. En generator som ikke kan kjøre med dem, stopper med `stop:` og årsaken, og det lages ikke noe utkast.

## Orakler: `oracles/`

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

- **Spørre:** `didact ask '…' --odds likely` kjører `ask`-prøven. Svaret er utfallet (et bånd), og markeringene følger med.
- **Tilstand:** den ligger i et oppslag som prøven får som `oracle`. En prøve endrer den med `set: oracle.chaos += 1`.
- **Lister:** `lists: {names: […], method: sections, most: 3}` holder vektede lister på det oppslaget. `didact lists add|drop|roll|show` håndterer dem, og regler kaster på dem med `pick`. `sections` kaster først for et avsnitt på fem linjer, så for en linje i det (en tom linje betyr velg); `uniform` gir alle linjer samme sjanse.
- **Mer til prøven:** `didact ask '…' --with as_rule=true` sender ekstra parametere til orakelets prøve.
- **Loggen:** hvert svar nummereres (`#o12`) og logges, og `didact interpret o12 '…'` tar vare på hva det betydde. Kjernepakkens `yes-no`-orakel er reserven.

## Generatorer og personskaping: `generators/`, `chargen/`

Begge er prosedyrer som bygger et **utkast**. De bruker alle regelsteg (`roll`, `table`, `if`, `let`, `prompt`, …) pluss disse:

| Steg | Gjør |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | legger et oppslag til i utkastet (nøkler `poi-1`, `poi-2`, …); et felt eller en lenke som nevner en nøkkel pakken skrev (`key:`, eller et `as:`-navn), blir det oppslagets ID ved godkjenning, så velg nøkler som ikke noe felt har som tekst (en entitet uten noen av delene har ingen som byttes ut); `from: "@relic.id"` lar det ta utgangspunkt i en oppføring i kompendiet (typen, navnet og feltene dens) |
| `choose: {from: [a, b], as: x}` (eller `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | et valg; i veiledet modus venter utkastet på `choose`; `exclude` utelukker tidligere valg (et kastet valg kastes på nytt); `records:` legger til oppslagene av den typen her, etter id (laget i spill); `answer:` tar valget uten å spørre når verdien er et av alternativene (en persons egen vei) |
| `choose_or_roll: {table: backgrounds, as: background}` | et valg terningene kan ta; en valgt oppførings data er `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | kaster inn i personen |
| `swap: {among: [STR, DEX, WIL], optional: true}` | bytt to verdier, eller behold |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | fordel en fast rekke |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | kjøp verdier innenfor et budsjett (`default: random` bruker det tilfeldig i tilfeldig modus) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | en liste går til inventaret; en mapping setter felter (lister legges sammen) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | legger til i et felt på personen (eller på en enhet i utkastet): tall legges sammen, alt annet føyes til en liste; ingenting å legge til er greit |
| `remove: {field: talents, value: "@old"}` | fjerner noe fra et listefelt (et utbyttet talent, et avsluttet bånd); ingenting å fjerne er greit |
| `roll_tables: [physique, vice]` | kaster på tabeller inn i `traits`; en oppførings `data.gear` går til inventaret, og `data.add: {gold: 20}` legger til i felter |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | navnet; `name: {prompt: …}` uten noe å kaste fra venter på et, selv i tilfeldig modus |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | et spørsmål der ethvert svar holder (et mål, navnet på et annet oppslag): utkastet venter på det, selv i tilfeldig modus, med mindre det er fylt ut på forhånd; `field:` lagrer svaret |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | en pointcrawl: et logget terningslipp på kartet, veier (alltid sammenhengende), avstander, skjulte veier (se nedenfor) |

Kartsteget tar mer, for bøkenes prosedyrer med terningslipp:

| Nøkkel | Gjør |
|---|---|
| `regions: terrain` | disse enhetene slippes også; hvert sted hører til den nærmeste (sin `region`) |
| `hidden: 6`, `conditional: 5` | en d6 per vei: på eller over tallet, en skjult eller betinget vei (skjulte veier holdes utenfor spillernes kart) |
| `describe: [path-feature, path-condition]` | tabeller som kastes for hver vei, lagret som veiens `details` |
| `entrance: true`, `exit: true` | stedet nærmest kanten er inngangen; resten nummereres fra den langs veiene (`map.n`), veiene fører bort fra den, og utgangen er et fjernt sted nær en kant, nummerert sist |
| `number: "{@dungeon_name}, room {@n}"` | gir de nummererte stedene nye navn (nøklene i utkastet følger med: `room-1` er rom 1) |

En tabell for terningslipp kan nevne de neste tabellene i oppføringenes data, så prosedyren leses som i boka: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, deretter `table: "{@drop.what}"`. Listefelter som ikke er satt (conditions, lists, tags), leses som tomme lister, så `'deprived' in @who.conditions` virker fra starten.

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

En personskaping med `advances:` endrer et oppslag i stedet for å lage et: systemets prosedyre for nytt nivå.

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

- **Ett oppslag:** en generator med `creates: npc` bygger det oppslaget slik personskaping bygger en person (`apply`, `add`, `name`, `field:`); `entity`-stegene dens legger til oppslag ved siden av, og en lenke `to: character` peker på det.
- **Kjøring:** `gen run` og `char new` lager et utkast (`#g7`, `#c3`) og lagrer ingenting. Et `stop:` avslutter den uten at noe utkast lages: under et `if:` som leser en kampanjeinnstilling, peker tipset på innstillingene (`didact session zero`); ellers sier dens egne ord hva man gjør i stedet.
- **Bestemme:** `--prefill '{…}'` bestemmer ting på forhånd, ut fra navnet et steg binder (`as:`): én verdi svarer på alle forekomster, en liste på én forekomst hver (en liste for `choose` med `count` er hele valget). `let`-verdier kan også fylles ut på forhånd (`{"hp": 6}`), og et navn, en `ask` eller en `let` beholder all tekst slik den er oppgitt. En verdi for et valg blant kjente alternativer (en `choose`, en tabelloppføring) er alternativet den nevner, slik det er skrevet eller med andre store og små bokstaver, via oppføringens `id`, eller via et kast som lander på det (`{"group": 3}`), og tar med seg dataene til den oppføringen; en verdi som ligger nær et alternativ uten å være noen av dem, avvises med henvisning til det nærmeste, og enhver annen verdi er et eget svar, uten data. `--auto` (eller `char new --mode random`) lar terningene bestemme resten. Ellers venter utkastet ved hvert valg.
- **Beskrive:** et valg sier hva hvert alternativ betyr, for spilleren som velger: en tabelloppførings `note:` eller tabellens `about:`, ellers oppføringen i kompendiet den navngir (dataenes `id`), eller den alternativet selv er (et valg blant ID-er fra kompendiet viser navnet til hver): dens `tagline` og `summary`, dens `description` eller `effect`, ellers første avsnitt av teksten.
- **Gå tilbake:** `char back` (eller `gen back`) tar tilbake det siste svaret, kastet eller redigeringen, så utkastet stiller det spørsmålet igjen; kastene det gjorde, markeres som angret.
- **Gjenoppta:** et gjenopptatt utkast spiller av sporet sitt på nytt: hver verdi som er kastet eller valgt, brukes én gang og i rekkefølge (kartets terningslipp også), så ingenting kastes to ganger og ingenting som allerede er bestemt, endres.
- **Lagring:** `commit` lagrer oppslagene, sjekket mot arkene deres.
- **Utvikling:** et `advances:`-utkast starter fra en kopi av oppslaget (med standardverdiene fra arket), stegene leser oppslaget som `@who` og utkastets verdier som `@character.*`, og `commit` lagrer bare det som ble endret, sjekket som ved `set`; oppslag fra `entity`-stegene (tråden til et nytt bånd) opprettes ved siden av: en lenke `to: character` peker på oppslaget, og et felt som nevner en nøkkel, inneholder ID-en til oppslaget med den nøkkelen, som ved personskaping (`apply: {blood: "@pool"}`). En `stop:` sier hvorfor ikke ennå (ikke nok XP), og det lages ikke noe utkast. Et system der utviklingen er én enkelt regel, angir den i stedet i personskapingen sin: `advance: {rule: grow}`.
- **Moduser:** `modes: [guided]` gjør at en prosedyre bare går steg for steg: `--mode random` avvises.

## Kompendium, håndbok og ordliste

- **Oppføringer i kompendiet** skrives som `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. En verdi som `"roll 2d8"` kastes når oppføringen lages. Kjør `didact spawn troll`, eller hent en pakkes oppføringer inn i verdenen med `didact compendium import <pack>` (`--type loc`, og `--tag coast` for dem som har hver oppgitte tagg).
- **For flere systemer:** en nøkkel på øverste nivå havner der `set` legger den: i systemets blokk når arket har det feltet, ellers i `fields`. En oppføring som en spillverden skriver for mer enn ett system, gir hvert systems tall i en egen blokk (`mechanics: {my-system: {hp: 12}}`): `pack validate` sjekker hver blokk mot arket til det systemet når det er installert, og noterer en nøkkel på øverste nivå som både det arket og cores ark har. Det en blokk sier, gjelder: ved siden av `mechanics: {my-system: {role: tactician}}` er en `role: innkeeper` på øverste nivå cores felt, slik alt under `fields:` er det. En blokk som nevner pakken som valideres, sjekkes mot den pakken slik den ligger i mappen sin.
- **Håndboksavsnitt** ligger i `reference/*.md`, med front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` finner dem; en frase i anførselstegn som ikke finnes der, prøves ord for ord.
- **Ordlisten** er `glossary.yaml`: `term: definition`, eller en liste med `{term, definition, aliases, see}`. `didact define <term>` leser den.

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

## Dele og fjerne pakker

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- En pakke som oppgir `redistributable: false`, kan ikke eksporteres.
- **core** er en del av Didact og alltid på: alle systemer bygger på den, så den kan ikke deaktiveres eller avinstalleres.
- De andre pakkene som følger med Didact, er `.didactpack`-filer i `packs/`-mappen dens. `pack list` viser dem til de er installert, og installerer du en, kommer pakkene den trenger som også følger med, på plass samtidig.
- `pack update` ser etter nyere versjoner i Didacts `packs/`-mappe og på GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` peker på et annet sted, eller ingenting for ikke å lete). En ny versjon installeres ved siden av den gamle: kampanjer beholder sin til `didact campaign upgrade`.
- Bare ett spillsystem er i bruk om gangen: den åpne verdenens. En verden beholder systemet den ble opprettet med (`didact world new <id> --system <pack>`; en verden som er opprettet uten system, tar det første den får, med `pack enable` eller `world set system=`), kampanjene dens spilles med det, og en pakke som trenger et annet system (en spillverden skrevet for det), kan ikke legges til: et annet system spilles i en egen verden.
- `uninstall` nekter så lenge en verden eller kampanje bruker pakkens eneste kopi (`--force` fjerner den likevel). Det kan ikke angres: installer .didactpack-filen på nytt.

## Fra regelbok til pakke: sjekklisten

Gå gjennom bokas mekanikker i denne rekkefølgen. Hver av dem svarer til noe ovenfor:

1. **Avgjøring:** hvordan et kast lykkes (en prøve: `success`, `bands`, `auto`).
2. **Terninger:** uvanlige terninger, symboler, trinn (`dice.yaml`, navngitte terninger, kjeder).
3. **Arket:** egenskaper, avledede tall (`schemas/`, avledede felter).
4. **Ressurser:** HP, flaks, momentum (resource- og counter-felter; `set`-steg).
5. **Tilstander:** tilstander og hva de gjør (`conditions`-felter; `if`-steg).
6. **Kamp:** angrep, skade, initiativ (handlinger; `bag`/`deck` for turrekkefølgen).
7. **Prosedyrer:** utforsking, reise, nedetid (prosedyrer med spørsmål).
8. **Tabeller:** alle tilfeldige tabeller (`tables/`; `pack import` for Markdown-tabeller).
9. **Bestiariet:** monstre og bifigurer (`compendium/`).
10. **Gjenstander:** utstyr, trylleformler, relikvier (`compendium/`, slots-felter).
11. **Råd til SL:** prinsipper og råd (`GUIDE.md`, `reference/`, `guidance:` på typer).
12. **Personskaping:** hvordan man lager en person (en `chargen/`-prosedyre, eller `roll:` på hvert felt).

Oppgi sidetall med `source:` overalt, så hull blir synlige. Legg til en prøvespilltest som lager en person, kaster en prøve, slåss og kjører en prosedyre.
