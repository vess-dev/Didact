<!-- translated from b1dfa1159ff4 -->
# Pakete

Ein Paket ist ein Spielsystem, Orakel, Setting, Abenteuer oder Zusatzmaterial, geschrieben als YAML-Dateien plus optionalem Python-Plugin. Diese Anleitung zeigt, wie man eines schreibt: ein Regelwerk in ein Paket verwandeln oder eigene Hausinhalte hinzufügen.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Ein Paket lässt sich auch aus dem machen, was in deiner Bibliothek liegt. `didact pack new my-brew --from-overlay my-system` macht aus deinem Homebrew für ein System (`compendium add`, mit `--scope system` geführte Einträge, Lore) ein Zusatzmaterial, und `didact world export --as setting` macht aus einer Welt ein Setting-Paket: ihre Personen, Orte und Lore als Kompendiumseinträge und Paket-Lore, die `compendium import` in eine andere Welt holt. Beide lassen Geheimnisse und die Notizen der SL weg, außer mit `--secrets`, und keines ist als teilbar markiert, bis du seine Lizenz setzt.

## Aufbau

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

Eine Datei enthält ein Element, eine Liste von Elementen oder mehrere durch `---` getrennte Elemente. Jedes Element nennt seine ID mit dem Schlüssel seiner Art: `table: weather`, `check: save`, `type: pc` oder `id: troll` bei Kompendiumseinträgen. Verweise auf Elemente als `pack.id` (`my-system.save`) oder über die bloße ID, wenn nur ein aktiviertes Paket sie hat.

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

Ein Hack nennt seine Basis in `extends` und enthält nur, was abweicht:

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Sein Element mit derselben ID ersetzt das der Basis, gleich welcher Art (eine Tabelle, eine Regel, ein Kompendiumseintrag, ein Referenzabschnitt, ein Glossarbegriff). Seine `settings` überlagern die der Basis Schlüssel für Schlüssel: Ein Schlüssel, den der Hack setzt, ersetzt den Wert der Basis als Ganzes (seine `names`-Tabellen treten an die Stelle derer der Basis), und auch die Regeln der Basis lesen die Werte des Hacks. `hides` lässt weg, was sonst übrig bleibt und der Hack nicht braucht: `*` passt auf jede Zeichenfolge, das letzte Muster, das auf eine ID passt, entscheidet, und eines, das mit `!` beginnt, behält das Element. Was der Hack ersetzt, wird nie verborgen. Die Arten sind `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` und `term`. `didact pack validate` warnt vor einem Muster, das auf nichts passt.

## Ausdrücke

Jede Bedingung und jede Formel verwendet die Würfelsprache (`didact guide dice`), dazu:
- **Werte:** `@name` liest einen Wert: `@roll`, `@who.STR`, `@settings.x`. `$name` fügt zuerst den Text eines Parameters ein, sodass `@who.$attr` zu `@who.STR` wird. Lies einen Parameter mit freiem Text als `@name`, nicht in Anführungszeichen (`'$name'`): ein Apostroph in seinem Text würde sie beenden (`pack validate` warnt).
- **Logik:** `and`, `or`, `not` und `in` (`'deprived' in @who.conditions`).
- **Literale:** Text (`'travel'`) und `true`/`false`.
- **Funktionen:** `if(cond, a, b)` würfelt nur den Zweig, den es nimmt. `default(@thread.flashpoint, 0)` ist der Wert oder der Ersatzwert, wenn er nicht gesetzt ist. `sum`, `count` (`count(@roll.dice, 6)` zählt die Sechsen), `min`, `max`, `any` und `all` nehmen Listen.

## Bögen: `schemas/`

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

| Art | Enthält | Optionen |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | einen einfachen Wert | min, max; `values` für enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}`: `@hp` ist der Wert, `@hp.max` die Obergrenze | range; min; max oder max_field; die |
| `counter` | eine Zahl | min, max, thresholds, occupies (ein slots-Feld) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | Gegenstände (`Rope` oder `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | wie benannt | `to` (für refs), `allowed` |
| `derived` | berechnet, nie gespeichert | expr |

Jedes Feld nimmt außerdem `label`, `help`, `default`, `required` und `roll`: `new pc Hero --fill` oder ein Wert von `"roll"` würfelt es über das Protokoll. Typen aus dem Paket `core` enthalten systemunabhängigen Text in `fields`. Die Typen eines Systems enthalten seine Zahlen in `mechanics.<system>`. `set hero hp-=2` findet das Feld, begrenzt den Wert und meldet jeden Überlauf. `+=` fügt einer Liste etwas hinzu: Eine `list` (wie `slots`) nimmt denselben Wert auch mehrfach auf, `tags`, `conditions` und `refs` enthalten ihn nur einmal, und `-=` entfernt alle Kopien.

