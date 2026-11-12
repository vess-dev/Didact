<!-- translated from b1dfa1159ff4 -->
# Pakker

En pakke er et spilsystem, et orakel, en spilverden, et eventyr eller et tillæg, skrevet som YAML-filer plus et valgfrit Python-plugin. Denne guide viser, hvordan du skriver en: hvordan du gør en regelbog til en pakke eller tilføjer dit eget husindhold.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

En pakke kan også laves ud fra det, der er i dit bibliotek. `didact pack new my-brew --from-overlay my-system` gør dit husindhold til et system (`compendium add`, opslag ført med `--scope system`, lore) til et tillæg, og `didact world export --as setting` gør en verden til en spilverdenspakke: dens personer, steder og lore som indgange i kompendiet og pakke-lore, som `compendium import` henter ind i en anden verden. Begge udelader hemmeligheder og SL's noter, medmindre `--secrets`, og ingen af dem er markeret som delbar, før du angiver dens licens.

## Opbygning

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

En fil rummer ét element, en liste af elementer eller flere elementer adskilt af `---`. Hvert element angiver sit id med sin slags nøgle: `table: weather`, `check: save`, `type: pc` eller `id: troll` for indgange i kompendiet. Henvis til elementer som `pack.id` (`my-system.save`), eller med det rene id, når kun én aktiveret pakke har det.

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

Et hack angiver sin basis i `extends` og rummer kun det, der afviger:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Dets element med samme id erstatter basens, uanset slags (en tabel, en regel, en indgang i kompendiet, et referenceafsnit, et begreb i ordlisten). Dets `settings` lægges oven på basens, nøgle for nøgle: en nøgle, som hacket sætter, erstatter basens værdi helt (dets `names`-tabeller træder i stedet for basens), og basens regler læser også hackets værdier. `hides` fjerner resten, som hacket ikke har brug for: `*` matcher en vilkårlig række tegn, det sidste mønster, der matcher et id, afgør sagen, og et mønster, der begynder med `!`, beholder elementet. Det, hacket erstatter, skjules aldrig. Slagsene er `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` og `term`. `didact pack validate` advarer om et mønster, der ikke matcher noget.

## Udtryk

Alle betingelser og formler bruger terningsproget (`didact guide dice`), plus:
- **Værdier:** `@name` læser en værdi: `@roll`, `@who.STR`, `@settings.x`. `$name` indsætter først en parameters tekst, så `@who.$attr` bliver til `@who.STR`. Læs en parameter med fri tekst som `@name`, ikke i anførselstegn (`'$name'`): en apostrof i dens tekst ville afslutte dem (`pack validate` advarer).
- **Logik:** `and`, `or`, `not` og `in` (`'deprived' in @who.conditions`).
- **Konstanter:** tekst (`'travel'`) og `true`/`false`.
- **Funktioner:** `if(cond, a, b)` slår kun for den gren, den vælger. `default(@thread.flashpoint, 0)` er værdien, eller reserveværdien, når den ikke er sat. `sum`, `count` (`count(@roll.dice, 6)` tæller seksere), `min`, `max`, `any` og `all` tager lister.

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

| Slags | Rummer | Tilvalg |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | en enkel værdi | min, max; `values` for enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` er værdien, `@hp.max` loftet | range; min; max eller max_field; die |
| `counter` | et tal | min, max, thresholds, occupies (et slots-felt) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | genstande (`Rope` eller `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | som navnet siger | `to` (for refs), `allowed` |
| `derived` | beregnet, gemmes aldrig | expr |

Alle felter tager også `label`, `help`, `default`, `required` og `roll`: `new pc Hero --fill`, eller værdien `"roll"`, slår det gennem loggen. Typer fra pakken `core` rummer systemuafhængig prosa i `fields`. Et systems typer rummer dets tal i `mechanics.<system>`. `set hero hp-=2` finder feltet, begrænser værdien og melder om eventuelt overløb. `+=` tilføjer til en liste: en `list` (som `slots`) beholder også en værdi, der tilføjes igen, `tags`, `conditions` og `refs` rummer den kun én gang, og `-=` fjerner alle kopier.

**Hooks** siger, hvad der sker, når en værdi krydser en grænse. De udløses ved hver ændring (`set`, `inv`, en regels `set`-trin), men kun når grænsen krydses: 3 → 0 udløser, 0 → 0 gør ikke. Redigeringer med `--force` springer dem over.

