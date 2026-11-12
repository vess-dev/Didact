<!-- translated from b1dfa1159ff4 -->
# Pack

Un pack è un sistema di gioco, un oracolo, un'ambientazione, un'avventura o un supplemento, scritto come file YAML più un plugin Python facoltativo. Questa guida mostra come scriverne uno: trasformare un manuale in un pack, o aggiungere contenuti fatti in casa.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Un pack si può anche creare da ciò che c'è nella libreria. `didact pack new my-brew --from-overlay my-system` trasforma l'homebrew per un sistema (`compendium add`, le schede conservate con `--scope system`, il lore) in un supplemento, e `didact world export --as setting` trasforma un mondo in un pack di ambientazione: le sue persone, i luoghi e il lore come voci del compendio e lore del pack, da portare in un altro mondo con `compendium import`. Entrambi lasciano fuori i segreti e le note del GM salvo `--secrets`, e nessuno dei due è segnato come condivisibile finché non se ne imposta la licenza.

## Struttura

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

Un file contiene un elemento, un elenco di elementi, o più elementi separati da `---`. Ogni elemento indica il proprio id con la chiave del suo genere: `table: weather`, `check: save`, `type: pc`, o `id: troll` per le voci del compendio. Ci si riferisce agli elementi come `pack.id` (`my-system.save`), o con il solo id quando un solo pack attivo lo possiede.

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

Un hack indica la propria base in `extends` e contiene solo ciò che cambia:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Il suo elemento con lo stesso id sostituisce quello della base, di qualunque genere sia (una tabella, una regola, una voce del compendio, una sezione di riferimento, un termine del glossario). I suoi `settings` si sovrappongono a quelli della base, chiave per chiave: una chiave impostata dall'hack sostituisce per intero il valore della base (le sue tabelle `names` prendono il posto di quelle della base), e anche le regole della base leggono i valori dell'hack. `hides` scarta ciò che resta e che all'hack non serve: `*` corrisponde a qualsiasi sequenza di caratteri, decide l'ultimo modello che corrisponde a un id, e uno che inizia con `!` conserva l'elemento. Ciò che l'hack sostituisce non viene mai nascosto. I generi sono `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` e `term`. `didact pack validate` avvisa di un modello che non corrisponde a nulla.

## Espressioni

Ogni condizione e formula usa il linguaggio dei dadi (`didact guide dice`), più:
- **Valori:** `@name` legge un valore: `@roll`, `@who.STR`, `@settings.x`. `$name` incolla prima il testo di un parametro, quindi `@who.$attr` diventa `@who.STR`. Leggi un parametro di testo libero come `@name`, non tra virgolette (`'$name'`): un apostrofo nel suo testo le chiuderebbe (`pack validate` lo segnala).
- **Logica:** `and`, `or`, `not`, e `in` (`'deprived' in @who.conditions`).
- **Letterali:** testo (`'travel'`) e `true`/`false`.
- **Funzioni:** `if(cond, a, b)` tira solo il ramo che prende. `default(@thread.flashpoint, 0)` è il valore, o il ripiego quando non è impostato. `sum`, `count` (`count(@roll.dice, 6)` conta i sei), `min`, `max`, `any` e `all` accettano liste.

## Schede: `schemas/`

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

| Genere | Contiene | Opzioni |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | un valore semplice | min, max; `values` per enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` è il valore, `@hp.max` il tetto | range; min; max o max_field; die |
| `counter` | un numero | min, max, thresholds, occupies (un campo slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | oggetti (`Rope` o `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | come dice il nome | `to` (per refs), `allowed` |
| `derived` | calcolato, mai salvato | expr |