**Hooks** legen fest, was passiert, wenn ein Wert eine Grenze überschreitet. Sie greifen bei jeder Änderung (`set`, `inv`, ein `set`-Schritt einer Regel), aber nur, wenn die Grenze überschritten wird: 3 → 0 löst aus, 0 → 0 nicht. Änderungen mit `--force` überspringen sie.

| Hook | Löst aus, wenn |
|---|---|
| `on_zero` | eine Zahl oder `{value}` 0 erreicht |
| `on_full` (`when_full` bei slots) | sie ihr Maximum, ihre Größe oder Kapazität erreicht |
| `thresholds: {10: …, 20: …}` (counters) | sie jede Marke übersteigt |

Eine Aktion ist Text (eine Notiz für das LLM), `{set: {hp: 0}}` oder `{condition: paralyzed}` auf demselben Eintrag, `{trigger: death}` (führt diese Regel mit `who` = dem Eintrag aus) oder eine Liste davon.

**Inventar** (`didact inv …`) arbeitet mit dem `slots`-Feld des Bogens:
- **Platz:** Gegenstände belegen ihre `size` × `count`, und Zähler, die das Feld mit `occupies` belegen, ihren Wert. Über `capacity` hinaus wird abgelehnt, außer mit `--force`.
- **Gruppen:** `groups: {backpack: 6, body: 4}` gibt jeder Gruppe ihren eigenen Platz und ihre eigenen Spalten und Summen: `@inventory.body.armor` ist nur, was getragen oder in der Hand gehalten wird, `@inventory.body.free` ihr restlicher Platz.
- **Verbrauch:** `uses: 3` zählt mit `inv use` herunter. `uses: d8` ist ein Verbrauchswürfel: Bei 1–2 sinkt er eine Stufe. Ein verbrauchter Gegenstand ist weg, außer er hat `recharge` oder `keep: true`. Von mehreren Gegenständen mit demselben Namen meint der Name den ersten; um einen Verbrauch auszugeben (`inv use`, der `use:`-Schritt einer Regel, `set …uses-=1`), den ersten, der noch einen übrig hat.
- **Eigene Schlüssel eines Gegenstands:** `didact set freya inventory.sword.damage=d10` (in einer Regel auch `set: who.inventory.$item.damage`) ändert einen davon, wobei der Gegenstand so angegeben wird wie bei `inv`, mit einem Teil seines Namens oder dem ganzen, samt Leerzeichen und Punkten (`'inventory.12.7mm pistol.damage=d10'`, für die Shell in Anführungszeichen); `uses` und `charges` zählen wie ein `uses`-Feld (`charges+=2` geht nicht über das Maximum hinaus), und der Platz wird so geprüft wie bei `inv add`. Eine Regel liest einen als `@{who.inventory.$item.damage}` (einen Verbrauchswürfel als seinen Würfel, Verbrauch als seine Anzahl); ein Gegenstand oder Schlüssel, der nicht da ist, gilt als fehlend, sodass `default(…)` seinen Ersatzwert liefert.
- **Kompendium:** Einträge vom Typ `item` (oder weapon, armor, relic, … oder ein eigener Typ des Pakets, der einen davon per `extends` erweitert) leihen `inv add` ihre Details, gefunden über ID, Namen oder einen Alias (teilen sich zwei einen, nenne den gemeinten als `pack.id`); jeder andere Name, `:` und alles, ist der eigene Name des Gegenstands.

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

