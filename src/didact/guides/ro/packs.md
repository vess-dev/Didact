<!-- translated from b1dfa1159ff4 -->
# Pachete

Un pachet este un sistem de joc, un oracol, un cadru de joc, o aventură sau un supliment, scris ca fișiere YAML plus un plugin Python opțional. Acest ghid arată cum scrii unul: transformând o carte de reguli într-un pachet sau adăugând conținut propriu.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Un pachet se poate face și din ce ai în bibliotecă. `didact pack new my-brew --from-overlay my-system` transformă conținutul tău propriu pentru un sistem (`compendium add`, fișe păstrate cu `--scope system`, cunoștințe) într-un supliment, iar `didact world export --as setting` transformă o lume într-un pachet de cadru de joc: persoanele, locurile și cunoștințele ei ca intrări de compendiu și cunoștințe ale pachetului, aduse în altă lume cu `compendium import`. Amândouă lasă pe dinafară secretele și notele MJ, dacă nu dai `--secrets`, și niciunul nu e marcat ca partajabil până nu îi setezi licența.

## Structura

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

Un fișier conține un element, o listă de elemente sau mai multe elemente separate prin `---`. Fiecare element își numește ID-ul cu cheia felului său: `table: weather`, `check: save`, `type: pc` sau `id: troll` pentru intrările din compendiu. Te referi la elemente ca `pack.id` (`my-system.save`) sau prin ID-ul simplu, când îl are un singur pachet activat.

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

Un hack își numește baza în `extends` și conține doar ce diferă:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Elementul său cu același ID îl înlocuiește pe cel al bazei, oricare ar fi felul (un tabel, o regulă, o intrare din compendiu, o secțiune de referință, un termen de glosar). Valorile sale din `settings` se aplică peste cele ale bazei, cheie cu cheie: o cheie pe care o setează hackul înlocuiește în întregime valoarea bazei (tabelele sale `names` iau locul celor ale bazei), iar regulile bazei citesc și ele valorile hackului. `hides` elimină ce rămâne și nu îi folosește hackului: `*` se potrivește cu orice șir de caractere, decide ultimul șablon care se potrivește cu un ID, iar unul care începe cu `!` păstrează elementul. Ce înlocuiește hackul nu este ascuns niciodată. Felurile sunt `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` și `term`. `didact pack validate` avertizează despre un șablon care nu se potrivește cu nimic.

## Expresii

Fiecare condiție și formulă folosește limbajul zarurilor (`didact guide dice`), plus:
- **Valori:** `@name` citește o valoare: `@roll`, `@who.STR`, `@settings.x`. `$name` inserează mai întâi textul unui parametru, așa că `@who.$attr` devine `@who.STR`. Citește un parametru de text liber ca `@name`, nu între ghilimele (`'$name'`): un apostrof din textul lui le-ar închide (`pack validate` avertizează).
- **Logică:** `and`, `or`, `not` și `in` (`'deprived' in @who.conditions`).
- **Literali:** text (`'travel'`) și `true`/`false`.
- **Funcții:** `if(cond, a, b)` aruncă doar ramura pe care o ia. `default(@thread.flashpoint, 0)` este valoarea sau rezerva, când nu e setată. `sum`, `count` (`count(@roll.dice, 6)` numără șesarii), `min`, `max`, `any` și `all` primesc liste.

## Foi: `schemas/`

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

| Fel | Conține | Opțiuni |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | o valoare simplă | min, max; `values` pentru enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` este valoarea, `@hp.max` plafonul | range; min; max sau max_field; die |
| `counter` | un număr | min, max, thresholds, occupies (un câmp slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | obiecte (`Rope` sau `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | ce spune numele | `to` (pentru refs), `allowed` |
| `derived` | calculat, niciodată stocat | expr |