Ogni campo accetta anche `label`, `help`, `default`, `required` e `roll`: `new pc Hero --fill`, o un valore `"roll"`, lo tira tramite il registro. I tipi del pack `core` contengono testo indipendente dal sistema in `fields`. I tipi di un sistema contengono i suoi numeri in `mechanics.<system>`. `set hero hp-=2` trova il campo, lo limita e segnala ogni eccedenza. `+=` aggiunge a una lista: un campo `list` (come `slots`) conserva un valore aggiunto di nuovo, `tags`, `conditions` e `refs` lo conservano una volta sola, e `-=` ne toglie ogni copia.

**Gli hook** dicono cosa succede quando un valore supera una soglia. Scattano a ogni modifica (`set`, `inv`, il passo `set` di una regola), ma solo quando la soglia viene superata: 3 → 0 scatta, 0 → 0 no. Le modifiche con `--force` li saltano.

| Hook | Scatta quando |
|---|---|
| `on_zero` | un numero o `{value}` arriva a 0 |
| `on_full` (`when_full` sugli slots) | arriva al suo massimo, alla sua dimensione o capacità |
| `thresholds: {10: …, 20: …}` (contatori) | supera ogni soglia |

Un'azione è testo (una nota per l'LLM), `{set: {hp: 0}}` o `{condition: paralyzed}` sulla stessa scheda, `{trigger: death}` (esegue quella regola con `who` = la scheda), o una lista di questi.

**L'inventario** (`didact inv …`) agisce sul campo `slots` della scheda:
- **Spazio:** gli oggetti occupano la loro `size` × `count`, e i contatori che `occupies` il campo occupano il loro valore. Superare `capacity` viene rifiutato, salvo con `--force`.
- **Gruppi:** `groups: {backpack: 6, body: 4}` dà a ogni gruppo il proprio spazio, e anche le proprie colonne e i propri totali: `@inventory.body.armor` è solo ciò che si indossa o si tiene in mano, `@inventory.body.free` lo spazio che gli resta.
- **Usi:** `uses: 3` scala con `inv use`. `uses: d8` è un dado di usura: con 1–2 scende di un gradino. Un oggetto esaurito sparisce, a meno che abbia `recharge` o `keep: true`. Di più oggetti con lo stesso nome, il nome indica il primo; per spendere un uso (`inv use`, il `use:` di una regola, `set …uses-=1`), il primo a cui ne resta uno.
- **Chiavi proprie di un oggetto:** `didact set freya inventory.sword.damage=d10` (anche il `set: who.inventory.$item.damage` di una regola) ne modifica una, indicando l'oggetto come lo indica `inv`, con una parte del suo nome o con il nome intero, spazi e punti compresi (`'inventory.12.7mm pistol.damage=d10'`, tra virgolette per la shell); `uses` e `charges` funzionano come un campo `uses` (`charges+=2` si ferma al suo massimo), e lo spazio viene controllato come fa `inv add`. Una regola ne legge una come `@{who.inventory.$item.damage}` (un dado di usura come il suo dado, gli usi come il loro numero); un oggetto o una chiave che non c'è si legge come assente, così `default(…)` dà il suo valore di ripiego.
- **Compendio:** le voci di tipo `item` (o weapon, armor, relic, …, o un tipo proprio del pack che ne estende uno con `extends`) prestano i loro dettagli a `inv add`, trovate per id, per nome o per un alias (se due ne condividono uno: indicala come `pack.id`); qualsiasi altro nome, `:` compresi, è il nome proprio dell'oggetto.

## Tabelle: `tables/`

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

