<!-- translated from b1dfa1159ff4 -->
# Packs

Un pack est un système de jeu, un oracle, un univers, une aventure ou un supplément, écrit sous forme de fichiers YAML plus un plugin Python facultatif. Ce guide montre comment en écrire un : transformer un livre de règles en pack, ou ajouter du contenu maison.

```
didact pack new my-hack --name "My Hack"        # a scaffold in the library's packs folder
didact pack add my-hack table --data '{…}'      # add content as JSON; Didact checks it and writes YAML
didact pack validate my-hack                    # every problem, with its file:line and a fix
didact pack lint my-hack                        # style notes: help, sources, guide
didact pack test my-hack                        # the pack's own tests and smoke-play scripts
didact pack enable my-hack                      # use it in the current campaign
```

Un pack peut aussi être fait à partir de ce que contient votre bibliothèque. `didact pack new my-brew --from-overlay my-system` transforme votre contenu maison pour un système (`compendium add`, les fiches gardées `--scope system`, le lore) en supplément, et `didact world export --as setting` transforme un monde en pack d'univers : ses personnes, lieux et lore deviennent des entrées du compendium et du lore de pack, à importer dans un autre monde avec `compendium import`. Les deux laissent de côté les secrets et les notes du MJ sauf avec `--secrets`, et aucun n'est marqué comme partageable tant que vous n'avez pas indiqué sa licence.

## Structure

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

Un fichier contient un élément, une liste d'éléments, ou plusieurs éléments séparés par `---`. Chaque élément indique son identifiant avec la clé de son genre : `table: weather`, `check: save`, `type: pc`, ou `id: troll` pour les entrées du compendium. Faites référence aux éléments par `pack.id` (`my-system.save`), ou par leur seul identifiant quand un seul pack activé le possède.

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

Un hack nomme sa base dans `extends` et ne contient que ce qui diffère :

```yaml
extends: [my-system]
hides:                         # what the base has that this pack drops, as patterns by kind
  entry: ["*", "!rope"]        # every compendium entry but the rope
  table: ["spell-*"]           # the spell tables
  reference: ["magic*"]        # the rules text on magic
  term: [spell]                # a glossary term, in lowercase
```

Son élément de même identifiant remplace celui de la base, quel que soit le genre (une table, une règle, une entrée du compendium, une section de référence, un terme de glossaire). Ses `settings` se superposent à ceux de la base, clé par clé : une clé que le hack définit remplace entièrement la valeur de la base (ses tables `names` prennent la place de celles de la base), et les règles de la base lisent aussi les valeurs du hack. `hides` écarte ce qui reste et dont le hack n'a pas l'usage : `*` correspond à n'importe quelle suite de caractères, le dernier motif qui correspond à un identifiant l'emporte, et un motif qui commence par `!` conserve l'élément. Ce que le hack remplace n'est jamais masqué. Les genres sont `type`, `table`, `deck`, `bag`, `check`, `action`, `procedure`, `trigger`, `option`, `entry`, `generator`, `chargen`, `oracle`, `lore`, `reference` et `term`. `didact pack validate` signale un motif qui ne correspond à rien.

## Expressions

Chaque condition et formule utilise le langage des dés (`didact guide dice`), plus :
- **Valeurs :** `@name` lit une valeur : `@roll`, `@who.STR`, `@settings.x`. `$name` colle d'abord le texte d'un paramètre, donc `@who.$attr` devient `@who.STR`. Lisez un paramètre de texte libre comme `@name`, pas entre apostrophes (`'$name'`) : une apostrophe dans son texte les fermerait (`pack validate` le signale).
- **Logique :** `and`, `or`, `not`, et `in` (`'deprived' in @who.conditions`).
- **Littéraux :** du texte (`'travel'`) et `true`/`false`.
- **Fonctions :** `if(cond, a, b)` ne lance que la branche retenue. `default(@thread.flashpoint, 0)` donne la valeur, ou la valeur de repli quand elle n'est pas définie. `sum`, `count` (`count(@roll.dice, 6)` compte les six), `min`, `max`, `any` et `all` prennent des listes.

## Feuilles : `schemas/`

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

| Genre | Contient | Options |
|---|---|---|
| `int`, `number`, `text`, `flag`, `enum` | une valeur simple | min, max ; `values` pour enum |
| `stat`, `resource`, `uses`, `pool` | `{value, max}` : `@hp` est la valeur, `@hp.max` le plafond | range ; min ; max ou max_field ; die |
| `counter` | un nombre | min, max, thresholds, occupies (un champ slots) |
| `track`, `clock` | `{value, size}` | size |
| `slots` | des objets (`Rope` ou `{name, size, count, uses, armor, …}`) | capacity, sizes, groups, when_full |
| `dice`, `ref`, `refs`, `tags`, `conditions`, `list`, `map` | comme leur nom l'indique | `to` (pour refs), `allowed` |
| `derived` | calculé, jamais stocké | expr |