Orice câmp primește și `label`, `help`, `default`, `required` și `roll`: `new pc Hero --fill` sau o valoare `"roll"` aruncă zarurile pentru el prin jurnal. Tipurile din pachetul `core` țin text independent de sistem în `fields`. Tipurile unui sistem își țin numerele în `mechanics.<system>`. `set hero hp-=2` găsește câmpul, limitează valoarea și raportează orice depășire. `+=` adaugă la o listă: o `list` (precum `slots`) păstrează și o valoare adăugată din nou, `tags`, `conditions` și `refs` o țin o singură dată, iar `-=` scoate toate copiile.

**Hook-urile** spun ce se întâmplă când o valoare trece de un prag. Se declanșează la fiecare modificare (`set`, `inv`, un pas `set` al unei reguli), dar doar când pragul e trecut: 3 → 0 declanșează, 0 → 0 nu. Editările cu `--force` le sar.

| Hook | Se declanșează când |
|---|---|
| `on_zero` | un număr sau `{value}` ajunge la 0 |
| `on_full` (`when_full` pe slots) | ajunge la max, size sau capacity |
| `thresholds: {10: …, 20: …}` (contoare) | trece de fiecare prag |

O acțiune este text (o notă pentru LLM), `{set: {hp: 0}}` sau `{condition: paralyzed}` pe aceeași fișă, `{trigger: death}` (rulează acea regulă cu `who` = fișa) sau o listă din acestea.

**Inventarul** (`didact inv …`) lucrează pe câmpul `slots` al foii:
- **Spațiu:** obiectele ocupă `size` × `count`, iar contoarele care au `occupies` pe câmp ocupă valoarea lor. Depășirea lui `capacity` e refuzată, fără `--force`.
- **Grupuri:** `groups: {backpack: 6, body: 4}` dă fiecărui grup propriul spațiu, precum și propriile coloane și totaluri: `@inventory.body.armor` e doar ce se poartă pe corp sau se ține în mână, `@inventory.body.free` spațiul care îi mai rămâne.
- **Utilizări:** `uses: 3` scade cu `inv use`. `uses: d8` e un zar de uzură: la 1–2 coboară o treaptă. Un obiect consumat dispare, dacă nu are `recharge` sau `keep: true`. Din mai multe obiecte cu același nume, numele îl desemnează pe primul; ca să cheltui o utilizare (`inv use`, `use:` al unei reguli, `set …uses-=1`), pe primul căruia îi mai rămâne una.
- **Cheile proprii ale unui obiect:** `didact set freya inventory.sword.damage=d10` (la fel și `set: who.inventory.$item.damage` al unei reguli) modifică una dintre ele, cu obiectul numit cum îl numește `inv`, după o parte din nume sau după numele întreg, cu spații și puncte cu tot (`'inventory.12.7mm pistol.damage=d10'`, între ghilimele pentru shell); `uses` și `charges` se numără ca într-un câmp `uses` (`charges+=2` se oprește la maxim), iar spațiul e verificat cum îl verifică `inv add`. O regulă citește una ca `@{who.inventory.$item.damage}` (un zar de uzură ca zarul lui, utilizările ca numărul lor); un obiect sau o cheie care nu e acolo se citește ca absent, așa că `default(…)` dă valoarea de rezervă.
- **Compendiu:** intrările de tip `item` (sau weapon, armor, relic, …, sau un tip propriu al pachetului care extinde unul dintre ele cu `extends`) își împrumută detaliile lui `inv add`, găsite după ID, după nume sau după un alias (dacă două au unul în comun: numește-o ca `pack.id`); orice alt nume, cu `:` cu tot, e numele propriu al obiectului.

## Tabele: `tables/`

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