Altre forme:
- **Liste pesate:** `entries` come lista, con `weight:` per ogni voce.
- **Colonne:** `columns: [a, b]` tira ogni colonna di una riga separatamente. Una voce semplice (non una lista) riempie ogni colonna, quindi `columns: [first, second]` su un elenco di parole significa "tira due volte su questo elenco". `labels: false` toglie i nomi delle colonne dal risultato ("Abandon · Advantage"). `read: "It's a {first} {second} with {third} {fourth} inside."` legge le colonne come una frase.
- **Tabelle di consultazione:** `lookup: hp_lost`, o `[odds, chaos]` per una tabella a doppia entrata.
- **Doppioni:** `duplicates: reroll | keep | make_it_worse` per "tira due volte".
- **In due passaggi:** una voce che tira su un'altra tabella (`{table: lightning}` al posto del testo, o `then:` dopo di esso) porta con sé i dati di quel tiro: una regola o una bozza che la tira legge entrambi, prima le chiavi proprie della voce, poi quelle della prima tabella tirata dopo. Un `--prefill` può nominare una voce più in basso, a qualsiasi profondità (`Ring of the Hunt`), con i dati di ogni voce lungo il percorso: di due con lo stesso nome conta la più vicina (poi la prima), una che prosegue tira da lì in poi, e una vicina a una di esse senza essere nessuna viene rifiutata, indicando la più vicina. Una bozza guidata offre il primo passaggio quando le sue voci dicono cosa sono (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): sceglierne una tira sulla tabella successiva, come un tiro che ci cade sopra.
- **Lettura nei due sensi:** `both_ways: true` su una tabella d66 aggiunge l'altra lettura: 31 dà anche 13, e chi legge sceglie.
- **Cosa significa una voce:** `about: "Knows: {skills}. Also known as: {aka}."` si compila con i dati di ogni voce (una lista si legge `a, b`; `{text}` è la voce stessa) per dire cosa dà quando una scelta la offre; il `note:` proprio di una voce lo dice al suo posto. Senza nessuno dei due, una voce i cui dati hanno un `id` che nomina una voce del compendio è descritta da quella voce.
- **Mazzi e sacchetti:** `deck: tarot` con `cards` (o `standard: true`); `bag: initiative` con `tokens`.

La validazione controlla che ogni risultato possibile dei dadi cada su una voce.

## Regole: `rules/`

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

Azioni e procedure sono liste di passi, e i trigger sono passi con una guardia `when:`. I passi sono:

| Passo | Cosa fa |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | un tiro registrato; lega `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; un `{…}` viene riempito prima, come in qualsiasi testo, così si tirano i dadi che un valore tiene come testo (`{@{who.inventory.$item.damage}}`), e il registro li mostra: un valore che non sono dadi viene rifiutato, e così `roll: "@die"` con un testo simile, che non tira nulla; un insieme di tiri (`{d8, d6}kh1`) resta tale |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | calcola valori; come per il `value` di `set`, un testo `{…}` è un modello e una parola da sola è testo; in ogni testo che si riempie, `{{` e `}}` scrivono la parentesi graffa stessa |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (o `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | modifica una scheda: validato, limitato, annullabile; `set: who.$attr` imposta il campo indicato da un parametro, e `set: who.inventory.$item.damage` una chiave di un oggetto che la scheda porta con sé (vedi Inventario); `-=` toglie un valore da un elenco, e uno che non contiene non cambia nulla (una nota lo dice; uno che non potrebbe mai contenere viene rifiutato); `unset:` toglie un campo, come `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | dà un oggetto a una scheda o gliene toglie uno, come fanno `inv add` e `inv drop`: i dettagli vengono dal compendio, basta una parte univoca del nome, e si controllano lo spazio e gli hook del campo |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | usa un oggetto portato come fa `inv use`: usi o cariche scalano, un dado di usura si tira e scende di un gradino con 1–2, e uno che si esaurisce sparisce, a meno che si ricarichi o venga tenuto; di più oggetti con quel nome, il primo a cui resta un uso; lega `@torch.out` (il suo ultimo uso è andato), `@torch.gone` (non ne resta niente), `@torch.left`, `@torch.die` e `@torch.rolled` (`as:` è `use` per impostazione predefinita) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | crea subito una scheda, descritta come nel passo `entity` di una bozza (vedi sotto) e controllata secondo il suo foglio; `as:` (altrimenti la sua `key`, altrimenti il suo tipo) la lega come scheda, che si legge e si imposta come un parametro `ref` (`pool: "@bleeding"`, `@bleeding.name`), e non è mai il nome di un parametro; senza `key:` nessun campo viene preso per una chiave (`kind: track` resta com'è scritto); se qui ce n'è già una con quel tipo e quel nome, viene presa così com'è, quindi una regola eseguita di nuovo non crea niente di nuovo |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | esegue una prova e lega il suo esito |
| `do: other-action`, `with: {…}`, `as: trip` | esegue un'altra regola; `@trip` è il suo esito e `@trip.<name>` ciò che ha legato (`@trip.found` per il suo `let: {found: 2}`, `@trip.luck` per il suo `roll: d6`, `as: luck`); `as:` è il suo id per impostazione predefinita |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | un tiro su tabella registrato; lega il testo e i `data` della voce (`@scar.<key>`, e le chiavi di una mappa tramite il loro percorso: `@scar.cost.hp`), insieme a quelli di ogni tabella tirata in seguito; un elenco di oggetti (`[Rope, {name: Laser, damage: d8}]`) si legge come i loro nomi (`count(@scar.gear)`, `'Laser' in @scar.gear`), e passato così com'è a un passo (`apply: "@scar.gear"`) sono gli oggetti stessi; un elenco di altre mappe lo legge solo un passo |
| `table: "setting-{@drop.difficulty}-terrain"` | una tabella calcolata: `{…}` e `$param` vengono riempiti |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | più risultati come lista (`distinct` ritira le ripetizioni) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | rami |
| `repeat: "@count"`, `as: i`, `steps: […]` | un ciclo: esegue i passi quel numero di volte, con `@i` che conta da 1 |
| `for: pcs` (o `party`), `as: member`, `steps: […]` | esegue i passi una volta per ogni personaggio giocante (o membro del gruppo), come `@member`: una scheda, simile a quella che lega `entity:` (`@member.name`, `set: member.fatigue`); `as:` non prende mai il nome di un parametro, quindi il `who` proprio della regola resta intatto |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | output per l'LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (o `every: 1 day`) | un promemoria che arriva a scadenza man mano che passa il tempo di gioco, come quelli che imposta `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | ritira alcuni dadi di un tiro (meccaniche per forzare un tiro) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | tira su un valore lista (le liste di un oracolo): lega la voce, `@who.choose` (una riga vuota) e `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | tira la riserva decrescente di un contatore come fa `track roll` (i dadi che mostrano 1-3 escono; i dadi di `drop` vengono scartati per primi, quelli di `extra` vengono tirati insieme) o scarta soltanto dei dadi (`mode: drop`: forzare, spuntare); seguono le fasi collegate e l'evento della riserva; lega `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

L'esito di una prova è leggibile dalla regola che l'ha eseguita (`check: … as: answer` dà `@answer`), e così i suoi indicatori: `'random-event' in @answer.flags`. I valori di `with:` vengono valutati quando contengono `@`, riempiti quando contengono `$param` o `{…}` ("Does $npc flee?"), e passati così come sono altrimenti. Una regola con un parametro `oracle` riceve la scheda di stato dell'oracolo della campagna senza che glielo si dica. Un parametro `ref` con `to: monster` prende una scheda di quel tipo: un nome che un'altra scheda condivide (la riserva di un nemico, chiamata come la sua carta) è quella di quel tipo.