Chaque champ accepte aussi `label`, `help`, `default`, `required` et `roll` : `new pc Hero --fill`, ou une valeur `"roll"`, le tire via le journal. Les types du pack `core` contiennent de la prose indépendante du système dans `fields`. Les types d'un système contiennent ses chiffres dans `mechanics.<system>`. `set hero hp-=2` trouve le champ, le borne et signale tout dépassement. `+=` ajoute à une liste : un champ `list` (comme `slots`) garde une valeur ajoutée de nouveau, `tags`, `conditions` et `refs` ne la gardent qu'une fois, et `-=` en retire tous les exemplaires.

**Les hooks** disent ce qui se passe quand une valeur franchit un seuil. Ils se déclenchent à chaque changement (`set`, `inv`, l'étape `set` d'une règle), mais seulement quand le seuil est franchi : 3 → 0 déclenche, 0 → 0 non. Les modifications avec `--force` les ignorent.

| Hook | Se déclenche quand |
|---|---|
| `on_zero` | un nombre ou `{value}` atteint 0 |
| `on_full` (`when_full` sur slots) | il atteint son max, sa taille ou sa capacité |
| `thresholds: {10: …, 20: …}` (compteurs) | il dépasse chaque palier |

Une action est du texte (une note pour le LLM), `{set: {hp: 0}}` ou `{condition: paralyzed}` sur la même fiche, `{trigger: death}` (lance cette règle avec `who` = la fiche), ou une liste de ceux-ci.