Andere Formen:
- **Gewichtete Listen:** `entries` als Liste, mit `weight:` pro Eintrag.
- **Spalten:** `columns: [a, b]` würfelt jede Spalte einer Zeile getrennt. Ein einfacher Eintrag (keine Liste) füllt jede Spalte, sodass `columns: [first, second]` über einer Wortliste „zweimal auf dieser Liste würfeln“ bedeutet. `labels: false` lässt die Spaltennamen im Ergebnis weg („Abandon · Advantage“). `read: "It's a {first} {second} with {third} {fourth} inside."` liest die Spalten als Satz.
- **Nachschlagetabellen:** `lookup: hp_lost` oder `[odds, chaos]` für eine 2-D-Tabelle.
- **Doppelte:** `duplicates: reroll | keep | make_it_worse` für „zweimal würfeln“.
- **Zweistufige Würfe:** Ein Eintrag, der auf eine andere Tabelle würfelt (stattdessen `{table: lightning}` oder danach `then:`), bringt die Daten dieses Wurfs mit: Regeln und Entwürfe, die ihn erwürfeln, lesen beides, zuerst die eigenen Schlüssel des Eintrags, dann die der ersten Tabelle, auf die danach gewürfelt wird. Ein `--prefill` kann einen Eintrag weiter unten nennen, in jeder Tiefe (`Ring of the Hunt`), mit den Daten jedes Eintrags auf dem Weg: von zweien eines Namens ist der nähere gemeint (dann der erste), einer, der weitergeht, würfelt von dort weiter, und einer, der einem davon nahekommt, aber keiner ist, wird abgelehnt, und der nächstliegende wird genannt. Ein geführter Entwurf bietet die erste Stufe an, wenn ihre Einträge sagen, was sie sind (`{text: "A ring: roll on Rings", then: [{table: rings}]}`): Wählt man einen, wird auf die nächste Tabelle gewürfelt, wie bei einem Wurf, der auf ihm landet.
- **In beide Richtungen lesen:** `both_ways: true` auf einer d66-Tabelle fügt die andere Lesart hinzu: 31 ergibt auch 13, und der Lesende wählt.
- **Was ein Eintrag bedeutet:** `about: "Knows: {skills}. Also known as: {aka}."` füllt die Daten jedes Eintrags ein (eine Liste liest sich `a, b`; `{text}` ist der Eintrag selbst), um zu sagen, was er gibt, wenn eine Wahl ihn anbietet; das eigene `note:` eines Eintrags sagt es stattdessen. Ohne beides wird ein Eintrag, dessen Daten eine `id` haben, die einen Kompendiumseintrag nennt, durch diesen Kompendiumseintrag beschrieben.
- **Decks und Beutel:** `deck: tarot` mit `cards` (oder `standard: true`); `bag: initiative` mit `tokens`.

Die Validierung prüft, dass jedes Ergebnis, das die Würfel liefern können, auf einem Eintrag landet.

## Regeln: `rules/`

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

Aktionen und Abläufe sind Schrittlisten, und Auslöser sind Schritte mit einer `when:`-Bedingung. Die Schritte sind:

| Schritt | Wirkung |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | ein protokollierter Wurf; bindet `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>`; ein `{…}` wird zuerst ausgefüllt, wie in jedem Text, sodass Würfel, die ein Wert als Text hält, gewürfelt werden (`{@{who.inventory.$item.damage}}`), und das Protokoll zeigt sie: ein Wert, der keine Würfel sind, wird abgelehnt, ebenso `roll: "@die"` mit solchem Text, das nichts würfelt; eine Menge von Würfen (`{d8, d6}kh1`) bleibt eine |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | berechnet Werte; wie bei `value` von `set` ist `{…}`-Text eine Vorlage und ein bloßes Wort Text; in jedem ausgefüllten Text schreiben `{{` und `}}` die Klammer selbst |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (oder `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | ändert einen Eintrag: validiert, begrenzt, rückgängig machbar; `set: who.$attr` setzt das Feld, das ein Parameter nennt, und `set: who.inventory.$item.damage` einen Schlüssel eines mitgeführten Gegenstands (siehe Inventar); `-=` nimmt einen Wert aus einer Liste, und einer, den sie nicht enthält, ändert nichts (ein Hinweis sagt es; einer, den sie nie enthalten könnte, wird abgelehnt); `unset:` nimmt ein Feld weg, wie es `set --unset` tut |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | gibt einem Eintrag einen Gegenstand oder nimmt ihm einen ab, wie es `inv add` und `inv drop` tun: Seine Details kommen aus dem Kompendium, ein eindeutiger Teil seines Namens genügt, und der Platz und die Hooks des Felds werden geprüft |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | verwendet einen mitgeführten Gegenstand, wie es `inv use` tut: Verbrauch oder Ladungen zählen herunter, ein Verbrauchswürfel wird gewürfelt und sinkt bei 1–2 eine Stufe, und einer, der aufgebraucht ist, ist weg, außer er lädt sich wieder auf oder wird behalten; von mehreren mit diesem Namen der erste, der noch einen Verbrauch übrig hat; bindet `@torch.out` (sein letzter Verbrauch ist weg), `@torch.gone` (nichts davon ist übrig), `@torch.left`, `@torch.die` und `@torch.rolled` (`as:` ist standardmäßig `use`) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | legt sofort einen Eintrag an, beschrieben wie im `entity`-Schritt eines Entwurfs (siehe unten) und gegen seinen Bogen geprüft; `as:` (sonst sein `key`, sonst sein Typ) bindet ihn als Eintrag, der sich wie ein `ref`-Parameter lesen und setzen lässt (`pool: "@bleeding"`, `@bleeding.name`), und ist nie der Name eines Parameters; ohne `key:` wird kein Feld für einen gehalten (`kind: track` bleibt, wie es steht); ist hier schon einer dieses Typs und Namens vorhanden, wird er so genommen, wie er ist, sodass eine erneut ausgeführte Regel nichts Neues anlegt |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | führt eine Probe aus und bindet ihr Ergebnis |
| `do: other-action`, `with: {…}`, `as: trip` | führt eine andere Regel aus; `@trip` ist ihr Ergebnis und `@trip.<name>`, was sie gebunden hat (`@trip.found` für ihr `let: {found: 2}`, `@trip.luck` für ihr `roll: d6`, `as: luck`); `as:` ist standardmäßig ihre ID |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | ein protokollierter Tabellenwurf; bindet den Text und die `data` des Eintrags (`@scar.<key>`, und die Schlüssel einer Zuordnung über ihren Pfad: `@scar.cost.hp`), samt den Daten jeder Tabelle, auf die er danach würfelt; eine Liste von Gegenständen (`[Rope, {name: Laser, damage: d8}]`) liest sich als ihre Namen (`count(@scar.gear)`, `'Laser' in @scar.gear`), und einem Schritt so übergeben, wie sie ist (`apply: "@scar.gear"`), ist sie die Gegenstände selbst; eine Liste anderer Zuordnungen ist nur für einen Schritt lesbar |
| `table: "setting-{@drop.difficulty}-terrain"` | eine berechnete Tabelle: `{…}` und `$param` werden eingesetzt |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | mehrere Ergebnisse als Liste (`distinct` würfelt Wiederholungen neu) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | Verzweigungen |
| `repeat: "@count"`, `as: i`, `steps: […]` | eine Schleife: führt die Schritte entsprechend oft aus, `@i` zählt ab 1 |
| `for: pcs` (oder `party`), `as: member`, `steps: […]` | führt die Schritte einmal für jeden Spielercharakter (bzw. jedes Gruppenmitglied) aus, als `@member`: ein Eintrag wie der, den `entity:` bindet (`@member.name`, `set: member.fatigue`); `as:` darf nie wie ein Parameter heißen, sodass das eigene `who` der Regel unberührt bleibt |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | Ausgabe für das LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (oder `every: 1 day`) | eine Erinnerung, die fällig wird, während Spielzeit vergeht, so wie `didact remind` sie setzt |
| `reroll: roll`, `keep_if: "@face == 6"` | würfelt einige Würfel eines Wurfs neu (Push-Mechaniken) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | würfelt auf einem Listenwert (den Listen eines Orakels): bindet den Eintrag, `@who.choose` (eine Leerzeile) und `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | würfelt den schrumpfenden Pool eines Zählers wie `track roll` (Würfel mit 1-3 fallen weg; `drop`-Würfel fallen zuerst weg, `extra`-Würfel rollen mit) oder lässt nur Würfel wegfallen (`mode: drop`: ein Push, ein Tick); verknüpfte Phasen und das Ereignis des Pools folgen; bindet `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

Das Ergebnis einer Probe kann die Regel lesen, die sie ausgeführt hat (`check: … as: answer` ergibt `@answer`), ebenso ihre Markierungen: `'random-event' in @answer.flags`. `with:`-Werte werden ausgewertet, wenn sie `@` enthalten, ausgefüllt, wenn sie `$param` oder `{…}` enthalten („Does $npc flee?“), und sonst so übergeben, wie sie geschrieben sind. Eine Regel mit einem Parameter `oracle` erhält den Zustandseintrag des Kampagnenorakels, ohne dass man es ihr sagen muss. Ein `ref`-Parameter mit `to: monster` nimmt einen Eintrag dieses Typs: Ein Name, den ein anderer Eintrag teilt (der Pool eines Gegners, benannt wie seine Karte), ist der Eintrag dieses Typs.

Auslöser laufen von selbst, wenn ihr Ereignis eintritt, und nur, wenn ihr `when:` zutrifft:

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Jede Regel (auch Generatoren und die Charaktererschaffung) kann `@system` (die ID des Systems, mit dem die Welt gespielt wird, sodass ein für zwei Systeme geschriebenes Setting sie auseinanderhalten kann), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` und `@time.is_night` lesen, mit einem Kalender aus Monaten auch `@time.month`, `@time.month_name`, `@time.day_of_month` und `@time.year`; während ein Kampf läuft, auch `@combat.round` und `@combat.fighters` (die IDs der Beteiligten). Ein Zeit-Auslöser kann außerdem `@time.passed` lesen, die gerade vorgerückten Sekunden, ein `combat_start`- oder `combat_end`-Auslöser liest den Kampf, der beginnt oder endet (`combat start` und `combat end` führen sie aus; steigt ein Kämpfer aus, endet der Kampf nicht), und eine Regel, die ein Auslöser ausführt, liest, was der Auslöser liest. Ein Auslöser mit Pflichtparametern wird nur über `didact do` oder einen Feld-Hook (`who` = der Eintrag) ausgeführt. Auslöser mit `on: manual` laufen nur, wenn sie aufgerufen werden. `for: pcs` (oder `party`) führt einen Auslöser einmal für jeden Spielercharakter (bzw. jedes Gruppenmitglied) aus, als `who`: etwa Erfahrung nach jeder Sitzung. Ein Auslöser, der fehlschlägt, stoppt den Befehl, der ihn ausgelöst hat, und sagt, welcher Auslöser es war und wie man ohne ihn weitermacht (`didact override add trigger <id> --data '{"on": "manual"}'`).

Der Kalender steht in den `settings` eines Pakets: Der eines Setting-Pakets geht dem des Systems vor, und der eigene Kalender einer Welt (`calendar:` in ihrer `world.yaml`) beiden:

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

`leap: 4` macht einen Monat jedes 4. Jahr einen Tag länger, und `leap: [4, 100, 400]` jedes 4., aber nicht jedes 100., dafür doch jedes 400.: Jede Zahl hebt die vorige auf. `weekday` nennt den Wochentag des Beginns (sonst ist es der erste der Woche), und `year` ist, wie ein Datum sein Jahr schreibt, in den Daten, die Didact zeigt, wie in denen, die es liest (`"3A {year}"`: `17 Frost 3A 201`); `pack validate` prüft alle drei. Eine Kampagne kann an einem anderen Datum des Kalenders beginnen, vor seinem Beginn oder danach: `didact campaign new <id> --date '4 July 1902'`, oder `didact time set '<date>'` bis zu ihrer ersten Sitzung. Ein Wochentag vor dem Datum wird geprüft: Das Datum entscheidet, und ein Hinweis sagt es, wenn es auf einen anderen fällt.

Optionen sind die Varianten und optionalen Regeln des Systems, die jede Kampagne in der Session Zero wählt:

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

`didact campaign profile lethality=deadly supplies=on` speichert sie (oder die Seite „Einstellungen“ der Web-App). Regeln, Charaktererschaffung und Generatoren lesen sie (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`): Eine Antwort geht vor dem, was eine andere Option nahelegt, und das geht vor dem Standardwert. Was eine Option nahelegt, wird bis zum Ende verfolgt (eine Stimmung, die die Tödlichkeit festlegt, legt auch fest, was diese Tödlichkeit nahelegt), und von zwei Folgerungen gewinnt die nähere. Das Briefing nennt die, die von ihrem Standardwert abweichen, mit ihrer Bedeutung, damit die Spielleitung anwendet, was die Regeln nicht können. Ein Generator, der unter ihnen nicht laufen kann, bricht mit `stop:` und dem Grund ab, und es entsteht kein Entwurf.

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

- **Fragen:** `didact ask '…' --odds likely` führt die Probe `ask` aus. Die Antwort ist ihr Ergebnis (eine Stufe), und ihre Markierungen kommen mit.
- **Zustand:** Er liegt in einem Eintrag, den die Probe als `oracle` erhält. Eine Probe ändert ihn mit `set: oracle.chaos += 1`.
- **Listen:** `lists: {names: […], method: sections, most: 3}` führt gewichtete Listen auf diesem Eintrag. `didact lists add|drop|roll|show` verwalten sie, und Regeln würfeln mit `pick` darauf. `sections` würfelt einen Abschnitt aus fünf Zeilen, dann eine Zeile darin (eine Leerzeile heißt: wählen); `uniform` gibt jeder Zeile dieselbe Chance.
- **Mehr für die Probe:** `didact ask '…' --with as_rule=true` übergibt der Probe des Orakels zusätzliche Parameter.
- **Das Protokoll:** Jede Antwort wird nummeriert (`#o12`) und protokolliert, und `didact interpret o12 '…'` hält fest, was sie bedeutete. Das Orakel `yes-no` des Pakets core ist die Rückfalloption.

## Generatoren und Charaktererschaffung: `generators/`, `chargen/`

Beides sind Abläufe, die einen **Entwurf** bauen. Sie verwenden jeden Regelschritt (`roll`, `table`, `if`, `let`, `prompt`, …) und dazu diese:

| Schritt | Wirkung |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | fügt dem Entwurf einen Eintrag hinzu (Schlüssel `poi-1`, `poi-2`, …); ein Feld oder eine Verknüpfung, die einen vom Paket geschriebenen Schlüssel nennt (`key:` oder einen `as:`-Namen), wird beim Übernehmen zur ID dieses Eintrags, also wähle Schlüssel, die kein Feld als Text enthält (eine Entität ohne beides hat keinen, der ersetzt würde); `from: "@relic.id"` nimmt einen Kompendiumseintrag als Ausgangspunkt (mit dessen Typ, Namen und Feldern) |
| `choose: {from: [a, b], as: x}` (oder `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | eine Wahl; im geführten Modus wartet der Entwurf auf `choose`; `exclude` schließt frühere Wahlen aus (eine gewürfelte wird neu gewürfelt); `records:` fügt hier die Einträge dieses Typs hinzu, per ID (im Spiel entstandene); `answer:` trifft die Wahl ohne Nachfrage, wenn sein Wert eine der Optionen ist (der eigene Pfad eines Charakters) |
| `choose_or_roll: {table: backgrounds, as: background}` | eine Wahl, die auch die Würfel treffen können; die Daten eines gewählten Eintrags sind `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | würfelt Werte für den Charakter |
| `swap: {among: [STR, DEX, WIL], optional: true}` | zwei Werte tauschen oder behalten |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | ein festes Werte-Array verteilen |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | Werte innerhalb eines Budgets kaufen (`default: random` gibt es im Zufallsmodus zufällig aus) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | eine Liste kommt ins Inventar; eine Zuordnung setzt Felder (Listen summieren sich) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | fügt einem Feld des Charakters (oder einer entworfenen Entität) etwas hinzu: Zahlen summieren sich, alles andere kommt in eine Liste; nichts hinzuzufügen ist in Ordnung |
| `remove: {field: talents, value: "@old"}` | nimmt etwas aus einem Listenfeld (ein ausgetauschtes Talent, eine aufgelöste Bindung); fehlt es, ist das in Ordnung |
| `roll_tables: [physique, vice]` | würfelt Tabellen in `traits`; `data.gear` eines Eintrags kommt ins Inventar, und `data.add: {gold: 20}` addiert zu Feldern |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | der Name; `name: {prompt: …}` ohne etwas zum Würfeln wartet auf einen, selbst im Zufallsmodus |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | eine Frage, auf die jede Antwort passt (ein Ziel, der Name eines weiteren Eintrags): Der Entwurf wartet darauf, selbst im Zufallsmodus, außer sie ist vorausgefüllt; `field:` speichert die Antwort |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | ein Pointcrawl: ein protokollierter Würfel-Drop, Wege (immer verbunden), Entfernungen, versteckte Wege (siehe unten) |

Der Schritt map nimmt noch mehr an, für die Würfel-Drop-Abläufe aus dem Buch:

| Schlüssel | Wirkung |
|---|---|
| `regions: terrain` | diese Entitäten werden auch geworfen; jeder Ort gehört zur nächstgelegenen (seine `region`) |
| `hidden: 6`, `conditional: 5` | ein d6 pro Weg: bei dieser Zahl oder darüber ein versteckter oder bedingter Weg (versteckte Wege bleiben von der Karte der Spieler fern) |
| `describe: [path-feature, path-condition]` | Tabellen, die für jeden Weg gewürfelt und als seine `details` behalten werden |
| `entrance: true`, `exit: true` | der Ort, der dem Rand am nächsten ist, ist der Eingang; die übrigen werden von ihm aus entlang der Wege nummeriert (`map.n`), Wege führen von ihm weg, und der Ausgang ist ein ferner Ort nahe einem Rand, als letzter nummeriert |
| `number: "{@dungeon_name}, room {@n}"` | benennt die nummerierten Orte um (ihre Entwurfsschlüssel folgen: `room-1` ist Raum 1) |

Eine Würfel-Drop-Tabelle kann in den Daten ihrer Einträge die nächsten Tabellen nennen, sodass sich der Ablauf wie das Buch liest: `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, dann `table: "{@drop.what}"`. Nicht gesetzte Listenfelder (conditions, lists, tags) gelten als leere Listen, sodass `'deprived' in @who.conditions` von Anfang an funktioniert.

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

Eine Charaktererschaffung mit `advances:` ändert einen Eintrag, statt einen anzulegen: der Stufenaufstieg des Systems.

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

- **Ein Eintrag:** Ein Generator mit `creates: npc` baut diesen Eintrag so, wie die Charaktererschaffung einen Charakter baut (`apply`, `add`, `name`, `field:`); seine `entity`-Schritte fügen Einträge daneben hinzu, und ein Link `to: character` zeigt auf ihn.
- **Ausführen:** `gen run` und `char new` legen einen Entwurf an (`#g7`, `#c3`) und schreiben nichts. Ein `stop:` beendet ihn, ohne dass ein Entwurf entsteht: Unter einem `if:`, das eine Kampagnenoption liest, verweist sein Hinweis auf die Optionen (`didact session zero`); sonst sagen seine eigenen Worte, was stattdessen zu tun ist.
- **Entscheiden:** `--prefill '{…}'` entscheidet Dinge im Voraus, über den Namen, den ein Schritt bindet (`as:`): Ein einzelner Wert beantwortet jedes Vorkommen, eine Liste je ein Vorkommen (eine Liste für `choose` mit `count` ist die ganze Auswahl). Auch `let`-Werte lassen sich vorbelegen (`{"hp": 6}`), und ein Name, ein `ask` oder ein `let` übernimmt jeden Text so, wie er angegeben ist. Ein Wert für eine Wahl unter bekannten Optionen (ein `choose`, der Eintrag einer Tabelle) ist die Option, die er nennt, ob wörtlich (unabhängig von Groß-/Kleinschreibung), über die `id` ihres Eintrags oder über einen Wurf, der darauf landet (`{"group": 3}`), und bringt die Daten dieses Eintrags mit; einer, der einer Option nahekommt, aber keine davon ist, wird unter Nennung der nächstliegenden abgelehnt, und jeder andere ist eine eigene Antwort, ohne Daten. `--auto` (oder `char new --mode random`) lässt die Würfel den Rest entscheiden. Sonst wartet der Entwurf bei jeder Wahl.
- **Beschreiben:** Eine Wahl sagt, was jede Option bedeutet, für den Spieler, der wählt: das `note:` eines Tabelleneintrags oder das `about:` seiner Tabelle, sonst der Kompendiumseintrag, den er nennt (die `id` seiner Daten), oder der, der die Option selbst ist (eine Wahl zwischen Kompendium-IDs zeigt den Namen von jedem): seine Felder `tagline` und `summary`, `description` oder `effect`, sonst der erste Absatz seines Textes.
- **Zurückgehen:** `char back` (oder `gen back`) nimmt die letzte Antwort, den letzten Wurf oder die letzte Bearbeitung zurück, sodass der Entwurf diese Frage erneut stellt; die Würfe, die dabei gemacht wurden, werden als rückgängig markiert.
- **Fortsetzen:** Ein fortgesetzter Entwurf spielt seine Spur erneut ab: jeden gewürfelten oder gewählten Wert, jeden einmal und der Reihe nach (auch den Würfel-Drop der Karte), sodass nichts zweimal gewürfelt wird und sich nichts bereits Entschiedenes ändert.
- **Schreiben:** `commit` schreibt die Einträge, geprüft gegen ihre Bögen.
- **Voranbringen:** Ein `advances:`-Entwurf beginnt mit einer Kopie des Eintrags (samt den Standardwerten seines Bogens), seine Schritte lesen den Eintrag als `@who` und die Werte des Entwurfs als `@character.*`, und `commit` schreibt nur, was sich geändert hat, geprüft wie bei `set`; Einträge aus seinen `entity`-Schritten (der Handlungsfaden einer neuen Bindung) entstehen daneben: Ein Link `to: character` zeigt auf den Eintrag, und ein Feld, das einen Schlüssel nennt, enthält die ID des Eintrags, der aus diesem Schlüssel entsteht, wie bei der Charaktererschaffung (`apply: {blood: "@pool"}`). Ein `stop:` sagt, warum noch nicht (nicht genug EP), und es entsteht kein Entwurf. Ein System, dessen Entwicklung eine einzige Regel ist, nennt sie stattdessen in seiner Charaktererschaffung: `advance: {rule: grow}`.
- **Modi:** `modes: [guided]` lässt einen Ablauf nur Schritt für Schritt laufen: `--mode random` wird abgelehnt.

## Kompendium, Referenz und Glossar

- **Kompendiumseinträge** werden wie `new --data` geschrieben: `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Ein Wert von `"roll 2d8"` wird gewürfelt, wenn der Eintrag erzeugt wird. Führe `didact spawn troll` aus, oder hol die Einträge eines Pakets mit `didact compendium import <pack>` in die Welt (`--type loc`, und `--tag coast` für die mit jedem genannten Tag).
- **Für mehrere Systeme:** Ein Schlüssel auf oberster Ebene landet dort, wo `set` ihn hinsetzt: im Block des Systems, wenn dessen Bogen dieses Feld hat, sonst in `fields`. Ein Eintrag, den ein Setting für mehr als ein System schreibt, gibt die Zahlen jedes Systems in einem eigenen Block an (`mechanics: {my-system: {hp: 12}}`): `pack validate` prüft jeden gegen den Bogen dieses Systems, wenn es installiert ist, und vermerkt einen Schlüssel auf oberster Ebene, den dieser Bogen und der von core beide haben. Was ein Block sagt, gilt: Neben `mechanics: {my-system: {role: tactician}}` ist ein `role: innkeeper` auf oberster Ebene das Feld von core, wie alles unter `fields:`. Ein Block, der das gerade geprüfte Paket nennt, wird gegen dieses Paket geprüft, so wie es in seinem Ordner liegt.
- **Referenzabschnitte** kommen in `reference/*.md`, mit Front Matter (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` findet sie; eine Phrase in Anführungszeichen, die nicht vorkommt, wird mit ihren einzelnen Wörtern versucht.
- **Das Glossar** ist `glossary.yaml`: `term: definition` oder eine Liste von `{term, definition, aliases, see}`. `didact define <term>` liest es.

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

## Pakete teilen und entfernen

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Ein Paket, das `redistributable: false` angibt, lässt sich nicht exportieren.
- **core** ist Teil von Didact und immer aktiv: Jedes System baut darauf auf, deshalb lässt es sich weder deaktivieren noch deinstallieren.
- Die anderen mit Didact ausgelieferten Pakete sind `.didactpack`-Dateien in seinem Ordner `packs/`. `pack list` zeigt sie, bis sie installiert sind, und die Installation eines davon bringt die Pakete mit, die es braucht und die ebenfalls mitgeliefert werden.
- `pack update` sucht nach neueren Versionen im Ordner `packs/` von Didact und auf GitHub (`vess-dev/Didact`; `DIDACT_PACK_UPDATES` nennt einen anderen Ort, oder nichts, um nicht zu suchen). Eine neue Version wird neben der alten installiert: Kampagnen behalten ihre bis `didact campaign upgrade`.
- Es ist immer nur ein Spielsystem in Verwendung: das der geöffneten Welt. Eine Welt behält das System, mit dem sie erstellt wurde (`didact world new <id> --system <pack>`; eine ohne System erstellte nimmt das erste, das sie bekommt, mit `pack enable` oder `world set system=`), ihre Kampagnen werden damit gespielt, und ein Paket, das ein anderes System braucht (ein dafür geschriebenes Setting), lässt sich nicht hinzufügen: Ein anderes System wird in einer eigenen Welt gespielt.
- `uninstall` verweigert, solange eine Welt oder Kampagne die einzige Kopie des Pakets verwendet (`--force` entfernt es trotzdem). Es lässt sich nicht rückgängig machen: Installiere die .didactpack erneut.

## Vom Regelwerk zum Paket: die Checkliste

Geh die Mechaniken des Buchs in dieser Reihenfolge durch. Jede entspricht etwas von oben:

1. **Auflösung:** wie ein Wurf gelingt (eine Probe: `success`, `bands`, `auto`).
2. **Würfel:** ungewöhnliche Würfel, Symbole, Stufen (`dice.yaml`, benannte Würfel, Ketten).
3. **Der Bogen:** Attribute, abgeleitete Werte (`schemas/`, abgeleitete Felder).
4. **Ressourcen:** TP, Glück, Schwung (Ressourcen- und Zählerfelder; `set`-Schritte).
5. **Zustände:** Zustände und was sie bewirken (`conditions`-Felder; `if`-Schritte).
6. **Kampf:** Angriffe, Schaden, Initiative (Aktionen; `bag`/`deck` für die Zugreihenfolge).
7. **Abläufe:** Erkundung, Reisen, Auszeit (Abläufe mit Prompts).
8. **Tabellen:** jede Zufallstabelle (`tables/`; `pack import` für Markdown-Tabellen).
9. **Das Bestiarium:** Monster und NSC (`compendium/`).
10. **Gegenstände:** Ausrüstung, Zauber, Relikte (`compendium/`, slots-Felder).
11. **Rat für die SL:** Prinzipien und Tipps (`GUIDE.md`, `reference/`, `guidance:` auf Typen).
12. **Charaktererschaffung:** wie man einen Charakter erschafft (ein `chargen/`-Ablauf oder `roll:` auf jedem Feld).

Gib überall mit `source:` Seiten an, damit Lücken auffallen. Füge einen Probespiel-Test hinzu, der einen Charakter erschafft, eine Probe würfelt, kämpft und einen Ablauf ausführt.