I trigger si eseguono da soli quando avviene il loro evento, e solo se il loro `when:` è vero:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Qualsiasi regola (anche un generatore e la creazione del personaggio) può leggere `@system` (l'id del sistema di gioco del mondo, così un'ambientazione scritta per due sistemi può distinguerli), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` e `@time.is_night` e, con un calendario a mesi, `@time.month`, `@time.month_name`, `@time.day_of_month` e `@time.year`; mentre è in corso un combattimento, `@combat.round` e `@combat.fighters` (gli id di chi vi prende parte). Un trigger temporale può leggere anche `@time.passed`, i secondi appena trascorsi, un trigger `combat_start` o `combat_end` legge il combattimento che inizia o finisce (`combat start` e `combat end` li eseguono; un combattente che se ne va non pone fine al combattimento), e una regola eseguita da un trigger legge ciò che legge il trigger. Un trigger con parametri obbligatori viene eseguito solo da `didact do` o da un hook di campo (`who` = la scheda). I trigger `on: manual` si eseguono solo quando vengono chiamati. `for: pcs` (o `party`) esegue un trigger una volta per ogni personaggio giocante (o membro del gruppo), come `who`: l'esperienza dopo ogni sessione, per esempio. Un trigger che fallisce ferma il comando che l'ha lanciato, e dice quale trigger era e come andare avanti senza (`didact override add trigger <id> --data '{"on": "manual"}'`).

Il calendario sta nei `settings` di un pack: quello di un pack di ambientazione prevale su quello del sistema, e quello proprio di un mondo (`calendar:` nel suo `world.yaml`) su entrambi:

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

`leap: 4` allunga un mese di un giorno ogni 4 anni, e `leap: [4, 100, 400]` ogni 4, ma non ogni 100, ma di nuovo ogni 400: ogni numero prevale sul precedente. `weekday` nomina il giorno della settimana dell'inizio (altrimenti è il primo della settimana), e `year` è come una data scrive il suo anno, sia in quelle che Didact mostra sia in quelle che legge (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` controlla tutti e tre. Una campagna può iniziare in un'altra data del calendario, prima del suo inizio o dopo: `didact campaign new <id> --date '4 July 1902'`, oppure `didact time set '<date>'` fino alla sua prima sessione. Un giorno della settimana scritto prima della data viene controllato: decide la data, e una nota lo dice quando cade in un altro.

Le opzioni sono le varianti e le regole opzionali del sistema, che ogni campagna sceglie nella sessione zero:

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

`didact campaign profile lethality=deadly supplies=on` le salva (o la pagina Impostazioni dell'app web). Le regole, la creazione del personaggio e i generatori le leggono (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): una risposta prevale su ciò che un'altra opzione implica, che prevale sul valore predefinito. Ciò che un'opzione implica viene seguito fino in fondo (un'atmosfera che imposta la letalità imposta anche ciò che quella letalità implica), e tra due implicazioni prevale la più vicina. Il riepilogo elenca quelle che differiscono dal loro valore predefinito, con il loro significato, perché il master applichi ciò che le regole non possono. Un generatore che non può funzionare con esse si ferma con `stop:` e il motivo, e non viene creata alcuna bozza.

## Oracoli: `oracles/`

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

- **Interrogare:** `didact ask '…' --odds likely` esegue la prova `ask`. La risposta è il suo esito (una fascia), e i suoi indicatori la accompagnano.
- **Stato:** vive in una scheda che la prova riceve come `oracle`. Una prova lo modifica con `set: oracle.chaos += 1`.
- **Liste:** `lists: {names: […], method: sections, most: 3}` tiene liste pesate su quella scheda. `didact lists add|drop|roll|show` le gestiscono, e le regole ci tirano con `pick`. `sections` tira una sezione di cinque righe, poi una riga al suo interno (una riga vuota significa a scelta); `uniform` dà a ogni riga la stessa probabilità.
- **Altro per la prova:** `didact ask '…' --with as_rule=true` passa parametri in più alla prova dell'oracolo.
- **Il registro:** ogni risposta è numerata (`#o12`) e registrata, e `didact interpret o12 '…'` conserva cosa significava. L'oracolo `yes-no` del pack core fa da ripiego.

## Generatori e creazione del personaggio: `generators/`, `chargen/`

Entrambi sono procedure che costruiscono una **bozza**. Usano ogni passo delle regole (`roll`, `table`, `if`, `let`, `prompt`, …) più questi:

| Passo | Cosa fa |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | aggiunge una scheda alla bozza (chiavi `poi-1`, `poi-2`, …); un campo o un collegamento che nomina una chiave scritta dal pack (`key:`, o un nome `as:`) diventa l'id di quella scheda alla conferma, quindi scegli chiavi che nessun campo contenga come testo (un'entità senza né l'una né l'altro non ne ha da sostituire); `from: "@relic.id"` la crea a partire da una voce del compendio (il suo tipo, il nome e i campi) |
| `choose: {from: [a, b], as: x}` (o `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | una scelta; in modalità guidata la bozza attende `choose`; `exclude` esclude le scelte precedenti (se i dadi ne tirano una, si ritira); `records:` aggiunge le schede di quel tipo presenti qui, per ID (create durante il gioco); `answer:` fa la scelta quando il suo valore è una delle opzioni (il percorso proprio di un personaggio), senza chiedere |
| `choose_or_roll: {table: backgrounds, as: background}` | una scelta che possono fare i dadi; i dati di una voce scelta sono `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | tira nel personaggio |
| `swap: {among: [STR, DEX, WIL], optional: true}` | scambia due punteggi, o li tiene |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | distribuisce una serie fissa |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | compra punteggi entro un budget (`default: random` lo spende a caso in modalità casuale) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | una lista va nell'inventario; una mappa imposta campi (le liste si sommano) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | aggiunge a un campo del personaggio (o di un'entità della bozza): i numeri si sommano, il resto si aggiunge a una lista; niente da aggiungere va bene |
| `remove: {field: talents, value: "@old"}` | toglie qualcosa da un campo lista (un talento sostituito, un legame risolto); niente da togliere va bene |
| `roll_tables: [physique, vice]` | tira tabelle in `traits`; il `data.gear` di una voce va nell'inventario e `data.add: {gold: 20}` aggiunge ai campi |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | il nome; `name: {prompt: …}` senza niente da cui tirare ne attende uno, anche in modalità casuale |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | una domanda a cui va bene qualsiasi risposta (un obiettivo, il nome di un'altra scheda): la bozza la attende, anche in modalità casuale, salvo che sia precompilata; `field:` memorizza la risposta |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | un pointcrawl: un lancio di dadi sulla mappa registrato, percorsi (sempre collegati), distanze, percorsi nascosti (vedi sotto) |

Il passo map accetta altro, per le procedure dei manuali basate sul lancio di dadi sulla mappa:

| Chiave | Cosa fa |
|---|---|
| `regions: terrain` | anche queste entità vengono lanciate; ogni luogo si unisce alla più vicina (la sua `region`) |
| `hidden: 6`, `conditional: 5` | un d6 per percorso: da quel numero in su, un percorso nascosto o condizionale (i percorsi nascosti restano fuori dalla mappa dei giocatori) |
| `describe: [path-feature, path-condition]` | tabelle tirate per ogni percorso, conservate come suoi `details` |
| `entrance: true`, `exit: true` | il luogo più vicino al bordo è l'ingresso; gli altri sono numerati a partire da lì lungo i percorsi (`map.n`), i percorsi se ne allontanano, e l'uscita è un luogo lontano vicino a un bordo, numerato per ultimo |
| `number: "{@dungeon_name}, room {@n}"` | rinomina i luoghi numerati (le loro chiavi di bozza seguono: `room-1` è la stanza 1) |

Una tabella per il lancio di dadi può nominare le tabelle successive nei dati delle sue voci, così la procedura si legge come il manuale: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, poi `table: "{@drop.what}"`. I campi lista non impostati (condizioni, liste, tag) si leggono come liste vuote, quindi `'deprived' in @who.conditions` funziona fin dall'inizio.

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

Un chargen con `advances:` modifica una scheda invece di crearne una: l'avanzamento di livello del sistema.

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