**L'inventaire** (`didact inv …`) agit sur le champ `slots` de la feuille :
- **Place :** les objets occupent leur `size` × `count`, et les compteurs qui `occupies` le champ occupent leur valeur. Dépasser `capacity` est refusé, sauf avec `--force`.
- **Groupes :** `groups: {backpack: 6, body: 4}` donne à chaque groupe sa propre place, ainsi que ses propres colonnes et totaux : `@inventory.body.armor` ne compte que ce qui est porté ou tenu en main, `@inventory.body.free` la place qui lui reste.
- **Utilisations :** `uses: 3` décompte avec `inv use`. `uses: d8` est un dé d'usure : sur 1–2, il descend d'un cran. Un objet épuisé disparaît, sauf s'il a `recharge` ou `keep: true`. De plusieurs objets d'un même nom, le nom désigne le premier ; pour dépenser une utilisation (`inv use`, le `use:` d'une règle, `set …uses-=1`), le premier à qui il en reste une.
- **Clés propres à un objet :** `didact set freya inventory.sword.damage=d10` (tout comme `set: who.inventory.$item.damage` dans une règle) en modifie une, l'objet étant désigné comme avec `inv`, par une partie de son nom ou par son nom entier, espaces et points compris (`'inventory.12.7mm pistol.damage=d10'`, entre apostrophes pour le shell) ; `uses` et `charges` fonctionnent comme un champ `uses` (`charges+=2` s'arrête à son maximum), et la place est vérifiée comme le fait `inv add`. Une règle en lit une sous la forme `@{who.inventory.$item.damage}` (un dé d'usure comme son dé, les utilisations comme leur nombre) ; un objet ou une clé qui n'est pas là se lit comme absent, si bien que `default(…)` donne sa valeur de repli.
- **Compendium :** les entrées de type `item` (ou weapon, armor, relic, …, ou un type propre au pack qui en étend un avec `extends`) prêtent leurs détails à `inv add`, trouvées par leur identifiant, leur nom ou un alias (si deux en partagent un : nommez-la `pack.id`) ; tout autre nom, `:` compris, est le nom propre de l'objet.

## Tables : `tables/`

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

Autres formes :
- **Listes pondérées :** `entries` sous forme de liste, avec `weight:` par entrée.
- **Colonnes :** `columns: [a, b]` tire chaque colonne d'une ligne séparément. Une entrée simple (pas une liste) remplit toutes les colonnes, donc `columns: [first, second]` sur une liste de mots signifie « tirer deux fois sur cette liste ». `labels: false` omet le nom des colonnes du résultat (« Abandon · Advantage »). `read: "It's a {first} {second} with {third} {fourth} inside."` lit les colonnes comme une phrase.
- **Tables de correspondance :** `lookup: hp_lost`, ou `[odds, chaos]` pour une grille à deux entrées.
- **Doublons :** `duplicates: reroll | keep | make_it_worse` pour « tirer deux fois ».
- **En deux temps :** une entrée qui tire sur une autre table (`{table: lightning}` au lieu d'un texte, ou `then:` à sa suite) apporte avec elle les données de ce tirage : une règle ou un brouillon qui la tire lit les deux, d'abord les clés propres à l'entrée, puis celles de la première table tirée ensuite. Un `--prefill` peut nommer une entrée plus bas, à n'importe quelle profondeur (`Ring of the Hunt`), avec les données de chaque entrée en chemin : de deux entrées du même nom, c'est la plus proche qui compte (puis la première), une entrée qui enchaîne continue à tirer à partir de là, et une entrée proche de l'une d'elles sans en être aucune est refusée, en nommant la plus proche. Un brouillon guidé propose la première étape quand ses entrées disent ce qu'elles sont (`{text: "A ring: roll on Rings", then: [{table: rings}]}`) : en choisir une tire sur la table suivante, comme un tirage qui tombe dessus.
- **Lecture dans les deux sens :** `both_ways: true` sur une table d66 ajoute l'autre lecture : 31 donne aussi 13, et le lecteur choisit.
- **Ce que signifie une entrée :** `about: "Knows: {skills}. Also known as: {aka}."` se remplit avec les données de chaque entrée (une liste se lit `a, b` ; `{text}` est l'entrée elle-même) pour dire ce qu'elle donne quand un choix la propose ; le `note:` propre à une entrée le dit à sa place. Sans l'un ni l'autre, une entrée dont les données ont un `id` qui nomme une entrée du compendium est décrite par cette entrée.
- **Paquets et sacs :** `deck: tarot` avec `cards` (ou `standard: true`) ; `bag: initiative` avec `tokens`.

La validation vérifie que chaque résultat possible des dés tombe sur une entrée.

## Règles : `rules/`

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

Les actions et les procédures sont des listes d'étapes, et les déclencheurs sont des étapes avec une garde `when:`. Les étapes sont :

| Étape | Effet |
|---|---|
| `roll: 2d6` (`as: dmg`) / `roll: "{@die} + 1"` | un jet journalisé ; lie `@dmg`, `@dmg.dice`, `@dmg.0`, `@dmg.flags`, `@dmg.<tag>`, `@dmg.symbols.<name>` ; un `{…}` est d'abord rempli, comme dans tout texte, si bien que des dés qu'une valeur contient sous forme de texte sont lancés (`{@{who.inventory.$item.damage}}`), et le journal les montre : une valeur qui n'est pas des dés est refusée, tout comme `roll: "@die"` sur un tel texte, qui ne lance rien ; un ensemble de jets (`{d8, d6}kh1`) en reste un |
| `let: {dealt: "max(0, @dmg - @target.armor)", title: "{@who.name} the Bold"}` | calcule des valeurs ; comme pour le `value` de `set`, un texte `{…}` est un modèle et un mot seul est du texte ; dans tout texte qu'on remplit, `{{` et `}}` écrivent l'accolade elle-même |
| `set: target.hp`, `op: "-="`, `value: "@dealt"` (ou `set: "target.hp -= @dealt"`) / `unset: who.curse_timer` | modifie une fiche : validé, borné, annulable ; `set: who.$attr` définit le champ que désigne un paramètre, et `set: who.inventory.$item.damage` une clé d'un objet que porte la fiche (voir Inventaire) ; `-=` retire une valeur d'une liste, et une valeur qu'elle ne contient pas ne change rien (une note le dit ; une valeur qu'elle ne pourrait jamais contenir est refusée) ; `unset:` retire un champ, comme `set --unset` |
| `give: Rope`, `to: "@who"` (`count: 2`, `data: {damage: d10}`) / `take: Rope`, `from: "@who"` (`count: 1`) | donne un objet à une fiche ou lui en retire un, comme `inv add` et `inv drop` : ses détails viennent du compendium, une partie unique de son nom suffit, et la place ainsi que les hooks du champ sont vérifiés |
| `use: Torch`, `from: "@who"` (`spend: 2`, `as: torch`) | utilise un objet porté comme le fait `inv use` : les utilisations ou les charges décomptent, un dé d'usure est lancé et descend d'un cran sur 1–2, et un objet épuisé disparaît, sauf s'il se recharge ou est gardé ; de plusieurs objets de ce nom, le premier à qui il reste une utilisation ; lie `@torch.out` (sa dernière utilisation est partie), `@torch.gone` (il n'en reste rien), `@torch.left`, `@torch.die` et `@torch.rolled` (`as:` vaut `use` par défaut) |
| `entity: {type: track, name: "{@who.name}: Bleeding Out", fields: {kind: pool, value: {value: 4, max: 4}}}`, `as: bleeding` | crée aussitôt une fiche, décrite comme l'`entity` d'un brouillon (ci-dessous) et vérifiée d'après sa feuille ; `as:` (sinon sa `key`, sinon son type) la lie en tant que fiche, lue et modifiée comme un paramètre `ref` (`pool: "@bleeding"`, `@bleeding.name`), et n'est jamais le nom d'un paramètre ; sans `key:`, aucun champ n'est pris pour une clé (`kind: track` reste tel quel) ; une fiche de ce type et de ce nom déjà présente ici est prise telle quelle, donc une règle relancée ne crée rien de nouveau |
| `check: save`, `with: {who: "@target", attr: STR}`, `as: crit` | lance un test et lie son issue |
| `do: other-action`, `with: {…}`, `as: trip` | lance une autre règle ; `@trip` est son issue et `@trip.<name>` ce qu'elle a lié (`@trip.found` pour son `let: {found: 2}`, `@trip.luck` pour son `roll: d6`, `as: luck`) ; `as:` vaut par défaut son identifiant |
| `table: scars`, `with: {hp_lost: "@lost"}`, `as: scar` | un tirage de table journalisé ; lie le texte et les `data` de l'entrée (`@scar.<key>`, et les clés d'un dictionnaire par leur chemin : `@scar.cost.hp`), ainsi que les données de toute table tirée ensuite ; une liste d'objets (`[Rope, {name: Laser, damage: d8}]`) se lit comme leurs noms (`count(@scar.gear)`, `'Laser' in @scar.gear`), et donnée telle quelle à une étape (`apply: "@scar.gear"`), ce sont les objets eux-mêmes ; une liste d'autres dictionnaires ne se lit que dans une étape |
| `table: "setting-{@drop.difficulty}-terrain"` | une table calculée : `{…}` et `$param` sont remplis |
| `table: advantages`, `times: "@count"`, `distinct: true`, `as: picks` | plusieurs résultats sous forme de liste (`distinct` relance les répétitions) |
| `if: "@crit == 'failure'"`, `then: […]`, `else: […]` | branches |
| `repeat: "@count"`, `as: i`, `steps: […]` | une boucle : les étapes autant de fois que demandé, avec `@i` qui compte à partir de 1 |
| `for: pcs` (ou `party`), `as: member`, `steps: […]` | les étapes une fois pour chaque personnage joueur (ou membre du groupe), comme `@member` : une fiche, semblable à celle que lie `entity:` (`@member.name`, `set: member.fatigue`) ; `as:` ne prend jamais le nom d'un paramètre, donc le `who` propre à la règle reste intact |
| `message: "{@who.name} falls."`, `prompt: …`, `reminder: …`, `stop: …` | sortie pour le LLM |
| `remind: "{@who.name} dies unless stabilized"`, `in: 1 hour` (ou `every: 1 day`) | un rappel qui arrive à échéance à mesure que le temps de jeu passe, comme ceux que programme `didact remind` |
| `reroll: roll`, `keep_if: "@face == 6"` | relance certains dés d'un jet (pour pousser un jet) |
| `pick: "@oracle.characters"`, `method: sections`, `as: who` | tire dans une valeur de liste (les listes d'un oracle) : lie l'entrée, `@who.choose` (une ligne vide) et `@who.empty` |
| `pool: "@quarry"` (`drop: 1`, `extra: "@spark"`, `mode: drop`, `as: q`) | lance la réserve décroissante d'un compteur comme `track roll` (les dés qui font 1-3 sont retirés ; les dés de `drop` sont retirés d'abord, ceux de `extra` sont lancés avec les autres) ou retire seulement des dés (`mode: drop` : pousser, cocher une case) ; les phases liées et l'événement de la réserve suivent ; lie `@q.highest`, `@q.dropped`, `@q.left`, `@q.empty`, `@q.faces` |