| Hook | Udløses, når |
|---|---|
| `on_zero` | et tal eller `{value}` når 0 |
| `on_full` (`when_full` på slots) | det når sit max, sin size eller sin capacity |
| `thresholds: {10: …, 20: …}` (counters) | det stiger forbi hver grænse |

En handling er tekst (en note til LLM'en), `{set: {hp: 0}}` eller `{condition: paralyzed}` på samme opslag, `{trigger: death}` (kører den regel med `who` = opslaget) eller en liste af disse.

**Inventar** (`didact inv …`) virker på arkets `slots`-felt:
- **Plads:** genstande fylder deres `size` × `count`, og counters, der `occupies` feltet, fylder deres værdi. Ud over `capacity` afvises, medmindre `--force`.
- **Grupper:** `groups: {backpack: 6, body: 4}` giver hver gruppe sin egen plads og sine egne kolonner og summer: `@inventory.body.armor` er kun det, der bæres på kroppen eller holdes i hånden, `@inventory.body.free` den plads, gruppen har tilbage.
- **Anvendelser:** `uses: 3` tæller ned med `inv use`. `uses: d8` er en forbrugsterning: 1–2 sænker den ét trin. En opbrugt genstand forsvinder, medmindre den har `recharge` eller `keep: true`. Af flere genstande med samme navn betyder navnet den første; for at bruge en anvendelse (`inv use`, en regels `use:`, `set …uses-=1`) den første, der har en tilbage.
- **En genstands egne nøgler:** `didact set freya inventory.sword.damage=d10` (også en regels `set: who.inventory.$item.damage`) ændrer én af dem, med genstanden angivet, som `inv` angiver den, med en del af navnet eller hele navnet, mellemrum og punktummer med (`'inventory.12.7mm pistol.damage=d10'`, i anførselstegn for skallen); `uses` og `charges` tæller som et `uses`-felt (`charges+=2` stopper ved maksimum), og pladsen tjekkes, som `inv add` tjekker den. En regel læser en som `@{who.inventory.$item.damage}` (en forbrugsterning som dens terning, anvendelser som deres antal); en genstand eller nøgle, der ikke er der, læses som fraværende, så `default(…)` giver sin reserveværdi.
- **Kompendium:** indgange af typen `item` (eller weapon, armor, relic, …, eller en af pakkens egne typer, der udvider en af dem med `extends`) låner `inv add` deres detaljer, fundet via id, navn eller et alias (deler to et: angiv den ønskede som `pack.id`); ethvert andet navn, `:` og det hele, er genstandens eget navn.

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
- **Vægtede lister:** `entries` som en liste, med `weight:` på hver indgang.
- **Kolonner:** `columns: [a, b]` slår for hver kolonne i en række for sig. En enkel indgang (ikke en liste) udfylder alle kolonner, så `columns: [first, second]` over en ordliste betyder »slå to gange på denne liste«. `labels: false` udelader kolonnenavnene i resultatet (»Abandon · Advantage«). `read: "It's a {first} {second} with {third} {fourth} inside."` læser kolonnerne som en sætning.
- **Opslagstabeller:** `lookup: hp_lost`, eller `[odds, chaos]` for et 2D-skema.
- **Dubletter:** `duplicates: reroll | keep | make_it_worse` for »slå to gange«.
- **Slag i to trin:** en indgang, der slår på en anden tabel (`{table: lightning}` i stedet, eller `then:` efter den), bringer data fra det slag med sig: en regel eller en kladde, hvis slag rammer den, læser begge dele, indgangens egne nøgler først, derefter nøglerne fra den første tabel, der slås på bagefter. En `--prefill` kan nævne en indgang længere nede, i enhver dybde (`Ring of the Hunt`), med data fra hver indgang på vejen: af to med samme navn gælder den nærmeste (derefter den første), en, der går videre, slår videre derfra, og en, der ligner en af dem uden at være det, afvises, og den nærmeste nævnes. En guidet kladde tilbyder første trin, når dens indgange siger, hvad de er (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): at vælge en slår på næste tabel, som når et slag lander på den.
- **Læs begge veje:** `both_ways: true` på en d66-tabel tilføjer den anden læsning: 31 giver også 13, og læseren vælger.
- **Hvad en indgang betyder:** `about: "Knows: {skills}. Also known as: {aka}."` udfylder hver indgangs data (en liste læses `a, b`; `{text}` er selve indgangen) for at sige, hvad den giver, når et valg tilbyder den; en indgangs egen `note:` siger det i stedet. Uden nogen af dem beskrives en indgang, hvis data har et `id`, der navngiver en post i kompendiet, af den post.
- **Kortspil og poser:** `deck: tarot` med `cards` (eller `standard: true`); `bag: initiative` med `tokens`.

Valideringen tjekker, at hvert resultat, terningerne kan give, lander på en indgang.

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

Handlinger og procedurer er lister af trin, og udløsere er trin med en `when:`-betingelse. Trinene er:

| Trin | Gør |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | et logget slag; binder `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; et `{…}` udfyldes først, som i al tekst, så terninger, som en værdi holder som tekst, bliver slået (`{@{who.inventory.$item.damage}}`), og loggen viser dem: en værdi, der ikke er terninger, afvises, ligesom `roll: "@die"` med sådan tekst, som ikke slår noget; et sæt slag (`{d8, d6}kh1`) forbliver et |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | beregner værdier; ligesom ved `set`'s `value` er tekst med `{…}` en skabelon, og et enkelt ord er tekst; i al tekst, der udfyldes, skriver `{{` og `}}` selve klammen |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (eller `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | ændrer et opslag: valideret, begrænset, kan fortrydes; `set: who.$attr` sætter det felt, som en parameter angiver, og `set: who.inventory.$item.damage` en nøgle på en genstand, som opslaget bærer (se Inventar); `-=` tager en værdi ud af en liste, og en, den ikke indeholder, ændrer intet (en note siger det; en, den aldrig ville kunne indeholde, afvises); `unset:` fjerner et felt, som `set --unset` gør |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | giver et opslag en genstand eller tager en fra det, som `inv add` og `inv drop` gør: detaljerne kommer fra kompendiet, en entydig del af dens navn er nok, og pladsen og feltets hooks tjekkes |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | bruger en båret genstand, som `inv use` gør: anvendelser eller ladninger tæller ned, en forbrugsterning slås og sænkes ét trin på 1–2, og en, der løber tør, forsvinder, medmindre den genoplades eller beholdes; af flere med det navn den første, der har en anvendelse tilbage; binder `@torch.out` (dens sidste anvendelse er brugt), `@torch.gone` (der er intet tilbage af den), `@torch.left`, `@torch.die` og `@torch.rolled` (`as:` er som standard `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | laver et opslag med det samme, beskrevet som i en kladdes `entity`-trin (nedenfor) og tjekket mod dets ark; `as:` (ellers dets `key`, ellers dets type) binder det som et opslag, der læses og sættes som en `ref`-parameter (`pool: "@bleeding"`, `@bleeding.name`), og er aldrig navnet på en parameter; uden `key:` tages intet felt for en nøgle (`kind: track` bliver stående, som det er skrevet); findes der allerede et af den type og med det navn her, tages det, som det er, så en regel, der køres igen, ikke laver noget nyt |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | kører en prøve og binder dens udfald |
| `do: other-action`, `with: {…}`, `as: trip` | kører en anden regel; `@trip` er dens udfald og `@trip.<name>` det, den bandt (`@trip.found` for dens `let: {found: 2}`, `@trip.luck` for dens `roll: d6`, `as: luck`); `as:` er som standard dens id |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | et logget tabelslag; binder teksten og indgangens `data` (`@scar.<key>`, og en mappings nøgler via deres sti: `@scar.cost.hp`) samt data fra hver tabel, der slås på bagefter; en liste af genstande (`[Rope, {name: Laser, damage: d8}]`) læses som deres navne (`count(@scar.gear)`, `'Laser' in @scar.gear`), og givet, som den er, til et trin (`apply: "@scar.gear"`) er den selve genstandene; en liste af andre mappings kan kun et trin læse |
| `table: "setting-{@drop.difficulty}-terrain"` | en beregnet tabel: `{…}` og `$param` udfyldes |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | flere resultater som en liste (`distinct` slår gentagelser om) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | forgreninger |
| `repeat: "@count"`, `as: i`, `steps: […]` | en løkke: kører trinene det angivne antal gange, og `@i` tæller fra 1 |
| `for: pcs` (eller `party`), `as: member`, `steps: […]` | kører trinene én gang for hver spillerperson (eller hvert gruppemedlem), som `@member`: et opslag ligesom det, `entity:` binder (`@member.name`, `set: member.fatigue`); `as:` kan aldrig hedde det samme som en parameter, så reglens eget `who` forbliver urørt |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | output til LLM'en |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (eller `every: 1 day`) | en påmindelse, der forfalder, efterhånden som spiltiden går, ligesom dem, `didact remind` sætter |
| `reroll: roll`, `keep_if: "@face == 6"` | slår nogle af et slags terninger om (push-mekanikker) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | slår på en listeværdi (et orakels lister): binder indgangen, `@who.choose` (en tom linje) og `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | slår en tællers svindende pulje, som `track roll` gør (terninger, der viser 1-3, fjernes; `drop`-terninger fjernes først, `extra`-terninger slås med) eller fjerner kun terninger (`mode: drop`: et push, et kryds); forbundne faser og puljens hændelse følger med; binder `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

En prøves udfald kan læses af den regel, der kørte den (`check: … as: answer` giver `@answer`), og det samme kan dens markeringer: `'random-event' in @answer.flags`. Værdier i `with:` evalueres, når de indeholder `@`, udfyldes, når de indeholder `$param` eller `{…}` (»Does $npc flee?«), og sendes videre, som de er skrevet, ellers. En regel med en `oracle`-parameter får kampagneoraklets tilstandsopslag uden at blive bedt om det. En `ref`-parameter med `to: monster` tager et opslag af den type: et navn, som et andet opslag deler (en fjendes pulje, navngivet efter dens kort), er det af den type.

Udløsere kører af sig selv, når deres hændelse sker, og kun hvis deres `when:` er opfyldt:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Enhver regel (også generatorer og personskabelse) kan læse `@system` (id'et på det system, verdenen spilles med, så en spilverden skrevet til to systemer kan skelne dem fra hinanden), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` og `@time.is_night` og med en kalender med måneder også `@time.month`, `@time.month_name`, `@time.day_of_month` og `@time.year`; mens en kamp er i gang, også `@combat.round` og `@combat.fighters` (id'erne på dem, der er med i den). En tidsudløser kan også læse `@time.passed`, de sekunder, der lige er gået, en `combat_start`- eller `combat_end`-udløser læser den kamp, der begynder eller slutter (`combat start` og `combat end` kører dem; kampen slutter ikke, fordi en kæmper forlader den), og en regel, som en udløser kører, læser det samme som udløseren. En udløser med påkrævede parametre køres kun af `didact do` eller et felt-hook (`who` = opslaget). Udløsere med `on: manual` kører kun, når de kaldes. `for: pcs` (eller `party`) kører en udløser én gang for hver spillerperson (eller hvert gruppemedlem), som `who`: erfaring efter hver spilgang, for eksempel. En udløser, der fejler, stopper den kommando, der affyrede den, og siger, hvilken udløser det var, og hvordan man fortsætter uden den (`didact override add trigger <id> --data '{"on": "manual"}'`).

Kalenderen ligger i en pakkes `settings`: en spilverdenspakkes kalender vinder over systemets, og en verdens egen (`calendar:` i dens `world.yaml`) over begge:

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

`leap: 4` gør en måned en dag længere hvert 4. år, og `leap: [4, 100, 400]` hvert 4., men ikke hvert 100., men så alligevel hvert 400.: hvert tal tilsidesætter det foregående. `weekday` angiver, hvilken ugedag starten er (ellers ugens første), og `year` er, hvordan en dato skriver sit år, både i de datoer, Didact viser, og i dem, den læser (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` tjekker alle tre. En kampagne kan begynde på en anden dato i kalenderen, før dens start eller efter den: `didact campaign new <id> --date '4 July 1902'`, eller `didact time set '<date>'` indtil kampagnens første spilgang. En ugedag skrevet foran datoen bliver tjekket: datoen afgør det, og en note siger til, når den falder på en anden.

Tilvalg er systemets varianter og valgfrie regler, som hver kampagne vælger ved session nul:

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

`didact campaign profile lethality=deadly supplies=on` gemmer dem (eller webappens side Indstillinger). Regler, personskabelse og generatorer læser dem (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): et svar går forud for det, et andet tilvalg medfører, som igen går forud for standarden. Det, et tilvalg medfører, følges hele vejen (en stemning, der sætter dødeligheden, sætter også det, den dødelighed medfører), og hvis to tilvalg medfører hver sin værdi, vinder det nærmeste. Briefingen viser dem, der afviger fra deres standard, med hvad de betyder, så spillederen kan anvende det, reglerne ikke kan. En generator, der ikke kan køre under dem, stopper med `stop:` og årsagen, og der laves ingen kladde.

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

- **Spørg:** `didact ask '…' --odds likely` kører `ask`-prøven. Svaret er dens udfald (et bånd), og dens markeringer følger med.
- **Tilstand:** den ligger i et opslag, som prøven modtager som `oracle`. En prøve ændrer den med `set: oracle.chaos += 1`.
- **Lister:** `lists: {names: […], method: sections, most: 3}` gemmer vægtede lister på det opslag. `didact lists add|drop|roll|show` håndterer dem, og regler slår på dem med `pick`. `sections` slår først for et afsnit på fem linjer og så for en linje i det (en tom linje betyder vælg); `uniform` giver alle linjer samme chance.
- **Mere til prøven:** `didact ask '…' --with as_rule=true` sender ekstra parametre til oraklets prøve.
- **Loggen:** hvert svar nummereres (`#o12`) og logges, og `didact interpret o12 '…'` gemmer, hvad det betød. Kernepakkens `yes-no`-orakel er reserven.

## Generatorer og personskabelse: `generators/`, `chargen/`

Begge er procedurer, der bygger en **kladde**. De bruger alle regeltrin (`roll`, `table`, `if`, `let`, `prompt`, …) plus disse:

| Trin | Gør |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | tilføjer et opslag til kladden (nøgler `poi-1`, `poi-2`, …); et felt eller et link, der nævner en nøgle, som pakken skrev (`key:`, eller et `as:`-navn), bliver til det opslags id ved godkendelse, så vælg nøgler, som intet felt har som tekst (en entitet uden nogen af delene har ingen at udskifte); `from: "@relic.id"` starter det ud fra en post i kompendiet (med dens type, navn og felter) |
| `choose: {from: [a, b], as: x}` (eller `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | et valg; i guidet tilstand venter kladden på `choose`; `exclude` udelukker tidligere valg (et slået valg slås igen); `records:` tilføjer opslagene af den type her, efter id (lavet under spillet); `answer:` træffer valget uden at spørge, når dens værdi er en af mulighederne (en persons egen vej) |
| `choose_or_roll: {table: backgrounds, as: background}` | et valg, terningerne kan træffe; en valgt indgangs data er `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | slår ind i personen |
| `swap: {among: [STR, DEX, WIL], optional: true}` | byt to værdier, eller behold |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | fordel en fast række |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | køb værdier inden for et budget (`default: random` bruger det tilfældigt i tilfældig tilstand) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | en liste går til inventaret; en mapping sætter felter (lister lægges sammen) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | tilføjer til et felt på personen (eller på en enhed i kladden): tal lægges sammen, alt andet føjes til en liste; intet at tilføje er i orden |
| `remove: {field: talents, value: "@old"}` | fjerner noget fra et listefelt (et udskiftet talent, et afsluttet bånd); intet at fjerne er i orden |
| `roll_tables: [physique, vice]` | slår på tabeller ind i `traits`; en indgangs `data.gear` går til inventaret, og `data.add: {gold: 20}` lægger til felter |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | navnet; `name: {prompt: …}` uden noget at slå ud fra venter på et, selv i tilfældig tilstand |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | et spørgsmål, hvor ethvert svar duer (et mål, et andet opslags navn): kladden venter på det, selv i tilfældig tilstand, medmindre det er udfyldt på forhånd; `field:` gemmer svaret |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | en pointcrawl: et logget terningkast på kortet, veje (altid forbundne), afstande, skjulte veje (se nedenfor) |

Kort-trinnet tager mere, til bøgernes procedurer med terningkast på kortet:

| Nøgle | Gør |
|---|---|
| `regions: terrain` | disse enheder kastes også; hvert sted hører til den nærmeste (dets `region`) |
| `hidden: 6`, `conditional: 5` | en d6 pr. vej: på eller over tallet en skjult eller betinget vej (skjulte veje holdes ude af spillernes kort) |
| `describe: [path-feature, path-condition]` | tabeller, der slås for hver vej, gemt som dens `details` |
| `entrance: true`, `exit: true` | stedet nærmest kanten er indgangen; resten nummereres ud fra den langs vejene (`map.n`), vejene fører væk fra den, og udgangen er et fjernt sted nær en kant, nummereret sidst |
| `number: "{@dungeon_name}, room {@n}"` | omdøber de nummererede steder (deres nøgler i kladden følger med: `room-1` er rum 1) |

En tabel til terningkast på kortet kan nævne de næste tabeller i sine indgangers data, så proceduren læses som i bogen: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, derefter `table: "{@drop.what}"`. Listefelter, der ikke er sat (conditions, lists, tags), læses som tomme lister, så `'deprived' in @who.conditions` virker fra starten.

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

En personskabelse med `advances:` ændrer et opslag i stedet for at lave et: systemets niveaustigning.

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

- **Ét opslag:** en generator med `creates: npc` bygger det opslag, sådan som personskabelse bygger en person (`apply`, `add`, `name`, `field:`); dens `entity`-trin tilføjer opslag ved siden af, og et link `to: character` peger på det.
- **Kørsel:** `gen run` og `char new` laver en kladde (`#g7`, `#c3`) og gemmer intet. Et `stop:` afslutter den, uden at der laves en kladde: under et `if:`, der læser en kampagneindstilling, peger dens tip på indstillingerne (`didact session zero`); ellers siger dens egne ord, hvad man gør i stedet.
- **Beslutninger:** `--prefill '{…}'` beslutter ting på forhånd ud fra det navn, et trin binder (`as:`): en enkelt værdi besvarer alle forekomster, en liste én forekomst hver (en liste til `choose` med `count` er hele valget). `let`-værdier kan også udfyldes på forhånd (`{"hp": 6}`), og et navn, et `ask` eller et `let` beholder enhver tekst som angivet. En værdi til et valg mellem kendte muligheder (et `choose`, en tabels indgang) er den mulighed, den nævner, som skrevet (uanset store og små bogstaver), ved indgangens `id` eller ved et slag, der lander på den (`{"group": 3}`), og bringer indgangens data med; en værdi, der ligger tæt på en mulighed uden at være nogen af dem, afvises med den nærmeste som forslag, og enhver anden er et frit svar uden data. `--auto` (eller `char new --mode random`) lader terningerne bestemme resten. Ellers venter kladden ved hvert valg.
- **Beskrivelse:** et valg siger, hvad hver mulighed betyder, til den spiller, der vælger: en tabelindgangs `note:` eller dens tabels `about:`, ellers den post i kompendiet, den navngiver (`id` i dens data), eller den, muligheden selv er (et valg mellem id'er i kompendiet viser hver posts navn): dens felter `tagline` og `summary`, `description` eller `effect`, ellers dens teksts første afsnit.
- **Trin tilbage:** `char back` (eller `gen back`) tager det seneste svar, slag eller den seneste redigering tilbage, så kladden stiller det spørgsmål igen; de slag, trinnet lavede, markeres som fortrudte.
- **Genoptagelse:** en genoptaget kladde afspiller sit spor igen: hver værdi, der er slået eller valgt, bruges én gang og i rækkefølge (også kortets terningkast), så intet slås to gange, og intet, der allerede er besluttet, ændres.
- **Gemning:** `commit` gemmer opslagene, tjekket mod deres ark.
- **Udvikling:** en `advances:`-kladde starter fra en kopi af opslaget (med standardværdierne fra dets ark), dens trin læser opslaget som `@who` og kladdens værdier som `@character.*`, og `commit` gemmer kun det, der er ændret, tjekket som ved `set`; opslag fra dens `entity`-trin (et nyt bånds tråd) oprettes ved siden af: et link `to: character` peger på opslaget, og et felt, der nævner en nøgle, rummer id'et på det opslag, nøglen bliver til, ligesom når en person skabes (`apply: {blood: "@pool"}`). Et `stop:` siger, hvorfor ikke endnu (ikke nok XP), og der laves ingen kladde. Et system, hvis udvikling er en enkelt regel, angiver den i stedet i sin personskabelse: `advance: {rule: grow}`.
- **Tilstande:** `modes: [guided]` gør, at en procedure kun kører trin for trin: `--mode random` afvises.

## Kompendium, håndbog og ordliste

- **Indgange i kompendiet** skrives som `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. En værdi som `"roll 2d8"` slås, når indgangen skabes. Kør `didact spawn troll`, eller hent en pakkes indgange ind i verdenen med `didact compendium import <pack>` (`--type loc`, og `--tag coast` for dem, der har hvert angivet tag).
- **Til flere systemer:** en nøgle på øverste niveau havner der, hvor `set` lægger den: i systemets blok, når dets ark har det felt, ellers i `fields`. En indgang, som en spilverden skriver til mere end ét system, giver hvert systems tal i sin egen blok (`mechanics: {my-system: {hp: 12}}`): `pack validate` tjekker hver blok mod det systems ark, når det er installeret, og noterer en nøgle på øverste niveau, som både det ark og cores ark har. Det, en blok siger, gælder: ved siden af `mechanics: {my-system: {role: tactician}}` er en `role: innkeeper` på øverste niveau cores felt, ligesom alt under `fields:`. En blok, der nævner den pakke, der valideres, tjekkes mod den pakke, som den ligger i sin mappe.
- **Håndbogsafsnit** ligger i `reference/*.md`, med front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` finder dem; en sætning i anførselstegn, der ikke står der, prøves ord for ord.
- **Ordlisten** er `glossary.yaml`: `term: definition`, eller en liste af `{term, definition, aliases, see}`. `didact define <term>` læser den.

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

## Del og fjern pakker

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- En pakke, der erklærer `redistributable: false`, kan ikke eksporteres.
- **core** er en del af Didact og altid slået til: alle systemer bygger på den, så den kan ikke deaktiveres eller afinstalleres.
- De andre pakker, der følger med Didact, er `.didactpack`-filer i dens `packs/`-mappe. `pack list` viser dem, indtil de er installeret, og installerer du en, kommer de pakker, den kræver og som følger med, også med.
- `pack update` leder efter nyere versioner i Didacts `packs/`-mappe og på GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` angiver et andet sted, eller intet for ikke at lede). En ny version installeres ved siden af den gamle: kampagner beholder deres indtil `didact campaign upgrade`.
- Der er kun ét spilsystem i brug ad gangen: den åbne verdens. En verden beholder det system, den blev oprettet med (`didact world new <id> --system <pack>`; en verden, der er oprettet uden system, tager det første, den får, med `pack enable` eller `world set system=`), dens kampagner spilles med det, og en pakke, der kræver et andet system (en spilverden skrevet til det), kan ikke tilføjes: et andet system spilles i sin egen verden.
- `uninstall` nægter, så længe en verden eller kampagne bruger pakkens eneste kopi (`--force` fjerner den alligevel). Det kan ikke fortrydes: installér .didactpack-filen igen.

## Fra regelbog til pakke: tjeklisten

Gå bogens mekanikker igennem i denne rækkefølge. Hver af dem svarer til noget ovenfor:

1. **Afgørelse af slag:** hvordan et slag lykkes (en prøve: `success`, `bands`, `auto`).
2. **Terninger:** usædvanlige terninger, symboler, trin (`dice.yaml`, navngivne terninger, kæder).
3. **Arket:** egenskaber, afledte tal (`schemas/`, afledte felter).
4. **Ressourcer:** HP, held, momentum (resource- og counter-felter; `set`-trin).
5. **Tilstande:** tilstande og hvad de gør (`conditions`-felter; `if`-trin).
6. **Kamp:** angreb, skade, initiativ (handlinger; `bag`/`deck` til turrækkefølgen).
7. **Procedurer:** udforskning, rejser, nedetid (procedurer med spørgsmål).
8. **Tabeller:** alle tilfældige tabeller (`tables/`; `pack import` til Markdown-tabeller).
9. **Bestiariet:** monstre og bipersoner (`compendium/`).
10. **Genstande:** udstyr, besværgelser, relikvier (`compendium/`, slots-felter).
11. **Vejledning til SL:** principper og råd (`GUIDE.md`, `reference/`, `guidance:` på typer).
12. **Personskabelse:** hvordan man laver en person (en `chargen/`-procedure, eller `roll:` på hvert felt).

Angiv sidetal med `source:` overalt, så huller bliver synlige. Tilføj en prøvespilstest, der laver en person, slår en prøve, kæmper og kører en procedure.