Alte forme:
- **Liste ponderate:** `entries` ca listă, cu `weight:` pentru fiecare intrare.
- **Coloane:** `columns: [a, b]` aruncă separat pentru fiecare coloană a unui rând. O intrare simplă (nu o listă) umple toate coloanele, așa că `columns: [first, second]` peste o listă de cuvinte înseamnă „aruncă de două ori pe această listă”. `labels: false` omite numele coloanelor din rezultat („Abandon · Advantage”). `read: "It's a {first} {second} with {third} {fourth} inside."` citește coloanele ca pe o propoziție.
- **Căutări:** `lookup: hp_lost` sau `[odds, chaos]` pentru un tabel bidimensional.
- **Dubluri:** `duplicates: reroll | keep | make_it_worse` pentru „aruncă de două ori”.
- **În două etape:** o intrare care aruncă pe alt tabel (`{table: lightning}` în locul textului sau `then:` după el) aduce cu ea datele acelei aruncări: o regulă sau o ciornă în care iese citește ambele seturi de date, întâi cheile proprii ale intrării, apoi pe cele ale primului tabel aruncat în continuare. Un `--prefill` poate numi o intrare mai jos, la orice adâncime (`Ring of the Hunt`), cu datele fiecărei intrări de pe drum: din două cu același nume contează cea mai apropiată (apoi prima), una care trece mai departe aruncă de acolo înainte, iar una apropiată de vreuna dintre ele fără să fie vreuna e refuzată, cu cea mai apropiată numită. O ciornă ghidată oferă primul pas când intrările lui spun ce sunt (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): alegerea uneia aruncă pe tabelul următor, ca o aruncare care cade pe ea.
- **Citire în ambele sensuri:** `both_ways: true` pe un tabel d66 adaugă cealaltă citire: 31 dă și 13, iar cititorul alege.
- **Ce înseamnă o intrare:** `about: "Knows: {skills}. Also known as: {aka}."` se completează cu datele fiecărei intrări (o listă se citește `a, b`; `{text}` e intrarea însăși) ca să spună ce oferă intrarea când o propune o alegere; propriul `note:` al unei intrări spune asta în locul lui. Fără niciunul dintre ele, o intrare ale cărei date au un `id` care numește o intrare de compendiu e descrisă de acea intrare.
- **Pachete de cărți și săculeți:** `deck: tarot` cu `cards` (sau `standard: true`); `bag: initiative` cu `tokens`.

Validarea verifică dacă fiecare rezultat pe care îl pot da zarurile cade pe o intrare.

## Reguli: `rules/`

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

Acțiunile și procedurile sunt liste de pași, iar declanșatorii sunt pași cu o condiție `when:`. Pașii sunt:

| Pas | Ce face |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | o aruncare notată; leagă `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; un `{…}` e completat întâi, ca în orice text, așa că zarurile pe care o valoare le ține ca text sunt aruncate (`{@{who.inventory.$item.damage}}`), iar jurnalul le arată: o valoare care nu sunt zaruri e refuzată, la fel ca `roll: "@die"` cu un asemenea text, care nu aruncă nimic; un set de aruncări (`{d8, d6}kh1`) rămâne set |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | calculează valori; ca la `value` din `set`, textul `{…}` e un șablon, iar un cuvânt simplu e text; în orice text completat, `{{` și `}}` scriu acolada însăși |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (sau `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | modifică o fișă: validat, limitat, se poate desface; `set: who.$attr` setează câmpul numit de un parametru, iar `set: who.inventory.$item.damage`, o cheie a unui obiect pe care îl duce fișa (vezi Inventarul); `-=` scoate o valoare dintr-o listă, iar una pe care nu o conține nu schimbă nimic (o notă o spune; una pe care n-ar putea-o conține niciodată e refuzată); `unset:` scoate un câmp, ca `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | dă unei fișe un obiect sau îi ia unul, așa cum fac `inv add` și `inv drop`: detaliile vin din compendiu, ajunge o parte unică din numele lui, iar spațiul și hook-urile câmpului sunt verificate |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | folosește un obiect purtat cum face `inv use`: utilizările sau încărcările scad, un zar de uzură e aruncat și coboară o treaptă la 1–2, iar unul consumat dispare, dacă nu se reîncarcă sau nu e păstrat; din mai multe cu acel nume, primul căruia îi mai rămâne o utilizare; leagă `@torch.out` (ultima lui utilizare s-a dus), `@torch.gone` (nu mai rămâne nimic din el), `@torch.left`, `@torch.die` și `@torch.rolled` (`as:` e implicit `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | creează pe loc o fișă, descrisă ca la pasul `entity` al unei ciorne (vezi mai jos) și verificată după foaia ei; `as:` (altfel `key` al ei, altfel tipul ei) o leagă ca fișă, citită și setată ca un parametru `ref` (`pool: "@bleeding"`, `@bleeding.name`), și nu e niciodată numele unui parametru; fără `key:`, niciun câmp nu e luat drept cheie (`kind: track` rămâne cum e scris); dacă aici există deja una de acel tip și cu acel nume, e luată așa cum e, așa că o regulă rulată din nou nu creează nimic nou |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | rulează un test și îi leagă rezultatul |
| `do: other-action`, `with: {…}`, `as: trip` | rulează altă regulă; `@trip` e rezultatul ei și `@trip.<name>` ce a legat (`@trip.found` pentru `let: {found: 2}` al ei, `@trip.luck` pentru `roll: d6`, `as: luck` al ei); `as:` e implicit ID-ul ei |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | o aruncare pe tabel notată; leagă textul și `data` intrării (`@scar.<key>`, iar cheile unei mapări după calea lor: `@scar.cost.hp`), împreună cu cele ale oricărui tabel aruncat în continuare; o listă de obiecte (`[Rope, {name: Laser, damage: d8}]`) se citește ca numele lor (`count(@scar.gear)`, `'Laser' in @scar.gear`), iar dată unui pas așa cum e (`apply: "@scar.gear"`) e obiectele înseși; o listă de alte mapări o citește doar un pas |
| `table: "setting-{@drop.difficulty}-terrain"` | un tabel calculat: `{…}` și `$param` se completează |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | mai multe rezultate ca listă (`distinct` rearuncă repetările) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | ramificare |
| `repeat: "@count"`, `as: i`, `steps: […]` | o buclă: pașii de atâtea ori, cu `@i` numărând de la 1 |
| `for: pcs` (sau `party`), `as: member`, `steps: […]` | pașii o dată pentru fiecare personaj jucător (sau membru al grupului), ca `@member`: o fișă, la fel ca aceea pe care o leagă `entity:` (`@member.name`, `set: member.fatigue`); `as:` nu ia niciodată numele unui parametru, așa că `who` al regulii rămâne al ei |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | ieșire pentru LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (sau `every: 1 day`) | un memento care devine scadent pe măsură ce trece timpul jocului, ca cele pe care le setează `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | rearuncă unele zaruri ale unei aruncări (mecanici de forțare) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | aruncă pe o valoare-listă (listele unui oracol): leagă intrarea, `@who.choose` (un rând gol) și `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | aruncă fondul descrescător al unui contor la fel ca `track roll` (zarurile cu 1-3 cad; zarurile din `drop` cad primele, cele din `extra` se aruncă odată cu celelalte) sau doar scoate zaruri (`mode: drop`: o forțare, o bifă); urmează fazele legate și evenimentul fondului; leagă `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Rezultatul unui test poate fi citit de regula care l-a rulat (`check: … as: answer` dă `@answer`), la fel și indicatorii lui: `'random-event' in @answer.flags`. Valorile din `with:` sunt evaluate când conțin `@`, completate când conțin `$param` sau `{…}` („Does $npc flee?”) și transmise așa cum sunt scrise în rest. O regulă cu un parametru `oracle` primește fișa de stare a oracolului campaniei fără să i se spună. Un parametru `ref` cu `to: monster` ia o fișă de acel tip: un nume pe care îl împarte cu altă fișă (rezerva unui dușman, numită ca fișa lui) e cea de acel tip.

Declanșatorii rulează singuri când are loc evenimentul lor, și doar dacă `when:` e adevărat:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Orice regulă (inclusiv un generator și crearea de personaje) poate citi `@system` (ID-ul sistemului pe care îl joacă lumea, ca un cadru de joc scris pentru două sisteme să le poată deosebi), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` și `@time.is_night`, iar cu un calendar cu luni, și `@time.month`, `@time.month_name`, `@time.day_of_month` și `@time.year`; în timpul unei lupte, `@combat.round` și `@combat.fighters` (ID-urile celor din ea). Un declanșator de timp poate citi și `@time.passed`, secundele tocmai avansate, un declanșator `combat_start` sau `combat_end` citește lupta care începe sau se încheie (`combat start` și `combat end` îi rulează; plecarea unui luptător nu încheie lupta), iar o regulă rulată de un declanșator citește ce citește și declanșatorul. Un declanșator cu parametri obligatorii e rulat doar de `didact do` sau de un hook de câmp (`who` = fișa). Declanșatorii `on: manual` rulează doar când sunt apelați. `for: pcs` (sau `party`) rulează un declanșator o dată pentru fiecare personaj jucător (sau membru al grupului), ca `who`: de exemplu, experiența după fiecare sesiune. Un declanșator care eșuează oprește comanda care l-a pornit și spune ce declanșator a fost și cum se continuă fără el (`didact override add trigger <id> --data '{"on": "manual"}'`).