L'issue d'un test est lisible par la règle qui l'a lancé (`check: … as: answer` donne `@answer`), tout comme ses indicateurs : `'random-event' in @answer.flags`. Les valeurs de `with:` sont évaluées quand elles contiennent `@`, remplies quand elles contiennent `$param` ou `{…}` (« Does $npc flee? »), et transmises telles quelles sinon. Une règle avec un paramètre `oracle` reçoit la fiche d'état de l'oracle de la campagne sans qu'on le lui dise. Un paramètre `ref` avec `to: monster` prend une fiche de ce type : un nom qu'une autre fiche partage (la réserve d'un adversaire, nommée comme sa carte) désigne celle de ce type.

Les déclencheurs s'exécutent d'eux-mêmes quand leur événement se produit, et seulement si leur `when:` est vrai :

```yaml
trigger: new-day
on: time            # time | scene_start | scene_end | session_start | session_end | combat_start | combat_end | manual
when: "@time.passed >= 86400"
steps: ["A new day dawns: check rations."]
```

Toute règle (y compris un générateur et la création de personnage) peut lire `@system` (l'identifiant du système de jeu du monde, pour qu'un univers écrit pour deux systèmes puisse les distinguer), `@session`, `@scene`, `@time.day`, `@time.hour`, `@time.watch` et `@time.is_night`, et, avec un calendrier de mois, `@time.month`, `@time.month_name`, `@time.day_of_month` et `@time.year` ; tant qu'un combat est en cours, `@combat.round` et `@combat.fighters` (les identifiants de ceux qui y participent). Un déclencheur temporel peut aussi lire `@time.passed`, les secondes qui viennent de s'écouler, un déclencheur `combat_start` ou `combat_end` lit le combat qui commence ou se termine (`combat start` et `combat end` les lancent ; le départ d'un combattant ne met pas fin au combat), et une règle lancée par un déclencheur lit ce que celui-ci lit. Un déclencheur avec des paramètres obligatoires n'est lancé que par `didact do` ou un hook de champ (`who` = la fiche). Les déclencheurs `on: manual` ne s'exécutent que lorsqu'on les appelle. `for: pcs` (ou `party`) exécute un déclencheur une fois pour chaque personnage joueur (ou membre du groupe), comme `who` : l'expérience après chaque séance, par exemple. Un déclencheur qui échoue arrête la commande qui l'a lancé, et dit de quel déclencheur il s'agit et comment continuer sans lui (`didact override add trigger <id> --data '{"on": "manual"}'`).

Le calendrier se trouve dans les `settings` d'un pack : celui d'un pack d'univers l'emporte sur celui du système, et celui d'un monde (`calendar:` dans son `world.yaml`) sur les deux :

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

`leap: 4` rallonge un mois d'un jour tous les 4 ans, et `leap: [4, 100, 400]` tous les 4 ans, mais pas tous les 100 ans, mais de nouveau tous les 400 ans : chaque nombre l'emporte sur le précédent. `weekday` nomme le jour de la semaine du début (sinon, c'est le premier de la semaine), et `year` est la façon dont une date écrit son année, dans celles que Didact affiche comme dans celles qu'il lit (`"3A {year}"` : `17 Frost 3A 201`) ; `pack validate` vérifie les trois. Une campagne peut commencer à une autre date du calendrier, avant son début ou après : `didact campaign new <id> --date '4 July 1902'`, ou `didact time set '<date>'` jusqu'à sa première séance. Un jour de la semaine écrit devant la date est vérifié : la date décide, et une note le dit quand elle tombe un autre jour.

Les options sont les variantes et règles optionnelles du système, que chaque campagne choisit en session zéro :

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

`didact campaign profile lethality=deadly supplies=on` les enregistre (ou la page Paramètres de l'application web). Les règles, la création de personnage et les générateurs les lisent (`if: "@option.lethality == 'deadly'"`; `@option.rest_resets` = `rest-resets`) : une réponse l'emporte sur ce qu'une autre option implique, qui l'emporte sur la valeur par défaut. Les implications d'une option sont suivies jusqu'au bout (une ambiance qui fixe la létalité fixe aussi ce que cette létalité implique), et entre deux implications, la plus proche l'emporte. Le résumé liste celles qui diffèrent de leur valeur par défaut, avec leur sens, pour que le MJ applique ce que les règles ne peuvent pas. Un générateur qui ne peut pas tourner avec elles s'arrête sur `stop:` avec la raison, et aucun brouillon n'est créé.

## Oracles : `oracles/`

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

- **Interroger :** `didact ask '…' --odds likely` lance le test `ask`. La réponse est son issue (une tranche), accompagnée de ses indicateurs.
- **État :** il vit dans une fiche que le test reçoit comme `oracle`. Un test le modifie avec `set: oracle.chaos += 1`.
- **Listes :** `lists: {names: […], method: sections, most: 3}` garde des listes pondérées sur cette fiche. `didact lists add|drop|roll|show` les gèrent, et les règles y tirent avec `pick`. `sections` tire une section de cinq lignes, puis une ligne dedans (une ligne vide signifie au choix) ; `uniform` donne la même chance à chaque ligne.
- **Plus pour le test :** `didact ask '…' --with as_rule=true` passe des paramètres supplémentaires au test de l'oracle.
- **Le journal :** chaque réponse est numérotée (`#o12`) et journalisée, et `didact interpret o12 '…'` garde ce qu'elle signifiait. L'oracle `yes-no` du pack core sert de repli.

## Générateurs et création de personnage : `generators/`, `chargen/`

Les deux sont des procédures qui construisent un **brouillon**. Elles utilisent toutes les étapes de règle (`roll`, `table`, `if`, `let`, `prompt`, …) plus celles-ci :

| Étape | Effet |
|---|---|
| `entity: {key: poi, type: loc, name: "The {@adjective} {@noun}", fields: {…}}` | ajoute une fiche au brouillon (clés `poi-1`, `poi-2`, …) ; un champ ou un lien qui nomme une clé écrite par le pack (`key:`, ou un nom `as:`) devient l'identifiant de cette fiche à la validation, donc choisissez des clés qu'aucun champ ne contient comme texte (une entité sans l'un ni l'autre n'a pas de clé à remplacer) ; `from: "@relic.id"` la crée à partir d'une entrée du compendium (son type, son nom et ses champs) |
| `choose: {from: [a, b], as: x}` (ou `table: t`, `table: "setting-{@kind}"`, `count: 2`, `field: x`, `exclude: "@first"`, `records: talent`, `answer: "@who.path"`) | un choix ; en mode guidé, le brouillon attend `choose` ; `exclude` écarte les choix précédents (un choix exclu sorti aux dés est relancé) ; `records:` ajoute les fiches de ce type présentes ici, par identifiant (créées en jeu) ; `answer:` fait le choix quand sa valeur est l'une des options (la voie propre à un personnage), sans rien demander |
| `choose_or_roll: {table: backgrounds, as: background}` | un choix que les dés peuvent faire ; les données d'une entrée choisie sont `@background.gear` |
| `roll: {each: [STR, DEX, WIL], dice: 3d6}` / `roll: {hp: 1d6}` | tire dans le personnage |
| `swap: {among: [STR, DEX, WIL], optional: true}` | échanger deux valeurs, ou les garder |
| `assign: {fields: [edge, heart, iron], values: [3, 2, 1]}` | répartir un tableau fixe |
| `point_buy: {fields: […], budget: 27, costs: {8: 0, …}, default: […]}` | acheter des valeurs dans un budget (`default: random` le dépense au hasard en mode aléatoire) |
| `apply: "@background.gear"` / `apply: {age: "{@character.age + 4}"}` | une liste va dans l'inventaire ; un dictionnaire définit des champs (les listes s'additionnent) |
| `add: {field: gold, value: "@bond.gold"}` / `add: {to: "@forest", field: trails, value: "…"}` | ajoute à un champ du personnage (ou d'une entité du brouillon) : les nombres s'additionnent, le reste rejoint une liste ; rien à ajouter ne pose pas de problème |
| `remove: {field: talents, value: "@old"}` | retire quelque chose d'un champ de liste (un talent remplacé, une attache résolue) ; s'il n'y a rien à retirer, ce n'est pas un problème |
| `roll_tables: [physique, vice]` | tire des tables dans `traits` ; le `data.gear` d'une entrée va dans l'inventaire et `data.add: {gold: 20}` ajoute aux champs |
| `name: {from: "@background.names"}` / `name: {table: first-names}` | le nom ; `name: {prompt: …}` sans rien où tirer en attend un, même en mode aléatoire |
| `ask: {as: goal, prompt: "a goal it's working toward"}` | une question à laquelle toute réponse convient (un objectif, le nom d'une autre fiche) : le brouillon l'attend, même en mode aléatoire, sauf si elle est préremplie ; `field:` garde la réponse |
| `map: {places: poi, paths: {max: 3}, watches: {short: 1, …}, hidden: 6}` | un pointcrawl : un lâcher de dés journalisé, des chemins (toujours connectés), des distances, des chemins cachés (voir ci-dessous) |

L'étape map accepte plus, pour les procédures de lâcher de dés des livres :

| Clé | Effet |
|---|---|
| `regions: terrain` | ces entités sont lâchées aussi ; chaque lieu rejoint la plus proche (sa `region`) |
| `hidden: 6`, `conditional: 5` | un d6 par chemin : à ce nombre ou au-dessus, un chemin caché ou conditionnel (les chemins cachés restent hors de la carte des joueurs) |
| `describe: [path-feature, path-condition]` | tables tirées pour chaque chemin, gardées comme ses `details` |
| `entrance: true`, `exit: true` | le lieu le plus proche du bord est l'entrée ; les autres sont numérotés à partir de lui le long des chemins (`map.n`), les chemins s'en éloignent, et la sortie est un lieu lointain près d'un bord, numéroté en dernier |
| `number: "{@dungeon_name}, room {@n}"` | renomme les lieux numérotés (leurs clés de brouillon suivent : `room-1` est la salle 1) |

Une table de lâcher de dés peut nommer les tables suivantes dans les données de ses entrées, pour que la procédure se lise comme le livre : `{text: Lair, data: {room: lair, what: dungeon-lair, detail: dungeon-lair-feature}}`, puis `table: "{@drop.what}"`. Les champs de liste non définis (conditions, listes, tags) se lisent comme des listes vides, donc `'deprived' in @who.conditions` fonctionne dès le départ.

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

Un chargen avec `advances:` modifie une fiche au lieu d'en créer une : la montée de niveau du système.

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

- **Une seule fiche :** un générateur avec `creates: npc` construit cette fiche comme la création de personnage construit un personnage (`apply`, `add`, `name`, `field:`) ; ses étapes `entity` ajoutent des fiches à côté, et un lien `to: character` pointe vers elle.
- **Lancer :** `gen run` et `char new` créent un brouillon (`#g7`, `#c3`) et n'écrivent rien. Un `stop:` y met fin sans rien créer : sous un `if:` qui lit une option de la campagne, son conseil renvoie aux options (`didact session zero`) ; sinon, ses propres mots disent quoi faire à la place.
- **Décider :** `--prefill '{…}'` décide des choses à l'avance, par le nom que lie une étape (`as:`) : une valeur seule répond à chaque occurrence, une liste à une occurrence chacune (une liste pour `choose` avec `count` est le choix entier). Les valeurs de `let` peuvent aussi être préremplies (`{"hp": 6}`), et un nom, un `ask` ou un `let` garde tout texte tel quel. Une valeur pour un choix parmi des options connues (un `choose`, une entrée de table) est l'option qu'elle nomme, telle qu'écrite ou dans une autre casse, par l'`id` de son entrée, ou par un jet qui tombe sur elle (`{"group": 3}`), et apporte les données de cette entrée ; une valeur proche d'une option sans correspondre à aucune est refusée, avec mention de la plus proche, et toute autre est une réponse libre, sans données. `--auto` (ou `char new --mode random`) laisse les dés décider du reste. Sinon, le brouillon attend à chaque choix.
- **Décrire :** un choix dit ce que signifie chaque option, pour le joueur qui choisit : le `note:` d'une entrée de table ou le `about:` de sa table, sinon l'entrée du compendium qu'elle nomme (l'`id` de ses données), ou celle qu'est l'option elle-même (un choix parmi des identifiants du compendium montre le nom de chacun) : son `tagline` et son `summary`, sa `description` ou son `effect`, sinon le premier paragraphe de son texte.
- **Revenir en arrière :** `char back` (ou `gen back`) annule la dernière réponse, le dernier jet ou la dernière modification, et le brouillon repose donc cette question ; les jets faits par cette étape sont marqués comme annulés.
- **Reprendre :** un brouillon repris rejoue sa trace : chaque valeur tirée ou choisie, chacune utilisée une fois et dans l'ordre (le lâcher de dés de la carte aussi), donc rien n'est tiré deux fois et rien de déjà décidé ne change.
- **Écrire :** `commit` écrit les fiches, vérifiées d'après leurs feuilles.
- **Progresser :** un brouillon `advances:` part d'une copie de la fiche (avec les valeurs par défaut de sa feuille), ses étapes lisent la fiche comme `@who` et les valeurs du brouillon comme `@character.*`, et `commit` n'écrit que ce qui a changé, vérifié comme avec `set` ; les fiches issues de ses étapes `entity` (l'intrigue d'une nouvelle attache) sont créées à côté : un lien `to: character` pointe vers la fiche, et un champ qui nomme une clé contient l'identifiant de la fiche de cette clé, comme lors de la création d'un personnage (`apply: {blood: "@pool"}`). Un `stop:` dit pourquoi ce n'est pas encore possible (pas assez d'XP), et aucun brouillon n'est créé. Un système dont la progression tient en une seule règle la nomme plutôt dans son chargen : `advance: {rule: grow}`.
- **Modes :** `modes: [guided]` garde une procédure étape par étape : `--mode random` est refusé.

## Compendium, référence et glossaire

- **Les entrées du compendium** s'écrivent comme `new --data` : `{id: troll, type: npc, name: Troll, hp: 12, STR: 16}`. Une valeur `"roll 2d8"` est tirée quand l'entrée apparaît. Lancez `didact spawn troll`, ou importez les entrées d'un pack dans le monde avec `didact compendium import <pack>` (`--type loc`, et `--tag coast` pour celles qui portent toutes les étiquettes données).
- **Pour plusieurs systèmes :** une clé de premier niveau va là où `set` la met : dans le bloc du système quand sa feuille a ce champ, sinon dans `fields`. Une entrée qu'un univers écrit pour plus d'un système donne les chiffres de chacun dans son propre bloc (`mechanics: {my-system: {hp: 12}}`) : `pack validate` vérifie chacun par rapport à la feuille de ce système quand il est installé, et signale une clé de premier niveau que cette feuille et celle de core ont toutes deux. Ce que dit un bloc tient : à côté de `mechanics: {my-system: {role: tactician}}`, un `role: innkeeper` de premier niveau est le champ de core, comme tout ce qui est sous `fields:`. Un bloc qui nomme le pack en cours de validation est vérifié d'après ce pack tel qu'il est dans son dossier.
- **Les sections de référence** vont dans `reference/*.md`, avec un en-tête (`id`, `title`, `tags`, `page`, `mechanics: [save]`). `didact rules lookup <topic>` les trouve ; une expression entre guillemets qui n'y figure pas est essayée mot par mot.
- **Le glossaire** est `glossary.yaml` : `term: definition`, ou une liste de `{term, definition, aliases, see}`. `didact define <term>` le lit.

## Tests : `tests/`

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

## Partager et retirer des packs

```
didact pack export my-hack --to ~/Desktop                    # my-hack-0.1.0.didactpack
didact pack install ~/Downloads/my-hack-0.1.0.didactpack     # or a folder, or an https URL
didact pack install my-system                                # a pack that ships with Didact, by its id
didact pack update                                           # newer versions of the installed packs
didact pack disable my-hack                                  # stop using it here
didact pack uninstall my-hack                                # what would go, and who uses it
didact pack uninstall my-hack --yes                          # remove it
```

- Un pack qui déclare `redistributable: false` ne peut pas être exporté.
- **core** fait partie de Didact et est toujours actif : chaque système repose sur lui, il ne peut donc être ni désactivé ni désinstallé.
- Les autres packs fournis avec Didact sont des fichiers `.didactpack` dans son dossier `packs/`. `pack list` les montre tant qu'ils ne sont pas installés, et en installer un installe aussi les packs fournis dont il a besoin.
- `pack update` cherche des versions plus récentes dans le dossier `packs/` de Didact et sur GitHub (`vess-dev/Didact` ; `DIDACT_PACK_UPDATES` désigne un autre endroit, ou rien pour ne pas chercher). Une nouvelle version s'installe à côté de l'ancienne : les campagnes gardent la leur jusqu'à `didact campaign upgrade`.
- Un seul système de jeu est utilisé à la fois : celui du monde ouvert. Un monde garde le système avec lequel il a été créé (`didact world new <id> --system <pack>` ; un monde créé sans système prend le premier qu'on lui donne, avec `pack enable` ou `world set system=`), ses campagnes se jouent avec lui, et un pack qui a besoin d'un autre système (un univers écrit pour lui) ne peut pas être ajouté : un autre système se joue dans un monde qui lui est propre.
- `uninstall` refuse tant qu'un monde ou une campagne utilise l'unique copie du pack (`--force` le retire quand même). Cela ne peut pas être annulé : réinstallez le .didactpack.

## Du livre de règles au pack : la liste de contrôle

Parcourez les mécaniques du livre dans cet ordre. Chacune correspond à quelque chose ci-dessus :

1. **Résolution :** comment un jet réussit (un test : `success`, `bands`, `auto`).
2. **Dés :** dés inhabituels, symboles, échelons (`dice.yaml`, dés nommés, chaînes).
3. **La feuille :** caractéristiques, valeurs dérivées (`schemas/`, champs dérivés).
4. **Ressources :** PV, chance, élan (champs resource et counter ; étapes `set`).
5. **États :** les états et leurs effets (champs `conditions` ; étapes `if`).
6. **Combat :** attaques, dégâts, initiative (actions ; `bag`/`deck` pour l'ordre des tours).
7. **Procédures :** exploration, voyage, temps libre (procédures avec des consignes).
8. **Tables :** chaque table aléatoire (`tables/` ; `pack import` pour les tables Markdown).
9. **Le bestiaire :** monstres et PNJ (`compendium/`).
10. **Objets :** équipement, sorts, reliques (`compendium/`, champs slots).
11. **Conseils au MJ :** principes et conseils (`GUIDE.md`, `reference/`, `guidance:` sur les types).
12. **Création de personnage :** comment créer un personnage (une procédure `chargen/`, ou `roll:` sur chaque champ).

Citez les pages avec `source:` partout, pour que les manques apparaissent. Ajoutez un test de partie rapide qui crée un personnage, lance un test, combat et exécute une procédure.