- **Una sola scheda:** un generatore con `creates: npc` costruisce quella scheda come la creazione del personaggio costruisce un personaggio (`apply`, `add`, `name`, `field:`); i suoi passi `entity` aggiungono schede accanto, e un collegamento `to: character` punta a essa.
- **Eseguire:** `gen run` e `char new` creano una bozza (`#g7`, `#c3`) e non scrivono nulla. Uno `stop:` la chiude senza creare nulla: sotto un `if:` che legge un'opzione della campagna, il suo suggerimento rimanda alle opzioni (`didact session zero`); altrimenti le sue parole dicono cosa fare invece.
- **Decidere:** `--prefill '{…}'` decide le cose in anticipo, per il nome che un passo lega (`as:`): un valore singolo risponde a ogni occorrenza, una lista a un'occorrenza ciascuno (una lista per `choose` con `count` è l'intera scelta). Anche i valori di `let` si possono precompilare (`{"hp": 6}`), e un nome, un `ask` o un `let` conserva qualsiasi testo così come viene dato. Un valore per una scelta tra opzioni note (un `choose`, la voce di una tabella) è l'opzione che nomina, così come è scritta o con maiuscole e minuscole diverse, tramite l'`id` della sua voce, o tramite un tiro che cade su di essa (`{"group": 3}`), e porta con sé i dati di quella voce; un valore vicino a un'opzione ma diverso da tutte viene rifiutato, con l'indicazione della più vicina, e ogni altro è una risposta libera, senza dati. `--auto` (o `char new --mode random`) lascia decidere il resto ai dadi. Altrimenti la bozza si ferma a ogni scelta.
- **Descrivere:** una scelta dice cosa significa ogni opzione, per il giocatore che sceglie: il `note:` di una voce di tabella o l'`about:` della sua tabella, altrimenti la voce del compendio che nomina (l'`id` dei suoi dati), o quella che è l'opzione stessa (una scelta tra ID del compendio mostra il nome di ciascuno): i suoi `tagline` e `summary`, la sua `description` o il suo `effect`, altrimenti il primo paragrafo del suo testo.
- **Tornare indietro:** `char back` (o `gen back`) annulla l'ultima risposta, l'ultimo tiro o l'ultima modifica, così la bozza ripropone quella domanda; i tiri fatti da quel passo vengono segnati come annullati.
- **Riprendere:** una bozza ripresa rigioca la sua traccia: ogni valore tirato o scelto, ognuno usato una volta e in ordine (anche il lancio di dadi della mappa), quindi nulla viene tirato due volte e nulla di già deciso cambia.
- **Scrivere:** `commit` scrive le schede, controllate secondo i loro fogli.
- **Avanzare:** una bozza `advances:` parte da una copia della scheda (con i valori predefiniti del suo foglio), i suoi passi leggono la scheda come `@who` e i valori della bozza come `@character.*`, e `commit` scrive solo ciò che è cambiato, controllato come con `set`; le schede prodotte dai suoi passi `entity` (la trama di un nuovo legame) vengono create accanto: un collegamento `to: character` punta alla scheda, e un campo che nomina una chiave contiene l'id della scheda di quella chiave, come quando si crea un personaggio (`apply: {blood: "@pool"}`). Uno `stop:` dice perché non è ancora possibile (PE insufficienti), e non viene creata nessuna bozza. Un sistema la cui crescita è una sola regola la indica invece sul suo chargen: `advance: {rule: grow}`.
- **Modalità:** `modes: [guided]` mantiene una procedura passo per passo: `--mode random` viene rifiutato.

## Compendio, riferimento e glossario