Calendarul stă în `settings` ale unui pachet: cel al unui pachet de cadru de joc îl întrece pe cel al sistemului, iar calendarul propriu al unei lumi (`calendar:` în `world.yaml` al ei) le întrece pe amândouă:

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

`leap: 4` face o lună cu o zi mai lungă din 4 în 4 ani, iar `leap: [4, 100, 400]` din 4 în 4, dar nu din 100 în 100, ci totuși din 400 în 400: fiecare număr îl anulează pe cel dinainte. `weekday` numește ziua săptămânii a începutului (altfel e prima zi a săptămânii), iar `year` e felul în care o dată își scrie anul, atât în cele pe care le arată Didact, cât și în cele pe care le citește (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` le verifică pe toate trei. O campanie poate începe la altă dată a calendarului, înainte de începutul lui sau după: `didact campaign new <id> --date '4 July 1902'` sau `didact time set '<date>'` până la prima ei sesiune. O zi a săptămânii scrisă înaintea datei e verificată: data decide, iar o notă o spune când cade în altă zi.

Opțiunile sunt variantele și regulile opționale ale sistemului, pe care fiecare campanie le alege la sesiunea zero:

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

`didact campaign profile lethality=deadly supplies=on` le salvează (sau pagina Setări a aplicației web). Regulile, crearea personajelor și generatoarele le citesc (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): un răspuns are prioritate față de ce implică altă opțiune, iar aceasta față de valoarea implicită. Ce implică o opțiune e urmat până la capăt (un stil care setează letalitatea setează și ce implică acea letalitate), iar dintre două implicații are prioritate cea mai apropiată. Rezumatul le enumeră pe cele care diferă de valoarea lor implicită, cu ce înseamnă, pentru ca maestrul de joc să aplice ce nu pot regulile. Un generator care nu poate rula cu ele se oprește cu `stop:` și motivul, și nu se creează nicio ciornă.

## Oracole: `oracles/`

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

- **Întrebarea:** `didact ask '…' --odds likely` rulează testul `ask`. Răspunsul e rezultatul lui (o bandă), iar indicatorii îl însoțesc.
- **Starea:** stă într-o fișă pe care testul o primește ca `oracle`. Un test o schimbă cu `set: oracle.chaos += 1`.
- **Liste:** `lists: {names: […], method: sections, most: 3}` ține liste ponderate pe acea fișă. `didact lists add|drop|roll|show` le gestionează, iar regulile aruncă pe ele cu `pick`. `sections` aruncă pentru o secțiune de cinci rânduri, apoi pentru un rând din ea (un rând gol înseamnă alege); `uniform` dă fiecărui rând aceeași șansă.
- **Mai mult pentru test:** `didact ask '…' --with as_rule=true` transmite parametri suplimentari testului oracolului.
- **Jurnalul:** fiecare răspuns e numerotat (`#o12`) și notat, iar `didact interpret o12 '…'` păstrează ce a însemnat. Oracolul `yes-no` al pachetului core e rezerva.

## Generatoare și crearea de personaje: `generators/`, `chargen/`

Amândouă sunt proceduri care construiesc o **ciornă**. Folosesc toți pașii regulilor (`roll`, `table`, `if`, `let`, `prompt`, …), plus aceștia:

| Pas | Ce face |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | adaugă o fișă în ciornă (chei `poi-1`, `poi-2`, …); un câmp sau o legătură care numește o cheie scrisă de pachet (`key:` sau un nume `as:`) devine ID-ul acelei fișe la confirmare, așa că alege chei pe care niciun câmp nu le are ca text (o entitate fără niciuna dintre ele nu are cheie de înlocuit); `from: "@relic.id"` o pornește de la o intrare de compendiu (tipul, numele și câmpurile ei) |
| `choose: {from: [a, b], as: x}` (sau `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | o alegere; în modul ghidat ciorna așteaptă `choose`; `exclude` exclude alegerile anterioare (una aruncată se aruncă din nou); `records:` adaugă fișele de acel tip de aici, după id (create în joc); `answer:` face alegerea când valoarea lui e una dintre opțiuni (calea proprie a personajului), fără să mai întrebe |
| `choose_or_roll: {table: backgrounds, as: background}` | o alegere pe care o pot face zarurile; datele unei intrări alese sunt `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | aruncă în personaj |
| `swap: {among: [STR, DEX, WIL], optional: true}` | schimbă două scoruri între ele sau le păstrează |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | distribuie un set fix de valori |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | cumpără scoruri dintr-un buget (`default: random` îl cheltuie la întâmplare în modul aleatoriu) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | o listă merge în inventar; o mapare setează câmpuri (listele se adună) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | adaugă la un câmp al personajului (sau al unei entități din ciornă): numerele se adună, orice altceva se alătură unei liste; dacă nu e nimic de adăugat, e în regulă |
| `remove: {field: talents, value: "@old"}` | scoate ceva dintr-un câmp-listă (un talent înlocuit, o relație încheiată); dacă nu e nimic de scos, e în regulă |
| `roll_tables: [physique, vice]` | aruncă pe tabele în `traits`; `data.gear` al unei intrări merge în inventar, iar `data.add: {gold: 20}` adaugă la câmpuri |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | numele; `name: {prompt: …}` fără nimic din care să arunce așteaptă un nume, chiar și în modul aleatoriu |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | o întrebare la care merge orice răspuns (un obiectiv, numele altei fișe): ciorna o așteaptă, chiar și în modul aleatoriu, dacă nu e completată dinainte; `field:` păstrează răspunsul |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | un pointcrawl: o aruncare de zaruri pe hartă notată, drumuri (mereu conectate), distanțe, drumuri ascunse (vezi mai jos) |

Pasul map primește mai multe, pentru procedurile cărților cu zaruri aruncate pe hartă:

| Cheie | Ce face |
|---|---|
| `regions: terrain` | și aceste entități sunt aruncate; fiecare loc se alătură celei mai apropiate (`region` al lui) |
| `hidden: 6`, `conditional: 5` | un d6 pe drum: la număr sau peste, un drum ascuns sau condiționat (drumurile ascunse nu apar pe harta jucătorilor) |
| `describe: [path-feature, path-condition]` | tabele aruncate pentru fiecare drum, păstrate ca `details` ale lui |
| `entrance: true`, `exit: true` | locul cel mai apropiat de margine e intrarea; celelalte sunt numerotate pornind de la ea de-a lungul drumurilor (`map.n`), drumurile se îndepărtează de ea, iar ieșirea e un loc îndepărtat, lângă o margine, numerotat ultimul |
| `number: "{@dungeon_name}, room {@n}"` | redenumește locurile numerotate (cheile lor din ciornă urmează: `room-1` e camera 1) |

Un tabel pentru aruncarea pe hartă poate numi următoarele tabele în datele intrărilor sale, așa că procedura se citește ca în carte: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, apoi `table: "{@drop.what}"`. Câmpurile-listă nesetate (conditions, lists, tags) se citesc ca liste goale, așa că `'deprived' in @who.conditions` funcționează de la început.

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

O procedură chargen cu `advances:` schimbă o fișă în loc să creeze una: avansarea în nivel a sistemului.

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

- **O singură fișă:** un generator cu `creates: npc` construiește acea fișă așa cum crearea de personaje construiește un personaj (`apply`, `add`, `name`, `field:`); pașii săi `entity` adaugă fișe alături, iar o legătură `to: character` arată spre ea.
- **Rularea:** `gen run` și `char new` fac o ciornă (`#g7`, `#c3`) și nu scriu nimic. Un `stop:` o încheie fără să creeze nimic: sub un `if:` care citește o opțiune a campaniei, indiciul lui trimite la opțiuni (`didact session zero`); altfel, propriile lui cuvinte spun ce să faci în loc.
- **Decizia:** `--prefill '{…}'` decide lucruri dinainte, după numele pe care îl leagă un pas (`as:`): o singură valoare răspunde la toate aparițiile, o listă câte una pentru fiecare apariție (o listă pentru `choose` cu `count` e toată alegerea). Și valorile `let` pot fi precompletate (`{"hp": 6}`), iar un nume, un `ask` sau un `let` păstrează orice text exact cum a fost dat. O valoare pentru o alegere între opțiuni cunoscute (un `choose`, o intrare de tabel) este opțiunea pe care o numește, așa cum e scrisă sau cu alte litere mari și mici, prin `id` al intrării ei sau printr-o aruncare care cade pe ea (`{"group": 3}`), și aduce datele acelei intrări; una apropiată de o opțiune, dar care nu e niciuna dintre ele, e refuzată, cu numele celei mai apropiate, iar oricare alta e un răspuns propriu, fără date. `--auto` (sau `char new --mode random`) lasă zarurile să decidă restul. Altfel, ciorna așteaptă la fiecare alegere.
- **Descrierea:** o alegere spune ce înseamnă fiecare opțiune, pentru jucătorul care alege: `note:` al unei intrări de tabel sau `about:` al tabelului ei, altfel intrarea de compendiu pe care o numește (`id` din datele ei) sau cea care este opțiunea însăși (o alegere între ID-uri de compendiu arată numele fiecăreia): `tagline` și `summary` ale ei, `description` sau `effect`, altfel primul paragraf al textului ei.
- **Pasul înapoi:** `char back` (sau `gen back`) retrage ultimul răspuns, ultima aruncare sau ultima editare, așa că ciorna pune din nou acea întrebare; aruncările făcute în acel pas sunt marcate ca anulate.
- **Reluarea:** o ciornă reluată își rejoacă traseul: fiecare valoare aruncată sau aleasă, fiecare folosită o dată și în ordine (inclusiv aruncarea de pe hartă), așa că nimic nu e aruncat de două ori și nimic deja decis nu se schimbă.
- **Scrierea:** `commit` scrie fișele, verificate după foile lor.
- **Avansarea:** o ciornă `advances:` pornește de la o copie a fișei (cu valorile implicite ale foii ei), pașii ei citesc fișa ca `@who` și valorile ciornei ca `@character.*`, iar `commit` scrie doar ce s-a schimbat, verificat ca la `set`; fișele din pașii ei `entity` (firul narativ al unei relații noi) sunt create alături: o legătură `to: character` arată spre fișă, iar un câmp care numește o cheie conține ID-ul fișei corespunzătoare, ca la crearea unui personaj (`apply: {blood: "@pool"}`). Un `stop:` spune de ce nu se poate încă (nu e destul XP) și nu se creează nicio ciornă. Un sistem a cărui dezvoltare e o singură regulă o numește în schimb în chargen-ul lui: `advance: {rule: grow}`.
- **Moduri:** `modes: [guided]` menține o procedură pas cu pas: `--mode random` e refuzat.

## Compendiu, referințe și glosar

- **Intrările din compendiu** se scriu ca `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. O valoare `"roll 2d8"` aruncă zarurile când intrarea e creată. Rulează `didact spawn troll` sau adu intrările unui pachet în lume cu `didact compendium import <pack>` (`--type loc`, și `--tag coast` pentru cele care au toate etichetele date).
- **Pentru mai multe sisteme:** o cheie de pe nivelul de sus ajunge unde o pune `set`: în blocul sistemului când foaia lui are acel câmp, altfel în `fields`. O intrare pe care un cadru de joc o scrie pentru mai multe sisteme dă numerele fiecăruia în propriul lui bloc (`mechanics: {my-system: {hp: 12}}`): `pack validate` verifică fiecare bloc după foaia acelui sistem când e instalat și notează o cheie de pe nivelul de sus pe care o au și acea foaie, și foaia lui core. Ce spune un bloc rămâne valabil: lângă `mechanics: {my-system: {role: tactician}}`, un `role: innkeeper` de pe nivelul de sus e câmpul lui core, la fel ca tot ce e sub `fields:`. Un bloc care numește pachetul validat e verificat față de acel pachet așa cum e în dosarul lui.
- **Secțiunile de referință** merg în `reference/*.md`, cu front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` le găsește; o expresie între ghilimele care nu apare e încercată cuvânt cu cuvânt.
- **Glosarul** este `glossary.yaml`: `term: definition` sau o listă de `{term, definition, aliases, see}`. `didact define <term>` îl citește.

## Teste: `tests/`

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

## Distribuirea și eliminarea pachetelor

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Un pachet care declară `redistributable: false` nu poate fi exportat.
- **core** face parte din Didact și e mereu activ: fiecare sistem se bazează pe el, așa că nu poate fi dezactivat sau dezinstalat.
- Celelalte pachete incluse în Didact sunt fișiere `.didactpack` în dosarul lui `packs/`. `pack list` le arată până sunt instalate, iar instalarea unuia aduce și pachetele incluse de care are nevoie.
- `pack update` caută versiuni mai noi în dosarul `packs/` al lui Didact și pe GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` numește alt loc, sau niciunul, ca să nu caute). O versiune nouă se instalează lângă cea veche: campaniile o păstrează pe a lor până la `didact campaign upgrade`.
- Un singur sistem de joc e în uz la un moment dat: al lumii deschise. O lume își păstrează sistemul cu care a fost creată (`didact world new <id> --system <pack>`; una creată fără sistem îl primește pe primul care i se dă, cu `pack enable` sau `world set system=`), campaniile ei îl joacă, iar un pachet care are nevoie de alt sistem (un cadru de joc scris pentru el) nu poate fi adăugat: alt sistem se joacă într-o lume proprie.
- `uninstall` refuză cât timp o lume sau o campanie folosește singura copie a pachetului (`--force` îl elimină oricum). Nu se poate desface: instalează din nou fișierul .didactpack.

## De la cartea de reguli la pachet: lista de verificare

Parcurge mecanicile cărții în această ordine. Fiecare corespunde unui lucru de mai sus:

1. **Rezolvarea:** cum reușește o aruncare (un test: `success`, `bands`, `auto`).
2. **Zarurile:** zaruri neobișnuite, simboluri, trepte (`dice.yaml`, zaruri cu nume, lanțuri).
3. **Foaia:** atribute, numere derivate (`schemas/`, câmpuri derived).
4. **Resursele:** HP, noroc, avânt (câmpuri resource și counter; pași `set`).
5. **Condițiile:** stări și ce fac (câmpuri `conditions`; pași `if`).
6. **Lupta:** atacuri, daune, inițiativă (acțiuni; `bag`/`deck` pentru ordinea turelor).
7. **Procedurile:** explorare, călătorie, timp liber (proceduri cu întrebări).
8. **Tabelele:** fiecare tabel aleatoriu (`tables/`; `pack import` pentru tabelele Markdown).
9. **Bestiarul:** monștri și PNJ (`compendium/`).
10. **Obiectele:** echipament, vrăji, relicve (`compendium/`, câmpuri slots).
11. **Îndrumarea pentru MJ:** principii și sfaturi (`GUIDE.md`, `reference/`, `guidance:` pe tipuri).
12. **Crearea de personaje:** cum se face un personaj (o procedură `chargen/` sau `roll:` pe fiecare câmp).

Citează paginile cu `source:` peste tot, ca să iasă la iveală golurile. Adaugă un test de joc de probă care face un personaj, aruncă un test, luptă și rulează o procedură.