- **Le voci del compendio** si scrivono come `new --data`: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Un valore `"roll 2d8"` viene tirato quando la voce viene generata. Esegui `didact spawn troll`, oppure porta nel mondo le voci di un pack con `didact compendium import <pack>` (`--type loc`, e `--tag coast` per quelle che hanno ogni tag indicato).
- **Per più sistemi:** una chiave di primo livello va dove la mette `set`: nel blocco del sistema quando il suo foglio ha quel campo, altrimenti in `fields`. Una voce che un'ambientazione scrive per più di un sistema dà i numeri di ciascuno nel suo blocco (`mechanics: {my-system: {hp: 12}}`): `pack validate` controlla ciascun blocco rispetto al foglio di quel sistema quando è installato, e segnala una chiave di primo livello che quel foglio e quello di core hanno entrambi. Ciò che dice un blocco vale: accanto a `mechanics: {my-system: {role: tactician}}`, un `role: innkeeper` di primo livello è il campo di core, come tutto ciò che sta sotto `fields:`. Un blocco che nomina il pack in convalida viene controllato secondo quel pack così com'è nella sua cartella.
- **Le sezioni di riferimento** vanno in `reference/*.md`, con un front matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` le trova; una frase tra virgolette che non c'è viene provata parola per parola.
- **Il glossario** è `glossary.yaml`: `term: definition`, o una lista di `{term, definition, aliases, see}`. `didact define <term>` lo legge.

## Test: `tests/`

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

## Condividere e rimuovere i pack

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Un pack che dichiara `redistributable: false` non si può esportare.
- **core** fa parte di Didact ed è sempre attivo: ogni sistema si basa su di esso, quindi non si può disattivare né disinstallare.
- Gli altri pack inclusi in Didact sono file `.didactpack` nella sua cartella `packs/`. `pack list` li mostra finché non sono installati, e installarne uno porta con sé i pack inclusi di cui ha bisogno.
- `pack update` cerca versioni più recenti nella cartella `packs/` di Didact e su GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` indica un altro posto, o nessuno per non cercare). Una nuova versione si installa accanto alla vecchia: le campagne tengono la loro fino a `didact campaign upgrade`.
- Si usa un solo sistema di gioco alla volta: quello del mondo aperto. Un mondo mantiene il sistema con cui è stato creato (`didact world new <id> --system <pack>`; uno creato senza sistema prende il primo che gli viene dato, con `pack enable` o `world set system=`), le sue campagne si giocano con esso, e non si può aggiungere un pack che richiede un altro sistema (un'ambientazione scritta per esso): un altro sistema si gioca in un mondo tutto suo.
- `uninstall` si rifiuta finché un mondo o una campagna usa l'unica copia del pack (`--force` lo rimuove comunque). Non si può annullare: installa di nuovo il .didactpack.

## Dal manuale al pack: la lista di controllo

Passa in rassegna le meccaniche del manuale in quest'ordine. Ognuna corrisponde a qualcosa qui sopra:

1. **Risoluzione:** come riesce un tiro (una prova: `success`, `bands`, `auto`).
2. **Dadi:** dadi insoliti, simboli, gradini (`dice.yaml`, dadi con nome, catene).
3. **La scheda:** caratteristiche, valori derivati (`schemas/`, campi derivati).
4. **Risorse:** PF, fortuna, slancio (campi resource e counter; passi `set`).
5. **Condizioni:** gli stati e i loro effetti (campi `conditions`; passi `if`).
6. **Combattimento:** attacchi, danni, iniziativa (azioni; `bag`/`deck` per l'ordine dei turni).
7. **Procedure:** esplorazione, viaggio, tempo libero (procedure con indicazioni).
8. **Tabelle:** ogni tabella casuale (`tables/`; `pack import` per le tabelle Markdown).
9. **Il bestiario:** mostri e PNG (`compendium/`).
10. **Oggetti:** equipaggiamento, incantesimi, reliquie (`compendium/`, campi slots).
11. **Consigli per il GM:** principi e consigli (`GUIDE.md`, `reference/`, `guidance:` sui tipi).
12. **Creazione del personaggio:** come si crea un personaggio (una procedura `chargen/`, o `roll:` su ogni campo).

Cita le pagine con `source:` ovunque, così le lacune saltano fuori. Aggiungi un test di gioco rapido che crei un personaggio, tiri una prova, combatta ed esegua una procedura.
